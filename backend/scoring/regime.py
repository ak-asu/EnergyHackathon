"""Market Regime Classifier — GMM 3-cluster on live ERCOT features.

Rule-based fallback when GMM model not yet trained.
"""
from dataclasses import dataclass, field
from pathlib import Path

_GMM_PATH = Path('data/models/regime_gmm.pkl')

LABELS = ['normal', 'stress_scarcity', 'wind_curtailment']


@dataclass
class RegimeState:
    label: str
    proba: list  # [normal, stress, wind] sums to 1.0


def _rule_based(lmp_mean: float, lmp_std: float, wind_pct: float,
                demand_mw: float, reserve_margin: float) -> RegimeState:
    if lmp_mean > 100 or (lmp_std > 50 and reserve_margin < 0.08):
        return RegimeState(label='stress_scarcity',  proba=[0.1, 0.8, 0.1])
    if wind_pct > 0.45 and lmp_mean < 25:
        return RegimeState(label='wind_curtailment', proba=[0.1, 0.1, 0.8])
    return RegimeState(label='normal', proba=[0.8, 0.1, 0.1])


def classify_regime(
    lmp_mean: float,
    lmp_std: float,
    wind_pct: float,
    demand_mw: float,
    reserve_margin: float = 0.18,
) -> RegimeState:
    if _GMM_PATH.exists():
        import pickle
        import numpy as np
        with open(_GMM_PATH, 'rb') as f:
            gmm, scaler = pickle.load(f)
        X = scaler.transform([[lmp_mean, lmp_std, wind_pct, demand_mw, reserve_margin]])
        proba = gmm.predict_proba(X)[0].tolist()
        label = LABELS[int(gmm.predict(X)[0])]
        return RegimeState(label=label, proba=proba)
    return _rule_based(lmp_mean, lmp_std, wind_pct, demand_mw, reserve_margin)
