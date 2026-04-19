from backend.scoring.topsis import topsis

W = (0.30, 0.35, 0.35)


def test_perfect_scores():
    assert topsis(1.0, 1.0, 1.0, W) > 0.95


def test_zero_scores():
    assert topsis(0.0, 0.0, 0.0, W) < 0.05


def test_in_range():
    assert 0.0 <= topsis(0.7, 0.8, 0.6, W) <= 1.0


def test_higher_scores_beat_lower():
    high = topsis(0.9, 0.9, 0.9, W)
    low  = topsis(0.3, 0.3, 0.3, W)
    assert high > low
