"""TOPSIS normalization for composite site score.

With 3 criteria all benefit-type (higher=better), TOPSIS reduces to:
  distance_to_ideal = sqrt(Σ w_i (1 - score_i)²)
  distance_to_nadir = sqrt(Σ w_i score_i²)
  topsis_score = D_nadir / (D_ideal + D_nadir)

User-overridable weights default to (0.30, 0.35, 0.35).
"""
import math


def topsis(
    land_score: float,
    gas_score: float,
    power_score: float,
    weights: tuple = (0.30, 0.35, 0.35),
) -> float:
    scores = [land_score, gas_score, power_score]
    w = weights

    d_ideal = math.sqrt(sum(w[i] * (1.0 - scores[i]) ** 2 for i in range(3)))
    d_nadir = math.sqrt(sum(w[i] * scores[i] ** 2 for i in range(3)))

    denom = d_ideal + d_nadir
    if denom < 1e-9:
        return 0.5
    return round(d_nadir / denom, 4)
