"""Oxygen (Z=8): Dev 2 text. GPU Qwen3.5-9B on the shared B300; Groq optional."""

from oxygen.constants import GPU_TEXT_MODEL, TEXT_MODEL

__all__ = [
    "GPU_TEXT_MODEL",
    "TEXT_MODEL",
    "GpuTextClient",
    "GroqTextClient",
    "MockTextClient",
    "get_client",
]


def __getattr__(name: str):
    if name in {"GpuTextClient", "GroqTextClient", "MockTextClient", "get_client"}:
        from oxygen.client import GpuTextClient, GroqTextClient, MockTextClient

        if name == "get_client":
            return get_client
        return {
            "GpuTextClient": GpuTextClient,
            "GroqTextClient": GroqTextClient,
            "MockTextClient": MockTextClient,
        }[name]
    raise AttributeError(f"module 'oxygen' has no attribute {name!r}")


def get_client():
    """GPU on the shared B300. Tests pass MockTextClient."""
    from oxygen.client import GpuTextClient

    return GpuTextClient()
