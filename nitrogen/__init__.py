"""Nitrogen (Z=7): Qwen3-VL-30B host. Prompt engineering is the caller's."""

from nitrogen.constants import VISION_MODEL

__all__ = [
    "VISION_MODEL",
    "MockVLClient",
    "ModalVLClient",
]


def __getattr__(name: str):
    if name in {"MockVLClient", "ModalVLClient"}:
        from nitrogen.client import MockVLClient, ModalVLClient

        return {"MockVLClient": MockVLClient, "ModalVLClient": ModalVLClient}[name]
    raise AttributeError(f"module 'nitrogen' has no attribute {name!r}")
