# Helium — Report LLM (Modal, B300)

**Status:** v1 done. `helium.diagnose` + mock tests + live B300. Default runtime is **`deployed`** (`min_containers=1`). `diagnose()` does not change.

Helium is CoHERence module Z=2. It writes **one diagnosis and one remediation** from the **whole** Hydrogen report.

It does not run analyzers. Text, vision, accessibility, color, and interaction evidence are produced **upstream** and supplied through the `HydrogenReport`; Hydrogen computes the fairness score and ranked findings from the relevant measured outcomes.

Helium’s job is to take those evidence-backed results and **explain the overall problem coherently** — not to emit one LLM opinion per finding.

---

## 1. Layout

| Z | Folder | Role |
|---|--------|------|
| 1 | `hydrogen/` | Score + ranked findings (done) |
| 2 | `helium/` | Report synthesis LLM (this doc) |
| 3 | `lithium/` | FastAPI (later) |
| 4 | `beryllium/` | Job runner, `n_trials` (later) |

Code and this doc live in `helium/`.

---

## 2. What Helium is / is not

**Is**

- The writer of report-level `diagnosis` and `remediation`.
- A synthesizer: it **considers** every evidence stream on the report, then writes **one** coherent story. It does not dump every row.
- One LLM on Modal (`gpu="B300"`). Other team models may share that replica; they are **not** Helium APIs.

**Is not**

- Text / vision / color / a11y test runners. No `helium.extra_*`.
- The fairness score. Must not change `overall_fairness_score`, `score_status`, `scoring_policy`, or disparity numbers.
- A persona. Constraints and evidence only (`docs/idea-brief.md`).
- A causation claim when `attribution_status = UNRESOLVED` on the rows it cites.

---

## 3. Public call surface

### `helium.diagnose`  ← **only entry**

| | Name | Type |
|---|------|------|
| **IN** | `report` | `HydrogenReport` |
| **OUT** | `report` | `HydrogenReport` |

Sets `analyst = "helium"`. Fills report-level `diagnosis` and `remediation` (empty strings from Hydrogen).

```
hydrogen.evaluate(bundle)  →  HydrogenReport
        │
        │  HydrogenReport is the assembled contract:
        │    Hydrogen-owned: score, disparities, ranking, breakdown
        │    Dev-2-owned (packaged, not authored by Hydrogen):
        │      word / visual / color / a11y findings
        │    Dev-1-owned (packaged): interaction / telemetry
        │    Helium-owned (empty until diagnose): diagnosis, remediation
        ▼
helium.diagnose(report)
        │
        ▼
HydrogenReport
  score unchanged
  diagnosis + remediation filled
```

---

## 4. Input: assembled `HydrogenReport` (ownership)

Helium receives the **full** `HydrogenReport`. Hydrogen **packages** the contract; it does **not** generate Dev 1/Dev 2 observations.

| Slice | Owner | Helium sees |
|-------|--------|-------------|
| `overall_fairness_score`, `breakdown`, `disparities`, finding **rank** | **Hydrogen** | e.g. completion gap = 28 pp |
| Word / visual / color / a11y findings | **Dev 2** (packaged on the report) | e.g. ambiguous instruction; low visual prominence; 14 keyboard steps |
| Interaction / telemetry | **Dev 1** (packaged on the report) | e.g. 3 additional errors |
| `diagnosis`, `remediation` | **Helium** (empty in) | written on the way out |

No second “packs” payload. **No screenshot.** Helium is text-only: JSON report in, JSON synthesis out.

Helium **considers all streams that are present**. It **does not** have to mention every row. Prioritize evidence that bears on the **strongest findings** and the **observed disparity**. A two-cause diagnosis is better than an evidence dump.

---

## 5. Output (synthesis, not a list of extras)

Helium writes **two report-level strings** (Hydrogen leaves them `""`):

| Field | Type | Who |
|-------|------|-----|
| `diagnosis` | `str` | Helium |
| `remediation` | `str` | Helium |
| `analyst` | `"helium"` | Helium |

Per-finding `diagnosis` / `remediation_diff` stay `""` in helium-v1 unless we add that later.

**Forbidden to mutate:** `overall_fairness_score`, `score_status`, `scoring_policy`, `disparities`, `breakdown`, `findings` metadata (`attribution_status`, `affected_profiles`, ids, severities).

JSON the model must emit (schema-locked):

```
HeliumSynthesis
  diagnosis: str
  remediation: str
```

---

## 6. Worked example

**IN** (what Helium reads — already on the Hydrogen report)

```
Hydrogen:
  completion gap = 28 pp

Text Analyzer:
  instruction is ambiguous

Vision Analyzer:
  primary action has low visual prominence

A11Y:
  keyboard navigation requires 14 steps

Interaction:
  constrained profile made 3 additional errors
```

