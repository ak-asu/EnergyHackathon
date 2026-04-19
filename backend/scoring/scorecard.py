from dataclasses import dataclass, field


@dataclass
class CostEstimate:
    land_acquisition_m: float
    pipeline_connection_m: float
    water_connection_m: float
    btm_capex_m: float
    npv_p10_m: float
    npv_p50_m: float
    npv_p90_m: float
    wacc: float = 0.08
    capacity_mw: float = 100.0


@dataclass
class SiteScorecard:
    lat: float
    lon: float
    hard_disqualified: bool
    disqualify_reason: str | None

    land_score: float = 0.0
    gas_score: float = 0.0
    power_score: float = 0.0
    composite_score: float = 0.0

    land_shap: dict = field(default_factory=dict)  # factor -> contribution
    spread_p50_mwh: float = 0.0
    spread_durability: float = 0.0   # fraction of 90-day history positive
    regime: str = "normal"
    regime_proba: list = field(default_factory=lambda: [1.0, 0.0, 0.0])

    cost: CostEstimate | None = None
    narrative: str = ""              # filled by Claude stream
