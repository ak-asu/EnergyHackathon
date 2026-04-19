from backend.features.vector import FeatureVector
from backend.scoring.cost import estimate_costs


def _fv():
    return FeatureVector(
        lat=31.9973, lon=-102.0779, state='TX', market='ERCOT',
        acres_available=1200.0, fema_zone='X', is_federal_wilderness=False,
        ownership_type='private', water_km=6.0, fiber_km=2.0,
        pipeline_km=0.4, substation_km=5.0, highway_km=3.0,
        seismic_hazard=0.1, wildfire_risk=0.1, epa_attainment=True,
        interstate_pipeline_km=15.0, waha_distance_km=80.0,
        phmsa_incident_density=0.001, lmp_mwh=42.0,
        ercot_node='HB_WEST', waha_price=1.84,
    )


def test_npv_order():
    ce = estimate_costs(_fv(), land_score=0.8, power_score=0.7)
    assert ce.npv_p10_m <= ce.npv_p50_m <= ce.npv_p90_m


def test_capex_positive():
    ce = estimate_costs(_fv(), land_score=0.8, power_score=0.7)
    assert ce.btm_capex_m > 0
    assert ce.land_acquisition_m > 0


def test_pipeline_cost_scales_with_distance():
    fv_near = _fv()
    fv_near.__dict__['pipeline_km'] = 0.5
    fv_far = _fv()
    fv_far.__dict__['pipeline_km'] = 10.0
    near = estimate_costs(fv_near, 0.8, 0.7)
    far  = estimate_costs(fv_far,  0.8, 0.7)
    assert far.pipeline_connection_m > near.pipeline_connection_m
