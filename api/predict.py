from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
import pandas as pd
import numpy as np
from pathlib import Path

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get base directory
BASE_DIR = Path(__file__).parent.parent

# Load models once at startup
models_cache = {}

def load_models():
    """Load trained models and scalers."""
    if not models_cache:
        try:
            with open(BASE_DIR / 'lens_size_model.pkl', 'rb') as f:
                models_cache['lens_model'] = pickle.load(f)
            with open(BASE_DIR / 'lens_size_scaler.pkl', 'rb') as f:
                models_cache['lens_scaler'] = pickle.load(f)
            with open(BASE_DIR / 'vault_model.pkl', 'rb') as f:
                models_cache['vault_model'] = pickle.load(f)
            with open(BASE_DIR / 'vault_scaler.pkl', 'rb') as f:
                models_cache['vault_scaler'] = pickle.load(f)
            with open(BASE_DIR / 'feature_names.pkl', 'rb') as f:
                models_cache['feature_names'] = pickle.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error loading models: {str(e)}")
    
    return (
        models_cache['lens_model'],
        models_cache['lens_scaler'],
        models_cache['vault_model'],
        models_cache['vault_scaler'],
        models_cache['feature_names']
    )


class PatientData(BaseModel):
    Age: float
    WTW: float
    ACD_internal: float
    SEQ: float
    CCT: float


@app.get("/")
def read_root():
    return {"message": "Vault 3.0 API", "status": "running"}


@app.post("/predict")
def predict(patient: PatientData):
    """Predict lens size and vault for a patient."""
    try:
        # Load models
        lens_model, lens_scaler, vault_model, vault_scaler, feature_names = load_models()
        
        # Prepare input
        patient_dict = patient.dict()
        X = pd.DataFrame([patient_dict])[feature_names]
        
        # Validate inputs
        if X.isnull().any().any():
            missing = X.columns[X.isnull().any()].tolist()
            raise HTTPException(status_code=400, detail=f"Missing features: {missing}")
        
        # Scale features
        X_lens_scaled = lens_scaler.transform(X)
        X_vault_scaled = vault_scaler.transform(X)
        
        # LENS SIZE PREDICTIONS
        lens_pred = lens_model.predict(X_lens_scaled)[0]
        
        # Get probability distribution
        lens_options = []
        if hasattr(lens_model, 'predict_proba'):
            lens_proba = lens_model.predict_proba(X_lens_scaled)[0]
            lens_classes = lens_model.classes_
            
            sorted_indices = np.argsort(lens_proba)[::-1]
            
            for idx in sorted_indices:
                if lens_proba[idx] > 0.01:
                    lens_options.append({
                        'size': float(lens_classes[idx]),
                        'probability': float(lens_proba[idx]),
                        'confidence_pct': float(lens_proba[idx] * 100)
                    })
        else:
            lens_options = [{
                'size': float(lens_pred),
                'probability': 1.0,
                'confidence_pct': 100.0
            }]
        
        # VAULT PREDICTION
        vault_pred = vault_model.predict(X_vault_scaled)[0]
        
        # Confidence interval (using MAE from training)
        mae = 131.7
        vault_lower = vault_pred - mae
        vault_upper = vault_pred + mae
        
        # Add vault predictions to lens options
        for option in lens_options:
            option['predicted_vault'] = float(vault_pred)
            option['vault_range_lower'] = float(vault_lower)
            option['vault_range_upper'] = float(vault_upper)
            option['vault_range'] = f"{vault_lower:.0f}-{vault_upper:.0f}µm"
        
        return {
            'success': True,
            'patient_data': patient_dict,
            'top_lens_size': float(lens_pred),
            'predicted_vault': float(vault_pred),
            'vault_confidence_interval': {
                'lower': float(vault_lower),
                'upper': float(vault_upper),
                'mae': mae
            },
            'lens_options': lens_options,
            'model_info': {
                'lens_accuracy': 0.818,
                'vault_mae': 131.7,
                'training_cases': 77
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


# For Vercel serverless
handler = app

