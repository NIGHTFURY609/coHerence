"""Edge cases from hydrogen/sub-arch.md that the happy-path tests do not cover."""

from hydrogen import (
    AttributionStatus,
    EvidenceBundle,
    ScoreStatus,
    evaluate,
    parse_contract2,
    rank_findings,
    score_fairness,
)
from hydrogen.models import Disparity


def _payload(**kwargs):
    base = {
        "evidence": [],
        "disparities": [],
        "target_url": "",
        "profiles_tested": [],
    }
    base.update(kwargs)
    return base


def _row(metric, baseline, constrained, group="motor_impaired", ratio=2.0):
    return {
        "metric": metric,
        "baseline_value": baseline,
        "constrained_value": constrained,
        "disparity_ratio": ratio,
        "disadvantaged_group": group,
    }


def test_ratio_does_not_drive_the_score():
    same_values_small_ratio = parse_contract2(
        _payload(disparities=[_row("task_completion_rate", 0.90, 0.45, ratio=2.0)])
    )
    same_values_huge_ratio = parse_contract2(
        _payload(disparities=[_row("task_completion_rate", 0.90, 0.45, ratio=99.0)])
    )
    a = score_fairness(same_values_small_ratio)
    b = score_fairness(same_values_huge_ratio)
    assert a.overall_fairness_score == b.overall_fairness_score == 55
    assert a.max_disparity_ratio == 2.0
    assert b.max_disparity_ratio == 99.0


def test_constrained_better_does_not_bonus_the_score():
    bundle = parse_contract2(
        _payload(disparities=[_row("task_completion_rate", 0.50, 0.90, ratio=0.5)])
    )
    breakdown = score_fairness(bundle)
    assert breakdown.bottleneck_abs_gap == 0.0
    assert breakdown.overall_fairness_score == 100


def test_worst_group_min_not_average():
    bundle = parse_contract2(
        _payload(
            disparities=[
                _row("task_completion_rate", 0.90, 0.45, group="motor_impaired"),
                _row("task_completion_rate", 0.90, 0.85, group="low_vision"),
            ]
        )
    )
    breakdown = score_fairness(bundle)
    assert breakdown.overall_fairness_score == 55
    assert breakdown.bottleneck_group == "motor_impaired"
    assert breakdown.collapsed_metrics == []


def test_family_collapse_is_per_group_not_global():
    bundle = parse_contract2(
        _payload(
            disparities=[
                _row("task_completion_rate", 0.90, 0.45, group="motor_impaired"),
                _row("task_failure_rate", 0.10, 0.15, group="low_vision"),
            ]
        )
    )
    breakdown = score_fairness(bundle)
    assert breakdown.collapsed_metrics == []
    assert breakdown.bottleneck_group == "motor_impaired"
    assert breakdown.overall_fairness_score == 55


def test_error_rate_preferred_over_error_count():
    bundle = parse_contract2(
        _payload(
            disparities=[
                _row("error_count", 1, 6),
                _row("error_rate", 0.10, 0.60),
            ]
        )
    )
    breakdown = score_fairness(bundle)
    assert breakdown.bottleneck_metric == "error_rate"
    assert "error_count" in breakdown.collapsed_metrics


def test_clicks_and_keyboard_are_not_aliases():
    bundle = parse_contract2(
        _payload(
            disparities=[
                _row("dead_clicks", 0, 2),
                _row("total_clicks", 8, 10),
                _row("keyboard_nav_steps", 8, 10),
            ]
        )
    )
    breakdown = score_fairness(bundle)
    assert breakdown.collapsed_metrics == []
    assert breakdown.scored is True


def test_keyboard_max_gap_cannot_tank_as_hard_as_failed_task():
    keyboard = score_fairness(
        parse_contract2(_payload(disparities=[_row("keyboard_nav_steps", 0, 20)]))
    )
    failed_task = score_fairness(
        parse_contract2(_payload(disparities=[_row("task_completion_rate", 1.0, 0.25)]))
    )
    # 20 extra steps → equity 0 × weight 0.25 → 75
    assert keyboard.overall_fairness_score == 75
    assert failed_task.overall_fairness_score == 25
    assert keyboard.overall_fairness_score > failed_task.overall_fairness_score


