"""
Supabase Client for Vault 3.0 Beta
Handles database operations and file storage with PHI stripping.
"""

import os
from datetime import date, datetime
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for backend


def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_user_client(access_token: str) -> Client:
    """Get Supabase client with user's JWT for RLS."""
    if not SUPABASE_URL:
        raise ValueError("Missing SUPABASE_URL environment variable")
    client = create_client(SUPABASE_URL, os.getenv("SUPABASE_ANON_KEY", ""))
    client.auth.set_session(access_token, "")
    return client


# =============================================================================
# PHI Stripping - Extract features, discard patient identifiers
# =============================================================================

def parse_ini_strip_phi(ini_content: str) -> dict:
    """
    Parse INI content and extract features while stripping PHI.
    
    Returns:
        dict with:
            - features: dict of extracted measurements (no PHI)
            - phi_hash: hash of name+DOB for deduplication (optional)
            - eye: OD/OS
    """
    import hashlib
    
    extracted = {}
    phi_data = {}
    lines = ini_content.split("\n")
    current_section = None

    for line in lines:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1]
            continue
        if "=" in line and current_section:
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if not value:
                continue

            try:
                # PHI fields - capture for hashing but don't store
                if key == "Name" and current_section == "Patient Data":
                    phi_data["first_name"] = value.strip()
                elif key == "Surname" and current_section == "Patient Data":
                    phi_data["last_name"] = value.strip()
                elif key == "DOB" and current_section == "Patient Data":
                    phi_data["dob"] = value.strip()
                    # Calculate age (this is OK to store - not PHI)
                    try:
                        dob = datetime.strptime(value, "%Y-%m-%d")
                        today = date.today()
                        extracted["Age"] = today.year - dob.year - (
                            (today.month, today.day) < (dob.month, dob.day)
                        )
                    except ValueError:
                        pass
                
                # Non-PHI measurement fields
                elif key == "ACD (Int.) [mm]":
                    extracted["ACD_internal"] = float(value)
                elif key == "ACD external" and "ACD_internal" not in extracted:
                    extracted["ACD_ext_temp"] = float(value)
                elif key == "Cornea Dia Horizontal":
                    extracted["WTW"] = float(value)
                elif key == "Central Corneal Thickness":
                    extracted["CCT"] = float(value)
                elif key == "ACV":
                    extracted["ACV"] = float(value)
                elif key == "SimK steep D":
                    extracted["SimK_steep"] = float(value)
                elif key == "TCRP 3mm zone pupil Km [D]":
                    extracted["TCRP_Km"] = float(value)
                elif key == "TCRP 3mm zone pupil Asti [D]":
                    extracted["TCRP_Astigmatism"] = float(value)
                elif key == "Pupil diameter mm":
                    extracted["Pupil_diameter"] = float(value)
                elif key == "ACA (180°) [°]":
                    extracted["ACA_global"] = float(value)
                elif key == "BAD D":
                    extracted["BAD_D"] = float(value)
                elif key == "Eye":
                    extracted["Eye"] = value.strip().upper()
                elif key == "Test Date":
                    extracted["Exam_Date"] = value.strip()
                    
            except ValueError:
                pass

    # Calculate derived features
    if "ACD_ext_temp" in extracted and "ACD_internal" not in extracted and "CCT" in extracted:
        extracted["ACD_internal"] = round(
            extracted["ACD_ext_temp"] - (extracted["CCT"] / 1000.0), 2
        )
        del extracted["ACD_ext_temp"]

    if "ACV" in extracted and "ACD_internal" in extracted and extracted["ACD_internal"] > 0:
        extracted["AC_shape_ratio"] = round(
            extracted["ACV"] / extracted["ACD_internal"], 2
        )

    # Create PHI hash for deduplication (user can identify patient without us storing PHI)
    phi_hash = None
    if phi_data.get("last_name") and phi_data.get("dob"):
        hash_input = f"{phi_data.get('last_name', '').lower()}:{phi_data.get('first_name', '').lower()}:{phi_data.get('dob', '')}"
        phi_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    # Build patient initials from name fields
    first_initial = phi_data.get("first_name", "")[:1].upper()
    last_initial = phi_data.get("last_name", "")[:1].upper()
    initials = f"{first_initial}{last_initial}" if (first_initial or last_initial) else None

    return {
        "features": extracted,
        "phi_hash": phi_hash,
        "eye": extracted.get("Eye", "UNKNOWN"),
        "initials": initials,
    }


