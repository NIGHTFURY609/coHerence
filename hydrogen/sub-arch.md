# Hydrogen — Mathematical Engine

**Status:** v1 implemented. Public calls match this doc.

Hydrogen is the first CoHERence module (periodic-table naming, Z=1). It is Dev 3’s **deterministic fairness layer**: turn Dev 2 evidence into a score and ranked findings. It does not call an LLM.

Hydrogen answers **what the measured outcomes are**. Helium later answers **what they might mean**. The integer score is never owned by an LLM.

---

## 1. Naming scheme and layout

Modules are **full lowercase element names**, in atomic-number order, as we add them.

This scheme **replaces** the old Dev 3 paths `src/api/`, `src/llm/`, and `src/orchestrator/`. Do not keep both.

| Z | Folder | Role | When |
|---|--------|------|------|
| 1 | `hydrogen/` | Mathematical engine (this doc + later code) | now |
| 2 | `helium/` | LLM analyst (Modal) | after Hydrogen is locked |
| 3 | `lithium/` | FastAPI gateway | after Helium’s I/O is locked |
| 4 | `beryllium/` | Pipeline orchestrator | integration |

Public call names are always `element.verb_object`. Later code should match these names exactly so Lithium and Helium can import them without renaming.

Architecture and implementation for this module both live in `hydrogen/`. No parallel `src/hydrogen/`.

---

## 2. What Hydrogen is / is not

**Is**

- The only place `overall_fairness_score` is computed.
- The place findings are **created and ranked** from evidence.
- A validator of disparity *shape and direction* before scoring (it does not recompute Dev 2’s ratio).
- A pure function of Contract 2. Same input → same output.

**Is not**

- Dev 2’s rule engine (WCAG, contrast, touch-target geometry, Flesch-Kincaid). Hydrogen does not re-measure the UI.
- Dev 1’s browser / telemetry collector.
- The LLM. Hydrogen never writes `diagnosis` or `remediation_diff`.
- A causation engine. It does not claim that a finding *caused* a disparity.
- A discrimination / intent judge.
- Persona / stereotype logic. It scores **constraints and group outcomes**, per `docs/idea-brief.md`.

---

## 3. Public call surface

These four calls are the engine. Validation is **internal** to `parse_contract2` / `score_fairness`, not a fifth public API.

### 3.1 `hydrogen.parse_contract2`

Normalizes Dev 2’s JSON into Hydrogen’s input object and runs shape checks.

| | Name | Type |
|---|------|------|
| **IN** | `contract2_payload` | `dict` (Contract 2 JSON) |
| **OUT** | `bundle` | `EvidenceBundle` |

### 3.2 `hydrogen.score_fairness`

Validates disparity semantics, then computes the 0–100 fairness score and the breakdown used to justify it.

| | Name | Type |
|---|------|------|
| **IN** | `bundle` | `EvidenceBundle` |
| **OUT** | `breakdown` | `FairnessBreakdown` |

### 3.3 `hydrogen.rank_findings`

Turns evidence rows into ordered finding shells. Does not explain, patch, or assert cause.

| | Name | Type |
|---|------|------|
| **IN** | `bundle` | `EvidenceBundle` |
| **IN** | `breakdown` | `FairnessBreakdown \| None` (optional) |
| **OUT** | `findings` | `list[FindingDraft]` |

`breakdown` is optional so this call stays usable in tests. If omitted, sort by severity only. `hydrogen.evaluate` always passes the breakdown from `score_fairness`. Bottleneck-boost sorting only applies to findings with `attribution_status = RESOLVED`.

### 3.4 `hydrogen.evaluate`  ← **main entry**

The call Lithium (API) and Beryllium (orchestrator) will use.

| | Name | Type |
|---|------|------|
| **IN** | `bundle` | `EvidenceBundle` |
| **IN** | `report_id` | `str` |
| **OUT** | `report` | `HydrogenReport` |

Internal order:

```
Dev 2 JSON
    │
    ▼
hydrogen.parse_contract2
    │  (shape + direction checks)
    ▼
EvidenceBundle
    │
    ├──────────────────────────────┐
    ▼                              │
hydrogen.score_fairness            │
    │  validate rows               │
    │  absolute gap × weight, min  │
    │  worst-group min             │
    ▼                              ▼
FairnessBreakdown          hydrogen.rank_findings(bundle, breakdown)
    │                              │
    └──────────────┬───────────────┘
                   ▼
            hydrogen.evaluate
                   ▼
             HydrogenReport
        (score owned here; diagnosis empty)
                   │
        later: helium.diagnose(report)
                   ▼
          Contract 3 FinalReportResponse
```

