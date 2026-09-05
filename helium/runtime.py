"""GPU lookup. diagnose() and ModalLLMClient do not branch on cold vs warm.

Flip helium.constants.HELIUM_RUNTIME (or env HELIUM_RUNTIME):
  ephemeral — app.run() per call; container boots each time (v1 default)
  deployed  — Cls.from_name; no boot if a replica is already up

Never import helium.modal_app while a live `modal run` is already up.
That import is a second module/App and makes Modal mount PythonPackage:helium
on the GPU, which then pulls hydrogen. Hydrogen stays on CPU.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from helium.constants import HELIUM_CLS_NAME, MODAL_APP_NAME

_VALID_RUNTIMES = frozenset({"ephemeral", "deployed"})


def current_runtime() -> str:
    from helium.constants import HELIUM_RUNTIME

    value = os.environ.get("HELIUM_RUNTIME", HELIUM_RUNTIME).strip().lower()
    if value not in _VALID_RUNTIMES:
        raise ValueError(
            f"Unknown HELIUM_RUNTIME={value!r}; use 'ephemeral' or 'deployed'"
        )
    return value


def complete_on_gpu(system: str, user: str) -> str:
    if current_runtime() == "deployed":
        return _deployed(system, user)
    return _ephemeral(system, user)


def _deployed(system: str, user: str) -> str:
    import modal

    cls = modal.Cls.from_name(MODAL_APP_NAME, HELIUM_CLS_NAME)
    return cls().complete.remote(system, user)


def _live_gpu_cls() -> Any | None:
    """HeliumGPU from the already-running `modal run` app, if any.

    `modal run helium/modal_app.py` loads the file as one module. Importing
    `helium.modal_app` again creates a second App. Prefer the live one.
    """
    for mod in list(sys.modules.values()):
        gpu = getattr(mod, "HeliumGPU", None)
        app = getattr(mod, "app", None)
        if gpu is None or app is None:
            continue
        if getattr(app, "name", None) != MODAL_APP_NAME:
            continue
        if getattr(app, "app_id", None):
            return gpu
    return None


def _ephemeral(system: str, user: str) -> str:
    """Cold-start path. Reuses the running app during `modal run`."""
    gpu = _live_gpu_cls()
    if gpu is not None:
        return gpu().complete.remote(system, user)

    import modal

    from helium.modal_app import HeliumGPU, app

    def _call() -> str:
        return HeliumGPU().complete.remote(system, user)

    if app.app_id:
        return _call()
    with modal.enable_output():
        with app.run():
            return _call()
