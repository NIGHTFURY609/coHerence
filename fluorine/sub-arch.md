# Fluorine — Gemma 4 26B-A4B-IT (shared B300)

**Status:** fourth engine on the Helium replica. `google/gemma-4-26B-A4B-it` (MoE, ~3.8B active, Apache-2.0). Callers own prompts.

Fluorine is CoHERence Z=9. It is **not** Helium and **not** Nitrogen. Both Nitrogen (Qwen VL 30B) and Fluorine (Gemma VL) can sit on the card; they take turns.

---

## 1. VRAM (with Helium + Nitrogen + Oxygen already resident)

| | |
|--|--|
| Weights on disk | ~51.6 GB |
| KV | **8 GiB** |
| `max_num_seqs` | **8** (not 1024) |
| util ceiling | **0.32** of the card, also capped to remaining free |

Do not use vLLM 0.92 util. ~30 GiB should remain after this load.

---

## 2. Call

```python
from fluorine import ModalVLClient

text = ModalVLClient().complete(system, user, image_b64=None)
```

Tests: `MockVLClient`.

Load all four:

```bash
modal run helium/modal_app.py::warm_all
```
