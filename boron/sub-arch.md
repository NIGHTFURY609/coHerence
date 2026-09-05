# Boron — Browser Ingestion & Synthetic User Agent Engine

**Status:** v1 implemented — contracts, fixtures, Playwright capture harness, the multi-profile suite runner, VL-driven navigation, and human-in-the-loop capture.

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
| `boron.run_session` | `url`, `profile_id`, `session_id`, `success_selector`, `steps` \| `goal`, `vl_client`, `max_steps`, `out_root`, `seed` | `RawSessionArtifacts` |
| `boron.run_suite` | `url`, `profile_ids`, `session_id_prefix`, `success_selector`, `steps` \| `goal`, `vl_client`, `plan_once`, `max_steps`, `runs=1`, `out_root`, `seed` | `list[RawSessionArtifacts]` |
| `boron.run_manual` | `url`, `session_id`, `profile_id`, `out_root`, `max_minutes` | `list[RawSessionArtifacts]` |
| `boron.from_screenshots` | `paths`, `url`, `session_id`, `profile_id`, `out_root` | `list[RawSessionArtifacts]` |
| `boron.describe_pages` | `records`, `vl_client` | `dict[session_id, str]` |

`run_suite` is the call `beryllium.run_pipeline` should use. It mints `{prefix}_{profile_id}` session ids (plus `_{n}` when `runs > 1`) so no two runs share an artifact directory, and it advances the seed per repeat — without that, `runs=3` would return three byte-identical measurements.

Profiles run **sequentially**. `completion_time_ms` drives the fairness score and concurrent Chromium instances contend for CPU, so parallelism would corrupt the measurement it is meant to speed up.

### The task shape

`run_session` takes `steps` (CSS selectors to activate in order) and `success_selector` (visible ⇒ `task_completed`). This is the minimum that makes the harness general across target sites without inventing a task DSL. A profile that cannot reach a step records the failure in `error_count` and stops — an unreachable control is a completed measurement, not a crash.

`MAX_ATTEMPTS = 5`: a pointer press that produces no DOM mutation counts as a `dead_click` and is retried, because a real user retries a slip rather than abandoning. Tremor is seeded (`DEFAULT_SEED = 1729`) so a run is reproducible.

Playwright **sync** API (`playwright.sync_api`). Profiles run sequentially: `completion_time_ms` drives the score, and concurrent Chromium instances contend for CPU and corrupt wall-clock timing. An async adapter can wrap `run_suite` in `asyncio.to_thread` if Dev 3 needs one.

---

## 3a. Two ways to drive a task

`steps=[...]` and `goal="..."` are mutually exclusive; passing both, or neither,
raises. The constraint layer is identical either way — only the source of the next
target changes.

| | `steps=[...]` | `goal="..."` |
|---|---|---|
| Next target from | a hand-written CSS selector list | Qwen3-VL, one action per screenshot |
| Needs | nothing | a `vl_client` |
| Reproducible | yes | no |
| `capture_policy` | `boron-v1` | `boron-vl-v1` |

### Nitrogen is called, not imported

`nitrogen/sub-arch.md` §2 says Nitrogen is a **host** and "callers own prompts".
Boron is that caller, and the navigation prompt lives in `boron/navigator.py`.
The client is a constructor argument typed only by `nitrogen.VLClient`'s shape
(`complete(system, user, image_b64=None) -> str`), so Boron never imports
`nitrogen/`, `helium/` or `hydrogen/` and Dev 1's tests need no GPU. Wire it at
the call site:

```python
from nitrogen import ModalVLClient
boron.run_suite(..., goal="Place the order", vl_client=ModalVLClient(), plan_once=True)
```

### Running the live path

