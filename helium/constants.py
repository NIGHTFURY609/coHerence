"""Helium-v1. Swap REPORT_MODEL or HELIUM_RUNTIME without changing diagnose()."""

REPORT_MODEL = "Qwen/Qwen3.6-27B"
MAX_MODEL_LEN = 8192
GPU = "B300"
# Helium KV pool. Weights stay ~52 GiB; this is not model quality.
KV_CACHE_GIB = 8
KV_CACHE_MEMORY_BYTES = KV_CACHE_GIB * 1024**3
# Qwen3.6 GDN/Mamba: one cache block per in-flight sequence. 8 GiB KV
# only has ~167 blocks; vLLM default max_num_seqs=1024 then fails.
# Helium is 1–2 jobs. Do not raise KV to satisfy the 1024 default.
MAX_NUM_SEQS = 8
# vLLM still checks free >= util * *total* card, even with kv_cache_memory_bytes.
# Helium loads first on an empty GPU. 0.26 ≈ weights + 8 GiB KV.
GPU_MEMORY_UTILIZATION = 0.26
# Nitrogen loads second (Helium already resident). 0.92 of 268 GiB is 246;
# only ~206 GiB is free then. 0.65 * 268 ≈ 174 < 206.
NITROGEN_GPU_MEMORY_UTILIZATION = 0.65
# Third engine: Qwen3.5-9B text for Dev 2. ~19 GiB weights + 4 GiB KV.
# Ceiling 0.35 of the *card*; _share_gpu_utilization also caps to free memory.
OXYGEN_MODEL = "Qwen/Qwen3.5-9B"
OXYGEN_KV_CACHE_GIB = 4
OXYGEN_KV_CACHE_MEMORY_BYTES = OXYGEN_KV_CACHE_GIB * 1024**3
OXYGEN_GPU_MEMORY_UTILIZATION = 0.35

MODAL_APP_NAME = "coherence-helium"
HELIUM_CLS_NAME = "HeliumGPU"

# ephemeral: each live call boots a container (cold start). v1 default.
# deployed:  Cls.from_name after `modal deploy helium/modal_app.py`.
# Env HELIUM_RUNTIME overrides this at call time (see helium.runtime).
HELIUM_RUNTIME = "ephemeral"
