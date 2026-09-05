"""Public Helium surface.

This module must not import hydrogen. The GPU worker may load `helium`
when Modal mounts the package; Hydrogen stays on CPU (diagnose/prompt).
"""

from helium.constants import HELIUM_RUNTIME, REPORT_MODEL
from helium.models import HeliumSynthesis

__all__ = [
    "HELIUM_RUNTIME",
    "HeliumSynthesis",
    "MockLLMClient",
    "ModalLLMClient",
    "REPORT_MODEL",
    "diagnose",
    "get_client",
]


def __getattr__(name: str):
    if name in {"MockLLMClient", "ModalLLMClient", "get_client"}:
        from helium.client import MockLLMClient, ModalLLMClient, get_client

        return {
            "MockLLMClient": MockLLMClient,
            "ModalLLMClient": ModalLLMClient,
            "get_client": get_client,
        }[name]
    if name == "diagnose":
        from helium.engine import diagnose

        return diagnose
    raise AttributeError(f"module 'helium' has no attribute {name!r}")
