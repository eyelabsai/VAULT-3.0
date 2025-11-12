# ICL Vault Prediction - Workflow Guide

## 🔄 Adding New Data Batches

When you get new INI files, follow this simple workflow:

### Step 1: Clear Old Data (Optional - if starting fresh)
```bash
# Delete old INI files and XMLs
rm -rf "XML files"/*
rm images/*.ini
rm images/*.zip

# Or just add new files alongside existing ones
```

### Step 2: Add New Files
1. Place new **ZIP files** or loose **INI files** in the `images/` folder
2. Update the **Excel roster** (`excel/VAULT 3.0.xlsx`) with new patient data

### Step 3: Run Complete Pipeline
```bash
# ONE COMMAND - does everything!
python run_pipeline.py
```

This automatically:
- ✅ Converts Excel → CSV
- ✅ Extracts ZIP files
- ✅ Converts INI → XML
- ✅ Matches patients with roster
- ✅ Extracts features
- ✅ Flags incomplete cases
- ✅ Creates training dataset

### Step 4: Train Models
```bash
python train_model.py
```

This will:
- Train on ALL complete cases (old + new)
- Show updated performance metrics
- Save new model files

---

## 📊 Current Performance (55 training cases)

### Lens Size Classifier
- **Accuracy: 69.1%**
- Model: Gradient Boosting
- Most important: SEQ, WTW, Age

### Vault Regressor
- **MAE: 124.6 µm** (mean prediction error)
- **78% within ±200µm** of actual vault
- Model: Gradient Boosting  
- Most important: SEQ, ACD_internal, CCT

---

## 📁 Generated Files

After running the pipeline:

| File | Description |
|------|-------------|
| `training_data.csv` | Complete dataset for ML training |
| `flagged_incomplete_cases.csv` | Cases with outcomes but missing features (review these) |
| `matched_patients.csv` | XML ↔ CSV crosswalk |
| `roster.md` | Quick patient reference |
| `lens_size_model.pkl` | Trained lens size classifier |
| `vault_model.pkl` | Trained vault regressor |
| `*_scaler.pkl` | Feature scalers for normalization |

---

## 🎯 Feature Set (13 independent variables)

From **XML/INI files**:
1. Eye (OD/OS)
2. Age (calculated from DOB + exam date)
3. ACD_internal (mm)
4. WTW (white-to-white, mm)
5. ACV (anterior chamber volume, mm³)
6. ACA_global (anterior chamber angle, °)
7. Pupil_diameter (mm)
8. AC_shape_ratio (ACV/ACD, calculated)
9. TCRP_Km (3mm zone, D)
10. TCRP_Astigmatism (D)
11. SimK steep D
12. CCT (central corneal thickness, µm)
13. BAD_D

From **CSV roster**:
- SEQ (Sphere + Cyl/2) - independent variable
- Vault - target outcome
- Lens Size - target outcome

---

## 🚨 Common Issues

### Issue: Some XMLs not matching with CSV
**Solution:** Check `matched_patients.csv` for match notes. Common causes:
- Name variations (spelling, order)
- DOB format differences
- Missing patients in roster

### Issue: Flagged incomplete cases
**Solution:** Review `flagged_incomplete_cases.csv`:
- **Missing ACD_internal**: Check if XML has `-9999` sentinel value
- **Missing WTW**: Not present in some INI exports
- Consider: Add missing data manually or exclude from training

### Issue: Model performance not improving
**Solution:** 
- Need more training data (aim for 100+ cases)
- Check feature quality (outliers, missing values)
- Consider feature engineering

---

## 📈 Expected Performance Growth

| Training Cases | Expected Lens Size Acc | Expected Vault MAE |
|----------------|------------------------|---------------------|
| 55 (current)   | ~69%                   | ~125 µm            |
| 100            | ~75-80%                | ~100 µm            |
| 200+           | ~80-85%                | ~80 µm             |
| 500+           | ~85-90%                | ~60 µm             |

*Estimates based on typical medical ML performance curves*

---

## 🔧 Troubleshooting

### Pipeline fails at Excel conversion
```bash
# Check if Excel file exists
ls -lh excel/*.xlsx

# Manually convert if needed
python excel_to_csv.py excel/VAULT\ 3.0.xlsx
```

### No INI files processed
```bash
# Check images folder
ls -lh images/

# Manually process specific file
python ini_to_xml.py images/yourfile.ini
```

### Training fails
```bash
# Check training data
head training_data.csv

# Count complete cases
python -c "import pandas as pd; df = pd.read_csv('training_data.csv'); print(f'Complete: {df.dropna().shape[0]}')"
```

---

## 💡 Tips for Best Results

1. **Consistent Data Entry**: Ensure Excel roster is updated before running pipeline
2. **Name Matching**: Use consistent name format (First Last or Last First)
3. **Check Flagged Cases**: Review and fix data issues in flagged cases
4. **Incremental Training**: Retrain after every 20-30 new cases
5. **Track Performance**: Keep log of model performance over time
6. **Backup Data**: Save Excel roster versions with dates

---

## 📞 Quick Reference

```bash
# Complete workflow (one line)
python run_pipeline.py && python train_model.py

# Check current status
python -c "import pandas as pd; df = pd.read_csv('training_data.csv'); complete = df.dropna(); print(f'Training cases: {len(complete)}')"

# View flagged cases
cat flagged_incomplete_cases.csv

# Check model files
ls -lh *.pkl
```

---

## 🎓 Next Steps After Training

1. **Validate predictions** on new patients
2. **Track real outcomes** vs predictions
3. **Update roster** with actual results
4. **Retrain periodically** with validated data
5. **Consider ensemble models** when you have 200+ cases


