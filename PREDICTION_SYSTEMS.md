# ICL Prediction Systems - Quick Reference

You now have **TWO prediction systems** available - choose based on your needs!

---

## 🆕 NEW: Web-Based Decision Support (Recommended)

**Files:** `app.py`, `predict_icl.py`, `run_prediction_app.sh`

### When to Use:
- ✅ You have patient measurements ready (5 values)
- ✅ You want to see ALL lens options with confidence scores
- ✅ You want visual charts and graphs
- ✅ You need clinical decision support
- ✅ You want to compare multiple lens sizes
- ✅ Best for routine pre-op planning

### How to Use:
```bash
./run_prediction_app.sh
```
Opens web interface at http://localhost:8501

**Input Required:**
- Age
- WTW
- ACD Internal
- SEQ
- CCT

**Output:**
```
12.6mm: 71.8% confidence → Vault: 438µm (306-570µm)
13.2mm: 27.5% confidence → Vault: 438µm (306-570µm)
```

---

## 📁 OLD: XML-Based Prediction

**Files:** `predict_new_patient.py`, `icl_ml_model.py`

### When to Use:
- ✅ You already have XML files from Pentacam
- ✅ You want command-line automation
- ✅ You need to batch process multiple patients
- ✅ You prefer working with XML directly

### How to Use:
```bash
python predict_new_patient.py --xml_file "XML files/00000123.xml" --eye OD
```

**Optional manual features:**
```bash
python predict_new_patient.py \
  --xml_file "XML files/patient.xml" \
  --eye OD \
  --sphere -8.5 \
  --cyl -1.0 \
  --wtw 11.8
```

**Output:**
```
Predicted Vault: 450 µm
Predicted Lens Size: 12.6 mm
Recommended Lens Size: 12.6 mm
```

---

## 🔄 Comparison

| Feature | NEW Web System | OLD XML System |
|---------|----------------|----------------|
| **Input** | 5 measurements | XML file required |
| **Interface** | Web browser | Command line |
| **Output** | All options with probabilities | Single prediction |
| **Confidence** | Yes (%, ranges) | No |
| **Visualization** | Charts & graphs | Text only |
| **Decision Support** | Full clinical guidance | Basic interpretation |
| **Best For** | Quick pre-op decisions | Batch processing |
| **Learning Curve** | Easy (form-based) | Medium (CLI) |

---

## 💡 Recommended Workflow

### Pre-Operative Planning (Typical Case):
1. **Use NEW web system** for interactive decision-making
2. Enter measurements from Pentacam
3. Review all lens options with probabilities
4. Discuss with patient if close call

### Batch Processing Multiple Patients:
1. **Use OLD XML system** for automation
2. Process all XML files at once
3. Export results to spreadsheet

### Research/Data Analysis:
1. **Use OLD XML system** with shell scripts
2. Automate predictions for entire dataset
3. Compare predictions vs. actual outcomes

---

## 🚀 Future Enhancements

Both systems will be updated when the vault model is retrained to include:
- **Conditional vault predictions** (different vaults for different lens sizes)
- **Lens size as a feature** in vault model
- **More accurate predictions** with larger dataset

---

## 📝 Notes

- Both systems use the same underlying trained models (`.pkl` files)
- Model performance: 81.8% lens accuracy, 131.7µm vault MAE
- Trained on 77 complete cases
- Both systems predict the same vault for all lens sizes (limitation of current model)

---

## 🆘 Quick Start Commands

**Start Web Interface:**
```bash
./run_prediction_app.sh
```

**Predict from XML:**
```bash
python predict_new_patient.py --xml_file "XML files/00000001.xml" --eye OD
```

**Train New Models (after adding data):**
```bash
./update_and_train.sh
```

---

**Choose the tool that fits your workflow!** Both are maintained and updated. 🎯

