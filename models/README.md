# Vault 3.0 — Model Registry

## Overview

All ICL vault prediction models live here. Each model predicts two things:

1. **Lens Size** (classification) — which ICL size to implant: 12.1, 12.6, 13.2, or 13.7 mm
2. **Vault** (regression) — predicted post-operative vault in microns (µm)

## Directory Structure

```
models/
├── current/            ← Live production model (deployed to Render)
│   ├── lens_size_model.pkl
│   ├── lens_size_scaler.pkl
│   ├── vault_model.pkl
│   ├── vault_scaler.pkl
│   └── feature_names.pkl
│
├── archives/           ← All versioned model snapshots
│   ├── base-5f-759c/
│   ├── gestalt-24f-55c/
│   ├── gestalt-24f-756c/
│   └── xgb-24f-756c/
│
└── README.md           ← This file
```

## Naming Convention

Model tags follow the pattern: `{algorithm}-{features}f-{cases}c`

| Segment | Meaning | Examples |
|---|---|---|
| `algorithm` | Model family | `base` (GradientBoosting, raw features only), `gestalt` (GradientBoosting + gestalt features), `xgb` (XGBoost + Optuna) |
| `{N}f` | Total feature count | `5f` = 5 raw features, `24f` = 9 base + 15 gestalt |
| `{N}c` | Training case count | `759c` = 759 cases, `55c` = ~55 cases |

## Model Comparison

| Model | Algorithm | Features | Cases | Lens Accuracy | Vault MAE | Status |
|---|---|---|---|---|---|---|
| `base-5f-759c` | GradientBoosting | 5 raw | 759 | 65.1% | 134.4 µm | Archived |
| `gestalt-24f-55c` | GradientBoosting | 24 (9+15) | ~55 | ~75% | Unknown | Archived |
| `gestalt-24f-756c` | GradientBoosting | 24 (9+15) | 756 | 73.2% | 128.3 µm | **Live (current/)** |
| `xgb-24f-756c` | XGBoost + Optuna | 24 (9+15) | 759 | 73.8% | 108.1 µm | Archived (candidate) |

## Feature Sets

### 9 Base Features (raw Pentacam measurements + ICL Power)

| Feature | Unit | Description |
|---|---|---|
| Age | years | Patient age |
| WTW | mm | White-to-white (horizontal corneal diameter) |
| ACD_internal | mm | Anterior chamber depth (internal) |
| ICL_Power | D | ICL lens power (diopters, negative for myopia) |
| AC_shape_ratio | — | Anterior chamber shape ratio |
| SimK_steep | D | Simulated keratometry, steep meridian |
| ACV | mm³ | Anterior chamber volume |
| TCRP_Km | D | Total corneal refractive power, mean K |
| TCRP_Astigmatism | D | Total corneal refractive power, astigmatism |

### 15 Gestalt Features (engineered from base features)

See individual model READMEs for full definitions and cutoffs.

**Bucketed:** WTW_Bucket, ACD_Bucket, Shape_Bucket
**Continuous ratios:** Space_Volume, Aspect_Ratio, Power_Density, Chamber_Tightness, Curvature_Depth_Ratio, Age_Space_Ratio
**Binary flags:** High_Power_Deep_ACD, Stability_Risk
**Nomogram-based:** Nomogram_Size, Volume_Constraint, Steep_Eye_Adjustment, Safety_Downsize_Flag

## How Models Are Loaded

- **`/predict`** endpoint → loads from `models/current/` (single live model)
- **`/predict-compare`** endpoint → loads all archives from `models/archives/*/` that contain the 5 required `.pkl` files
- **`/models`** endpoint → lists all available archived models with metadata

The backend (`backend/app/main.py`) auto-discovers archives by scanning for directories containing: `lens_size_model.pkl`, `lens_size_scaler.pkl`, `vault_model.pkl`, `vault_scaler.pkl`, `feature_names.pkl`.

## How to Deploy a Model

Copy an archive's `.pkl` files into `models/current/`:

```bash
cp models/archives/<model-tag>/*.pkl models/current/
git add models/current/*.pkl
git commit -m "Deploy <model-tag> to production"
git push origin main
```

## Training Scripts

| Script | Purpose |
|---|---|
| `scripts/training/train_model.py` | GradientBoosting training with gestalt feature engineering |
| `scripts/training/train_xgb.py` | XGBoost + Optuna hyperparameter optimization |
| `scripts/training/track_performance.py` | Logs metrics to `model_performance_history.json` |
| `scripts/training/feature_selection_analysis.py` | Ablation studies and feature importance |

## Training Data

Source: `data/processed/training_data.csv`
Pipeline: `scripts/pipeline/` (extract → match → feature config → training CSV)
