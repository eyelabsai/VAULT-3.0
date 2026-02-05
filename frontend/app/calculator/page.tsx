"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
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
  TCRP_Astigmatism: 1.0
};

export default function Calculator() {
  const [form, setForm] = useState<PredictionForm>(defaultForm);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading">("idle");
  const [error, setError] = useState<string | null>(null);

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
    []
  );

  const onFieldChange = (key: keyof PredictionForm, value: string) => {
    setForm((prev) => ({
      ...prev,
      [key]: value === "" ? "" : Number(value)
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
        ICL_Power: prev.ICL_Power
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setStatus("idle");
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

  return (
    <main className="calculator-page">
      <nav className="calculator-nav">
        <Link href="/" className="nav-logo">
          <Image
            src="/images/vault-dark-mode.svg"
            alt="Vault 3"
            width={120}
            height={40}
            priority
          />
        </Link>
      </nav>

      <header className="calculator-header">
        <h1 className="calculator-title">ICL Sizing Calculator</h1>
        <p className="calculator-subtitle">
          Clinical decision support for ICL lens size and post-operative vault prediction
        </p>
      </header>

      <div className="calculator-grid">
        <section className="calculator-card">
          <div className="section-title">Data Import</div>
          <div className="field">
            <label htmlFor="iniUpload">Pentacam INI</label>
            <input
              id="iniUpload"
              type="file"
              accept=".ini"
              onChange={(event) => handleIniUpload(event.target.files?.[0] ?? null)}
            />
          </div>
          {form.Eye && (
            <div className="field">
              <label>Eye</label>
              <div className="pill">{form.Eye}</div>
            </div>
          )}
          <div className="section-title">Patient Biometrics</div>
          <div className="field">
            <label>Age</label>
            <input
              type="number"
              value={form.Age}
              onChange={(event) => onFieldChange("Age", event.target.value)}
            />
          </div>
          <div className="field">
            <label>WTW (mm)</label>
            <input
              type="number"
              step="0.1"
              value={form.WTW}
              onChange={(event) => onFieldChange("WTW", event.target.value)}
            />
          </div>
          <div className="field">
            <label>ACD Internal (mm)</label>
            <input
              type="number"
              step="0.01"
              value={form.ACD_internal}
              onChange={(event) => onFieldChange("ACD_internal", event.target.value)}
            />
          </div>
          <div className="field">
            <label>AC Shape Ratio (Jump)</label>
            <input
              type="number"
              step="0.1"
              value={form.AC_shape_ratio}
              onChange={(event) =>
                onFieldChange("AC_shape_ratio", event.target.value)
              }
            />
          </div>
          <div className="field">
            <label>SimK Steep (D)</label>
            <input
              type="number"
              step="0.1"
              value={form.SimK_steep}
              onChange={(event) => onFieldChange("SimK_steep", event.target.value)}
            />
          </div>
          <div className="field">
            <label>ACV (mm³)</label>
            <input
              type="number"
              step="1"
              value={form.ACV}
              onChange={(event) => onFieldChange("ACV", event.target.value)}
            />
          </div>
          <div className="field">
            <label>TCRP Km (D)</label>
            <input
              type="number"
              step="0.1"
              value={form.TCRP_Km}
              onChange={(event) => onFieldChange("TCRP_Km", event.target.value)}
            />
          </div>
          <div className="field">
            <label>TCRP Astigmatism (D)</label>
            <input
              type="number"
              step="0.25"
              value={form.TCRP_Astigmatism}
              onChange={(event) =>
                onFieldChange("TCRP_Astigmatism", event.target.value)
              }
            />
          </div>
          <button className="calculator-button" onClick={handlePredict} disabled={status === "loading"}>
            {status === "loading" ? "Calculating..." : "Calculate"}
          </button>
          {error && <p className="error">{error}</p>}
        </section>

        <section className="calculator-card">
          <div className="section-title">Results</div>
          {!result && (
            <p className="placeholder-text">Enter patient measurements and click Calculate.</p>
          )}
          {result && (
            <>
              <div>
                <label>Lens Size</label>
                <div className="result-value">{result.lens_size_mm} mm</div>
                <div className="pill">
                  Probability: {(result.lens_probability * 100).toFixed(1)}%
                </div>
              </div>
              <div style={{ marginTop: 24 }}>
                <label>Predicted Vault</label>
                <div className="result-value">{result.vault_pred_um} µm</div>
                <div className="pill">
                  Expected Range: {result.vault_range_um[0]}-{result.vault_range_um[1]} µm
                </div>
              </div>
              <div style={{ marginTop: 16 }} className={`alert ${result.vault_flag}`}>
                {result.vault_flag === "ok" && "Optimal Vault Range Predicted"}
                {result.vault_flag === "low" && "Low Vault Predicted (Below 250µm)"}
                {result.vault_flag === "high" && "High Vault Predicted (Above 800µm)"}
              </div>

              <div style={{ marginTop: 24 }}>
                <div className="section-title">Size Probability Distribution</div>
                <div className="prob-grid">
                  {result.size_probabilities.map((item) => (
                    <div className="prob-card" key={item.size_mm}>
                      <div>{item.size_mm}mm</div>
                      <strong>{(item.probability * 100).toFixed(1)}%</strong>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
