"""Deterministic fairness engine. No LLM, no network, no ratio-only scoring."""

from __future__ import annotations

import math
from collections import defaultdict

from hydrogen.constants import (
    FRICTION_COMPONENT_METRICS,
    GAP_REF,
    METRIC_FAMILY,
    METRIC_KIND,
    METRIC_TO_FAMILY,
    METRIC_WEIGHT,
    POOR_BASELINE_RATE,
    RATE_METRICS,
    SCORE_100_METRICS,
    SCORING_POLICY,
    SEVERITY_ORDER,
)
from hydrogen.models import (
    AttributionStatus,
    Disparity,
    EvidenceBundle,
    EvidenceRecord,
    FairnessBreakdown,
    FindingDraft,
    HydrogenReport,
    ScoreStatus,
)


def parse_contract2(contract2_payload: dict) -> EvidenceBundle:
    """Normalize Contract 2 JSON. Shape only; semantic skips happen in score_fairness."""
    return EvidenceBundle.model_validate(contract2_payload)


def score_fairness(bundle: EvidenceBundle) -> FairnessBreakdown:
    skipped: list[str] = []
    valid: list[Disparity] = []
    for row in bundle.disparities:
        label = _skip_label(row)
        if label is not None:
            skipped.append(label)
            continue
        valid.append(row)

    eligible, collapsed = _collapse_families(valid)

    if not eligible:
        return FairnessBreakdown(
            score_status=ScoreStatus.INSUFFICIENT_EVIDENCE,
            scored=False,
            overall_fairness_score=None,
            outcome_equity=None,
            skipped_metrics=skipped,
            collapsed_metrics=collapsed,
            scoring_policy=SCORING_POLICY,
        )

    scored_rows = []
    for index, row in enumerate(eligible):
        item = _row_equity(row)
        item["index"] = index
        scored_rows.append(item)
    bottleneck = min(scored_rows, key=lambda item: (item["weighted"], item["index"]))
    outcome_equity = float(bottleneck["weighted"])
    score = int(round(_clamp(outcome_equity, 0.0, 100.0)))

    return FairnessBreakdown(
        score_status=ScoreStatus.VALID,
        scored=True,
        overall_fairness_score=score,
        outcome_equity=outcome_equity,
        bottleneck_metric=bottleneck["row"].metric,
        bottleneck_group=bottleneck["row"].disadvantaged_group,
        bottleneck_baseline=float(bottleneck["row"].baseline_value),
        bottleneck_constrained=float(bottleneck["row"].constrained_value),
        bottleneck_abs_gap=bottleneck["abs_gap"],
        max_disparity_ratio=float(bottleneck["row"].disparity_ratio),
        baseline_poor=_baseline_poor(bottleneck["row"]),
        skipped_metrics=skipped,
        collapsed_metrics=collapsed,
        scoring_policy=SCORING_POLICY,
    )


def rank_findings(
    bundle: EvidenceBundle,
    breakdown: FairnessBreakdown | None = None,
) -> list[FindingDraft]:
    drafts: list[tuple[int, FindingDraft]] = []
    for index, evidence in enumerate(bundle.evidence):
        drafts.append((index, _finding_from_evidence("tmp", evidence)))

    def sort_key(item: tuple[int, FindingDraft]) -> tuple[int, int, int]:
        index, finding = item
        severity_rank = SEVERITY_ORDER.get(finding.severity.value, 99)
        boosted = 1
        if (
            breakdown is not None
            and breakdown.scored
            and finding.attribution_status is AttributionStatus.RESOLVED
            and breakdown.bottleneck_group in finding.affected_profiles
        ):
            boosted = 0
        return (severity_rank, boosted, index)

    ordered = [finding for _, finding in sorted(drafts, key=sort_key)]
    numbered: list[FindingDraft] = []
    for i, finding in enumerate(ordered, start=1):
        numbered.append(finding.model_copy(update={"id": f"find_{i}"}))
    return numbered


def evaluate(bundle: EvidenceBundle, report_id: str) -> HydrogenReport:
    breakdown = score_fairness(bundle)
    findings = rank_findings(bundle, breakdown)
    return HydrogenReport(
        report_id=report_id,
        target_url=bundle.target_url,
        overall_fairness_score=breakdown.overall_fairness_score,
        score_status=breakdown.score_status,
        scoring_policy=SCORING_POLICY,
        profiles_tested=list(bundle.profiles_tested),
        disparities=list(bundle.disparities),
        findings=findings,
        breakdown=breakdown,
        analyst="hydrogen",
    )


