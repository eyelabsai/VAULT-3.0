# ICL Vault Prediction System

Machine learning system to predict ICL lens size and vault from Pentacam measurements.

## 🚀 Quick Start - Adding New Data

When you get new INI files or update the Excel roster:

```bash
./update_and_train.sh
```

That's it! This one command:
1. Processes all INI/ZIP files
2. Matches with Excel roster
3. Extracts features
4. Trains ML models
5. Shows performance metrics

## 📂 Folder Structure

```
Vault 3.0/
├── images/                      # PUT NEW INI/ZIP FILES HERE
├── XML files/                   # Auto-generated XMLs
├── excel/
│   └── VAULT 3.0.xlsx          # UPDATE THIS WITH NEW PATIENTS
├── training_data.csv            # Generated: ML dataset
├── flagged_incomplete_cases.csv # Generated: Cases to review
└── *.pkl                        # Generated: Trained models
```

## 📊 Current Status

**Training Cases:** 55 complete pairs  
**Lens Size Model:** 69% accuracy  
**Vault Model:** 125µm mean error (78% within ±200µm)

## 📈 Workflow for New Batches

### Option 1: Keep Existing Data
```bash
# 1. Add new INI/ZIP files to images/
# 2. Update excel/VAULT 3.0.xlsx with new patients
# 3. Run workflow
./update_and_train.sh
```

### Option 2: Start Fresh
```bash
# 1. Clear old data
rm -rf "XML files"/*
rm images/*.ini images/*.zip

# 2. Add new files to images/
# 3. Replace excel/VAULT 3.0.xlsx
# 4. Run workflow
./update_and_train.sh
```

## 🎯 What Gets Extracted

### From INI/XML Files:
- Eye (OD/OS)
- Age, WTW, ACD, ACV
- ACA, Pupil diameter
- TCRP (Km + Astigmatism)
- SimK, CCT, BAD-D
- Shape ratios (calculated)

### From Excel Roster:
- Sphere + Cyl → SEQ
- Vault (target)
- Lens Size (target)

## 📋 Files Created

| File | Purpose |
|------|---------|
| `training_data.csv` | Ready for ML training |
| `flagged_incomplete_cases.csv` | Cases with missing data - review these |
| `matched_patients.csv` | Shows XML↔Excel matching |
| `roster.md` | Quick patient list |
| `lens_size_model.pkl` | Trained classifier |
| `vault_model.pkl` | Trained regressor |

## 🚨 Check After Each Run

1. **Review flagged cases:**
   ```bash
   cat flagged_incomplete_cases.csv
   ```

2. **Check training size:**
   ```bash
   python -c "import pandas as pd; print(f'Cases: {len(pd.read_csv(\"training_data.csv\").dropna())}')"
   ```

3. **Verify model files exist:**
   ```bash
   ls -lh *.pkl
   ```

## 🔧 Individual Scripts (if needed)

```bash
# Just process data (no training)
python run_pipeline.py

# Just train models (if data already processed)
python train_model.py

# Convert single INI file
python ini_to_xml.py path/to/file.ini

# Convert Excel to CSV
python excel_to_csv.py excel/VAULT\ 3.0.xlsx
```

## 📖 Documentation

- **WORKFLOW_GUIDE.md** - Detailed workflow documentation
- **extract_features.py** - Feature extraction logic
- **train_model.py** - Model training details

## 💡 Tips

- **Model improves with more data:** Expect better performance at 100+ cases
- **Review flagged cases:** Fix missing data before retraining
- **Update Excel first:** Ensure roster has all patient outcomes
- **Retrain often:** Every 20-30 new cases, rerun training
- **Track performance:** Keep notes on model accuracy over time

## 🎓 Model Performance Expectations

| Cases | Lens Size Accuracy | Vault MAE |
|-------|-------------------|-----------|
| 50    | ~70%              | ~125µm    |
| 100   | ~75-80%           | ~100µm    |
| 200+  | ~80-85%           | ~80µm     |
| 500+  | ~85-90%           | ~60µm     |

## ❓ Troubleshooting

### Pipeline fails
```bash
# Check file exists
ls -lh excel/*.xlsx
ls -lh images/

# Run individual steps
python excel_to_csv.py excel/VAULT\ 3.0.xlsx
python ini_to_xml.py --auto
```

### Training fails
```bash
# Check data quality
head training_data.csv

# Look for issues
python -c "import pandas as pd; df = pd.read_csv('training_data.csv'); print(df.info())"
```

### Names not matching
- Check `matched_patients.csv` for match notes
- Verify name format consistency in Excel
- Check DOB format matches

## 📞 Quick Commands

```bash
# Full workflow
./update_and_train.sh

# Check status
ls -lh *.csv *.pkl

# View results
cat training_data.csv | head -10

# Count cases
wc -l training_data.csv
```

---

**Ready for production!** Just keep adding data and rerunning `./update_and_train.sh`
