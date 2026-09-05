"""Fluorine (Z=9): Gemma 4 26B-A4B-IT vision host. Callers own prompts."""

from fluorine.constants import VISION_MODEL

__all__ = [
    "VISION_MODEL",
    "MockVLClient",
    "ModalVLClient",
]


def __getattr__(name: str):
    if name in {"MockVLClient", "ModalVLClient"}:
        from fluorine.client import MockVLClient, ModalVLClient

        return {"MockVLClient": MockVLClient, "ModalVLClient": ModalVLClient}[name]
    raise AttributeError(f"module 'fluorine' has no attribute {name!r}")
