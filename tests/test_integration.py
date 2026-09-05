"""Dev 1 -> Dev 2 -> Dev 3 seam. Boron artifacts through carbon rules into hydrogen."""

from pathlib import Path

import pytest

import boron
import hydrogen

carbon = pytest.importorskip("carbon", reason="Dev 2 module or its deps missing")

FIXTURE_URL = (Path(__file__).parent / "fixtures" / "test_page.html").resolve().as_uri()
STEPS = ["#fake-button", "#submit-order"]
SUCCESS = "#order-confirmed"


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    records = boron.run_suite(
        url=FIXTURE_URL,
        profile_ids=boron.list_profiles(),
        session_id_prefix="itest",
        steps=STEPS,
        success_selector=SUCCESS,
        out_root=str(tmp_path_factory.mktemp("sessions")),
    )
    by_id = {r.profile_id: r for r in records}

    evidence = carbon.RuleEngine().evaluate_context(
        boron.page_context(by_id["baseline_default"])
    )
    sessions = {
        p: carbon.RawSessionArtifacts.model_validate(boron.to_contract1(r))
        for p, r in by_id.items()
    }
    disparities = carbon.DisparityEngine().analyze_sessions(
        sessions.pop("baseline_default"), list(sessions.values()), evidence
    )
    contract2 = carbon.EvidenceRecord(
        evidence=evidence,
        disparities=disparities,
        target_url=FIXTURE_URL,
        profiles_tested=list(by_id),
    )
    report = hydrogen.evaluate(
        hydrogen.parse_contract2(contract2.model_dump(mode="json")), "itest_1"
    )
    return evidence, disparities, report


def test_carbon_accepts_boron_contract1(pipeline):
    _, disparities, _ = pipeline
    assert disparities, "carbon derived no disparities from boron telemetry"


def test_geometry_reaches_the_touch_target_rule(pipeline):
    """Without boron's elements.json carbon has no source of layout geometry."""
    evidence, _, _ = pipeline
    hits = [e for e in evidence if e.rule_id == "TOUCH_TARGET_TOO_SMALL"]
    assert any(e.element_selector.endswith("#submit-order") for e in hits)
    assert any(e.metric_value == "24x22px" for e in hits)


def test_effective_background_reaches_the_contrast_rule(pipeline):
    """Element background is transparent by default; contrast needs the painted one."""
    evidence, _, _ = pipeline
    assert any(e.rule_id == "COLOR_CONTRAST_FAIL_AA" for e in evidence)


def test_keyboard_trap_shows_up_as_both_defect_and_outcome(pipeline):
    evidence, disparities, _ = pipeline
    assert any(e.rule_id == "INACCESSIBLE_CLICKABLE_ELEMENT" for e in evidence)
    failed = [
        d for d in disparities
        if d.metric == "task_completion_rate" and d.disadvantaged_group == "keyboard_only"
    ]
    assert failed and failed[0].constrained_value == 0.0


def test_hydrogen_scores_the_run(pipeline):
    _, _, report = pipeline
    assert report.score_status is hydrogen.ScoreStatus.VALID
    assert report.breakdown.bottleneck_group == "keyboard_only"
    assert report.profiles_tested == boron.list_profiles()


def test_page_defects_are_not_attributed_to_the_baseline(pipeline):
    """Evaluating rules once on the baseline page must not tag the control group."""
    _, _, report = pipeline
    for finding in report.findings:
        assert "baseline_default" not in finding.affected_profiles


def test_evidence_is_not_duplicated_per_profile(pipeline):
    evidence, _, _ = pipeline
    keys = [(e.element_selector, e.rule_id) for e in evidence]
    assert len(keys) == len(set(keys))


def test_carbon_reads_geometry_without_being_handed_it(tmp_path):
    """The obvious call must work: beryllium will not know to pass kwargs."""
    record = boron.run_session(
        url=FIXTURE_URL, profile_id="baseline_default", session_id="nokwargs",
        steps=STEPS, success_selector=SUCCESS, out_root=str(tmp_path),
    )
    session = carbon.RawSessionArtifacts.model_validate(boron.to_contract1(record))
    assert session.artifacts.elements_path, "elements_path was dropped by carbon"
    evidence = carbon.RuleEngine().evaluate_session_artifacts(session)
    hits = [e for e in evidence if e.rule_id == "TOUCH_TARGET_TOO_SMALL"]
    assert any(e.metric_value == "24x22px" for e in hits)


def test_observed_failure_sharpens_attribution_without_overreaching(tmp_path):
    """A failure to click an element attributes interaction rules, not perception ones."""
    records = boron.run_suite(
        url=FIXTURE_URL, profile_ids=["baseline_default", "keyboard_only"],
        session_id_prefix="attr", steps=STEPS, success_selector=SUCCESS,
        out_root=str(tmp_path),
    )
    sessions = [carbon.RawSessionArtifacts.model_validate(boron.to_contract1(r)) for r in records]
    engine = carbon.RuleEngine()
    evidence = engine.attribute_from_failures(
        engine.evaluate_session_artifacts(sessions[0]), sessions
    )
    by_rule = {e.rule_id: e.affected_profiles for e in evidence
               if e.element_selector == "div#fake-button"}
    assert "keyboard_only" in by_rule["INACCESSIBLE_CLICKABLE_ELEMENT"]
    # The keyboard user's failure says nothing about the element's contrast.
    assert by_rule.get("COLOR_CONTRAST_FAIL_AAA") == ["low_vision"]
