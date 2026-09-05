"""Playwright execution harness. Sync API, one profile per session."""

from __future__ import annotations

import random
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from boron.capture import CANONICAL_SELECTOR_SCRIPT, capture_artifacts
from boron.models import RawSessionArtifacts, SessionArtifacts, Telemetry
from boron.profiles import get_profile

DATA_ROOT = "data/sessions"

DEFAULT_SEED = 1729

# Counts DOM changes so a click that achieved nothing can be called dead.
_OBSERVER_SCRIPT = """
window.__boron = { mutations: 0 };
new MutationObserver((records) => { window.__boron.mutations += records.length; })
  .observe(document, { subtree: true, childList: true, attributes: true });
"""


def run_session(
    url: str,
    profile_id: str,
    session_id: str,
    steps: list[str],
    success_selector: str,
    out_root: str = DATA_ROOT,
    seed: int = DEFAULT_SEED,
) -> RawSessionArtifacts:
    """Drive one profile through one task. Writes artifacts, returns Contract 1."""
    profile = get_profile(profile_id)
    out_dir = Path(out_root) / session_id

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={
                "width": profile.viewport_width,
                "height": profile.viewport_height,
            },
            has_touch=profile.has_touch,
        )
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        page.add_init_script(_OBSERVER_SCRIPT)
        page.goto(url, wait_until="load")
        if profile.zoom != 1.0:
            page.evaluate("(z) => { document.body.style.zoom = z; }", profile.zoom)

        started = time.perf_counter()
        counters = _run_steps(page, profile, steps, errors, random.Random(seed))
        completed = _is_visible(page, success_selector)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        artifacts = capture_artifacts(page, out_dir)
        context.close()
        browser.close()

    return RawSessionArtifacts(
        session_id=session_id,
        profile_id=profile.id,
        url=url,
        artifacts=SessionArtifacts(**artifacts),
        telemetry=Telemetry(
            completion_time_ms=elapsed_ms,
            task_completed=completed,
            total_clicks=counters["total_clicks"],
            dead_clicks=counters["dead_clicks"],
            missed_clicks=counters["missed_clicks"],
            keyboard_nav_steps=counters["keyboard_nav_steps"],
            error_count=len(errors),
            failed_selectors=counters["failed_selectors"],
        ),
    )


def _run_steps(page, profile, steps, errors, rng) -> dict[str, int]:
    counters = {
        "total_clicks": 0,
        "dead_clicks": 0,
        "missed_clicks": 0,
        "keyboard_nav_steps": 0,
        "failed_selectors": [],
    }
    for selector in steps:
        try:
            if profile.read_delay_ms:
                page.wait_for_timeout(profile.read_delay_ms)
            _activate(page, profile, selector, counters, rng)
        except Exception as exc:  # a step that cannot be reached is a real failure
            errors.append(f"{selector}: {exc}")
            _record_failure(counters, selector, page)
            break
    return counters


def _record_failure(counters, selector: str, page=None) -> None:
    """Store the elements.json form of the selector so Dev 2's join matches."""
    if page is not None:
        try:
            selector = page.evaluate(CANONICAL_SELECTOR_SCRIPT, selector)
        except Exception:
            pass
    if selector not in counters["failed_selectors"]:
        counters["failed_selectors"].append(selector)


def _activate(page, profile, selector, counters, rng) -> None:
    """Reach the target and act on it. Retries a slip the way a person would."""
    if profile.keyboard_only:
        if profile.ax_tree_only and not _has_accessible_name(page, selector):
            raise RuntimeError("no accessible name exposed")
        before = page.evaluate("() => window.__boron.mutations")
        counters["keyboard_nav_steps"] += _tab_to(page, selector)
        page.keyboard.press("Enter")
        page.wait_for_timeout(50)
        if page.evaluate("() => window.__boron.mutations") == before:
            counters["dead_clicks"] += 1
        return

    for _ in range(profile.max_attempts):
        before = page.evaluate("() => window.__boron.mutations")
        _press(page, profile, selector, rng, counters)
        counters["total_clicks"] += 1
        page.wait_for_timeout(50)
        if page.evaluate("() => window.__boron.mutations") != before:
            return
        counters["dead_clicks"] += 1
        _record_failure(counters, selector, page)
    raise RuntimeError(f"{profile.max_attempts} attempts produced no change")


def _press(page, profile, selector, rng, counters=None) -> None:
    """One pointer press, displaced by the profile tremor."""
    box = page.locator(selector).bounding_box()
    if box is None:
        raise RuntimeError("no bounding box")
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    if profile.tremor_px:
        x += rng.gauss(0.0, profile.tremor_px)
        y += rng.gauss(0.0, profile.tremor_px)
        outside = not (
            box["x"] <= x <= box["x"] + box["width"]
            and box["y"] <= y <= box["y"] + box["height"]
        )
        if outside and counters is not None:
            counters["missed_clicks"] += 1
    page.mouse.move(x, y)
    page.mouse.down()
    if profile.dwell_ms:
        page.wait_for_timeout(profile.dwell_ms)
    page.mouse.up()


def _has_accessible_name(page, selector: str) -> bool:
    """An assistive-tech user can only reach what the a11y tree actually names."""
    return page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel);
            if (!el) return false;
            const name = el.getAttribute('aria-label')
              || el.getAttribute('alt')
              || el.getAttribute('title')
              || (el.textContent || '').trim();
            return Boolean(name) && el.tabIndex >= 0;
        }""",
        selector,
    )


def _tab_to(page, selector, limit: int = 60) -> int:
    """Tab until the target holds focus. Raises if it is never reachable."""
    for pressed in range(1, limit + 1):
        page.keyboard.press("Tab")
        if page.evaluate(
            "(sel) => document.activeElement === document.querySelector(sel)", selector
        ):
            return pressed
    raise RuntimeError(f"not keyboard reachable within {limit} tab stops")


def _is_visible(page, selector: str) -> bool:
    return page.locator(selector).is_visible()


def run_suite(
    url: str,
    profile_ids: list[str],
    session_id_prefix: str,
    steps: list[str],
    success_selector: str,
    runs: int = 1,
    out_root: str = DATA_ROOT,
    seed: int = DEFAULT_SEED,
) -> list[RawSessionArtifacts]:
    """Run every profile through the same task. One record per (profile, run).

    Profiles run sequentially on purpose: completion_time_ms drives the fairness
    score, and concurrent browsers contend for CPU and skew it.
    """
    records = []
    for profile_id in profile_ids:
        for index in range(runs):
            suffix = "" if runs == 1 else f"_{index + 1}"
            records.append(
                run_session(
                    url=url,
                    profile_id=profile_id,
                    session_id=f"{session_id_prefix}_{profile_id}{suffix}",
                    steps=steps,
                    success_selector=success_selector,
                    out_root=out_root,
                    # Each run needs its own seed or repeats are byte-identical.
                    seed=seed + index,
                )
            )
    return records
