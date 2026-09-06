"""Beryllium (Z=4): pipeline orchestrator. Owns n_trials."""

__all__ = ["run_pipeline", "run_screenshot_pipeline"]


def __getattr__(name: str):
    if name in __all__:
        import beryllium.pipeline as pipeline

        return getattr(pipeline, name)
    raise AttributeError(f"module 'beryllium' has no attribute {name!r}")
