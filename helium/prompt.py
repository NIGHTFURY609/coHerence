"""Build the text-only Helium prompt from a HydrogenReport."""

from __future__ import annotations

import json

from hydrogen.models import HydrogenReport

SYSTEM_PROMPT = """You write one diagnosis and one remediation for an inclusive-design test report.

Rules:
- Use only the JSON evidence you are given. Do not invent WCAG, users, or metrics.
- Consider all evidence streams that are present. Prioritize what is relevant to the strongest findings and the observed disparity. Do not mention every row. Do not dump a list of every click or INFO item.
- Write about constraints and interface evidence, never personas or stereotypes.
- If a finding's attribution_status is UNRESOLVED, state the gap and the UI facts side by side. Do not say the UI facts caused the gap. Forbidden phrasing: "driven by", "caused by", "due to", "disproportionately impact".
- Do not change or invent the fairness score. You may quote a gap that is in the JSON (for example 28 pp).
- Short paragraphs. No chain-of-thought. No preamble.

Reply with JSON only, matching:
{"diagnosis": "...", "remediation": "..."}
"""


def brief(report: HydrogenReport) -> dict:
    """Compact view of the assembled contract for the LLM."""
    gap_pp = None
    if report.breakdown.bottleneck_abs_gap and report.breakdown.bottleneck_metric.endswith(
        ("rate", "completion_rate", "failure_rate", "abandonment_rate")
    ):
        gap_pp = round(report.breakdown.bottleneck_abs_gap * 100)
    elif report.breakdown.bottleneck_abs_gap:
        gap_pp = report.breakdown.bottleneck_abs_gap

    return {
        "hydrogen": {
            "overall_fairness_score": report.overall_fairness_score,
            "score_status": report.score_status.value,
            "bottleneck_metric": report.breakdown.bottleneck_metric,
            "bottleneck_group": report.breakdown.bottleneck_group,
            "bottleneck_abs_gap": report.breakdown.bottleneck_abs_gap,
            "completion_gap_pp": gap_pp,
            "baseline_poor": report.breakdown.baseline_poor,
        },
        "disparities": [
            {
                "metric": row.metric,
                "baseline_value": row.baseline_value,
                "constrained_value": row.constrained_value,
                "disadvantaged_group": row.disadvantaged_group,
            }
            for row in report.disparities
        ],
        "findings": [
            {
                "id": f.id,
                "title": f.title,
                "severity": f.severity.value,
                "rule_id": f.rule_id,
                "element_selector": f.element_selector,
                "attribution_status": f.attribution_status.value,
                "affected_profiles": f.affected_profiles,
            }
            for f in report.findings
        ],
    }


def user_prompt(report: HydrogenReport) -> str:
    return (
        "Synthesize one diagnosis and one remediation from this HydrogenReport.\n\n"
        + json.dumps(brief(report), indent=2)
    )
