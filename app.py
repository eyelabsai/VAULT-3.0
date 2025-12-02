#!/usr/bin/env python3
"""
ICL Vault Prediction - Streamlit Web Application
Clinical Decision Support Tool for ICL Size and Vault Prediction
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from predict_icl import predict_patient, load_models
import numpy as np
import configparser
import io
from datetime import datetime, date


def parse_ini_file(ini_content: str) -> dict:
    """
    Parse Pentacam INI file and extract relevant values for prediction.
    
    Returns dict with: WTW, ACD_internal, CCT, Age (if DOB available)
    """
    extracted = {}
    
    # Parse INI file
    config = configparser.ConfigParser()
    # Handle the INI file which may have duplicate keys by reading line by line
    lines = ini_content.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1]
            continue
        
        if '=' in line and current_section:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Extract CCT (Central Corneal Thickness)
            if key == 'Central Corneal Thickness' and value:
                try:
                    extracted['CCT'] = int(float(value))
                except ValueError:
                    pass
            
            # Extract WTW (Cornea Dia Horizontal) - check multiple possible keys
            if key in ['Cornea Dia Horizontal', 'WTW', 'White to White', 'W-T-W'] and value and 'WTW' not in extracted:
                try:
                    extracted['WTW'] = float(value)
                except ValueError:
                    pass
            
            # Extract ACD Internal
            if key == 'ACD (Int.) [mm]' and value:
                try:
                    extracted['ACD_internal'] = float(value)
                except ValueError:
                    pass
            
            # Extract Pupil Diameter
            if key == 'Pupil diameter mm' and value and 'Pupil_diameter' not in extracted:
                try:
                    extracted['Pupil_diameter'] = float(value)
                except ValueError:
                    pass
            
            # Extract DOB for age calculation
            if key == 'DOB' and value and current_section == 'Patient Data':
                try:
                    dob = datetime.strptime(value, '%Y-%m-%d')
                    today = date.today()
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    extracted['Age'] = age
                except ValueError:
                    pass
            
    
    return extracted

# Page configuration
st.set_page_config(
    page_title="Vault 3.0",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Remove Streamlit's global top padding */
    .st-emotion-cache-18ni7ap, .st-emotion-cache-q8sbsg, .st-emotion-cache-ztfqz8 {
        padding-top: 0 !important;
        margin-top: -40px !important;
    }
    /* Remove padding around main block */
    .block-container {
        padding-top: 0 !important;
        margin-top: -20px !important;
    }
    /* Light elegant background */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    /* Content area background */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 0rem 2rem 1rem 2rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    /* Large Hero Title */
    .main-header {
        font-size: 4rem !important;
        font-weight: 900 !important;
        background: linear-gradient(135deg, #5a67d8 0%, #7f3ab8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
        line-height: 1.0 !important;
        letter-spacing: 0.03em !important;
    }
    /* Shrink Sidebar Instruction Banner Text */
    .instruction-text {
        font-size: 1.1rem !important;
        font-weight: 500 !important;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .recommendation-box {
        background-color: #e8f4f8;
        border-left: 5px solid #1f77b4;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.3rem;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Initialize session state for INI-extracted values
    if 'ini_values' not in st.session_state:
        st.session_state.ini_values = {}
    
    # Sidebar - Patient Input
    with st.sidebar:
        st.header("⚙️ Prediction Mode")
        
        # Mode selection
        prediction_mode = st.radio(
            "Choose mode:",
            ["Single Recommendation", "Multiple Options"],
            index=0,  # Default to Single
            help="Single: One recommendation | Multiple: All options with probabilities"
        )
        
        st.markdown("---")
        
        # INI File Upload Section
        st.header("📁 Import Pentacam INI")
        uploaded_file = st.file_uploader(
            "Upload INI file",
            type=None,  # Accept any file type
            help="Upload Pentacam INI file to auto-fill measurements",
            key="ini_uploader"
        )
        
        if uploaded_file is not None:
            # Check file extension
            file_name = uploaded_file.name.lower()
            if not file_name.endswith('.ini'):
                st.warning(f"⚠️ Expected .INI file, got: {uploaded_file.name}")
            
            # Read and parse INI file
            try:
                ini_content = uploaded_file.read().decode('utf-8', errors='ignore')
                extracted = parse_ini_file(ini_content)
                
                if extracted:
                    st.session_state.ini_values = extracted
                    
                    # Count only the relevant values
                    relevant_keys = ['Age', 'WTW', 'ACD_internal', 'CCT', 'Pupil_diameter']
                    relevant_count = sum(1 for k in extracted if k in relevant_keys)
                    st.success(f"✅ Loaded {relevant_count} values from INI")
                    
                    # Show what was extracted
                    with st.expander("📋 Extracted Values", expanded=True):
                        if 'Age' in extracted:
                            st.write(f"**Age:** {extracted['Age']} years")
                        if 'WTW' in extracted:
                            st.write(f"**WTW:** {extracted['WTW']} mm")
                        else:
                            st.write("**WTW:** ⚠️ Not found in INI")
                        if 'ACD_internal' in extracted:
                            st.write(f"**ACD internal:** {extracted['ACD_internal']} mm")
                        if 'CCT' in extracted:
                            st.write(f"**CCT:** {extracted['CCT']} µm")
                        if 'Pupil_diameter' in extracted:
                            st.write(f"**Pupil Diameter:** {extracted['Pupil_diameter']} mm")
                else:
                    st.warning("⚠️ No valid measurements found in file")
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
        
        st.markdown("---")
        
        st.header("📋 Patient Information")
        st.markdown("Enter patient measurements:")
        
        # Get default values from INI or use standard defaults
        ini_vals = st.session_state.ini_values
        
        # Input fields with INI values as defaults
        age = st.number_input(
            "Age (years)",
            min_value=18,
            max_value=70,
            value=ini_vals.get('Age', 32),
            help="Patient age in years" + (" *(from INI)*" if 'Age' in ini_vals else "")
        )
        
        wtw = st.number_input(
            "WTW (mm)",
            min_value=10.0,
            max_value=14.0,
            value=float(ini_vals.get('WTW', 11.8)),
            step=0.1,
            format="%.1f",
            help="White-to-White diameter" + (" *(from INI)*" if 'WTW' in ini_vals else "")
        )
        
        acd = st.number_input(
            "ACD Internal (mm)",
            min_value=2.0,
            max_value=5.0,
            value=float(ini_vals.get('ACD_internal', 3.2)),
            step=0.01,
            format="%.2f",
            help="Anterior Chamber Depth (internal)" + (" *(from INI)*" if 'ACD_internal' in ini_vals else "")
        )
        
        seq = st.number_input(
            "SEQ (D) ⚠️",
            min_value=-20.0,
            max_value=5.0,
            value=-8.5,
            step=0.25,
            format="%.2f",
            help="Spherical Equivalent (Sphere + Cyl/2) - *Manual entry required*"
        )
        
        cct = st.number_input(
            "CCT (µm)",
            min_value=400,
            max_value=700,
            value=ini_vals.get('CCT', 540),
            step=1,
            help="Central Corneal Thickness" + (" *(from INI)*" if 'CCT' in ini_vals else "")
        )
        
        pupil = st.number_input(
            "Pupil Diameter (mm)",
            min_value=1.0,
            max_value=10.0,
            value=float(ini_vals.get('Pupil_diameter', 3.5)),
            step=0.1,
            format="%.2f",
            help="Pupil diameter in mm" + (" *(from INI)*" if 'Pupil_diameter' in ini_vals else "")
        )
        
        # Show reminder for SEQ if INI was loaded
        if ini_vals:
            st.info("ℹ️ **SEQ** must be entered manually (not in INI file)")
        
        st.markdown("---")
        predict_button = st.button("🔮 Generate Prediction", type="primary", use_container_width=True)
    
    # Main content area
    if predict_button:
        try:
            # Prepare patient data
            patient_data = {
                'Age': age,
                'WTW': wtw,
                'ACD_internal': acd,
                'SEQ': seq,
                'CCT': cct,
                'Pupil_diameter': pupil
            }
            
            # Show loading spinner
            with st.spinner("Analyzing patient data and generating recommendations..."):
                prediction = predict_patient(patient_data)
            
            # Display results
            st.success("✅ Prediction Complete!")
            
            # Get top recommendation
            top_lens = prediction['lens_options'][0]
            
            # === SINGLE RECOMMENDATION MODE ===
            if prediction_mode == "Single Recommendation":
                
                # Round vault values to nearest 10
                vault_lower_rounded = round(prediction['vault_confidence_interval']['lower'] / 10) * 10
                vault_upper_rounded = round(prediction['vault_confidence_interval']['upper'] / 10) * 10
                
                # Create elegant compact recommendation display
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.2rem 2rem; border-radius: 0.6rem; color: white; box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3); margin: 1rem 0;">
                    <div style="display: flex; justify-content: space-around; align-items: center; gap: 2rem;">
                        <div style="flex: 1; text-align: center;">
                            <p style="font-size: 0.85rem; margin: 0; opacity: 0.85; text-transform: uppercase; letter-spacing: 1px;">Recommended Size</p>
                            <p style="font-size: 3.5rem; margin: 0.2rem 0; font-weight: 900; line-height: 1;">{top_lens['size']:.1f}</p>
                            <p style="font-size: 0.8rem; margin: 0; opacity: 0.75;">{top_lens['confidence_pct']:.0f}% confidence</p>
                        </div>
                        <div style="font-size: 2.5rem; opacity: 0.4;">→</div>
                        <div style="flex: 1; text-align: center;">
                            <p style="font-size: 0.85rem; margin: 0; opacity: 0.85; text-transform: uppercase; letter-spacing: 1px;">95% Confidence Vault</p>
                            <p style="font-size: 2.8rem; margin: 0.2rem 0; font-weight: 900; line-height: 1;">{int(vault_lower_rounded)}-{int(vault_upper_rounded)}</p>
                            <p style="font-size: 0.8rem; margin: 0; opacity: 0.75;">micrometers (µm)</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Vault interpretation
                vault_mid = (vault_lower_rounded + vault_upper_rounded) / 2
                
                if vault_upper_rounded < 250:
                    st.error("⚠️ **Low Vault Predicted** - Risk of contact. Consider larger size if available.")
                elif vault_mid < 400:
                    st.warning("✓ **Lower Optimal Range** - Acceptable but monitor closely.")
                elif vault_mid < 750:
                    st.success("✅ **Optimal Vault Range**")
                elif vault_mid < 1000:
                    st.warning("⚠️ **Upper Optimal Range** - Acceptable but on higher end.")
                else:
                    st.error("⚠️ **High Vault Predicted** - Consider smaller size if available.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Confidence")
                    
                    # Confidence gauge chart
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = top_lens['confidence_pct'],
                        title = {'text': f"Lens Size: {top_lens['size']:.1f}mm"},
                        gauge = {
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "#667eea"},
                            'steps': [
                                {'range': [0, 50], 'color': "lightgray"},
                                {'range': [50, 75], 'color': "#d1d5db"},
                                {'range': [75, 100], 'color': "#e5e7eb"}
                            ],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': 90
                            }
                        }
                    ))
                    fig_gauge.update_layout(height=300)
                    st.plotly_chart(fig_gauge, use_container_width=True)
                
                with col2:
                    st.subheader("📈 Vault Range")
                    
                    # Vault range visualization with rounded values
                    vault_mid = (vault_lower_rounded + vault_upper_rounded) / 2
                    
                    # Create vault range visualization
                    x_vault = np.linspace(vault_lower_rounded - 100, vault_upper_rounded + 100, 200)
                    y_vault = np.maximum(0, 1 - np.abs((x_vault - vault_mid) / (vault_upper_rounded - vault_mid)))
                    
                    fig_vault = go.Figure()
                    
                    # Add distribution curve
                    fig_vault.add_trace(go.Scatter(
                        x=x_vault,
                        y=y_vault,
                        fill='tozeroy',
                        fillcolor='rgba(102, 126, 234, 0.3)',
                        line=dict(color='#667eea', width=2),
                        name='Probability'
                    ))
                    
                    # Add confidence interval shading
                    fig_vault.add_vrect(
                        x0=vault_lower_rounded, x1=vault_upper_rounded,
                        fillcolor="rgba(102, 126, 234, 0.2)",
                        layer="below",
                        line_width=0,
                        annotation_text=f"{int(vault_lower_rounded)}-{int(vault_upper_rounded)}µm",
                        annotation_position="top"
                    )
                    
                    # Add optimal range
                    fig_vault.add_vrect(
                        x0=250, x1=750,
                        fillcolor="green",
                        opacity=0.1,
                        annotation_text="Optimal",
                        annotation_position="top left"
                    )
                    
                    fig_vault.update_layout(
                        xaxis_title="Vault (µm)",
                        yaxis_title="Likelihood",
                        showlegend=False,
                        height=300
                    )
                    
                    st.plotly_chart(fig_vault, use_container_width=True)
                
                # Show prediction details in expander
                with st.expander("📊 View Detailed Analysis"):
                    st.markdown(f"""
                    **Confidence Level:** {top_lens['confidence_pct']:.1f}%
                    
                    **95% Confidence Vault Range:** {int(vault_lower_rounded)}-{int(vault_upper_rounded)}µm
                    
                    **Optimal Vault Range:** 250-750µm
                    """)
                    
                    if len(prediction['lens_options']) > 1:
                        alt = prediction['lens_options'][1]
                        if alt['confidence_pct'] > 25:
                            st.info(f"ℹ️ Alternative option: {alt['size']:.1f}mm ({alt['confidence_pct']:.0f}% confidence) - Consider if clinical factors suggest different vault target.")
            
            # === MULTIPLE OPTIONS MODE ===
            else:
                # Round vault values to nearest 10
                vault_lower_rounded = round(prediction['vault_confidence_interval']['lower'] / 10) * 10
                vault_upper_rounded = round(prediction['vault_confidence_interval']['upper'] / 10) * 10
                vault_mid = (vault_lower_rounded + vault_upper_rounded) / 2
                
                # Top recommendation banner
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        label="🎯 Recommended Lens Size",
                        value=f"{top_lens['size']:.1f} mm",
                        delta=f"{top_lens['confidence_pct']:.0f}% confidence"
                    )
                
                with col2:
                    st.metric(
                        label="📊 95% Confidence Vault",
                        value=f"{int(vault_lower_rounded)}-{int(vault_upper_rounded)} µm"
                    )
                
                with col3:
                    vault_status = "Optimal" if 250 <= vault_mid <= 750 else "Review"
                    vault_color = "normal" if vault_status == "Optimal" else "inverse"
                    st.metric(
                        label="✓ Vault Status",
                        value=vault_status
                    )
                
                st.markdown("---")
                
                # Detailed lens size options
                st.subheader("📋 All Lens Size Options")
                
                # Create DataFrame for display
                options_df = pd.DataFrame(prediction['lens_options'])
                options_df['Size (mm)'] = options_df['size'].apply(lambda x: f"{x:.1f}")
                options_df['Confidence'] = options_df['confidence_pct'].apply(lambda x: f"{x:.1f}%")
                options_df['Predicted Vault (µm)'] = options_df['predicted_vault'].apply(lambda x: f"{x:.0f}")
                options_df['Vault Range (µm)'] = options_df['vault_range']
                
                display_df = options_df[['Size (mm)', 'Confidence', 'Predicted Vault (µm)', 'Vault Range (µm)']]
                
                # Highlight top recommendation
                def highlight_top(s):
                    return ['background-color: #e8f4f8; font-weight: bold' if i == 0 else '' 
                           for i in range(len(s))]
                
                st.dataframe(
                    display_df.style.apply(highlight_top, axis=0),
                    use_container_width=True,
                    hide_index=True
                )
                
                st.markdown("---")
                
                # Visualization
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Lens Size Confidence")
                    
                    # Bar chart of probabilities
                    fig_lens = go.Figure(data=[
                        go.Bar(
                            x=[f"{opt['size']:.1f}mm" for opt in prediction['lens_options']],
                            y=[opt['confidence_pct'] for opt in prediction['lens_options']],
                            marker_color=['#1f77b4' if i == 0 else '#7fcdbb' 
                                         for i in range(len(prediction['lens_options']))],
                            text=[f"{opt['confidence_pct']:.1f}%" for opt in prediction['lens_options']],
                            textposition='outside'
                        )
                    ])
                    
                    fig_lens.update_layout(
                        yaxis_title="Confidence (%)",
                        xaxis_title="Lens Size",
                        showlegend=False,
                        height=400
                    )
                    
                    st.plotly_chart(fig_lens, use_container_width=True)
                
                with col2:
                    st.subheader("📈 Vault Distribution")
                    
                    # Create vault range visualization with rounded values
                    # Simple triangular distribution for visualization
                    x_vault = np.linspace(vault_lower_rounded - 100, vault_upper_rounded + 100, 200)
                    y_vault = np.maximum(0, 1 - np.abs((x_vault - vault_mid) / (vault_upper_rounded - vault_mid)))
                    
                    fig_vault = go.Figure()
                    
                    # Add distribution curve
                    fig_vault.add_trace(go.Scatter(
                        x=x_vault,
                        y=y_vault,
                        fill='tozeroy',
                        fillcolor='rgba(31, 119, 180, 0.3)',
                        line=dict(color='#1f77b4', width=2),
                        name='Probability'
                    ))
                    
                    # Add confidence interval shading
                    fig_vault.add_vrect(
                        x0=vault_lower_rounded, x1=vault_upper_rounded,
                        fillcolor="rgba(31, 119, 180, 0.2)",
                        layer="below",
                        line_width=0,
                        annotation_text=f"95% CI: {int(vault_lower_rounded)}-{int(vault_upper_rounded)}µm",
                        annotation_position="top"
                    )
                    
                    # Add optimal range
                    fig_vault.add_vrect(
                        x0=250, x1=750,
                        fillcolor="green",
                        opacity=0.1,
                        annotation_text="Optimal Range",
                        annotation_position="top left"
                    )
                    
                    fig_vault.update_layout(
                        xaxis_title="Vault (µm)",
                        yaxis_title="Likelihood",
                        showlegend=False,
                        height=400
                    )
                    
                    st.plotly_chart(fig_vault, use_container_width=True)
                
                st.markdown("---")
                
                # Clinical guidance
                st.subheader("🩺 Clinical Guidance")
                
                # Determine recommendation type
                if len(prediction['lens_options']) > 1 and prediction['lens_options'][1]['confidence_pct'] > 25:
                    st.markdown(f"""
                    <div class="warning-box">
                        <strong>⚠️ Multiple Viable Options</strong><br>
                        Two lens sizes show significant probability. Consider:
                        <ul>
                            <li><strong>{prediction['lens_options'][0]['size']:.1f}mm</strong> ({prediction['lens_options'][0]['confidence_pct']:.0f}% confidence) - Primary recommendation</li>
                            <li><strong>{prediction['lens_options'][1]['size']:.1f}mm</strong> ({prediction['lens_options'][1]['confidence_pct']:.0f}% confidence) - Viable alternative</li>
                        </ul>
                        Consider patient-specific factors and vault target when making final decision.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="recommendation-box">
                        <strong>✅ Clear Recommendation</strong><br>
                        Model strongly suggests <strong>{prediction['lens_options'][0]['size']:.1f}mm</strong> with {prediction['lens_options'][0]['confidence_pct']:.0f}% confidence.
                    </div>
                    """, unsafe_allow_html=True)
                
                # Vault guidance
                if vault_mid < 250:
                    st.warning("⚠️ Low vault predicted. Consider larger lens size if available.")
                elif vault_mid > 750:
                    st.warning("⚠️ High vault predicted. Consider smaller lens size if available.")
                else:
                    st.info("✓ Predicted vault is within optimal range (250-750µm).")
            
        except Exception as e:
            st.error(f"❌ Error generating prediction: {str(e)}")
            st.info("Please ensure all patient measurements are entered correctly.")
    
    else:
        # Welcome screen
        st.markdown("""
        <div style="background-color: #e8f4f8; padding: 1.5rem; border-radius: 0.5rem;
                    border-left: 5px solid #1f77b4; margin-bottom: 2rem;">
            <p class="instruction-text" style="margin: 0; color: #1f77b4;">
                👈 Select prediction mode and enter patient measurements in the sidebar
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<p class="main-header">Vault 3.0</p>', unsafe_allow_html=True)
        
        st.markdown("""
        Machine learning system that predicts **ICL Lens Size** with confidence scores and **Post-operative Vault** with expected range.
        
        ### 📁 Quick Import
        Upload a **Pentacam INI file** in the sidebar to auto-fill measurements.
        
        ### Required Measurements
        | Measurement | Source | Auto-Import |
        |-------------|--------|-------------|
        | **Age** | Patient DOB | ✅ From INI |
        | **WTW** | Cornea Dia Horizontal | ✅ From INI |
        | **ACD Internal** | ACD (Int.) | ✅ From INI |
        | **CCT** | Central Corneal Thickness | ✅ From INI |
        | **Pupil Diameter** | Pupil diameter mm | ✅ From INI |
        | **SEQ** | Refraction (Sphere + Cyl/2) | ⚠️ Manual |
        """)
        
        # Two columns for prediction modes
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            #### 🎯 Single Recommendation
            - Simple, fast result
            - One recommended lens size
            - Predicted vault with range
            - Best for routine cases
            """)
        
        with col2:
            st.markdown("""
            #### 📊 Multiple Options
            - All lens size options with probabilities
            - Confidence scores for each option
            - Visual charts and comparisons
            - Best when choosing between close options
            """)
        
        st.markdown("""
        ---
        
        ⚕️ **Note:** This tool is for clinical decision support only. Final lens selection should 
        incorporate clinical judgment and patient-specific factors.
        """)


if __name__ == '__main__':
    main()

