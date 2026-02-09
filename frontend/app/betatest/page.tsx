"use client";

import { useState, useEffect, useMemo } from "react";
import Image from "next/image";
import Link from "next/link";

type Scan = {
  scan_id: string;
  doctor: string;
  doctor_email: string;
  patient_id: string;
  eye: string;
  scan_date: string;
  age: number | null;
  wtw: number | null;
  acd_internal: number | null;
  acv: number | null;
  ac_shape_ratio: number | null;
  simk_steep: number | null;
  tcrp_km: number | null;
  tcrp_astigmatism: number | null;
  icl_power: number | null;
  cct: number | null;
  predicted_lens_size: string | null;
  predicted_vault: number | null;
  vault_range_low: number | null;
  vault_range_high: number | null;
  prob_12_1: number;
  prob_12_6: number;
  prob_13_2: number;
  prob_13_7: number;
  model_version: string;
  actual_lens_size: string | null;
  vault_1day: number | null;
  vault_1week: number | null;
  vault_1month: number | null;
  surgery_date: string | null;
};

type Summary = {
  total_scans: number;
  total_doctors: number;
  with_outcomes: number;
  current_model?: string;
  current_model_mae?: number;
};

type SortKey = keyof Scan;
type SortDir = "asc" | "desc";

const ADMIN_KEY = "vaultbeta2026";

