# Nitrogen — Qwen3-VL 30B (shared B300)

**Status:** host only. Downloads and runs `Qwen/Qwen3-VL-30B-A3B-Instruct` on the **same** Modal replica as Helium. Callers own prompts.

Nitrogen is CoHERence Z=7. It is **not** Helium. It does not write `diagnosis` / `remediation`. It does not score.

---

## 1. Layout

| Z | Folder | Role |
|---|--------|------|
| 2 | `helium/` | Report LLM + **shared** `HeliumGPU` box |
| 7 | `nitrogen/` | This VL host (client + constants) |

GPU methods live on `HeliumGPU` in `helium/modal_app.py` so we do **not** start a second `gpu="B300"`.

---

## 2. What Nitrogen is / is not

**Is**

- Download + load of Qwen3-VL-30B-A3B onto `helium-hf-cache`
- `nitrogen_complete(system, user, image_b64=None)` raw text out
- Same container / instance as Helium

**Is not**

- Helium `diagnose`
- Hydrogen
- Prompt engineering (Dev 2 / whoever calls it)

---

## 3. Call

```
from nitrogen import ModalVLClient, VISION_MODEL

text = ModalVLClient().complete(system, user, image_b64=None)
```

Tests: `MockVLClient`. No live B300 in pytest.

---

## 4. Pull weights (B300, not the laptop)

From repo root:

```bash
modal run helium/modal_app.py::pull_nitrogen
```

First run downloads ~62 GB into the Modal HF volume, then loads the model (~8 GiB KV, `max_num_seqs=8`, `gpu_memory_utilization=0.65` so it fits beside Helium). Later runs reuse the volume.

One container (`max_containers=1`). Helium and Nitrogen generate under one lock — they wait their turn on the same B300.

Helium `complete` still loads Qwen 27B on enter. Nitrogen loads **lazily** on `load_nitrogen` / first `nitrogen_complete` so a Helium-only smoke does not pull 30B.
