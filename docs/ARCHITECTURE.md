# Architecture

## 1. Requirements coverage

| Requirement | Where | How |
|---|---|---|
| Inputs: origin, destination, departure time, load | `SearchForm.tsx`, `PlaceInput.tsx` | Typeahead geocoding, `datetime-local`, load in lb. Validated again by the API serializer. |
| 3 route options from a routing API | `providers.get_routes` | OSRM alternatives; if fewer than 3 distinct routes, via-point detours are added. Duplicates are removed by geometry similarity. |
| Weather every 10 / 25 / 50 miles at the truck's ETA | `geo.make_checkpoints`, `weather.at_time` | Spacing by trip length (<100 mi: 10, 100-300: 25, >300: 50). ETA is proportional to distance, and the forecast hour nearest the ETA is used. |
| Risk from the provided rules | `risk.classify` | Wind / rain / snow bands, worst one wins, then the load overrides raise it. |
| Recommend best route | `recommend.py` | Lexicographic: Severe miles, High miles, average risk, duration. No Travel miles are compared first (my addition). |
| Map with routes, checkpoints, risk, ETAs, summaries | `MapView.tsx`, `RouteCards.tsx` | Route lines, risk-coloured checkpoints with popups, summary cards, checkpoint table. |
| Heatmap with 0-48 h slider | `service._grid`, `HeatmapControl.tsx` | Grid along the corridor with 49 hourly scores per point, preloaded; the slider swaps one GeoJSON source. |
| Deliverables | GitHub, Pages, Render | Frontend on GitHub Pages, backend on Render. |

## 2. System overview

```mermaid
flowchart LR
    subgraph Browser["Browser: GitHub Pages"]
        UI["React + TypeScript<br/>form, route cards, slider"]
        MAP["MapLibre GL<br/>routes, checkpoints, heatmap"]
        UI --- MAP
    end

    subgraph API["Django REST API: Render"]
        V["views.py<br/>validation"]
        S["service.py<br/>orchestration"]
        R["risk.py<br/>classify"]
        G["geo.py<br/>sampling and ETA"]
        RC["recommend.py<br/>ranking"]
        V --> S
        S --> G
        S --> R
        S --> RC
    end

    subgraph Ext["Free third-party APIs"]
        OSRM["OSRM<br/>routes"]
        GEO["Photon / Nominatim / Open-Meteo<br/>geocoding"]
        WX["Open-Meteo<br/>hourly forecast"]
    end

    UI -- "POST /api/analyze" --> V
    UI -- "GET /api/geocode" --> V
    S --> OSRM
    S --> WX
    V --> GEO
```

## 3. What happens on one request

```mermaid
sequenceDiagram
    participant U as User
    participant FE as React app
    participant BE as Django service
    participant OS as OSRM
    participant OM as Open-Meteo

    U->>FE: origin, destination, time, load
    FE->>BE: POST /api/analyze
    BE->>OS: routes with alternatives
    OS-->>BE: up to 3 geometries
    Note over BE: add detour routes if fewer than 3, drop duplicates
    Note over BE: checkpoints every 10/25/50 mi with ETA each
    BE->>OM: one batched call, checkpoints plus heatmap grid, cached 15 min
    OM-->>BE: hourly wind, rain, snow
    Note over BE: pick forecast hour nearest each ETA, classify risk, summarize miles per level, rank
    BE-->>FE: routes, checkpoints, recommendation, heatmap scores for 49 h
    FE-->>U: map, cards, slider with no further requests
```

## 4. Risk classification (per checkpoint)

```mermaid
flowchart TD
    A["Checkpoint weather at ETA<br/>wind mph, rain in/hr, snow in/hr"] --> B["Band each condition<br/>Low, Moderate, High, Severe, No Travel"]
    B --> C["Take the worst of the three"]
    C --> D{"Wind 55 mph or more?"}
    D -- yes --> NT["No Travel"]
    D -- no --> E{"Wind 45 to 54 mph<br/>and load over 30,000 lb?"}
    E -- yes --> NT
    E -- no --> F{"Wind 35 to 44 mph<br/>and load over 40,000 lb?"}
    F -- yes --> SV["raise to at least Severe"]
    F -- no --> OUT["keep worst-of-three level"]
```

## 5. Route recommendation

```mermaid
flowchart LR
    CP["Checkpoints<br/>risk and segment miles"] --> SUM["Per route: miles at each level,<br/>mile-weighted average risk"]
    SUM --> K["Sort key, lowest wins:<br/>1. No Travel miles<br/>2. Severe miles<br/>3. High miles<br/>4. Average risk<br/>5. Duration"]
    K --> REC["Recommended route<br/>plus a one-line reason"]
```

Each checkpoint represents half the distance to each neighbour, so miles per risk level add up to the route length.

## 6. Heatmap data flow

```mermaid
flowchart LR
    A["Route polylines"] --> B["Grid: every 15 mi along each route,<br/>12 mi to either side, max 240 points"]
    B --> C["Forecast for each point, 49 hours"]
    C --> D["Risk score 0-4 per point per hour<br/>same classify function and load"]
    D --> E["Sent once with the analysis"]
    E --> F["Slider changes the hour"]
    F --> G["setData on one GeoJSON source,<br/>one update per frame, no network"]
```

## Design decisions

- **Pure functions for logic.** `risk.py`, `geo.py` and `recommend.py` have no I/O, so the rules are covered by fast unit tests.
- **One response, no slider requests.** The heatmap ships with the analysis so scrubbing stays smooth.
- **Blurred circles, not a density heatmap.** Colour always means the real risk level and does not inflate where points overlap.
- **Resilience.** Weather calls are batched, cached and parallel; geocoding falls back across three providers.
