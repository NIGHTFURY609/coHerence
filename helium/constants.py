"""Helium-v1. Swap REPORT_MODEL or HELIUM_RUNTIME without changing diagnose()."""

REPORT_MODEL = "Qwen/Qwen3.6-27B"
MAX_MODEL_LEN = 8192
GPU = "B300"
# Leave room on the B300 for other models. 0.42 ≈ 110 GiB of 268, not 187 GiB KV.
GPU_MEMORY_UTILIZATION = 0.42

MODAL_APP_NAME = "coherence-helium"
HELIUM_CLS_NAME = "HeliumGPU"

# ephemeral: each live call boots a container (cold start). v1 default.
# deployed:  Cls.from_name after `modal deploy helium/modal_app.py`.
# Env HELIUM_RUNTIME overrides this at call time (see helium.runtime).
HELIUM_RUNTIME = "ephemeral"
