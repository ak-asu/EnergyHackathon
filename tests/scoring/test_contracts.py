from backend.features.vector import FeatureVector, DISQUALIFY_FEMA, MIN_ACRES
from backend.scoring.scorecard import SiteScorecard, CostEstimate


def test_feature_vector_instantiates():
    fv = FeatureVector(
        lat=31.9973, lon=-102.0779, state='TX', market='ERCOT',
        acres_available=1200.0, fema_zone='X', is_federal_wilderness=False,
        ownership_type='private', water_km=6.0, fiber_km=2.0,
        pipeline_km=0.4, substation_km=5.0, highway_km=3.0,
        seismic_hazard=0.1, wildfire_risk=0.1, epa_attainment=True,
        interstate_pipeline_km=15.0, waha_distance_km=80.0,
        phmsa_incident_density=0.001, lmp_mwh=42.0,
        ercot_node='HB_WEST', waha_price=1.84,
    )
    assert fv.state == 'TX'


def test_disqualify_zones_correct():
    assert 'A' in DISQUALIFY_FEMA
    assert 'AE' in DISQUALIFY_FEMA
    assert 'V' in DISQUALIFY_FEMA
    assert 'X' not in DISQUALIFY_FEMA


def test_min_acres():
    assert MIN_ACRES == 50.0


def test_scorecard_defaults():
    sc = SiteScorecard(lat=31.9, lon=-102.0, hard_disqualified=False, disqualify_reason=None)
    assert sc.composite_score == 0.0
    assert sc.narrative == ""
