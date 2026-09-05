"""Mathematical and statistical functions for calculating accessibility and usability disparities."""
from __future__ import annotations
import math
from typing import Dict, Any, Optional

from carbon.schemas.contracts import TelemetryData


def compute_disparity_ratio(
    baseline_val: float,
    constrained_val: float,
    higher_is_better: bool = False,
    epsilon: float = 0.01,
) -> float:
    """Calculate disparity ratio between baseline and constrained user profiles.
    
    Args:
        baseline_val: Metric value recorded for baseline profile.
        constrained_val: Metric value recorded for constrained profile.
        higher_is_better: True for metrics like completion rate, False for time, errors, clicks.
        epsilon: Small constant to avoid zero division.
        
    Returns:
        Disparity ratio rounded to 2 decimal places.
        A ratio > 1.0 means constrained group experiences disproportionate disadvantage.
    """
    if higher_is_better:
        # e.g., Task Completion: Baseline 1.0, Constrained 0.25 -> Ratio = 1.0 / 0.25 = 4.0
        safe_constrained = max(epsilon, constrained_val)
        ratio = max(0.0, baseline_val) / safe_constrained
    else:
        # e.g., Time: Constrained 14200ms, Baseline 3500ms -> Ratio = 14200 / 3500 = 4.06
        safe_baseline = max(epsilon, baseline_val)
        ratio = max(0.0, constrained_val) / safe_baseline

    return round(float(ratio), 2)


def compute_friction_score(
    telemetry: TelemetryData,
    baseline_expected_time_ms: int = 5000,
) -> float:
    """Calculate a normalized Friction Score (0.0 to 100.0) from session telemetry.
    
    Components:
    - Task Failure penalty (up to 40 pts)
    - Excess Time penalty (up to 25 pts)
    - Dead Clicks / Missed Clicks penalty (up to 20 pts)
    - Navigation Complexity penalty (up to 15 pts)
    """
    # 1. Completion penalty
    completion_penalty = 0.0 if telemetry.task_completed else 40.0

    # 2. Time penalty: ratio of actual time to standard baseline
    time_ratio = telemetry.completion_time_ms / max(1000, baseline_expected_time_ms)
    time_penalty = min(25.0, max(0.0, (time_ratio - 1.0) * 8.0))

    # 3. Dead / Missed click penalty
    click_friction = (telemetry.dead_clicks * 4.0) + (telemetry.missed_clicks * 3.0)
    click_penalty = min(20.0, float(click_friction))

    # 4. Keyboard / Navigation error penalty
    nav_penalty = min(15.0, (telemetry.keyboard_nav_steps * 0.5) + (telemetry.errors * 5.0))

    total = completion_penalty + time_penalty + click_penalty + nav_penalty
    return round(float(min(100.0, max(0.0, total))), 2)


def compute_confidence_heuristic(
    ratio: float,
    sample_size: int = 1,
) -> float:
    """Estimate an algorithmic confidence heuristic for disparity significance (0.0 - 1.0).
    
    Heuristic combines effect size (magnitude of ratio delta) with available run sample size.
    Note: For large sample populations, replace with rigorous student t-test or Mann-Whitney U test.
    """
    if ratio <= 1.1:
        return 0.1

    # Logarithmic scaling based on magnitude of disparity
    effect_size = math.log10(ratio) if ratio > 1.0 else 0.0
    confidence = min(0.99, (effect_size * 0.6) + min(0.3, sample_size * 0.05))
    return round(float(max(0.1, confidence)), 2)


# Backwards compatibility alias
compute_statistical_significance = compute_confidence_heuristic