---

## 4. Named inputs

### `EvidenceBundle`  (Hydrogen’s input)

| Field | From | Notes |
|-------|------|-------|
| `evidence` | Contract 2 `evidence` | `list[EvidenceRecord]` |
| `disparities` | Contract 2 `disparities` | `list[Disparity]` |
| `target_url` | optional, default `""` | Contract 2 example omits this; Lithium may inject it |
| `profiles_tested` | optional, default `[]` | **Trust this field only.** If missing or empty, leave `[]`. Do **not** infer the tested population from `disadvantaged_group` — that under-reports profiles that were tested and had no disparity. |

### `EvidenceRecord`

| Field | Notes |
|-------|-------|
| `element_selector` | CSS selector of the design element |
| `bounding_box` | optional `{x, y, width, height}` |
| `rule_id` | Dev 2 rule, e.g. `TOUCH_TARGET_TOO_SMALL` |
| `severity` | `CRITICAL` \| `WARNING` \| `INFO` |
| `metric_value` | observed, e.g. `"24x22px"` |
| `recommended_min` | optional, e.g. `"48x48px"` |
| `affected_profiles` | optional `list[str]`. **Join key.** If Dev 2 sends a non-empty list, attribution is `RESOLVED`. If absent or empty, attribution is `UNRESOLVED` — Hydrogen does not guess. |

Hydrogen does not independently verify these measurements.

### `Disparity`

| Field | Notes |
|-------|-------|
| `metric` | e.g. `task_completion_rate` |
| `baseline_value` | default-user outcome |
| `constrained_value` | constrained-profile outcome |
| `disparity_ratio` | **already computed and direction-normalized by Dev 2** |
| `disadvantaged_group` | e.g. `motor_impaired` |

Required meaning of `disparity_ratio` (Dev 2 contract, Hydrogen enforces):

```
1.0  = equal outcome
> 1.0 = constrained group did worse
< 1.0 = constrained group did better
```

Hydrogen **does not** recompute the ratio, and **does not score from the ratio alone**. The integer uses `baseline_value` and `constrained_value` (absolute gap). `disparity_ratio` is validated and passed through for Helium; two 2× ratios can be completely different situations (see §6.2).

Ratio `< 1` does not raise the score (no bonus for a group doing better).

---

## 5. Named outputs

### `FairnessBreakdown`  (from `hydrogen.score_fairness`)

| Field | Type | Meaning |
|-------|------|---------|
| `score_status` | `VALID` \| `PARTIAL` \| `INSUFFICIENT_EVIDENCE` | see §6.3. v1 emits `VALID` or `INSUFFICIENT_EVIDENCE` |
| `scored` | `bool` | `true` iff `score_status = VALID` |
| `overall_fairness_score` | `int` 0–100, or `null` | **the** report score when scored. `null` otherwise |
| `outcome_equity` | `float` 0–100, or `null` | min **weighted absolute-gap** equity |
| `bottleneck_metric` | `str` | metric of that min; `""` if not scored |
| `bottleneck_group` | `str` | group of that min; `""` if not scored |
| `bottleneck_baseline` | `float \| null` | baseline of that row |
| `bottleneck_constrained` | `float \| null` | constrained value of that row |
| `bottleneck_abs_gap` | `float` | absolute extra harm of that row |
| `max_disparity_ratio` | `float` | that row’s ratio (reported, **not** the score driver); `0` if not scored |
| `baseline_poor` | `bool` | `true` when the bottleneck baseline is poor **according to Hydrogen policy** (`POOR_BASELINE`). Not an objective claim that the product is broken for everybody. |
| `skipped_metrics` | `list[str]` | malformed, out-of-range, or unknown metric names |
| `collapsed_metrics` | `list[str]` | valid rows dropped as aliases / same family (see §6.2.1) |
| `scoring_policy` | `str` | `"hydrogen-v1"` |

This integer is a **worst-group outcome-equity score**, not a claim that every aspect of fairness has been measured.

