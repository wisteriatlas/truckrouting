from datetime import datetime, timezone

import pytest

from .geo import cumulative_miles, make_checkpoints, sample_interval_mi
from .recommend import recommend, summarize
from .risk import Risk, classify, classify_rain, classify_snow, classify_wind


@pytest.mark.parametrize("mph,expected", [
    (0, Risk.LOW), (24.9, Risk.LOW), (25, Risk.MODERATE), (34.9, Risk.MODERATE),
    (35, Risk.HIGH), (44.9, Risk.HIGH), (45, Risk.SEVERE), (54.9, Risk.SEVERE),
    (55, Risk.NO_TRAVEL), (80, Risk.NO_TRAVEL),
])
def test_wind_bands(mph, expected):
    assert classify_wind(mph) == expected


@pytest.mark.parametrize("v,expected", [
    (0.09, Risk.LOW), (0.10, Risk.MODERATE), (0.25, Risk.HIGH), (0.50, Risk.SEVERE),
    (1.00, Risk.SEVERE), (1.01, Risk.NO_TRAVEL),
])
def test_rain_bands(v, expected):
    assert classify_rain(v) == expected


@pytest.mark.parametrize("v,expected", [
    (0.4, Risk.LOW), (0.5, Risk.MODERATE), (1.0, Risk.HIGH), (2.0, Risk.SEVERE),
    (3.0, Risk.SEVERE), (3.1, Risk.NO_TRAVEL),
])
def test_snow_bands(v, expected):
    assert classify_snow(v) == expected


def test_worst_condition_wins():
    assert classify(10, 0.3, 0.6, 10_000) == Risk.HIGH


def test_wind_55_is_no_travel_for_any_load():
    assert classify(55, 0, 0, 0) == Risk.NO_TRAVEL


def test_severe_wind_with_heavy_load_is_no_travel():
    assert classify(50, 0, 0, 30_001) == Risk.NO_TRAVEL
    assert classify(50, 0, 0, 30_000) == Risk.SEVERE


def test_high_wind_with_very_heavy_load_is_severe():
    assert classify(40, 0, 0, 40_001) == Risk.SEVERE
    assert classify(40, 0, 0, 40_000) == Risk.HIGH
    assert classify(30, 0, 0, 80_000) == Risk.MODERATE


def test_load_rule_never_lowers_risk():
    assert classify(40, 1.5, 0, 50_000) == Risk.NO_TRAVEL


def test_interval_selection():
    assert [sample_interval_mi(x) for x in (50, 99.9, 100, 300, 301)] == [10, 10, 25, 25, 50]


def test_checkpoints_cover_route_and_segments_sum_to_total():
    pts = [(40.0, -100.0 + i * 0.1) for i in range(0, 301)]
    dep = datetime(2026, 1, 1, tzinfo=timezone.utc)
    total = cumulative_miles(pts)[-1]
    cps = make_checkpoints(pts, 3600 * 10, dep, interval=50)
    assert cps[0]["mile"] == 0
    assert cps[-1]["mile"] == pytest.approx(total, abs=0.1)
    assert sum(c["segment_miles"] for c in cps) == pytest.approx(total, rel=1e-6)
    assert (cps[-1]["eta"] - dep).total_seconds() == pytest.approx(36000)
    etas = [c["eta"] for c in cps]
    assert etas == sorted(etas)


def _route(rid, risks, duration=3600):
    cps = [{"risk": r, "segment_miles": 10.0} for r in risks]
    return {"id": rid, "duration_s": duration, "summary": summarize(cps)}


def test_summary_mile_weighting():
    s = summarize([{"risk": Risk.SEVERE, "segment_miles": 5}, {"risk": Risk.LOW, "segment_miles": 15}])
    assert s["severe_miles"] == 5 and s["low_miles"] == 15
    assert s["avg_risk"] == pytest.approx(0.75)


def test_fewest_severe_beats_everything_else():
    a = _route(0, [Risk.SEVERE, Risk.LOW], 1000)
    b = _route(1, [Risk.HIGH, Risk.HIGH, Risk.HIGH], 9000)
    assert recommend([a, b])[0] == 1


def test_then_fewest_high():
    a = _route(0, [Risk.HIGH, Risk.LOW])
    b = _route(1, [Risk.MODERATE, Risk.MODERATE])
    assert recommend([a, b])[0] == 1


def test_then_average_then_time():
    a = _route(0, [Risk.MODERATE, Risk.MODERATE], 5000)
    b = _route(1, [Risk.MODERATE, Risk.LOW], 9000)
    assert recommend([a, b])[0] == 1
    c = _route(0, [Risk.LOW], 9000)
    d = _route(1, [Risk.LOW], 5000)
    assert recommend([c, d])[0] == 1


def test_no_travel_route_is_not_preferred():
    a = _route(0, [Risk.NO_TRAVEL, Risk.LOW])
    b = _route(1, [Risk.SEVERE, Risk.SEVERE])
    assert recommend([a, b])[0] == 1
