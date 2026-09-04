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

Modules communicate exclusively through versioned files on disk (GeoJSON and JSON) and lightweight database tables.

```
[ Dev 1: Geo Engine ]  ──────>  geo_features.geojson  ──────┐
                                                           │
[ Dev 2: Workforce Engine ] ──>  workforce_metrics.json ───┼──> [ Dev 3: Scoring, DB & API ] ──> gap_analysis.json
                                                           │                                            │
                                                           │                                            ▼
                                                           └───────────────────[ Dev 4: Frontend (via Mock JSON) ]
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

### Module 3: Gap Scoring, Database & API Service (`src/scoring/`, `src/db/` & `src/api/`)
* **Owner:** Backend Developer 3 (25% Workload)
* **Domain:** Algorithmic modeling, "What-If" simulation, database schemas, authentication, and API endpoints.
* **Key Tasks:**
  - **Gap Scoring Algorithm:** Implement the mathematical model cross-referencing spatial access ($A$, from Dev 1) with female workforce density ($W$, from Dev 2) to produce the normalized **Facility Desert Index** (0–100).
  - **Simulation Engine:** Implement "What-If" logic calculating score deltas when hypothetical facilities (streetlights, transit hubs) are introduced at given coordinates.
  - **Database & Auth (Sign-in):** SQLite / SQLModel schemas (`User`, `SavedScenario`), password hashing, JWT creation, and auth routes (`/api/auth/login`, `/api/auth/register`, `/api/auth/me`).
  - **DB Seeding CLI:** Ingestion script to seed Dev 1 & Dev 2's JSON/GeoJSON outputs directly into the DB tables.
  - **FastAPI Layer:** REST endpoints for GeoJSON spatial data, workforce metrics, auth, and real-time simulation requests, with automatic fallback to mock payloads.
* **CLI & API Contract:**
  ```bash
  # Standalone self-test of scoring math & simulation:
  python -m src.scoring --test

  # Initialize and seed database:
  python -m src.db --init
  python -m src.db --seed

  # Standalone self-test of API routes and Auth against mock data:
  python -m src.api --test
  python -m src.api --test-auth

  # Start development server:
  uvicorn src.api.main:app --reload --port 8000
  ```
* **Output Artifact:** `data/gap_analysis.json`, `coherence.db`, and REST endpoints.

---

### Module 4: Geospatial & Analytics UI (`frontend/`)
* **Owner:** Frontend Developer (25% Workload)
* **Domain:** Interactive map, visual charts, simulation controls, auth UI, and filter interface.
* **Key Tasks:**
  - **Interactive Map View (Layer A):** Choropleth visualization of facility desert zones + clickable POI facility markers using MapLibre GL / Mapbox.
  - **Workforce Analytics View (Layer B):** Clean charts displaying regional FLFPR, sector distributions, and gap rankings using Recharts / Chart.js.
  - **Simulation Drawer:** Interactive UI controls to simulate adding public infrastructure and visualize score improvements.
  - **Auth Integration:** Login/Register modal, storing JWT in `localStorage`/cookies, and route protection for planner-specific dashboards.
* **CLI / Script Contract:**
  ```bash
  # Run frontend purely on local mock JSON (zero backend dependency):
  npm run dev:mock

  # Headless test runner to verify components render with mock data:
  npm run test
  ```

---

## 4. Database Architecture & Authentication Strategy

CoHERence handles two distinct categories of data:

```
                          DATABASE (SQLite via SQLModel)
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
   1. Analytical / GIS Data                         2. User & Session Data
   (Read-heavy, populated by Dev 1 & 2)             (Read/Write, handled by Dev 3)
   ──────────────────────────────────               ──────────────────────────────
   • Facilities (toilets, lights, transit)          • Users (email, hashed password, role)
   • Ward / District Boundaries                     • User Roles (Urban Planner, NGO, Admin)
   • Workforce Indicators (PLFS/Census)             • Saved "What-If" Simulations
   • Precomputed Gap / Desert Scores                • Bookmarked / Exported Reports
```

### Who Handles What?
1. **Backend Dev 3 (Owner):** 
   - Defines database tables using **SQLModel / SQLAlchemy**.
   - Handles password hashing (`passlib[bcrypt]`) and JWT token issuing (`python-jose`).
   - Implements authentication endpoints (`/api/auth/register`, `/api/auth/login`, `/api/auth/me`).
   - Implements scenarios endpoints (`/api/scenarios/save`, `/api/scenarios/list`).
2. **Frontend Dev 4:** 
   - Builds the Login/Register modal.
   - Saves the bearer token on login and attaches `Authorization: Bearer <token>` to protected API requests.
3. **Backend Dev 1 & 2:** 
   - Do NOT need to write SQL queries. They output standardized GeoJSON / JSON files, which Dev 3's seed script imports.

### Recommended Stack (Zero Docker Overhead)
* **SQLite + SQLModel:**
  - Stored in a single local file (`coherence.db`).
  - Zero server configuration, zero Docker RAM overhead, and native Python support.
  - Seamless migration path: changing the connection string to `postgresql://...` converts it into production PostgreSQL/Supabase without rewriting queries.
* **Mock Auth Bypass for Teammates:**
  - To prevent auth from blocking other developers during testing, Dev 3 includes an optional bypass flag (`--no-auth`) or pre-configured `MOCK_BEARER_TOKEN` in the API service.

---

## 5. Mandatory Pre-Report Test Protocol

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

   # Example: Anyone can verify Dev 3's DB and Auth in 2 seconds
   python -m src.api --test-auth
   ```

---

## 6. Development Environment: `venv` Over Docker

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
