import json
from pathlib import Path

import pytest

from hydrogen import METRIC_FAMILY, METRIC_KIND

from boron import RawSessionArtifacts, Telemetry, get_profile, list_profiles

FIXTURES = Path(__file__).parent / "fixtures"

EXPECTED_PROFILES = {
    "baseline_default",
    "motor_impaired",
    "tremor_users",
    "touch_screen_users",
    "keyboard_only",
    "screen_reader_users",
    "low_vision",
    "elderly",
    "cognitive_impaired",
    "adhd_users",
    "esl_users",
}

# Consumed by carbon, never emitted as a Disparity.metric, so hydrogen never
# sees these names and they cannot land in skipped_metrics.
NOT_SCORED = {"task_completed", "missed_clicks", "failed_selectors"}


def _scored_telemetry_fields():
    return set(Telemetry.model_fields) - NOT_SCORED


def _session(name):
    payload = json.loads((FIXTURES / f"session_{name}.json").read_text())
    return RawSessionArtifacts.model_validate(payload)


def test_contract1_pair_round_trips():
    baseline = _session("baseline_default")
    constrained = _session("motor_impaired")
    assert baseline.telemetry.task_completed is True
    assert constrained.telemetry.task_completed is False
    assert constrained.telemetry.dead_clicks == 3
    assert constrained.artifacts.html_path.endswith("/dom.html")


def test_session_ids_are_unique_per_profile():
    baseline = _session("baseline_default")
    constrained = _session("motor_impaired")
    assert baseline.session_id != constrained.session_id
    paths = {baseline.artifacts.html_path, constrained.artifacts.html_path}
    assert len(paths) == 2, "profiles would overwrite each other's artifacts"


def test_artifact_paths_are_posix():
    for name in ("baseline_default", "motor_impaired"):
        artifacts = _session(name).artifacts
        for path in (artifacts.html_path, artifacts.screenshot_path, artifacts.a11y_tree_path):
            assert "\\" not in path


def test_telemetry_fields_are_scoreable_by_hydrogen():
    unknown = _scored_telemetry_fields() - set(METRIC_KIND)
    assert unknown == set(), f"would land in skipped_metrics: {sorted(unknown)}"


def test_unscored_fields_really_are_unscored():
    """The allowlist must stay honest: none of these may be a hydrogen metric."""
    assert NOT_SCORED.isdisjoint(METRIC_KIND)


def test_telemetry_families_do_not_collide():
    fields = _scored_telemetry_fields()
    for family, metrics in METRIC_FAMILY.items():
        overlap = fields & set(metrics)
        assert len(overlap) <= 1, f"{family} would collapse: {sorted(overlap)}"


def test_profile_ids_are_short_form():
    assert set(list_profiles()) == EXPECTED_PROFILES


def test_roster_covers_carbon_group_vocabulary():
    """Every group carbon can name must be a profile boron actually runs."""
    carbon_engine = pytest.importorskip("carbon.rules.engine")
    groups = {g for v in carbon_engine.RULE_AFFECTED_PROFILES_MAP.values() for g in v}
    assert groups <= set(list_profiles())


def test_legacy_long_profile_id_resolves():
    assert get_profile("motor_impaired_keyboard_only").id == "motor_impaired"


def test_baseline_profile_is_unconstrained():
    baseline = get_profile("baseline_default")
    assert baseline.zoom == 1.0
    assert baseline.keyboard_only is False
    assert baseline.tremor_px == 0.0
    assert baseline.dwell_ms == 0


def test_all_profiles_share_the_baseline_viewport():
    sizes = {(get_profile(p).viewport_width, get_profile(p).viewport_height) for p in list_profiles()}
    assert len(sizes) == 1, "a per-profile viewport confounds disparity with layout"


def test_fixture_page_is_offline_and_still_defective():
    html = (FIXTURES / "test_page.html").read_text()
    assert "http://" not in html
    assert "https://" not in html
    for marker in ('id="submit-order"', 'id="fake-button"', 'class="wide"', "#a8a8a8"):
        assert marker in html
