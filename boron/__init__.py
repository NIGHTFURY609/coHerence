"""Boron - browser ingestion and synthetic user agent engine (Dev 1)."""

from boron.handoff import load_elements, page_context, rule_context, to_contract1
from boron.models import RawSessionArtifacts, SessionArtifacts, Telemetry
from boron.profiles import PROFILE_ALIASES, PROFILES, ProfileSpec, get_profile, list_profiles
from boron.runner import DATA_ROOT, run_session, run_suite

__all__ = [
    "DATA_ROOT",
    "PROFILES",
    "PROFILE_ALIASES",
    "ProfileSpec",
    "RawSessionArtifacts",
    "SessionArtifacts",
    "Telemetry",
    "get_profile",
    "load_elements",
    "list_profiles",
    "run_session",
    "run_suite",
    "page_context",
    "rule_context",
    "to_contract1",
]
