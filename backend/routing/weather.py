"""Open-Meteo client. Hourly wind (mph), rain (in/hr) and snowfall (in/hr)."""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from django.core.cache import cache

URL = "https://api.open-meteo.com/v1/forecast"
CHUNK = 50
CACHE_TTL = 15 * 60
RETRIES = 3


class WeatherError(Exception):
    pass


def _key(lat, lon, days):
    return f"wx:{days}:{round(lat, 1)}:{round(lon, 1)}"


def _get(params):
    """GET with backoff on 429 / 5xx (Open-Meteo rate limits shared hosts)."""
    for attempt in range(RETRIES + 1):
        try:
            r = requests.get(URL, params=params, timeout=20)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < RETRIES:
                time.sleep(1.5 * 2 ** attempt)
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt >= RETRIES:
                raise WeatherError(f"Weather service unavailable: {e}") from e
            time.sleep(1.5 * 2 ** attempt)


def _fetch_chunk(args):
    points, days = args
    params = {
        "latitude": ",".join(f"{p[0]:.4f}" for p in points),
        "longitude": ",".join(f"{p[1]:.4f}" for p in points),
        "hourly": "wind_speed_10m,rain,snowfall",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "UTC",
        "forecast_days": days,
    }
    data = _get(params).json()
    if isinstance(data, dict):
        data = [data]
    out = []
    for d in data:
        h = d["hourly"]
        out.append({
            "start": datetime.fromisoformat(h["time"][0]).replace(tzinfo=timezone.utc),
            "wind": [v or 0.0 for v in h["wind_speed_10m"]],
            "rain": [v or 0.0 for v in h["rain"]],
            "snow": [v or 0.0 for v in h["snowfall"]],
        })
    return out


def fetch_hourly(points, days=16):
    """points: list of (lat, lon). Returns a same-length list of hourly series.

    `days` limits the forecast window; Open-Meteo's rate limit is weighted by days requested.
    """
    result = [None] * len(points)
    # Points in the same 0.1 degree cell share one request slot and cache entry.
    cells = {}
    for i, (lat, lon) in enumerate(points):
        k = _key(lat, lon, days)
        cached = cache.get(k)
        if cached:
            result[i] = cached
        else:
            cells.setdefault(k, []).append(i)
    keys = list(cells)
    reps = [points[cells[k][0]] for k in keys]
    chunks = [(reps[i:i + CHUNK], days) for i in range(0, len(reps), CHUNK)]
    if chunks:
        with ThreadPoolExecutor(max_workers=3) as ex:
            fetched = [s for part in ex.map(_fetch_chunk, chunks) for s in part]
        for k, series in zip(keys, fetched):
            cache.set(k, series, CACHE_TTL)
            for i in cells[k]:
                result[i] = series
    return result


def index_at(series, when: datetime) -> int:
    hours = (when - series["start"]).total_seconds() / 3600
    return min(max(int(round(hours)), 0), len(series["wind"]) - 1)


def at_time(series, when: datetime):
    """Conditions at the forecast hour nearest `when` (clamped to the range)."""
    i = index_at(series, when)
    return {"wind_mph": series["wind"][i], "rain_in_hr": series["rain"][i], "snow_in_hr": series["snow"][i]}
