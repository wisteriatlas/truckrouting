"""Geometry helpers: distances, polyline sampling, ETAs."""
import math
from datetime import datetime, timedelta

EARTH_MI = 3958.8


def haversine_mi(a, b) -> float:
    """a, b are (lat, lon)."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_MI * math.asin(math.sqrt(h))


def cumulative_miles(points):
    out = [0.0]
    for p, q in zip(points, points[1:]):
        out.append(out[-1] + haversine_mi(p, q))
    return out


def point_at(points, cum, target):
    """Interpolated (lat, lon) at `target` miles along the polyline."""
    if target <= 0:
        return points[0]
    if target >= cum[-1]:
        return points[-1]
    lo, hi = 0, len(cum) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cum[mid] <= target:
            lo = mid
        else:
            hi = mid
    span = cum[hi] - cum[lo] or 1e-9
    t = (target - cum[lo]) / span
    return (points[lo][0] + (points[hi][0] - points[lo][0]) * t,
            points[lo][1] + (points[hi][1] - points[lo][1]) * t)


def sample_interval_mi(total_mi: float) -> int:
    """Checkpoint spacing picked by trip length (10 / 25 / 50 miles)."""
    if total_mi < 100:
        return 10
    if total_mi <= 300:
        return 25
    return 50


def sample_marks(total: float, interval: float):
    marks = [0.0]
    m = interval
    while m < total - interval * 0.25:
        marks.append(m)
        m += interval
    if total > 0:
        marks.append(total)
    return marks


def make_checkpoints(points, duration_s: float, departure: datetime, interval=None):
    """Checkpoints every `interval` miles (plus start and end) with ETA and the
    number of route miles each one represents."""
    cum = cumulative_miles(points)
    total = cum[-1]
    interval = interval or sample_interval_mi(total)
    marks = sample_marks(total, interval)
    cps = []
    for i, mile in enumerate(marks):
        left = (mile - marks[i - 1]) / 2 if i > 0 else 0.0
        right = (marks[i + 1] - mile) / 2 if i < len(marks) - 1 else 0.0
        lat, lon = point_at(points, cum, mile)
        frac = mile / total if total else 0
        cps.append({
            "mile": round(mile, 1),
            "lat": lat,
            "lon": lon,
            "eta": departure + timedelta(seconds=duration_s * frac),
            "segment_miles": left + right,
        })
    return cps


def offset_point(lat, lon, bearing_deg, miles):
    d = miles / EARTH_MI
    b = math.radians(bearing_deg)
    la1, lo1 = math.radians(lat), math.radians(lon)
    la2 = math.asin(math.sin(la1) * math.cos(d) + math.cos(la1) * math.sin(d) * math.cos(b))
    lo2 = lo1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(la1), math.cos(d) - math.sin(la1) * math.sin(la2))
    return math.degrees(la2), math.degrees(lo2)


def bearing(a, b) -> float:
    la1, la2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    y = math.sin(dl) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360
