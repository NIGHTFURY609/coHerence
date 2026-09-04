# CoHERence — The World Redesigned for Her

A geospatial and workforce-data intelligence platform that makes gender-blind spots in public infrastructure measurable, empowering urban planners and policymakers to identify and prioritize essential civic interventions.

---

## Overview

Public infrastructure is frequently planned around a male-default routine, lacking gender-disaggregated spatial and workforce data. As a result, critical services—such as well-lit transit corridors, public sanitation, childcare, and healthcare—are often missing where working women need them most.

**CoHERence** bridges this gap by unifying spatial equity mapping with gender-disaggregated workforce analytics into an actionable decision-making platform:

- **Layer A — Facility Gap Mapping (GIS):** Cross-references female workplace presence with public infrastructure (OpenStreetMap, VIIRS night lights, transit routes) to identify and visualize **"Facility Deserts"**.
- **Layer B — Workforce Analytics Dashboard:** Ingests and normalizes national microdata (PLFS, Census) to track female labor force participation (FLFPR), sectoral employment, and education-to-work ratios across districts and wards.
- **The Gap Score Index:** A mathematical score quantifying infrastructure deficiency against female workforce concentration to prioritize municipal spending.
- **"What-If" Infrastructure Simulator:** Allows planners to test civic interventions (e.g., adding streetlights, bus stops, or childcare facilities) and evaluate projected safety and accessibility score improvements in real time.

---

## System Architecture

```
                                  ┌────────────────────────┐
                                  │      Frontend UI       │
                                  │ Next.js + MapLibre GL  │
                                  │   + Recharts + Tailwind│
                                  └───────────┬────────────┘
                                              │ REST API / GeoJSON
                                  ┌───────────▼────────────┐
                                  │    FastAPI Gateway     │
                                  │ Auth, Routes, Cache    │
                                  └─────┬────────────┬─────┘
                                        │            │
             ┌──────────────────────────┴─┐        ┌─┴──────────────────────────┐
             ▼                            ▼        ▼                            ▼
   ┌───────────────────┐        ┌───────────────────┐                 ┌───────────────────┐
   │ Geospatial Engine │        │ Workforce Engine  │                 │  Scoring Engine   │
   │  OSM Ingestion    │        │ PLFS / Census ETL │                 │ Gap Index & Math  │
   │  Buffer & Density │        │ Normalization     │                 │ What-If Simulator │
   └───────────────────┘        └───────────────────┘                 └───────────────────┘
```

---

## Core Principles

- **Modularity:** Every subsystem operates independently with its own CLI interface and bundled mock test runner.
- **Offline / Mock Testing:** Every module can be developed and verified end-to-end using synthetic fixtures without depending on other services or live internet connections.
- **Lightweight Development:** Runs natively using a Python virtual environment (`venv`) and Node.js—eliminating heavy Docker overhead during local development.

---

## Project Structure

```
.
├── src/
│   ├── geo/           # Geospatial processing, OSM parser, spatial buffers & density
│   ├── workforce/     # PLFS & Census microdata ingestion and demographic indicators
│   ├── scoring/       # Gap score calculation algorithm & "What-If" simulation engine
│   ├── db/            # SQLite / SQLModel schemas, migrations, and seed scripts
│   └── api/           # FastAPI application, authentication, and REST routes
├── frontend/          # Next.js / React application, MapLibre GIS viewer, and charts
├── data/              # Data storage (GeoJSON outputs, normalized JSON tables, DB)
└── tests/             # Shared fixtures and integration tests
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup

1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run module self-tests (verifies with bundled mock datasets in `< 3s`):
   ```bash
   # Test Geospatial Engine
   python -m src.geo --test

   # Test Workforce Analytics Engine
   python -m src.workforce --test

   # Test Scoring & Simulation Engine
   python -m src.scoring --test

   # Test Database & Authentication
   python -m src.api --test-auth
   ```

4. Start the API server:
   ```bash
   uvicorn src.api.main:app --reload --port 8000
   ```
   Interactive API documentation will be available at `http://localhost:8000/docs`.

### 2. Frontend Setup

1. Navigate to the frontend directory and install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the development server with mock data:
   ```bash
   npm run dev:mock
   ```
   Open `http://localhost:3000` to view the application.

---

## License

This project is licensed under the MIT License.
