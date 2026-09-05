"""helium.diagnose — fill report-level diagnosis/remediation. Score is immutable."""

from __future__ import annotations

import json

from helium.client import LLMClient
from helium.models import HeliumSynthesis
from helium.prompt import SYSTEM_PROMPT, user_prompt
from hydrogen.models import HydrogenReport


def diagnose(report: HydrogenReport, client: LLMClient) -> HydrogenReport:
    raw = client.complete(SYSTEM_PROMPT, user_prompt(report))
    synthesis = _parse_synthesis(raw)
    out = report.model_copy(deep=True)
    out.diagnosis = synthesis.diagnosis.strip()
    out.remediation = synthesis.remediation.strip()
    out.analyst = "helium"
    return out


def _parse_synthesis(raw: str) -> HeliumSynthesis:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Helium model did not return JSON") from exc
    return HeliumSynthesis.model_validate(payload)
