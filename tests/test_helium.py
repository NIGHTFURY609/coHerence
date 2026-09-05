from helium import REPORT_MODEL, diagnose
from helium.client import MockLLMClient
from helium.prompt import SYSTEM_PROMPT, user_prompt
from hydrogen.models import (
    AttributionStatus,
    FairnessBreakdown,
    FindingDraft,
    HydrogenReport,
    ScoreStatus,
    Severity,
)


def _report() -> HydrogenReport:
    return HydrogenReport(
        report_id="rep_example",
        target_url="https://example.com/checkout",
        overall_fairness_score=72,
        score_status=ScoreStatus.VALID,
        scoring_policy="hydrogen-v1",
        profiles_tested=["baseline_default", "motor_impaired"],
        disparities=[],
        findings=[
            FindingDraft(
                id="find_1",
                title="instruction is ambiguous",
                severity=Severity.WARNING,
                affected_profiles=[],
                attribution_status=AttributionStatus.UNRESOLVED,
                rule_id="TEXT_AMBIGUOUS_INSTRUCTION",
                element_selector="#submit-help",
            ),
            FindingDraft(
                id="find_2",
                title="primary action has low visual prominence",
                severity=Severity.CRITICAL,
                affected_profiles=[],
                attribution_status=AttributionStatus.UNRESOLVED,
                rule_id="VISION_LOW_PROMINENCE",
                element_selector="button#submit-order",
            ),
            FindingDraft(
                id="find_3",
                title="keyboard navigation requires 14 steps",
                severity=Severity.WARNING,
                affected_profiles=[],
                attribution_status=AttributionStatus.UNRESOLVED,
                rule_id="A11Y_KEYBOARD_STEPS",
                element_selector="body",
            ),
            FindingDraft(
                id="find_4",
                title="constrained profile made 3 additional errors",
                severity=Severity.CRITICAL,
                affected_profiles=["motor_impaired"],
                attribution_status=AttributionStatus.UNRESOLVED,
                rule_id="INTERACTION_EXTRA_ERRORS",
                element_selector="",
            ),
        ],
        breakdown=FairnessBreakdown(
            score_status=ScoreStatus.VALID,
            scored=True,
            overall_fairness_score=72,
            outcome_equity=72.0,
            bottleneck_metric="task_completion_rate",
            bottleneck_group="motor_impaired",
            bottleneck_abs_gap=0.28,
            scoring_policy="hydrogen-v1",
        ),
        diagnosis="",
        remediation="",
        analyst="hydrogen",
    )


def test_report_model_is_qwen_27b_text():
    assert "27B" in REPORT_MODEL
    assert "VL" not in REPORT_MODEL


def test_diagnose_fills_synthesis_and_locks_score():
    src = _report()
    out = diagnose(src, MockLLMClient())
    assert out.analyst == "helium"
    assert "lower completion" in out.diagnosis.lower() or "substantially lower" in out.diagnosis
    assert "prominence" in out.remediation.lower() or "instruction" in out.remediation.lower()
    assert out.overall_fairness_score == 72
    assert out.score_status is ScoreStatus.VALID
    assert out.scoring_policy == "hydrogen-v1"
    assert out.breakdown.bottleneck_abs_gap == 0.28
    assert out.findings[0].diagnosis == ""
    assert src.diagnosis == ""
    assert src.analyst == "hydrogen"


def test_prompt_has_gap_and_findings_not_personas():
    client = MockLLMClient()
    diagnose(_report(), client)
    assert "28" in client.last_user
    assert "ambiguous" in client.last_user.lower()
    assert "prominence" in client.last_user.lower()
    assert "14" in client.last_user
    assert "3 additional" in client.last_user.lower() or "INTERACTION_EXTRA_ERRORS" in client.last_user
    assert "UNRESOLVED" in client.last_user
    assert "woman" not in SYSTEM_PROMPT.lower()
    assert "prioritize" in SYSTEM_PROMPT.lower()
    assert "do not mention every row" in SYSTEM_PROMPT.lower()


def test_user_prompt_builder_sets_completion_gap_pp():
    text = user_prompt(_report())
    assert '"completion_gap_pp": 28' in text


def test_bad_json_raises():
    class Bad:
        def complete(self, system: str, user: str) -> str:
            return "not json"

    try:
        diagnose(_report(), Bad())
    except ValueError as exc:
        assert "JSON" in str(exc)
    else:
        raise AssertionError("expected ValueError")
