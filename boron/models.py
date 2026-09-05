"""Contract 1 models for Boron. One record per (session, profile)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Changing tremor, dwell or attempt policy changes the telemetry. Stamp which
# emulation produced a number, mirroring hydrogen's scoring_policy.
CAPTURE_POLICY = "boron-v1"

# A VL-driven path is not bit-reproducible (vLLM batching, page variance), so it
# must not claim the scripted stamp. One string covers both the live loop and a
# plan_once replay -- in both the path came from the model.
CAPTURE_POLICY_VL = "boron-vl-v1"
# A human drove a headed browser; all four artifacts are real.
CAPTURE_POLICY_MANUAL = "boron-manual-v1"
# Loose PNGs with no browser: screenshot only, no geometry for Dev 2 to score.
CAPTURE_POLICY_MANUAL_PNG = "boron-manual-png-v1"


class SessionArtifacts(BaseModel):
    model_config = ConfigDict(extra="ignore")

    html_path: str
    screenshot_path: str
    a11y_tree_path: str
    elements_path: str


class Telemetry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    completion_time_ms: int
    task_completed: bool
    total_clicks: int = 0
    dead_clicks: int = 0
    keyboard_nav_steps: int = 0
    missed_clicks: int = 0
    error_count: int = 0
    # Selectors this profile could not operate. The evidence -> profile join key:
    # only the agent knows which element a given profile actually failed on.
    failed_selectors: list[str] = Field(default_factory=list)


class RawSessionArtifacts(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    profile_id: str
    url: str
    artifacts: SessionArtifacts
    telemetry: Telemetry
    capture_policy: str = CAPTURE_POLICY
