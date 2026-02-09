# gestalt-28f-756c

GradientBoosting (same algo + hyperparams as gestalt-24f-756c) with 4 new 12.1-focused gestalt features.

- **Algorithm:** GradientBoostingClassifier / GradientBoostingRegressor (sklearn)
- **Hyperparams:** Identical to gestalt-24f-756c (lens: n_est=150, depth=4, lr=0.05, sub=0.8; vault: n_est=50, depth=3, lr=0.1)
- **Features:** 28 (9 base + 15 original gestalts + 4 new gestalts)
- **Training cases:** 756
- **Lens accuracy (CV):** 72.6%
- **12.1 recall (CV):** 24/81 (30%)
- **Vault MAE (CV):** 129.3 um
- **Date:** 2026-02-09

## New Gestalt Features (vs 24f)
1. **Tight_Chamber** — `ACV < 170 AND WTW < 11.7` (35% of 12.1 vs 13% of 12.6)
2. **ACV_Density** — `ACV / WTW^2` (volume relative to eye width squared)
3. **Power_Space** — `ACV / (|ICL_Power| + 1)` (room per diopter of correction)
4. **Wide_Eye_Downsize** — `WTW >= 11.7 AND AC_shape_ratio < 58` (wide eye but flat chamber -> downsize)

## Parent Model
gestalt-24f-756c (untouched foundation)
