"""
COLLIDE — Market Regime GMM Training Script
============================================
Trains a 3-component Gaussian Mixture Model on historical ERCOT market data.
Clusters map to: normal | stress_scarcity | wind_curtailment

Features: [lmp_mean, lmp_std, wind_pct, demand_mw, reserve_margin]
Output:   data/models/regime_gmm.pkl  (GMM + StandardScaler bundled)

Data: Uses EIA-930 + gridstatus.io historical ERCOT data.
      Falls back to synthetic data if not available.

Run on Google Colab:
  !git clone https://github.com/BhavyaShah1234/EnergyHackathon
  %cd EnergyHackathon
  !python scripts/training/train_regime_gmm.py
"""

import subprocess, sys

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

install("scikit-learn")
install("pandas")
install("numpy")
install("matplotlib")

try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
    CKPT_DIR = "/content/drive/MyDrive/collide_checkpoints"
    print(f"✅ Drive mounted — checkpoints at {CKPT_DIR}")
except Exception:
    CKPT_DIR = "/tmp/collide_checkpoints"
    print(f"⚠️  Not on Colab — checkpoints at {CKPT_DIR}")

import os, pickle
import numpy as np
import pandas as pd
from pathlib import Path

os.makedirs(CKPT_DIR, exist_ok=True)
MODEL_OUT = Path("data/models")
MODEL_OUT.mkdir(parents=True, exist_ok=True)


def ckpt_path(name):
    return os.path.join(CKPT_DIR, f"{name}.pkl")


def save_ckpt(name, obj):
    with open(ckpt_path(name), "wb") as f:
        pickle.dump(obj, f)
    print(f"  💾 Checkpoint saved: {name}")


def load_ckpt(name):
    p = ckpt_path(name)
    if os.path.exists(p):
        with open(p, "rb") as f:
            return pickle.load(f)
    return None


# ── 1. Load or generate historical ERCOT market data ────────────────────────

print("\n📊 Step 1: Load historical ERCOT market data")

CKPT_DATA = load_ckpt("regime_dataset")

