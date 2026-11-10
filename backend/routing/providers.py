"""Routing (OSRM) and geocoding (Photon) clients."""
import requests
from django.core.cache import cache

from .geo import bearing, haversine_mi, offset_point

OSRM = "https://router.project-osrm.org/route/v1/driving"
PHOTON = "https://photon.komoot.io/api/"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OPEN_METEO_GEO = "https://geocoding-api.open-meteo.com/v1/search"
M_PER_MI = 1609.344
HEADERS = {"User-Agent": "truck-weather-router/1.0"}
TRUCK_MAX_MPH = 62  # trucks are slower than OSRM's car profile


class ProviderError(Exception):
    pass


def _photon(query, limit):
    r = requests.get(PHOTON, params={"q": query, "limit": limit, "lang": "en", "bbox": "-170,15,-50,72"},
                     headers=HEADERS, timeout=8)
    r.raise_for_status()
    out = []
    for f in r.json().get("features", []):
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        parts = [p.get("name"), p.get("city") if p.get("city") != p.get("name") else None, p.get("state"), p.get("country")]
        out.append({"label": ", ".join(x for x in parts if x), "lat": lat, "lon": lon})
    return out


def _nominatim(query, limit):
    r = requests.get(NOMINATIM, params={"q": query, "format": "jsonv2", "limit": limit, "countrycodes": "us,ca,mx"},
                     headers=HEADERS, timeout=8)
    r.raise_for_status()
    return [{"label": x["display_name"], "lat": float(x["lat"]), "lon": float(x["lon"])} for x in r.json()]


def _open_meteo(query, limit):
    r = requests.get(OPEN_METEO_GEO, params={"name": query, "count": limit, "language": "en"}, headers=HEADERS, timeout=8)
    r.raise_for_status()
    out = []
    for x in r.json().get("results", []):
        parts = [x.get("name"), x.get("admin1"), x.get("country")]
        out.append({"label": ", ".join(p for p in parts if p), "lat": x["latitude"], "lon": x["longitude"]})
    return out


def geocode(query: str, limit: int = 6):
    """Try several free geocoders in turn; hosted IPs are sometimes refused by one of them."""
    key = f"geo:{query.strip().lower()}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    last = None
    for fn in (_photon, _nominatim, _open_meteo):
        try:
            out = fn(query, limit)
        except (requests.RequestException, ValueError, KeyError) as e:
            last = e
            continue
        if out:
            cache.set(key, out, 3600)
            return out
    if last:
        raise ProviderError(f"Geocoding unavailable: {last}")
    return []


def _osrm(coords, alternatives):
    path = ";".join(f"{lon:.5f},{lat:.5f}" for lat, lon in coords)
    params = {"overview": "full", "geometries": "geojson", "steps": "false",
              "alternatives": "3" if alternatives else "false"}
    try:
        r = requests.get(f"{OSRM}/{path}", params=params, headers=HEADERS, timeout=30)
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        raise ProviderError(f"Routing unavailable: {e}") from e
    if data.get("code") != "Ok":
        raise ProviderError(data.get("message") or "No route found between those locations.")
    out = []
    for rt in data["routes"]:
        pts = [(lat, lon) for lon, lat in rt["geometry"]["coordinates"]]
        miles = rt["distance"] / M_PER_MI
        duration = max(rt["duration"], miles / TRUCK_MAX_MPH * 3600)
        out.append({"points": pts, "distance_mi": miles, "duration_s": duration})
    return out


def _similar(a, b, tol_mi=1.5):
    """Routes are duplicates if sampled points stay within tol_mi of each other."""
    n = 25
    for i in range(n):
        pa = a[int(i * (len(a) - 1) / (n - 1))]
        pb = min(b[:: max(1, len(b) // 400)], key=lambda q: (q[0] - pa[0]) ** 2 + (q[1] - pa[1]) ** 2)
        if haversine_mi(pa, pb) > tol_mi:
            return False
    return True


def get_routes(origin, destination, wanted=3):
    """Up to `wanted` distinct routes. OSRM alternatives first, then via-point detours."""
    routes = _osrm([origin, destination], alternatives=True)

    def add(candidates):
        for c in candidates:
            if len(routes) >= wanted:
                return
            if not any(_similar(c["points"], r["points"]) for r in routes):
                routes.append(c)

    if len(routes) < wanted:
        base = routes[0]
        pts = base["points"]
        mid = pts[len(pts) // 2]
        brg = (bearing(origin, destination) + 90) % 360
        span = haversine_mi(origin, destination)
        for frac in (0.15, 0.3):
            for sign in (1, -1):
                if len(routes) >= wanted:
                    break
                via = offset_point(mid[0], mid[1], (brg if sign > 0 else brg + 180) % 360, span * frac)
                try:
                    add(_osrm([origin, via, destination], alternatives=False))
                except ProviderError:
                    continue
    routes = routes[:wanted]
    routes.sort(key=lambda r: r["duration_s"])
    return routes
