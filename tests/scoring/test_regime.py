from backend.scoring.regime import classify_regime


def test_high_lmp_stress():
    state = classify_regime(lmp_mean=200.0, lmp_std=80.0, wind_pct=0.10,
                            demand_mw=75000, reserve_margin=0.05)
    assert state.label == 'stress_scarcity'


def test_high_wind_curtailment():
    state = classify_regime(lmp_mean=10.0, lmp_std=5.0, wind_pct=0.60,
                            demand_mw=40000, reserve_margin=0.30)
    assert state.label == 'wind_curtailment'


def test_normal_conditions():
    state = classify_regime(lmp_mean=42.0, lmp_std=12.0, wind_pct=0.28,
                            demand_mw=55000, reserve_margin=0.18)
    assert state.label == 'normal'


def test_proba_sums_to_one():
    state = classify_regime(42.0, 12.0, 0.28, 55000, 0.18)
    assert abs(sum(state.proba) - 1.0) < 0.001
