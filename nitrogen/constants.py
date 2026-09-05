"""Nitrogen — Qwen3-VL 30B on the shared Helium B300. No Helium prompts here."""

VISION_MODEL = "Qwen/Qwen3-VL-30B-A3B-Instruct"
KV_CACHE_GIB = 8
MAX_NUM_SEQS = 8
# Second vLLM on the same B300. Must be < free/total after Helium (~206/268).
GPU_MEMORY_UTILIZATION = 0.65
