# Beryllium — Pipeline orchestrator

**Status:** v1. `beryllium.run_pipeline` is the public call.

Beryllium is CoHERence Z=4. It owns **`n_trials`** and the handoff **Boron → Carbon → Hydrogen**. Helium is optional.

---

## 1. Layout

| Z | Folder | Role |
|---|--------|------|
| 1 | `hydrogen/` | Score |
| 2 | `helium/` | Diagnosis (optional here) |
| 3 | `lithium/` | HTTP |
| 4 | `beryllium/` | This runner |
| 5 | `boron/` | Capture (`run_suite`) |
| 6 | `carbon/` | Rules + disparities |

---

## 2. What Beryllium is / is not

**Is**

- The owner of `n_trials`. That value becomes `boron.run_suite(..., runs=N)`.
- The folder of one-session-per-profile telemetry (`rate = successes / N`) before Carbon sees a bool `task_completed`.
- A caller of Carbon's obvious APIs (`evaluate_session_artifacts`, `attribute_from_failures`, `analyze_sessions`) with no extra kwargs.
- A caller of `hydrogen.evaluate`. It does not recompute the score.

**Is not**

- A second score.
- A prompt owner (Nitrogen / Helium callers stay at those modules).
- Lithium. HTTP lives in `lithium/`.

---

## 3. `beryllium.run_pipeline`

| | Name | Type |
|--|------|------|
| **IN** | `job_id` | `str` (Hydrogen `report_id`) |
| **IN** | `url` | capture target, **or** |
| **IN** | `contract2_path` | skip capture; already Contract 2 JSON |
| **IN** | `n_trials` | `int >= 1`, default `1` |
| **IN** | `success_selector`, `steps` \| `goal` | Boron's task shape |
| **IN** | `diagnose` | default `False`; Lithium turns this on |
| **OUT** | `HydrogenReport` | Hydrogen-owned score; Helium text only if `diagnose` |

Hydrogen never receives `n_trials`. Helium never receives `n_trials`.

`run_suite` is the capture call. Profiles stay sequential (Boron's timing rule).

```python
from beryllium import run_pipeline

report = run_pipeline(
    "job_1",
    url="https://example.com/checkout",
    n_trials=3,
    success_selector="#order-confirmed",
    steps=["#fake-button", "#submit-order"],
)
```

Skip the browser when Contract 2 is already on disk:

```python
run_pipeline("job_1", contract2_path="data/contract2.json")
```

---

## 4. Invariants

1. Score path is Hydrogen-only.
2. Default N=1.
3. `profiles_tested` is the request list (baseline prepended if missing), never inferred from disparities.
4. Tests do not call a live B300. Pass `diagnose=False` or `helium.client.MockLLMClient`.
