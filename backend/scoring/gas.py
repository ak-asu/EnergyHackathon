"""Gas Supply Reliability scorer. Loads KDE from data/models/gas_kde.pkl when available."""
from pathlib import Path

_KDE_PATH = Path('data/models/gas_kde.pkl')

_INCIDENT_WEIGHT = 0.40
_PIPELINE_WEIGHT = 0.35
_WAHA_WEIGHT     = 0.25


def score_gas(
    lat: float,
    lon: float,
    incident_density: float,
    interstate_pipeline_km: float,
    waha_distance_km: float,
) -> float:
    """Return gas reliability score 0–1.

    Args:
        lat, lon: coordinate (used for KDE lookup when model is loaded)
        incident_density: PHMSA fallback density when KDE not available
        interstate_pipeline_km: distance to nearest interstate pipeline
        waha_distance_km: distance to Waha Hub
    """
    if _KDE_PATH.exists():
        import pickle, numpy as np
        with open(_KDE_PATH, 'rb') as f:
            kde = pickle.load(f)
        log_density = float(kde.score_samples([[lat, lon]])[0])
        # log_density is negative; higher (less negative) = denser incidents = lower reliability
        # Normalize: typical range is [-15, -3]; map to incident_score in [0, 1]
        incident_score = max(0.0, min(1.0, 1.0 - (log_density + 15) / 12.0))
    else:
        incident_score = max(0.0, 1.0 - min(incident_density * 200, 1.0))

    pipeline_score = max(0.0, 1.0 - interstate_pipeline_km / 100.0)
    waha_score     = max(0.0, 1.0 - waha_distance_km / 400.0)

    raw = (
        incident_score * _INCIDENT_WEIGHT +
        pipeline_score * _PIPELINE_WEIGHT +
        waha_score     * _WAHA_WEIGHT
    )
    return round(min(max(raw, 0.0), 1.0), 4)
