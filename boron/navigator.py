"""Vision-driven navigation. Screenshot -> Qwen3-VL -> one action -> repeat.

The model supplies the *intent* (where a user would aim); the profile supplies
the *channel* (tremor, dwell, keyboard-only). Boron never snaps a click to the
nearest element -- if it did, tremor could never miss and the disparity this
whole system measures would vanish.

Nothing here names the profile to the model. `docs/idea-brief.md` rejects
persona role-play, so a constraint is expressed by what the model is *given*:
a zoomed screenshot, a click-free vocabulary, or no image at all.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from boron.capture import element_at_point, focusable_ax_text, viewport_screenshot_b64

MAX_STEPS = 12

# Qwen3-VL grounds on a normalized 0-1000 grid per axis rather than in image
# pixels. Measured against tests/fixtures/test_page.html its boxes match true
# geometry to within one unit once divided by 1000, and telling it the pixel
# size of the screenshot does not change that. So state the grid in the prompt
# and convert deterministically -- that holds for any model which follows the
# instruction and never depends on the screenshot's pixel dimensions.
COORDINATE_SCALE = 1000

# How many times a model may claim the goal is met while the page disagrees.
# Observed live: told only that the goal was not visible, Qwen3-VL repeated
# "done" for the whole remaining budget without looking again. One correction
# is worth giving; a second identical claim means it is not going to re-examine
# the page, and the run should end rather than spend the budget arguing.
MAX_UNVERIFIED_DONE = 2
# Observed live on Wikipedia: Qwen3-VL clicked the same dead heading 12 times
# after being told it did nothing. Two identical misses is enough.
MAX_IDENTICAL_DEAD = 2
# An action that navigates leaves no page to screenshot or query until the next
# document exists. Bounded, because a page that never settles must not hang the
# step budget.
SETTLE_TIMEOUT_MS = 5_000

_ACTIONS_POINTER = """{"action": "click", "x": <int>, "y": <int>, "target": "<what you are aiming at>"}
{"action": "press", "key": "Tab" | "Shift+Tab" | "Enter"}
{"action": "type", "text": "<text to type into the focused field>"}
{"action": "scroll", "dy": <int, positive scrolls down>}
{"action": "done", "reason": "<why the goal is met>"}
{"action": "give_up", "reason": "<why the goal cannot be met>"}"""

# keyboard_only and screen_reader_users have no pointer. Removing the verb is
# the constraint -- there is no instruction telling them to pretend.
_ACTIONS_KEYBOARD = """{"action": "press", "key": "Tab" | "Shift+Tab" | "Enter"}
{"action": "type", "text": "<text to type into the focused field>"}
{"action": "done", "reason": "<why the goal is met>"}
{"action": "give_up", "reason": "<why the goal cannot be met>"}"""

_SYSTEM = """You operate a web page one action at a time to accomplish a goal.

Reply with exactly one JSON object and nothing else. Valid actions:

{actions}

Rules:
- Coordinates are on a 0-1000 grid, whatever the image size: x=0 is the left
  edge and x=1000 the right edge; y=0 is the top and y=1000 the bottom.
