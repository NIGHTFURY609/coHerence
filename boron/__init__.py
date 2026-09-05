"""Boron - browser ingestion and synthetic user agent engine (Dev 1)."""

from boron.handoff import load_elements, page_context, rule_context, to_contract1
from boron.manual import describe_pages, from_screenshots, run_manual
from boron.models import (
    CAPTURE_POLICY,
    CAPTURE_POLICY_MANUAL,
    CAPTURE_POLICY_MANUAL_PNG,
    CAPTURE_POLICY_VL,
    RawSessionArtifacts,
    SessionArtifacts,
    Telemetry,
)
from boron.navigator import MAX_STEPS, NavResult, build_prompt, navigate, parse_action
from boron.profiles import PROFILE_ALIASES, PROFILES, ProfileSpec, get_profile, list_profiles
from boron.runner import DATA_ROOT, NAV_TRACE_FILENAME, run_session, run_suite

__all__ = [
    "CAPTURE_POLICY",
    "CAPTURE_POLICY_MANUAL",
    "CAPTURE_POLICY_MANUAL_PNG",
    "CAPTURE_POLICY_VL",
    "DATA_ROOT",
    "MAX_STEPS",
    "NAV_TRACE_FILENAME",
    "NavResult",
    "PROFILES",
    "PROFILE_ALIASES",
    "ProfileSpec",
    "RawSessionArtifacts",
    "SessionArtifacts",
    "Telemetry",
    "build_prompt",
    "describe_pages",
    "from_screenshots",
    "get_profile",
    "load_elements",
    "list_profiles",
    "navigate",
    "parse_action",
    "run_manual",
    "run_session",
    "run_suite",
    "page_context",
    "rule_context",
    "to_contract1",
]
