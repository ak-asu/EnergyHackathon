import pickle, os
import numpy as np
from sklearn.neighbors import KernelDensity

def _make_fake_kde(tmp_path):
    coords = np.array([[31.9, -102.1], [32.5, -101.2], [29.8, -95.4]])
    kde = KernelDensity(kernel='gaussian', bandwidth=0.5).fit(coords)
    path = os.path.join(tmp_path, 'gas_kde.pkl')
    with open(path, 'wb') as f:
        pickle.dump(kde, f)
    return path

def test_score_gas_uses_actual_coords(tmp_path, monkeypatch):
    model_path = _make_fake_kde(tmp_path)
    import backend.scoring.gas as gas_mod
    monkeypatch.setattr(gas_mod, '_KDE_PATH', __import__('pathlib').Path(model_path))
    # Permian Basin should score differently from remote NM desert
    score_permian = gas_mod.score_gas(
        lat=31.9, lon=-102.1,
        incident_density=0.0, interstate_pipeline_km=5.0, waha_distance_km=50.0
    )
    score_remote = gas_mod.score_gas(
        lat=36.0, lon=-108.0,
        incident_density=0.0, interstate_pipeline_km=5.0, waha_distance_km=50.0
    )
    # Permian = high incident density (low score); remote NM = lower density (higher score)
    assert score_remote > score_permian, (
        f"Remote NM ({score_remote:.3f}) should score higher gas reliability than "
        f"Permian Basin ({score_permian:.3f}) — KDE not using actual coords"
    )

def test_score_gas_fallback_no_model():
    import backend.scoring.gas as gas_mod
    # When no model file exists, should use rule-based fallback
    score = gas_mod.score_gas(
        lat=31.9, lon=-102.1,
        incident_density=0.1, interstate_pipeline_km=10.0, waha_distance_km=100.0
    )
    assert 0.0 <= score <= 1.0
