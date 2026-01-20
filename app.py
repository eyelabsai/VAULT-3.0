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

# --- UI HELPERS ---
def parse_ini_file(ini_content: str) -> dict:
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
            if key == 'ACD (Int.) [mm]': extracted['ACD_internal'] = float(value)
            elif key == 'Cornea Dia Horizontal': extracted['WTW'] = float(value)
            elif key == 'Central Corneal Thickness': extracted['CCT'] = float(value)
            elif key == 'Anterior Chamber Volume': extracted['ACV'] = float(value)
            elif key == 'Km (Front)': extracted['SimK_steep'] = float(value)
            elif key == 'DOB' and current_section == 'Patient Data':
                try:
                    dob = datetime.strptime(value, '%Y-%m-%d')
                    today = date.today()
                    extracted['Age'] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                except: pass
    return extracted

# --- PAGE SETUP ---
st.set_page_config(page_title="Vault 3.0", page_icon="👁️", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .main-header {
        font-size: 3.5rem !important;
        font-weight: 900 !important;
        background: linear-gradient(135deg, #5a67d8 0%, #7f3ab8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
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

def main():
    st.markdown('<p class="main-header">Vault 3.0</p>', unsafe_allow_html=True)
    
    lens_model, lens_scaler, vault_model, vault_scaler, feature_names = load_models()
    if not lens_model: return

    # Sidebar Inputs
    with st.sidebar:
        st.header("📂 Data Import")
        uploaded_file = st.file_uploader("Import Pentacam INI", type=['ini'])
        ini_vals = {}
        if uploaded_file:
            ini_vals = parse_ini_file(uploaded_file.read().decode('utf-8', errors='ignore'))
            st.success("✅ Imported measurements")

        st.header("📋 Patient Biometrics")
        age = st.number_input("Age", 18, 90, ini_vals.get('Age', 35))
        wtw = st.number_input("WTW (mm)", 10.0, 15.0, ini_vals.get('WTW', 11.8), step=0.1)
        acd = st.number_input("ACD Internal (mm)", 2.0, 5.0, ini_vals.get('ACD_internal', 3.20), step=0.01)
        pwr = st.number_input("ICL Power (D)", -20.0, 10.0, -10.0, step=0.5)
        shape = st.number_input("AC Shape Ratio (Jump)", 0.0, 100.0, 60.0, step=0.1)
        simk = st.number_input("SimK Steep (D)", 35.0, 60.0, 44.0, step=0.1)
        acv = st.number_input("ACV (mm³)", 50.0, 400.0, ini_vals.get('ACV', 180.0), step=1.0)
        tcrp_km = st.number_input("TCRP Km (D)", 35.0, 60.0, 44.0, step=0.1)
        tcrp_astig = st.number_input("TCRP Astigmatism (D)", 0.0, 10.0, 1.0, step=0.25)
        
        predict_btn = st.button("🔮 Generate Recommendation", type="primary", use_container_width=True)

    if predict_btn:
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
        
        # Display
        st.markdown(f"""
        <div class="recommendation-card">
            <h2 style="color: #5a67d8; margin-bottom: 0;">Recommended ICL Size</h2>
            <div style="font-size: 5rem; font-weight: 900; color: #2d3748; line-height: 1.2;">{best_size}mm</div>
            <div style="font-size: 1.2rem; color: #718096; margin-bottom: 2rem;">{best_prob:.1%} Confidence Score</div>
            
            <div style="display: flex; justify-content: center; gap: 4rem; border-top: 1px solid #e2e8f0; padding-top: 2rem;">
                <div>
                    <div style="font-size: 0.9rem; text-transform: uppercase; color: #a0aec0;">Predicted Vault</div>
                    <div style="font-size: 2.5rem; font-weight: 700; color: #4a5568;">{int(pred_vault)}µm</div>
                </div>
                <div>
                    <div style="font-size: 0.9rem; text-transform: uppercase; color: #a0aec0;">Expected Range</div>
                    <div style="font-size: 2.5rem; font-weight: 700; color: #4a5568;">{int(pred_vault-125)}-{int(pred_vault+125)}µm</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Logic Check
        if pred_vault < 250: st.error("⚠️ WARNING: Potential Low Vault (Below 250µm)")
        elif pred_vault > 800: st.warning("⚠️ NOTICE: High Vault Predicted (Above 800µm)")
        else: st.success("✅ Optimal Vault Range Predicted")

        # Probability Breakdown
        st.markdown("### 📊 Probability Breakdown")
        cols = st.columns(len(lens_classes))
        for i, (size, prob) in enumerate(zip(lens_classes, lens_probs)):
            cols[i].metric(f"{size}mm", f"{prob:.1%}")

if __name__ == '__main__':
    main()
