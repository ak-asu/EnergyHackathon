"""Market Regime Classifier — GMM 3-cluster on live ERCOT features."""
import logging
import warnings
from dataclasses import dataclass
from pathlib import Path

try:
    from sklearn.exceptions import InconsistentVersionWarning
except Exception:  # pragma: no cover - sklearn may be absent in some test environments
    InconsistentVersionWarning = Warning

_GMM_PATH = Path('data/models/regime_gmm.pkl')
_LOGGER = logging.getLogger(__name__)
_GMM_BUNDLE = None
_GMM_LOAD_ATTEMPTED = False
_GMM_LOAD_WARNED = False
_GMM_INFER_WARNED = False

LABELS = ['normal', 'stress_scarcity', 'wind_curtailment']


@dataclass
class RegimeState:
    label: str
    proba: list   # [normal_p, stress_p, wind_p], sums to 1.0
    labels: list  # always ['normal', 'stress_scarcity', 'wind_curtailment']


def _load_gmm_bundle():
    """Load persisted GMM assets once; return None when unavailable/incompatible."""
    global _GMM_BUNDLE, _GMM_LOAD_ATTEMPTED, _GMM_LOAD_WARNED
    if _GMM_LOAD_ATTEMPTED:
        return _GMM_BUNDLE

    _GMM_LOAD_ATTEMPTED = True
    if not _GMM_PATH.exists():
        return None

    try:
        import pickle
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InconsistentVersionWarning)
            with open(_GMM_PATH, 'rb') as f:
                bundle = pickle.load(f)
        if isinstance(bundle, tuple) and len(bundle) == 3:
            _GMM_BUNDLE = bundle
    except Exception as exc:
        _GMM_BUNDLE = None
        if not _GMM_LOAD_WARNED:
            _LOGGER.warning("Failed to load regime GMM model from %s; using rule-based regime fallback (%s)", _GMM_PATH, exc)
            _GMM_LOAD_WARNED = True

    return _GMM_BUNDLE


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
    global _GMM_INFER_WARNED
    bundle = _load_gmm_bundle()
    if bundle is not None:
        try:
            gmm, scaler, label_map = bundle
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
        except Exception as exc:
            if not _GMM_INFER_WARNED:
                _LOGGER.warning("Regime GMM inference failed; using rule-based regime fallback (%s)", exc)
                _GMM_INFER_WARNED = True
            pass
    return _rule_based(lmp_mean, lmp_std, wind_pct, demand_mw, reserve_margin)
