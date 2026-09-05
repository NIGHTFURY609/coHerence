"""Access to Gemma 4 26B-A4B-IT. Callers own the prompt. Tests use MockVLClient."""

from __future__ import annotations

from typing import Protocol


class VLClient(Protocol):
    def complete(
        self, system: str, user: str, image_b64: str | None = None
    ) -> str:
        """Raw model text."""


class MockVLClient:
    def __init__(self, text: str = "ok") -> None:
        self.text = text
        self.last_system = ""
        self.last_user = ""
        self.last_image_b64: str | None = None

    def complete(
        self, system: str, user: str, image_b64: str | None = None
    ) -> str:
        self.last_system = system
        self.last_user = user
        self.last_image_b64 = image_b64
        return self.text


class ModalVLClient:
    """Same B300 replica. Weights on helium-hf-cache."""

    def complete(
        self, system: str, user: str, image_b64: str | None = None
    ) -> str:
        from helium.runtime import invoke_gpu

        return invoke_gpu("fluorine_complete", system, user, image_b64)