def test_gap_above_ref_caps_at_equity_zero_then_weight():
    breakdown = score_fairness(
        parse_contract2(_payload(disparities=[_row("dead_clicks", 0, 50)]))
    )
    # abs_gap 50 / GAP_REF 10 → cap 1 → equity 0 → weight 0.25 → 75
    assert breakdown.bottleneck_abs_gap == 50
    assert breakdown.overall_fairness_score == 75


def test_unknown_metric_skipped():
    breakdown = score_fairness(
        parse_contract2(
            _payload(
                disparities=[
                    _row("flesch_kincaid", 0.2, 0.8),
                    _row("task_completion_rate", 0.90, 0.45),
                ]
            )
        )
    )
    assert "flesch_kincaid" in breakdown.skipped_metrics
    assert breakdown.overall_fairness_score == 55


def test_non_positive_ratio_skipped():
    breakdown = score_fairness(
        parse_contract2(_payload(disparities=[_row("task_completion_rate", 0.9, 0.45, ratio=0)]))
    )
    assert breakdown.score_status is ScoreStatus.INSUFFICIENT_EVIDENCE
    assert "task_completion_rate" in breakdown.skipped_metrics


def test_empty_group_skipped():
    breakdown = score_fairness(
        parse_contract2(_payload(disparities=[_row("task_completion_rate", 0.9, 0.45, group="  ")]))
    )
    assert breakdown.scored is False


def test_failure_rate_baseline_poor_is_policy():
    poor = score_fairness(
        parse_contract2(_payload(disparities=[_row("task_failure_rate", 0.90, 0.95)]))
    )
    ok = score_fairness(
        parse_contract2(_payload(disparities=[_row("task_failure_rate", 0.10, 0.20)]))
    )
    assert poor.baseline_poor is True
    assert ok.baseline_poor is False


def test_time_never_sets_baseline_poor_in_v1():
    breakdown = score_fairness(
        parse_contract2(_payload(disparities=[_row("completion_time_ms", 120000, 150000)]))
    )
    assert breakdown.baseline_poor is False
    assert breakdown.scored is True


def test_skipped_rows_still_passed_through_on_report():
    payload = _payload(
        disparities=[
            _row("flesch_kincaid", 1, 2),
            _row("task_completion_rate", 0.9, 0.45),
        ]
    )
    report = evaluate(parse_contract2(payload), "rep_pass")
    assert len(report.disparities) == 2
    assert report.disparities[0].metric == "flesch_kincaid"


def test_rank_without_breakdown_is_severity_then_original_order():
    bundle = parse_contract2(
        _payload(
            evidence=[
                {
                    "element_selector": "#info",
                    "rule_id": "INFO_RULE",
                    "severity": "INFO",
                    "metric_value": "x",
                },
                {
                    "element_selector": "#crit-a",
                    "rule_id": "CRIT_A",
                    "severity": "CRITICAL",
                    "metric_value": "x",
                },
                {
                    "element_selector": "#crit-b",
                    "rule_id": "CRIT_B",
                    "severity": "CRITICAL",
                    "metric_value": "x",
                },
            ]
        )
    )
    findings = rank_findings(bundle, breakdown=None)
    assert [f.rule_id for f in findings] == ["CRIT_A", "CRIT_B", "INFO_RULE"]


def test_empty_affected_profiles_list_is_unresolved():
    bundle = parse_contract2(
        _payload(
            evidence=[
                {
                    "element_selector": "#x",
                    "rule_id": "R",
                    "severity": "WARNING",
                    "metric_value": "1",
                    "affected_profiles": [],
                }
            ]
        )
    )
    findings = rank_findings(bundle)
    assert findings[0].attribution_status is AttributionStatus.UNRESOLVED
    assert findings[0].affected_profiles == []


