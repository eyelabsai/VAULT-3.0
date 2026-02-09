# Model: gestalt-24f-55c

## Summary
Jan 19 gestalt model with toric/sizing rules, small dataset

## Details
- **Trained:** Jan 19, 2026
- **Training cases:** ~55
- **Lens accuracy:** ~75%
- **Vault MAE:** unknown
- **Lens model:** GradientBoostingClassifier
- **Vault model:** GradientBoostingRegressor

## Features (24)
- Age
- WTW
- ACD_internal
- ICL_Power
- AC_shape_ratio
- SimK_steep
- ACV
- TCRP_Km
- TCRP_Astigmatism
- WTW_Bucket
- ACD_Bucket
- Shape_Bucket
- Space_Volume
- Aspect_Ratio
- Power_Density
- High_Power_Deep_ACD
- Chamber_Tightness
- Curvature_Depth_Ratio
- Stability_Risk
- Age_Space_Ratio
- Nomogram_Size
- Volume_Constraint
- Steep_Eye_Adjustment
- Safety_Downsize_Flag

## Gestalt Features Included
- WTW_Bucket
- ACD_Bucket
- Shape_Bucket
- Space_Volume
- Aspect_Ratio
- Power_Density
- High_Power_Deep_ACD
- Chamber_Tightness
- Curvature_Depth_Ratio
- Stability_Risk
- Age_Space_Ratio
- Nomogram_Size
- Volume_Constraint
- Steep_Eye_Adjustment
- Safety_Downsize_Flag

## How to deploy
```bash
cp models/archives/gestalt-24f-55c/*.pkl .
git add *.pkl && git commit -m "Deploy gestalt-24f-55c" && git push origin main
```
