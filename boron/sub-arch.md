# Boron — Browser Ingestion & Synthetic User Agent Engine

**Status:** v1 implemented — contracts, fixtures, Playwright capture harness, and the multi-profile suite runner.

Boron is the fifth CoHERence module (periodic-table naming, Z=5). It is Dev 1's **capture layer**: drive a headless browser as a constrained user, write page artifacts to disk, and emit friction telemetry.

Boron answers **what happened to this user on this page**. Dev 2 turns that into evidence and disparities; Hydrogen turns those into a score.

---

## 1. Naming and layout

Follows `hydrogen/sub-arch.md` §1: modules are full lowercase element names in atomic-number order. `beryllium` (Z=4) is reserved for Dev 3's orchestrator, so this module is `boron` (Z=5).

This **replaces** the DEV.md paths `src/agent/` and `src/browser/`. Do not keep both. Constraint emulation and browser driving live in one folder because the profile spec *is* the driver configuration.

Architecture and implementation both live in `boron/`. No parallel `src/boron/`.

---

## 2. What Boron is / is not

**Is**

- The only producer of Contract 1 `RawSessionArtifacts`.
- The only source of friction telemetry, and therefore the only input that moves `overall_fairness_score` (`hydrogen/sub-arch.md` §5: evidence only ranks findings).
- The owner of the `profile_id` vocabulary.
- A deterministic constraint emulator.

**Is not**

- Dev 2's rule engine. Boron does not measure WCAG, contrast, or touch-target compliance.
- A persona role-player. Per `docs/idea-brief.md`, profiles are input-channel constraints, not stereotypes of a person.
- A computer of ratios or disparities. `hydrogen/sub-arch.md` §4: direction normalization is Dev 2's job. Boron emits raw counts and times only.

---

## 3. Public call surface

Implemented:

| Call | IN | OUT |
|------|----|-----|
| `boron.get_profile` | `profile_id: str` | `ProfileSpec` |
| `boron.list_profiles` | — | `list[str]` |
| `boron.run_session` | `url`, `profile_id`, `session_id`, `steps`, `success_selector`, `out_root`, `seed` | `RawSessionArtifacts` |
| `boron.run_suite` | `url`, `profile_ids`, `session_id_prefix`, `steps`, `success_selector`, `runs=1`, `out_root`, `seed` | `list[RawSessionArtifacts]` |

`run_suite` is the call `beryllium.run_pipeline` should use. It mints `{prefix}_{profile_id}` session ids (plus `_{n}` when `runs > 1`) so no two runs share an artifact directory, and it advances the seed per repeat — without that, `runs=3` would return three byte-identical measurements.

Profiles run **sequentially**. `completion_time_ms` drives the fairness score and concurrent Chromium instances contend for CPU, so parallelism would corrupt the measurement it is meant to speed up.

### The task shape

`run_session` takes `steps` (CSS selectors to activate in order) and `success_selector` (visible ⇒ `task_completed`). This is the minimum that makes the harness general across target sites without inventing a task DSL. A profile that cannot reach a step records the failure in `error_count` and stops — an unreachable control is a completed measurement, not a crash.

`MAX_ATTEMPTS = 5`: a pointer press that produces no DOM mutation counts as a `dead_click` and is retried, because a real user retries a slip rather than abandoning. Tremor is seeded (`DEFAULT_SEED = 1729`) so a run is reproducible.

Playwright **sync** API (`playwright.sync_api`). Profiles run sequentially: `completion_time_ms` drives the score, and concurrent Chromium instances contend for CPU and corrupt wall-clock timing. An async adapter can wrap `run_suite` in `asyncio.to_thread` if Dev 3 needs one.

---

## 4. Contract 1 — `RawSessionArtifacts`

One record per **(session, profile)**. Artifacts are paths on disk; Dev 2 opens the files.

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | `str` | one directory under `data/sessions/` |
| `profile_id` | `str` | short form, see §5 |
| `url` | `str` | target under test |
| `artifacts.html_path` | `str` | → Dev 2 text analyzer |
| `artifacts.screenshot_path` | `str` | → Dev 2 vision analyzer |
| `artifacts.a11y_tree_path` | `str` | → Dev 2 accessibility rules (CDP `Accessibility.getFullAXTree`) |
| `artifacts.elements_path` | `str` | → Dev 2 rule engine. **Added to Contract 1, see below** |
| `telemetry` | `Telemetry` | see below |

