from backend.features.vector import FeatureVector
from backend.scoring.land import score_land, check_hard_disqualifiers


def _fv(**overrides):
    defaults = dict(
        lat=31.9973, lon=-102.0779, state='TX', market='ERCOT',
        acres_available=1200.0, fema_zone='X', is_federal_wilderness=False,
        ownership_type='private', water_km=6.0, fiber_km=2.0,
        pipeline_km=0.4, substation_km=5.0, highway_km=3.0,
        seismic_hazard=0.1, wildfire_risk=0.1, epa_attainment=True,
        interstate_pipeline_km=15.0, waha_distance_km=80.0,
        phmsa_incident_density=0.001, lmp_mwh=42.0,
        ercot_node='HB_WEST', waha_price=1.84,
    )
    return FeatureVector(**(defaults | overrides))


def test_fema_flood_disqualifies():
    for zone in ('A', 'AE', 'V'):
        reason = check_hard_disqualifiers(_fv(fema_zone=zone))
        assert reason is not None, f"Zone {zone} should disqualify"
        assert 'flood' in reason.lower()


def test_wilderness_disqualifies():
    reason = check_hard_disqualifiers(_fv(is_federal_wilderness=True))
    assert reason is not None


def test_insufficient_acres_disqualifies():
    reason = check_hard_disqualifiers(_fv(acres_available=40.0))
    assert reason is not None


def test_valid_site_not_disqualified():
    reason = check_hard_disqualifiers(_fv())
    assert reason is None


def test_score_in_range():
    score, shap = score_land(_fv())
    assert 0.0 <= score <= 1.0


def test_shap_sums_to_score():
    score, shap = score_land(_fv())
    assert abs(sum(shap.values()) - score) < 0.001


def test_private_beats_blm():
    s_priv, _ = score_land(_fv(ownership_type='private'))
    s_blm,  _ = score_land(_fv(ownership_type='blm_federal'))
    assert s_priv > s_blm


def test_close_water_beats_far():
    s_close, _ = score_land(_fv(water_km=1.0))
    s_far,   _ = score_land(_fv(water_km=14.0))
    assert s_close > s_far


def test_high_seismic_lowers_score():
    s_low,  _ = score_land(_fv(seismic_hazard=0.05))
    s_high, _ = score_land(_fv(seismic_hazard=0.95))
    assert s_high < s_low
