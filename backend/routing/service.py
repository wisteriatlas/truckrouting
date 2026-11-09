"""Orchestration: routes -> checkpoints -> weather -> risk -> recommendation."""
from datetime import datetime, timedelta, timezone

from . import providers, weather
from .geo import bearing, cumulative_miles, make_checkpoints, offset_point, point_at
from .recommend import recommend, summarize
from .risk import Risk, classify

HEATMAP_HOURS = 49  # hours 0..48
HEATMAP_MAX_POINTS = 240
GEOMETRY_MAX_POINTS = 700
ROUTE_COLORS = ["#2563eb", "#9333ea", "#0d9488"]


def _decimate(points, limit):
    if len(points) <= limit:
        return points
    step = len(points) / limit
    out = [points[int(i * step)] for i in range(limit)]
    out.append(points[-1])
    return out


def _grid(routes_points, spacing_mi=15, half_width_mi=12):
    """Points across the trip corridor: along each route, with lateral offsets."""
    seen, pts = set(), []
    while True:
        seen.clear()
        pts = []
        for points in routes_points:
            cum = cumulative_miles(points)
            m = 0.0
            while m <= cum[-1]:
                a = point_at(points, cum, m)
                b = point_at(points, cum, min(m + 2, cum[-1]))
                brg = bearing(a, b) if a != b else 0
                for off in (-half_width_mi, 0, half_width_mi):
                    p = a if off == 0 else offset_point(a[0], a[1], (brg + (90 if off > 0 else -90)) % 360, abs(off))
                    cell = (round(p[0] * 5), round(p[1] * 5))  # ~0.2 degree cells
                    if cell not in seen:
                        seen.add(cell)
                        pts.append(p)
                m += spacing_mi
        if len(pts) <= HEATMAP_MAX_POINTS:
            return pts
        spacing_mi *= 1.3


def analyze(origin, destination, departure: datetime, load_lb: float):
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    departure = departure.astimezone(timezone.utc)
    raw_routes = providers.get_routes(origin, destination)

    all_cps = [make_checkpoints(r["points"], r["duration_s"], departure) for r in raw_routes]
    grid = _grid([r["points"] for r in raw_routes])

    cp_points = [(c["lat"], c["lon"]) for cps in all_cps for c in cps]
    series = weather.fetch_hourly(cp_points + grid)
    cp_series, grid_series = series[:len(cp_points)], series[len(cp_points):]

    routes, k = [], 0
    for i, (r, cps) in enumerate(zip(raw_routes, all_cps)):
        out_cps = []
        for c in cps:
            wx = weather.at_time(cp_series[k], c["eta"])
            k += 1
            risk = classify(wx["wind_mph"], wx["rain_in_hr"], wx["snow_in_hr"], load_lb)
            out_cps.append({**c, **wx, "risk": risk})
        summary = summarize(out_cps)
        routes.append({
            "id": i,
            "color": ROUTE_COLORS[i % len(ROUTE_COLORS)],
            "distance_mi": round(r["distance_mi"], 1),
            "duration_s": round(r["duration_s"]),
            "arrival": (departure + timedelta(seconds=r["duration_s"])).isoformat(),
            "geometry": [[round(lon, 5), round(lat, 5)] for lat, lon in _decimate(r["points"], GEOMETRY_MAX_POINTS)],
            "checkpoints": [{
                "mile": c["mile"], "lat": round(c["lat"], 5), "lon": round(c["lon"], 5),
                "eta": c["eta"].isoformat(),
                "wind_mph": round(c["wind_mph"], 1), "rain_in_hr": round(c["rain_in_hr"], 3),
                "snow_in_hr": round(c["snow_in_hr"], 3),
                "risk": int(c["risk"]), "risk_label": c["risk"].label,
            } for c in out_cps],
            "summary": summary,
        })

    best, reason = recommend([{**r, "summary": r["summary"]} for r in routes])
    for r in routes:
        r["recommended"] = r["id"] == best

    # Heatmap: risk score per grid point for forecast hours 0..48 from the current hour.
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    heat = []
    for (lat, lon), s in zip(grid, grid_series):
        scores = []
        for h in range(HEATMAP_HOURS):
            wx = weather.at_time(s, now + timedelta(hours=h))
            scores.append(int(classify(wx["wind_mph"], wx["rain_in_hr"], wx["snow_in_hr"], load_lb)))
        heat.append([round(lat, 4), round(lon, 4), scores])

    warnings = []
    last_arrival = max(departure + timedelta(seconds=r["duration_s"]) for r in raw_routes)
    if departure < now - timedelta(hours=1):
        warnings.append("Departure is in the past; forecast values for the nearest available hour are used.")
    if last_arrival > now + timedelta(days=15):
        warnings.append("Part of the trip is beyond the 16-day forecast; the last available forecast is used.")
    if len(routes) < 3:
        warnings.append(f"Only {len(routes)} distinct route(s) could be found for this trip.")

    return {
        "routes": routes,
        "recommended_id": best,
        "recommendation_reason": reason,
        "heatmap": {"start": now.isoformat(), "hours": HEATMAP_HOURS, "points": heat},
        "warnings": warnings,
    }
