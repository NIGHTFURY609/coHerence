"""Orchestrator for deterministic rules and multi-modal evidence collection."""
from __future__ import annotations
import json
import os
from typing import Dict, List, Any, Optional

from carbon.schemas.contracts import (
    EvidenceItem,
    Severity,
    RawSessionArtifacts,
)
from carbon.rules.base import BaseRule
from carbon.rules.touch_target import TouchTargetSizeRule
from carbon.rules.spacing import InteractiveSpacingRule
from carbon.rules.contrast import ColorContrastRule
from carbon.rules.readability import ReadabilityRule, InclusiveLanguageRule
from carbon.analyzers.a11y_analyzer import A11yAnalyzer
from carbon.analyzers.vision_analyzer import VisionAnalyzer
from carbon.analyzers.text_analyzer import TextAnalyzer


SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}

# Rule-to-constrained-profile taxonomy map (Join Key for Hydrogen)
RULE_AFFECTED_PROFILES_MAP: Dict[str, List[str]] = {
    "TOUCH_TARGET_TOO_SMALL": ["motor_impaired", "touch_screen_users"],
    "TOUCH_TARGET_SUBOPTIMAL": ["motor_impaired"],
    "INTERACTIVE_SPACING_TOO_TIGHT": ["motor_impaired", "tremor_users"],
    "INTERACTIVE_ELEMENTS_OVERLAPPING": ["motor_impaired", "keyboard_only"],
    "COLOR_CONTRAST_FAIL_AA": ["low_vision", "elderly"],
    "COLOR_CONTRAST_FAIL_AAA": ["low_vision"],
    "MISSING_ALT_TEXT": ["screen_reader_users"],
    "SUSPICIOUS_ALT_TEXT": ["screen_reader_users"],
    "UNLABELLED_FORM_INPUT": ["screen_reader_users", "motor_impaired"],
    "UNLABELLED_BUTTON": ["screen_reader_users"],
    "HEADING_HIERARCHY_SKIPPED": ["screen_reader_users"],
    "INACCESSIBLE_CLICKABLE_ELEMENT": ["keyboard_only", "screen_reader_users"],
    "POSITIVE_TABINDEX_DISCOURAGED": ["keyboard_only"],
    "AX_TREE_UNNAMED_INTERACTIVE_NODE": ["screen_reader_users"],
    "HIGH_READING_DIFFICULTY": ["cognitive_impaired", "esl_users"],
    "EXCLUSIONARY_LANGUAGE_DETECTED": ["marginalized_demographics"],
    "HIGH_VISUAL_CLUTTER": ["cognitive_impaired", "low_vision", "adhd_users"],
    "INSUFFICIENT_WHITESPACE": ["low_vision", "cognitive_impaired"],
}


