"""Deterministic rule verifying color contrast ratios against WCAG 2.1 AA and AAA."""
from __future__ import annotations
from typing import Dict, List, Any, Optional

from carbon.rules.base import BaseRule
from carbon.schemas.contracts import EvidenceItem, Severity, BoundingBox
from carbon.analyzers.vision_analyzer import VisionAnalyzer


class ColorContrastRule(BaseRule):
    """Rule verifying color contrast ratios for text elements against background colors.
    
    Standards:
    - WCAG 2.1 AA: 4.5:1 for normal text, 3.0:1 for large text.
    - WCAG 2.1 AAA: 7.0:1 for normal text, 4.5:1 for large text.
    """

    rule_id = "COLOR_CONTRAST_FAIL_AA"
    name = "Color Contrast Compliance"
    category = "vision"
    default_severity = Severity.CRITICAL

    def evaluate(self, context: Dict[str, Any]) -> List[EvidenceItem]:
        """Evaluate text contrast pairs in context.
        
        Expected context keys:
            'contrast_elements': List of dicts with:
                - 'selector': str
                - 'fg_color': str (hex or rgb)
                - 'bg_color': str (hex or rgb)
                - 'is_large_text': Optional[bool]
                - 'bounding_box': Optional[dict or BoundingBox]
        """
        evidence: List[EvidenceItem] = []
        elements = context.get("contrast_elements", [])

        for elem in elements:
            selector = elem.get("selector", "text-element")
            fg = elem.get("fg_color")
            bg = elem.get("bg_color")
            is_large = bool(elem.get("is_large_text", False))
            bbox_raw = elem.get("bounding_box")

            bbox = None
            if isinstance(bbox_raw, dict):
                bbox = BoundingBox(**bbox_raw)
            elif isinstance(bbox_raw, BoundingBox):
                bbox = bbox_raw

            if fg and bg:
                item = VisionAnalyzer.evaluate_contrast_rule(
                    fg_color=fg,
                    bg_color=bg,
                    element_selector=selector,
                    is_large_text=is_large,
                    bounding_box=bbox,
                )
                if item:
                    evidence.append(item)

        return evidence
