# CoHERence — The World Redesigned for Her

> Source: `The World Redesigned for her (1) (1).pdf` (8-page pitch deck)

A geospatial + workforce-data platform that makes gender-blind spots in public
infrastructure measurable, so planners can see exactly where and what to fix first.

---

## 1. Problem Domain

- **Male-default design bias** — urban and policy infrastructure is planned
  without gender-disaggregated data.
- **Spatial gender-blind spots** — public facility provisioning shows no
  correlation between women's workplace geography and access to essential services.
- **Implicit linguistic bias** — sector documents and legal drafts carry it,
  largely undetected due to the absence of systematic bias auditing.
- **No consolidated workforce data** — the lack of gender-disaggregated figures
  limits evidence-based policy targeting.
- **Algorithmic amplification** — ML systems trained on this same biased data
  risk amplifying it in welfare, hiring, and credit-scoring pipelines.

## 2. Proposed Solution

Two layers that together turn scattered, invisible gaps into a single prioritized,
data-backed view.

### Layer A — Facility Gap Mapping
A geospatial platform that maps **where women work** and cross-references it
against essential public infrastructure — safety, childcare, healthcare, transit.
It flags **facility deserts**: zones with high female workforce presence but low
access to essential services.

### Layer B — Workforce Data Dashboard
A workforce data layer consolidating gender-disaggregated data — tracking
**working, educated, and non-working women** across regions and sectors.

## 3. Relevance to the Track

A literal build of the track's premise — not referenced in spirit, but
operationalized as the redesign instrument itself.

- **Facility Gap Mapping** answers the spatial claim directly: geospatial,
  block-by-block visibility into where infrastructure wasn't built around her routine.
- **Workforce Data Dashboard** redesigns the data layer: surfacing metrics on
  working, educated, and unemployed women who existed but were never tallied.

The solution doesn't patch one symptom — it redesigns the structural layers where
the gap was hiding.

## 4. Innovation and Originality

| Claim | What it means |
|---|---|
| **Cross-domain integration** | Unifies spatial equity mapping (GIS) with gender-disaggregated workforce analytics in a single operational pipeline — existing tools address these in isolation. |
| **Closed-loop design** | Facility gaps identified spatially connect directly to workforce data, turning fragmented observations into one prioritized, actionable view. |
| **Qualitative → measurable** | Converts "the world isn't built for her" from anecdotal experience into a quantifiable, trackable **gap score**. |
| **Built for adoption** | Designed to plug into existing public data systems rather than function as a standalone prototype — impact scales with reuse, not just relevance. |

## 5. Feasibility — Data Sources

| Layer | Source |
|---|---|
| Roads, transit, footpaths | OpenStreetMap (Geofabrik / QuickOSM extracts) — strong coverage for Indian cities |
| Facilities (toilets, hospitals, streetlights) | OSM tags + VIIRS Nighttime Lights for lighting gaps; regional open-data portals for depth |
| Workforce | PLFS + Census microdata — public datasets with employment, education, and workplace-location fields at district level |
| Pedestrian density | No direct open layer — modeled via OSM footway density + WorldPop + night lights as proxy |
| Safety / surveillance | **Acknowledged gap** — largely non-public; approached via proxy indicators (facility density, lighting coverage) |

## 6. Potential Impact

- **Individual** — fewer invisible risk calculations, detours, and safety
  trade-offs baked into a woman's daily commute.
- **Retention** — closes the gap between a woman staying in the workforce or
  dropping out due to unsafe or exhausting daily conditions; directly tied to
  female labour force participation.
- **Scalability** — fully GIS-based and interoperable with existing public data
  systems; any district or state with facility data can run the same gap analysis.
- **Evidence-based governance** — replaces guesswork with real,
  gender-disaggregated numbers on working, educated, and non-working women.
- **Structural shift** — moves from reactive, anecdotal response to default,
  structural planning: the same standard already applied to everyone else.

---

## Supporting Context

The deck includes a chart page on **India's female labour force participation
rate (%)**, noting that female workforce participation varies significantly from
state to state. (Image-only in the source PDF — figures not extractable.)
