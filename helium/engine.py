"""helium.diagnose — fill report-level diagnosis/remediation. Score is immutable."""

from __future__ import annotations

import json

from helium.client import LLMClient, get_client
from helium.models import HeliumSynthesis
from helium.prompt import SYSTEM_PROMPT, user_prompt
from hydrogen.models import HydrogenReport


def diagnose(
    report: HydrogenReport, client: LLMClient | None = None
) -> HydrogenReport:
    if client is None:
        client = get_client()
    raw = client.complete(SYSTEM_PROMPT, user_prompt(report))
    synthesis = _parse_synthesis(raw)
    out = report.model_copy(deep=True)
    out.diagnosis = synthesis.diagnosis.strip()
    out.remediation = synthesis.remediation.strip()
    out.analyst = "helium"
    return out


def _parse_synthesis(raw: str) -> HeliumSynthesis:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Helium model did not return JSON")
    text = raw.strip()
    if "</think>" in text:
        text = text.split("</think>", 1)[-1].strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Helium model did not return JSON") from exc
    return HeliumSynthesis.model_validate(payload)
