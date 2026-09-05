import json
from pathlib import Path

import pytest

from boron import get_profile, run_session, run_suite

FIXTURE_URL = (Path(__file__).parent / "fixtures" / "test_page.html").resolve().as_uri()
STEPS = ["#fake-button", "#submit-order"]
SUCCESS = "#order-confirmed"

pytest.importorskip("playwright", reason="run: playwright install chromium")


def _run(profile_id, tmp_path, seed=1729):
    return run_session(
        url=FIXTURE_URL,
        profile_id=profile_id,
        session_id=f"t_{profile_id}",
        steps=STEPS,
        success_selector=SUCCESS,
        out_root=str(tmp_path),
        seed=seed,
    )


@pytest.fixture(scope="module")
def baseline(tmp_path_factory):
    return _run("baseline_default", tmp_path_factory.mktemp("baseline"))


def test_baseline_completes_the_task(baseline):
    assert baseline.telemetry.task_completed is True
    assert baseline.telemetry.total_clicks == len(STEPS)
    assert baseline.telemetry.dead_clicks == 0
    assert baseline.telemetry.error_count == 0
    assert baseline.telemetry.completion_time_ms > 0


def test_all_four_artifacts_are_written(baseline):
    for path in baseline.artifacts.model_dump().values():
        assert Path(path).stat().st_size > 0


def test_a11y_tree_is_a_real_cdp_dump(baseline):
    tree = json.loads(Path(baseline.artifacts.a11y_tree_path).read_text())
    assert tree["nodes"], "Accessibility.getFullAXTree returned nothing"


def test_elements_carry_contract2_geometry(baseline):
    elements = json.loads(Path(baseline.artifacts.elements_path).read_text(encoding="utf-8"))
    submit = next(e for e in elements if e["element_selector"].endswith("#submit-order"))
    assert set(submit["bounding_box"]) == {"x", "y", "width", "height"}
    assert (submit["bounding_box"]["width"], submit["bounding_box"]["height"]) == (24, 22)


def test_keyboard_only_cannot_reach_a_clickable_div(tmp_path):
    record = _run("keyboard_only", tmp_path)
    assert record.telemetry.task_completed is False
    assert record.telemetry.error_count >= 1


def test_zoom_scales_geometry_for_low_vision(tmp_path):
    record = _run("low_vision", tmp_path)
    elements = json.loads(Path(record.artifacts.elements_path).read_text(encoding="utf-8"))
    submit = next(e for e in elements if e["element_selector"].endswith("#submit-order"))
    zoom = get_profile("low_vision").zoom
    assert submit["bounding_box"]["width"] == 24 * zoom


def test_tremor_is_applied_and_costs_clicks(tmp_path):
    record = _run("motor_impaired", tmp_path, seed=2024)
    assert record.telemetry.dead_clicks > 0
    assert record.telemetry.total_clicks > len(STEPS)


def test_run_suite_mints_unique_sessions_per_profile(tmp_path):
    records = run_suite(
        url=FIXTURE_URL,
        profile_ids=["baseline_default", "keyboard_only"],
        session_id_prefix="sess_suite",
        steps=STEPS,
        success_selector=SUCCESS,
        out_root=str(tmp_path),
    )
    assert [r.profile_id for r in records] == ["baseline_default", "keyboard_only"]
    assert len({r.session_id for r in records}) == 2
    assert len({r.artifacts.html_path for r in records}) == 2


def test_run_suite_repeats_are_not_identical(tmp_path):
    records = run_suite(
        url=FIXTURE_URL,
        profile_ids=["motor_impaired"],
        session_id_prefix="sess_repeat",
        steps=STEPS,
        success_selector=SUCCESS,
        runs=3,
        out_root=str(tmp_path),
        seed=2023,
    )
    assert len(records) == 3
    assert len({r.session_id for r in records}) == 3
    # Different seed per run, or N>1 would just repeat one measurement.
    assert len({r.telemetry.total_clicks for r in records}) > 1


def test_capture_policy_is_stamped(baseline):
    assert baseline.capture_policy == "boron-v1"


def test_screen_reader_cannot_reach_an_unnamed_div(tmp_path):
    """ax_tree_only fails a target with no accessible name, before tabbing."""
    record = _run("screen_reader_users", tmp_path)
    assert record.telemetry.task_completed is False
    assert record.telemetry.failed_selectors == ["div#fake-button"]


def test_failed_selectors_use_the_elements_json_form(tmp_path):
    """The join key only works if both sides spell the selector identically."""
    record = _run("keyboard_only", tmp_path)
    elements = json.loads(Path(record.artifacts.elements_path).read_text(encoding="utf-8"))
    known = {e["element_selector"] for e in elements}
    assert record.telemetry.failed_selectors
    assert set(record.telemetry.failed_selectors) <= known


def test_read_delay_slows_a_profile_down(tmp_path):
    fast = _run("baseline_default", tmp_path)
    slow = _run("esl_users", tmp_path)
    assert slow.telemetry.completion_time_ms > fast.telemetry.completion_time_ms
