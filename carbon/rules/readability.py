"""Deterministic rules for reading difficulty and exclusionary language."""
from __future__ import annotations
from typing import Dict, List, Any, Optional

from carbon.rules.base import BaseRule
from carbon.schemas.contracts import EvidenceItem, Severity
from carbon.analyzers.text_analyzer import TextAnalyzer


class ReadabilityRule(BaseRule):
    """Rule evaluating text content against plain language reading grade standards."""

    rule_id = "HIGH_READING_DIFFICULTY"
    name = "Reading Grade Level & Comprehension"
    category = "text"
    default_severity = Severity.WARNING

    def __init__(self, max_grade_level: float = 8.0):
        super().__init__()
        self.max_grade_level = max_grade_level
        self.analyzer = TextAnalyzer()

    def evaluate(self, context: Dict[str, Any]) -> List[EvidenceItem]:
        """Evaluate text or html in context."""
        evidence: List[EvidenceItem] = []
        text = context.get("text")
        html = context.get("html")

        if not text and html:
            text = self.analyzer.extract_clean_text_from_html(html)

        if text:
            result = self.analyzer.analyze_text(text, source_selector=context.get("selector", "body"))
            for item in result["evidence"]:
                if item.rule_id == self.rule_id:
                    evidence.append(item)

        return evidence


class InclusiveLanguageRule(BaseRule):
    """Rule evaluating text for gendered, ableist, or exclusionary terminology."""

    rule_id = "EXCLUSIONARY_LANGUAGE_DETECTED"
    name = "Inclusive Language & Terminology"
    category = "text"
    default_severity = Severity.WARNING

    def __init__(self):
        super().__init__()
        self.analyzer = TextAnalyzer()

    def evaluate(self, context: Dict[str, Any]) -> List[EvidenceItem]:
        """Evaluate text or html in context."""
        evidence: List[EvidenceItem] = []
        html = context.get("html")

        if html:
            evidence.extend(self.analyzer.analyze_html_elements(html))
        else:
            text = context.get("text")
            if text:
                result = self.analyzer.analyze_text(text, source_selector=context.get("selector", "body"))
                for item in result["evidence"]:
                    if item.rule_id == self.rule_id:
                        evidence.append(item)

        return evidence
