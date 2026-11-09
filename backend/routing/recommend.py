"""Route aggregation and recommendation."""
from .risk import Risk


def summarize(checkpoints):
    """checkpoints: dicts with `risk` (Risk) and `segment_miles`."""
    miles = {r: 0.0 for r in Risk}
    weighted = 0.0
    total = 0.0
    for cp in checkpoints:
        miles[cp["risk"]] += cp["segment_miles"]
        weighted += int(cp["risk"]) * cp["segment_miles"]
        total += cp["segment_miles"]
    return {
        "no_travel_miles": round(miles[Risk.NO_TRAVEL], 1),
        "severe_miles": round(miles[Risk.SEVERE], 1),
        "high_miles": round(miles[Risk.HIGH], 1),
        "moderate_miles": round(miles[Risk.MODERATE], 1),
        "low_miles": round(miles[Risk.LOW], 1),
        "avg_risk": round(weighted / total, 3) if total else 0.0,
        "max_risk": max((cp["risk"] for cp in checkpoints), default=Risk.LOW).label,
    }


def rank_key(route):
    s = route["summary"]
    # No Travel miles first (a route you cannot drive must not win), then the spec's order.
    return (s["no_travel_miles"], s["severe_miles"], s["high_miles"], s["avg_risk"], route["duration_s"])


def recommend(routes):
    """Returns (index_of_best, reason)."""
    if not routes:
        return None, ""
    order = sorted(range(len(routes)), key=lambda i: rank_key(routes[i]))
    best = order[0]
    bs = routes[best]["summary"]
    if bs["no_travel_miles"] > 0:
        return best, "Every route has No Travel weather; this one has the fewest No Travel miles. Consider delaying."
    if len(routes) == 1:
        return best, "Only one route available."
    os_ = routes[order[1]]["summary"]
    if bs["severe_miles"] < os_["severe_miles"]:
        return best, f"Fewest Severe miles ({bs['severe_miles']:.0f} vs {os_['severe_miles']:.0f})."
    if bs["high_miles"] < os_["high_miles"]:
        return best, f"Fewest High-risk miles ({bs['high_miles']:.0f} vs {os_['high_miles']:.0f})."
    if bs["avg_risk"] < os_["avg_risk"]:
        return best, f"Lowest average weather risk ({bs['avg_risk']:.2f} vs {os_['avg_risk']:.2f})."
    return best, "Weather risk is equal across routes; this one is the fastest."
