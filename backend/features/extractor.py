"""extract_features(lat, lon) -> FeatureVector.

Uses regional approximation tables as baseline. Replace _spatial_query_*
functions with real DuckDB calls as silver-lake data becomes available.
"""
import math
from backend.features.vector import FeatureVector

# ── Regional baseline tables ───────────────────────────────────────────────

def _classify_state(lat: float, lon: float) -> tuple[str, str]:
    """Return (state, market) from coordinate bounding boxes."""
    if lon > -104.0 and lat < 36.5 and lon < -93.5:  # Texas
        return 'TX', 'ERCOT'
    if lon <= -104.0 and lon > -109.0 and lat < 37.0:  # New Mexico
        return 'NM', 'ERCOT' if lon > -105.0 else 'WECC'
    if lon <= -109.0:  # Arizona and further west
        return 'AZ', 'WECC'
    return 'TX', 'ERCOT'  # default


_NEAREST_ERCOT_NODES = {
    # (lat_center, lon_center, node_id, lmp_fallback)
    'HB_WEST':  (31.5, -102.5, 'HB_WEST',  42.0),
    'HB_NORTH': (35.0, -101.5, 'HB_NORTH', 40.0),
    'HB_SOUTH': (29.5, -98.5,  'HB_SOUTH', 43.0),
}
_CAISO_NODE = ('PALOVRDE_ASR-APND', 38.5)


def _nearest_ercot_node(lat: float, lon: float) -> tuple[str, float]:
    best, best_d = 'HB_WEST', 9999.0
    best_node, best_lmp = 'HB_WEST', 42.0
    for node, (nlat, nlon, nid, lmp) in _NEAREST_ERCOT_NODES.items():
        d = math.hypot(lat - nlat, lon - nlon)
        if d < best_d:
            best, best_d = node, d
            best_node, best_lmp = nid, lmp
    return best_node, best_lmp


# State-level medians for proxy distances (km)
_STATE_MEDIANS = {
    'TX': dict(water_km=7.0, fiber_km=3.0, pipeline_km=1.0, substation_km=8.0,
               highway_km=4.0, interstate_pipeline_km=12.0, waha_distance_km=90.0,
               seismic_hazard=0.05, wildfire_risk=0.15, phmsa_incident_density=0.002,
               acres_available=1500.0, fema_zone='X', ownership_type='private',
               is_federal_wilderness=False, epa_attainment=True),
    'NM': dict(water_km=10.0, fiber_km=6.0, pipeline_km=2.0, substation_km=12.0,
               highway_km=6.0, interstate_pipeline_km=20.0, waha_distance_km=60.0,
               seismic_hazard=0.08, wildfire_risk=0.30, phmsa_incident_density=0.001,
               acres_available=1800.0, fema_zone='X', ownership_type='blm_federal',
               is_federal_wilderness=False, epa_attainment=True),
    'AZ': dict(water_km=5.0, fiber_km=2.0, pipeline_km=4.0, substation_km=10.0,
               highway_km=3.0, interstate_pipeline_km=30.0, waha_distance_km=280.0,
               seismic_hazard=0.12, wildfire_risk=0.45, phmsa_incident_density=0.0005,
               acres_available=800.0, fema_zone='X', ownership_type='state',
               is_federal_wilderness=False, epa_attainment=False),
}


def extract_features(lat: float, lon: float) -> FeatureVector:
    """Return FeatureVector for arbitrary coordinate using regional approximations.

    Each _spatial_query_* call is a stub — replace with DuckDB spatial query
    when the corresponding silver-lake layer is available.
    """
    state, market = _classify_state(lat, lon)
    medians = _STATE_MEDIANS[state]

    if market == 'ERCOT':
        ercot_node, lmp_mwh = _nearest_ercot_node(lat, lon)
    else:
        ercot_node, lmp_mwh = _CAISO_NODE

    return FeatureVector(
        lat=lat, lon=lon, state=state, market=market,
        acres_available=medians['acres_available'],
        fema_zone=medians['fema_zone'],
        is_federal_wilderness=medians['is_federal_wilderness'],
        ownership_type=medians['ownership_type'],
        water_km=medians['water_km'],
        fiber_km=medians['fiber_km'],
        pipeline_km=medians['pipeline_km'],
        substation_km=medians['substation_km'],
        highway_km=medians['highway_km'],
        seismic_hazard=medians['seismic_hazard'],
        wildfire_risk=medians['wildfire_risk'],
        epa_attainment=medians['epa_attainment'],
        interstate_pipeline_km=medians['interstate_pipeline_km'],
        waha_distance_km=medians['waha_distance_km'],
        phmsa_incident_density=medians['phmsa_incident_density'],
        lmp_mwh=lmp_mwh,
        ercot_node=ercot_node,
        waha_price=1.84,  # refreshed by background job in production
    )
