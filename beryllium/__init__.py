"""Beryllium (Z=4): pipeline orchestrator. Owns n_trials."""

__all__ = ["run_pipeline"]


def __getattr__(name: str):
    if name == "run_pipeline":
        from beryllium.pipeline import run_pipeline

        return run_pipeline
    raise AttributeError(f"module 'beryllium' has no attribute {name!r}")
