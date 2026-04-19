from backend.features.vector import FeatureVector
from backend.scoring.regime import RegimeState
from backend.scoring.power import score_power, btm_spread


def _fv(lmp=42.0, waha=1.84):
    return FeatureVector(
        lat=31.9973, lon=-102.0779, state='TX', market='ERCOT',
        acres_available=1200.0, fema_zone='X', is_federal_wilderness=False,
        ownership_type='private', water_km=6.0, fiber_km=2.0,
        pipeline_km=0.4, substation_km=5.0, highway_km=3.0,
        seismic_hazard=0.1, wildfire_risk=0.1, epa_attainment=True,
        interstate_pipeline_km=15.0, waha_distance_km=80.0,
        phmsa_incident_density=0.001, lmp_mwh=lmp,
        ercot_node='HB_WEST', waha_price=waha,
    )

_regime = RegimeState(label='normal', proba=[1.0, 0.0, 0.0])


def test_positive_spread_scores_high():
    fv = _fv(lmp=55.0, waha=1.84)  # spread = 55 - (1.84*8.5+3) = ~36
    result = score_power(fv, _regime)
    assert result['power_score'] > 0.7


def test_negative_spread_scores_low():
    fv = _fv(lmp=10.0, waha=4.0)  # spread = 10 - (4*8.5+3) = -27
    result = score_power(fv, _regime)
    assert result['power_score'] < 0.3


def test_spread_formula():
    spread = btm_spread(lmp_mwh=42.0, waha_price=1.84)
    assert abs(spread - (42.0 - (1.84 * 8.5 + 3.0))) < 0.01


def test_result_keys():
    result = score_power(_fv(), _regime)
    for k in ('power_score', 'spread_p50_mwh', 'spread_durability'):
        assert k in result
