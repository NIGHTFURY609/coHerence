"""Canonical smoke inputs. Tests may use the packaged report; `modal run` uses the bundle."""

from __future__ import annotations

from hydrogen.models import (
    AttributionStatus,
    EvidenceBundle,
    FairnessBreakdown,
    FindingDraft,
    HydrogenReport,
    ScoreStatus,
    Severity,
)


def example_bundle() -> EvidenceBundle:
    """Contract 2 in. Hydrogen.evaluate owns the score; Helium only reads the report."""
    return EvidenceBundle.model_validate(
        {
            "target_url": "https://example.com/checkout",
            "profiles_tested": ["baseline_default", "motor_impaired"],
            "disparities": [
                {
                    "metric": "task_completion_rate",
                    "baseline_value": 0.90,
                    "constrained_value": 0.62,
                    "disparity_ratio": 0.90 / 0.62,
                    "disadvantaged_group": "motor_impaired",
                }
            ],
            "evidence": [
                {
                    "element_selector": "#submit-help",
                    "rule_id": "TEXT_AMBIGUOUS_INSTRUCTION",
                    "severity": "WARNING",
                    "metric_value": "ambiguous",
                },
                {
                    "element_selector": "button#submit-order",
                    "rule_id": "VISION_LOW_PROMINENCE",
                    "severity": "CRITICAL",
                    "metric_value": "low visual prominence",
                },
                {
                    "element_selector": "body",
                    "rule_id": "A11Y_KEYBOARD_STEPS",
                    "severity": "WARNING",
                    "metric_value": "14",
                },
                {
                    "element_selector": "",
                    "rule_id": "INTERACTION_EXTRA_ERRORS",
                    "severity": "CRITICAL",
                    "metric_value": "3 additional errors",
                    "affected_profiles": ["motor_impaired"],
                },
            ],
        }
    )


def example_report() -> HydrogenReport:
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
