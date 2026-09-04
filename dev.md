# CoHERence — Development Architecture & Team Division

This document outlines the modular team division, contracts, and testing protocols for the CoHERence project based on [docs/project-brief.md](file:///home/light/Documents/.hack/docs/project-brief.md).

---

## 1. Core Principles

| Principle | Meaning in Practice |
| :--- | :--- |
| **Equality** | Workload is split 25% across all 4 developers (3 Backend : 1 Frontend). Each role owns a complete, intellectually challenging domain slice rather than superficial boilerplate or glue code. |
| **Modularity** | Every module is strictly decoupled. No developer ever needs another teammate's server or code running to develop, modify, or test their component. |
| **Flexibility** | Every module features a dual-mode CLI interface: switch between embedded dummy data (`--test`) and production datasets (`--input <path>`) with a single flag. |

---

## 2. Architecture & Data Flow Contract

Modules communicate exclusively through versioned files on disk (GeoJSON and JSON).

```
[ Dev 1: Geo Engine ]  ──────>  geo_features.geojson  ──────┐
                                                           │
[ Dev 2: Workforce Engine ] ──>  workforce_metrics.json ───┼──> [ Dev 3: Scoring & API ] ──> gap_analysis.json
                                                           │                                      │
                                                           │                                      ▼
                                                           └─────────────[ Dev 4: Frontend (via Mock JSON) ]
```

---

## 3. Team Workload & Module Specifications

### Module 1: Geospatial Processing Engine (`src/geo/`)
* **Owner:** Backend Developer 1 (25% Workload)
* **Domain:** Spatial data ingestion, geometry cleaning, spatial indexing, and proximity analysis.
* **Key Tasks:**
  - Pull and parse OpenStreetMap (OSM) extracts (public toilets, streetlights, transit stops, footpaths, health centers).
  - Compute spatial buffers (500m/1km walking radii) and infrastructure density.
  - Implement spatial indexing (H3 hexagons or bounding-box grid cells).
  - Proxy modeling (VIIRS night lights / pedestrian density indicators).
* **CLI Contract:**
  ```bash
  # Standalone self-test with bundled dummy OSM fixture:
  python -m src.geo --test

  # Production run with real raw OSM data:
  python -m src.geo --input data/osm_raw.xml --output data/geo_features.geojson
  ```
* **Output Artifact:** `data/geo_features.geojson` (zones/cells containing facility counts, lighting proxies, and distance to nearest transit).

---

### Module 2: Workforce Analytics Engine (`src/workforce/`)
* **Owner:** Backend Developer 2 (25% Workload)
* **Domain:** Microdata wrangling, demographic normalization, and workforce metric calculations.
* **Key Tasks:**
  - Ingest and clean PLFS (Periodic Labour Force Survey) and Census microdata tables.
  - Compute gender-disaggregated indicators: Female Labour Force Participation Rate (FLFPR), sectoral breakdown (formal vs. informal), and education-to-employment ratios.
  - Aggregate statistics to standardized administrative units (ward/district levels).
* **CLI Contract:**
  ```bash
  # Standalone self-test with bundled dummy survey fixture:
  python -m src.workforce --test

  # Production run with real survey data:
  python -m src.workforce --input data/plfs_raw.csv --output data/workforce_metrics.json
  ```
* **Output Artifact:** `data/workforce_metrics.json` (normalized metrics keyed by `district_id` / `ward_id`).

---

### Module 3: Gap Scoring, Simulation & API Service (`src/scoring/` & `src/api/`)
* **Owner:** Backend Developer 3 (25% Workload)
* **Domain:** Algorithmic modeling, "What-If" scenario simulation, and API endpoint delivery.
* **Key Tasks:**
  - **Gap Scoring Algorithm:** Implement the mathematical model cross-referencing spatial access ($A$, from Dev 1) with female workforce density ($W$, from Dev 2) to produce the normalized **Facility Desert Index** (0–100).
  - **Simulation Engine:** Implement "What-If" logic calculating score deltas when hypothetical facilities (streetlights, transit hubs) are introduced at given coordinates.
  - **FastAPI Layer:** REST endpoints for GeoJSON spatial data, workforce metrics, and real-time simulation requests, with automatic fallback to mock payloads.
* **CLI & API Contract:**
  ```bash
  # Standalone self-test of scoring math & simulation:
  python -m src.scoring --test

  # Standalone self-test of API routes against mock data:
  python -m src.api --test

  # Start development server:
  uvicorn src.api.main:app --reload --port 8000
  ```
* **Output Artifact:** `data/gap_analysis.json` and REST endpoints.

---

### Module 4: Geospatial & Analytics UI (`frontend/`)
* **Owner:** Frontend Developer (25% Workload)
* **Domain:** Interactive map, visual charts, simulation controls, and filter interface.
* **Key Tasks:**
  - **Interactive Map View (Layer A):** Choropleth visualization of facility desert zones + clickable POI facility markers using MapLibre GL / Mapbox.
  - **Workforce Analytics View (Layer B):** Clean charts displaying regional FLFPR, sector distributions, and gap rankings using Recharts / Chart.js.
  - **Simulation Drawer:** Interactive UI controls to simulate adding public infrastructure and visualize score improvements.
* **CLI / Script Contract:**
  ```bash
  # Run frontend purely on local mock JSON (zero backend dependency):
  npm run dev:mock

  # Headless test runner to verify components render with mock data:
  npm run test
  ```

---

## 4. Mandatory Pre-Report Test Protocol

To ensure code quality and independence, every developer must follow this 3-step cycle before reporting progress or submitting code:

```
[ Step 1: Code & Modify ] ──> [ Step 2: Run CLI --test (Mock) ] ──> [ Step 3: Report with Output ]
```

1. **Isolated Execution:** The developer modifies code in their assigned module.
2. **Local Test Execution:** The developer runs their module's `--test` harness:
   - Must run in `< 3 seconds`.
   - Uses bundled mock fixtures; requires **zero network calls** and **no dependencies on other modules**.
   - Validates mathematical bounds, data normalization, and output schema conformity.
3. **Peer Verification:** Any teammate can review and test another member's branch simply by running their `--test` command:
   ```bash
   # Example: Anyone can verify Dev 1's work in 2 seconds
   python -m src.geo --test
   ```

---

## 5. Development Environment: `venv` Over Docker

* **No Docker overhead:** Docker is not required for local development to avoid memory and CPU bottlenecks during GIS data processing.
* **Python virtual environment:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
* **Frontend:**
  ```bash
  cd frontend
  npm install
  npm run dev:mock
  ```
* **Production / Hackathon Submission:** A single, lightweight `Dockerfile` can be added at the final stage for cloud deployment if required.
