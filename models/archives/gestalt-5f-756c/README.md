# gestalt-5f-756c

GradientBoosting on 5 base Pentacam features only. Minimal model, no engineered gestalts.

- **Algorithm:** GradientBoostingClassifier / GradientBoostingRegressor (sklearn)
- **Hyperparams:** Same as gestalt-24f-756c (lens: n_est=150, depth=4, lr=0.05, sub=0.8)
- **Features:** 5 (Age, WTW, ACD_internal, ACV, SimK_steep)
- **Training cases:** 756
- **Lens accuracy (CV):** 72.1%
- **12.1 recall (CV):** 25/81 (31%)
- **Vault MAE (CV):** 133.7 um
- **Date:** 2026-02-09

## Parent
gestalt-24f-756c (foundation, untouched)
