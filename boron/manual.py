"""Human-in-the-loop capture. You drive; Boron records each page state.

For flows automation cannot reach on its own -- logins, captchas, payment walls
-- or when you simply want the real thing audited rather than a simulation.

Two entry points, and the difference matters downstream:

  run_manual        headed browser, all four artifacts, carbon can score it
  from_screenshots  loose PNGs, no browser, no geometry -- vision only

Neither simulates a constraint. A record here is what actually happened to a
real person, so it drops straight in as the baseline a constrained profile is
compared against.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from boron.capture import (
    A11Y_TREE_FILENAME,
    DOM_FILENAME,
    ELEMENTS_FILENAME,
    SCREENSHOT_FILENAME,
    _posix,
    _write_json,
    capture_artifacts,
)
from boron.models import (
    CAPTURE_POLICY_MANUAL,
    CAPTURE_POLICY_MANUAL_PNG,
    RawSessionArtifacts,
    SessionArtifacts,
    Telemetry,
)

DATA_ROOT = "data/sessions"

POLL_MS = 200

# F8 captures the current page, Escape ends the session. Re-injected on every
# navigation, so it survives the user clicking through to a new page.
_HOTKEY_SCRIPT = """
window.__boronCapture = 0;
window.__boronDone = 0;
window.__boronClicks = 0;
document.addEventListener('click', () => { window.__boronClicks += 1; }, true);
document.addEventListener('keydown', (e) => {
  if (e.key === 'F8') { window.__boronCapture += 1; e.preventDefault(); }
  if (e.key === 'Escape') { window.__boronDone = 1; }
}, true);
"""

_POLL_SCRIPT = """() => {
  const out = {
    capture: window.__boronCapture || 0,
    done: window.__boronDone || 0,
    clicks: window.__boronClicks || 0,
  };
  window.__boronCapture = 0;
  return out;
}"""


def run_manual(
    url: str,
    session_id: str,
    profile_id: str = "baseline_default",
    out_root: str = DATA_ROOT,
    max_minutes: int = 30,
) -> list[RawSessionArtifacts]:
    """Open a visible browser, capture a state per F8, stop on Escape.

    One Contract 1 record per captured state, session ids `{session_id}_{n}`.
    Only genuinely observable telemetry is filled in: dead_clicks and
    missed_clicks stay 0 because neither is measurable for a real person.
    """
    from boron.runner import _driver

    records: list[RawSessionArtifacts] = []
    deadline = time.perf_counter() + max_minutes * 60

    with _driver() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        page.add_init_script(_HOTKEY_SCRIPT)
        page.goto(url, wait_until="load")
        print(f"Drive the browser. F8 captures this page, Escape finishes. ({url})")

        started = time.perf_counter()
        clicks = 0
        on_page = 0
        while time.perf_counter() < deadline:
            try:
                state = page.evaluate(_POLL_SCRIPT)
            except Exception:  # mid-navigation; the init script comes back
                page.wait_for_timeout(POLL_MS)
                continue
            # The counter lives in the page, so it restarts at 0 on every
            # navigation. Accumulate deltas instead of tracking a maximum, or a
            # five-click page followed by a three-click page reports five.
            seen = int(state["clicks"])
            if seen < on_page:
                on_page = 0
            clicks += seen - on_page
            on_page = seen
            for _ in range(int(state["capture"])):
                step = len(records) + 1
                step_id = f"{session_id}_{step}"
                artifacts = capture_artifacts(page, Path(out_root) / step_id)
                records.append(
                    _record(
                        session_id=step_id,
                        profile_id=profile_id,
                        url=page.url,
                        artifacts=artifacts,
                        policy=CAPTURE_POLICY_MANUAL,
                        telemetry=Telemetry(
                            completion_time_ms=int(
                                (time.perf_counter() - started) * 1000
                            ),
                            task_completed=False,
                            total_clicks=clicks,
                            error_count=len(errors),
                        ),
                    )
                )
                print(f"captured {step_id}  ({page.url})")
            if state["done"]:
                break
            page.wait_for_timeout(POLL_MS)

        context.close()
        browser.close()

    # Reaching Escape means the human finished the flow; the last state is the
    # outcome, so only it carries task_completed.
    if records:
        records[-1] = records[-1].model_copy(
            update={
                "telemetry": records[-1].telemetry.model_copy(
                    update={"task_completed": True}
                )
            }
        )
    return records


def from_screenshots(
    paths: list[str],
    url: str,
    session_id: str,
    profile_id: str = "baseline_default",
    out_root: str = DATA_ROOT,
) -> list[RawSessionArtifacts]:
    """Wrap images captured outside this machine as Contract 1 records.

    Vision only. There is no DOM, no computed style and no a11y tree behind a
    PNG, so carbon's geometry, contrast and accessibility rules will find
    nothing here. The `boron-manual-png-v1` stamp is what stops that reading as
    a clean audit downstream.
    """
    records = []
    for index, source in enumerate(paths, start=1):
        src = Path(source)
        if not src.is_file():
            raise FileNotFoundError(f"no such screenshot: {source}")
        step_id = f"{session_id}_{index}"
        out_dir = Path(out_root) / step_id
        out_dir.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(src, out_dir / SCREENSHOT_FILENAME)
        (out_dir / DOM_FILENAME).write_text("", encoding="utf-8")
        _write_json(out_dir / A11Y_TREE_FILENAME, {"nodes": []})
        _write_json(out_dir / ELEMENTS_FILENAME, [])

        records.append(
            _record(
                session_id=step_id,
                profile_id=profile_id,
                url=url,
                artifacts={
                    "html_path": _posix(out_dir / DOM_FILENAME),
                    "screenshot_path": _posix(out_dir / SCREENSHOT_FILENAME),
                    "a11y_tree_path": _posix(out_dir / A11Y_TREE_FILENAME),
                    "elements_path": _posix(out_dir / ELEMENTS_FILENAME),
                },
                policy=CAPTURE_POLICY_MANUAL_PNG,
                telemetry=Telemetry(completion_time_ms=0, task_completed=False),
            )
        )
    return records


_DESCRIBE_SYSTEM = (
    "You describe what a web page shows. Report only what is visible: the "
    "controls, their labels, and what the page appears to be for. Do not judge "
    "the design and do not suggest changes."
)


def describe_pages(records: list[RawSessionArtifacts], vl_client) -> dict[str, str]:
    """One VL call per captured state, keyed by session_id.

    A capture-time annotation, not a finding. Boron does not score (that is
    hydrogen) and does not diagnose or remediate (that is helium).
    """
    import base64

    out: dict[str, str] = {}
    for record in records:
        png = Path(record.artifacts.screenshot_path).read_bytes()
        out[record.session_id] = vl_client.complete(
            _DESCRIBE_SYSTEM,
            "Describe this page and list the controls a user could act on.",
            image_b64=base64.b64encode(png).decode("ascii"),
        )
    return out


def _record(session_id, profile_id, url, artifacts, policy, telemetry):
    return RawSessionArtifacts(
        session_id=session_id,
        profile_id=profile_id,
        url=url,
        artifacts=SessionArtifacts(**artifacts),
        telemetry=telemetry,
        capture_policy=policy,
    )
