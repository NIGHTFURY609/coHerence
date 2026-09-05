"""Accessibility analyzer for DOM markup, WCAG 2.1 criteria, and Chromium Accessibility Tree."""
from __future__ import annotations
import json
import re
from typing import Dict, List, Any, Optional, Union
from bs4 import BeautifulSoup, Tag

from carbon.schemas.contracts import EvidenceItem, Severity, BoundingBox


SUSPICIOUS_ALT_PATTERNS = [
    r"^image$",
    r"^picture$",
    r"^photo$",
    r"^icon$",
    r"^logo$",
    r"^graphic$",
    r"^untitled$",
    r"^dsc_\d+$",
    r"^img_\d+$",
    r"\.(png|jpg|jpeg|gif|webp|svg)$",
]


class A11yAnalyzer:
    """Multi-modal accessibility analyzer examining DOM markup and Chromium Accessibility Trees."""

    @classmethod
    def analyze_html(cls, html_content: str) -> List[EvidenceItem]:
        """Run all accessibility audits against an HTML DOM snapshot."""
        if not html_content or not html_content.strip():
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        evidence: List[EvidenceItem] = []

        evidence.extend(cls.check_images(soup))
        evidence.extend(cls.check_form_controls(soup))
        evidence.extend(cls.check_heading_hierarchy(soup))
        evidence.extend(cls.check_aria_and_roles(soup))
        evidence.extend(cls.check_keyboard_and_focus(soup))

        return evidence

    @classmethod
    def check_images(cls, soup: BeautifulSoup) -> List[EvidenceItem]:
        """Validate image alternative text (WCAG 1.1.1 Non-text Content)."""
        evidence: List[EvidenceItem] = []

        for idx, img in enumerate(soup.find_all("img")):
            selector = cls._get_element_selector(img, idx, "img")
            has_alt = img.has_attr("alt")
            alt_text = img.get("alt", "")

            # Decorative images marked role="presentation" or role="none" are allowed empty alt
            is_decorative = img.get("role") in ["presentation", "none"] or img.get("aria-hidden") == "true"

            if not has_alt:
                evidence.append(
                    EvidenceItem(
                        element_selector=selector,
                        rule_id="MISSING_ALT_TEXT",
                        severity=Severity.CRITICAL,
                        metric_value="Missing alt attribute",
                        recommended_min="alt=\"[Descriptive text]\" or alt=\"\" for decorative images",
                        message=f"Image {selector} has no alt attribute, making it invisible to screen reader users.",
                        category="accessibility",
                    )
                )
            elif not is_decorative and alt_text:
                cleaned_alt = alt_text.strip().lower()
                for pat in SUSPICIOUS_ALT_PATTERNS:
                    if re.search(pat, cleaned_alt):
                        evidence.append(
                            EvidenceItem(
                                element_selector=selector,
                                rule_id="SUSPICIOUS_ALT_TEXT",
                                severity=Severity.WARNING,
                                metric_value=f"alt=\"{alt_text}\"",
                                recommended_min="Provide meaningful, contextual description",
                                message=(
                                    f"Image {selector} has placeholder or file-name alt text ('{alt_text}'). "
                                    "Fails to communicate image meaning to screen readers."
                                ),
                                category="accessibility",
                            )
                        )
                        break

        return evidence

    @classmethod
    def check_form_controls(cls, soup: BeautifulSoup) -> List[EvidenceItem]:
        """Validate form inputs, controls, and buttons have accessible names (WCAG 4.1.2 & 1.3.1)."""
        evidence: List[EvidenceItem] = []

        # 1. Inputs, textareas, selects
        controls = soup.find_all(["input", "select", "textarea"])
        for idx, ctrl in enumerate(controls):
            tag_name = ctrl.name
            ctrl_type = ctrl.get("type", "text").lower() if tag_name == "input" else tag_name

            # Skip hidden inputs or buttons handled separately
            if ctrl_type in ["hidden", "submit", "reset", "button", "image"]:
                continue

            ctrl_id = ctrl.get("id")
            selector = cls._get_element_selector(ctrl, idx, tag_name)

            has_aria_label = bool(ctrl.get("aria-label", "").strip())
            has_aria_labelledby = bool(ctrl.get("aria-labelledby", "").strip())
            has_title = bool(ctrl.get("title", "").strip())

            has_label_for = False
            if ctrl_id:
                label_elem = soup.find("label", attrs={"for": ctrl_id})
                if label_elem and label_elem.get_text(strip=True):
                    has_label_for = True

            has_wrapping_label = False
            parent_label = ctrl.find_parent("label")
            if parent_label and parent_label.get_text(strip=True):
                has_wrapping_label = True

            if not (has_aria_label or has_aria_labelledby or has_label_for or has_wrapping_label or has_title):
                evidence.append(
                    EvidenceItem(
                        element_selector=selector,
                        rule_id="UNLABELLED_FORM_INPUT",
                        severity=Severity.CRITICAL,
                        metric_value=f"Type '{ctrl_type}' without accessible label",
                        recommended_min="Associated <label for='...'> or aria-label",
                        message=(
                            f"Form field {selector} is missing an accessible label or name. "
                            "Screen reader users cannot understand what input is expected."
                        ),
                        category="accessibility",
                    )
                )

        # 2. Buttons
        buttons = soup.find_all(["button", "input"])
        for idx, btn in enumerate(buttons):
            if btn.name == "input" and btn.get("type", "").lower() not in ["submit", "button", "reset"]:
                continue

            selector = cls._get_element_selector(btn, idx, "button")
            text_content = btn.get_text(strip=True)
            aria_label = btn.get("aria-label", "").strip()
            aria_labelledby = btn.get("aria-labelledby", "").strip()
            val = btn.get("value", "").strip() if btn.name == "input" else ""
            title = btn.get("title", "").strip()

            # Check if button contains image with alt text
            has_img_with_alt = False
            img = btn.find("img")
            if img and img.get("alt", "").strip():
                has_img_with_alt = True

            if not (text_content or aria_label or aria_labelledby or val or title or has_img_with_alt):
                evidence.append(
                    EvidenceItem(
                        element_selector=selector,
                        rule_id="UNLABELLED_BUTTON",
                        severity=Severity.CRITICAL,
                        metric_value="Empty button text and missing aria-label",
                        recommended_min="Visible text or aria-label describing action",
                        message=f"Interactive button {selector} has no accessible label or inner text.",
                        category="accessibility",
                    )
                )

        return evidence

    @classmethod
    def check_heading_hierarchy(cls, soup: BeautifulSoup) -> List[EvidenceItem]:
        """Validate logical heading structure and prevent skipped heading levels (WCAG 1.3.1)."""
        evidence: List[EvidenceItem] = []
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])

        if not headings:
            evidence.append(
                EvidenceItem(
                    element_selector="body",
                    rule_id="NO_HEADINGS_FOUND",
                    severity=Severity.WARNING,
                    metric_value="0 headings",
                    recommended_min="At least one <h1> and logical heading tree",
                    message="Document has no heading tags (<h1> - <h6>), hindering screen reader navigation.",
                    category="accessibility",
                )
            )
            return evidence

        has_h1 = any(h.name == "h1" for h in headings)
        if not has_h1:
            evidence.append(
                EvidenceItem(
                    element_selector="body",
                    rule_id="MISSING_H1_HEADING",
                    severity=Severity.WARNING,
                    metric_value="No <h1> present",
                    recommended_min="One primary <h1> identifying the page purpose",
                    message="The page is missing an <h1> main title heading.",
                    category="accessibility",
                )
            )

        last_level = 0
        for idx, h in enumerate(headings):
            current_level = int(h.name[1])
            selector = cls._get_element_selector(h, idx, h.name)

            if not h.get_text(strip=True):
                evidence.append(
                    EvidenceItem(
                        element_selector=selector,
                        rule_id="EMPTY_HEADING",
                        severity=Severity.WARNING,
                        metric_value="Empty text",
                        recommended_min="Informative title text",
                        message=f"Heading {selector} has no text content.",
                        category="accessibility",
                    )
                )

            # Check skipped levels (e.g. h1 directly followed by h3)
            if last_level > 0 and current_level > last_level + 1:
                evidence.append(
                    EvidenceItem(
                        element_selector=selector,
                        rule_id="HEADING_HIERARCHY_SKIPPED",
                        severity=Severity.WARNING,
                        metric_value=f"<h{last_level}> directly followed by <h{current_level}>",
                        recommended_min=f"<h{last_level + 1}>",
                        message=(
                            f"Heading level skipped from <h{last_level}> to <h{current_level}> at {selector}. "
                            "Breaks screen reader navigational outlines."
                        ),
                        category="accessibility",
                    )
                )

            last_level = current_level

        return evidence

    @classmethod
    def check_aria_and_roles(cls, soup: BeautifulSoup) -> List[EvidenceItem]:
        """Validate interactive elements have proper semantics and required ARIA attributes."""
        evidence: List[EvidenceItem] = []

        # Non-semantic clickable elements
        for idx, elem in enumerate(soup.find_all(["div", "span", "p", "a"])):
            has_onclick = elem.has_attr("onclick") or elem.has_attr("@click") or elem.has_attr("v-on:click")
            role = elem.get("role")
            tabindex = elem.get("tabindex")

            if has_onclick and role not in ["button", "link", "menuitem", "tab"]:
                selector = cls._get_element_selector(elem, idx, elem.name)
                evidence.append(
                    EvidenceItem(
                        element_selector=selector,
                        rule_id="INACCESSIBLE_CLICKABLE_ELEMENT",
                        severity=Severity.CRITICAL,
                        metric_value="Non-semantic click handler without role",
                        recommended_min="Use <button> or role='button' with tabindex='0'",
                        message=(
                            f"Element {selector} has click interactions but lacks semantic role and keyboard tab stops. "
                            "Completely unusable for keyboard-only and screen-reader users."
                        ),
                        category="accessibility",
                    )
                )

        # Check required ARIA attributes for custom roles
        for idx, elem in enumerate(soup.find_all(attrs={"role": True})):
            role = elem.get("role", "").strip()
            selector = cls._get_element_selector(elem, idx, elem.name)

            if role in ["checkbox", "switch"] and not elem.has_attr("aria-checked"):
                evidence.append(
                    EvidenceItem(
                        element_selector=selector,
                        rule_id="MISSING_REQUIRED_ARIA_ATTR",
                        severity=Severity.WARNING,
                        metric_value=f"role='{role}' missing aria-checked",
                        recommended_min="aria-checked='true' or 'false'",
                        message=f"Element {selector} with role='{role}' requires aria-checked attribute.",
                        category="accessibility",
                    )
                )
            elif role == "slider" and not elem.has_attr("aria-valuenow"):
                evidence.append(
                    EvidenceItem(
                        element_selector=selector,
                        rule_id="MISSING_REQUIRED_ARIA_ATTR",
                        severity=Severity.WARNING,
                        metric_value="role='slider' missing aria-valuenow",
                        recommended_min="aria-valuenow, aria-valuemin, aria-valuemax",
                        message=f"Slider {selector} is missing aria-valuenow.",
                        category="accessibility",
                    )
                )

        return evidence

    @classmethod
    def check_keyboard_and_focus(cls, soup: BeautifulSoup) -> List[EvidenceItem]:
        """Validate keyboard navigability and identify potential focus anomalies."""
        evidence: List[EvidenceItem] = []

        # Check positive tabindex
        for idx, elem in enumerate(soup.find_all(attrs={"tabindex": True})):
            tabindex_val = elem.get("tabindex", "")
            try:
                ti = int(tabindex_val)
                if ti > 0:
                    selector = cls._get_element_selector(elem, idx, elem.name)
                    evidence.append(
                        EvidenceItem(
                            element_selector=selector,
                            rule_id="POSITIVE_TABINDEX_DISCOURAGED",
                            severity=Severity.WARNING,
                            metric_value=f"tabindex=\"{ti}\"",
                            recommended_min="tabindex=\"0\" or native element order",
                            message=(
                                f"Element {selector} uses positive tabindex ({ti}). "
                                "Overrides logical DOM reading order and disorients keyboard users."
                            ),
                            category="accessibility",
                        )
                    )
            except ValueError:
                pass

        return evidence

    @classmethod
    def analyze_a11y_tree_json(
        cls,
        tree_input: Union[str, Dict[str, Any], List[Any]],
    ) -> List[EvidenceItem]:
        """Parse Chromium DevTools Protocol Accessibility Tree (CDP Accessibility.getFullAXTree)."""
        evidence: List[EvidenceItem] = []

        if isinstance(tree_input, str):
            try:
                tree_data = json.loads(tree_input)
            except Exception:
                return evidence
        else:
            tree_data = tree_input

        nodes = tree_data if isinstance(tree_data, list) else tree_data.get("nodes", [])

        interactive_roles = {"button", "link", "checkbox", "radio", "combobox", "textbox", "slider", "menuitem"}

        for node in nodes:
            raw_role = node.get("role")
            role = raw_role.get("value") if isinstance(raw_role, dict) else raw_role

            raw_name = node.get("name")
            if isinstance(raw_name, dict):
                name = raw_name.get("value", "")
            else:
                name = raw_name

            backend_id = node.get("backendDOMNodeId") or node.get("nodeId", "ax_node")

            if role in interactive_roles and (name is None or str(name).strip() == ""):
                evidence.append(
                    EvidenceItem(
                        element_selector=f"[ax-node='{backend_id}']",
                        rule_id="AX_TREE_UNNAMED_INTERACTIVE_NODE",
                        severity=Severity.CRITICAL,
                        metric_value=f"Role '{role}' has empty accessibility name",
                        recommended_min="Valid accessible name in accessibility tree",
                        message=f"Interactive accessibility node with role '{role}' has no accessible name exposed to assistive tech.",
                        category="accessibility",
                    )
                )

        return evidence

    @staticmethod
    def _get_element_selector(tag: Tag, idx: int, default_name: str) -> str:
        """Construct a readable, precise CSS selector for a BeautifulSoup Tag."""
        elem_id = tag.get("id")
        if elem_id:
            return f"{tag.name}#{elem_id}"

        classes = tag.get("class")
        if classes and isinstance(classes, list):
            class_str = ".".join(classes[:2])
            return f"{tag.name}.{class_str}"

        return f"{tag.name}:nth-of-type({idx + 1})"
