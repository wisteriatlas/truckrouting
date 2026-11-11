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

```text
 BROWSER (GitHub Pages)             DJANGO API (Render)                  FREE EXTERNAL APIS
+-------------------------+        +---------------------------+        +----------------------------+
| React + TypeScript      |        | views.py    validation    |        | OSRM          routes       |
|  form, route cards,     | -----> |     |                     | -----> | Open-Meteo    hourly       |
|  checkpoint table,      |  POST  |     v                     |        |               forecast     |
|  heatmap slider         |  /api/ | service.py  orchestration |        | Photon / Nominatim /       |
|                         | analyze|     |-- geo.py       sampling + ETA | Open-Meteo    geocoding    |
| MapLibre GL             |        |     |-- risk.py      classify |     +----------------------------+
|  routes, checkpoints,   | <----- |     '-- recommend.py ranking |
|  heatmap layer          |  JSON  |                           |
+-------------------------+        +---------------------------+
        GET /api/geocode  ------>   views.py ------> geocoders
```

## 3. What happens on one request

```text
User -> React: origin, destination, departure time, load
React -> Django: POST /api/analyze

Django:
  1. OSRM            -> up to 3 route geometries
                        (add detour routes if fewer than 3, drop duplicates)
  2. geo.py          -> checkpoints every 10 / 25 / 50 mi, each with an ETA
  3. Open-Meteo      -> ONE batched call: checkpoints + heatmap grid
                        (cached 15 min, fetched in parallel)
  4. weather.py      -> take the forecast hour nearest each ETA
  5. risk.py         -> classify each checkpoint
  6. recommend.py    -> miles per risk level per route, then rank
  7. heatmap         -> risk score per grid point for each of the next 49 hours

Django -> React: routes, checkpoints, recommendation, heatmap scores (one response)
React: draws map + cards; the slider needs no more requests
```

## 4. Risk classification (per checkpoint)

```text
 weather at ETA (wind mph, rain in/hr, snow in/hr)
        |
        v
 band each condition:  Low | Moderate | High | Severe | No Travel
        |
        v
 take the WORST of the three
        |
        v
 wind >= 55 mph?  ------------------------------ yes --> NO TRAVEL
        | no
        v
 wind 45-54 mph AND load > 30,000 lb?  ---------- yes --> NO TRAVEL
        | no
        v
 wind 35-44 mph AND load > 40,000 lb?  ---------- yes --> at least SEVERE
        | no
        v
 keep the worst-of-three level
```

Load rules only raise the level, never lower it.

## 5. Route recommendation

```text
 checkpoints (risk level + segment miles)
        |
        v
 per route: miles at each level, mile-weighted average risk
        |
        v
 sort, lowest wins, comparing in this order:
   1. No Travel miles      (my addition: an undrivable route must not win)
   2. Severe miles
   3. High miles
   4. Average risk
   5. Duration
        |
        v
 recommended route + one-line reason
```

Each checkpoint represents half the distance to each neighbour, so miles per risk level add up to the route length.

## 6. Heatmap data flow

```text
 route polylines
      |
      v
 grid: every 15 mi along each route, 12 mi to either side (max 240 points)
      |
      v
 forecast for every grid point, 49 hours
      |
      v
 risk score 0-4 per point per hour (same classify(), same load)
      |
      v
 sent ONCE with the analysis response
      |
      v
 slider changes the hour --> setData on one GeoJSON source
                             (one update per frame, no network)
```

## Design decisions

- **Pure functions for logic.** `risk.py`, `geo.py` and `recommend.py` have no I/O, so the rules are covered by fast unit tests.
- **One response, no slider requests.** The heatmap ships with the analysis so scrubbing stays smooth.
- **Blurred circles, not a density heatmap.** Colour always means the real risk level and does not inflate where points overlap.
- **Resilience.** Weather calls are batched, cached and parallel; geocoding falls back across three providers.
