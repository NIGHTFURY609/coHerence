"""hydrogen-v1 scoring policy. Changing these requires a new SCORING_POLICY string."""

from __future__ import annotations

SCORING_POLICY = "hydrogen-v1"

# Policy: default-user rate below this (higher_better) is "poor", not a diagnosis.
POOR_BASELINE_RATE = 0.5

SEVERITY_ORDER = {
    "CRITICAL": 0,
    "WARNING": 1,
    "INFO": 2,
}

# higher_better | lower_better
METRIC_KIND: dict[str, str] = {
    "task_completion_rate": "higher_better",
    "task_failure_rate": "lower_better",
    "abandonment_rate": "lower_better",
    "task_completion_time": "lower_better",
    "completion_time_ms": "lower_better",
    "error_rate": "lower_better",
    "error_count": "lower_better",
    "dead_clicks": "lower_better",
    "total_clicks": "lower_better",
    "keyboard_nav_steps": "lower_better",
    "composite_friction_score": "lower_better",
}

# Policy: abs_gap that maps to equity 0. Not a universal constant.
GAP_REF: dict[str, float] = {
    "task_completion_rate": 1.0,
    "task_failure_rate": 1.0,
    "abandonment_rate": 1.0,
    "task_completion_time": 30000.0,
    "completion_time_ms": 30000.0,
    "error_rate": 1.0,
    "error_count": 10.0,
    "dead_clicks": 10.0,
    "total_clicks": 20.0,
    "keyboard_nav_steps": 20.0,
    "composite_friction_score": 50.0,
}

# How hard this row's equity hits the final min(). Separate from GAP_REF.
METRIC_WEIGHT: dict[str, float] = {
    "task_completion_rate": 1.00,
    "task_failure_rate": 1.00,
    "abandonment_rate": 1.00,
    "task_completion_time": 0.50,
    "completion_time_ms": 0.50,
    "error_rate": 0.50,
    "error_count": 0.50,
    "dead_clicks": 0.25,
    "total_clicks": 0.25,
    "keyboard_nav_steps": 0.25,
    # Composite of interaction friction (clicks / tabs / tremor), not time or errors.
    # Table said "(Composite)" not a number; 0.50 matches the time/error band, not completion.
    "composite_friction_score": 0.50,
}

# First present after validation wins, per (family, disadvantaged_group).
METRIC_FAMILY: dict[str, list[str]] = {
    "outcome": [
        "task_completion_rate",
        "task_failure_rate",
        "abandonment_rate",
    ],
    "time": [
        "completion_time_ms",
        "task_completion_time",
    ],
    "errors": [
        "error_rate",
        "error_count",
    ],
    "dead_clicks": ["dead_clicks"],
    "total_clicks": ["total_clicks"],
    "keyboard": ["keyboard_nav_steps"],
    "friction": ["composite_friction_score"],
}

RATE_METRICS = frozenset(
    {
        "task_completion_rate",
        "task_failure_rate",
        "abandonment_rate",
        "error_rate",
    }
)

# 0–100 normalized scores (not 0–1 rates).
SCORE_100_METRICS = frozenset({"composite_friction_score"})

# Dropped for a group when composite_friction_score is present (avoid double-count).
FRICTION_COMPONENT_METRICS = frozenset(
    {
        "dead_clicks",
        "total_clicks",
        "keyboard_nav_steps",
    }
)

METRIC_TO_FAMILY: dict[str, str] = {
    metric: family
    for family, metrics in METRIC_FAMILY.items()
    for metric in metrics
}