class RuleEngine:
    """Deterministic Rule Engine orchestrating accessibility, UX, vision, and text rules."""

    def __init__(self, rules: Optional[List[BaseRule]] = None):
        if rules is not None:
            self.rules = rules
        else:
            self.rules = [
                TouchTargetSizeRule(),
                InteractiveSpacingRule(),
                ColorContrastRule(),
                ReadabilityRule(),
                InclusiveLanguageRule(),
            ]

    def add_rule(self, rule: BaseRule) -> None:
        """Register a new rule in the engine."""
        self.rules.append(rule)

    def evaluate_context(self, context: Dict[str, Any]) -> List[EvidenceItem]:
        """Run all registered rules and analyzers against the provided context dictionary."""
        evidence: List[EvidenceItem] = []

        # 1. Run deterministic registered rules
        for rule in self.rules:
            try:
                results = rule.evaluate(context)
                if results:
                    evidence.extend(results)
            except Exception as ex:
                # Safeguard rule evaluation from crashing overall pipeline
                evidence.append(
                    EvidenceItem(
                        element_selector="rule-engine",
                        rule_id=f"{rule.rule_id}_ERROR",
                        severity=Severity.INFO,
                        metric_value="Rule evaluation exception",
                        message=f"Rule {rule.name} raised error: {str(ex)}",
                        category="system",
                    )
                )

        # 2. Run A11yAnalyzer on HTML if provided
        html_content = context.get("html")
        if html_content:
            a11y_findings = A11yAnalyzer.analyze_html(html_content)
            evidence.extend(a11y_findings)

        # 3. Run A11y tree analyzer if tree provided
        a11y_tree = context.get("a11y_tree")
        if a11y_tree:
            tree_findings = A11yAnalyzer.analyze_a11y_tree_json(a11y_tree)
            evidence.extend(tree_findings)

        # 4. Run VisionAnalyzer on screenshot if provided
        screenshot = context.get("screenshot")
        if screenshot is not None:
            try:
                vis_result = VisionAnalyzer.analyze_screenshot_image(screenshot)
                evidence.extend(vis_result.get("evidence", []))
            except Exception as ex:
                evidence.append(
                    EvidenceItem(
                        element_selector="screenshot",
                        rule_id="VISION_ANALYSIS_FAILED",
                        severity=Severity.INFO,
                        metric_value="Screenshot analysis failed",
                        message=f"VisionAnalyzer could not process screenshot: {str(ex)}",
                        category="vision",
                    )
                )

        return self.deduplicate_and_sort(evidence)

    def evaluate_session_artifacts(
        self,
        session: RawSessionArtifacts,
        base_dir: str = "",
        interactive_elements: Optional[List[Dict[str, Any]]] = None,
        contrast_elements: Optional[List[Dict[str, Any]]] = None,
    ) -> List[EvidenceItem]:
        """Evaluate a RawSessionArtifacts payload from Dev 1.
        
        Reads artifact files (DOM HTML, screenshot, AXTree) from disk if present.
        """
        context: Dict[str, Any] = {
            "session_id": session.session_id,
            "profile_id": session.profile_id,
            "url": session.url,
            "interactive_elements": interactive_elements or [],
            "contrast_elements": contrast_elements or [],
        }

        # Load DOM HTML if path is valid
        if session.artifacts.html_path:
            p = os.path.join(base_dir, session.artifacts.html_path) if base_dir else session.artifacts.html_path
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    context["html"] = f.read()

        # Load Accessibility Tree if present
        if session.artifacts.a11y_tree_path:
            p = os.path.join(base_dir, session.artifacts.a11y_tree_path) if base_dir else session.artifacts.a11y_tree_path
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    try:
                        context["a11y_tree"] = json.load(f)
                    except Exception:
                        pass

        # Reference screenshot path if present
        if session.artifacts.screenshot_path:
            p = os.path.join(base_dir, session.artifacts.screenshot_path) if base_dir else session.artifacts.screenshot_path
            if os.path.exists(p):
                context["screenshot"] = p

        evidence = self.evaluate_context(context)
        for item in evidence:
            if not item.profile_id and session.profile_id:
                item.profile_id = session.profile_id
            if session.profile_id and session.profile_id not in item.affected_profiles:
                item.affected_profiles.append(session.profile_id)
        return evidence

    @staticmethod
    def deduplicate_and_sort(evidence_items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Deduplicate findings by (element_selector, rule_id) and sort by severity."""
        seen = set()
        unique_items: List[EvidenceItem] = []

        for item in evidence_items:
            # Populate affected_profiles from taxonomy if empty
            if not item.affected_profiles and item.rule_id in RULE_AFFECTED_PROFILES_MAP:
                item.affected_profiles = list(RULE_AFFECTED_PROFILES_MAP[item.rule_id])

            key = (item.element_selector, item.rule_id)
            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        # Sort: CRITICAL (0), WARNING (1), INFO (2)
        unique_items.sort(key=lambda it: SEVERITY_ORDER.get(it.severity, 3))
        return unique_items
