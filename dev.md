# CoHERence — Team Work Breakdown & Architecture Guide

This document outlines the architecture, responsibilities, data contracts, and development plan for the 4-person development team (**3 Backend : 1 Frontend**).

---

## 1. Team Roles Overview (3:1 Split)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                FRONTEND DEVELOPER                                      │
│  Playground UI • Test Runner Config • Disparity Visualizations • Remediation Diff View │
└─────────────────────────────────────────▲──────────────────────────────────────────────┘
                                          │ REST & WebSockets (FastAPI Gateway)
┌─────────────────────────────────────────┴──────────────────────────────────────────────┐
│                                BACKEND DEV 3 (Lead / AI)                               │
│   FastAPI Gateway & Job Queue • LLM Analyst • Prompt Engineering • Synthesis Pipeline │
└───────────────────────────▲──────────────────────────────────▲─────────────────────────┘
                            │ Reads Evidence & Disparities     │ Triggers & Awaits
┌───────────────────────────┴──────────────────────┐ ┌─────────┴─────────────────────────┐
│               BACKEND DEV 2                      │ │              BACKEND DEV 1        │
│        Logic, Rules & Disparity Engine           │ │        Browser & User Simulation  │
│  • Multi-Modal Analyzers (Text, Vision, A11y)    │ │  • Playwright automation harness  │
│  • Deterministic Rule Engine (WCAG, Spacing)     │ │  • Multi-modal data extraction    │
│  • Evidence Store Schemas                        │ │  • Synthetic user constraints     │
│  • Statistical Disparity Math                    │ │    (motor, vision, keyboard-only) │
└──────────────────────────────────────────────────┘ └───────────────────────────────────┘
```

| Role | Title | Core Mission | Primary Stack |
| :--- | :--- | :--- | :--- |
| **Dev 1** | **Simulation & Automation Engineer** | The **"Hands & Eyes"**: Controls headless browsers, simulates diverse human constraints, and captures raw page artifacts. | Python, Playwright, Chrome DevTools Protocol (CDP) |
| **Dev 2** | **Logic, Rules & Disparity Engineer** | The **"Brain (Math & Rules)"**: Ingests raw artifacts, runs deterministic audits (WCAG, contrast, readability), and computes group disparities. | Python, BeautifulSoup4, PIL/OpenCV, Pydantic, NumPy |
| **Dev 3** | **AI & API Orchestrator** | The **"Intelligence & Voice"**: Evaluates disparity evidence using LLMs, produces actionable code fixes, and serves the FastAPI gateway. | Python, FastAPI, LiteLLM / Google GenAI / Anthropic, Pydantic |
| **Frontend** | **UI/UX Playground Engineer** | The **"Interface"**: Builds the interactive test runner, live execution monitor, disparity charts, and remediation dashboard. | Next.js (App Router), TypeScript, Tailwind CSS, Shadcn UI, Recharts |

---

## 2. Detailed Work Division

### Backend Dev 1: Browser Ingestion & Synthetic User Agent Engine

* **Owned Directory:** `src/agent/` & `src/browser/`
* **Core Responsibilities:**
  1. **Playwright Execution Harness:**
     - Headless Chromium lifecycle management (navigation, SPA render detection, cookie/modal handling).
     - Single-page and multi-step user journey automation (navigating forms, buttons, links).
  2. **Multi-Modal Data Capture:**
     - Extract DOM snapshot and computed styles (bounding boxes `x, y, w, h`, font sizes, line heights).
     - Capture full-page and viewport screenshots.
     - Dump the Chromium Accessibility Tree via CDP (`Accessibility.getFullAXTree`).
  3. **User Profile & Constraint Emulation:**
     - **Motor Constraints:** Simulated cursor tremor, click jitter, increased click dwell time, and strict keyboard-only navigation (`Tab`, `Shift+Tab`, `Enter`).
     - **Vision Constraints:** Viewport scaling (200% zoom), small screens (mobile viewports), high-contrast simulation.
     - **Friction Telemetry:** Track task completion time, missed clicks, dead clicks, and navigation errors per profile.
* **Isolated Testing:**
  - Test against local static test pages (`tests/fixtures/test_page.html`) without internet access:
    ```bash
    pytest tests/test_browser_runner.py
    ```

---

### Backend Dev 2: Logic, Rules & Disparity Analytics Engine

* **Owned Directory:** `src/analyzers/`, `src/rules/`, & `src/disparity/`
* **Core Responsibilities:**
  1. **Multi-Modal Analyzers:**
     - **Text Analyzer:** Flesch-Kincaid readability scoring, sentence complexity, and exclusionary/gendered terminology detection.
     - **Vision Analyzer:** Visual density, clutter scoring, whitespace ratio, and contrast ratio validation.
     - **Accessibility Analyzer:** Missing ARIA attributes, image `alt` text validation, heading hierarchy, and focus traps.
  2. **Deterministic Rule Engine:**
     - Touch target size evaluation ($\ge 48\times 48\text{px}$ standard).
     - Interactive spacing rules (preventing accidental misclicks).
     - Color contrast thresholds against WCAG AA/AAA.
  3. **Evidence Store Schemas:**
     - Normalize findings across all analyzers into structured Pydantic models.
  4. **Disparity Engine:**
     - Compute quantitative deltas between baseline and constrained profiles (e.g. $\Delta \text{Completion Time}$, $\Delta \text{Error Rate}$, $\Delta \text{Friction Score}$).
     - Flag statistically significant disparities indicating systemic design bias.
* **Isolated Testing:**
  - Run tests directly on pre-captured fixture files (`tests/fixtures/dom_sample.html`, `screenshot_sample.png`) in $<1\text{s}$:
    ```bash
    pytest tests/test_rules_and_disparity.py
    ```

---

### Backend Dev 3: AI Intelligence, LLM Analyst & API Gateway

* **Owned Directory:** `src/api/`, `src/llm/`, & `src/orchestrator/`
* **Core Responsibilities:**
  1. **LLM Analyst Pipeline:**
     - Design structured JSON prompts that ingest the disparity summary and evidence records.
     - Generate root cause diagnoses (e.g. *"Why is this workflow 4x harder for motor-impaired users?"*).
     - Generate copyable remediation suggestions and code patches (HTML/CSS diffs).
  2. **FastAPI Gateway:**
     - Endpoints for test triggering, execution status, and final report retrieval.
     - Asynchronous task management (FastAPI `BackgroundTasks` or Celery/RQ).
     - WebSocket or Server-Sent Events (SSE) for streaming test progress to the frontend.
  3. **Pipeline Orchestrator:**
     - Coordinates the execution handoff: **Dev 1 (Browser)** $\rightarrow$ **Dev 2 (Rules & Disparity)** $\rightarrow$ **Dev 3 (LLM)**.
* **Isolated Testing:**
  - Test the API and LLM prompts against mocked evidence fixtures without calling live browser sessions:
    ```bash
    pytest tests/test_api_and_llm.py
    uvicorn src.api.main:app --reload --port 8000
    ```

---

### Frontend Dev: Testing Playground & Visual Analytics Dashboard

* **Owned Directory:** `frontend/`
* **Core Responsibilities:**
  1. **Test Runner & Playground View:**
     - Target URL input, workflow step configurator, and profile toggles (Motor, Vision, Cognitive, Assistive).
  2. **Live Execution Tracker:**
     - Real-time stepper displaying current profile run, live Playwright screenshots, and log output.
  3. **Disparity & Bias Matrix Visualizations:**
     - Multi-profile comparison charts (e.g. radar charts, error delta bar charts using Recharts).
     - Visual overlay view: Render target screenshots with bounding boxes highlighting elements with high disparity scores.
  4. **Inspection & Remediation Report:**
     - Categorized findings (Critical, Warning, Info).
     - Expandable LLM reasoning cards with copyable HTML/CSS code diffs.
* **Isolated Testing:**
  - Build and verify the entire UI against static mock data with zero backend running:
    ```bash
    cd frontend
    npm run dev:mock
    ```

---

## 3. Core Data Contracts (The Handoff Schemas)

To guarantee that everyone can work concurrently without blocking, adhere to these three core schemas:

### Contract 1: `RawSessionArtifacts` (Dev 1 $\rightarrow$ Dev 2)
```json
{
  "session_id": "sess_12345",
  "profile_id": "motor_impaired_keyboard_only",
  "url": "https://example.com/checkout",
  "artifacts": {
    "html_path": "data/sessions/sess_12345/dom.html",
    "screenshot_path": "data/sessions/sess_12345/screenshot.png",
    "a11y_tree_path": "data/sessions/sess_12345/a11y_tree.json"
  },
  "telemetry": {
    "completion_time_ms": 14200,
    "task_completed": false,
    "total_clicks": 8,
    "dead_clicks": 3,
    "keyboard_nav_steps": 24
  }
}
```

### Contract 2: `EvidenceRecord` & `DisparityMatrix` (Dev 2 $\rightarrow$ Dev 3)
```json
{
  "evidence": [
    {
      "element_selector": "button#submit-order",
      "bounding_box": {"x": 120, "y": 450, "width": 24, "height": 22},
      "rule_id": "TOUCH_TARGET_TOO_SMALL",
      "severity": "CRITICAL",
      "metric_value": "24x22px",
      "recommended_min": "48x48px"
    }
  ],
  "disparities": [
    {
      "metric": "task_completion_rate",
      "baseline_value": 1.0,
      "constrained_value": 0.25,
      "disparity_ratio": 4.0,
      "disadvantaged_group": "motor_impaired"
    }
  ]
}
```

### Contract 3: `FinalReportResponse` (Dev 3 $\rightarrow$ Frontend)
```json
{
  "report_id": "rep_9876",
  "target_url": "https://example.com/checkout",
  "overall_fairness_score": 62,
  "profiles_tested": ["baseline_default", "motor_impaired", "low_vision"],
  "disparities": [...],
  "findings": [
    {
      "id": "find_1",
      "title": "Checkout button fails minimum touch target size",
      "severity": "CRITICAL",
      "affected_profiles": ["motor_impaired"],
      "diagnosis": "The button is 24x22px, leading to a 300% increase in missed clicks during simulated tremor navigation.",
      "remediation_diff": "```css\n- padding: 4px 8px;\n+ padding: 14px 24px; min-height: 48px; min-width: 48px;\n```"
    }
  ]
}
```

---

## 4. Execution Milestones & Phasing

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: CONTRACT LOCK & MOCK FIXTURES (Day 1)                               │
│ • Commit Pydantic schemas & static JSON files to tests/fixtures/             │
│ • Frontend runs `npm run dev:mock` reading mock_report.json                  │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼───────────────────────────────────────┐
│ PHASE 2: PARALLEL MODULE BUILD (Day 2 - 3)                                   │
│ • Dev 1: Playwright runner & profile constraint simulator                    │
│ • Dev 2: Text/Vision/A11y analyzers & disparity calculation engine           │
│ • Dev 3: LLM prompt chains & FastAPI test orchestration routes               │
│ • Frontend: Dashboard, radar charts, and interactive report viewer           │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼───────────────────────────────────────┐
│ PHASE 3: INTEGRATION & BENCHMARKING (Day 4)                                  │
│ • Hook up Dev 1 -> Dev 2 -> Dev 3 pipeline                                   │
│ • Connect Next.js frontend to live FastAPI endpoints                         │
│ • Run test benchmarks across 3 reference websites                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Offline Testing Quick Reference

Every team member can test their own module locally at any time:

```bash
# 1. Dev 1 — Test browser automation with local fixtures
pytest tests/test_browser.py

# 2. Dev 2 — Test rule engine and disparity math offline (< 1 sec)
pytest tests/test_rules.py

# 3. Dev 3 — Test LLM prompt parsing and API endpoints
pytest tests/test_api.py

# 4. Frontend — Run dev server with static mock data (no backend needed)
cd frontend && npm run dev:mock
```
