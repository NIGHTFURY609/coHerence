"""Constraint profiles. Deterministic input-channel limits, not personas.

Each profile is a bundle of driver parameters. Nothing here role-plays a person:
`docs/idea-brief.md` rejects persona modelling, so an id names the constraint
bundle it configures, not a character to imitate. Ids match the group names in
carbon's RULE_AFFECTED_PROFILES_MAP so the two vocabularies line up.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProfileSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    viewport_width: int = 1280
    viewport_height: int = 800
    zoom: float = 1.0
    keyboard_only: bool = False
    tremor_px: float = 0.0
    dwell_ms: int = 0
    has_touch: bool = False
    ax_tree_only: bool = False
    read_delay_ms: int = 0
    max_attempts: int = 5


PROFILES: dict[str, ProfileSpec] = {
    "baseline_default": ProfileSpec(
        id="baseline_default",
        label="Default user",
    ),
    "motor_impaired": ProfileSpec(
        id="motor_impaired",
        label="Reduced pointing precision",
        tremor_px=12.0,
        dwell_ms=400,
    ),
    "tremor_users": ProfileSpec(
        id="tremor_users",
        label="High-amplitude tremor",
        tremor_px=20.0,
        dwell_ms=250,
    ),
    "touch_screen_users": ProfileSpec(
        id="touch_screen_users",
        label="Coarse pointer, no hover",
        has_touch=True,
        tremor_px=8.0,
    ),
    "keyboard_only": ProfileSpec(
        id="keyboard_only",
        label="Keyboard-only navigation",
        keyboard_only=True,
    ),
    "screen_reader_users": ProfileSpec(
        id="screen_reader_users",
        label="Accessible-name navigation only",
        keyboard_only=True,
        ax_tree_only=True,
    ),
    "low_vision": ProfileSpec(
        id="low_vision",
        label="200% magnification",
        zoom=2.0,
    ),
    "elderly": ProfileSpec(
        id="elderly",
        label="Reduced acuity with slower pointing",
        zoom=1.5,
        tremor_px=8.0,
        dwell_ms=300,
        read_delay_ms=600,
    ),
    "cognitive_impaired": ProfileSpec(
        id="cognitive_impaired",
        label="Longer reading time, low retry tolerance",
        read_delay_ms=1200,
        max_attempts=2,
    ),
    "adhd_users": ProfileSpec(
        id="adhd_users",
        label="Short attention budget",
        read_delay_ms=300,
        max_attempts=2,
    ),
    "esl_users": ProfileSpec(
        id="esl_users",
        label="Slower reading of complex text",
        read_delay_ms=900,
    ),
}

# DEV.md Contract 1 uses one compound id. Canonical ids stay short-form.
PROFILE_ALIASES: dict[str, str] = {
    "motor_impaired_keyboard_only": "motor_impaired",
}


def get_profile(profile_id: str) -> ProfileSpec:
    return PROFILES[PROFILE_ALIASES.get(profile_id, profile_id)]


def list_profiles() -> list[str]:
    return list(PROFILES)
