#!/usr/bin/env python3
"""
ICL Vault Prediction - Streamlit Web Application (Vault 3.0)
Updated: Jan 20, 2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pickle
import warnings
import configparser
from datetime import datetime, date

warnings.filterwarnings('ignore')

# --- NOMOGRAM LOGIC ---
def get_nomogram_size(wtw, acd):
    """Implementation of the sizing nomogram from the provided table."""
    if wtw < 10.5 or wtw >= 13.0:
        return 0.0
    
    if 10.5 <= wtw < 10.7:
        return 12.1 if acd > 3.5 else 0.0
    elif 10.7 <= wtw < 11.1:
        return 12.1
    elif 11.1 <= wtw < 11.2:
        return 12.6 if acd > 3.5 else 12.1
    elif 11.2 <= wtw < 11.5:
        return 12.6
    elif 11.5 <= wtw < 11.7:
        return 13.2 if acd > 3.5 else 12.6
    elif 11.7 <= wtw < 12.2:
        return 13.2
    elif 12.2 <= wtw < 12.3:
        return 13.7 if acd > 3.5 else 13.2
    elif 12.3 <= wtw < 13.0:
        return 13.7
    
    return 0.0

# --- FEATURE ENGINEERING ---
def engineer_features(data):
    """Apply the same gestalt feature engineering as used in training."""
    df = pd.DataFrame([data])
    
    # Core Features (already in data)
    # ['Age', 'WTW', 'ACD_internal', 'ICL_Power', 'AC_shape_ratio', 'SimK_steep', 'ACV', 'TCRP_Km', 'TCRP_Astigmatism']
    
    # 1. Buckets
    df['WTW_Bucket'] = pd.cut(df['WTW'], bins=[0, 11.6, 11.9, 12.4, 20], labels=[0, 1, 2, 3]).astype(int)
    df['ACD_Bucket'] = pd.cut(df['ACD_internal'], bins=[0, 3.1, 3.3, 10], labels=[0, 1, 2]).astype(int)
    df['Shape_Bucket'] = pd.cut(df['AC_shape_ratio'], bins=[0, 58, 62.5, 68, 300], labels=[0, 1, 2, 3]).astype(int)
    
    # 2. Interactions
    df['Space_Volume'] = df['WTW'] * df['ACD_internal']
    df['Aspect_Ratio'] = df['WTW'] / df['ACD_internal']
    df['Power_Density'] = abs(df['ICL_Power']) / df['ACV']
    
    # 3. Advanced Gestalt
    df['High_Power_Deep_ACD'] = ((abs(df['ICL_Power']) > 14) & (df['ACD_internal'] > 3.3)).astype(int)
    df['Chamber_Tightness'] = df['ACV'] / df['WTW']
    df['Curvature_Depth_Ratio'] = df['SimK_steep'] / df['ACD_internal']
    
    # 4. Rotational/Age
    df['Stability_Risk'] = ((df['TCRP_Astigmatism'] > 1.5) & (df['WTW'] > 12.0)).astype(int)
    df['Age_Space_Ratio'] = df['Age'] / df['ACD_internal']
    
    # 5. Nomogram
    df['Nomogram_Size'] = df.apply(lambda row: get_nomogram_size(row['WTW'], row['ACD_internal']), axis=1)
    
    # 6. Conservative Deviations
    df['Volume_Constraint'] = ((df['Nomogram_Size'] > 12.1) & (df['ACV'] < 170)).astype(int)
    df['Steep_Eye_Adjustment'] = ((df['Nomogram_Size'] > 12.1) & (df['SimK_steep'] > 46.0)).astype(int)
    df['Safety_Downsize_Flag'] = ((df['Nomogram_Size'] == 13.2) & (abs(df['ICL_Power']) < 10.0)).astype(int)
    
    return df

# --- MODEL LOADING ---
@st.cache_resource
def load_models():
    try:
        with open('lens_size_model.pkl', 'rb') as f:
            lens_model = pickle.load(f)
        with open('lens_size_scaler.pkl', 'rb') as f:
            lens_scaler = pickle.load(f)
        with open('vault_model.pkl', 'rb') as f:
            vault_model = pickle.load(f)
        with open('vault_scaler.pkl', 'rb') as f:
            vault_scaler = pickle.load(f)
        with open('feature_names.pkl', 'rb') as f:
            feature_names = pickle.load(f)
        return lens_model, lens_scaler, vault_model, vault_scaler, feature_names
    except FileNotFoundError as e:
        st.error(f"Model files not found. Please ensure .pkl files are in the root directory. Error: {e}")
        return None, None, None, None, None

# --- UNCERTAINTY ESTIMATE ---
@st.cache_data
def get_vault_residual_sigma(feature_names):
    """Estimate vault residual sigma from training data (no retraining)."""
    try:
        df = pd.read_csv("data/processed/training_data.csv")
        df = df[df["Vault"].notna()].copy()
        if df.empty:
            return None

        with open("vault_model.pkl", "rb") as f:
            vault_model = pickle.load(f)
        with open("vault_scaler.pkl", "rb") as f:
            vault_scaler = pickle.load(f)

        X = df[feature_names].copy().fillna(0)
        X_scaled = vault_scaler.transform(X)
        preds = vault_model.predict(X_scaled)
        residuals = df["Vault"].values - preds
        return float(np.std(residuals, ddof=1))
    except Exception:
        return None

# --- UI HELPERS ---
def parse_ini_file(ini_content: str) -> dict:
    """
    Parse INI file content and extract clinical features.
    Uses the same key names as extract_features.py for consistency.
    """
    extracted = {}
    lines = ini_content.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1]
            continue
        if '=' in line and current_section:
            key, value = line.split('=', 1)
            key, value = key.strip(), value.strip()
            if not value: continue
            
            try:
                # 1. ACD Internal - exact match from XML extraction
                if key == 'ACD (Int.) [mm]': 
                    extracted['ACD_internal'] = float(value)
                elif key == 'ACD external' and 'ACD_internal' not in extracted:
                    extracted['ACD_ext_temp'] = float(value)
                
                # 2. WTW - exact match from XML extraction
                elif key == 'Cornea Dia Horizontal': 
                    extracted['WTW'] = float(value)
                
                # 3. CCT
                elif key == 'Central Corneal Thickness': 
                    extracted['CCT'] = float(value)
                
                # 4. ACV - exact key match (just "ACV")
                elif key == 'ACV': 
                    extracted['ACV'] = float(value)
                
                # 5. SimK Steep - exact match from XML extraction
                elif key == 'SimK steep D': 
                    extracted['SimK_steep'] = float(value)
                
                # 6. TCRP Km - exact match from XML extraction
                elif key == 'TCRP 3mm zone pupil Km [D]':
                    extracted['TCRP_Km'] = float(value)
                
                # 7. TCRP Astigmatism - exact match from XML extraction
                elif key == 'TCRP 3mm zone pupil Asti [D]':
                    extracted['TCRP_Astigmatism'] = float(value)
                
                # 8. Patient name
                elif key == 'Name' and current_section == 'Patient Data':
                    extracted['First_Name'] = value.strip()
                elif key == 'Surname' and current_section == 'Patient Data':
                    extracted['Last_Name'] = value.strip()

                # 9. Eye laterality
                elif key == 'Eye':
                    extracted['Eye'] = value.strip().upper()
                
                # 10. Age extraction from DOB
                elif key == 'DOB' and current_section == 'Patient Data':
                    try:
                        dob = datetime.strptime(value, '%Y-%m-%d')
                        today = date.today()
                        extracted['Age'] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    except: pass
            except: pass

    # Post-processing calculations
    # Estimate ACD internal if only external was found (ACD int = ACD ext - CCT/1000)
    if 'ACD_ext_temp' in extracted and 'ACD_internal' not in extracted and 'CCT' in extracted:
        extracted['ACD_internal'] = round(extracted['ACD_ext_temp'] - (extracted['CCT'] / 1000.0), 2)
    
    # Calculate AC Shape Ratio = ACV / ACD_internal (same as extract_features.py)
    if 'ACV' in extracted and 'ACD_internal' in extracted and extracted['ACD_internal'] > 0:
        extracted['ac_shape'] = round(extracted['ACV'] / extracted['ACD_internal'], 2)

    # Combine patient name if present
    first = extracted.get('First_Name')
    last = extracted.get('Last_Name')
    if first and last:
        extracted['Full_Name'] = f"{last} {first}"
    elif last:
        extracted['Full_Name'] = last
    elif first:
        extracted['Full_Name'] = first
        
    return extracted

# --- PAGE SETUP ---
st.set_page_config(page_title="Vault 3.0", page_icon=None, layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .main-header {
        font-size: 3.5rem !important;
        font-weight: 900 !important;
        color: #2d3748;
        text-align: center;
        margin-bottom: 2rem !important;
    }
    .recommendation-card {
        background: white;
        padding: 2rem;
        border-radius: 1rem;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for disclaimer
if 'disclaimer_accepted' not in st.session_state:
    st.session_state.disclaimer_accepted = False

def main():
    lens_model, lens_scaler, vault_model, vault_scaler, feature_names = load_models()
    if not lens_model: return

    # Sidebar Inputs
    with st.sidebar:
        st.header("Data Import")
        uploaded_file = st.file_uploader("Import Pentacam INI", type=['ini'])
        ini_vals = {}
        if uploaded_file:
            ini_vals = parse_ini_file(uploaded_file.read().decode('utf-8', errors='ignore'))
            st.success("Measurements loaded")

        st.header("Patient Biometrics")
        
        def clamp(val, min_v, max_v):
            return max(min_v, min(val, max_v))

        eye_val = ini_vals.get('Eye')
        if eye_val:
            st.markdown(f"**Eye:** {eye_val}")
        else:
            st.markdown("**Eye:** —")

        age = st.number_input("Age", 18, 90, clamp(ini_vals.get('Age', 35), 18, 90))
        wtw = st.number_input("WTW (mm)", 10.0, 15.0, clamp(ini_vals.get('WTW', 11.8), 10.0, 15.0), step=0.1)
        acd = st.number_input("ACD Internal (mm)", 2.0, 5.0, clamp(ini_vals.get('ACD_internal', 3.20), 2.0, 5.0), step=0.01)
        
        # ICL Power removed from UI as per user request
        # Setting a standard median value in background for model stability
        pwr = -9.0 
        
        # AC Shape Ratio calculated from ACV/ACD (default 60.0 if not from INI)
        shape = st.number_input("AC Shape Ratio (Jump)", 0.0, 100.0, clamp(ini_vals.get('ac_shape', 60.0), 0.0, 100.0), step=0.1)
        
        simk = st.number_input("SimK Steep (D)", 35.0, 60.0, clamp(ini_vals.get('SimK_steep', 44.0), 35.0, 60.0), step=0.1)
        acv = st.number_input("ACV (mm³)", 50.0, 400.0, clamp(ini_vals.get('ACV', 180.0), 50.0, 400.0), step=1.0)
        tcrp_km = st.number_input("TCRP Km (D)", 35.0, 60.0, clamp(ini_vals.get('TCRP_Km', 44.0), 35.0, 60.0), step=0.1)
        tcrp_astig = st.number_input("TCRP Astigmatism (D)", 0.0, 10.0, clamp(ini_vals.get('TCRP_Astigmatism', 1.0), 0.0, 10.0), step=0.25)
        
        predict_btn = st.button("Calculate", type="primary", use_container_width=True)

    if predict_btn:
        st.markdown('<p class="main-header">Vault 3.0</p>', unsafe_allow_html=True)
        name_val = ini_vals.get('Full_Name')
        if name_val:
            st.markdown(
                f'<div style="text-align:center; font-size: 2.0rem; font-weight: 700;">Patient: {name_val}</div>',
                unsafe_allow_html=True
            )
        if eye_val:
            st.markdown(
                f'<div style="text-align:center; font-size: 2.0rem; font-weight: 700;">Eye: {eye_val}</div>',
                unsafe_allow_html=True
            )
        input_data = {
            'Age': age, 'WTW': wtw, 'ACD_internal': acd, 'ICL_Power': pwr,
            'AC_shape_ratio': shape, 'SimK_steep': simk, 'ACV': acv,
            'TCRP_Km': tcrp_km, 'TCRP_Astigmatism': tcrp_astig
        }
        
        # Engineering
        df_eng = engineer_features(input_data)
        X = df_eng[feature_names]
        X_scaled = lens_scaler.transform(X)
        
        # Predictions
        lens_probs = lens_model.predict_proba(X_scaled)[0]
        lens_classes = lens_model.classes_
        
        # Sort by probability
        top_indices = np.argsort(lens_probs)[::-1]
        best_size = lens_classes[top_indices[0]]
        best_prob = lens_probs[top_indices[0]]
        
        # Vault prediction
        vault_scaled = vault_scaler.transform(X)
        pred_vault = vault_model.predict(vault_scaled)[0]
        sigma = get_vault_residual_sigma(feature_names)
        ci_margin = 1.96 * sigma if sigma else 125
        ci_low = int(pred_vault - ci_margin)
        ci_high = int(pred_vault + ci_margin)
        
        # Calculate outlier probability based on predicted vault range
        def get_outlier_probability(predicted_vault):
            """Return probability of outlier (100 - P(actual in 250-900)) based on predicted vault."""
            if predicted_vault < 300:
                return 35.6  # 100 - 64.4
            elif predicted_vault < 400:
                return 35.6  # 100 - 64.4
            elif predicted_vault < 500:
                return 15.2  # 100 - 84.8
            elif predicted_vault < 600:
                return 6.8   # 100 - 93.2
            elif predicted_vault < 700:
                return 6.4   # 100 - 93.6
            elif predicted_vault < 800:
                return 20.0  # 100 - 80.0
            else:
                return 83.3  # 100 - 16.7
        
        outlier_prob = get_outlier_probability(pred_vault)
        
        # Display - Clinical Version
        st.divider()
        col_res1, col_res2 = st.columns([1, 1])
        
        with col_res1:
            st.markdown(f"### Lens Size: **{best_size}mm**")
            st.write(f"**Probability:** {best_prob:.1%}")
            
        with col_res2:
            # Predicted vault is calculated but not displayed (kept commented out)
            # st.markdown(f"### Predicted Vault: **{int(pred_vault)}µm**")
            st.markdown(f"### Expected Vault Range")
            if sigma:
                st.info(f"**{ci_low}–{ci_high}µm**")
            else:
                st.info(f"**{ci_low}-{ci_high}µm**")
        
        # Disclaimer with dynamic outlier probability
        st.markdown(f"""
        <div style="background: #f7fafc; border-left: 4px solid #4299e1; padding: 1rem; margin: 1rem 0; border-radius: 4px;">
            <p style="margin: 0; color: #2d3748; font-size: 0.95rem;">
                Based on the file uploaded and surgical results of thousands of eyes, 
                the size most likely to result in an acceptable vault range is as above.<br><br>
                <strong>The probability of an outlier requiring repeat surgical intervention 
                for size mismatch is &lt;{outlier_prob:.0f}%</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Logic Check
        if pred_vault < 250: st.error("Low Vault Predicted (Below 250µm)")
        elif pred_vault > 800: st.warning("High Vault Predicted (Above 800µm)")
        else: st.success("Optimal Vault Range Predicted")

        # Probability Breakdown
        st.markdown("### Size Probability Distribution")
        cols = st.columns(len(lens_classes))
        for i, (size, prob) in enumerate(zip(lens_classes, lens_probs)):
            cols[i].metric(f"{size}mm", f"{prob:.1%}")
    
    else:
        # Welcome screen with disclaimer popup
        st.markdown('<p class="main-header">Vault 3.0</p>', unsafe_allow_html=True)
        
        if not st.session_state.disclaimer_accepted:
            # Disclaimer popup
            st.markdown("""
            <style>
            .disclaimer-box {
                background: white;
                border-radius: 16px;
                padding: 2rem;
                box-shadow: 0 20px 40px rgba(0,0,0,0.15);
                max-width: 600px;
                margin: 2rem auto;
                text-align: center;
            }
            .disclaimer-title {
                font-size: 1.5rem;
                font-weight: 700;
                color: #2d3748;
                margin-bottom: 1rem;
            }
            .disclaimer-text {
                font-size: 1.1rem;
                color: #4a5568;
                line-height: 1.6;
                margin-bottom: 1.5rem;
            }
            </style>
            <div class="disclaimer-box">
                <div class="disclaimer-title">📋 Clinical Disclaimer</div>
                <div class="disclaimer-text">
                    Vault AI is one tool to assist surgeons in selecting ICL size for their patients. 
                    It is not intended to replace surgeon judgement, and does not claim to result in 
                    zero sizing errors or potential need for additional surgical interventions.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("✓ Accept & Continue", type="primary", use_container_width=True):
                    st.session_state.disclaimer_accepted = True
                    st.rerun()
        else:
            # Normal welcome screen after disclaimer accepted
            st.info("Enter patient measurements in the sidebar and click Calculate")
            
            st.markdown("""
            Clinical decision support system for **ICL Lens Size** and **Post-operative Vault** prediction.
            
            ### Parameters
            | Measurement | Source |
            |-------------|--------|
            | **Age** | Patient DOB |
            | **WTW** | Cornea Dia Horizontal |
            | **ACD Internal** | ACD (Int.) |
            | **ACV** | Chamber Volume |
            | **SimK** | Km (Front) |
            """)
            
            st.markdown("""
            ---
            **Note:** This tool is for clinical decision support only. Final lens selection should 
            incorporate clinical judgment and patient-specific factors.
            """)

if __name__ == '__main__':
    main()
