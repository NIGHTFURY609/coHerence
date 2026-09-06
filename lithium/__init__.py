"""Lithium (Z=3): FastAPI gateway. create_report is the public call."""

__all__ = ["app", "create_report"]


def __getattr__(name: str):
    if name == "create_report":
        from lithium.reports import create_report

        return create_report
    if name == "app":
        from lithium.app import app

        return app
    raise AttributeError(f"module 'lithium' has no attribute {name!r}")