#### `elements_path` is an addition to DEV.md's Contract 1

DEV.md §2.2 assigns Boron "DOM snapshot and computed styles (bounding boxes, font sizes, line heights)", but DEV.md §3's Contract 1 gives only three artifact paths, so there was nowhere to put them. Geometry cannot be recovered from serialized HTML — it needs a layout engine — so without a fourth artifact Dev 2 cannot produce the canonical `TOUCH_TARGET_TOO_SMALL` finding with a `bounding_box` at all.

`elements.json` is a list of interactive and text-bearing elements, each carrying `element_selector`, `tag`, `bounding_box` (`x, y, width, height` — Contract 2's key names, not DEV.md §2.2's `w`/`h`), `font_size`, `line_height`, `color`, `background_color`, `alt`, `aria_label`, `tabindex`, `visible`. Those are exactly Dev 2's inputs for touch-target, spacing, contrast, readability and alt-text rules.

**This is a contract change and needs Dev 2's ack.**

### `Telemetry`

**Every field name here must exist in `hydrogen.METRIC_KIND`.** `hydrogen/sub-arch.md` §6.5: unknown metric names go to `skipped_metrics` and silently stop affecting the score. `tests/test_boron.py::test_telemetry_fields_are_scoreable_by_hydrogen` enforces this.

| Field | Type | In `METRIC_KIND` |
|-------|------|------------------|
| `completion_time_ms` | `int` | yes, `lower_better` |
| `task_completed` | `bool` | no — per-session bool that Dev 2 aggregates into `task_completion_rate` |
| `total_clicks` | `int` | yes, `lower_better` |
| `dead_clicks` | `int` | yes, `lower_better` |
| `keyboard_nav_steps` | `int` | yes, `lower_better` |
| `error_count` | `int` | yes, `lower_better` |

`missed_clicks` is named in DEV.md §2.3 but is **not** in `METRIC_KIND`. It is deliberately omitted: it would never affect the score. Adding it requires a `hydrogen-v2` policy bump. `dead_clicks` covers the concept today.

Boron must also emit at most one field per `hydrogen.METRIC_FAMILY`, or the extras land in `collapsed_metrics`. Enforced by `test_telemetry_families_do_not_collide`.

---

## 5. Profiles

Short-form IDs only, so `profile_id` equals Dev 2's `disadvantaged_group` verbatim and no mapping table is needed. DEV.md's Contract 1 example uses the compound `motor_impaired_keyboard_only`; Contracts 2 and 3 and every Hydrogen test use short forms. Short form wins.

| `id` | Constraint |
|------|-----------|
| `baseline_default` | none — the reference run |
| `motor_impaired` | `tremor_px=6.0`, `dwell_ms=400` |
| `tremor_users` | `tremor_px=20` |
| `touch_screen_users` | `has_touch`, `tremor_px=8` |
| `screen_reader_users` | `ax_tree_only` + `keyboard_only` |
| `low_vision` | `zoom=2.0` |
| `elderly` | `zoom=1.5`, `tremor_px=8`, `dwell_ms=300`, `read_delay_ms=600` |
| `cognitive_impaired` | `read_delay_ms=1200`, `max_attempts=2` |
| `adhd_users` | `read_delay_ms=300`, `max_attempts=2` |
| `esl_users` | `read_delay_ms=900` |

Ids match the group names in `carbon`'s `RULE_AFFECTED_PROFILES_MAP` so the two
vocabularies line up: every group carbon can name is a profile boron runs.
Enforced by `test_roster_covers_carbon_group_vocabulary`.

Each id names a **parameter bundle, not a person**. There is no LLM roleplay:
`elderly` is `zoom=1.5` plus tremor plus a read delay, nothing more. This keeps
the constraint framing `docs/idea-brief.md` requires while matching Dev 2's
strings.

`marginalized_demographics` is deliberately **not** a profile. It was mapped to
`EXCLUSIONARY_LANGUAGE_DETECTED`, a content defect detectable from the DOM with
no simulated user at all, and there is no input-channel constraint to emulate
for it. That mapping was removed; the rule now ships `affected_profiles=[]` /
`UNRESOLVED`, which hydrogen handles correctly.
| `keyboard_only` | `keyboard_only=True` (Tab / Shift+Tab / Enter only) |

Motor and keyboard-only are **separate** profiles, not one compound. Isolating constraints is what lets the disparity engine attribute a gap to a cause.

