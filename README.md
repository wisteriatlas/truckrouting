# Weather-Aware Truck Routing

React + Django app that generates three driving routes, samples the forecast at the truck's
estimated arrival time along each one, classifies weather risk using the load rules, and
recommends the safest route. A 0-48 h heatmap slider shows the corridor weather.

## Live

- App: https://wisteriatlas.github.io/truckrouting/
- API: https://truck-routing-api-owru.onrender.com/api/health (Render free tier: the first request after idle takes ~30-60 s)

## Run locally

```bash
# backend (http://localhost:8000)
cd backend
python -m venv .venv && .venv/Scripts/activate   # source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python manage.py runserver

# frontend (http://localhost:5173, proxies /api to the backend)
cd frontend
npm install
npm run dev
```

Tests: `cd backend && python -m pytest`

No API keys are required. Optional env vars are listed in `backend/.env.example` and
`frontend/.env.example` (`VITE_API_URL` points the frontend at a hosted backend).

## Services used

| Purpose | Service |
|---|---|
| Routing (3 routes) | OSRM public server (`alternatives=3`, plus via-point detours if fewer than 3 distinct routes come back) |
| Geocoding | Photon, falling back to Nominatim and Open-Meteo (Photon refuses some hosted IPs) |
| Weather | Open-Meteo hourly forecast (wind mph, rain in/hr, snowfall in/hr) |
| Map | MapLibre GL JS with OpenStreetMap tiles |

OSRM's profile is for cars, so durations are floored at 62 mph average to be realistic for a truck.
OpenRouteService's truck profile was considered, but its alternative routes only work on short trips.

## How it works

`POST /api/analyze` -> `routing/service.py`:

1. `providers.get_routes` returns up to 3 distinct routes.
2. `geo.make_checkpoints` places a checkpoint every 10 mi (route < 100 mi), 25 mi (100-300 mi) or
   50 mi (> 300 mi), plus the start and end. ETA is proportional to distance along the route.
3. `weather.fetch_hourly` batches Open-Meteo calls (cached 15 min) and `weather.at_time` takes the
   forecast hour nearest each checkpoint's ETA.
4. `risk.classify` returns the worst of wind / rain / snow, then applies the load rules.
5. `recommend.summarize` / `recommend.recommend` aggregate miles per risk level and rank routes.

### Assumptions

- Bands are lower-bound inclusive: wind 25.0 is Moderate, 24.9 is Low. Rain > 1.00 and snow > 3.0 are No Travel.
- Wind >= 55 mph is No Travel for any load. Wind 45-54 mph with a load over 30,000 lb is No Travel.
  Wind 35-44 mph with a load over 40,000 lb is at least Severe. Load rules only raise the level.
- Each checkpoint represents half the distance to its neighbours ("miles" of that risk). Average risk is
  mile-weighted over levels 0 (Low) to 4 (No Travel).
- Ranking: fewest Severe miles, fewest High miles, lowest average risk, shortest time.
  **Addition to the spec:** No Travel miles are compared first, so a route you cannot legally drive never
  beats one you can. If every route has No Travel weather the app says so and suggests delaying.
- Sustained wind (10 m) is used, not gusts.

### Heatmap

The backend returns a grid (<= 240 points, about 12 mi either side of every route) with a risk score
for each of the next 49 hours, in the same response as the analysis. Moving the slider only swaps one
GeoJSON source on the client, with no network requests, throttled to one update per frame. It is drawn
as blurred circles coloured by risk level rather than a density heatmap, so colour always means the
real risk level and does not inflate where points overlap.

## Deploy

- Backend: Render web service (root `backend`; settings are in `render.yaml`, or create it by hand as a
  Free web service). Free tiers sleep, so the first request can be slow.
- Frontend: GitHub Pages via `.github/workflows/pages.yml`. The repo variable `VITE_API_URL` holds the
  backend URL. Set `CORS_ORIGINS` on the backend to `https://wisteriatlas.github.io`.

## Limits

- The public OSRM, Photon and Open-Meteo servers are rate limited and meant for light use.
- Forecasts cover 16 days; ETAs beyond that clamp to the last hour and a warning is shown.
