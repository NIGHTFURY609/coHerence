"""Disparity analytics engine calculating demographic and constraint disparities."""
from __future__ import annotations
from typing import Dict, List, Any, Optional, Sequence
from collections import defaultdict

from carbon.schemas.contracts import (
    RawSessionArtifacts,
    DisparityItem,
    Severity,
    EvidenceItem,
)
from carbon.disparity.metrics import (
    compute_disparity_ratio,
    compute_friction_score,
    compute_statistical_significance,
)


class DisparityEngine:
    """Disparity Engine computing quantitative deltas between baseline and constrained user profiles."""

    def __init__(
        self,
        critical_disparity_threshold: float = 2.5,
        warning_disparity_threshold: float = 1.5,
    ):
        self.critical_disparity_threshold = critical_disparity_threshold
        self.warning_disparity_threshold = warning_disparity_threshold

    def analyze_sessions(
        self,
        baseline_session: RawSessionArtifacts,
        constrained_sessions: Sequence[RawSessionArtifacts],
        evidence: Optional[List[EvidenceItem]] = None,
    ) -> List[DisparityItem]:
        """Compute disparities between a baseline session and one or more constrained sessions.
        
        Args:
            baseline_session: RawSessionArtifacts from baseline unconstrained run.
            constrained_sessions: Collection of RawSessionArtifacts from constrained runs.
            evidence: Optional list of EvidenceItems to enrich disparity interpretations.
            
        Returns:
            List of DisparityItem records meeting Contract 2 specification.
        """
        disparities: List[DisparityItem] = []

        base_telemetry = baseline_session.telemetry
        base_completion = 1.0 if base_telemetry.task_completed else 0.0
        base_time = float(base_telemetry.completion_time_ms)
        base_dead_clicks = float(base_telemetry.dead_clicks)
        base_keyboard = float(base_telemetry.keyboard_nav_steps)
        base_friction = compute_friction_score(base_telemetry)

        # Look for relevant evidence rules to contextualize disparities
        rule_ids = {item.rule_id for item in (evidence or [])}

        for session in constrained_sessions:
            group = session.profile_id
            tel = session.telemetry

            c_completion = 1.0 if tel.task_completed else 0.0
            c_time = float(tel.completion_time_ms)
            c_dead_clicks = float(tel.dead_clicks)
            c_keyboard = float(tel.keyboard_nav_steps)
            c_friction = compute_friction_score(tel)

            # 1. Task Completion Rate
            comp_ratio = compute_disparity_ratio(base_completion, c_completion, higher_is_better=True)
            if comp_ratio >= self.warning_disparity_threshold or (base_completion > c_completion):
                interp = (
                    f"{group} experienced a {comp_ratio:.1f}x lower completion rate compared to baseline."
                )
                disparities.append(
                    DisparityItem(
                        metric="task_completion_rate",
                        baseline_value=round(base_completion, 2),
                        constrained_value=round(c_completion, 2),
                        disparity_ratio=comp_ratio,
                        disadvantaged_group=group,
                        delta_absolute=round(c_completion - base_completion, 2),
                        statistical_significance=compute_statistical_significance(comp_ratio),
                        severity=Severity.CRITICAL if comp_ratio >= self.critical_disparity_threshold else Severity.WARNING,
                        interpretation=interp,
                    )
                )

            # 2. Completion Time
            if base_time > 0:
                time_ratio = compute_disparity_ratio(base_time, c_time, higher_is_better=False)
                if time_ratio >= self.warning_disparity_threshold:
                    interp = (
                        f"{group} required {time_ratio:.1f}x more time ({int(c_time)}ms vs {int(base_time)}ms) to navigate."
                    )
                    disparities.append(
                        DisparityItem(
                            metric="completion_time_ms",
                            baseline_value=base_time,
                            constrained_value=c_time,
                            disparity_ratio=time_ratio,
                            disadvantaged_group=group,
                            delta_absolute=round(c_time - base_time, 1),
                            statistical_significance=compute_statistical_significance(time_ratio),
                            severity=Severity.CRITICAL if time_ratio >= self.critical_disparity_threshold else Severity.WARNING,
                            interpretation=interp,
                        )
                    )

            # 3. Dead Clicks / Misclicks
            click_ratio = compute_disparity_ratio(max(1.0, base_dead_clicks), max(1.0, c_dead_clicks), higher_is_better=False)
            if c_dead_clicks > base_dead_clicks and click_ratio >= self.warning_disparity_threshold:
                bias_hint = ""
                if "TOUCH_TARGET_TOO_SMALL" in rule_ids:
                    bias_hint = " Potential contributing factor: detected undersized touch targets (< 48x48px) on page."
                elif "INTERACTIVE_SPACING_TOO_TIGHT" in rule_ids:
                    bias_hint = " Potential contributing factor: detected tight spacing between adjacent interactive controls."

                interp = (
                    f"{group} suffered {c_dead_clicks} dead clicks vs {base_dead_clicks} baseline ({click_ratio:.1f}x disparity).{bias_hint}"
                )
                disparities.append(
                    DisparityItem(
                        metric="dead_clicks",
                        baseline_value=base_dead_clicks,
                        constrained_value=c_dead_clicks,
                        disparity_ratio=click_ratio,
                        disadvantaged_group=group,
                        delta_absolute=round(c_dead_clicks - base_dead_clicks, 1),
                        statistical_significance=compute_statistical_significance(click_ratio),
                        severity=Severity.CRITICAL if click_ratio >= self.critical_disparity_threshold else Severity.WARNING,
                        interpretation=interp,
                    )
                )

            # 4. Keyboard Navigation Overhead
            # Standard mouse baseline users typically execute 0 or very few keyboard steps.
            # Constrained keyboard users taking significant navigation steps represent high friction.
            if c_keyboard > base_keyboard:
                effective_base = max(1.0, base_keyboard)
                kb_ratio = compute_disparity_ratio(effective_base, c_keyboard, higher_is_better=False)
                if kb_ratio >= self.warning_disparity_threshold or (c_keyboard - base_keyboard >= 8):
                    interp = (
                        f"{group} required {int(c_keyboard)} keyboard navigation steps vs {int(base_keyboard)} baseline "
                        f"({kb_ratio:.1f}x navigation overhead)."
                    )
                    disparities.append(
                        DisparityItem(
                            metric="keyboard_nav_steps",
                            baseline_value=base_keyboard,
                            constrained_value=c_keyboard,
                            disparity_ratio=kb_ratio,
                            disadvantaged_group=group,
                            delta_absolute=round(c_keyboard - base_keyboard, 1),
                            statistical_significance=compute_statistical_significance(kb_ratio),
                            severity=Severity.CRITICAL if kb_ratio >= 4.0 or c_keyboard >= 20 else Severity.WARNING,
                            interpretation=interp,
                        )
                    )

            # 5. Composite Friction Score
            friction_ratio = compute_disparity_ratio(max(5.0, base_friction), max(5.0, c_friction), higher_is_better=False)
            if friction_ratio >= self.warning_disparity_threshold or (c_friction - base_friction) >= 20.0:
                interp = (
                    f"{group} encountered an aggregate friction score of {c_friction} vs baseline {base_friction}."
                )
                disparities.append(
                    DisparityItem(
                        metric="composite_friction_score",
                        baseline_value=base_friction,
                        constrained_value=c_friction,
                        disparity_ratio=friction_ratio,
                        disadvantaged_group=group,
                        delta_absolute=round(c_friction - base_friction, 1),
                        statistical_significance=compute_statistical_significance(friction_ratio),
                        severity=Severity.CRITICAL if friction_ratio >= self.critical_disparity_threshold else Severity.WARNING,
                        interpretation=interp,
                    )
                )

        return disparities

    def compare_groups(
        self,
        sessions: Sequence[RawSessionArtifacts],
        baseline_profile_id: str = "baseline_default",
        evidence: Optional[List[EvidenceItem]] = None,
    ) -> List[DisparityItem]:
        """Group sessions by profile ID, locate baseline, and calculate disparities."""
        grouped: Dict[str, List[RawSessionArtifacts]] = defaultdict(list)
        for s in sessions:
            grouped[s.profile_id].append(s)

        baseline_runs = grouped.get(baseline_profile_id)
        if not baseline_runs:
            # Fallback to first session if baseline_default not found
            if not sessions:
                return []
            baseline_run = sessions[0]
        else:
            baseline_run = baseline_runs[0]

        constrained_runs = [s for s in sessions if s.profile_id != baseline_run.profile_id]
        return self.analyze_sessions(baseline_run, constrained_runs, evidence)
