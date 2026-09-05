"""Handoff models for Hydrogen. Contract 2 in, report out (pre-LLM)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class ScoreStatus(str, Enum):
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class AttributionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="ignore")

    x: float
    y: float
    width: float
    height: float


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    element_selector: str
    bounding_box: BoundingBox | None = None
    rule_id: str
    severity: Severity
    metric_value: str
    recommended_min: str | None = None
    affected_profiles: list[str] | None = None


class Disparity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    metric: str
    baseline_value: float
    constrained_value: float
    disparity_ratio: float
    disadvantaged_group: str


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    evidence: list[EvidenceRecord] = Field(default_factory=list)
    disparities: list[Disparity] = Field(default_factory=list)
    target_url: str = ""
    profiles_tested: list[str] = Field(default_factory=list)


class FairnessBreakdown(BaseModel):
    score_status: ScoreStatus
    scored: bool
    overall_fairness_score: int | None
    outcome_equity: float | None
    bottleneck_metric: str = ""
    bottleneck_group: str = ""
    bottleneck_baseline: float | None = None
    bottleneck_constrained: float | None = None
    bottleneck_abs_gap: float = 0.0
    max_disparity_ratio: float = 0.0
    baseline_poor: bool = False
    skipped_metrics: list[str] = Field(default_factory=list)
    collapsed_metrics: list[str] = Field(default_factory=list)
    scoring_policy: str


class FindingDraft(BaseModel):
    id: str
    title: str
    severity: Severity
    affected_profiles: list[str]
    attribution_status: AttributionStatus
    rule_id: str
    element_selector: str
    diagnosis: str = ""
    remediation_diff: str = ""


class HydrogenReport(BaseModel):
    report_id: str
    target_url: str
    overall_fairness_score: int | None
    score_status: ScoreStatus
    scoring_policy: str
    profiles_tested: list[str]
    disparities: list[Disparity]
    findings: list[FindingDraft]
    breakdown: FairnessBreakdown
    diagnosis: str = ""
    remediation: str = ""
    analyst: str = "hydrogen"
