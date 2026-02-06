"""
Beta API Routes for Vault 3.0
Handles INI uploads, predictions, and outcome recording with Supabase.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Header
from pydantic import BaseModel, Field

from .supabase_client import (
    VaultDatabase,
    VaultStorage,
    parse_ini_strip_phi,
    get_supabase_client,
)
from .main import predict, PredictionInput, load_models

router = APIRouter(prefix="/beta", tags=["beta"])

# Model version for tracking
MODEL_VERSION = "v1.0.0-beta"
VAULT_MAE = 134.0  # Current model MAE (759 cases, Feb 2026)


# =============================================================================
# Request/Response Models
# =============================================================================

class UploadResponse(BaseModel):
    scan_id: str
    patient_id: str
    anonymous_id: str
    eye: str
    features: dict
    prediction: Optional[dict] = None
    message: str


class OutcomeInput(BaseModel):
    actual_lens_size: Optional[str] = Field(None, description="Lens size used (e.g., '12.6')")
    actual_vault: Optional[float] = Field(None, ge=0, le=2000, description="Measured vault in µm")
    surgery_date: Optional[str] = Field(None, description="Surgery date (YYYY-MM-DD)")
    notes: Optional[str] = None


class OutcomeResponse(BaseModel):
    outcome_id: str
    scan_id: str
    actual_lens_size: Optional[str]
    actual_vault: Optional[float]
    message: str


class PatientListItem(BaseModel):
    id: str
    anonymous_id: str
    scan_count: int
    has_outcomes: bool
    created_at: str


class ScanListItem(BaseModel):
    id: str
    patient_anonymous_id: str
    eye: str
    predicted_lens_size: Optional[str]
    predicted_vault: Optional[float]
    actual_lens_size: Optional[str]
    actual_vault: Optional[float]
    created_at: str


class StatsResponse(BaseModel):
    total_patients: int
    total_scans: int
    scans_with_outcomes: int


# =============================================================================
# Auth Dependency (simplified for beta)
# =============================================================================

async def get_current_user(authorization: str = Header(None)) -> dict:
    """
    Extract user from Authorization header.
    For beta: expects 'Bearer <supabase_access_token>'
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
        
        # Verify token with Supabase
        client = get_supabase_client()
        user_response = client.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {
            "id": user_response.user.id,
            "email": user_response.user.email,
        }
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


# =============================================================================
# Routes
# =============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_ini_file(
    file: UploadFile = File(...),
    anonymous_id: str = "Patient-001",
    icl_power: float = -10.0,
    user: dict = Depends(get_current_user),
):
    """
    Upload an INI file, extract features (strip PHI), and get prediction.
    
    - PHI (name, DOB) is stripped and NOT stored
    - Only measurements and calculated Age are stored
    - User provides anonymous_id to identify their patient locally
    """
    # Validate file type
    filename = (file.filename or "").lower()
    if not filename.endswith(".ini"):
        raise HTTPException(status_code=400, detail="Only .ini files are supported")
    
    # Read and parse INI
    try:
        raw = await file.read()
        content = raw.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    # Extract features (strips PHI)
    parsed = parse_ini_strip_phi(content)
    features = parsed["features"]
    eye = parsed["eye"]
    
    if not features:
        raise HTTPException(status_code=400, detail="Could not extract features from INI file")
    
    # Add ICL_Power from user input (not in INI file)
    features["ICL_Power"] = icl_power
    
    # Initialize database
    db = VaultDatabase()
    storage = VaultStorage()
    user_id = user["id"]
    
    # Get or create patient
    patient = db.get_or_create_patient(user_id, anonymous_id)
    
    # Upload INI file to storage (optional - for audit trail)
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        storage_filename = f"{anonymous_id}_{eye}_{timestamp}.ini"
        ini_path = storage.upload_ini(user_id, storage_filename, raw)
    except Exception:
        ini_path = None  # Continue without storage if it fails
    
    # Create scan record
    scan = db.create_scan(
        patient_id=patient["id"],
        user_id=user_id,
        eye=eye,
        features=features,
        ini_file_path=ini_path,
        original_filename=file.filename,
    )
    
    # Run prediction if we have enough features
    prediction_result = None
    required_features = ["Age", "WTW", "ACD_internal", "ICL_Power", "AC_shape_ratio", "SimK_steep", "ACV", "TCRP_Km", "TCRP_Astigmatism"]
    
    if all(features.get(f) is not None for f in required_features):
        try:
            # Build prediction input
            pred_input = PredictionInput(
                Age=int(features["Age"]),
                WTW=float(features["WTW"]),
                ACD_internal=float(features["ACD_internal"]),
                ICL_Power=float(features["ICL_Power"]),
                AC_shape_ratio=float(features["AC_shape_ratio"]),
                SimK_steep=float(features["SimK_steep"]),
                ACV=float(features["ACV"]),
                TCRP_Km=float(features["TCRP_Km"]),
                TCRP_Astigmatism=float(features["TCRP_Astigmatism"]),
            )
            
            # Get prediction
            pred_response = predict(pred_input)
            
            # Store prediction
            lens_probs = {str(sp.size_mm): sp.probability for sp in pred_response.size_probabilities}
            
            db.create_prediction(
                scan_id=scan["id"],
                predicted_lens_size=str(pred_response.lens_size_mm),
                lens_probabilities=lens_probs,
                predicted_vault=pred_response.vault_pred_um,
                vault_mae=VAULT_MAE,
                model_version=MODEL_VERSION,
                features_used=required_features,
            )
            
            prediction_result = {
                "lens_size_mm": pred_response.lens_size_mm,
                "lens_probability": pred_response.lens_probability,
                "vault_pred_um": pred_response.vault_pred_um,
                "vault_range_um": pred_response.vault_range_um,
                "vault_flag": pred_response.vault_flag,
                "size_probabilities": lens_probs,
            }
            
        except Exception as e:
            # Log but don't fail - still saved the scan
            print(f"Prediction failed: {str(e)}")
    
    missing_features = [f for f in required_features if features.get(f) is None]
    
    return UploadResponse(
        scan_id=scan["id"],
        patient_id=patient["id"],
        anonymous_id=anonymous_id,
        eye=eye,
        features=features,
        prediction=prediction_result,
        message=f"Scan uploaded successfully. Missing features for prediction: {missing_features}" if missing_features else "Scan uploaded and prediction generated.",
    )


