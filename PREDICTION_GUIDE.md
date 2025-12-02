# ICL Prediction System - User Guide

## 🎯 Overview

The ICL Prediction System provides **clinical decision support** for ICL lens size selection and vault prediction. It shows **probability distributions** for all viable lens sizes and predicted vaults for each option.

## ✨ Key Features

### 1. **Probability-Based Recommendations**
- Not just a single prediction, but confidence scores for all options
- See the likelihood of each lens size (12.1, 12.6, 13.2, 13.7mm)
- Make informed decisions when probabilities are close

### 2. **Conditional Vault Predictions**
- Predicted vault for each lens size option
- Confidence intervals (±131.7µm MAE)
- Visual representation of prediction uncertainty

### 3. **Clinical Decision Support**
- Identifies when multiple lens sizes are viable
- Highlights optimal vault range (250-750µm)
- Warns about predicted low/high vaults

## 🚀 Two Ways to Use

### Option 1: Web Interface (Recommended)

**Start the application:**
```bash
./run_prediction_app.sh
```

Or manually:
```bash
source venv/bin/activate
streamlit run app.py
```

The web app will open in your browser at: `http://localhost:8501`

**Features:**
- 📊 Interactive visualizations
- 📋 Real-time probability updates
- 🎨 Clean, medical-grade UI
- 📱 Responsive design

### Option 2: Command Line

**For quick predictions:**
```bash
source venv/bin/activate
python predict_icl.py
```

**For programmatic use (API-style):**
```python
from predict_icl import predict_patient

patient = {
    'Age': 32,
    'WTW': 11.8,
    'ACD_internal': 3.2,
    'SEQ': -8.5,
    'CCT': 540
}

prediction = predict_patient(patient)
print(prediction)
```

## 📊 Understanding the Results

### Lens Size Recommendations

```
Size      Confidence    Pred. Vault      Vault Range
----------------------------------------------------------------
12.6mm       57.4% ★         641µm        509-772µm
13.2mm       41.9%           641µm        509-772µm
```

**What this means:**
- **57.4% confidence for 12.6mm**: Model thinks this is most likely correct
- **41.9% confidence for 13.2mm**: Close second option - consider patient factors
- **★ Symbol**: Highest confidence recommendation

### When to Consider the Alternative

Consider the lower-confidence option when:
1. **Vault concerns**: If predicted vault is borderline, alternative size may be safer
2. **Patient anatomy**: Unusual measurements may favor less common size
3. **Clinical judgment**: Your experience suggests different from model
4. **Close probabilities**: When difference is <20%, both are viable

### Vault Prediction

```
Predicted Vault:  641µm
Confidence Range: 509-772µm
Expected Error:   ±131.7µm (MAE)
```

**Interpretation:**
- **641µm**: Most likely vault outcome
- **509-772µm**: Range where actual vault will likely fall (±1 MAE)
- **75% chance**: Actual vault within ±200µm of prediction

### Vault Zones

| Vault Range | Status | Clinical Significance |
|-------------|--------|---------------------|
| < 250µm | ⚠️ Low | Consider larger size if available |
| 250-750µm | ✅ Optimal | Target range for most patients |
| > 750µm | ⚠️ High | Consider smaller size if available |

## 📈 Model Performance

**Training Data:** 77 complete cases

### Lens Size Classifier
- **Accuracy:** 81.8%
- **When wrong:** 86% are only one size off
- **Completely wrong:** <3% of cases

### Vault Regressor
- **MAE:** 131.7µm (average error)
- **Within ±100µm:** 58% of cases
- **Within ±200µm:** 75% of cases

## 🎓 Clinical Use Cases

### Case 1: Clear Recommendation
```
12.6mm: 75% confidence
13.2mm: 20% confidence
```
→ **Action:** Use 12.6mm with high confidence

### Case 2: Close Call
```
12.6mm: 57% confidence (vault: 420µm)
13.2mm: 42% confidence (vault: 580µm)
```
→ **Action:** Consider patient factors:
- Need lower vault? → 12.6mm
- Need higher vault? → 13.2mm
- Borderline anatomy? → Use clinical judgment

### Case 3: High Vault Predicted
```
13.2mm: 65% confidence (vault: 820µm)
12.6mm: 30% confidence (vault: 680µm)
```
→ **Action:** Model suggests 13.2mm, but vault may be high. Consider 12.6mm to reduce vault risk.

## 🔧 Required Patient Measurements

| Measurement | Source | Normal Range | Critical? |
|------------|--------|--------------|-----------|
| **Age** | DOB + DOS | 18-70 years | ✅ Yes |
| **WTW** | Pentacam | 10-14mm | ✅ Yes |
| **ACD_internal** | Pentacam | 2.0-5.0mm | ✅ Yes |
| **SEQ** | Refraction | -20 to +5D | ✅ Yes |
| **CCT** | Pentacam | 400-700µm | ✅ Yes |

All 5 measurements are required for prediction.

## ⚠️ Important Disclaimers

1. **Clinical Tool Only**: This is decision support, not a replacement for clinical judgment
2. **Validation Needed**: Predictions should be validated against your clinical experience
3. **Patient-Specific Factors**: Consider factors the model doesn't know:
   - Previous surgeries
   - Corneal irregularities
   - Patient preferences
   - Lens availability

4. **Model Limitations**:
   - Trained on 77 cases (growing dataset)
   - May not generalize to all populations
   - Cannot predict complications

## 📞 Tips for Best Results

1. **Use accurate measurements**: Garbage in = garbage out
2. **Check multiple scans**: Use average of reliable Pentacam scans
3. **Consider both options**: When probabilities are close (<20% difference)
4. **Track outcomes**: Record actual results to validate predictions
5. **Update models**: Retrain with new data every 20-30 cases

## 🔄 Workflow Integration

### Pre-Operative Planning
1. Gather Pentacam measurements and refraction
2. Input into prediction system
3. Review lens size probabilities and predicted vaults
4. Discuss options with patient if close call
5. Make final decision incorporating clinical factors

### Post-Operative Follow-up
1. Measure actual vault at 1-month follow-up
2. Record in Excel roster
3. Re-run pipeline to include in training data
4. Model improves with each new case!

## 🚀 Future Enhancements

As your dataset grows (aim for 100+ cases):
- More features can be added (currently using 5 of 13 available)
- Vault predictions conditional on selected lens size
- Confidence intervals may narrow
- Accuracy expected to improve to 85-90%

---

**Version:** 1.0  
**Last Updated:** December 2025  
**Model Performance:** 81.8% lens accuracy, 131.7µm vault MAE

