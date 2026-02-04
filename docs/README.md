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
├── data/
│   ├── images/                  # PUT NEW INI/ZIP FILES HERE
│   ├── excel/
│   │   └── VAULT 3.0.xlsx       # UPDATE THIS WITH NEW PATIENTS
│   └── processed/               # Generated audit + training outputs
├── XML files/                   # Auto-generated XMLs
└── *.pkl                        # Generated: Trained models
```

## 📊 Current Status

**Training Cases:** 55 complete pairs  
**Lens Size Model:** 69% accuracy  
**Vault Model:** 125µm mean error (78% within ±200µm)

## 📈 Workflow for New Batches

### Option 1: Keep Existing Data
```bash
# 1. Add new INI/ZIP files to data/images/
# 2. Update data/excel/VAULT 3.0.xlsx with new patients
# 3. Run workflow
./update_and_train.sh
```

### Option 2: Start Fresh
```bash
# 1. Clear old data
rm -rf "XML files"/*
rm data/images/*.ini data/images/*.zip

# 2. Add new files to data/images/
# 3. Replace data/excel/VAULT 3.0.xlsx
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
| `data/processed/training_data.csv` | Ready for ML training |
| `data/processed/flagged_incomplete_cases.csv` | Cases with missing data - review these |
| `data/processed/matched_patients.csv` | Shows XML↔Excel matching |
| `data/processed/missing_outcomes.csv` | Outcomes missing (Vault/Lens Size) |
| `data/processed/failed_extractions.csv` | XMLs that failed extraction |
| `data/processed/unmatched_xmls.csv` | XMLs with no roster match |
| `data/processed/missing_xml_ids.csv` | Missing numeric IDs in XML sequence |
| `data/processed/duplicate_xml_ids.csv` | Duplicate numeric IDs |
| `data/processed/nonstandard_xml_filenames.csv` | Non-numeric XML filenames |
| `data/processed/roster.md` | Quick patient list |
| `lens_size_model.pkl` | Trained classifier |
| `vault_model.pkl` | Trained regressor |
| `scripts/prediction/gestalt_postprocess.py` | Optional post-processing advisory rules |

## 🚨 Check After Each Run

1. **Review flagged cases:**
   ```bash
   cat data/processed/flagged_incomplete_cases.csv
   ```

2. **Check training size:**
   ```bash
   python -c "import pandas as pd; print(f'Cases: {len(pd.read_csv(\"data/processed/training_data.csv\").dropna())}')"
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
python scripts/pipeline/ini_to_xml.py data/images/yourfile.ini

# Convert Excel to CSV
python scripts/pipeline/excel_to_csv.py data/excel/VAULT\ 3.0.xlsx
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
- **Gestalt advisory:** Optional post-processing suggestions (no impact on model output)

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
ls -lh data/excel/*.xlsx
ls -lh data/images/

# Run individual steps
python scripts/pipeline/excel_to_csv.py data/excel/VAULT\ 3.0.xlsx
python scripts/pipeline/ini_to_xml.py --auto
```

### Training fails
```bash
# Check data quality
head data/processed/training_data.csv

# Look for issues
python -c "import pandas as pd; df = pd.read_csv('data/processed/training_data.csv'); print(df.info())"
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
cat data/processed/training_data.csv | head -10

# Count cases
wc -l data/processed/training_data.csv
```

---

**Ready for production!** Just keep adding data and rerunning `./update_and_train.sh`
