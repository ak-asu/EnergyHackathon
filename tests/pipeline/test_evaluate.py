from unittest.mock import patch
from backend.pipeline.evaluate import evaluate_coordinate
from backend.scoring.scorecard import SiteScorecard


def test_evaluate_returns_scorecard():
    sc = evaluate_coordinate(31.9973, -102.0779)
    assert isinstance(sc, SiteScorecard)


def test_disqualified_coordinate_returns_early():
    from backend.features.vector import FeatureVector
    fv = FeatureVector(
        lat=31.9973, lon=-102.0779, state='TX', market='ERCOT',
        acres_available=1200.0, fema_zone='X', is_federal_wilderness=True,
        ownership_type='private', water_km=6.0, fiber_km=2.0,
        pipeline_km=0.4, substation_km=5.0, highway_km=3.0,
        seismic_hazard=0.1, wildfire_risk=0.1, epa_attainment=True,
        interstate_pipeline_km=15.0, waha_distance_km=80.0,
        phmsa_incident_density=0.001, lmp_mwh=42.0,
        ercot_node='HB_WEST', waha_price=1.84,
    )
    with patch('backend.pipeline.evaluate.extract_features', return_value=fv):
        sc = evaluate_coordinate(31.9973, -102.0779)
    assert sc.hard_disqualified is True
    assert sc.composite_score == 0.0


def test_scores_in_range():
    sc = evaluate_coordinate(31.9973, -102.0779)
    if not sc.hard_disqualified:
        assert 0.0 <= sc.land_score <= 1.0
        assert 0.0 <= sc.gas_score <= 1.0
        assert 0.0 <= sc.power_score <= 1.0
        assert 0.0 <= sc.composite_score <= 1.0
