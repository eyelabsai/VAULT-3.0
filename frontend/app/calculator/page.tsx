"use client";

import { useMemo, useState, useRef } from "react";
import Image from "next/image";

type PredictionForm = {
  Age: number;
  WTW: number;
  ACD_internal: number;
  ICL_Power: number;
  AC_shape_ratio: number;
  SimK_steep: number;
  ACV: number;
  TCRP_Km: number;
  TCRP_Astigmatism: number;
  Eye?: string;
  LastName?: string;
  FirstName?: string;
};

type SizeProbability = {
  size_mm: number;
  probability: number;
};

type PredictionResponse = {
  lens_size_mm: number;
  lens_probability: number;
  vault_pred_um: number;
  vault_range_um: number[];
  vault_flag: "ok" | "low" | "high";
  size_probabilities: SizeProbability[];
};

const defaultForm: PredictionForm = {
  Age: 35,
  WTW: 11.8,
  ACD_internal: 3.2,
  ICL_Power: -9.0,
  AC_shape_ratio: 60.0,
  SimK_steep: 44.0,
  ACV: 180.0,
  TCRP_Km: 44.0,
  TCRP_Astigmatism: 1.0,
  LastName: "",
  FirstName: ""
};

const defaultSizes: SizeProbability[] = [
  { size_mm: 12.1, probability: 0 },
  { size_mm: 12.6, probability: 0 },
  { size_mm: 13.2, probability: 0 },
  { size_mm: 13.7, probability: 0 }
];