- Aim at the centre of what you want to activate.
- Emit "done" only once the goal is actually visible as achieved.
- Emit "give_up" if the page offers no way to reach the goal."""


@dataclass
class NavResult:
    completed: bool = False
    steps_taken: int = 0
    vl_ms: int = 0
    activated_selectors: list[str] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)


def build_prompt(
    profile,
    goal: str,
    image_b64: str | None,
    ax_text: str,
    viewport: tuple[int, int],
    history: list[str],
) -> tuple[str, str]:
    """One system + one user message. Returns (system, user)."""
    pointer = not profile.keyboard_only
    system = _SYSTEM.format(actions=_ACTIONS_POINTER if pointer else _ACTIONS_KEYBOARD)

    parts = [f"Goal: {goal}"]
    if image_b64 is None:
        parts.append(
            "You cannot see the page. These are the elements it exposes by name, "
            "in focus order:\n" + (ax_text or "(the page exposes no named elements)")
        )
    else:
        parts.append(
            f"The screenshot is {viewport[0]}x{viewport[1]} pixels, but answer "
            f"on the 0-1000 grid."
        )
    if history:
        parts.append("Actions so far:\n" + "\n".join(history))
    parts.append("What is your next action?")
    return system, "\n\n".join(parts)


def parse_action(raw: str) -> dict | None:
    """Tolerant extraction. A malformed reply is a failed step, never a crash."""
    text = (raw or "").strip()
    if "</think>" in text:
        text = text.split("</think>", 1)[-1].strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("action"), str):
        return None
    return payload


def navigate(
    page,
    profile,
    goal,
    success_selector,
    vl_client,
    press_point,
    is_visible,
    max_steps: int = MAX_STEPS,
    errors=None,
    counters=None,
    emit=None,
) -> NavResult:
    """Drive the page toward `goal`. Mutates `counters` / `errors` in place.

    `press_point` and `is_visible` are injected from the runner so the pointer
    mechanics (tremor, dwell, dead-click detection) stay in one place.
    """
    result = NavResult()
    errors = [] if errors is None else errors
    history: list[str] = []
    unverified_done = 0

    for _ in range(max_steps):
        if is_visible(page, success_selector):
            result.completed = True
            break

        image_b64: str | None = None
        ax_text = ""
        size = page.viewport_size or {"width": 0, "height": 0}
        width, height = size["width"], size["height"]
        if profile.ax_tree_only:
            ax_text = focusable_ax_text(page)
        else:
            image_b64, width, height = viewport_screenshot_b64(page)

        if profile.read_delay_ms:
            page.wait_for_timeout(profile.read_delay_ms)

        system, user = build_prompt(
            profile, goal, image_b64, ax_text, (width, height), history
        )
        started = time.perf_counter()
        if emit is not None:
            emit({"stage": "vl_wait", "selector": "nitrogen"})
        try:
            raw = vl_client.complete(system, user, image_b64=image_b64)
        except Exception as exc:
            errors.append(f"vl_client: {exc}")
            result.vl_ms += int((time.perf_counter() - started) * 1000)
            break
        result.vl_ms += int((time.perf_counter() - started) * 1000)

        action = parse_action(raw)
        result.steps_taken += 1
        if action is None:
            errors.append("unparseable model reply")
            result.trace.append({"raw": (raw or "")[:200], "error": "unparseable"})
            history.append("(unreadable action, ignored)")
            continue

        entry = dict(action)
        verb = action.get("action")
        if verb == "done":
            result.completed = is_visible(page, success_selector)
            entry["verified"] = result.completed
            result.trace.append(entry)
            if result.completed:
                break
            # A claim is not an outcome. Say so and keep going: a person who
            # believed they had finished would look again and carry on, and
            # stopping here would throw away the rest of the step budget on a
            # task the model merely thinks it has completed.
            unverified_done += 1
            if unverified_done >= MAX_UNVERIFIED_DONE:
                errors.append(
                    f"claimed done {unverified_done} times without reaching the goal"
                )
                break
            history.append(
                "CORRECTION: the goal is NOT complete. The page does not show it. "
                "Look at the new screenshot and choose a different action. "
                "Do not answer done again."
            )
            continue
        if verb == "give_up":
            errors.append(f"gave up: {action.get('reason', '')}")
            result.trace.append(entry)
            break

        try:
            _apply(page, profile, action, width, height, press_point, entry, result, counters)
        except Exception as exc:
            errors.append(f"{verb}: {exc}")
            entry["error"] = str(exc)
        result.trace.append(entry)
        unverified_done = 0
        history.append(_outcome(action, entry))
        _settle(page)
        if emit is not None:
            emit(
                {
                    "stage": "step",
                    "selector": entry.get("aimed_selector") or verb,
                    "action": verb,
                }
            )
        if entry.get("error") and _identical_dead_count(result.trace, entry) >= MAX_IDENTICAL_DEAD:
            errors.append("repeated dead click; stopping")
            break

    if not result.completed:
        result.completed = is_visible(page, success_selector)
    return result


def _settle(page) -> None:
    """Wait out a navigation the action may have started.

    Everything the next lines do -- the preview screenshot in `emit`, the
    success check, the screenshot the model reasons over -- reads the page, and
    every one of them raises while a new document is still loading.
    """
    try:
        page.wait_for_load_state("domcontentloaded", timeout=SETTLE_TIMEOUT_MS)
    except Exception:
        pass
    page.wait_for_timeout(50)


def _identical_dead_count(trace: list[dict], entry: dict) -> int:
    key = (entry.get("action"), entry.get("aimed_selector"), entry.get("x"), entry.get("y"))
    return sum(
        1
        for row in trace
        if row.get("error")
        and (row.get("action"), row.get("aimed_selector"), row.get("x"), row.get("y")) == key
    )


def _outcome(action: dict, entry: dict) -> str:
    """What the model did and what the page did back.

    Reporting only the attempt hides the single most useful signal there is. A
    person knows immediately when a click achieves nothing; observed live, a
    model told only what it had tried clicked the same dead control 21 times.
    """
    attempt = json.dumps(
        {k: action[k] for k in ("action", "x", "y", "key", "target") if k in action}
    )
    aimed = entry.get("aimed_selector")
    where = f" on {aimed}" if aimed else ""
    if entry.get("error"):
        return (
            f"{attempt} ->{where or ' this'} produced NO change. That element does "
            f"nothing. Choose a different one."
        )
    return f"{attempt} ->{where} worked; the page changed."


def _apply(page, profile, action, width, height, press_point, entry, result, counters) -> None:
    verb = action["action"]

    if verb == "click":
        if profile.keyboard_only:
            raise RuntimeError("no pointer available to this profile")
        x, y = _to_css_px(action, page, width, height)
        aimed = element_at_point(page, x, y)
        entry["aimed_selector"] = aimed
        press_point(page, profile, x, y, counters, aimed)
        if aimed:
            result.activated_selectors.append(aimed)
        return

    if verb == "press":
        key = str(action.get("key", "")).strip()
        if key not in {"Tab", "Shift+Tab", "Enter"}:
            raise RuntimeError(f"unsupported key {key!r}")
        page.keyboard.press(key)
        if counters is not None and key in {"Tab", "Shift+Tab"}:
            counters["keyboard_nav_steps"] += 1
        if key == "Enter":
            entry["focused_selector"] = page.evaluate(
                "() => document.activeElement ? document.activeElement.id : null"
            )
        return

    if verb == "type":
        page.keyboard.type(str(action.get("text", "")))
        return

    if verb == "scroll":
        page.mouse.wheel(0, int(action.get("dy", 0)))
        return

    raise RuntimeError(f"unknown action {verb!r}")


def _to_css_px(action, page, width, height) -> tuple[float, float]:
    """0-1000 grid -> viewport CSS px, which is what page.mouse takes."""
    x, y = _point(action)
    size = page.viewport_size or {"width": width, "height": height}
    return (
        x / COORDINATE_SCALE * size["width"],
        y / COORDINATE_SCALE * size["height"],
    )


def _numbers(value) -> list[float]:
    """Every number in a scalar, a list, or a list of lists, in order."""
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        try:
            return [float(value.strip())]
        except ValueError:
            return []
    if isinstance(value, (list, tuple)):
        return [n for item in value for n in _numbers(item)]
    return []


def _point(action) -> tuple[float, float]:
    """The aim point, however the model chose to spell it.

    Qwen-VL grounding output is not one fixed shape. Observed live: the model
    packed the pair into `x` as `{"x": [64, 431], "y": 431}`. It also emits
    `point`/`coordinate` keys and 4-number boxes. Refusing anything but two
    scalars turns a correctly located target into a crashed step.
    """
    for key in ("point", "point_2d", "coordinate", "coordinates", "position"):
        found = _numbers(action.get(key))
        if len(found) >= 2:
            return found[0], found[1]

    for key in ("bbox", "bbox_2d", "box", "rect"):
        found = _numbers(action.get(key))
        if len(found) >= 4:  # a box: aim at its centre
            return (found[0] + found[2]) / 2, (found[1] + found[3]) / 2
        if len(found) == 2:
            return found[0], found[1]

    xs, ys = _numbers(action.get("x")), _numbers(action.get("y"))
    if len(xs) >= 4:  # a whole box landed in x
        return (xs[0] + xs[2]) / 2, (xs[1] + xs[3]) / 2
    if len(xs) >= 2:  # the pair landed in x
        return xs[0], xs[1]
    if xs and ys:
        return xs[0], ys[0]
    raise RuntimeError(f"no usable coordinates in {action!r}")
