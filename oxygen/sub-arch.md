# Oxygen — Dev 2 text (Qwen3.5-9B on the shared B300)

**Status:** Groq `gpt-oss-20b` is optional and currently unreachable from this network (SSL timeout). Default is **`Qwen/Qwen3.5-9B`** on the **same** Modal replica as Helium and Nitrogen.

Oxygen is CoHERence Z=8. It does not write Helium `diagnosis` / `remediation`. It does not score. Callers own prompts.

---

## 1. Same card, take turns

One container (`max_containers=1`). `@modal.enter` loads all three:

| Slot | Model | KV | `max_num_seqs` | util ceiling |
|------|--------|----|----------------|--------------|
| Helium | Qwen3.6-27B | 8 GiB | 8 | 0.26 |
| Nitrogen | Qwen3-VL-30B-A3B | 8 GiB | 8 | 0.65 of remaining |
| Oxygen | Qwen3.5-9B | **4 GiB** | **8** | 0.35 of remaining |

Do **not** use vLLM’s default 0.92 util or 1024 seqs. Each generate holds `self._turn`.

---

## 2. Call

```python
from oxygen import GpuTextClient, GPU_TEXT_MODEL

text = GpuTextClient().complete(system, user)
```

Tests: `MockTextClient`. No live B300/Groq in pytest.

Warm all three (download 9B + load):

```bash
modal run helium/modal_app.py::warm_all
```

---

## 3. Groq fallback

`GroqTextClient` + `GROQ_API_KEY` still exists. Use it only if Groq is reachable. Default for Dev 2 is the GPU 9B.
