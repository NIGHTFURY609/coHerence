"""LLM client protocol. Tests use MockLLMClient. Live Modal is later."""

from __future__ import annotations

from typing import Protocol

from helium.models import HeliumSynthesis


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str:
        """Return a JSON string matching HeliumSynthesis."""


class MockLLMClient:
    def __init__(self, synthesis: HeliumSynthesis | None = None) -> None:
        self.synthesis = synthesis or HeliumSynthesis(
            diagnosis=(
                "The constrained interaction path has substantially lower "
                "completion and requires additional navigation and errors. "
                "The interface also presents the primary action with low "
                "visual prominence and uses ambiguous instructions."
            ),
            remediation=(
                "Increase prominence of the primary action and clarify "
                "the instruction."
            ),
        )
        self.last_system = ""
        self.last_user = ""

    def complete(self, system: str, user: str) -> str:
        self.last_system = system
        self.last_user = user
        return self.synthesis.model_dump_json()
