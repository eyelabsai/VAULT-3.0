"use client";

import { useMemo, useState, useRef, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";

const UserMenu = dynamic(() => import("@/components/UserMenu"), { ssr: false });

type PredictionForm = {
  Age: number | null;
  WTW: number | null;
  ACD_internal: number | null;
  ICL_Power: number | null;
  AC_shape_ratio: number | null;
  SimK_steep: number | null;
  ACV: number | null;
  TCRP_Km: number | null;
  TCRP_Astigmatism: number | null;
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
  Age: null,
  WTW: null,
  ACD_internal: null,
  ICL_Power: -10.0,
  AC_shape_ratio: null,
  SimK_steep: null,
  ACV: null,
  TCRP_Km: null,
  TCRP_Astigmatism: null,
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
  const [inputValues, setInputValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [lastScanId, setLastScanId] = useState<string | null>(null);
  const router = useRouter();

  // Check if user is logged in
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
  const [status, setStatus] = useState<"idle" | "loading">("idle");
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
    []
  );

  const getInputValue = (key: keyof PredictionForm, decimals: number = 2) => {
    if (key in inputValues) {
      return inputValues[key];
    }
    const val = form[key];
    if (val === null || val === undefined) {
      return "";
    }
    if (typeof val === "number") {
      return val.toFixed(decimals);
    }
    return String(val);
  };

  const onFieldChange = (key: keyof PredictionForm, value: string) => {
    setInputValues((prev) => ({ ...prev, [key]: value }));
    if (key === "LastName" || key === "FirstName") {
      setForm((prev) => ({ ...prev, [key]: value }));
    } else {
      const numVal = parseFloat(value);
      if (!isNaN(numVal)) {
        setForm((prev) => ({ ...prev, [key]: numVal }));
      }
    }
  };

  const onFieldBlur = (key: keyof PredictionForm) => {
    setInputValues((prev) => {
      const newValues = { ...prev };
      delete newValues[key];
      return newValues;
    });
  };

  const incrementField = (key: keyof PredictionForm, step: number) => {
    setForm((prev) => ({
      ...prev,
      [key]: Number(((Number(prev[key]) || 0) + step).toFixed(2))
    }));
  };

  const getAccessToken = async (): Promise<string | null> => {
    const { createClient } = await import("@/lib/supabase");
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token || null;
  };

  const handleIniUpload = async (file: File | null) => {
    if (!file) return;
    setError(null);
    setResult(null);
    // Reset form to defaults so stale manual values don't carry over
    setForm({ ...defaultForm });
    setStatus("loading");

    try {
      const token = await getAccessToken();

      // Use beta upload endpoint (saves to Supabase + runs prediction)
      const formData = new FormData();
      // Use INI filename (without extension) as patient identifier
      const baseName = file.name.replace(/\.ini$/i, "");
      formData.append("file", file);
      formData.append("anonymous_id", baseName);
      formData.append("icl_power", String(form.ICL_Power));

      const response = await fetch(`${apiBase}/beta/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData
      });

      if (!response.ok) {
        // Fallback to original parse-ini if beta endpoint fails
        const fallbackFormData = new FormData();
        fallbackFormData.append("file", file);
        const fallbackResponse = await fetch(`${apiBase}/parse-ini`, {
          method: "POST",
          body: fallbackFormData
        });

        if (!fallbackResponse.ok) {
          const payload = await fallbackResponse.json();
          throw new Error(payload.detail || "Failed to parse INI file.");
        }

        const payload = await fallbackResponse.json();
        const extracted = payload.extracted || {};
        const newForm = { ...form, ...extracted, ICL_Power: form.ICL_Power };
        setForm(newForm);
        setUploadedFileName(file.name);

        // Auto-run prediction
        try {
          const predictResponse = await fetch(`${apiBase}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newForm)
          });
          if (predictResponse.ok) {
            setResult(await predictResponse.json());
          }
        } catch {
          // Silently fail prediction
        }
      } else {
        // Beta endpoint succeeded — extract features + prediction from response
        const payload = await response.json();
        const features = payload.features || {};

        // Track scan ID for later Calculate updates
        setLastScanId(payload.scan_id || null);

        const newForm = {
          ...form,
          ...features,
          ICL_Power: form.ICL_Power,
          LastName: payload.patient_last_name || form.LastName,
          FirstName: payload.patient_first_name || form.FirstName,
        };
        setForm(newForm);
        setUploadedFileName(file.name);

        if (payload.prediction) {
          setResult({
            lens_size_mm: payload.prediction.lens_size_mm,
            lens_probability: payload.prediction.lens_probability,
            vault_pred_um: payload.prediction.vault_pred_um,
            vault_range_um: payload.prediction.vault_range_um,
            vault_flag: payload.prediction.vault_flag,
            size_probabilities: Object.entries(payload.prediction.size_probabilities || {}).map(
              ([size, prob]) => ({ size_mm: parseFloat(size), probability: prob as number })
            ),
          });
        } else {
          // Missing features — tell user which ones to fill in
          setResult(null);
          const required = ["Age", "WTW", "ACD_internal", "ICL_Power", "AC_shape_ratio", "SimK_steep", "ACV", "TCRP_Km", "TCRP_Astigmatism"];
          const fieldLabels: Record<string, string> = {
            Age: "Age", WTW: "WTW", ACD_internal: "ACD Internal",
            ICL_Power: "ICL Power", AC_shape_ratio: "AC Shape Ratio",
            SimK_steep: "SimK Steep", ACV: "ACV", TCRP_Km: "TCRP Km",
            TCRP_Astigmatism: "TCRP Astigmatism",
          };
          const missing = required.filter(f => features[f] == null);
          if (missing.length > 0) {
            setError(`Missing from INI: ${missing.map(f => fieldLabels[f] || f).join(", ")}. Please enter manually and click Calculate.`);
          }
        }
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

    // Check for empty required fields
    const required: (keyof PredictionForm)[] = ["Age", "WTW", "ACD_internal", "ICL_Power", "AC_shape_ratio", "SimK_steep", "ACV", "TCRP_Km", "TCRP_Astigmatism"];
    const fieldLabels: Record<string, string> = {
      Age: "Age", WTW: "WTW", ACD_internal: "ACD Internal",
      ICL_Power: "ICL Power", AC_shape_ratio: "AC Shape Ratio",
      SimK_steep: "SimK Steep", ACV: "ACV", TCRP_Km: "TCRP Km",
      TCRP_Astigmatism: "TCRP Astigmatism",
    };
    const missing = required.filter(f => form[f] == null || form[f] === 0);
    if (missing.length > 0) {
      setError(`Missing: ${missing.map(f => fieldLabels[f as string] || f).join(", ")}. Please fill in before calculating.`);
      return;
    }

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

      // Save prediction to Supabase if we have a scan_id from INI upload
      if (lastScanId) {
        try {
          const token = await getAccessToken();
          const lens_probs: Record<string, number> = {};
          payload.size_probabilities.forEach(sp => {
            lens_probs[String(sp.size_mm)] = sp.probability;
          });

          await fetch(`${apiBase}/beta/scans/${lastScanId}/prediction`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({
              predicted_lens_size: String(payload.lens_size_mm),
              lens_probabilities: lens_probs,
              predicted_vault: payload.vault_pred_um,
              vault_mae: 134,
              model_version: "v1.0.0-beta",
              features_used: required,
            }),
          });
        } catch {
          // Silently fail — prediction still shows to user
        }
      }
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

  // Show loading while checking auth
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
      {/* User Menu Top Right */}
      <div className="user-menu-topright">
        <UserMenu />
      </div>

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
            {error && (
              <div style={{
                marginTop: "12px",
                padding: "12px 16px",
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "8px",
                color: "#f87171",
                fontSize: "13px",
                lineHeight: "1.5",
              }}>
                {error}
              </div>
            )}
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
                  type="text"
                  inputMode="numeric"
                  value={getInputValue("Age", 0)}
                  onChange={(e) => onFieldChange("Age", e.target.value)}
                  onBlur={() => onFieldBlur("Age")}
                />
                <button onClick={() => incrementField("Age", -1)}>−</button>
                <button onClick={() => incrementField("Age", 1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>WTW (mm)</label>
              <div className="stepper-input">
                <input
                  type="text"
                  inputMode="decimal"
                  value={getInputValue("WTW")}
                  onChange={(e) => onFieldChange("WTW", e.target.value)}
                  onBlur={() => onFieldBlur("WTW")}
                />
                <button onClick={() => incrementField("WTW", -0.1)}>−</button>
                <button onClick={() => incrementField("WTW", 0.1)}>+</button>
              </div>
              {form.WTW != null && (form.WTW < 8 || form.WTW > 14) && (
                <span className="field-warning">Check value (expected 8–14 mm)</span>
              )}
            </div>

            <div className="bio-field">
              <label>ACD Internal (mm)</label>
              <div className="stepper-input">
                <input
                  type="text"
                  inputMode="decimal"
                  value={getInputValue("ACD_internal")}
                  onChange={(e) => onFieldChange("ACD_internal", e.target.value)}
                  onBlur={() => onFieldBlur("ACD_internal")}
                />
                <button onClick={() => incrementField("ACD_internal", -0.01)}>−</button>
                <button onClick={() => incrementField("ACD_internal", 0.01)}>+</button>
              </div>
              {form.ACD_internal != null && (form.ACD_internal < 0 || form.ACD_internal > 6) && (
                <span className="field-warning">Check value (expected 0–6 mm)</span>
              )}
            </div>

            <div className="bio-field">
              <label>AC Shape Ratio (Jump)</label>
              <div className="stepper-input">
                <input
                  type="text"
                  inputMode="decimal"
                  value={getInputValue("AC_shape_ratio")}
                  onChange={(e) => onFieldChange("AC_shape_ratio", e.target.value)}
                  onBlur={() => onFieldBlur("AC_shape_ratio")}
                />
                <button onClick={() => incrementField("AC_shape_ratio", -1)}>−</button>
                <button onClick={() => incrementField("AC_shape_ratio", 1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>SimK Steep (D)</label>
              <div className="stepper-input">
                <input
                  type="text"
                  inputMode="decimal"
                  value={getInputValue("SimK_steep")}
                  onChange={(e) => onFieldChange("SimK_steep", e.target.value)}
                  onBlur={() => onFieldBlur("SimK_steep")}
                />
                <button onClick={() => incrementField("SimK_steep", -0.1)}>−</button>
                <button onClick={() => incrementField("SimK_steep", 0.1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>ACV (mm³)</label>
              <div className="stepper-input">
                <input
                  type="text"
                  inputMode="decimal"
                  value={getInputValue("ACV")}
                  onChange={(e) => onFieldChange("ACV", e.target.value)}
                  onBlur={() => onFieldBlur("ACV")}
                />
                <button onClick={() => incrementField("ACV", -1)}>−</button>
                <button onClick={() => incrementField("ACV", 1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>TCRP Km (D)</label>
              <div className="stepper-input">
                <input
                  type="text"
                  inputMode="decimal"
                  value={getInputValue("TCRP_Km")}
                  onChange={(e) => onFieldChange("TCRP_Km", e.target.value)}
                  onBlur={() => onFieldBlur("TCRP_Km")}
                />
                <button onClick={() => incrementField("TCRP_Km", -0.1)}>−</button>
                <button onClick={() => incrementField("TCRP_Km", 0.1)}>+</button>
              </div>
            </div>

            <div className="bio-field">
              <label>TCRP Astigmatism (D)</label>
              <div className="stepper-input">
                <input
                  type="text"
                  inputMode="decimal"
                  value={getInputValue("TCRP_Astigmatism")}
                  onChange={(e) => onFieldChange("TCRP_Astigmatism", e.target.value)}
                  onBlur={() => onFieldBlur("TCRP_Astigmatism")}
                />
                <button onClick={() => incrementField("TCRP_Astigmatism", -0.25)}>−</button>
                <button onClick={() => incrementField("TCRP_Astigmatism", 0.25)}>+</button>
              </div>
            </div>
          </div>

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
              <h3 className="size-title">VAULT3 SUGGESTED SIZE</h3>
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
                        ⚠️ WARNING: Anatomical measurements indicate an increased likelihood of vault outside the manufacturer's specified range (250–900 µm).
                      </p>
                    );
                  }
                  return (
                    <p>
                      Based on the file uploaded and surgical results of thousands of eyes, the size most likely to result in an acceptable vault range is as above. The probability of an outlier requiring repeat surgical intervention for size mismatch is &lt;1% based on the data this model was trained on.
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