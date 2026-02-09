"use client";

import { useMemo, useState, useRef, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";

type ModelInfo = {
  feature_count: number;
  features: string[];
  lens_model: string;
  vault_model: string;
  description: string;
};

type ModelPrediction = {
  lens_size_mm: number;
  lens_probability: number;
  vault_pred_um: number;
  vault_range_um: number[];
  vault_flag: "ok" | "low" | "high";
  size_probabilities: Record<string, number>;
  feature_count: number;
  description: string;
  error?: string;
};

type ParsedFeatures = {
  Age?: number;
  WTW?: number;
  ACD_internal?: number;
  ICL_Power?: number;
  AC_shape_ratio?: number;
  SimK_steep?: number;
  ACV?: number;
  TCRP_Km?: number;
  TCRP_Astigmatism?: number;
  Eye?: string;
  FirstName?: string;
  LastName?: string;
  [key: string]: unknown;
};

const SIZES = [12.1, 12.6, 13.2, 13.7];

export default function ComparePage() {
  const [availableModels, setAvailableModels] = useState<Record<string, ModelInfo>>({});
  const [enabledModels, setEnabledModels] = useState<Set<string>>(new Set());
  const [predictions, setPredictions] = useState<Record<string, ModelPrediction>>({});
  const [features, setFeatures] = useState<ParsedFeatures>({});
  const [iclPower, setIclPower] = useState(-10.0);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
    []
  );

  // Load available models on mount
  useEffect(() => {
    fetch(`${apiBase}/models`)
      .then((r) => r.json())
      .then((data) => {
        setAvailableModels(data);
        setEnabledModels(new Set(Object.keys(data)));
      })
      .catch(() => setError("Failed to load models"));
  }, [apiBase]);

  const toggleModel = (tag: string) => {
    setEnabledModels((prev) => {
      const next = new Set(prev);
      if (next.has(tag)) {
        next.delete(tag);
      } else {
        next.add(tag);
      }
      return next;
    });
  };

  const enableAll = () => setEnabledModels(new Set(Object.keys(availableModels)));
  const disableAll = () => setEnabledModels(new Set());

  const handleIniUpload = async (file: File | null) => {
    if (!file) return;
    setError(null);
    setPredictions({});
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${apiBase}/parse-ini`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const payload = await res.json();
        throw new Error(payload.detail || "Failed to parse INI file.");
      }

      const payload = await res.json();
      const extracted = payload.extracted || {};
      setFeatures(extracted);
      setUploadedFileName(file.name);

      // Auto-run comparison if we have enough features
      const required = ["Age", "WTW", "ACD_internal", "AC_shape_ratio", "SimK_steep", "ACV", "TCRP_Km", "TCRP_Astigmatism"];
      const missing = required.filter((f) => extracted[f] == null);
      if (missing.length > 0) {
        setError(`Missing from INI: ${missing.join(", ")}. Cannot run comparison.`);
      } else {
        await runComparison({ ...extracted, ICL_Power: iclPower });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setUploadedFileName(null);
    } finally {
      setUploading(false);
    }
  };

  const runComparison = async (feats: ParsedFeatures) => {
    setLoading(true);
    setError(null);

    try {
      const body = {
        Age: Math.round(Number(feats.Age)),
        WTW: Number(feats.WTW),
        ACD_internal: Number(feats.ACD_internal),
        ICL_Power: Number(feats.ICL_Power ?? iclPower),
        AC_shape_ratio: Number(feats.AC_shape_ratio),
        SimK_steep: Number(feats.SimK_steep),
        ACV: Number(feats.ACV),
        TCRP_Km: Number(feats.TCRP_Km),
        TCRP_Astigmatism: Number(feats.TCRP_Astigmatism),
      };

      const res = await fetch(`${apiBase}/predict-compare?models=all`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const payload = await res.json();
        throw new Error(payload.detail || "Comparison failed.");
      }

      const data = await res.json();
      setPredictions(data.predictions || {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed.");
    } finally {
      setLoading(false);
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

  const visiblePredictions = Object.entries(predictions).filter(([tag]) =>
    enabledModels.has(tag)
  );

  const patientName = [features.LastName, features.FirstName].filter(Boolean).join(", ");

  return (
    <main className="calc-page">
      <header className="calc-header" style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <Link href="/">
          <Image src="/images/vault-dark-mode.svg" alt="Vault 3" width={200} height={65} priority className="vault-logo-link" />
        </Link>
        <span style={{ color: "#6b7280", fontSize: "14px" }}>Model Comparison</span>
      </header>

      <div style={{ padding: "20px 40px", maxWidth: "1400px", margin: "0 auto" }}>

        {/* Upload Section */}
        <div style={{ display: "flex", gap: "24px", marginBottom: "32px", flexWrap: "wrap" }}>
          <div style={{ flex: "1", minWidth: "300px" }}>
            <div style={{ background: "#1a1a1a", borderRadius: "12px", padding: "20px" }}>
              <h3 style={{ color: "#9ca3af", fontSize: "13px", fontWeight: 600, marginBottom: "12px", marginTop: 0 }}>Upload Pentacam INI</h3>
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
                    <p>Drag and drop INI file here</p>
                    <span className="dropzone-hint">Upload a Pentacam INI to compare all models</span>
                  </>
                )}
                <button className="browse-btn" onClick={() => fileInputRef.current?.click()}>
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
              <div style={{ marginTop: "12px" }}>
                <label style={{ color: "#9ca3af", fontSize: "13px" }}>ICL Power (D)</label>
                <input
                  type="number"
                  value={iclPower}
                  onChange={(e) => setIclPower(parseFloat(e.target.value) || -10)}
                  step={0.5}
                  style={{
                    width: "100%", marginTop: "4px", padding: "8px 12px",
                    background: "#262626", border: "1px solid #374151", borderRadius: "6px",
                    color: "#fff", fontSize: "14px",
                  }}
                />
              </div>
              {uploadedFileName && features.Age != null && (
                <button
                  className="calc-btn-primary"
                  style={{ marginTop: "12px" }}
                  onClick={() => runComparison({ ...features, ICL_Power: iclPower })}
                  disabled={loading}
                >
                  {loading ? "Comparing..." : "Re-run Comparison"}
                </button>
              )}
            </div>
          </div>

          {/* Patient Info */}
          {features.Age != null && (
            <div style={{ flex: "1", minWidth: "300px" }}>
              <div style={{ background: "#1a1a1a", borderRadius: "12px", padding: "20px" }}>
                <h3 style={{ color: "#9ca3af", fontSize: "13px", fontWeight: 600, marginBottom: "12px", marginTop: 0 }}>Extracted Features</h3>
                {patientName && <p style={{ color: "#fff", fontSize: "18px", fontWeight: 600, margin: "0 0 8px" }}>{patientName}</p>}
                {features.Eye && (
                  <span style={{
                    padding: "3px 10px", borderRadius: "4px", fontSize: "12px", fontWeight: 600,
                    background: features.Eye === "OD" ? "rgba(59, 130, 246, 0.2)" : "rgba(168, 85, 247, 0.2)",
                    color: features.Eye === "OD" ? "#60a5fa" : "#c084fc",
                    marginBottom: "12px", display: "inline-block",
                  }}>{features.Eye}</span>
                )}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px", marginTop: "8px" }}>
                  {[
                    ["Age", features.Age, 0],
                    ["WTW", features.WTW, 1],
                    ["ACD", features.ACD_internal, 2],
                    ["ACV", features.ACV, 0],
                    ["Shape", features.AC_shape_ratio, 1],
                    ["SimK", features.SimK_steep, 1],
                    ["TCRP", features.TCRP_Km, 1],
                    ["Astig", features.TCRP_Astigmatism, 2],
                    ["ICL Pw", iclPower, 1],
                  ].map(([label, val, dec]) => (
                    <div key={label as string} style={{ padding: "6px 8px", background: "#262626", borderRadius: "6px" }}>
                      <span style={{ color: "#6b7280", fontSize: "11px", display: "block" }}>{label as string}</span>
                      <span style={{ color: "#fff", fontSize: "14px", fontWeight: 500 }}>
                        {val != null ? Number(val).toFixed(dec as number) : "—"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div style={{
            marginBottom: "20px", padding: "12px 16px",
            background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "8px", color: "#f87171", fontSize: "13px",
          }}>
            {error}
          </div>
        )}

        {/* Model Toggle Chips */}
        {Object.keys(availableModels).length > 0 && (
          <div style={{ marginBottom: "24px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px", flexWrap: "wrap" }}>
              <span style={{ color: "#9ca3af", fontSize: "13px", fontWeight: 600 }}>MODELS:</span>
              <button
                onClick={enableAll}
                style={{
                  padding: "4px 12px", borderRadius: "4px", fontSize: "11px",
                  background: "transparent", border: "1px solid #374151", color: "#9ca3af", cursor: "pointer",
                }}
              >All On</button>
              <button
                onClick={disableAll}
                style={{
                  padding: "4px 12px", borderRadius: "4px", fontSize: "11px",
                  background: "transparent", border: "1px solid #374151", color: "#9ca3af", cursor: "pointer",
                }}
              >All Off</button>
            </div>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {Object.entries(availableModels).map(([tag, info]) => {
                const active = enabledModels.has(tag);
                return (
                  <button
                    key={tag}
                    onClick={() => toggleModel(tag)}
                    style={{
                      padding: "8px 16px", borderRadius: "8px", fontSize: "13px", fontWeight: 500,
                      cursor: "pointer", transition: "all 0.2s",
                      background: active ? "rgba(59, 130, 246, 0.2)" : "#1a1a1a",
                      border: active ? "1px solid rgba(59, 130, 246, 0.5)" : "1px solid #374151",
                      color: active ? "#60a5fa" : "#6b7280",
                    }}
                  >
                    {tag}
                    <span style={{ marginLeft: "6px", fontSize: "11px", opacity: 0.7 }}>
                      {info.feature_count}f
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Loading */}
        {(loading || uploading) && (
          <div style={{ textAlign: "center", padding: "40px", color: "#9ca3af" }}>
            {uploading ? "Parsing INI file..." : "Running predictions across all models..."}
          </div>
        )}

        {/* Results */}
        {!loading && !uploading && visiblePredictions.length > 0 && (
          <div style={{
            display: "grid",
            gridTemplateColumns: visiblePredictions.length === 1 ? "1fr" : `repeat(${Math.min(visiblePredictions.length, 3)}, 1fr)`,
            gap: "20px",
          }}>
            {visiblePredictions.map(([tag, pred]) => {
              if (pred.error) {
                return (
                  <div key={tag} style={{ background: "#1a1a1a", borderRadius: "12px", padding: "24px", border: "1px solid #374151" }}>
                    <h3 style={{ color: "#fff", fontSize: "16px", margin: "0 0 8px" }}>{tag}</h3>
                    <p style={{ color: "#f87171", fontSize: "13px", margin: 0 }}>Error: {pred.error}</p>
                  </div>
                );
              }

              const sortedProbs = Object.entries(pred.size_probabilities)
                .sort(([, a], [, b]) => b - a);
              const bestSize = sortedProbs[0]?.[0];
              const secondSize = sortedProbs[1]?.[0];

              return (
                <div key={tag} style={{
                  background: "#1a1a1a", borderRadius: "12px", padding: "24px",
                  border: "1px solid #374151",
                }}>
                  {/* Model header */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                    <h3 style={{ color: "#fff", fontSize: "16px", fontWeight: 600, margin: 0 }}>{tag}</h3>
                    <span style={{
                      padding: "3px 8px", borderRadius: "4px", fontSize: "11px",
                      background: "rgba(139, 92, 246, 0.15)", color: "#a78bfa",
                    }}>
                      {pred.feature_count} features
                    </span>
                  </div>
                  {pred.description && (
                    <p style={{ color: "#6b7280", fontSize: "12px", margin: "0 0 16px", lineHeight: 1.4 }}>{pred.description}</p>
                  )}

                  {/* Lens size cards */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "8px", marginBottom: "16px" }}>
                    {SIZES.map((size) => {
                      const sizeStr = String(size);
                      const prob = pred.size_probabilities[sizeStr] || 0;
                      const isBest = sizeStr === bestSize;
                      const isSecond = sizeStr === secondSize;

                      return (
                        <div key={size} style={{
                          textAlign: "center", padding: "12px 4px", borderRadius: "8px",
                          background: isBest ? "rgba(34, 197, 94, 0.1)" : isSecond ? "rgba(250, 204, 21, 0.1)" : "rgba(255,255,255,0.03)",
                          border: isBest ? "2px solid rgba(34, 197, 94, 0.5)" : isSecond ? "1px solid rgba(250, 204, 21, 0.3)" : "1px solid rgba(255,255,255,0.08)",
                        }}>
                          <div style={{
                            fontSize: "24px", fontWeight: 400,
                            color: isBest ? "#4ade80" : isSecond ? "#facc15" : "#fff",
                          }}>{size}</div>
                          <div style={{
                            fontSize: "13px",
                            color: isBest ? "#4ade80" : isSecond ? "#facc15" : "#6b7280",
                          }}>{(prob * 100).toFixed(0)}%</div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Vault */}
                  <div style={{
                    padding: "12px", borderRadius: "8px",
                    background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                    textAlign: "center",
                  }}>
                    <div style={{ color: "#9ca3af", fontSize: "11px", marginBottom: "4px" }}>VAULT RANGE</div>
                    <div style={{ color: "#fff", fontSize: "18px", fontWeight: 600 }}>
                      {pred.vault_range_um[0]} – {pred.vault_range_um[1]} µm
                    </div>
                    {pred.vault_flag !== "ok" && (
                      <div style={{
                        marginTop: "6px", fontSize: "12px", fontWeight: 500,
                        color: pred.vault_flag === "low" ? "#f87171" : "#facc15",
                      }}>
                        ⚠ {pred.vault_flag === "low" ? "Low vault risk" : "High vault risk"}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Empty state */}
        {!loading && !uploading && Object.keys(predictions).length === 0 && (
          <div style={{
            textAlign: "center", padding: "60px 20px",
            background: "#1a1a1a", borderRadius: "12px", border: "1px solid #374151",
          }}>
            <p style={{ color: "#9ca3af", fontSize: "16px", margin: "0 0 8px" }}>
              Upload a Pentacam INI file to compare predictions across all models
            </p>
            <p style={{ color: "#6b7280", fontSize: "14px", margin: 0 }}>
              {Object.keys(availableModels).length} models available
            </p>
          </div>
        )}

        {/* No models selected */}
        {!loading && !uploading && Object.keys(predictions).length > 0 && visiblePredictions.length === 0 && (
          <div style={{
            textAlign: "center", padding: "40px",
            background: "#1a1a1a", borderRadius: "12px", border: "1px solid #374151",
          }}>
            <p style={{ color: "#9ca3af", fontSize: "14px", margin: 0 }}>
              No models selected — toggle models above to see predictions
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
