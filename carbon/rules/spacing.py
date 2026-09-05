"""Deterministic rule verifying minimum spacing between adjacent interactive elements."""
from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple

from carbon.rules.base import BaseRule
from carbon.schemas.contracts import EvidenceItem, Severity, BoundingBox


class InteractiveSpacingRule(BaseRule):
    """Rule evaluating interactive touch target spacing to prevent accidental misclicks.
    
    Standard:
    - Minimum edge-to-edge separation: >= 8px between separate interactive targets.
    - Intentional segmented controls/button groups (is_grouped=True or shared group_id) are respected.
    - Accidental misclicks occur frequently when small independent buttons are placed too close together.
    """

    rule_id = "INTERACTIVE_SPACING_TOO_TIGHT"
    name = "Interactive Target Spacing"
    category = "motor"
    default_severity = Severity.WARNING

    def __init__(self, min_spacing_px: float = 8.0):
        super().__init__()
        self.min_spacing_px = min_spacing_px

    def evaluate(self, context: Dict[str, Any]) -> List[EvidenceItem]:
        """Evaluate interactive elements provided in context for spacing proximity."""
        evidence: List[EvidenceItem] = []
        elements = context.get("interactive_elements", [])

        # Parse valid elements with bounding boxes and group metadata
        parsed_items: List[Dict[str, Any]] = []
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

            parsed_items.append({
                "selector": selector,
                "bbox": bbox,
                "group_id": elem.get("group_id"),
                "is_grouped": bool(elem.get("is_grouped", False)),
                "role": elem.get("role", ""),
            })

        n = len(parsed_items)
        for i in range(n):
            item_a = parsed_items[i]
            sel_a, box_a = item_a["selector"], item_a["bbox"]

            for j in range(i + 1, n):
                item_b = parsed_items[j]
                sel_b, box_b = item_b["selector"], item_b["bbox"]

                # Skip intentionally grouped controls (e.g. segmented controls, tablist, toolbars)
                if item_a["group_id"] and item_a["group_id"] == item_b["group_id"]:
                    continue
                if item_a["is_grouped"] and item_b["is_grouped"]:
                    continue
                if item_a["role"] in ["tab", "radio"] and item_b["role"] in ["tab", "radio"]:
                    continue

                # Compute bounding box union for frontend overlay highlighting
                union_x = min(box_a.x, box_b.x)
                union_y = min(box_a.y, box_b.y)
                union_w = max(box_a.x + box_a.width, box_b.x + box_b.width) - union_x
                union_h = max(box_a.y + box_a.height, box_b.y + box_b.height) - union_y
                union_box = BoundingBox(x=union_x, y=union_y, width=union_w, height=union_h)

                if box_a.overlaps(box_b):
                    evidence.append(
                        EvidenceItem(
                            element_selector=f"{sel_a} & {sel_b}",
                            bounding_box=union_box,
                            rule_id="INTERACTIVE_ELEMENTS_OVERLAPPING",
                            severity=Severity.CRITICAL,
                            metric_value="0px (overlapping targets)",
                            recommended_min=f">={int(self.min_spacing_px)}px separation",
                            message=(
                                f"Interactive targets '{sel_a}' and '{sel_b}' overlap bounding areas. "
                                "Causes severe click interception and misclicks for all users."
                            ),
                            category="motor",
                        )
                    )
                else:
                    dist = box_a.edge_distance(box_b)
                    if dist < self.min_spacing_px:
                        evidence.append(
                            EvidenceItem(
                                element_selector=f"{sel_a} & {sel_b}",
                                bounding_box=union_box,
                                rule_id="INTERACTIVE_SPACING_TOO_TIGHT",
                                severity=Severity.WARNING,
                                metric_value=f"{dist:.1f}px separation",
                                recommended_min=f">={int(self.min_spacing_px)}px separation",
                                message=(
                                    f"Interactive targets '{sel_a}' and '{sel_b}' are only {dist:.1f}px apart. "
                                    f"Fails minimum {int(self.min_spacing_px)}px spacing guideline, increasing "
                                    "accidental click errors for users with motor tremors."
                                ),
                                category="motor",
                            )
                        )

        return evidence