Evidence / linter hits do **not** change the score. They only rank findings.

### `FindingDraft`  (from `hydrogen.rank_findings`)

| Field | Type | Who fills it |
|-------|------|----------------|
| `id` | `str` | Hydrogen (`find_1`, `find_2`, …) |
| `title` | `str` | Hydrogen, from `rule_id` + selector. Descriptive, not causal |
| `severity` | `CRITICAL` \| `WARNING` \| `INFO` | copied from evidence |
| `affected_profiles` | `list[str]` | Dev 2 join key if present; else `[]` |
| `attribution_status` | `RESOLVED` \| `UNRESOLVED` | `RESOLVED` only when Dev 2 sent a non-empty `affected_profiles` |
| `rule_id` | `str` | copied |
| `element_selector` | `str` | copied |
| `diagnosis` | `str` | **always `""` here** |
| `remediation_diff` | `str` | **always `""` here** |

### `HydrogenReport`  (from `hydrogen.evaluate`)

This is Contract 3 **minus** LLM text. Helium will write into the same object.

| Field | Type | Source |
|-------|------|--------|
| `report_id` | `str` | argument to `evaluate` |
| `target_url` | `str` | `bundle.target_url` |
| `overall_fairness_score` | `int \| null` | `breakdown.overall_fairness_score` |
| `score_status` | enum | `breakdown.score_status` |
| `scoring_policy` | `str` | `"hydrogen-v1"` |
| `profiles_tested` | `list[str]` | `bundle.profiles_tested` as sent. Never inferred. |
| `disparities` | `list[Disparity]` | passed through unchanged |
| `findings` | `list[FindingDraft]` | ranked |
| `breakdown` | `FairnessBreakdown` | extra, for debugging / UI tooltips |
| `analyst` | `"hydrogen"` | so the frontend knows the report is pre-LLM |

If a downstream schema ever *requires* an integer, still do not send `100` for missing data. Send `null` plus `score_status`. Lithium may map that to the HTTP layer; it may not invent a 100.

---

## 6. Formula and policy (`hydrogen-v1`)

The brief asks *who the software works for*, not how many linter hits it has.

### 6.0 Internal validation (not a public call)

For each disparity row, keep it only if **all** of:

1. `metric` is a non-empty string in `METRIC_KIND`
2. `baseline_value` and `constrained_value` are finite numbers
3. Kind-specific bounds:
   - **rate** (`task_completion_rate`, `task_failure_rate`, `abandonment_rate`, `error_rate`): `0 ≤ value ≤ 1` for **both** baseline and constrained
   - **time / count** (ms, clicks, steps, `error_count`): `value ≥ 0` for both
4. `disparity_ratio` is present, finite, and `> 0`
5. `disadvantaged_group` is a non-empty string

Otherwise append the metric name (or `"<missing>"`) to `skipped_metrics` and drop the row.

Finite-but-out-of-range is a skip, not a clamp. Hydrogen does not rewrite Dev 2’s numbers. The score is **not** `f(ratio)`.

### 6.1 Why ratio-only is invalid

Both of these are “about 2×”:

| | Case A | Case B |
|---|--------|--------|
| Baseline completion | 90% | 10% |
| Constrained completion | 45% | 5% |
| `disparity_ratio` | 2.0 | 2.0 |
| Absolute gap | **45 pp** | **5 pp** |

They are not equivalent.

- **Case A:** the constrained group fails almost half the time while the default user mostly succeeds. That is an inclusion failure.
- **Case B:** the product is already failing for everybody. The constrained group is only 5 percentage points worse. That is a quality failure with a small extra gap.

A ratio-only curve would give both the same equity (~83). Hydrogen must not do that.

The integer is driven by **absolute extra harm** (`baseline_value` vs `constrained_value`). The ratio is kept on the report so Helium can still say “twice as likely,” but it does not set the score.

**v1 limitation (intentional):** 10 s → 20 s and 100 s → 110 s are the same 10 s `abs_gap`. Relative severity is lost. Helium still has `disparity_ratio` for that. Do not mix ratio back into the integer.

### 6.2 `GAP_REF` vs `METRIC_WEIGHT` (two different knobs)

Do not collapse these.

