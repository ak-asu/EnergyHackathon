import pickle, os
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

def _make_fake_power_models(tmp_path):
    # Forecast cache: node -> {p10, p50, p90, spread_durability, btm_cost_mwh, method}
    cache = {
        'HB_WEST': {
            'p10': np.full(72, 5.0),
            'p50': np.full(72, 18.0),
            'p90': np.full(72, 35.0),
            'spread_durability': 0.72,
            'btm_cost_mwh': 18.64,
            'method': 'test',
        }
    }
    cache_path = os.path.join(tmp_path, 'power_forecast_cache.pkl')
    with open(cache_path, 'wb') as f:
        pickle.dump(cache, f)

    # Durability model
    X = np.array([[50, 2.0, 0, 0.28, 55.0], [10, 4.0, 1, 0.10, 72.0]])
    y = np.array([1, 0])
    scaler = StandardScaler().fit(X)
    lr = LogisticRegression().fit(scaler.transform(X), y)
    dur_path = os.path.join(tmp_path, 'power_durability.pkl')
    with open(dur_path, 'wb') as f:
        pickle.dump((lr, scaler), f)

    return cache_path, dur_path

def test_score_power_uses_forecast_cache(tmp_path, monkeypatch):
    cache_path, dur_path = _make_fake_power_models(tmp_path)
    import backend.scoring.power as power_mod
    from pathlib import Path
    monkeypatch.setattr(power_mod, '_CACHE_PATH', Path(cache_path))
    monkeypatch.setattr(power_mod, '_DUR_PATH', Path(dur_path))
    # Reset cached globals so monkeypatched paths are used
    monkeypatch.setattr(power_mod, '_forecast_cache', None)
    monkeypatch.setattr(power_mod, '_dur_model', None)
    monkeypatch.setattr(power_mod, '_dur_scaler', None)

    from backend.features.vector import FeatureVector
    from backend.scoring.regime import RegimeState
    fv = FeatureVector(
        lat=31.9, lon=-102.1, state='TX', market='ERCOT',
        acres_available=200, fema_zone='X', is_federal_wilderness=False,
        ownership_type='private', water_km=6.0, fiber_km=2.0,
        pipeline_km=0.5, substation_km=4.0, highway_km=2.5,
        seismic_hazard=0.05, wildfire_risk=0.15, epa_attainment=True,
        interstate_pipeline_km=5.0, waha_distance_km=50.0,
        phmsa_incident_density=0.02, lmp_mwh=42.0,
        ercot_node='HB_WEST', waha_price=1.84,
    )
    regime = RegimeState(label='normal', proba=[0.8, 0.1, 0.1], labels=['normal','stress_scarcity','wind_curtailment'])
    result = power_mod.score_power(fv, regime)
    assert 'power_score' in result
    assert 'spread_p50_mwh' in result
    assert 'spread_durability' in result
    assert 0.0 <= result['power_score'] <= 1.0