def test_parse_ignores_unknown_contract_keys():
    bundle = parse_contract2(
        {
            "evidence": [],
            "disparities": [_row("task_completion_rate", 1.0, 1.0, ratio=1.0)],
            "extra_dev2_field": {"ok": True},
        }
    )
    assert bundle.profiles_tested == []
    assert bundle.target_url == ""


def test_v1_never_emits_partial():
    empty = score_fairness(parse_contract2(_payload()))
    ok = score_fairness(
        parse_contract2(_payload(disparities=[_row("task_completion_rate", 1.0, 1.0, ratio=1.0)]))
    )
    assert empty.score_status is not ScoreStatus.PARTIAL
    assert ok.score_status is not ScoreStatus.PARTIAL


def test_nan_and_inf_are_skipped():
    nan_row = Disparity(
        metric="task_completion_rate",
        baseline_value=float("nan"),
        constrained_value=0.5,
        disparity_ratio=2.0,
        disadvantaged_group="motor_impaired",
    )
    inf_row = Disparity(
        metric="completion_time_ms",
        baseline_value=1000,
        constrained_value=float("inf"),
        disparity_ratio=2.0,
        disadvantaged_group="motor_impaired",
    )
    breakdown = score_fairness(EvidenceBundle(disparities=[nan_row, inf_row]))
    assert breakdown.scored is False
    assert "task_completion_rate" in breakdown.skipped_metrics
    assert "completion_time_ms" in breakdown.skipped_metrics


def test_weighted_keyboard_loses_to_completion_gap():
    bundle = parse_contract2(
        _payload(
            disparities=[
                _row("task_completion_rate", 1.0, 1.0, ratio=1.0),
                _row("keyboard_nav_steps", 0, 20),
            ]
        )
    )
    breakdown = score_fairness(bundle)
    assert breakdown.bottleneck_metric == "keyboard_nav_steps"
    assert breakdown.overall_fairness_score == 75


def test_findings_never_copy_disadvantaged_group():
    payload = _payload(
        evidence=[
            {
                "element_selector": "#x",
                "rule_id": "R",
                "severity": "CRITICAL",
                "metric_value": "1",
            }
        ],
        disparities=[_row("task_completion_rate", 0.9, 0.45)],
    )
    report = evaluate(parse_contract2(payload), "rep_no_join")
    assert report.findings[0].affected_profiles == []
    assert "motor_impaired" not in report.findings[0].affected_profiles


def test_composite_friction_gap_ref_50_weight_50():
    # baseline 20, constrained 70 → abs_gap 50 / GAP_REF 50 → equity 0 → weight 0.50 → 50
    breakdown = score_fairness(
        parse_contract2(
            _payload(disparities=[_row("composite_friction_score", 20.0, 70.0, ratio=3.5)])
        )
    )
    assert breakdown.scored is True
    assert breakdown.bottleneck_metric == "composite_friction_score"
    assert breakdown.bottleneck_abs_gap == 50.0
    assert breakdown.overall_fairness_score == 50


def test_composite_friction_replaces_click_and_keyboard_rows():
    breakdown = score_fairness(
        parse_contract2(
            _payload(
                disparities=[
                    _row("composite_friction_score", 10.0, 20.0),
                    _row("dead_clicks", 0, 10),
                    _row("total_clicks", 8, 28),
                    _row("keyboard_nav_steps", 4, 24),
                    _row("error_count", 1, 2),
                ]
            )
        )
    )
    assert breakdown.bottleneck_metric == "composite_friction_score"
    assert "dead_clicks" in breakdown.collapsed_metrics
    assert "total_clicks" in breakdown.collapsed_metrics
    assert "keyboard_nav_steps" in breakdown.collapsed_metrics
    assert "error_count" not in breakdown.collapsed_metrics


def test_composite_friction_out_of_range_skipped():
    breakdown = score_fairness(
        parse_contract2(_payload(disparities=[_row("composite_friction_score", 10.0, 140.0)]))
    )
    assert breakdown.scored is False
    assert "composite_friction_score" in breakdown.skipped_metrics
