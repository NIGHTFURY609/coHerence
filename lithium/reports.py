"""lithium.create_report — Hydrogen score, optional Helium text. No rescoring."""

from __future__ import annotations

import hydrogen
from hydrogen.models import EvidenceBundle, HydrogenReport


def create_report(
    payload: dict | EvidenceBundle,
    report_id: str,
    *,
    diagnose: bool = True,
    llm_client=None,
) -> HydrogenReport:
    """Contract 2 JSON (or EvidenceBundle) → Contract 3 HydrogenReport.

    Always `hydrogen.evaluate`. `helium.diagnose` only when `diagnose=True`.
    The integer score is never rewritten here.
    """
    if not isinstance(payload, dict):
        payload = payload.model_dump(mode="json")
    report = hydrogen.evaluate(hydrogen.parse_contract2(payload), report_id)
    if not diagnose:
        return report
    from helium import diagnose as helium_diagnose

    return helium_diagnose(report, client=llm_client)