| Knob | Question it answers | Effect |
|------|---------------------|--------|
| `hydrogen.GAP_REF[metric]` | How large a gap is **maximum severity** (equity 0) for this metric? | Scales `abs_gap` → 0–100 equity **for that row** |
| `hydrogen.METRIC_WEIGHT[metric]` | How strongly does this metric’s equity move the **final** score? | After equity: `weighted = 100 − weight × (100 − equity)` |

A 30 s extra wait can already be “max severity” for time (`GAP_REF`) while still mattering less than a failed task (`METRIC_WEIGHT` 0.50 vs 1.00).

`GAP_REF` values are **Hydrogen policy thresholds**, not universal constants. `30000` ms, `10` extra errors, `20` extra clicks are chosen for this product, versioned as `"hydrogen-v1"`. Changing them requires a new policy string.

Direction (`hydrogen.METRIC_KIND`):

```
higher_better: abs_gap = max(baseline - constrained, 0)   # completion
lower_better:  abs_gap = max(constrained - baseline, 0)   # time, errors, clicks, steps
```

| Metric | Kind | `GAP_REF` (policy: gap → equity 0) | `METRIC_WEIGHT` |
|--------|------|-----------------------------------:|----------------:|
| `task_completion_rate` | higher_better | `1.0` (100 pp) | `1.00` |
| `task_failure_rate` | lower_better | `1.0` | `1.00` |
| `abandonment_rate` | lower_better | `1.0` | `1.00` |
| `task_completion_time` | lower_better | `30000` ms | `0.50` |
| `completion_time_ms` | lower_better | `30000` ms | `0.50` |
| `error_rate` | lower_better | `1.0` | `0.50` |
| `error_count` | lower_better | `10` extra errors | `0.50` |
| `dead_clicks` | lower_better | `10` extra | `0.25` |
| `total_clicks` | lower_better | `20` extra | `0.25` |
| `keyboard_nav_steps` | lower_better | `20` extra | `0.25` |

```
unit_gap          = min(abs_gap / GAP_REF[metric], 1)
equity_i          = 100 * (1 - unit_gap)
weighted_equity_i = 100 - METRIC_WEIGHT[metric] * (100 - equity_i)
```

Worked rates (weight 1.00):

| | abs_gap | equity | reading |
|---|---------|-------:|---------|
| Case A (90% vs 45%) | 0.45 | **55** | large inclusion gap |
| Case B (10% vs 5%) | 0.05 | **95** | small extra gap; baseline already poor |
| Checkout (100% vs 25%) | 0.75 | **25** | 75 pp lost |

### 6.2.1 One row per family (no alias / overlap double-count)

If Dev 2 sends both `task_completion_time` and `completion_time_ms`, that is one fact. Same for `error_rate` / `error_count`, and for completion / failure / abandonment (often `failure ≈ 1 − completion`).

`hydrogen.METRIC_FAMILY` — keep **one** scoring row per family, in this priority (first present after validation wins). The rest go to `collapsed_metrics`, not the `min()`.

| Family | Priority (keep first that exists) |
|--------|-----------------------------------|
| `outcome` | `task_completion_rate`, then `task_failure_rate`, then `abandonment_rate` |
| `time` | `completion_time_ms`, then `task_completion_time` |
| `errors` | `error_rate`, then `error_count` |
| `dead_clicks` | `dead_clicks` |
| `total_clicks` | `total_clicks` |
| `keyboard` | `keyboard_nav_steps` |

`dead_clicks`, `total_clicks`, and `keyboard_nav_steps` are **not** aliases of each other.

### 6.2.2 `baseline_poor` is a policy flag

`hydrogen.POOR_BASELINE_RATE = 0.5` (policy, not a law of nature).

```
higher_better rates: baseline_poor = (baseline < POOR_BASELINE_RATE)
lower_better rates:  baseline_poor = (baseline > 1 - POOR_BASELINE_RATE)
time / counts:       baseline_poor = false in v1 (no agreed “already slow for everyone” cutoff)
```

This means: **the Hydrogen policy considers the default-user outcome poor.** It does **not** mean “the product is broken for everybody.” Helium may use the flag; it must not treat it as an objective diagnosis. Hydrogen still writes no sentence.

Unknown metric names → `skipped_metrics`. All of the above are git constants. Helium never sets them.

### 6.3 Aggregate (worst weighted row wins)

