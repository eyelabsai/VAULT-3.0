from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import pickle
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_TITLE = "ICL Vault API"

app = FastAPI(title=APP_TITLE, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictionInput(BaseModel):
    Age: int = Field(..., ge=18, le=90)
    WTW: float = Field(..., ge=10.0, le=15.0)
    ACD_internal: float = Field(..., ge=2.0, le=5.0)
    ICL_Power: float = Field(..., ge=-30.0, le=0.0)
    AC_shape_ratio: float = Field(..., ge=0.0, le=100.0)
    SimK_steep: float = Field(..., ge=35.0, le=60.0)
    ACV: float = Field(..., ge=50.0, le=400.0)
    TCRP_Km: float = Field(..., ge=35.0, le=60.0)
    TCRP_Astigmatism: float = Field(..., ge=0.0, le=10.0)


class SizeProbability(BaseModel):
    size_mm: float
    probability: float


class PredictionResponse(BaseModel):
    lens_size_mm: float
    lens_probability: float
    vault_pred_um: int
    vault_range_um: List[int]
    vault_flag: str
    size_probabilities: List[SizeProbability]


def get_nomogram_size(wtw: float, acd: float) -> float:
    if wtw < 10.5 or wtw >= 13.0:
        return 0.0

    if 10.5 <= wtw < 10.7:
        return 12.1 if acd > 3.5 else 0.0
    if 10.7 <= wtw < 11.1:
        return 12.1
    if 11.1 <= wtw < 11.2:
        return 12.6 if acd > 3.5 else 12.1
    if 11.2 <= wtw < 11.5:
        return 12.6
    if 11.5 <= wtw < 11.7:
        return 13.2 if acd > 3.5 else 12.6
    if 11.7 <= wtw < 12.2:
        return 13.2
    if 12.2 <= wtw < 12.3:
        return 13.7 if acd > 3.5 else 13.2
    if 12.3 <= wtw < 13.0:
        return 13.7

    return 0.0


def engineer_features(data: dict) -> pd.DataFrame:
    df = pd.DataFrame([data])

    df["WTW_Bucket"] = pd.cut(
        df["WTW"], bins=[0, 11.6, 11.9, 12.4, 20], labels=[0, 1, 2, 3]
    ).astype(int)
    df["ACD_Bucket"] = pd.cut(
        df["ACD_internal"], bins=[0, 3.1, 3.3, 10], labels=[0, 1, 2]
    ).astype(int)
    df["Shape_Bucket"] = pd.cut(
        df["AC_shape_ratio"], bins=[0, 58, 62.5, 68, 300], labels=[0, 1, 2, 3]
    ).astype(int)

    df["Space_Volume"] = df["WTW"] * df["ACD_internal"]
    df["Aspect_Ratio"] = df["WTW"] / df["ACD_internal"]
    df["Power_Density"] = abs(df["ICL_Power"]) / df["ACV"]

    df["High_Power_Deep_ACD"] = (
        (abs(df["ICL_Power"]) > 14) & (df["ACD_internal"] > 3.3)
    ).astype(int)
    df["Chamber_Tightness"] = df["ACV"] / df["WTW"]
    df["Curvature_Depth_Ratio"] = df["SimK_steep"] / df["ACD_internal"]

    df["Stability_Risk"] = (
        (df["TCRP_Astigmatism"] > 1.5) & (df["WTW"] > 12.0)
    ).astype(int)
    df["Age_Space_Ratio"] = df["Age"] / df["ACD_internal"]

    df["Nomogram_Size"] = df.apply(
        lambda row: get_nomogram_size(row["WTW"], row["ACD_internal"]), axis=1
    )

    df["Volume_Constraint"] = (
        (df["Nomogram_Size"] > 12.1) & (df["ACV"] < 170)
    ).astype(int)
    df["Steep_Eye_Adjustment"] = (
        (df["Nomogram_Size"] > 12.1) & (df["SimK_steep"] > 46.0)
    ).astype(int)
    df["Safety_Downsize_Flag"] = (
        (df["Nomogram_Size"] == 13.2) & (abs(df["ICL_Power"]) < 10.0)
    ).astype(int)

    return df


def parse_ini_content(ini_content: str) -> dict:
    extracted: dict = {}
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
                if key == "ACD (Int.) [mm]":
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
                elif key == "Eye":
                    extracted["Eye"] = value.strip().upper()
                elif key == "DOB" and current_section == "Patient Data":
                    try:
                        dob = datetime.strptime(value, "%Y-%m-%d")
                        today = date.today()
                        extracted["Age"] = today.year - dob.year - (
                            (today.month, today.day) < (dob.month, dob.day)
                        )
                    except ValueError:
                        pass
            except ValueError:
                pass

    if (
        "ACD_ext_temp" in extracted
        and "ACD_internal" not in extracted
        and "CCT" in extracted
    ):
        extracted["ACD_internal"] = round(
            extracted["ACD_ext_temp"] - (extracted["CCT"] / 1000.0), 2
        )

    if "ACV" in extracted and "ACD_internal" in extracted and extracted["ACD_internal"] > 0:
        extracted["AC_shape_ratio"] = round(
            extracted["ACV"] / extracted["ACD_internal"], 2
        )

    return extracted


@lru_cache(maxsize=1)
def load_models():
    model_dir = Path(__file__).resolve().parents[2]

    def read_pickle(filename: str):
        path = model_dir / filename
        with path.open("rb") as f:
            return pickle.load(f)

    return {
        "lens_model": read_pickle("lens_size_model.pkl"),
        "lens_scaler": read_pickle("lens_size_scaler.pkl"),
        "vault_model": read_pickle("vault_model.pkl"),
        "vault_scaler": read_pickle("vault_scaler.pkl"),
        "feature_names": read_pickle("feature_names.pkl"),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse-ini")
async def parse_ini(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith(".ini"):
        raise HTTPException(status_code=400, detail="Only .ini files are supported.")

    raw = await file.read()
    try:
        content = raw.decode("utf-8", errors="ignore")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Failed to decode INI file.") from exc

    extracted = parse_ini_content(content)
    return {"extracted": extracted}


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionInput):
    models = load_models()
    df_eng = engineer_features(payload.model_dump())

    feature_names = models["feature_names"]
    X = df_eng[feature_names]
    X_scaled = models["lens_scaler"].transform(X)

    lens_probs = models["lens_model"].predict_proba(X_scaled)[0]
    lens_classes = models["lens_model"].classes_

    top_idx = int(np.argsort(lens_probs)[::-1][0])
    best_size = float(lens_classes[top_idx])
    best_prob = float(lens_probs[top_idx])

    vault_scaled = models["vault_scaler"].transform(X)
    pred_vault = int(models["vault_model"].predict(vault_scaled)[0])

    if pred_vault < 250:
        vault_flag = "low"
    elif pred_vault > 800:
        vault_flag = "high"
    else:
        vault_flag = "ok"

    size_probs = [
        SizeProbability(size_mm=float(size), probability=float(prob))
        for size, prob in zip(lens_classes, lens_probs)
    ]

    return PredictionResponse(
        lens_size_mm=best_size,
        lens_probability=best_prob,
        vault_pred_um=pred_vault,
        vault_range_um=[pred_vault - 125, pred_vault + 125],
        vault_flag=vault_flag,
        size_probabilities=size_probs,
    )
