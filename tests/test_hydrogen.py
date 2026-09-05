from hydrogen import (
    AttributionStatus,
    ScoreStatus,
    evaluate,
    parse_contract2,
    rank_findings,
    score_fairness,
)


def _payload(**kwargs):
    base = {
        "evidence": [],
        "disparities": [],
        "target_url": "https://example.com/checkout",
        "profiles_tested": ["baseline_default", "motor_impaired"],
    }
    base.update(kwargs)
    return base


def _completion(baseline, constrained, group="motor_impaired", ratio=None):
    if ratio is None:
        ratio = baseline / constrained if constrained else 99.0
    return {
        "metric": "task_completion_rate",
        "baseline_value": baseline,
        "constrained_value": constrained,
        "disparity_ratio": ratio,
        "disadvantaged_group": group,
    }


def test_case_a_not_equal_case_b():
    case_a = parse_contract2(_payload(disparities=[_completion(0.90, 0.45, ratio=2.0)]))
    case_b = parse_contract2(_payload(disparities=[_completion(0.10, 0.05, ratio=2.0)]))
    a = score_fairness(case_a)
    b = score_fairness(case_b)
    assert a.overall_fairness_score == 55
    assert b.overall_fairness_score == 95
    assert a.baseline_poor is False
    assert b.baseline_poor is True
    assert a.max_disparity_ratio == b.max_disparity_ratio == 2.0


def test_checkout_evaluate_unresolved():
    payload = _payload(
        evidence=[
            {
                "element_selector": "button#submit-order",
                "rule_id": "TOUCH_TARGET_TOO_SMALL",
                "severity": "CRITICAL",
                "metric_value": "24x22px",
                "recommended_min": "48x48px",
            }
        ],
        disparities=[_completion(1.0, 0.25, ratio=4.0)],
    )
    report = evaluate(parse_contract2(payload), "rep_9876")
    assert report.overall_fairness_score == 25
    assert report.score_status is ScoreStatus.VALID
    assert report.scoring_policy == "hydrogen-v1"
    assert report.breakdown.bottleneck_abs_gap == 0.75
    assert report.findings[0].id == "find_1"
    assert report.findings[0].attribution_status is AttributionStatus.UNRESOLVED
    assert report.findings[0].affected_profiles == []
    assert report.findings[0].diagnosis == ""
    assert report.findings[0].remediation_diff == ""
    assert "TOUCH_TARGET_TOO_SMALL" in report.findings[0].title
    assert report.analyst == "hydrogen"


def test_empty_disparities_are_not_a_perfect_score():
    report = evaluate(parse_contract2(_payload()), "rep_empty")
    assert report.overall_fairness_score is None
    assert report.score_status is ScoreStatus.INSUFFICIENT_EVIDENCE
    assert report.breakdown.scored is False


def test_out_of_range_rate_is_skipped_not_clamped():
    bundle = parse_contract2(
        _payload(disparities=[_completion(1.2, 0.5, ratio=2.4)])
    )
    breakdown = score_fairness(bundle)
    assert breakdown.score_status is ScoreStatus.INSUFFICIENT_EVIDENCE
    assert "task_completion_rate" in breakdown.skipped_metrics


def test_negative_time_is_skipped():
    bundle = parse_contract2(
        _payload(
            disparities=[
                {
                    "metric": "completion_time_ms",
                    "baseline_value": 1000,
                    "constrained_value": -50,
                    "disparity_ratio": 2.0,
                    "disadvantaged_group": "motor_impaired",
                }
            ]
        )
    )
    breakdown = score_fairness(bundle)
    assert breakdown.scored is False
    assert "completion_time_ms" in breakdown.skipped_metrics


def test_time_aliases_do_not_double_count():
    bundle = parse_contract2(
        _payload(
            disparities=[
                {
                    "metric": "task_completion_time",
                    "baseline_value": 1000,
                    "constrained_value": 16000,
                    "disparity_ratio": 16.0,
                    "disadvantaged_group": "motor_impaired",
                },
                {
                    "metric": "completion_time_ms",
                    "baseline_value": 1000,
                    "constrained_value": 16000,
                    "disparity_ratio": 16.0,
                    "disadvantaged_group": "motor_impaired",
                },
            ]
        )
    )
    breakdown = score_fairness(bundle)
    assert breakdown.scored is True
    assert breakdown.bottleneck_metric == "completion_time_ms"
    assert "task_completion_time" in breakdown.collapsed_metrics


def test_outcome_family_prefers_completion_over_failure():
    bundle = parse_contract2(
        _payload(
            disparities=[
                {
                    "metric": "task_failure_rate",
                    "baseline_value": 0.1,
                    "constrained_value": 0.55,
                    "disparity_ratio": 5.5,
                    "disadvantaged_group": "motor_impaired",
                },
                _completion(0.90, 0.45, ratio=2.0),
            ]
        )
    )
    breakdown = score_fairness(bundle)
    assert breakdown.bottleneck_metric == "task_completion_rate"
    assert "task_failure_rate" in breakdown.collapsed_metrics


def test_does_not_infer_profiles_tested():
    payload = _payload(
        profiles_tested=[],
        disparities=[_completion(0.9, 0.45, ratio=2.0)],
    )
    report = evaluate(parse_contract2(payload), "rep_no_infer")
    assert report.profiles_tested == []


def test_resolved_finding_sorts_before_unresolved_same_severity():
    payload = _payload(
        evidence=[
            {
                "element_selector": "#a",
                "rule_id": "LOW_CONTRAST",
                "severity": "CRITICAL",
                "metric_value": "2.1",
            },
            {
                "element_selector": "#b",
                "rule_id": "TOUCH_TARGET_TOO_SMALL",
                "severity": "CRITICAL",
                "metric_value": "24x22px",
                "affected_profiles": ["motor_impaired"],
            },
        ],
        disparities=[_completion(0.9, 0.45, ratio=2.0)],
    )
    bundle = parse_contract2(payload)
    findings = rank_findings(bundle, score_fairness(bundle))
    assert findings[0].rule_id == "TOUCH_TARGET_TOO_SMALL"
    assert findings[0].attribution_status is AttributionStatus.RESOLVED
    assert findings[1].attribution_status is AttributionStatus.UNRESOLVED


def test_same_abs_gap_same_time_equity_regardless_of_baseline():
    ten_to_twenty = parse_contract2(
        _payload(
            disparities=[
                {
                    "metric": "completion_time_ms",
                    "baseline_value": 10000,
                    "constrained_value": 20000,
                    "disparity_ratio": 2.0,
                    "disadvantaged_group": "motor_impaired",
                }
            ]
        )
    )
    hundred_to_hundred_ten = parse_contract2(
        _payload(
            disparities=[
                {
                    "metric": "completion_time_ms",
                    "baseline_value": 100000,
                    "constrained_value": 110000,
                    "disparity_ratio": 1.1,
                    "disadvantaged_group": "motor_impaired",
                }
            ]
        )
    )
    a = score_fairness(ten_to_twenty)
    b = score_fairness(hundred_to_hundred_ten)
    assert a.bottleneck_abs_gap == 10000
    assert b.bottleneck_abs_gap == 10000
    assert a.outcome_equity == b.outcome_equity