```
eligible = validated rows after METRIC_FAMILY collapse (§6.2.1)
```

| Condition | `score_status` | `scored` | `overall_fairness_score` |
|-----------|----------------|----------|--------------------------|
| `eligible` is non-empty | `VALID` | `true` | `round(clamp(min(weighted_equity_i), 0, 100))` |
| no usable rows | `INSUFFICIENT_EVIDENCE` | `false` | `null` |

`PARTIAL` is reserved (not emitted in v1).

When `VALID`:

```
outcome_equity = min(weighted_equity_i)
bottleneck_*   = that row's metric, group, baseline, constrained, abs_gap, ratio
```

Do **not** emit 100 for missing data. An average is rejected: one excluded group must not disappear behind healthy groups.

### 6.4 Finding rank and attribution (not the score)

```
severity_rank = { CRITICAL: 0, WARNING: 1, INFO: 2 }
```

Sort:

1. `severity_rank`
2. If `breakdown` is present, `score_status = VALID`, **and** the finding is `RESOLVED` with `bottleneck_group` in `affected_profiles` — those come first within the same severity
3. Original evidence order

**Attribution (join key):**

Contract 2 has evidence and disparities as separate lists. There is no foreign key. Hydrogen must not invent one (no taxonomy table, no “CRITICAL gets every group”).

```
if evidence.affected_profiles is a non-empty list:
    FindingDraft.affected_profiles   = that list
    FindingDraft.attribution_status  = RESOLVED
else:
    FindingDraft.affected_profiles   = []
    FindingDraft.attribution_status  = UNRESOLVED
```

Unresolved is honest. Copying every disadvantaged group onto every CRITICAL finding would tag a contrast issue as motor-impaired and a touch-target issue as screen-reader — false attribution.

Titles stay descriptive (`TOUCH_TARGET_TOO_SMALL` on `button#submit-order`). They must not read as “this button caused the motor-impaired failure.” Helium may argue cause later.

### 6.5 Named constants (`hydrogen-v1`)

| Name | Proposed | Used by |
|------|----------|---------|
| `hydrogen.METRIC_KIND` | see §6.2 | `score_fairness` |
| `hydrogen.GAP_REF` | see §6.2 — **policy** max-severity gap | `score_fairness` |
| `hydrogen.METRIC_WEIGHT` | see §6.2 — influence on the final min | `score_fairness` |
| `hydrogen.METRIC_FAMILY` | see §6.2.1 | `score_fairness` |
| `hydrogen.POOR_BASELINE_RATE` | `0.5` (policy) | `baseline_poor` |
| `hydrogen.SEVERITY_ORDER` | `CRITICAL < WARNING < INFO` | `rank_findings` |
| `hydrogen.SCORING_POLICY` | `"hydrogen-v1"` | stamped on every report |

`hydrogen.RATIO_STEEPNESS` is **retired**. Do not score from `disparity_ratio`. Changing gap refs, weights, families, or `POOR_BASELINE_RATE` is a new `hydrogen-v2` string. Helium never sets them.

No barrier / linter penalty on the score.

---

## 7. Worked examples

### 7.1 Same ratio, different fairness (the 2× trap)

| | Case A | Case B |
|---|--------|--------|
| baseline / constrained | 0.90 / 0.45 | 0.10 / 0.05 |
| `disparity_ratio` | 2.0 | 2.0 |
| `abs_gap` | 0.45 | 0.05 |
| `baseline_poor` | `false` | `true` |
| `overall_fairness_score` | **55** | **95** |

Helium may still mention the 2× ratio. Hydrogen must not treat A and B as the same score.

### 7.2 Checkout button (100% vs 25%)

**IN** `bundle` (no join key from Dev 2)

```
evidence[0]:
  element_selector = "button#submit-order"
  rule_id          = "TOUCH_TARGET_TOO_SMALL"
  severity         = CRITICAL
  metric_value     = "24x22px"
  recommended_min  = "48x48px"
  affected_profiles = <absent>

disparities[0]:
  metric               = "task_completion_rate"
  baseline_value       = 1.0
  constrained_value    = 0.25
  disparity_ratio      = 4.0
  disadvantaged_group  = "motor_impaired"
```

**CALL** `hydrogen.evaluate(bundle, report_id="rep_9876")`

