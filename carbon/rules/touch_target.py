"""Deterministic rule verifying touch target sizing for interactive elements."""
from __future__ import annotations
from typing import Dict, List, Any, Optional

from carbon.rules.base import BaseRule
from carbon.schemas.contracts import EvidenceItem, Severity, BoundingBox


class TouchTargetSizeRule(BaseRule):
    """Rule evaluating interactive touch target dimensions against WCAG 2.5.5 and mobile HIG standards.
    
    Standard:
    - Recommended standard: >= 48x48px (or 44x44px iOS / 48x48px Android Material)
    - Minimum threshold: >= 24x24px (WCAG 2.5.8 Level AA minimum)
    """

    rule_id = "TOUCH_TARGET_TOO_SMALL"
    suboptimal_rule_id = "TOUCH_TARGET_SUBOPTIMAL"
    declared_rule_ids = ["TOUCH_TARGET_TOO_SMALL", "TOUCH_TARGET_SUBOPTIMAL"]
    name = "Interactive Touch Target Minimum Size"
    category = "motor"
    default_severity = Severity.CRITICAL

    def __init__(
        self,
        recommended_min_px: float = 48.0,
        absolute_min_px: float = 24.0,
    ):
        super().__init__()
        self.recommended_min_px = recommended_min_px
        self.absolute_min_px = absolute_min_px

    def evaluate(self, context: Dict[str, Any]) -> List[EvidenceItem]:
        """Evaluate interactive elements provided in context.
        
        Expected context keys:
            'interactive_elements': List of dicts or objects with:
                - 'selector': str
                - 'bounding_box': BoundingBox or dict with {x, y, width, height}
                - 'tag': Optional[str]
        """
        evidence: List[EvidenceItem] = []
        elements = context.get("interactive_elements", [])

        for elem in elements:
            selector = elem.get("selector", "interactive-element")
            bbox_raw = elem.get("bounding_box")

            if not bbox_raw:
                continue

            if isinstance(bbox_raw, dict):
                bbox = BoundingBox(**bbox_raw)
            elif isinstance(bbox_raw, BoundingBox):
                bbox = bbox_raw
            else:
                continue

            w = bbox.width
            h = bbox.height

            # If either dimension falls below the minimum standard
            if w < self.absolute_min_px or h < self.absolute_min_px:
                evidence.append(
                    EvidenceItem(
                        element_selector=selector,
                        bounding_box=bbox,
                        rule_id="TOUCH_TARGET_TOO_SMALL",
                        severity=Severity.CRITICAL,
                        metric_value=f"{int(w)}x{int(h)}px",
                        recommended_min=f"{int(self.recommended_min_px)}x{int(self.recommended_min_px)}px",
                        message=(
                            f"Touch target {selector} is only {int(w)}x{int(h)}px, failing the minimum "
                            f"{int(self.absolute_min_px)}x{int(self.absolute_min_px)}px standard. "
                            "Leads to high missed-click rates for users with motor tremors or touch input."
                        ),
                        category="motor",
                    )
                )
            elif w < self.recommended_min_px or h < self.recommended_min_px:
                evidence.append(
                    EvidenceItem(
                        element_selector=selector,
                        bounding_box=bbox,
                        rule_id="TOUCH_TARGET_SUBOPTIMAL",
                        severity=Severity.WARNING,
                        metric_value=f"{int(w)}x{int(h)}px",
                        recommended_min=f"{int(self.recommended_min_px)}x{int(self.recommended_min_px)}px",
                        message=(
                            f"Touch target {selector} is {int(w)}x{int(h)}px, which is below the recommended "
                            f"{int(self.recommended_min_px)}x{int(self.recommended_min_px)}px ergonomic baseline."
                        ),
                        category="motor",
                    )
                )

        return evidence
