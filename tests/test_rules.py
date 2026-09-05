"""Quick offline test runner for deterministic rules and disparity math (< 1 second).

Command:
    pytest tests/test_rules.py
"""
import pytest
from carbon.rules.engine import RuleEngine
from carbon.rules.touch_target import TouchTargetSizeRule
from carbon.rules.spacing import InteractiveSpacingRule
from carbon.rules.contrast import ColorContrastRule
from carbon.disparity.engine import DisparityEngine
from carbon.disparity.metrics import compute_disparity_ratio, compute_friction_score
from carbon.schemas.contracts import RawSessionArtifacts, TelemetryData, ArtifactPaths, Severity


def test_touch_target_rules_offline():
    rule = TouchTargetSizeRule()
    context = {
        "interactive_elements": [
            {"selector": "button#too-small", "bounding_box": {"x": 10, "y": 10, "width": 20, "height": 20}},
            {"selector": "button#medium", "bounding_box": {"x": 50, "y": 10, "width": 32, "height": 32}},
            {"selector": "button#valid", "bounding_box": {"x": 100, "y": 10, "width": 48, "height": 48}},
        ]
    }
    findings = rule.evaluate(context)
    assert len(findings) == 2
    assert findings[0].severity == Severity.CRITICAL
    assert findings[1].severity == Severity.WARNING


def test_interactive_spacing_rules_offline():
    rule = InteractiveSpacingRule(min_spacing_px=8.0)
    context = {
        "interactive_elements": [
            {"selector": "btn1", "bounding_box": {"x": 0, "y": 0, "width": 30, "height": 30}},
            {"selector": "btn2", "bounding_box": {"x": 34, "y": 0, "width": 30, "height": 30}},  # 4px gap
        ]
    }
    findings = rule.evaluate(context)
    assert len(findings) == 1
    assert findings[0].rule_id == "INTERACTIVE_SPACING_TOO_TIGHT"


def test_contrast_rules_offline():
    rule = ColorContrastRule()
    context = {
        "contrast_elements": [
            {"selector": ".failing-text", "fg_color": "#888888", "bg_color": "#ffffff"},
            {"selector": ".passing-text", "fg_color": "#111111", "bg_color": "#ffffff"},
        ]
    }
    findings = rule.evaluate(context)
    assert len(findings) == 1
    assert findings[0].rule_id == "COLOR_CONTRAST_FAIL_AA"


def test_disparity_engine_offline():
    engine = DisparityEngine()
    baseline = RawSessionArtifacts(
        session_id="s1",
        profile_id="baseline_default",
        url="https://test.com",
        artifacts=ArtifactPaths(),
        telemetry=TelemetryData(completion_time_ms=2000, task_completed=True, dead_clicks=0),
    )
    constrained = RawSessionArtifacts(
        session_id="s2",
        profile_id="motor_impaired",
        url="https://test.com",
        artifacts=ArtifactPaths(),
        telemetry=TelemetryData(completion_time_ms=8000, task_completed=False, dead_clicks=4),
    )

    disparities = engine.analyze_sessions(baseline, [constrained])
    assert len(disparities) >= 3
    rates = {d.metric: d.disparity_ratio for d in disparities}
    assert rates["completion_time_ms"] == 4.0
    assert rates["task_completion_rate"] >= 4.0
