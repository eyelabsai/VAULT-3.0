"use client";

import { useMemo, useState, useRef, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";

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

/** Featured models — the two active routing models */
const FEATURED_MODELS: Record<string, { label: string; color: string; notes: string }> = {
  "gestalt-24f-756c": {
    label: "Foundation Model",
    color: "green",
    notes: "Production default for normal/large chambers. Trained Feb 8, 2026.",
  },
  "lgb-27f-756c": {
    label: "Tight Chamber Model",
    color: "blue",
    notes: "Auto-routes for tight chambers (ACD < 3.07 or ACV < 175 or WTW < 11.6). Strongest 12.1 detection. Trained Feb 13, 2026.",
  },
};

const FEATURED_ORDER = ["gestalt-24f-756c", "lgb-27f-756c"];

/** Legacy models — collapsed by default, ablation baselines */
const LEGACY_MODELS = new Set(["gestalt-5f-756c", "gestalt-10f-756c"]);

const getFeaturedStyle = (color: string) => {
  if (color === "green") return {
    bg: "rgba(34, 197, 94, 0.12)",
    border: "rgba(34, 197, 94, 0.5)",
    topBorder: "#22c55e",
    shadow: "0 0 20px rgba(34, 197, 94, 0.15), 0 0 40px rgba(34, 197, 94, 0.05)",
    badgeBg: "rgba(34, 197, 94, 0.25)",
    badgeBorder: "rgba(34, 197, 94, 0.5)",
    badgeText: "#4ade80",
    chipActiveBg: "rgba(34, 197, 94, 0.2)",
    chipInactiveBg: "rgba(34, 197, 94, 0.08)",
    chipActiveBorder: "1px solid rgba(34, 197, 94, 0.5)",
    chipInactiveBorder: "1px solid rgba(34, 197, 94, 0.3)",
    chipActiveText: "#4ade80",
  };
  return {
    bg: "rgba(59, 130, 246, 0.12)",
    border: "rgba(59, 130, 246, 0.5)",
    topBorder: "#3b82f6",
    shadow: "0 0 20px rgba(59, 130, 246, 0.15), 0 0 40px rgba(59, 130, 246, 0.05)",
    badgeBg: "rgba(59, 130, 246, 0.25)",
    badgeBorder: "rgba(59, 130, 246, 0.5)",
    badgeText: "#60a5fa",
    chipActiveBg: "rgba(59, 130, 246, 0.2)",
    chipInactiveBg: "rgba(59, 130, 246, 0.08)",
    chipActiveBorder: "1px solid rgba(59, 130, 246, 0.5)",
    chipInactiveBorder: "1px solid rgba(59, 130, 246, 0.3)",
    chipActiveText: "#60a5fa",
  };
};

export default function ComparePage() {
  const [authChecked, setAuthChecked] = useState(false);
  const [availableModels, setAvailableModels] = useState<Record<string, ModelInfo>>({});
  const [enabledModels, setEnabledModels] = useState<Set<string>>(new Set());
  const [predictions, setPredictions] = useState<Record<string, ModelPrediction>>({});
  const [features, setFeatures] = useState<ParsedFeatures>({});
  const [iclPower, setIclPower] = useState(-10.0);
  const [iclPowerInput, setIclPowerInput] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showLegacy, setShowLegacy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
    []
  );

  // Auth check
  useEffect(() => {
    const checkAuth = async () => {
      const { createClient } = await import("@/lib/supabase");
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push("/login");
        return;
      }
      setAuthChecked(true);
    };
    checkAuth();
  }, [router]);

  const getAccessToken = async (): Promise<string | null> => {
    const { createClient } = await import("@/lib/supabase");
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token || null;
  };

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
      const token = await getAccessToken();

      const formData = new FormData();
      const baseName = file.name.replace(/\.ini$/i, "");
      formData.append("file", file);
      formData.append("anonymous_id", baseName);
      formData.append("icl_power", String(iclPower));

      const res = await fetch(`${apiBase}/beta/compare-upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!res.ok) {
        const payload = await res.json();
        throw new Error(payload.detail || "Failed to upload INI file.");
      }

      const payload = await res.json();
      const extracted = payload.features || {};
      if (payload.patient_first_name) extracted.FirstName = payload.patient_first_name;
      if (payload.patient_last_name) extracted.LastName = payload.patient_last_name;
      setFeatures(extracted);
      setUploadedFileName(file.name);
      setPredictions(payload.predictions || {});
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

  const allVisible = Object.entries(predictions)
    .filter(([tag]) => enabledModels.has(tag))
    .sort(([a], [b]) => {
      const aIdx = FEATURED_ORDER.indexOf(a);
      const bIdx = FEATURED_ORDER.indexOf(b);
      if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
      if (aIdx !== -1) return -1;
      if (bIdx !== -1) return 1;
      return a.localeCompare(b);
    });

  const mainPredictions = allVisible.filter(([tag]) => !LEGACY_MODELS.has(tag));
  const legacyPredictions = allVisible.filter(([tag]) => LEGACY_MODELS.has(tag));

  const patientName = [features.LastName, features.FirstName].filter(Boolean).join(", ");

  if (!authChecked) {
    return (
      <main className="calc-page">
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
          <p style={{ color: "#9ca3af" }}>Loading...</p>
        </div>
      </main>
    );
  }

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
              <div className="bio-field" style={{ marginTop: "12px" }}>
                <label>ICL Power (D)</label>
                <div className="stepper-input">
                  <input
                    type="text"
                    inputMode="decimal"
                    value={iclPowerInput !== "" ? iclPowerInput : iclPower.toFixed(1)}
                    onFocus={() => setIclPowerInput(iclPower.toFixed(1))}
                    onChange={(e) => setIclPowerInput(e.target.value)}
                    onBlur={() => {
                      const num = parseFloat(iclPowerInput);
                      if (!isNaN(num)) setIclPower(num);
                      setIclPowerInput("");
                    }}
                  />
                  <button onClick={() => setIclPower((p) => Number((p - 0.5).toFixed(1)))}>−</button>
                  <button onClick={() => setIclPower((p) => Number((p + 0.5).toFixed(1)))}>+</button>
                </div>
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
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
              {[
                ...FEATURED_ORDER.filter((t) => t in availableModels),
                ...Object.keys(availableModels).filter((t) => !FEATURED_MODELS[t] && !LEGACY_MODELS.has(t)).sort(),
              ].map((tag) => {
                const info = availableModels[tag];
                const active = enabledModels.has(tag);
                const featured = FEATURED_MODELS[tag];
                const style = featured ? getFeaturedStyle(featured.color) : null;
                return (
                  <button
                    key={tag}
                    onClick={() => toggleModel(tag)}
                    style={{
                      padding: "8px 16px", borderRadius: "8px", fontSize: "13px", fontWeight: 500,
                      cursor: "pointer", transition: "all 0.2s",
                      background: active
                        ? (style ? style.chipActiveBg : "rgba(59, 130, 246, 0.2)")
                        : (style ? style.chipInactiveBg : "#1a1a1a"),
                      border: active
                        ? (style ? style.chipActiveBorder : "1px solid rgba(59, 130, 246, 0.5)")
                        : (style ? style.chipInactiveBorder : "1px solid #374151"),
                      color: active ? (style ? style.chipActiveText : "#60a5fa") : "#6b7280",
                    }}
                  >
                    {tag}
                    <span style={{ marginLeft: "6px", fontSize: "11px", opacity: 0.7 }}>
                      {info.feature_count}f
                    </span>
                    {featured && (
                      <span style={{ marginLeft: "6px", fontSize: "10px", color: "inherit", opacity: 0.8 }}>
                        ({featured.label})
                      </span>
                    )}
                  </button>
                );
              })}
              {Object.keys(availableModels).some((t) => LEGACY_MODELS.has(t)) && (
                <>
                  <span style={{ color: "#374151", fontSize: "16px", margin: "0 2px" }}>|</span>
                  {Object.keys(availableModels).filter((t) => LEGACY_MODELS.has(t)).sort().map((tag) => {
                    const info = availableModels[tag];
                    const active = enabledModels.has(tag);
                    return (
                      <button
                        key={tag}
                        onClick={() => toggleModel(tag)}
                        style={{
                          padding: "8px 16px", borderRadius: "8px", fontSize: "13px", fontWeight: 500,
                          cursor: "pointer", transition: "all 0.2s", opacity: 0.6,
                          background: active ? "rgba(107, 114, 128, 0.2)" : "#1a1a1a",
                          border: active ? "1px solid rgba(107, 114, 128, 0.5)" : "1px solid #2a2a2a",
                          color: active ? "#9ca3af" : "#4b5563",
                        }}
                      >
                        {tag}
                        <span style={{ marginLeft: "6px", fontSize: "11px", opacity: 0.7 }}>
                          {info.feature_count}f
                        </span>
                        <span style={{ marginLeft: "6px", fontSize: "10px", color: "inherit", opacity: 0.8 }}>
                          (legacy)
                        </span>
                      </button>
                    );
                  })}
                </>
              )}
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
        {!loading && !uploading && mainPredictions.length > 0 && (
          <div style={{
            display: "grid",
            gridTemplateColumns: mainPredictions.length === 1 ? "1fr" : `repeat(${Math.min(mainPredictions.length, 3)}, 1fr)`,
            gap: "20px",
          }}>
            {mainPredictions.map(([tag, pred]) => {
              const featured = FEATURED_MODELS[tag];
              const style = featured ? getFeaturedStyle(featured.color) : null;
              if (pred.error) {
                return (
                  <div key={tag} style={{
                    background: style ? style.bg : "#1a1a1a",
                    borderRadius: "12px", padding: "24px",
                    border: style ? `1px solid ${style.border}` : "1px solid #374151",
                    borderTop: style ? `3px solid ${style.topBorder}` : undefined,
                    boxShadow: style ? style.shadow : undefined,
                  }}>
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
                  background: style ? style.bg : "#1a1a1a",
                  borderRadius: "12px", padding: "24px",
                  border: style ? `1px solid ${style.border}` : "1px solid #374151",
                  borderTop: style ? `3px solid ${style.topBorder}` : undefined,
                  boxShadow: style ? style.shadow : undefined,
                }}>
                  {/* Model header */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "8px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                      <h3 style={{ color: "#fff", fontSize: "16px", fontWeight: 600, margin: 0 }}>{tag}</h3>
                      {featured && style && (
                        <span style={{
                          padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700,
                          background: style.badgeBg, color: style.badgeText,
                          border: `1px solid ${style.badgeBorder}`,
                          letterSpacing: "0.02em",
                        }}>
                          {featured.label}
                        </span>
                      )}
                    </div>
                    <span style={{
                      padding: "3px 8px", borderRadius: "4px", fontSize: "11px",
                      background: "rgba(139, 92, 246, 0.15)", color: "#a78bfa",
                    }}>
                      {pred.feature_count} features
                    </span>
                  </div>
                  {pred.description && (
                    <p style={{ color: "#6b7280", fontSize: "12px", margin: featured ? "0 0 8px" : "0 0 16px", lineHeight: 1.4 }}>{pred.description}</p>
                  )}
                  {featured && (
                    <p style={{ color: "#9ca3af", fontSize: "11px", margin: "0 0 16px", lineHeight: 1.4, fontStyle: "italic" }}>
                      {featured.notes}
                    </p>
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

        {/* Legacy Models — collapsible */}
        {!loading && !uploading && legacyPredictions.length > 0 && (
          <div style={{ marginTop: "32px" }}>
            {/* Divider with toggle */}
            <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "16px" }}>
              <div style={{ flex: 1, height: "1px", background: "#2a2a2a" }} />
              <button
                onClick={() => setShowLegacy((v) => !v)}
                style={{
                  background: "#1a1a1a",
                  border: "1px solid #374151",
                  borderRadius: "20px",
                  cursor: "pointer",
                  color: "#9ca3af",
                  fontSize: "13px",
                  fontWeight: 500,
                  padding: "8px 20px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  transition: "all 0.2s",
                  whiteSpace: "nowrap",
                }}
              >
                <span style={{
                  display: "inline-block", transition: "transform 0.2s",
                  transform: showLegacy ? "rotate(90deg)" : "rotate(0deg)",
                  fontSize: "10px",
                }}>
                  ▶
                </span>
                Legacy Models
                <span style={{
                  background: "#374151",
                  color: "#9ca3af",
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "1px 7px",
                  borderRadius: "10px",
                }}>
                  {legacyPredictions.length}
                </span>
              </button>
              <div style={{ flex: 1, height: "1px", background: "#2a2a2a" }} />
            </div>

            {showLegacy && (
              <div style={{
                display: "grid",
                gridTemplateColumns: legacyPredictions.length === 1 ? "1fr" : `repeat(${Math.min(legacyPredictions.length, 3)}, 1fr)`,
                gap: "20px",
              }}>
                {legacyPredictions.map(([tag, pred]) => {
                  if (pred.error) {
                    return (
                      <div key={tag} style={{
                        background: "#141414", borderRadius: "12px", padding: "24px",
                        border: "1px solid #262626",
                      }}>
                        <h3 style={{ color: "#9ca3af", fontSize: "16px", margin: "0 0 8px" }}>{tag}</h3>
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
                      background: "#141414", borderRadius: "12px", padding: "24px",
                      border: "1px solid #262626",
                      borderTop: "2px solid #374151",
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "8px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <h3 style={{ color: "#d1d5db", fontSize: "16px", fontWeight: 600, margin: 0 }}>{tag}</h3>
                          <span style={{
                            padding: "3px 10px", borderRadius: "10px", fontSize: "10px", fontWeight: 600,
                            background: "rgba(107, 114, 128, 0.2)", color: "#9ca3af",
                            textTransform: "uppercase" as const, letterSpacing: "0.05em",
                          }}>
                            Legacy
                          </span>
                        </div>
                        <span style={{
                          padding: "3px 8px", borderRadius: "4px", fontSize: "11px",
                          background: "rgba(139, 92, 246, 0.1)", color: "#8b7fc7",
                        }}>
                          {pred.feature_count} features
                        </span>
                      </div>
                      {pred.description && (
                        <p style={{ color: "#6b7280", fontSize: "12px", margin: "0 0 16px", lineHeight: 1.4 }}>{pred.description}</p>
                      )}

                      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "8px", marginBottom: "16px" }}>
                        {SIZES.map((size) => {
                          const sizeStr = String(size);
                          const prob = pred.size_probabilities[sizeStr] || 0;
                          const isBest = sizeStr === bestSize;
                          const isSecond = sizeStr === secondSize;
                          return (
                            <div key={size} style={{
                              textAlign: "center", padding: "12px 4px", borderRadius: "8px",
                              background: isBest ? "rgba(34, 197, 94, 0.08)" : isSecond ? "rgba(250, 204, 21, 0.08)" : "rgba(255,255,255,0.02)",
                              border: isBest ? "2px solid rgba(34, 197, 94, 0.4)" : isSecond ? "1px solid rgba(250, 204, 21, 0.25)" : "1px solid rgba(255,255,255,0.06)",
                            }}>
                              <div style={{ fontSize: "24px", fontWeight: 400, color: isBest ? "#4ade80" : isSecond ? "#facc15" : "#d1d5db" }}>{size}</div>
                              <div style={{ fontSize: "13px", color: isBest ? "#4ade80" : isSecond ? "#facc15" : "#6b7280" }}>{(prob * 100).toFixed(0)}%</div>
                            </div>
                          );
                        })}
                      </div>

                      <div style={{
                        padding: "12px", borderRadius: "8px",
                        background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
                        textAlign: "center",
                      }}>
                        <div style={{ color: "#6b7280", fontSize: "11px", marginBottom: "4px" }}>VAULT RANGE</div>
                        <div style={{ color: "#d1d5db", fontSize: "18px", fontWeight: 600 }}>
                          {pred.vault_range_um[0]} – {pred.vault_range_um[1]} µm
                        </div>
                        {pred.vault_flag !== "ok" && (
                          <div style={{ marginTop: "6px", fontSize: "12px", fontWeight: 500, color: pred.vault_flag === "low" ? "#f87171" : "#facc15" }}>
                            ⚠ {pred.vault_flag === "low" ? "Low vault risk" : "High vault risk"}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
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
        {!loading && !uploading && Object.keys(predictions).length > 0 && mainPredictions.length === 0 && legacyPredictions.length === 0 && (
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