export default function BetaTestPage() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("scan_date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [filterDoctor, setFilterDoctor] = useState("all");
  const [filterEye, setFilterEye] = useState("all");
  const [filterLens, setFilterLens] = useState("all");
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [tab, setTab] = useState<"scans" | "features" | "probabilities">("scans");

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${apiBase}/beta/admin/export?key=${ADMIN_KEY}`);
        if (!res.ok) throw new Error("Failed to fetch data");
        const data = await res.json();
        setScans(data.scans || []);
        setSummary(data.summary || null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [apiBase]);

  const doctors = useMemo(() => [...new Set(scans.map(s => s.doctor))].sort(), [scans]);
  const lensOptions = useMemo(() => [...new Set(scans.map(s => s.predicted_lens_size).filter(Boolean))].sort(), [scans]);

  const filtered = useMemo(() => {
    return scans.filter(s => {
      if (filterDoctor !== "all" && s.doctor !== filterDoctor) return false;
      if (filterEye !== "all" && s.eye !== filterEye) return false;
      if (filterLens !== "all" && s.predicted_lens_size !== filterLens) return false;
      return true;
    });
  }, [scans, filterDoctor, filterEye, filterLens]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDir === "asc" ? aVal - bVal : bVal - aVal;
      }
      const aStr = String(aVal);
      const bStr = String(bVal);
      return sortDir === "asc" ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
    });
  }, [filtered, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const SortHeader = ({ label, field }: { label: string; field: SortKey }) => (
    <th
      onClick={() => handleSort(field)}
      className="beta-th"
    >
      {label}
      {sortKey === field && (
        <span className="sort-arrow">{sortDir === "asc" ? " ↑" : " ↓"}</span>
      )}
    </th>
  );

  const fmt = (v: number | null, d: number = 1) => v != null ? v.toFixed(d) : "—";
  const pct = (v: number) => v > 0 ? `${(v * 100).toFixed(1)}%` : "—";

  if (loading) {
    return (
      <main className="calc-page">
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
          <p style={{ color: "#9ca3af" }}>Loading beta data...</p>
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
        <div style={{ textAlign: "right" }}>
          <span style={{ color: "#6b7280", fontSize: "14px" }}>Beta Data Dashboard</span>
          {summary?.current_model && (
            <div style={{ marginTop: "4px", display: "flex", alignItems: "center", gap: "8px", justifyContent: "flex-end" }}>
              <span style={{
                padding: "3px 10px", borderRadius: "4px", fontSize: "12px", fontWeight: "600",
                background: "rgba(34, 197, 94, 0.15)", color: "#4ade80", border: "1px solid rgba(34, 197, 94, 0.3)"
              }}>
                LIVE: {summary.current_model}
              </span>
              {summary.current_model_mae && (
                <span style={{ color: "#6b7280", fontSize: "11px" }}>MAE: {summary.current_model_mae}µm</span>
              )}
            </div>
          )}
        </div>
      </header>

      <div className="beta-container">
        {error && <p style={{ color: "#f87171", marginBottom: "16px" }}>{error}</p>}

        {/* Summary Cards */}
        {summary && (
          <div className="beta-stats">
            <div className="beta-stat-card">
              <p className="beta-stat-label">Total Scans</p>
              <p className="beta-stat-value">{summary.total_scans}</p>
            </div>
            <div className="beta-stat-card">
              <p className="beta-stat-label">Doctors</p>
              <p className="beta-stat-value">{summary.total_doctors}</p>
            </div>
            <div className="beta-stat-card">
              <p className="beta-stat-label">With Outcomes</p>
              <p className="beta-stat-value" style={{ color: "#4ade80" }}>{summary.with_outcomes}</p>
            </div>
            <div className="beta-stat-card">
              <p className="beta-stat-label">Awaiting</p>
              <p className="beta-stat-value" style={{ color: "#facc15" }}>{summary.total_scans - summary.with_outcomes}</p>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="beta-filters">
          <select value={filterDoctor} onChange={(e) => setFilterDoctor(e.target.value)} className="beta-select">
            <option value="all">All Doctors</option>
            {doctors.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
          <select value={filterEye} onChange={(e) => setFilterEye(e.target.value)} className="beta-select">
            <option value="all">All Eyes</option>
            <option value="OD">OD (Right)</option>
            <option value="OS">OS (Left)</option>
          </select>
          <select value={filterLens} onChange={(e) => setFilterLens(e.target.value)} className="beta-select">
            <option value="all">All Lens Sizes</option>
            {lensOptions.map(l => <option key={l} value={l!}>{l}mm</option>)}
          </select>
          <span className="beta-count">{sorted.length} scan{sorted.length !== 1 ? "s" : ""}</span>
        </div>

        {/* Tabs */}
        <div className="beta-tabs">
          <button className={`beta-tab ${tab === "scans" ? "active" : ""}`} onClick={() => setTab("scans")}>Scans & Predictions</button>
          <button className={`beta-tab ${tab === "features" ? "active" : ""}`} onClick={() => setTab("features")}>Biometric Features</button>
          <button className={`beta-tab ${tab === "probabilities" ? "active" : ""}`} onClick={() => setTab("probabilities")}>Lens Probabilities</button>
        </div>

        {/* Scans Table */}
        {tab === "scans" && (
          <div className="beta-table-wrap">
            <table className="beta-table">
              <thead>
                <tr>
                  <SortHeader label="Date" field="scan_date" />
                  <SortHeader label="Doctor" field="doctor" />
                  <SortHeader label="Patient" field="patient_id" />
                  <SortHeader label="Eye" field="eye" />
                  <SortHeader label="Pred Size" field="predicted_lens_size" />
                  <SortHeader label="Pred Vault" field="predicted_vault" />
                  <SortHeader label="Range" field="vault_range_low" />
                  <SortHeader label="Actual Size" field="actual_lens_size" />
                  <SortHeader label="Vault 1d" field="vault_1day" />
                  <SortHeader label="Vault 1wk" field="vault_1week" />
                  <SortHeader label="Vault 1mo" field="vault_1month" />
                  <SortHeader label="Model" field="model_version" />
                  <th className="beta-th">Details</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((s) => (
                  <>
                    <tr key={s.scan_id} className="beta-tr">
                      <td className="beta-td">{s.scan_date}</td>
                      <td className="beta-td">{s.doctor}</td>
                      <td className="beta-td">{s.patient_id}</td>
                      <td className="beta-td">
                        <span className={`eye-pill ${s.eye === "OD" ? "od" : "os"}`}>{s.eye}</span>
                      </td>
                      <td className="beta-td">{s.predicted_lens_size ? `${s.predicted_lens_size}mm` : "—"}</td>
                      <td className="beta-td">{s.predicted_vault ? `${s.predicted_vault}µm` : "—"}</td>
                      <td className="beta-td dim">{s.vault_range_low && s.vault_range_high ? `${s.vault_range_low}–${s.vault_range_high}` : "—"}</td>
                      <td className="beta-td">{s.actual_lens_size ? <span className="actual">{s.actual_lens_size}mm</span> : <span className="dim">—</span>}</td>
                      <td className="beta-td">{s.vault_1day != null ? <span className="actual">{s.vault_1day}µm</span> : <span className="dim">—</span>}</td>
                      <td className="beta-td">{s.vault_1week != null ? <span className="actual">{s.vault_1week}µm</span> : <span className="dim">—</span>}</td>
                      <td className="beta-td">{s.vault_1month != null ? <span className="actual">{s.vault_1month}µm</span> : <span className="dim">—</span>}</td>
                      <td className="beta-td">
                        <span style={{ fontSize: "11px", color: "#6b7280", fontFamily: "monospace" }}>{s.model_version || "—"}</span>
                      </td>
                      <td className="beta-td">
                        <button className="expand-btn" onClick={() => setExpandedRow(expandedRow === s.scan_id ? null : s.scan_id)}>
                          {expandedRow === s.scan_id ? "▾" : "▸"}
                        </button>
                      </td>
                    </tr>
                    {expandedRow === s.scan_id && (
                      <tr key={`${s.scan_id}-detail`} className="beta-detail-row">
                        <td colSpan={13} className="beta-detail-td">
                          <div className="detail-grid">
                            <div><span className="detail-label">Age</span><span className="detail-value">{fmt(s.age, 0)}</span></div>
                            <div><span className="detail-label">WTW</span><span className="detail-value">{fmt(s.wtw)}mm</span></div>
                            <div><span className="detail-label">ACD</span><span className="detail-value">{fmt(s.acd_internal, 2)}mm</span></div>
                            <div><span className="detail-label">ACV</span><span className="detail-value">{fmt(s.acv)}mm³</span></div>
                            <div><span className="detail-label">Shape Ratio</span><span className="detail-value">{fmt(s.ac_shape_ratio)}</span></div>
                            <div><span className="detail-label">SimK Steep</span><span className="detail-value">{fmt(s.simk_steep)}D</span></div>
                            <div><span className="detail-label">TCRP Km</span><span className="detail-value">{fmt(s.tcrp_km)}D</span></div>
                            <div><span className="detail-label">Astigmatism</span><span className="detail-value">{fmt(s.tcrp_astigmatism, 2)}D</span></div>
                            <div><span className="detail-label">ICL Power</span><span className="detail-value">{fmt(s.icl_power)}D</span></div>
                            <div><span className="detail-label">CCT</span><span className="detail-value">{fmt(s.cct, 0)}µm</span></div>
                            <div><span className="detail-label">Vault 1 Day</span><span className="detail-value">{s.vault_1day != null ? `${s.vault_1day}µm` : "—"}</span></div>
                            <div><span className="detail-label">Vault 1 Week</span><span className="detail-value">{s.vault_1week != null ? `${s.vault_1week}µm` : "—"}</span></div>
                            <div><span className="detail-label">Vault 1 Month</span><span className="detail-value">{s.vault_1month != null ? `${s.vault_1month}µm` : "—"}</span></div>
                            <div><span className="detail-label">P(12.1)</span><span className="detail-value">{pct(s.prob_12_1)}</span></div>
                            <div><span className="detail-label">P(12.6)</span><span className="detail-value">{pct(s.prob_12_6)}</span></div>
                            <div><span className="detail-label">P(13.2)</span><span className="detail-value">{pct(s.prob_13_2)}</span></div>
                            <div><span className="detail-label">P(13.7)</span><span className="detail-value">{pct(s.prob_13_7)}</span></div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Features Table */}
        {tab === "features" && (
          <div className="beta-table-wrap">
            <table className="beta-table">
              <thead>
                <tr>
                  <SortHeader label="Patient" field="patient_id" />
                  <SortHeader label="Eye" field="eye" />
                  <SortHeader label="Age" field="age" />
                  <SortHeader label="WTW" field="wtw" />
                  <SortHeader label="ACD" field="acd_internal" />
                  <SortHeader label="ACV" field="acv" />
                  <SortHeader label="Shape" field="ac_shape_ratio" />
                  <SortHeader label="SimK" field="simk_steep" />
                  <SortHeader label="TCRP" field="tcrp_km" />
                  <SortHeader label="Astig" field="tcrp_astigmatism" />
                  <SortHeader label="ICL Pw" field="icl_power" />
                  <SortHeader label="CCT" field="cct" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((s) => (
                  <tr key={s.scan_id} className="beta-tr">
                    <td className="beta-td">{s.patient_id}</td>
                    <td className="beta-td"><span className={`eye-pill ${s.eye === "OD" ? "od" : "os"}`}>{s.eye}</span></td>
                    <td className="beta-td">{fmt(s.age, 0)}</td>
                    <td className="beta-td">{fmt(s.wtw)}</td>
                    <td className="beta-td">{fmt(s.acd_internal, 2)}</td>
                    <td className="beta-td">{fmt(s.acv)}</td>
                    <td className="beta-td">{fmt(s.ac_shape_ratio)}</td>
                    <td className="beta-td">{fmt(s.simk_steep)}</td>
                    <td className="beta-td">{fmt(s.tcrp_km)}</td>
                    <td className="beta-td">{fmt(s.tcrp_astigmatism, 2)}</td>
                    <td className="beta-td">{fmt(s.icl_power)}</td>
                    <td className="beta-td">{fmt(s.cct, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Probabilities Table */}
        {tab === "probabilities" && (
          <div className="beta-table-wrap">
            <table className="beta-table">
              <thead>
                <tr>
                  <SortHeader label="Doctor" field="doctor" />
                  <SortHeader label="Patient" field="patient_id" />
                  <SortHeader label="Eye" field="eye" />
                  <SortHeader label="12.1mm" field="prob_12_1" />
                  <SortHeader label="12.6mm" field="prob_12_6" />
                  <SortHeader label="13.2mm" field="prob_13_2" />
                  <SortHeader label="13.7mm" field="prob_13_7" />
                  <SortHeader label="→ Predicted" field="predicted_lens_size" />
                  <SortHeader label="Vault" field="predicted_vault" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((s) => (
                  <tr key={s.scan_id} className="beta-tr">
                    <td className="beta-td">{s.doctor}</td>
                    <td className="beta-td">{s.patient_id}</td>
                    <td className="beta-td"><span className={`eye-pill ${s.eye === "OD" ? "od" : "os"}`}>{s.eye}</span></td>
                    <td className="beta-td">{pct(s.prob_12_1)}</td>
                    <td className="beta-td">{pct(s.prob_12_6)}</td>
                    <td className="beta-td">{pct(s.prob_13_2)}</td>
                    <td className="beta-td">{pct(s.prob_13_7)}</td>
                    <td className="beta-td" style={{ fontWeight: "600" }}>{s.predicted_lens_size ? `${s.predicted_lens_size}mm` : "—"}</td>
                    <td className="beta-td">{s.predicted_vault ? `${s.predicted_vault}µm` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
