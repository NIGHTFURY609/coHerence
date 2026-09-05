"""Core Data Contracts adhering to dev.md specification.

Contracts:
- Contract 1: RawSessionArtifacts (Dev 1 -> Dev 2)
- Contract 2: EvidenceRecord & DisparityMatrix (Dev 2 -> Dev 3)
"""
from __future__ import annotations
import math
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class Severity(str, Enum):
    """Rule severity classifications."""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class BoundingBox(BaseModel):
    """Bounding box coordinates and dimensions in pixels."""
    model_config = ConfigDict(extra="ignore")

    x: float = Field(..., description="X coordinate of top-left corner in pixels")
    y: float = Field(..., description="Y coordinate of top-left corner in pixels")
    width: float = Field(..., description="Width in pixels")
    height: float = Field(..., description="Height in pixels")

    @property
    def area(self) -> float:
        """Area of the bounding box in square pixels."""
        return max(0.0, self.width) * max(0.0, self.height)

    @property
    def center(self) -> tuple[float, float]:
        """Center coordinate (cx, cy)."""
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)

    def overlaps(self, other: BoundingBox) -> bool:
        """Check if this bounding box intersects/overlaps with another."""
        return not (
            self.x + self.width <= other.x
            or other.x + other.width <= self.x
            or self.y + self.height <= other.y
            or other.y + other.height <= self.y
        )

    def edge_distance(self, other: BoundingBox) -> float:
        """Calculate the minimum edge-to-edge distance to another bounding box."""
        if self.overlaps(other):
            return 0.0

        dx = 0.0
        if self.x + self.width < other.x:
            dx = other.x - (self.x + self.width)
        elif other.x + other.width < self.x:
            dx = self.x - (other.x + other.width)

        dy = 0.0
        if self.y + self.height < other.y:
            dy = other.y - (self.y + self.height)
        elif other.y + other.height < self.y:
            dy = self.y - (other.y + other.height)

        return math.hypot(dx, dy)


# ==============================================================================
# Contract 1: Dev 1 -> Dev 2
# ==============================================================================

class ArtifactPaths(BaseModel):
    """Paths to artifacts generated during browser session."""
    model_config = ConfigDict(extra="ignore")

    html_path: Optional[str] = Field(None, description="Path to captured DOM HTML snapshot")
    screenshot_path: Optional[str] = Field(None, description="Path to viewport or full-page screenshot PNG")
    a11y_tree_path: Optional[str] = Field(None, description="Path to dumped Chromium accessibility tree JSON")


class TelemetryData(BaseModel):
    """Interaction and friction telemetry for a user profile run."""
    model_config = ConfigDict(extra="ignore")

    completion_time_ms: int = Field(..., description="Task duration in milliseconds")
    task_completed: bool = Field(..., description="Whether user completed target workflow")
    total_clicks: int = Field(default=0, description="Total click attempts")
    dead_clicks: int = Field(default=0, description="Clicks on non-interactive regions or missed hits")
    missed_clicks: int = Field(default=0, description="Clicks near targets that failed target hit")
    keyboard_nav_steps: int = Field(default=0, description="Number of Tab/Enter/Arrow navigation events")
    errors: int = Field(default=0, description="Count of interaction or validation errors encountered")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom metrics")


class RawSessionArtifacts(BaseModel):
    """Contract 1: Raw browser execution payload from Dev 1 to Dev 2."""
    model_config = ConfigDict(extra="ignore")

    session_id: str = Field(..., description="Unique test session identifier")
    profile_id: str = Field(..., description="Tested synthetic profile e.g. motor_impaired_keyboard_only")
    url: str = Field(..., description="Target webpage URL evaluated")
    artifacts: ArtifactPaths = Field(..., description="File paths to recorded artifacts")
    telemetry: TelemetryData = Field(..., description="Telemetry captured during session run")


# ==============================================================================
# Contract 2: Dev 2 -> Dev 3
# ==============================================================================

class EvidenceItem(BaseModel):
    """Individual rule violation or multi-modal observation."""
    model_config = ConfigDict(extra="ignore")

    element_selector: str = Field(..., description="CSS selector or unique path to element")
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding box if element has visual placement")
    rule_id: str = Field(..., description="Identified rule code e.g. TOUCH_TARGET_TOO_SMALL")
    severity: Severity = Field(..., description="Severity rating: CRITICAL, WARNING, INFO")
    metric_value: str = Field(..., description="Observed metric value e.g. '24x22px' or '2.8:1'")
    recommended_min: Optional[str] = Field(None, description="Standard or recommended baseline e.g. '48x48px'")
    message: Optional[str] = Field(None, description="Human-readable explanation of the finding")
    category: Optional[str] = Field(None, description="Category: a11y, vision, text, spacing, etc.")
    profile_id: Optional[str] = Field(None, description="Synthetic user profile ID that encountered or triggered this evidence")
    affected_profiles: List[str] = Field(default_factory=list, description="Target constrained profile IDs affected by this violation (Join Key for Hydrogen)")


class DisparityItem(BaseModel):
    """Quantitative delta between baseline and constrained profile."""
    model_config = ConfigDict(extra="ignore")

    metric: str = Field(..., description="Evaluated metric e.g. task_completion_rate, completion_time_ms")
    baseline_value: float = Field(..., description="Value recorded for unconstrained baseline profile")
    constrained_value: float = Field(..., description="Value recorded for constrained user profile")
    disparity_ratio: float = Field(..., description="Disparity ratio: constrained / baseline or inverse")
    disadvantaged_group: str = Field(..., description="Profile ID suffering disproportionate friction")
    delta_absolute: Optional[float] = Field(None, description="Absolute difference between values")
    statistical_significance: Optional[float] = Field(None, description="Confidence or significance level (0.0 - 1.0)")
    severity: Optional[Severity] = Field(Severity.WARNING, description="Assigned severity of disparity")
    interpretation: Optional[str] = Field(None, description="Brief contextual summary of disparity impact")


class EvidenceRecord(BaseModel):
    """Contract 2: Structured evidence and disparity payload from Dev 2 to Dev 3."""
    model_config = ConfigDict(extra="ignore")

    evidence: List[EvidenceItem] = Field(default_factory=list, description="All rule violations found")
    disparities: List[DisparityItem] = Field(default_factory=list, description="Calculated group disparities")
    target_url: str = Field(default="", description="Target webpage URL evaluated")
    profiles_tested: List[str] = Field(default_factory=list, description="List of profile IDs tested across sessions")
    session_ids: Optional[List[str]] = Field(default_factory=list, description="IDs of sessions analyzed")
    analyzed_at: Optional[str] = Field(None, description="ISO timestamp when analysis completed")
