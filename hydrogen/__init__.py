"""Hydrogen — deterministic fairness engine (Dev 3)."""

from hydrogen.constants import (
    GAP_REF,
    METRIC_FAMILY,
    METRIC_KIND,
    METRIC_WEIGHT,
    POOR_BASELINE_RATE,
    SCORING_POLICY,
)
from hydrogen.engine import evaluate, parse_contract2, rank_findings, score_fairness
from hydrogen.models import (
    AttributionStatus,
    EvidenceBundle,
    FairnessBreakdown,
    FindingDraft,
    HydrogenReport,
    ScoreStatus,
)

__all__ = [
    "GAP_REF",
    "METRIC_FAMILY",
    "METRIC_KIND",
    "METRIC_WEIGHT",
    "POOR_BASELINE_RATE",
    "SCORING_POLICY",
    "AttributionStatus",
    "EvidenceBundle",
    "FairnessBreakdown",
    "FindingDraft",
    "HydrogenReport",
    "ScoreStatus",
    "evaluate",
    "parse_contract2",
    "rank_findings",
    "score_fairness",
]
