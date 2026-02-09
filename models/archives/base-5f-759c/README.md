# Model: base-5f-759c

## Summary
Plain GradientBoosting, 5 raw features, no gestalts

## Details
- **Trained:** Feb 4, 2026
- **Training cases:** 759
- **Lens accuracy:** 65.1%
- **Vault MAE:** 134.4 um
- **Lens model:** GradientBoostingClassifier
- **Vault model:** GradientBoostingRegressor

## Features (5)
- Age
- WTW
- ACD_internal
- ACV
- SimK_steep

## Gestalt Features Included
None — raw features only

## How to deploy
```bash
cp models/archives/base-5f-759c/*.pkl .
git add *.pkl && git commit -m "Deploy base-5f-759c" && git push origin main
```
