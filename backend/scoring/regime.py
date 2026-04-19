"""Market Regime Classifier — GMM 3-cluster on live ERCOT features."""
from dataclasses import dataclass
from pathlib import Path

_GMM_PATH = Path('data/models/regime_gmm.pkl')

LABELS = ['normal', 'stress_scarcity', 'wind_curtailment']


@dataclass
class RegimeState:
    label: str
    proba: list   # [normal_p, stress_p, wind_p], sums to 1.0
    labels: list  # always ['normal', 'stress_scarcity', 'wind_curtailment']


def _rule_based(lmp_mean: float, lmp_std: float, wind_pct: float,
                demand_mw: float, reserve_margin: float) -> RegimeState:
    if lmp_mean > 100 or (lmp_std > 50 and reserve_margin < 0.08):
        return RegimeState(label='stress_scarcity', proba=[0.1, 0.8, 0.1], labels=LABELS)
    if wind_pct > 0.45 and lmp_mean < 25:
        return RegimeState(label='wind_curtailment', proba=[0.1, 0.1, 0.8], labels=LABELS)
    return RegimeState(label='normal', proba=[0.8, 0.1, 0.1], labels=LABELS)


def classify_regime(
    lmp_mean: float,
    lmp_std: float,
    wind_pct: float,
    demand_mw: float,
    reserve_margin: float = 0.18,
) -> RegimeState:
    if _GMM_PATH.exists():
        import pickle, numpy as np
        with open(_GMM_PATH, 'rb') as f:
            gmm, scaler, label_map = pickle.load(f)  # 3-tuple from training script
        X = scaler.transform([[lmp_mean, lmp_std, wind_pct, demand_mw, reserve_margin]])
        raw_idx = int(gmm.predict(X)[0])
        semantic_idx = label_map[raw_idx]
        label = LABELS[semantic_idx]
        # GMM proba is over raw cluster indices; re-order to semantic order
        raw_proba = gmm.predict_proba(X)[0]
        proba = [0.0, 0.0, 0.0]
        for cluster_idx, sem_idx in label_map.items():
            proba[sem_idx] += float(raw_proba[cluster_idx])
        return RegimeState(label=label, proba=proba, labels=LABELS)
    return _rule_based(lmp_mean, lmp_std, wind_pct, demand_mw, reserve_margin)