# =============================================================================
# Database Operations
# =============================================================================

class VaultDatabase:
    """Database operations for Vault 3.0."""
    
    def __init__(self, client: Optional[Client] = None):
        self.client = client or get_supabase_client()
    
    # -------------------------------------------------------------------------
    # Patients
    # -------------------------------------------------------------------------
    
    def create_patient(self, user_id: str, anonymous_id: str, notes: str = None) -> dict:
        """Create a new patient record."""
        data = {
            "user_id": user_id,
            "anonymous_id": anonymous_id,
            "notes": notes,
        }
        result = self.client.table("patients").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_patient(self, patient_id: str) -> Optional[dict]:
        """Get patient by ID."""
        result = self.client.table("patients").select("*").eq("id", patient_id).execute()
        return result.data[0] if result.data else None
    
    def get_patient_by_anonymous_id(self, user_id: str, anonymous_id: str) -> Optional[dict]:
        """Get patient by user_id and anonymous_id."""
        result = (
            self.client.table("patients")
            .select("*")
            .eq("user_id", user_id)
            .eq("anonymous_id", anonymous_id)
            .execute()
        )
        return result.data[0] if result.data else None
    
    def list_patients(self, user_id: str) -> list:
        """List all patients for a user."""
        result = (
            self.client.table("patients")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    
    def get_or_create_patient(self, user_id: str, anonymous_id: str) -> dict:
        """Get existing patient or create new one."""
        existing = self.get_patient_by_anonymous_id(user_id, anonymous_id)
        if existing:
            return existing
        return self.create_patient(user_id, anonymous_id)
    
    # -------------------------------------------------------------------------
    # Scans
    # -------------------------------------------------------------------------
    
    def create_scan(
        self,
        patient_id: str,
        user_id: str,
        eye: str,
        features: dict,
        ini_file_path: str = None,
        original_filename: str = None,
    ) -> dict:
        """Create a new scan record."""
        data = {
            "patient_id": patient_id,
            "user_id": user_id,
            "eye": eye.upper() if eye else "OD",
            "features": features,
            "ini_file_path": ini_file_path,
            "original_filename": original_filename,
            "extraction_status": "success" if features else "failed",
            "extracted_at": datetime.utcnow().isoformat(),
        }
        result = self.client.table("scans").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_scan(self, scan_id: str) -> Optional[dict]:
        """Get scan by ID."""
        result = self.client.table("scans").select("*").eq("id", scan_id).execute()
        return result.data[0] if result.data else None
    
    def list_scans(self, user_id: str, patient_id: str = None) -> list:
        """List scans for a user, optionally filtered by patient."""
        query = self.client.table("scans").select("*").eq("user_id", user_id)
        if patient_id:
            query = query.eq("patient_id", patient_id)
        result = query.order("created_at", desc=True).execute()
        return result.data or []
    
    def list_scans_with_patients(self, user_id: str) -> list:
        """List scans with patient info joined."""
        result = (
            self.client.table("scans")
            .select("*, patients(anonymous_id, notes)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    
    # -------------------------------------------------------------------------
    # Predictions
    # -------------------------------------------------------------------------
    
    def create_prediction(
        self,
        scan_id: str,
        predicted_lens_size: str,
        lens_probabilities: dict,
        predicted_vault: float,
        vault_mae: float,
        model_version: str,
        features_used: list,
    ) -> dict:
        """Create a prediction record."""
        data = {
            "scan_id": scan_id,
            "predicted_lens_size": predicted_lens_size,
            "lens_probabilities": lens_probabilities,
            "predicted_vault": predicted_vault,
            "vault_mae": vault_mae,
            "vault_range_low": predicted_vault - vault_mae,
            "vault_range_high": predicted_vault + vault_mae,
            "model_version": model_version,
            "features_used": features_used,
        }
        result = self.client.table("predictions").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_prediction(self, scan_id: str) -> Optional[dict]:
        """Get prediction for a scan."""
        result = (
            self.client.table("predictions")
            .select("*")
            .eq("scan_id", scan_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    
    # -------------------------------------------------------------------------
    # Outcomes
    # -------------------------------------------------------------------------
    
    def create_or_update_outcome(
        self,
        scan_id: str,
        actual_lens_size: str = None,
        vault_1day: float = None,
        vault_1week: float = None,
        vault_1month: float = None,
        surgery_date: str = None,
        notes: str = None,
    ) -> dict:
        """Create or update outcome for a scan."""
        data = {
            "scan_id": scan_id,
            "actual_lens_size": actual_lens_size,
            "vault_1day": vault_1day,
            "vault_1week": vault_1week,
            "vault_1month": vault_1month,
            "surgery_date": surgery_date,
            "notes": notes,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Try to update existing
        existing = (
            self.client.table("outcomes")
            .select("id")
            .eq("scan_id", scan_id)
            .execute()
        )
        
        if existing.data:
            result = (
                self.client.table("outcomes")
                .update(data)
                .eq("scan_id", scan_id)
                .execute()
            )
        else:
            data["recorded_at"] = datetime.utcnow().isoformat()
            result = self.client.table("outcomes").insert(data).execute()
        
        return result.data[0] if result.data else None
    
    def get_outcome(self, scan_id: str) -> Optional[dict]:
        """Get outcome for a scan."""
        result = (
            self.client.table("outcomes")
            .select("*")
            .eq("scan_id", scan_id)
            .execute()
        )
        return result.data[0] if result.data else None
    
    # -------------------------------------------------------------------------
    # Analytics / Export
    # -------------------------------------------------------------------------
    
    def get_user_stats(self, user_id: str) -> dict:
        """Get statistics for a user."""
        patients = self.client.table("patients").select("id", count="exact").eq("user_id", user_id).execute()
        scans = self.client.table("scans").select("id", count="exact").eq("user_id", user_id).execute()
        
        # Get scans with outcomes
        scans_with_outcomes = (
            self.client.table("scans")
            .select("id, outcomes(id)")
            .eq("user_id", user_id)
            .execute()
        )
        outcomes_count = sum(1 for s in (scans_with_outcomes.data or []) if s.get("outcomes"))
        
        return {
            "total_patients": patients.count or 0,
            "total_scans": scans.count or 0,
            "scans_with_outcomes": outcomes_count,
        }
    
    def export_training_data(self, user_id: str) -> list:
        """Export user's data in training format (for model improvement)."""
        result = (
            self.client.table("scans")
            .select("*, predictions(*), outcomes(*)")
            .eq("user_id", user_id)
            .execute()
        )
        
        training_rows = []
        for scan in result.data or []:
            features = scan.get("features") or {}
            outcome = scan.get("outcomes", [{}])[0] if scan.get("outcomes") else {}
            
            if outcome.get("actual_lens_size") or outcome.get("actual_vault"):
                row = {
                    **features,
                    "Lens_Size": outcome.get("actual_lens_size"),
                    "Vault": outcome.get("actual_vault"),
                }
                training_rows.append(row)
        
        return training_rows


# =============================================================================
# Storage Operations
# =============================================================================

class VaultStorage:
    """File storage operations for Vault 3.0."""
    
    BUCKET = "ini-files"
    
    def __init__(self, client: Optional[Client] = None):
        self.client = client or get_supabase_client()
    
    def upload_ini(self, user_id: str, filename: str, content: bytes) -> str:
        """
        Upload INI file to storage.
        
        Returns:
            Storage path (user_id/filename)
        """
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        path = f"{user_id}/{safe_filename}"
        
        self.client.storage.from_(self.BUCKET).upload(
            path,
            content,
            {"content-type": "application/octet-stream"}
        )
        
        return path
    
    def download_ini(self, path: str) -> bytes:
        """Download INI file from storage."""
        response = self.client.storage.from_(self.BUCKET).download(path)
        return response
    
    def delete_ini(self, path: str) -> bool:
        """Delete INI file from storage."""
        self.client.storage.from_(self.BUCKET).remove([path])
        return True
    
    def get_signed_url(self, path: str, expires_in: int = 3600) -> str:
        """Get a signed URL for temporary access."""
        response = self.client.storage.from_(self.BUCKET).create_signed_url(path, expires_in)
        return response.get("signedURL", "")