`modal` is imported by `helium/runtime.py` on every live call and was undeclared;
it is now in `requirements.txt`. Pull the weights once (Dev 3's entrypoint):

```bash
modal run helium/modal_app.py::pull_nitrogen
```

**On Windows set `PYTHONIOENCODING=utf-8` first.** Modal's progress renderer emits
`✓`, which the default `cp1252` console codec cannot encode; the run dies
immediately with `'charmap' codec can't encode character '✓'` and exits **0**,
so it looks like it succeeded when nothing was downloaded.

```bash
PYTHONIOENCODING=utf-8 modal run helium/modal_app.py::pull_nitrogen
```

**Then deploy, and set `HELIUM_RUNTIME=deployed`.** This is not optional for VL
navigation. `helium.constants.HELIUM_RUNTIME` defaults to `ephemeral`, which by its
own comment "boots a container per live call". Helium makes one `diagnose` call per
report, so a cold start there is amortised over a whole run. A navigation loop makes
**one call per step** — under `ephemeral` a 12-step session boots the B300 twelve
times and reloads a 27B plus a 30B model on each, which is slower than the run it is
driving and costs accordingly.

```bash
modal deploy helium/modal_app.py
HELIUM_RUNTIME=deployed python -c "...run_suite(goal=..., vl_client=ModalVLClient())"
```

Boron does not enforce this — it only ever sees a `VLClient`, and coupling the
capture layer to Dev 3's transport would break the separation that makes the client
injectable in the first place. It is a run-book step.

### `import modal` breaks the browser on Windows

`nitrogen.ModalVLClient` reaches the GPU through `helium.runtime`, which does
`import modal` on the first call. Modal installs `WindowsSelectorEventLoopPolicy`
process-wide, and on Windows a selector loop **cannot spawn a subprocess** —
which is exactly how Playwright's sync API starts its driver.

The failure is delayed and misleading: the first profile in a suite launches its
browser *before* the first VL call, so it succeeds. Every profile after it dies in
`asyncio.new_event_loop()` with a bare `NotImplementedError` and no mention of
modal, playwright or policies.

`boron/runner.py::_driver` pins a Proactor policy across Playwright's `__enter__`
and restores modal's policy immediately afterwards. Playwright builds its loop in
`__enter__` and never consults the policy again, so this is enough for the driver
and leaves modal's gRPC stack with the policy it chose.

**Always start a browser through `_driver()`, never `sync_playwright()` directly** —
a bare call is still vulnerable. Locked by
`tests/test_boron_vl.py::test_a_suite_survives_the_modal_import`.

### Coordinates are a 0-1000 grid, not pixels

Qwen3-VL grounds on a **normalized 0-1000 grid per axis**. Measured against
`tests/fixtures/test_page.html` at a 1280x800 viewport:

| Control | True centre (px) | Model | px x 1000 / viewport |
|---|---|---|---|
| `div#fake-button` "Place order" | (83, 346) | (64.5, 431.5) | (64.8, 432.5) |
| `button#apply-coupon` "Apply" | (48, 295) | (37.5, 367.5) | (37.5, 368.8) |

Within one unit on both axes. Telling the model the screenshot is 1280x800 does
not make it answer in pixels, so the prompt states the grid explicitly and
`_to_css_px` divides by `COORDINATE_SCALE`. The conversion therefore depends on
the **viewport**, never on the screenshot's pixel size, and holds for any model
that follows the instruction.

Read as pixels, the model's numbers land roughly one control too low — close
enough to hit a real neighbouring element, which is how this hid: the click
succeeded, on the wrong button.

Test actions carry grid coordinates for this reason. `(83, 346)` in a test would
be a pixel value the live model would never emit.

### Grounding output shapes

`_point` accepts what the model actually emits, not one canonical form. A live run
produced `{"x": [64, 431], "y": 431}` — the pair packed into `x` — which had been
the correct location of "Place order" all along. `point`, `coordinate`, and
4-number `bbox` forms are handled too; a box means aim at its centre. Rejecting
anything but two scalars turns a correctly located target into a crashed step.

### The model supplies intent, the profile supplies the channel

A click action is a **point**, and Boron does not snap it to the nearest element.
Snapping would mean tremor could never miss, which would delete the disparity the
whole system exists to measure. The model's point goes through the same
`_press_point` the scripted path uses: tremor displacement, `dwell_ms`,
`max_attempts`, MutationObserver dead-click detection.

Nothing in the prompt names the profile. `docs/idea-brief.md` rejects persona
role-play, so a constraint is expressed by what the model is **given**:

| Profile | Given | Action vocabulary |
|---|---|---|
| sighted, pointer | viewport screenshot | click, press, type, scroll |
| `keyboard_only` | viewport screenshot | **no click** |
| `screen_reader_users` (`ax_tree_only`) | **no image**; focusable a11y nodes as text | **no click** |

`test_the_prompt_never_names_the_profile` enforces this — the word "elderly"
never reaches the model on an `elderly` run.

### What the model can and cannot do — measured

Live against `tests/fixtures/test_page.html` on the deployed B300, Qwen3-VL-30B-A3B:

| Capability | Result |
|---|---|
| Reads the page | **Yes.** Lists all five buttons — Apply, Remove, Place order, Pay, Continue shopping |
| Locates a control | **Yes.** Within one grid unit of true geometry (§3a) |
| Clicks the right element | **Yes.** `aimed_selector: div#fake-button`, 0 dead clicks on the first press |
| Finishes a two-step flow | **No.** Asked which button finishes the checkout, it answers "Place order" |

The fixture gates completion behind a 24x22px button labelled **Pay**, while a
prominent div labelled **Place order** does nothing. The model clicks the label
that matches the goal, declares the task done, and — told explicitly that the
element produced no change — clicks it again.

That is a reasoning limit, not a plumbing fault, and it is not obviously *wrong*:
a page whose most prominent control is inert while a tiny one submits is the exact
defect this project exists to find. Do not tune the navigator prompt against this
fixture; it is adversarial by construction.

Practical consequence for `plan_once`: if the planning profile cannot finish the
flow, `PlanFailed` fires rather than replaying a dead path across eleven profiles.
On pages where the model cannot complete the task, drive the suite with explicit
`steps=[...]` — the scripted path is not deprecated and is still the default for
deterministic measurement.

### `plan_once`

One B300, `max_containers=1`, and the generate lock is shared with Helium
(`helium/modal_app.py::HeliumGPU._turn`). A live loop across the 11-profile roster
serialises ~90 30B calls behind that lock and blocks Helium meanwhile.
`plan_once=True` runs the VL loop on `profile_ids[0]` only, then replays the
selectors it discovered through the rest. Records from the replayed profiles keep
`boron-vl-v1` — the path still came from the model — and their `nav_trace.json`
records `mode: "replayed"`.

**The planning run must prove its path**, or `run_suite` raises `PlanFailed`. If the
planner activated nothing, or never reached `success_selector`, every constrained
profile would replay an empty or unfinished path, complete nothing, and — because a
profile that runs no steps also logs no errors — look like a clean run. A suite where
nobody completes reads downstream as *"this site fails everyone"* when the truth is
only that the model could not drive it. That is a false negative wearing a score, so
it fails loudly instead. This is the canary for open item 3.

Use the live per-profile loop when inspecting one profile, `plan_once` for a suite.

### Model inference is not the user's think time

`completion_time_ms` **subtracts** accumulated VL wall-clock. A 30B call is seconds;
`read_delay_ms` is hundreds of ms. Left in, every profile's completion time would
measure how busy the B300 was, and `completion_time_ms` is the telemetry that moves
`overall_fairness_score`. Locked by
`tests/test_boron_vl.py::test_completion_time_excludes_model_inference`.

### The trace is a sidecar, not a fifth artifact

`data/sessions/{session_id}/nav_trace.json` records the goal, mode, per-step
`vl_ms`, each action, the selector aimed at, and whether a `done` claim verified.
It is deliberately **not** declared in `SessionArtifacts`: Contract 1 has four
artifact paths and a fifth needs Dev 2's ack. Carbon ignores files it does not know
about, so the trace rides along for debugging and the frontend's execution tracker
with no contract change.

### `missed_clicks` on a coordinate click

The scripted path judges a miss against the target's bounding box. A VL click has
no box — only a point — so it judges against `document.elementFromPoint`: the
element under the displaced point differs from the element under the aimed point.
Same concept, measured with the tool each mode actually has.

`elementFromPoint` is also what keeps `failed_selectors` valid for VL runs. Carbon's
`attribute_from_failures` needs selectors in `elements.json` form, and
`capture.element_at_point` returns exactly that (shared `cssPath`, so both sides
spell a selector identically).

---

## 3b. Manual capture — a human drives

For flows automation cannot reach on its own (logins, captchas, payment walls), or
when the real thing should be audited rather than a simulation.

| Call | Browser | Artifacts | `capture_policy` |
|---|---|---|---|
| `run_manual` | headed Chromium you drive | all four, real | `boron-manual-v1` |
| `from_screenshots` | none | screenshot only | `boron-manual-png-v1` |

`run_manual` injects a hotkey listener on every navigation: **F8** captures the
current page, **Escape** ends the session. Each capture is one `RawSessionArtifacts`
at `{session_id}_{n}`. Only observable telemetry is filled in — `completion_time_ms`
(wall clock), `total_clicks` (click listener), `error_count` (`pageerror`).
`dead_clicks` and `missed_clicks` stay `0`: neither is measurable for a real person,
and inventing them would feed carbon's `compute_friction_score` a fabricated number.

`total_clicks` accumulates **deltas**, not a running maximum. The counter lives in the
page and restarts at zero on every navigation, so a five-click page followed by a
three-click page would otherwise report five instead of eight.

`from_screenshots` accepts images captured anywhere. It writes `elements.json` as
`[]` and an empty a11y tree, because there is no DOM behind a PNG — carbon's
geometry, contrast and accessibility rules will correctly find nothing. The separate
`boron-manual-png-v1` stamp is what stops that reading downstream as a clean audit.

Manual records default to `profile_id="baseline_default"`: a real person under no
emulated constraint **is** the baseline, so the record drops straight into
`DisparityEngine.analyze_sessions(baseline, constrained)`. Override if you are
capturing someone who does use assistive technology.

`describe_pages(records, vl_client)` annotates each captured screenshot with what
the model sees on it. That is a capture-time note only — Boron does not score
(hydrogen) and does not diagnose or remediate (helium).

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

## 7a. Nitrogen seam — one fix in Dev 3's file

The first live run failed with the model clicking `(640, 720)` — the exact centre
of a 1280-wide viewport, 90% down — while the target sat at `(36, 385)`. That is
the shape of a guess, not a mis-grounded look, so the question was whether the
model could see at all.

A control image (green border, blue ellipse bottom-right, large text `BANANA 4271`)
came back as *"the text is 100, the border is red, and the shape in the bottom right
is a triangle"* — every visual fact wrong. **The model was blind.**

Cause, in `helium/modal_app.py::nitrogen_complete`:

```python
prompt = tokenizer.apply_chat_template(messages, tokenize=False, ...)
result = llm.generate([prompt], params)      # <- pixels never passed
```

`apply_chat_template` only renders `<|vision_start|><|image_pad|><|vision_end|>`
into the prompt *text*. The `data:image/png;base64,...` URL ends up inside a string
and nowhere else. vLLM needs the decoded image handed to it alongside the prompt:

```python
request = {"prompt": prompt}
if image_b64:
    request["multi_modal_data"] = {"image": _decode_image(image_b64)}
result = llm.generate([request], params)
```

The placeholders were therefore backed by nothing, and the model described an image
it had never seen. `pillow` was already in the Modal image, so the intent was there —
only the hand-off was missing.

**This is Dev 3's file and needs their ack.** It is confined to `nitrogen_complete`;
Helium's own `complete` is untouched, and no signature changed. Every Nitrogen caller
was affected, not just Boron — any VL result produced before this fix was a
hallucination.

---

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
2. **Sample size.** N=1 makes every binary outcome look total. Raising `runs` is a parameter change; agreeing the number is a team call. Note the interaction with VL mode: `runs=3` on a live per-profile loop triples ~90 sequential 30B calls on the one shared B300. `plan_once=True` makes raising N cheap, because only the baseline spends GPU.
3. **VL task reasoning is the current ceiling, not vision.** Grounding is accurate to within one grid unit (§3a) and the model reads the page correctly, but it does not finish the fixture's two-step flow. Whether a larger or agent-tuned VL model clears this is untested. Until then `goal=` is for exploration and `steps=` remains the path for reproducible measurement.

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
