from backend.scoring.gas import score_gas


def test_score_in_range():
    assert 0.0 <= score_gas(0.001, 0.4, 80.0) <= 1.0


def test_high_incident_density_lowers_score():
    low  = score_gas(0.001, 0.4, 80.0)
    high = score_gas(50.0,  0.4, 80.0)
    assert high < low


def test_closer_pipeline_raises_score():
    near = score_gas(0.001, 0.2, 80.0)
    far  = score_gas(0.001, 20.0, 80.0)
    assert near > far
