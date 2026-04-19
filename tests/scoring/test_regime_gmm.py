import pickle, tempfile, os
import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

def _make_fake_gmm_bundle(tmp_path):
    """Creates a minimal 3-tuple bundle matching what train_regime_gmm.py saves."""
    X = np.array([
        [42, 12, 0.28, 55000, 0.18],   # normal
        [180, 80, 0.10, 72000, 0.05],  # stress
        [12, 20, 0.55, 38000, 0.35],   # wind curtailment
    ])
    scaler = StandardScaler().fit(X)
    gmm = GaussianMixture(n_components=3, random_state=42).fit(scaler.transform(X))
    # label_map: cluster_idx -> semantic_idx (0=normal,1=stress,2=wind)
    label_map = {0: 0, 1: 1, 2: 2}
    bundle = (gmm, scaler, label_map)
    model_path = os.path.join(tmp_path, 'regime_gmm.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(bundle, f)
    return model_path

def test_classify_regime_with_gmm_bundle(tmp_path, monkeypatch):
    model_path = _make_fake_gmm_bundle(tmp_path)
    import backend.scoring.regime as regime_mod
    monkeypatch.setattr(regime_mod, '_GMM_PATH', __import__('pathlib').Path(model_path))
    result = regime_mod.classify_regime(
        lmp_mean=42.0, lmp_std=12.0, wind_pct=0.28, demand_mw=55000
    )
    assert result.label in ('normal', 'stress_scarcity', 'wind_curtailment')
    assert len(result.proba) == 3
    assert abs(sum(result.proba) - 1.0) < 0.01
    assert result.labels == ['normal', 'stress_scarcity', 'wind_curtailment']
