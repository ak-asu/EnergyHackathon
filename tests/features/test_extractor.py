from backend.features.extractor import extract_features
from backend.features.vector import FeatureVector, DISQUALIFY_FEMA


def test_returns_feature_vector_for_permian():
    fv = extract_features(31.9973, -102.0779)
    assert isinstance(fv, FeatureVector)
    assert fv.state == 'TX'
    assert fv.market == 'ERCOT'


def test_returns_feature_vector_for_phoenix():
    fv = extract_features(33.3703, -112.5838)
    assert isinstance(fv, FeatureVector)
    assert fv.state == 'AZ'
    assert fv.market == 'WECC'


def test_all_distances_nonnegative():
    fv = extract_features(31.9973, -102.0779)
    assert fv.water_km >= 0
    assert fv.fiber_km >= 0
    assert fv.pipeline_km >= 0
    assert fv.substation_km >= 0
    assert fv.highway_km >= 0
    assert fv.interstate_pipeline_km >= 0


def test_scores_in_range():
    fv = extract_features(31.9973, -102.0779)
    assert 0.0 <= fv.seismic_hazard <= 1.0
    assert 0.0 <= fv.wildfire_risk <= 1.0
    assert fv.phmsa_incident_density >= 0.0
