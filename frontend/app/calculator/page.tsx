"use client";

import { useMemo, useState, useRef } from "react";
import Image from "next/image";
import Link from "next/link";

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

      const newForm = {
        ...form,
        ...extracted,
        ICL_Power: form.ICL_Power
      };
      setForm(newForm);
      setUploadedFileName(file.name);
      
      // Auto-run prediction after INI upload
      try {
        const predictResponse = await fetch(`${apiBase}/predict`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(newForm)
        });

        if (predictResponse.ok) {
          const predictPayload = await predictResponse.json();
          setResult(predictPayload);
        }
      } catch {
        // Silently fail prediction, user can manually calculate
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setUploadedFileName(null);
    } finally {
      setStatus("idle");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.toLowerCase().endsWith(".ini")) {
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
    const lastName = form.LastName || "";
    const firstName = form.FirstName || "";
    const eye = form.Eye || "";
    const namePart = `${lastName}${firstName ? "_" + firstName : ""}`.trim();
    const fileName = namePart 
      ? `${namePart}_${eye}_ICL_Vault`.replace(/\s+/g, "_")
      : "ICL_Vault_Report";
    
    document.title = fileName;
    window.print();
    document.title = "ICL Vault";
  };

  const sizeProbabilities = result?.size_probabilities || defaultSizes;
  
  const sortedByProb = result 
    ? [...result.size_probabilities].sort((a, b) => b.probability - a.probability)
    : [];
  const secondBestSize = sortedByProb.length > 1 ? sortedByProb[1].size_mm : null;

  return (
    <main className="calc-page">
      {/* Bimini Logo Top Right */}
      <a href="https://biminiai.com/" target="_blank" rel="noopener noreferrer" className="bimini-logo-topright">
        <Image
          src="/images/bimini-darkmode.svg"
          alt="Bimini"
          width={100}
          height={32}
        />
      </a>

      {/* Header */}
      <header className="calc-header">
        <Link href="/">
          <Image
            src="/images/vault-dark-mode.svg"
            alt="Vault 3"
            width={280}
            height={90}
            priority
            className="vault-logo-link"
          />
        </Link>
        <p className="calc-tagline">Pentacam-Based, AI-Driven ICL Sizing Nomogram</p>
      </header>

      <div className="calc-layout">
        {/* Left Sidebar */}
        <aside className="calc-sidebar">
          <div className="sidebar-section">
            <div className="sidebar-title">Import Pentacam INI</div>
            <div 
              className={`dropzone ${isDragging ? "dragging" : ""}`}
              onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
              onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
              onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); }}
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
            <button 
              className="calc-btn-primary" 
              onClick={handlePredict} 
              disabled={status === "loading"}
            >
              {status === "loading" ? "Calculating..." : "Calculate"}
            </button>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-title">Patient Biometrics</div>
            
            <div className={`bio-field eye-field ${form.Eye === "OD" ? "eye-od" : ""} ${form.Eye === "OS" ? "eye-os" : ""}`}>
              <label>Eye: {form.Eye ? `${form.Eye} — ${form.Eye === "OD" ? "Right Eye" : "Left Eye"}` : "—"}</label>
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
          {(form.FirstName || form.LastName || form.Eye) && (
            <div className="results-header">
              {(form.FirstName || form.LastName) && (
                <span className="patient-name">
                  {form.LastName && form.FirstName 
                    ? `${form.LastName}, ${form.FirstName}` 
                    : form.LastName || form.FirstName || "Patient"}
                </span>
              )}
              {form.Eye && (
                <span className={`eye-badge ${form.Eye === "OD" ? "eye-right" : "eye-left"}`}>
                  {form.Eye} — {form.Eye === "OD" ? "Right Eye" : "Left Eye"}
                </span>
              )}
            </div>
          )}

          <div className="size-section">
            <div className="size-section-wrapper">
              <h3 className="size-title">VAULT 3 SUGGESTED SIZE</h3>
              <div className="size-grid">
                {sizeProbabilities.map((item) => {
                  const isBest = result && item.size_mm === result.lens_size_mm;
                  const isSecond = result && item.size_mm === secondBestSize;
                  return (
                    <div 
                      key={item.size_mm} 
                      className={`size-card ${isBest ? "best" : ""} ${isSecond ? "second" : ""}`}
                    >
                      <div className="size-value">{item.size_mm}</div>
                      {/* <div className="size-prob">
                        {result ? `${(item.probability * 100).toFixed(0)}%` : "—%"}
                      </div> */}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="vault-section">
            {/* <h3 className="vault-title">PREDICTED VAULT</h3>
            <div className="vault-value">{result ? `${result.vault_pred_um} µm` : "—"}</div> */}
            {result && (
              <p className="vault-range">
                Expected Range: {result.vault_range_um[0]} - {result.vault_range_um[1]} µm
              </p>
            )}
            {result && (
              <div className="results-disclaimer">
                {(() => {
                  const v = result.vault_pred_um;
                  const outlierPct = v < 400 ? 36 : v < 500 ? 15 : v < 600 ? 7 : v < 700 ? 6 : v < 800 ? 20 : 83;
                  if (outlierPct > 10) {
                    return (
                      <p className="disclaimer-warning">
                        WARNING: Based on eye anatomy, there is an &gt;10% risk the resulting vault may be outside the manufacturer's specified range (250–900 µm).
                      </p>
                    );
                  }
                  return (
                    <p>
                      Based on the file uploaded and surgical results of thousands of eyes, the size most likely to result in an acceptable vault range is as above. The probability of an outlier requiring repeat surgical intervention for size mismatch is &lt;10% based on the data this model was trained on.
                    </p>
                  );
                })()}
                <div className="color-legend">
                  <p><span className="legend-green">Green</span> — Indicates the size that best aligns with this eye's measured anatomy and is expected to produce a vault closest to the ideal range based on prior results.</p>
                  <p><span className="legend-yellow">Yellow</span> — Indicates a size that is anatomically plausible based on surgeon discretion.</p>
                </div>
              </div>
            )}
            <button className="print-btn" onClick={handlePrint}>
              PRINT
            </button>
          </div>
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