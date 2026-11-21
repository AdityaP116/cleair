from typing import Tuple

# Measurement range boundaries
BOUNDARIES = {
    "PM2.5": {"min": 0.0, "max": 1000.0, "unit": "ug/m3"},
    "PM10": {"min": 0.0, "max": 2000.0, "unit": "ug/m3"},
    "CO2": {"min": 0.0, "max": 10000.0, "unit": "ppm"}, # 0-10000 physical sensor limits
    "TEMP": {"min": -10.0, "max": 60.0, "unit": "C"},
    "RH": {"min": 0.0, "max": 100.0, "unit": "%"}
}

def validate_and_classify_measurement(measurement_type: str, value: float) -> Tuple[str, str]:
    """
    Validates a measurement against physical sensor operating boundaries.
    Returns:
      (quality_status, normalized_unit)
    quality_status can be: VALID, SUSPECT, OUT_OF_RANGE, INVALID
    """
    mtype = measurement_type.upper()
    if mtype not in BOUNDARIES:
        return "SUSPECT", "unknown"

    cfg = BOUNDARIES[mtype]
    unit = cfg["unit"]

    if value is None:
        return "INVALID", unit

    # Negative particulate, CO2, or humidity is physically invalid
    if value < 0 and mtype in ["PM2.5", "PM10", "CO2", "RH"]:
        return "INVALID", unit

    # Exceeding sensor physical upper limit
    if value < cfg["min"] or value > cfg["max"]:
        return "OUT_OF_RANGE", unit

    # Indoor CO2 between 0 and 350 ppm is physically possible for outdoor air,
    # but suspect for an occupied indoor school classroom (atmospheric baseline error)
    if mtype == "CO2" and value < 350.0:
        return "SUSPECT", unit

    return "VALID", unit