@router.post("/scans/{scan_id}/outcome", response_model=OutcomeResponse)
async def record_outcome(
    scan_id: str,
    outcome: OutcomeInput,
    user: dict = Depends(get_current_user),
):
    """
    Record actual surgical outcome for a scan.
    This helps improve the model over time.
    """
    db = VaultDatabase()
    
    # Verify scan belongs to user
    scan = db.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to modify this scan")
    
    # Create/update outcome
    result = db.create_or_update_outcome(
        scan_id=scan_id,
        actual_lens_size=outcome.actual_lens_size,
        actual_vault=outcome.actual_vault,
        surgery_date=outcome.surgery_date,
        notes=outcome.notes,
    )
    
    return OutcomeResponse(
        outcome_id=result["id"],
        scan_id=scan_id,
        actual_lens_size=outcome.actual_lens_size,
        actual_vault=outcome.actual_vault,
        message="Outcome recorded successfully. Thank you for contributing to model improvement!",
    )


@router.get("/patients")
async def list_patients(user: dict = Depends(get_current_user)):
    """List all patients for the current user."""
    db = VaultDatabase()
    patients = db.list_patients(user["id"])
    
    # Get scan counts
    result = []
    for patient in patients:
        scans = db.list_scans(user["id"], patient["id"])
        has_outcomes = any(db.get_outcome(s["id"]) for s in scans)
        result.append({
            "id": patient["id"],
            "anonymous_id": patient["anonymous_id"],
            "scan_count": len(scans),
            "has_outcomes": has_outcomes,
            "created_at": patient["created_at"],
        })
    
    return result


@router.get("/scans")
async def list_scans(
    patient_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List all scans for the current user, optionally filtered by patient."""
    db = VaultDatabase()
    scans = db.list_scans_with_patients(user["id"])
    
    if patient_id:
        scans = [s for s in scans if s["patient_id"] == patient_id]
    
    result = []
    for scan in scans:
        prediction = db.get_prediction(scan["id"])
        outcome = db.get_outcome(scan["id"])
        
        result.append({
            "id": scan["id"],
            "patient_anonymous_id": scan.get("patients", {}).get("anonymous_id", "Unknown"),
            "eye": scan["eye"],
            "predicted_lens_size": prediction["predicted_lens_size"] if prediction else None,
            "predicted_vault": prediction["predicted_vault"] if prediction else None,
            "actual_lens_size": outcome["actual_lens_size"] if outcome else None,
            "actual_vault": outcome["actual_vault"] if outcome else None,
            "created_at": scan["created_at"],
        })
    
    return result


@router.get("/scans/{scan_id}")
async def get_scan_detail(
    scan_id: str,
    user: dict = Depends(get_current_user),
):
    """Get detailed information for a specific scan."""
    db = VaultDatabase()
    
    scan = db.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this scan")
    
    prediction = db.get_prediction(scan_id)
    outcome = db.get_outcome(scan_id)
    
    return {
        "scan": scan,
        "prediction": prediction,
        "outcome": outcome,
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats(user: dict = Depends(get_current_user)):
    """Get usage statistics for the current user."""
    db = VaultDatabase()
    stats = db.get_user_stats(user["id"])
    return StatsResponse(**stats)


@router.get("/export")
async def export_data(user: dict = Depends(get_current_user)):
    """
    Export all scans with outcomes in training format.
    Useful for users who want to analyze their own data.
    """
    db = VaultDatabase()
    data = db.export_training_data(user["id"])
    
    return {
        "count": len(data),
        "data": data,
        "note": "Only scans with recorded outcomes are included.",
    }
