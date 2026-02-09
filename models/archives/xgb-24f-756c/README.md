# Model: xgb-24f-756c

## Summary

XGBoost model with Optuna hyperparameter optimization. Uses the same 24 gestalt features as `gestalt-24f-756c` but replaces sklearn GradientBoosting with XGBoost and tunes 9 hyperparameters over 100 Optuna trials per model. Achieves the best vault MAE of any model (108.1 µm) and slightly higher lens accuracy (73.8%). Currently archived as a candidate for promotion to production.

## Performance

| Metric | Value |
|---|---|
| Lens size accuracy | 73.8% (5-fold CV) |
| Vault MAE | 108.1 µm (5-fold CV) |
| Training cases | 759 |
| Trained | Feb 8, 2026 |
| Training script | `scripts/training/train_xgb.py` |
| Training data | `data/processed/training_data.csv` |

### Comparison to Current Production Model

| Metric | gestalt-24f-756c | **xgb-24f-756c** | Delta |
|---|---|---|---|
| Lens accuracy | 73.2% | **73.8%** | +0.6% |
| Vault MAE | 128.3 µm | **108.1 µm** | −20.2 µm (15.7% better) |

## Algorithm

### Lens Size Classifier
- **Type:** `XGBClassifier` (xgboost)
- **Objective:** `multi:softprob`
- **Optimization:** Optuna, 100 trials, maximizing 5-fold CV accuracy
- **Tuned hyperparameters:**
  - `n_estimators`: 50–500
  - `max_depth`: 2–8
  - `learning_rate`: 0.01–0.3 (log scale)
  - `subsample`: 0.5–1.0
  - `colsample_bytree`: 0.5–1.0
  - `min_child_weight`: 1–10
  - `gamma`: 0.0–5.0
  - `reg_alpha`: 1e-8–10.0 (log scale)
  - `reg_lambda`: 1e-8–10.0 (log scale)
- **Classes:** 12.1, 12.6, 13.2, 13.7 mm
- **Note:** Lens classes stored as `model._vault_classes` (numpy array of floats) for label mapping

### Vault Regressor
- **Type:** `XGBRegressor` (xgboost)
- **Objective:** `reg:squarederror`
- **Optimization:** Optuna, 100 trials, maximizing 5-fold CV neg_mean_absolute_error
- **Tuned hyperparameters:** Same 9 parameters as classifier (independently tuned)
- **Output:** Predicted vault in microns (µm)

### Cross-Validation
- 5-fold, `KFold(n_splits=5, shuffle=True, random_state=42)`
- Optuna studies: `direction="maximize"` for lens (accuracy), `direction="maximize"` for vault (neg MAE)
- Final models retrained on full dataset with best params

### Preprocessing
- `StandardScaler` fitted independently for lens and vault models
- If `AC_shape_ratio` is missing, imputed as `ACV / ACD_internal`
- Lens_Size target: absolute value, outlier filter `0 < Lens_Size < 20`, cast to string

## Features (24)

### 9 Base Features

| # | Feature | Unit | Description |
|---|---|---|---|
| 1 | Age | years | Patient age |
| 2 | WTW | mm | White-to-white corneal diameter |
| 3 | ACD_internal | mm | Anterior chamber depth (internal) |
| 4 | ICL_Power | D | ICL lens power (negative for myopia) |
| 5 | AC_shape_ratio | — | Anterior chamber shape ratio |
| 6 | SimK_steep | D | Simulated keratometry, steep meridian |
| 7 | ACV | mm³ | Anterior chamber volume |
| 8 | TCRP_Km | D | Total corneal refractive power, mean K |
| 9 | TCRP_Astigmatism | D | Total corneal refractive power, astigmatism |

### 15 Gestalt Features

#### Bucketed Features (discretize continuous measurements)

| Feature | Formula | Cutoffs |
|---|---|---|
| WTW_Bucket | `pd.cut(WTW, [0, 11.6, 11.9, 12.4, 20])` → 0,1,2,3 | 0: ≤11.6, 1: 11.6–11.9, 2: 11.9–12.4, 3: >12.4 mm |
| ACD_Bucket | `pd.cut(ACD_internal, [0, 3.1, 3.3, 10])` → 0,1,2 | 0: ≤3.1, 1: 3.1–3.3, 2: >3.3 mm |
| Shape_Bucket | `pd.cut(AC_shape_ratio, [0, 58, 62.5, 68, 300])` → 0,1,2,3 | 0: ≤58, 1: 58–62.5, 2: 62.5–68, 3: >68 |

#### Continuous Ratios / Interactions

| Feature | Formula | Clinical Meaning |
|---|---|---|
| Space_Volume | `WTW × ACD_internal` | 2D approximation of anterior chamber space |
| Aspect_Ratio | `WTW / ACD_internal` | Width-to-depth proportion |
| Power_Density | `abs(ICL_Power) / ACV` | Refractive correction per unit chamber volume |
| Chamber_Tightness | `ACV / WTW` | Volume relative to horizontal diameter |
| Curvature_Depth_Ratio | `SimK_steep / ACD_internal` | Corneal steepness relative to chamber depth |
| Age_Space_Ratio | `Age / ACD_internal` | Age-adjusted chamber depth (lens thickening) |

#### Binary Clinical Flags

| Feature | Rule | Triggers When |
|---|---|---|
| High_Power_Deep_ACD | `abs(ICL_Power) > 14 AND ACD_internal > 3.3` | High myope with deep chamber |
| Stability_Risk | `TCRP_Astigmatism > 1.5 AND WTW > 12.0` | High astigmatism + wide eye → rotation risk |

#### Nomogram-Based Features

| Feature | Rule | Clinical Logic |
|---|---|---|
| Nomogram_Size | Manufacturer WTW/ACD lookup table | Maps WTW ranges to expected sizes (12.1–13.7), ACD >3.5 shifts up at boundary zones |
| Volume_Constraint | `Nomogram_Size > 12.1 AND ACV < 170` | Nomogram says bigger lens but chamber volume is small → crowding risk |
| Steep_Eye_Adjustment | `Nomogram_Size > 12.1 AND SimK_steep > 46.0` | Nomogram says bigger lens but cornea is steep → consider downsizing |
| Safety_Downsize_Flag | `Nomogram_Size == 13.2 AND abs(ICL_Power) < 10.0` | 13.2 suggested but low power → consider 12.6 to avoid over-vaulting |

#### Nomogram Lookup Table (`get_nomogram_size`)

```
WTW Range        ACD ≤ 3.5    ACD > 3.5
─────────────    ──────────   ──────────
10.5–10.7        0.0          12.1
10.7–11.1        12.1         12.1
11.1–11.2        12.1         12.6
11.2–11.5        12.6         12.6
11.5–11.7        12.6         13.2
11.7–12.2        13.2         13.2
12.2–12.3        13.2         13.7
12.3–13.0        13.7         13.7
```

## Why Not Production Yet?

- XGBoost requires the `xgboost` Python package — already installed on Render but adds a dependency
- Lens class mapping uses `model._vault_classes` (custom attribute) — the backend `predict_compare` handler already supports this
- Vault MAE improvement is significant (20 µm better) — strong candidate for promotion
- Needs validation on incoming beta cases before replacing the GradientBoosting production model

## Deploy

```bash
cp models/archives/xgb-24f-756c/*.pkl models/current/
git add models/current/*.pkl
git commit -m "Deploy xgb-24f-756c to production"
git push origin main
```