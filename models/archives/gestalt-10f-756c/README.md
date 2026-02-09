# gestalt-10f-756c

GradientBoosting on 5 base Pentacam features + 5 gestalt ratios. Minimal feature set.

- **Algorithm:** GradientBoostingClassifier / GradientBoostingRegressor (sklearn)
- **Hyperparams:** Same as gestalt-24f-756c (lens: n_est=150, depth=4, lr=0.05, sub=0.8)
- **Features:** 10 (5 base + 5 gestalt ratios)
- **Base features:** Age, WTW, ACD_internal, ACV, SimK_steep
- **Gestalt features:** Space_Volume, Aspect_Ratio, Chamber_Tightness, Age_Space_Ratio, Curvature_Depth_Ratio
- **Training cases:** 756
- **Lens accuracy (CV):** 70.4%
- **12.1 recall (CV):** 25/81 (31%)
- **Vault MAE (CV):** 133.2 um
- **Date:** 2026-02-09

## Parent
gestalt-24f-756c (foundation, untouched)