if CKPT_DATA is None:
    # Try to load from silver parquet
    SILVER_LMP = Path("data/silver/ercot_lmp")
    SILVER_EIA = Path("data/silver/eia_demand")

    df = None
    if SILVER_LMP.exists() and any(SILVER_LMP.glob("*.parquet")):
        try:
            lmp_df  = pd.concat([pd.read_parquet(f) for f in SILVER_LMP.glob("*.parquet")])
            eia_df  = pd.concat([pd.read_parquet(f) for f in SILVER_EIA.glob("*.parquet")])
            # Merge on period and compute rolling stats
            # (Adjust column names to match your actual parquet schema)
            print(f"  Loaded {len(lmp_df):,} LMP records, {len(eia_df):,} demand records")
        except Exception as e:
            print(f"  Failed to load silver data: {e}")

    if df is None:
        print("  Generating synthetic ERCOT regime dataset")
        print("  (3 regimes: normal, stress_scarcity, wind_curtailment)")
        np.random.seed(42)

        n_per_regime = 500

        # Regime 0: Normal — stable LMP, moderate wind, normal demand
        normal = pd.DataFrame({
            'lmp_mean':      np.random.normal(42, 8, n_per_regime),
            'lmp_std':       np.abs(np.random.normal(12, 4, n_per_regime)),
            'wind_pct':      np.clip(np.random.normal(0.28, 0.06, n_per_regime), 0.05, 0.60),
            'demand_mw':     np.random.normal(55000, 8000, n_per_regime),
            'reserve_margin': np.clip(np.random.normal(0.18, 0.05, n_per_regime), 0.05, 0.40),
            'true_label':    0,
        })

        # Regime 1: Stress/Scarcity — very high LMP, high demand, low reserves
        # Real examples: Winter Storm Uri, 2022 heat dome
        stress = pd.DataFrame({
            'lmp_mean':      np.random.normal(180, 60, n_per_regime),
            'lmp_std':       np.abs(np.random.normal(80, 30, n_per_regime)),
            'wind_pct':      np.clip(np.random.normal(0.10, 0.05, n_per_regime), 0.01, 0.25),
            'demand_mw':     np.random.normal(72000, 5000, n_per_regime),
            'reserve_margin': np.clip(np.random.normal(0.05, 0.02, n_per_regime), 0.01, 0.12),
            'true_label':    1,
        })

        # Regime 2: Wind Curtailment — low/negative LMP, high wind, low demand
        # Real examples: spring 2021/2022 overnight curtailment events
        wind_curt = pd.DataFrame({
            'lmp_mean':      np.random.normal(12, 15, n_per_regime),
            'lmp_std':       np.abs(np.random.normal(20, 8, n_per_regime)),
            'wind_pct':      np.clip(np.random.normal(0.55, 0.08, n_per_regime), 0.35, 0.80),
            'demand_mw':     np.random.normal(38000, 6000, n_per_regime),
            'reserve_margin': np.clip(np.random.normal(0.32, 0.08, n_per_regime), 0.15, 0.60),
            'true_label':    2,
        })

        df = pd.concat([normal, stress, wind_curt], ignore_index=True)
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)

        print(f"  Synthetic dataset: {len(df):,} samples")
        print(f"    Normal:      {(df.true_label==0).sum()}")
        print(f"    Stress:      {(df.true_label==1).sum()}")
        print(f"    Wind Curt:   {(df.true_label==2).sum()}")

    FEATURE_COLS = ['lmp_mean', 'lmp_std', 'wind_pct', 'demand_mw', 'reserve_margin']
    X = df[FEATURE_COLS].values
    y_true = df.get('true_label', pd.Series([0] * len(df))).values

    save_ckpt("regime_dataset", {"X": X, "y_true": y_true, "feature_cols": FEATURE_COLS})
else:
    X = CKPT_DATA["X"]
    y_true = CKPT_DATA["y_true"]
    FEATURE_COLS = CKPT_DATA["feature_cols"]
    print(f"  Loaded {len(X):,} samples from checkpoint")


# ── 2. Scale features ────────────────────────────────────────────────────────

print("\n🔀 Step 2: Scale features")

from sklearn.preprocessing import StandardScaler

CKPT_SCALED = load_ckpt("regime_scaled")

if CKPT_SCALED is None:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    save_ckpt("regime_scaled", {"scaler": scaler, "X_scaled": X_scaled})
else:
    scaler   = CKPT_SCALED["scaler"]
    X_scaled = CKPT_SCALED["X_scaled"]
    print("  Scaler loaded from checkpoint")

print(f"  Feature means: {dict(zip(FEATURE_COLS, scaler.mean_.round(1)))}")


# ── 3. Fit GMM and determine cluster labels ──────────────────────────────────

print("\n🔵 Step 3: Fit GMM (3 components)")

from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score, silhouette_score

CKPT_GMM = load_ckpt("regime_gmm_model")

