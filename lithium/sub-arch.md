# Lithium — FastAPI gateway

**Status:** v1. `lithium.create_report` is the public call. HTTP wraps it and `beryllium.run_pipeline`.

Lithium is CoHERence Z=3. It is the HTTP edge. It does not score.

---

## 1. Layout

| Z | Folder | Role |
|---|--------|------|
| 1 | `hydrogen/` | Score |
| 2 | `helium/` | Diagnosis |
| 3 | `lithium/` | This gateway |
| 4 | `beryllium/` | Job runner (`n_trials`) |

---

## 2. What Lithium is / is not

**Is**

- `lithium.create_report(payload, report_id)` → Contract 3 JSON (`HydrogenReport`).
- HTTP for that call and for capture jobs.
- The place `n_trials` arrives from a client, then is handed to Beryllium.

**Is not**

- A second fairness engine. `overall_fairness_score` is Hydrogen's.
- A mapper of `null` → `100`. Missing evidence stays `null` plus `score_status`.

---

## 3. `lithium.create_report`

| | Name | Type |
|--|------|------|
| **IN** | `payload` | Contract 2 dict or `EvidenceBundle` |
| **IN** | `report_id` | `str` |
| **IN** | `diagnose` | default `True` |
| **OUT** | `HydrogenReport` | Contract 3 |

```
hydrogen.evaluate(bundle)  →  HydrogenReport
        │
        │  diagnose=True (default)
        ▼
helium.diagnose(report)
        │
        ▼
Contract 3 JSON
```

Tests pass `helium.client.MockLLMClient` or `diagnose=False`. No live B300 in pytest.

---

## 4. HTTP

```
uvicorn lithium.app:app --reload --port 8000
```

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | liveness |
| GET | `/profiles` | `boron.list_profiles()` |
| POST | `/reports` | body is Contract 2 + `report_id` + `diagnose` |
| POST | `/jobs` | 202; runs `beryllium.run_pipeline` in a background task |
| GET | `/jobs/{job_id}` | status; `report` when done |
| GET | `/jobs/{job_id}/report` | Contract 3 only; 409 until done |
| GET | `/jobs/{job_id}/preview` | latest capture PNG (path must sit under `data/sessions`) |

HTTP `url` must be `http`/`https`. `file:` and link-local metadata hosts are rejected. Client `out_root` is ignored. `job_id` is a slug. If Helium fails after Hydrogen has scored, the job stays `done` with the score and `warning`.

`POST /jobs` body: `url`, `n_trials` (default 1), `success_selector`, `steps` or `goal`, optional `profile_ids`, `diagnose` (default true).

A `goal` without `steps` constructs `nitrogen.ModalVLClient` at the gateway. Scripted `steps` do not.

---

## 5. Invariants

1. Must not recompute the score.
2. `INSUFFICIENT_EVIDENCE` keeps `overall_fairness_score: null`.
3. Finding `diagnosis` / `remediation_diff` stay empty; Helium writes report-level `diagnosis` / `remediation`.
4. In-process job store. Restart loses queued jobs.