`PROFILE_ALIASES` maps the one long-form string that exists in the repo (`motor_impaired_keyboard_only`, DEV.md §3) onto `motor_impaired`, so a teammate copying the DEV.md example gets a profile instead of a `KeyError`. Canonical output is always short-form.

**Every profile shares the 1280×800 viewport.** Only the constraint under test may vary, or the disparity is confounded with a pure layout difference. In particular `low_vision` carries `zoom=2.0` and *not* a smaller viewport — 200% zoom on 1280px already yields 640 effective CSS px, so setting both would double-count to ~320px. A small screen is a *context* constraint and belongs in a separate run, not in the vision profile. Enforced by `test_all_profiles_share_the_baseline_viewport`.

`ProfileSpec` fields map 1:1 to step-2 Playwright calls: `viewport_width`/`viewport_height` → `new_context(viewport=...)`, `zoom` → page zoom, `keyboard_only` → navigation branch, `tremor_px` → `mouse.move` jitter, `dwell_ms` → hold before click.

`baseline_default` must stay unconstrained — a baseline carrying a hidden constraint corrupts every disparity. Enforced by `test_baseline_profile_is_unconstrained`.

---

## 6. Storage layout

```
data/sessions/{session_id}/
    dom.html
    screenshot.png
    a11y_tree.json
    elements.json
```

`data/` is gitignored, so `data/sessions/` will not exist on a fresh clone — step 2's writer must create it with `parents=True, exist_ok=True`.

**`session_id` must be unique per (run, profile).** There is one Contract 1 record per (session, profile), so four profiles sharing one `session_id` would overwrite the same three files. Convention: `sess_<run>_<profile_id>`. This needs no contract change — the path shape stays exactly as DEV.md shows it. Enforced by `test_session_ids_are_unique_per_profile`.

Paths are POSIX-separated strings relative to the repo root, never `pathlib.Path`. A `Path` serialized on Windows produces `data\sessions\...`, which Dev 2 on Linux cannot open. Enforced by `test_artifact_paths_are_posix`.

---

## 6a. Test fixtures

`tests/fixtures/test_page.html` is a fully offline checkout page (inline styles, `data:` URI images, no network). It carries a **two-step gated task** so each constraint fails differently rather than every profile trivially succeeding: click `div#fake-button` to enable `button#submit-order`, then click that to reveal `#order-confirmed`.

| Selector | Defect | Profile hurt |
|---|---|---|
| `button#submit-order` | 24×22px target | `motor_impaired` — dead clicks, time up |
| `div#fake-button` | clickable div, no role/tabindex | `keyboard_only` — task cannot complete |
| `.wide` | 900px, no reflow at 200% | `low_vision` — time up |
| `p.hint` | ~2.3:1 contrast | evidence only |
| first `img` | missing `alt` | evidence only |
| `#apply-coupon` / `#remove-coupon` | 0px gap | `motor_impaired` |
| `h1` → `h3` | skipped heading level | evidence only |
| `#continue`, `img[alt]` | **correct** | true negatives |

The two control elements matter as much as the defects: without them Dev 2 cannot tell "my rule works" from "my rule always fires".

`session_baseline_default.json` and `session_motor_impaired.json` are a **pair**, not a single sample — Dev 2 cannot compute a disparity from one record.

---

## 7. Handoff to Carbon (Dev 2)

`boron/handoff.py` adapts Boron output to carbon's input shapes. Boron does **not** import carbon — the adapters return plain dicts, so the dependency runs one way only.

| Call | Gives carbon |
|------|--------------|
| `boron.to_contract1(record)` | Contract 1 JSON for `carbon.RawSessionArtifacts` |
| `boron.rule_context(record)` | `interactive_elements` + `contrast_elements` |
| `boron.page_context(record)` | the full dict for `carbon.RuleEngine.evaluate_context` |

### Wiring rule

Evidence and disparities come from different places:

- **Evidence** — run `RuleEngine.evaluate_context(boron.page_context(baseline))` **once**, on the baseline session. Static defects are properties of the page as authored.
- **Disparities** — run `DisparityEngine.analyze_sessions(baseline, constrained)` over **all** sessions. Outcomes are per-profile.

Running the rule engine once per profile instead produced 47 findings for 12 distinct defects, and `evaluate_session_artifacts` appended the running profile's id to `affected_profiles`, tagging page defects with `baseline_default` — the false join `hydrogen/sub-arch.md` §6.4 forbids. `tests/test_integration.py` locks both behaviours.

### Field alias

