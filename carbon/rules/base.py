"""Base classes and interfaces for the Deterministic Rule Engine."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from carbon.schemas.contracts import EvidenceItem, Severity


class BaseRule(ABC):
    """Abstract base rule class for all deterministic accessibility and UX rules."""

    rule_id: str
    name: str
    category: str
    default_severity: Severity

    def __init__(
        self,
        rule_id: Optional[str] = None,
        name: Optional[str] = None,
        category: Optional[str] = None,
        default_severity: Optional[Severity] = None,
    ):
        if rule_id:
            self.rule_id = rule_id
        if name:
            self.name = name
        if category:
            self.category = category
        if default_severity:
            self.default_severity = default_severity

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> List[EvidenceItem]:
        """Evaluate rule against provided context.
        
        Args:
            context: Dictionary that may contain 'elements', 'html', 'image',
                     'bounding_boxes', 'styles', etc.
                     
        Returns:
            List of generated EvidenceItem violations.
        """
        pass
