"""Build the text-only Helium prompt from a HydrogenReport.

Facts come from the report (gap, titles, selectors). The system prompt is
format-only — it must not name a specific page or control.
"""

from __future__ import annotations

from hydrogen.models import FindingDraft, HydrogenReport, Severity

SYSTEM_PROMPT = """You write one diagnosis and one remediation for an inclusive-design test report.

The output is a short report on the issues and what to change in the UI.
Name the actual controls from the USER facts. It is NOT a dump of finding ids or score fields.

The user message is the only source of controls, numbers, and gaps.
Do not reuse controls or numbers from any example. If a selector is in the user facts, repeat it.

Format of the user facts:
Hydrogen:
  completion gap = <N> pp

  <issue> (<css selector>)
  ...

Output:
{"diagnosis": "...", "remediation": "..."}

diagnosis names the gap and the same selectors/numbers as the user facts.
remediation says what to change on those same selectors.

Rules:
- Use only the user facts. Do not invent WCAG, users, metrics, CSS, or controls.
- One combined diagnosis. Weave the gap with the relevant interface facts. Do not mention every row. Do not list find_1, rule ids, or attribution labels.
- Repeat each css selector from the user facts in diagnosis AND remediation. Do not say "the primary action" or "the instruction" unless that exact phrase is in the user facts; still include the selector.
- Quote numbers from the user facts (gaps, steps, error counts). Do not replace them with "extensive" or "additional" alone.
- Do not quote overall_fairness_score, RESOLVED, UNRESOLVED, or bottleneck field names in the output.
- Constraints and interface evidence only. No personas or stereotypes.
- State the gap and the UI facts side by side. Do not say the UI facts caused the gap. Forbidden: "driven by", "caused by", "due to", "disproportionately impact", "correlates", "directly correlates".
- Do not change or invent the fairness score. You may quote a gap that is in the user facts.
- diagnosis = what was observed, naming the controls. remediation = what to change on those same controls. Not "investigate findings".
- Both strings must be complete sentences that end with a period. Never stop mid-phrase.
- Short paragraphs. No <think>. No preamble.

Reply with JSON only:
{"diagnosis": "...", "remediation": "..."}
"""


def _with_selector(text: str, selector: str) -> str:
    sel = (selector or "").strip()
    if not sel or sel in text:
        return text
    return f"{text} ({sel})"


def _fact(finding: FindingDraft) -> str:
    title = (finding.title or "").strip()
    if not title:
        title = (finding.rule_id or "issue").replace("_", " ").lower()
    return _with_selector(title, finding.element_selector)


def _completion_gap_pp(report: HydrogenReport) -> int | None:
    gap = report.breakdown.bottleneck_abs_gap
    metric = report.breakdown.bottleneck_metric or ""
    if not gap:
        return None
    if metric.endswith(("rate", "completion_rate", "failure_rate", "abandonment_rate")):
        return round(gap * 100)
    return None


def _priority_findings(report: HydrogenReport) -> list[FindingDraft]:
    rank = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    rows = [f for f in report.findings if f.severity is not Severity.INFO]
    rows.sort(key=lambda f: rank.get(f.severity, 9))
    return rows[:6]


def brief(report: HydrogenReport) -> dict:
    """Compact structured view. Prefer user_prompt() for the model."""
    gap_pp = _completion_gap_pp(report)
    return {
        "hydrogen": {
            "completion_gap_pp": gap_pp,
            "bottleneck_metric": report.breakdown.bottleneck_metric,
            "bottleneck_group": report.breakdown.bottleneck_group,
            "bottleneck_abs_gap": report.breakdown.bottleneck_abs_gap,
        },
        "facts": [
            {
                "fact": _fact(f),
                "element_selector": f.element_selector,
            }
            for f in _priority_findings(report)
        ],
    }


def user_prompt(report: HydrogenReport) -> str:
    """Facts from this HydrogenReport only."""
    gap_pp = _completion_gap_pp(report)
    lines = [
        "Write one diagnosis and one remediation from these facts.",
        "Name each control by its selector in both diagnosis and remediation.",
        "Do not quote finding ids, scores, or attribution labels.",
        "",
        "Hydrogen:",
    ]
    if gap_pp is not None:
        lines.append(f"  completion gap = {gap_pp} pp")
    elif report.breakdown.bottleneck_metric:
        lines.append(
            f"  {report.breakdown.bottleneck_metric} gap = "
            f"{report.breakdown.bottleneck_abs_gap}"
        )
    else:
        lines.append("  (no completion gap on the report)")
    lines.append("")
    lines.append("Interface:")
    for finding in _priority_findings(report):
        lines.append(f"  {_fact(finding)}")
    lines.append("")
    return "\n".join(lines)