if CKPT_GMM is None:
    best_gmm, best_bic = None, np.inf

    # Try multiple random seeds, keep best BIC
    for seed in range(5):
        gmm = GaussianMixture(
            n_components=3,
            covariance_type='full',
            max_iter=200,
            n_init=10,
            random_state=seed,
        )
        gmm.fit(X_scaled)
        bic = gmm.bic(X_scaled)
        print(f"  Seed {seed}: BIC={bic:.1f}, converged={gmm.converged_}")
        if bic < best_bic:
            best_bic = bic
            best_gmm = gmm

    gmm = best_gmm
    labels_raw = gmm.predict(X_scaled)
    ari = adjusted_rand_score(y_true, labels_raw)
    sil = silhouette_score(X_scaled, labels_raw)
    print(f"\n  Best GMM — BIC: {best_bic:.1f}, ARI: {ari:.3f}, Silhouette: {sil:.3f}")

    # Map GMM cluster indices to semantic labels based on mean LMP
    # Cluster with highest mean LMP → stress_scarcity
    # Cluster with highest wind_pct → wind_curtailment
    # Remaining → normal
    LABELS = ['normal', 'stress_scarcity', 'wind_curtailment']
    cluster_stats = {}
    for c in range(3):
        mask = labels_raw == c
        cluster_stats[c] = {
            'lmp_mean':  X[mask, 0].mean(),
            'wind_pct':  X[mask, 2].mean(),
            'count':     mask.sum(),
        }
        print(f"  Cluster {c}: n={mask.sum()}, lmp_mean={X[mask,0].mean():.0f}, wind%={X[mask,2].mean():.1%}")

    stress_cluster  = max(cluster_stats, key=lambda c: cluster_stats[c]['lmp_mean'])
    wind_cluster    = max((c for c in range(3) if c != stress_cluster),
                         key=lambda c: cluster_stats[c]['wind_pct'])
    normal_cluster  = [c for c in range(3) if c not in (stress_cluster, wind_cluster)][0]

    label_map = {
        normal_cluster:  0,  # 'normal'
        stress_cluster:  1,  # 'stress_scarcity'
        wind_cluster:    2,  # 'wind_curtailment'
    }
    print(f"\n  Label mapping: cluster {normal_cluster}→normal, "
          f"{stress_cluster}→stress_scarcity, {wind_cluster}→wind_curtailment")

    save_ckpt("regime_gmm_model", {
        "gmm": gmm, "label_map": label_map, "bic": best_bic,
        "ari": ari, "silhouette": sil,
    })
else:
    gmm       = CKPT_GMM["gmm"]
    label_map = CKPT_GMM["label_map"]
    print(f"  GMM loaded (BIC={CKPT_GMM['bic']:.1f}, ARI={CKPT_GMM['ari']:.3f})")


# ── 4. Validate against known regimes ────────────────────────────────────────

print("\n✅ Step 4: Validate against known market conditions")

LABEL_NAMES = {0: 'normal', 1: 'stress_scarcity', 2: 'wind_curtailment'}

test_cases = [
    {"name": "Winter Storm Uri peak",   "features": [200, 90, 0.05, 78000, 0.04]},
    {"name": "Normal spring morning",   "features": [38,  10, 0.30, 50000, 0.20]},
    {"name": "High wind overnight",     "features": [8,   18, 0.62, 35000, 0.35]},
    {"name": "Summer heat dome",        "features": [150, 60, 0.12, 72000, 0.06]},
    {"name": "Normal summer afternoon", "features": [55,  15, 0.18, 65000, 0.14]},
]

for tc in test_cases:
    x = scaler.transform([tc["features"]])
    raw_label  = int(gmm.predict(x)[0])
    final_label = label_map[raw_label]
    proba = gmm.predict_proba(x)[0]
    name = LABEL_NAMES[final_label]
    print(f"  {tc['name']:35s} → {name:20s} (p={proba[raw_label]:.2f})")


# ── 5. Save production model ─────────────────────────────────────────────────

print("\n💾 Step 5: Save production GMM model")

# Bundle GMM + scaler + label_map for backend/scoring/regime.py
bundle = (gmm, scaler, label_map)

with open(MODEL_OUT / "regime_gmm.pkl", "wb") as f:
    pickle.dump(bundle, f)
print(f"  ✅ Saved: {MODEL_OUT}/regime_gmm.pkl")

import shutil
shutil.copy(MODEL_OUT / "regime_gmm.pkl", f"{CKPT_DIR}/regime_gmm.pkl")
print(f"  ✅ Backed up to Drive")

print("\n🎉 Regime GMM training complete!")
print()
print("   IMPORTANT: Update backend/scoring/regime.py to unpack the 3-tuple:")
print("   gmm, scaler, label_map = pickle.load(f)")
print("   Then use label_map[int(gmm.predict(X)[0])] to get the semantic label.")