**OUT** `HydrogenReport` (expected)

| Field | Value |
|-------|--------|
| `overall_fairness_score` | `25` |
| `score_status` | `VALID` |
| `scoring_policy` | `"hydrogen-v1"` |
| `breakdown.outcome_equity` | `25` |
| `breakdown.bottleneck_metric` | `task_completion_rate` |
| `breakdown.bottleneck_group` | `motor_impaired` |
| `breakdown.bottleneck_abs_gap` | `0.75` |
| `breakdown.max_disparity_ratio` | `4.0` (reported only) |
| `breakdown.baseline_poor` | `false` |
| `findings[0].id` | `find_1` |
| `findings[0].title` | derived from `TOUCH_TARGET_TOO_SMALL` + `button#submit-order` |
| `findings[0].severity` | `CRITICAL` |
| `findings[0].affected_profiles` | `[]` |
| `findings[0].attribution_status` | `UNRESOLVED` |
| `findings[0].diagnosis` | `""` |
| `findings[0].remediation_diff` | `""` |
| `analyst` | `"hydrogen"` |

Ratio 4× is on the report. The score is 25 because **75 percentage points** of completion were lost, not because 4× is a magic number.

Hydrogen may surface both facts: the motor-impaired group lost 75 pp of completion, **and** a below-minimum touch target exists. It must not state that the button caused the gap. Helium can argue that later.

If Dev 2 had sent `affected_profiles = ["motor_impaired"]`, attribution would be `RESOLVED` and the finding could bottleneck-sort.

Helium fills the two empty strings. It must **not** change `overall_fairness_score` or `score_status`.

---

## 8. Downstream call names (reserved, not built)

| Future call | IN | OUT | Notes |
|-------------|----|-----|-------|
| `helium.diagnose` | `report: HydrogenReport` | `HydrogenReport` | writes `diagnosis`, `remediation_diff`; `analyst = "helium"`; **must not** change score, status, or policy |
| `lithium.create_report` | HTTP body → `EvidenceBundle` | Contract 3 JSON | calls `hydrogen.evaluate`, then optionally `helium.diagnose` |
| `beryllium.run_pipeline` | job id + Contract 2 path | `HydrogenReport` | Dev 1 → Dev 2 → `hydrogen.evaluate` |

---

## 9. Invariants

1. `hydrogen.evaluate` is deterministic. No LLM, network, browser, RNG, or runtime-generated weights.
2. When `score_status = VALID`, `overall_fairness_score ∈ [0, 100]` and is an `int`. Otherwise it is `null`.
3. `diagnosis` and `remediation_diff` leave Hydrogen as `""`.
4. Disparity rows are passed through unmodified on the report (skipped rows are flagged, not rewritten).
5. Hydrogen never invents a per-finding group join.
6. Hydrogen never claims causation or intent.
7. Every report stamps `scoring_policy = "hydrogen-v1"`.
8. The integer is a function of absolute gap × weight, never of `disparity_ratio` alone.
9. At most one scoring row per `METRIC_FAMILY`.
10. `profiles_tested` is never inferred from `disadvantaged_group`.

---

## 10. Decisions (closed)