export default function Calculator() {
  const [form, setForm] = useState<PredictionForm>(defaultForm);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading">("idle");
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
    []
  );

  const onFieldChange = (key: keyof PredictionForm, value: string) => {
    if (key === "LastName" || key === "FirstName") {
      setForm((prev) => ({ ...prev, [key]: value }));
    } else {
      setForm((prev) => ({
        ...prev,
        [key]: value === "" ? "" : Number(value)
      }));
    }
  };

  const incrementField = (key: keyof PredictionForm, step: number) => {
    setForm((prev) => ({
      ...prev,
      [key]: Number((Number(prev[key]) + step).toFixed(2))
    }));
  };

  const handleIniUpload = async (file: File | null) => {
    if (!file) return;
    setError(null);
    setStatus("loading");

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${apiBase}/parse-ini`, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "Failed to parse INI file.");
      }

      const payload = await response.json();
      const extracted = payload.extracted || {};

      setForm((prev) => ({
        ...prev,
        ...extracted,
        ICL_Power: prev.ICL_Power,
        LastName: prev.LastName,
        FirstName: prev.FirstName
      }));
      setUploadedFileName(file.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setUploadedFileName(null);
    } finally {
      setStatus("idle");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".ini")) {
      handleIniUpload(file);
    }
  };

  const handlePredict = async () => {
    setError(null);
    setStatus("loading");

    try {
      const response = await fetch(`${apiBase}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });

      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "Prediction failed.");
      }

      const payload: PredictionResponse = await response.json();
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed.");
    } finally {
      setStatus("idle");
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const sizeProbabilities = result?.size_probabilities || defaultSizes;
  const patientName = form.LastName || form.FirstName 
    ? `${form.LastName || ""}${form.LastName && form.FirstName ? ", " : ""}${form.FirstName || ""}`
    : "LAST NAME, FIRST NAME";
  const eyeLabel = form.Eye || "—";

  return (
    <main className="calc-page">
      {/* Header */}
      <header className="calc-header">
        <Image
          src="/images/vault-dark-mode.svg"
          alt="Vault 3"
          width={280}
          height={90}
          priority
        />
        <p className="calc-tagline">Pentacam-Based, AI-Driven ICL Sizing Nomogram</p>
      </header>

      <div className="calc-layout">
        {/* Left Sidebar */}
        <aside className="calc-sidebar">
          <button 
            className="calc-btn-primary" 
            onClick={handlePredict} 
            disabled={status === "loading"}
          >
            {status === "loading" ? "Calculating..." : "Calculate"}
          </button>

          <div className="sidebar-section">
            <div className="sidebar-title">Import Pentacam INI</div>
            <div 
              className={`dropzone ${isDragging ? "dragging" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              {uploadedFileName ? (
                <p className="uploaded-file">{uploadedFileName}</p>
              ) : (
                <>
                  <p>Drag and drop file here</p>
                  <span className="dropzone-hint">Limit 200MB per file • INI</span>
                </>
              )}
              <button 
                className="browse-btn"
                onClick={() => fileInputRef.current?.click()}
              >
                Browse files
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".ini"
                style={{ display: "none" }}
                onChange={(e) => handleIniUpload(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-title">Patient Biometrics</div>
            
            <div className="bio-field">
              <label>Eye: {form.Eye || "—"}</label>
            </div>

            <div className="bio-field">
              <label>Age</label>
              <div className="stepper-input">
                <input
                  type="number"
                  value={form.Age}
                  onChange={(e) => onFieldChange("Age", e.target.value)}
                />
                <button onClick={() => incrementField("Age", -1)}>−</button>
                <button onClick={() => incrementField("Age", 1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>WTW (mm)</label>
              <div className="stepper-input">
                <input
                  type="number"
                  step="0.01"
                  value={form.WTW.toFixed(2)}
                  onChange={(e) => onFieldChange("WTW", e.target.value)}
                />
                <button onClick={() => incrementField("WTW", -0.1)}>−</button>
                <button onClick={() => incrementField("WTW", 0.1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>ACD Internal (mm)</label>
              <div className="stepper-input">
                <input
                  type="number"
                  step="0.01"
                  value={form.ACD_internal.toFixed(2)}
                  onChange={(e) => onFieldChange("ACD_internal", e.target.value)}
                />
                <button onClick={() => incrementField("ACD_internal", -0.01)}>−</button>
                <button onClick={() => incrementField("ACD_internal", 0.01)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>AC Shape Ratio (Jump)</label>
              <div className="stepper-input">
                <input
                  type="number"
                  step="0.01"
                  value={form.AC_shape_ratio.toFixed(2)}
                  onChange={(e) => onFieldChange("AC_shape_ratio", e.target.value)}
                />
                <button onClick={() => incrementField("AC_shape_ratio", -1)}>−</button>
                <button onClick={() => incrementField("AC_shape_ratio", 1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>SimK Steep (D)</label>
              <div className="stepper-input">
                <input
                  type="number"
                  step="0.01"
                  value={form.SimK_steep.toFixed(2)}
                  onChange={(e) => onFieldChange("SimK_steep", e.target.value)}
                />
                <button onClick={() => incrementField("SimK_steep", -0.1)}>−</button>
                <button onClick={() => incrementField("SimK_steep", 0.1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>ACV (mm³)</label>
              <div className="stepper-input">
                <input
                  type="number"
                  step="0.01"
                  value={form.ACV.toFixed(2)}
                  onChange={(e) => onFieldChange("ACV", e.target.value)}
                />
                <button onClick={() => incrementField("ACV", -1)}>−</button>
                <button onClick={() => incrementField("ACV", 1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>TCRP Km (D)</label>
              <div className="stepper-input">
                <input
                  type="number"
                  step="0.01"
                  value={form.TCRP_Km.toFixed(2)}
                  onChange={(e) => onFieldChange("TCRP_Km", e.target.value)}
                />
                <button onClick={() => incrementField("TCRP_Km", -0.1)}>−</button>
                <button onClick={() => incrementField("TCRP_Km", 0.1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>TCRP Astigmatism (D)</label>
              <div className="stepper-input">
                <input
                  type="number"
                  step="0.01"
                  value={form.TCRP_Astigmatism.toFixed(2)}
                  onChange={(e) => onFieldChange("TCRP_Astigmatism", e.target.value)}
                />
                <button onClick={() => incrementField("TCRP_Astigmatism", -0.25)}>−</button>
                <button onClick={() => incrementField("TCRP_Astigmatism", 0.25)}>+</button>
              </div>
            </div>
          </div>

          {error && <p className="error">{error}</p>}
        </aside>

        {/* Main Results Area */}
        <section className="calc-results">
          <div className="results-header">
            <h2 className="patient-name">{patientName}</h2>
            {form.Eye && <span className="eye-badge">{form.Eye}</span>}
          </div>

          <div className="size-section">
            <div className="size-section-wrapper">
              <h3 className="size-title">BEST SIZE PROBABILITY</h3>
              <div className="size-grid">
                {sizeProbabilities.map((item) => (
                  <div 
                    key={item.size_mm} 
                    className={`size-card ${result && item.size_mm === result.lens_size_mm ? "best" : ""}`}
                  >
                    <div className="size-value">{item.size_mm}</div>
                    <div className="size-prob">
                      {result ? `${(item.probability * 100).toFixed(0)}%` : "—%"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="vault-section">
            <h3 className="vault-title">PREDICTED VAULT</h3>
            <div className="vault-value">{result ? `${result.vault_pred_um} µm` : "—"}</div>
            {result && (
              <p className="vault-range">
                Expected Range: {result.vault_range_um[0]} - {result.vault_range_um[1]} µm
              </p>
            )}
          </div>

          <button className="print-btn" onClick={handlePrint}>
            PRINT
          </button>
        </section>
      </div>

      {/* Footer */}
      <footer className="calc-footer">
        <Image
          src="/images/vault flavicon.svg"
          alt="Bimini"
          width={80}
          height={24}
          className="footer-logo"
        />
      </footer>
    </main>
  );
}