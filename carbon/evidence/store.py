"""Evidence store for normalizing, querying, and persisting Contract 2 payloads."""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Sequence

from carbon.schemas.contracts import (
    EvidenceItem,
    DisparityItem,
    EvidenceRecord,
    Severity,
)


class EvidenceStore:
    """Store managing normalized evidence items and disparity records for Dev 2 -> Dev 3 handoff."""

    def __init__(
        self,
        evidence: Optional[List[EvidenceItem]] = None,
        disparities: Optional[List[DisparityItem]] = None,
        session_ids: Optional[List[str]] = None,
        target_url: str = "",
        profiles_tested: Optional[List[str]] = None,
    ):
        self.evidence: List[EvidenceItem] = list(evidence) if evidence else []
        self.disparities: List[DisparityItem] = list(disparities) if disparities else []
        self.session_ids: List[str] = list(session_ids) if session_ids else []
        self.target_url: str = target_url
        self.profiles_tested: List[str] = list(profiles_tested) if profiles_tested else []

    def add_evidence(self, item: EvidenceItem) -> None:
        """Add a single evidence finding."""
        self.evidence.append(item)

    def add_evidence_batch(self, items: Sequence[EvidenceItem]) -> None:
        """Add multiple evidence findings."""
        self.evidence.extend(items)

    def add_disparity(self, item: DisparityItem) -> None:
        """Add a single disparity finding."""
        self.disparities.append(item)

    def add_disparity_batch(self, items: Sequence[DisparityItem]) -> None:
        """Add multiple disparity findings."""
        self.disparities.extend(items)

    def add_session_id(self, session_id: str) -> None:
        """Record session identifier."""
        if session_id not in self.session_ids:
            self.session_ids.append(session_id)

    def build_record(self) -> EvidenceRecord:
        """Compile contents into an EvidenceRecord adhering to Contract 2.

        `profiles_tested` is the caller's roster. Do not infer it from
        `disadvantaged_group` — that drops groups with no disparity row.
        """
        return EvidenceRecord(
            evidence=self.evidence,
            disparities=self.disparities,
            target_url=self.target_url,
            profiles_tested=list(self.profiles_tested),
            session_ids=self.session_ids,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_contract2_dict(self) -> Dict[str, Any]:
        """Output exact Contract 2 dictionary payload."""
        rec = self.build_record()
        return rec.model_dump(exclude_none=True)

    def to_contract2_json(self, indent: int = 2) -> str:
        """Output exact Contract 2 JSON formatted string."""
        return json.dumps(self.to_contract2_dict(), indent=indent)

    def save_to_file(self, filepath: str) -> None:
        """Persist Contract 2 payload to JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_contract2_json())

    @classmethod
    def load_from_file(cls, filepath: str) -> EvidenceStore:
        """Load an EvidenceStore from a saved Contract 2 JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        record = EvidenceRecord(**data)
        return cls(
            evidence=record.evidence,
            disparities=record.disparities,
            session_ids=record.session_ids or [],
            target_url=record.target_url or "",
            profiles_tested=list(record.profiles_tested or []),
        )

    def filter_by_severity(self, severity: Severity) -> List[EvidenceItem]:
        """Filter evidence items by severity level."""
        return [e for e in self.evidence if e.severity == severity]

    def filter_by_rule(self, rule_id: str) -> List[EvidenceItem]:
        """Filter evidence items matching a specific rule code."""
        return [e for e in self.evidence if e.rule_id == rule_id]

    def filter_disparities_by_group(self, group: str) -> List[DisparityItem]:
        """Filter calculated disparities affecting a specific disadvantaged profile."""
        return [d for d in self.disparities if d.disadvantaged_group == group]
