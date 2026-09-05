"""Adapters from Boron output to the Dev 2 (carbon) input shapes."""

from __future__ import annotations

import json
from pathlib import Path

from boron.models import RawSessionArtifacts

# WCAG 2.1: large text is >=24px, or >=18.66px when bold.
LARGE_TEXT_PX = 24.0
LARGE_BOLD_PX = 18.66
BOLD_WEIGHT = 700


def load_elements(record: RawSessionArtifacts) -> list[dict]:
    return json.loads(Path(record.artifacts.elements_path).read_text(encoding="utf-8"))


def rule_context(record: RawSessionArtifacts) -> dict:
    """The `interactive_elements` / `contrast_elements` carbon's RuleEngine expects.

    carbon.RuleEngine.evaluate_session_artifacts takes these as arguments and
    defaults them to empty lists; it has no other source of layout geometry.
    """
    elements = [e for e in load_elements(record) if e.get("visible")]
    return {
        "interactive_elements": [
            {
                "selector": e["element_selector"],
                "bounding_box": e["bounding_box"],
                "tag": e["tag"],
            }
            for e in elements
            if e.get("interactive")
        ],
        "contrast_elements": [
            {
                "selector": e["element_selector"],
                "fg_color": e["color"],
                "bg_color": e["background_color"],
                "is_large_text": _is_large_text(e),
                "bounding_box": e["bounding_box"],
            }
            for e in elements
            if e.get("text")
        ],
    }


def to_contract1(record: RawSessionArtifacts) -> dict:
    """Contract 1 JSON. carbon declares every field Boron emits, so this is a plain dump."""
    return record.model_dump()


def _is_large_text(element: dict) -> bool:
    size = _px(element.get("font_size"))
    weight = _weight(element.get("font_weight"))
    return size >= LARGE_TEXT_PX or (size >= LARGE_BOLD_PX and weight >= BOLD_WEIGHT)


def _px(value) -> float:
    try:
        return float(str(value).removesuffix("px"))
    except (TypeError, ValueError):
        return 0.0


def _weight(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 400 if value != "bold" else BOLD_WEIGHT


def page_context(record: RawSessionArtifacts) -> dict:
    """Everything carbon's RuleEngine.evaluate_context needs, from one session.

    Evaluate this on the BASELINE session. Static defects are properties of the
    page as authored, not of a profile, so running the rule engine once per
    profile would duplicate every finding N times. It would also attribute page
    defects to whichever profile happened to be running, which is the false
    join hydrogen/sub-arch.md 6.4 forbids.
    """
    context = {
        "session_id": record.session_id,
        "profile_id": record.profile_id,
        "url": record.url,
        **rule_context(record),
    }
    html = Path(record.artifacts.html_path)
    if html.exists():
        context["html"] = html.read_text(encoding="utf-8", errors="ignore")
    tree = Path(record.artifacts.a11y_tree_path)
    if tree.exists():
        context["a11y_tree"] = json.loads(tree.read_text(encoding="utf-8"))
    screenshot = Path(record.artifacts.screenshot_path)
    if screenshot.exists():
        context["screenshot"] = str(screenshot)
    return context