| Topic | Verdict |
|-------|---------|
| Worst-group `min` vs average | **Keep `min`.** An average hides exclusion. |
| Score ignores linter / evidence counts | **Keep.** Brief scores outcomes, not WCAG hit count. |
| Score from `disparity_ratio` alone | **Invalid. Fixed.** 90% vs 45% and 10% vs 5% are both 2×; only A is an inclusion failure. Score absolute gap. |
| `RATIO_STEEPNESS` fitted to mock 62 | **Retired.** That knob assumed ratio-only scoring. |
| Empty / failed pipeline → 100 | **Invalid. Fixed.** `INSUFFICIENT_EVIDENCE` + `null`. |
| All-groups-on-CRITICAL join | **Invalid. Fixed.** `UNRESOLVED` + `affected_profiles = []` unless Dev 2 sent a join key. |
| `rank_findings` bottleneck without `breakdown` | **Fixed.** Optional `breakdown`; boost only if `RESOLVED`. |
| Time / errors / clicks / tabs ignored by the score | **Invalid. Fixed.** They affect the integer via `METRIC_WEIGHT` < 1. A 4× fail still hurts more than a 4× extra tab. |
| Weights chosen by Helium | **Never.** Named constants in git only. |
| Raise on empty vs return a report | **Return a report** with `null` + status. Callers still get findings. |
| Rule→constraint taxonomy table | **Not in v1.** That is another guessed join. Wait for Dev 2’s `affected_profiles`. |
| Layout `src/api` vs `hydrogen/` | **Valid. Fixed.** Element folders replace the old Dev 3 paths. |
| Causal titles / “button caused failure” | **Invalid. Fixed.** Findings are evidence shells; Helium interprets. |
| Scoring policy version | **Added.** `"hydrogen-v1"` on every report. |
| Validation is “finite only” | **Invalid. Fixed.** Rates `0–1`; time/counts `≥ 0`. Out of range → skip, not clamp. |
| `GAP_REF` as universal math | **Invalid. Fixed.** Policy thresholds, versioned. |
| `GAP_REF` vs `METRIC_WEIGHT` mixed | **Fixed.** Ref = max-severity gap; weight = influence on the final min. |
| Alias double-count (`time` / `errors`) | **Fixed.** `METRIC_FAMILY`, one row kept. |
| Outcome overlap (completion / failure / abandonment) | **Fixed in v1** as the `outcome` family (same class as aliases). |
| `low_baseline` = “broken for everybody” | **Invalid. Fixed.** Renamed `baseline_poor`; policy flag via `POOR_BASELINE_RATE`. |
| Infer `profiles_tested` | **Invalid. Fixed.** Trust the field or `[]`. |

---

## 11. To add or change later

Not in `hydrogen-v1`. Do **not** implement these until the policy string bumps (or the named call exists). Call names below are reserved so we do not rename later.

| Later item | How | Notes |
|------------|-----|-------|
| Tune metric weights / gap refs | Edit `METRIC_WEIGHT` or `GAP_REF` + new `SCORING_POLICY` | Do not silently retune. |
| Add a metric | Put it in `METRIC_KIND`, `GAP_REF`, `METRIC_WEIGHT` + new policy string | Unknown names stay in `skipped_metrics`. |
| Bring back ratio-only scoring | **Do not.** | Ratio stays a report field for Helium, not the integer. |
| Barrier / linter penalty on the score | New named constant, new policy string | v1 score is outcomes-only. |
| Evidence → profile join | Dev 2 fills `EvidenceRecord.affected_profiles` | Then Hydrogen already marks `RESOLVED`. No Hydrogen taxonomy table in v1. |
| Rule→constraint taxonomy | Only if Dev 2 never ships the join key | New table + new policy string. Guessing joins is still forbidden in v1. |
| Evidence-strength rank key | Extra sort key on `hydrogen.rank_findings` | Undefined today; do not invent a strength score. |
| Hard-fail empty input | Optional flag on `hydrogen.evaluate` | v1 returns a report with `null` + `INSUFFICIENT_EVIDENCE`. |
| Contract 3 requires an integer | Lithium maps `null` at the HTTP edge | Hydrogen still must not emit `100` for missing data. |
| Helium / Lithium / Beryllium | `helium.diagnose`, `lithium.create_report`, `beryllium.run_pipeline` | Reserved in §8. Must not recompute the score. |
| Weighted average instead of `min` | New policy string only | Default stays worst-group `min`. |
| Sample size / statistical confidence | New fields on `Disparity` + policy | 1/1 vs 0/1 can look like 1000/1000 vs 500/1000. Fine for v1/hackathon. |
| Mix relative severity back into the integer | **Do not** for v1 | 10 s→20 s vs 100 s→110 s are the same gap; ratio stays on the report for Helium. |

Changing any scoring rule without bumping `hydrogen.SCORING_POLICY` is a bug.

---

## 12. Folder (now)

```
hydrogen/
  sub-arch.md
  issue.md
  __init__.py
  constants.py
  models.py
  engine.py
```

Public calls:

```
hydrogen.parse_contract2
hydrogen.score_fairness
hydrogen.rank_findings   # (bundle, breakdown=None)
hydrogen.evaluate
hydrogen.METRIC_KIND
hydrogen.GAP_REF
hydrogen.METRIC_WEIGHT
hydrogen.METRIC_FAMILY
hydrogen.POOR_BASELINE_RATE
hydrogen.SCORING_POLICY
```