def _skip_label(row: Disparity) -> str | None:
    metric = (row.metric or "").strip()
    if metric not in METRIC_KIND:
        return metric or "<missing>"
    if not _finite(row.baseline_value) or not _finite(row.constrained_value):
        return metric or "<missing>"
    if not _finite(row.disparity_ratio) or float(row.disparity_ratio) <= 0:
        return metric or "<missing>"
    if not (row.disadvantaged_group or "").strip():
        return metric or "<missing>"

    baseline = float(row.baseline_value)
    constrained = float(row.constrained_value)
    if metric in RATE_METRICS:
        if not (0.0 <= baseline <= 1.0 and 0.0 <= constrained <= 1.0):
            return metric
    elif metric in SCORE_100_METRICS:
        if not (0.0 <= baseline <= 100.0 and 0.0 <= constrained <= 100.0):
            return metric
    elif baseline < 0.0 or constrained < 0.0:
        return metric
    return None


def _collapse_families(rows: list[Disparity]) -> tuple[list[Disparity], list[str]]:
    buckets: dict[tuple[str, str], list[tuple[int, Disparity]]] = defaultdict(list)
    for index, row in enumerate(rows):
        family = METRIC_TO_FAMILY[row.metric]
        buckets[(family, row.disadvantaged_group)].append((index, row))

    winners: set[int] = set()
    for (family, _group), items in buckets.items():
        priority = METRIC_FAMILY[family]

        def key(item: tuple[int, Disparity], family_priority: list[str] = priority) -> tuple[int, int]:
            index, row = item
            try:
                rank = family_priority.index(row.metric)
            except ValueError:
                rank = 99
            return (rank, index)

        winner_index, _winner = min(items, key=key)
        winners.add(winner_index)

    groups_with_composite = {
        row.disadvantaged_group
        for row in rows
        if row.metric == "composite_friction_score"
    }
    if groups_with_composite:
        winners = {
            index
            for index in winners
            if not (
                rows[index].metric in FRICTION_COMPONENT_METRICS
                and rows[index].disadvantaged_group in groups_with_composite
            )
        }

    kept: list[Disparity] = []
    collapsed: list[str] = []
    for index, row in enumerate(rows):
        if index in winners:
            kept.append(row)
        else:
            collapsed.append(row.metric)
    return kept, collapsed


def _row_equity(row: Disparity) -> dict:
    baseline = float(row.baseline_value)
    constrained = float(row.constrained_value)
    kind = METRIC_KIND[row.metric]
    if kind == "higher_better":
        abs_gap = max(baseline - constrained, 0.0)
    else:
        abs_gap = max(constrained - baseline, 0.0)

    ref = GAP_REF[row.metric]
    unit_gap = min(abs_gap / ref, 1.0) if ref > 0 else 1.0
    equity = 100.0 * (1.0 - unit_gap)
    weight = METRIC_WEIGHT[row.metric]
    weighted = 100.0 - weight * (100.0 - equity)
    return {
        "row": row,
        "abs_gap": abs_gap,
        "equity": equity,
        "weighted": weighted,
        "index": 0,
    }


def _baseline_poor(row: Disparity) -> bool:
    if row.metric not in RATE_METRICS:
        return False
    baseline = float(row.baseline_value)
    kind = METRIC_KIND[row.metric]
    if kind == "higher_better":
        return baseline < POOR_BASELINE_RATE
    return baseline > (1.0 - POOR_BASELINE_RATE)


def _finding_from_evidence(finding_id: str, evidence: EvidenceRecord) -> FindingDraft:
    profiles = [p for p in (evidence.affected_profiles or []) if p]
    if profiles:
        attribution = AttributionStatus.RESOLVED
    else:
        attribution = AttributionStatus.UNRESOLVED
        profiles = []
    title = f"{evidence.rule_id} on {evidence.element_selector}"
    return FindingDraft(
        id=finding_id,
        title=title,
        severity=evidence.severity,
        affected_profiles=profiles,
        attribution_status=attribution,
        rule_id=evidence.rule_id,
        element_selector=evidence.element_selector,
        diagnosis="",
        remediation_diff="",
    )


def _finite(value: float) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