**CALL** `helium.diagnose(report)`

**OUT**

```
Diagnosis:
The constrained interaction path has substantially lower
completion and requires additional navigation and errors.
The interface also presents the primary action with low
visual prominence and uses ambiguous instructions.

Remediation:
Increase prominence of the primary action and clarify
the instruction.
```

That is **one** combined diagnosis, not four (or fifteen) mini-reports. It weaves the gap with the **relevant** analyzer rows. It does not list every extra click. It does not say the instruction **caused** the 28 pp unless `attribution_status = RESOLVED` on a join Dev 2 actually sent.

---

## 7. Prompt policy

1. Use only the Hydrogen report. No extra web search, no invented WCAG.
2. Consider all available evidence streams, but **prioritize** what is relevant to the strongest findings and the observed disparity. Do **not** mention every row.
3. Constraints, not identities.
4. `UNRESOLVED`: state facts side by side; do not assert cause.
5. Do not invent or change the fairness integer; quoting the given gap (e.g. 28 pp) is allowed.
6. Short paragraphs. No chain-of-thought in the visible strings.

---

## 8. Modal / GPU

Catalog UI may lock **H100**. Helium uses a **custom app**: `@app.cls(gpu="B300")`, CUDA **13.1+**.

| | helium-v1 |
|--|-----------|
| Report model | `helium.REPORT_MODEL` = **`Qwen/Qwen3.6-27B`**. **Text only. No vision.** |
| Live client | `ModalLLMClient` / `get_client()`. Tests pass `MockLLMClient`. |
| Runtime | `helium.runtime.complete_on_gpu`. Default **`deployed`** (`min_containers=1`). |
| Other models on the same B300 | Allowed for **other teammates** (not Helium calls). One replica; do not start four B300 functions. |
| KV | `kv_cache_memory_bytes` = **8 GiB**, `max_num_seqs=8`, `max_model_len=8192`. |
| Structured out | JSON schema `HeliumSynthesis` |

Same `modal run` process, two machines in it:

- **CPU (local):** `hydrogen.evaluate` then `helium.diagnose` (prompt + parse). Hydrogen never loads on the GPU.
- **GPU (one B300):** `HeliumGPU.complete`. Other team models load on **this same class / replica** (Helium KV is 8 GiB). Do **not** add another `@app.cls(gpu="B300")`.

`diagnose(report)` builds the prompt locally in the §6 shape (Hydrogen gap + analyzer facts **with `element_selector`**), then `client.complete(system, user)`. The GPU worker is a dumb completer. During `modal run`, reuse the live app — do not start a second one. The model must emit the §6 report (issues + UI suggestions), naming the actual controls, not a dump of finding ids or score fields.

Keep the replica up (do not rewrite `diagnose`):

```bash
modal deploy helium/modal_app.py
```

`min_containers=1` is set on `HeliumGPU`. First deploy still loads all engines once; later calls skip that boot.

Swapping the checkpoint is still `helium.REPORT_MODEL` only. v1 does **not** take screenshots. Hydrogen stays on CPU.

---

## 9. Downstream

| Call | Notes |
|------|--------|
| `lithium.create_report` | `hydrogen.evaluate` then `helium.diagnose` |
| `beryllium.run_pipeline` | Owns `n_trials`. Helium never sees N |

---

## 10. Invariants

1. Score path is Hydrogen-only.
2. Helium has **one** public call: `diagnose`.
3. Diagnosis is **one** report-level synthesis, not per-finding opinions. It considers all streams; it need not cite every row.
4. `UNRESOLVED` stays unresolved.
5. Tests use a **mock** LLM. No live B300 in CI.

---

## 11. To add or change later

| Later | How |
|-------|-----|
| Scale to zero again | `min_containers=0` + redeploy |
| Per-finding `diagnosis` / `remediation_diff` | Extra keys on `HeliumSynthesis` |
| Screenshots in Helium | **Not in v1.** Would need a multimodal `REPORT_MODEL`. |
| Swap report weights | Change `helium.REPORT_MODEL` only |
| Streaming to the UI | Lithium SSE |
| H100 fallback | Only if the chosen `REPORT_MODEL` fits ~80 GB **alone**; the 4-model mix does not |

---

## 12. Folder (now)

```
helium/
  sub-arch.md
  __init__.py
  constants.py
  models.py
  prompt.py
  example.py
  client.py
  runtime.py
  engine.py
  modal_app.py
```

Public:

```
helium.diagnose
helium.REPORT_MODEL
helium.HELIUM_RUNTIME
helium.get_client
```

Tests: `tests/test_helium.py` with `MockLLMClient`. No live B300 in pytest.
