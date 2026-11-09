"""Weather risk classification. Pure functions, no I/O."""
from enum import IntEnum


class Risk(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


# Lower bounds (inclusive) of Moderate, High, Severe, No Travel for each condition.
WIND_BOUNDS = (25.0, 35.0, 45.0, 55.0)     # mph
RAIN_BOUNDS = (0.10, 0.25, 0.50, 1.00001)  # in/hr, "No Travel" is strictly > 1.00
SNOW_BOUNDS = (0.5, 1.0, 2.0, 3.00001)     # in/hr, "No Travel" is strictly > 3.0

HEAVY_LOAD_SEVERE_LB = 40_000     # with wind 35-44 mph -> at least Severe
HEAVY_LOAD_NO_TRAVEL_LB = 30_000  # with wind 45-54 mph -> No Travel


def _band(value: float, bounds) -> Risk:
    level = Risk.LOW
    for i, lower in enumerate(bounds):
        if value >= lower:
            level = Risk(i + 1)
    return level


def classify_wind(mph: float) -> Risk:
    return _band(mph, WIND_BOUNDS)


def classify_rain(in_hr: float) -> Risk:
    return _band(in_hr, RAIN_BOUNDS)


def classify_snow(in_hr: float) -> Risk:
    return _band(in_hr, SNOW_BOUNDS)


def classify(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_lb: float) -> Risk:
    """Worst of the three conditions, then raised by the load rules."""
    wind = classify_wind(wind_mph)
    level = max(wind, classify_rain(rain_in_hr), classify_snow(snow_in_hr))
    if wind == Risk.SEVERE and load_lb > HEAVY_LOAD_NO_TRAVEL_LB:
        level = Risk.NO_TRAVEL
    elif wind == Risk.HIGH and load_lb > HEAVY_LOAD_SEVERE_LB:
        level = max(level, Risk.SEVERE)
    return level