`carbon.TelemetryData` names the error field `errors`; Boron names it `error_count` because that is the name `hydrogen.METRIC_KIND` scores. `to_contract1` emits **both**. Each model ignores the key it does not declare. This is a shim, not a design — see open item 1.

## 8. Open items for the team

### Closed

**Runs per profile = 1 (v1).** `runs` is a parameter with default `1`. With N=1, `task_completion_rate` is only ever `0.0` or `1.0` per profile, so a failing constrained profile produces the maximum `abs_gap` of 1.0 and drives the score to 0. Correct arithmetic on a one-sample measurement, not a bug. Observed directly: across five tremor seeds, four runs produced 0 dead clicks and one produced 2. Raise N when the numbers must be defensible rather than demonstrative.

**`profiles_tested` producer = whoever starts the job** — Lithium or Beryllium, from the request toggles. Dev 2 may alternatively unique `profile_id` across the ingested batch. Hydrogen still trusts the field and never infers it.

**Tremor seed.** `run_session(seed=...)`, default `DEFAULT_SEED = 1729`; `run_suite` advances it per repeat so `runs=3` is three measurements, not one repeated three times.

**High-contrast emulation stays omitted.** DEV.md §2.3 lists it as a vision constraint, but forcing high contrast would *mask* the `COLOR_CONTRAST_FAIL_AA` defects Dev 2 exists to detect. Vision profiles magnify only.

**`missed_clicks` needs no hydrogen policy bump.** The `METRIC_KIND` constraint applies to *disparity metric names*, not telemetry field names. Carbon derives disparities only for `task_completion_rate`, `completion_time_ms`, `dead_clicks`, `keyboard_nav_steps` and `composite_friction_score`, so `missed_clicks` never reaches hydrogen. It is now emitted for carbon's `compute_friction_score`, defined distinctly: **`missed_clicks`** = pointer landed outside the target box; **`dead_clicks`** = press produced no DOM mutation. `NOT_SCORED` in `tests/test_boron.py` keeps the guard honest.

**`capture_policy = "boron-v1"`** is stamped on every record, mirroring hydrogen's `scoring_policy`. `tremor_px=12` and `tremor_px=20` produce very different `dead_clicks`; the stamp records which emulation produced a number.

**Evidence → profile join.** `Telemetry.failed_selectors` records the selectors a profile could not operate, in the same canonical form `elements.json` uses (one shared `cssPath` definition, `boron/capture.py::CANONICAL_SELECTOR_SCRIPT`). `carbon.RuleEngine.attribute_from_failures` **intersects** those with the rule taxonomy rather than substituting: a keyboard user failing to reach a button is evidence for `INACCESSIBLE_CLICKABLE_ELEMENT`, not for that element's contrast. Where the intersection is empty the taxonomy stands.

**DEV.md corrected** — owned directories are element folders, bounding boxes are `width`/`height`, Contract 1 shows all four artifacts plus the new telemetry, Contract 3 lists the full roster, and test filenames match reality.

### Open

1. **`composite_friction_score` is not in `METRIC_KIND`** and lands in `breakdown.skipped_metrics`. Dev 3 is adding it in a future update; left alone deliberately, since changing scoring rules without bumping `SCORING_POLICY` is a bug by hydrogen's own doc.
2. **Sample size.** N=1 makes every binary outcome look total. Raising `runs` is a parameter change; agreeing the number is a team call.

---

## 9. Carbon seam — resolved

All six findings from wiring Dev 2 in are fixed. Boron no longer carries adapter shims; carbon accepts Boron output directly.

| Was | Now |
|---|---|
| `TelemetryData.errors` not scoreable | renamed `error_count`, with `AliasChoices("error_count", "errors")` so Dev 2's existing fixture still parses |
| `ArtifactPaths` dropped `elements_path` | declared; `evaluate_session_artifacts` loads it and derives the geometry inputs itself |
| geometry rules silently found nothing | the bare `evaluate_session_artifacts(session)` call now yields `TOUCH_TARGET_TOO_SMALL` at `24x22px` |
| session `profile_id` appended to `affected_profiles` | removed — a page defect is not owned by whichever profile was running |
| taxonomy named 8 untested groups | roster expanded to 11; `marginalized_demographics` mapping removed |
| `beautifulsoup4` / `pillow` / `numpy` undeclared | added to `requirements.txt` |

`boron/handoff.py` remains for callers that want to override the rule inputs, but nothing depends on it any more.
