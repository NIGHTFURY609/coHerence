"""Oxygen — Dev 2 text. GPU default is Qwen3.5-9B on the shared B300."""

# Groq fallback (often blocked from this network).
TEXT_MODEL = "openai/gpt-oss-20b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Same replica as Helium/Nitrogen. 4 GiB KV, max_num_seqs=8 (not 1024).
GPU_TEXT_MODEL = "Qwen/Qwen3.5-9B"
