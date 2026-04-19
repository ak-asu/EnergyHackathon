from dataclasses import dataclass, field


@dataclass
class FeatureVector:
    lat: float
    lon: float
    state: str            # 'TX' | 'NM' | 'AZ'
    market: str           # 'ERCOT' | 'WECC'

    # Land features
    acres_available: float        # max contiguous acres within 500m radius
    fema_zone: str                # 'X' | 'X500' | 'D' | 'A' | 'AE' | 'V'
    is_federal_wilderness: bool
    ownership_type: str           # 'private' | 'state' | 'blm_federal'
    water_km: float
    fiber_km: float
    pipeline_km: float            # nearest gas pipeline (any type)
    substation_km: float
    highway_km: float
    seismic_hazard: float         # 0–1, from USGS raster
    wildfire_risk: float          # 0–1, from USFS raster
    epa_attainment: bool

    # Gas features
    interstate_pipeline_km: float
    waha_distance_km: float
    phmsa_incident_density: float  # incidents/km² from KDE

    # Power features
    lmp_mwh: float
    ercot_node: str
    waha_price: float              # live $/MMBtu


DISQUALIFY_FEMA = {'A', 'AE', 'V'}
MIN_ACRES = 50.0
