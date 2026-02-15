"use client";

import React, { useState, useEffect, useMemo } from "react";
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
  ini_filename: string | null;
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

type SortKey = keyof Scan;
type SortDir = "asc" | "desc";

const ADMIN_KEY = "vaultbeta2026";
const SIZES = [12.1, 12.6, 13.2, 13.7];

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
  };
  return {
    bg: "rgba(59, 130, 246, 0.12)",
    border: "rgba(59, 130, 246, 0.5)",
    topBorder: "#3b82f6",
    shadow: "0 0 20px rgba(59, 130, 246, 0.15), 0 0 40px rgba(59, 130, 246, 0.05)",
    badgeBg: "rgba(59, 130, 246, 0.25)",
    badgeBorder: "rgba(59, 130, 246, 0.5)",
    badgeText: "#60a5fa",
  };
};

const sortModels = (entries: [string, ModelPrediction][]) => {
  const main: [string, ModelPrediction][] = [];
  const legacy: [string, ModelPrediction][] = [];

  // Sort all entries: featured first, then alpha, separate legacy
  const sorted = [...entries].sort(([a], [b]) => {
    const aIdx = FEATURED_ORDER.indexOf(a);
    const bIdx = FEATURED_ORDER.indexOf(b);
    if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
    if (aIdx !== -1) return -1;
    if (bIdx !== -1) return 1;
    return a.localeCompare(b);
  });

  for (const entry of sorted) {
    if (LEGACY_MODELS.has(entry[0])) legacy.push(entry);
    else main.push(entry);
  }
  return { main, legacy };
};

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
  const [tab, setTab] = useState<"scans" | "features" | "probabilities" | "comparison">("scans");
  const [expandedCompareRows, setExpandedCompareRows] = useState<Set<string>>(new Set());
  const [comparisonCache, setComparisonCache] = useState<Record<string, Record<string, ModelPrediction>>>({});
  const [comparisonLoading, setComparisonLoading] = useState<Set<string>>(new Set());
  const [deleteConfirmScan, setDeleteConfirmScan] = useState<Scan | null>(null);
  const [deletingScanId, setDeletingScanId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [legacyOpen, setLegacyOpen] = useState<Set<string>>(new Set());

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  const fetchData = async () => {
    try {
      setError(null);
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

  useEffect(() => {
    fetchData();
  }, [apiBase]);

  const handleDeleteScan = async (s: Scan) => {
    setDeletingScanId(s.scan_id);
    try {
      const res = await fetch(`${apiBase}/beta/admin/scan/${s.scan_id}?key=${ADMIN_KEY}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Delete failed");
      }
      setDeleteConfirmScan(null);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete scan");
    } finally {
      setDeletingScanId(null);
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllScans = () => {
    if (tab !== "scans") return;
    const visibleIds = sorted.map((s) => s.scan_id);
    if (selectedIds.size === visibleIds.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(visibleIds));
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    setBulkDeleting(true);
    const ids = Array.from(selectedIds);
    let hadError = false;
    for (const id of ids) {
      try {
        const res = await fetch(`${apiBase}/beta/admin/scan/${id}?key=${ADMIN_KEY}`, { method: "DELETE" });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          setError(err?.detail || "Delete failed");
          hadError = true;
          break;
        }
        setSelectedIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete scan");
        hadError = true;
        break;
      }
    }
    if (!hadError) {
      setBulkDeleteConfirm(false);
      await fetchData();
    }
    setBulkDeleting(false);
  };

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
  const fmtDate = (d: string) => {
    if (!d) return "—";
    const dt = new Date(d);
    if (isNaN(dt.getTime())) return d;
    return dt.toLocaleString("en-US", { 
      month: "short", 
      day: "numeric", 
      year: "numeric", 
      hour: "numeric", 
      minute: "2-digit",
      timeZone: "America/New_York"
    });
  };

  const REQUIRED_FEATURES = ["age", "wtw", "acd_internal", "icl_power", "ac_shape_ratio", "simk_steep", "acv", "tcrp_km", "tcrp_astigmatism"] as const;

  const scanHasRequiredFeatures = (s: Scan) =>
    s.age != null && s.wtw != null && s.acd_internal != null && s.icl_power != null &&
    s.ac_shape_ratio != null && s.simk_steep != null && s.acv != null &&
    s.tcrp_km != null && s.tcrp_astigmatism != null;

  const fetchComparison = async (s: Scan) => {
    if (comparisonCache[s.scan_id]) return;
    setComparisonLoading((prev) => new Set(prev).add(s.scan_id));
    try {
      const body = {
        Age: Math.round(Number(s.age)),
        WTW: Number(s.wtw),
        ACD_internal: Number(s.acd_internal),
        ICL_Power: Number(s.icl_power),
        AC_shape_ratio: Number(s.ac_shape_ratio),
        SimK_steep: Number(s.simk_steep),
        ACV: Number(s.acv),
        TCRP_Km: Number(s.tcrp_km),
        TCRP_Astigmatism: Number(s.tcrp_astigmatism),
      };
      const res = await fetch(`${apiBase}/predict-compare?models=all`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Comparison failed");
      const data = await res.json();
      setComparisonCache((prev) => ({ ...prev, [s.scan_id]: data.predictions || {} }));
    } catch {
      setComparisonCache((prev) => ({ ...prev, [s.scan_id]: {} }));
    } finally {
      setComparisonLoading((prev) => { const next = new Set(prev); next.delete(s.scan_id); return next; });
    }
  };

  const handleCompareExpand = (s: Scan) => {
    setExpandedCompareRows((prev) => {
      const next = new Set(prev);
      if (next.has(s.scan_id)) {
        next.delete(s.scan_id);
      } else {
        next.add(s.scan_id);
        if (!comparisonCache[s.scan_id] && scanHasRequiredFeatures(s)) {
          fetchComparison(s);
        }
      }
      return next;
    });
  };

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
        <span style={{ color: "#6b7280", fontSize: "14px" }}>Beta Data Dashboard</span>
      </header>

      <div className="beta-container">
        {error && <p style={{ color: "#f87171", marginBottom: "16px" }}>{error}</p>}

        {/* Delete confirmation dialog */}
        {deleteConfirmScan && (
          <div className="beta-delete-overlay" onClick={() => !deletingScanId && setDeleteConfirmScan(null)}>
            <div className="beta-delete-modal" onClick={(e) => e.stopPropagation()}>
              <h3 className="beta-delete-title">Delete scan?</h3>
              <p className="beta-delete-text">
                This will permanently delete the scan, prediction, and any outcome data for{" "}
                <strong>{deleteConfirmScan.patient_id}</strong>
                {deleteConfirmScan.ini_filename && (
                  <> — <span style={{ fontFamily: "monospace", fontSize: "12px" }}>{deleteConfirmScan.ini_filename}</span></>
                )}
                . This cannot be undone.
              </p>
              <div className="beta-delete-actions">
                <button
                  type="button"
                  className="beta-delete-cancel"
                  onClick={() => setDeleteConfirmScan(null)}
                  disabled={!!deletingScanId}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="beta-delete-confirm"
                  onClick={() => handleDeleteScan(deleteConfirmScan)}
                  disabled={!!deletingScanId}
                >
                  {deletingScanId === deleteConfirmScan.scan_id ? "Deleting…" : "Delete"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Bulk delete confirmation */}
        {bulkDeleteConfirm && (
          <div className="beta-delete-overlay" onClick={() => !bulkDeleting && setBulkDeleteConfirm(false)}>
            <div className="beta-delete-modal" onClick={(e) => e.stopPropagation()}>
              <h3 className="beta-delete-title">Delete {selectedIds.size} scan{selectedIds.size !== 1 ? "s" : ""}?</h3>
              <p className="beta-delete-text">
                This will permanently delete the selected scan(s) and cannot be undone.
              </p>
              <div className="beta-delete-actions">
                <button type="button" className="beta-delete-cancel" onClick={() => setBulkDeleteConfirm(false)} disabled={!!bulkDeleting}>
                  Cancel
                </button>
                <button type="button" className="beta-delete-confirm" onClick={handleBulkDelete} disabled={!!bulkDeleting}>
                  {bulkDeleting ? "Deleting…" : "Delete"}
                </button>
              </div>
            </div>
          </div>
        )}

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
          <button className={`beta-tab ${tab === "comparison" ? "active" : ""}`} onClick={() => setTab("comparison")}>Model Comparison</button>
        </div>

        {/* Bulk actions bar (Scans tab) */}
        {tab === "scans" && selectedIds.size > 0 && (
          <div className="beta-filters" style={{ marginBottom: "12px" }}>
            <span className="beta-count">{selectedIds.size} selected</span>
            <button type="button" className="beta-delete-btn" onClick={() => setBulkDeleteConfirm(true)} disabled={!!deletingScanId || !!bulkDeleting}>
              Delete selected
            </button>
            <button
              type="button"
              style={{ padding: "6px 12px", fontSize: "12px", color: "#9ca3af", background: "transparent", border: "1px solid #4b5563", borderRadius: "6px", cursor: "pointer" }}
              onClick={() => setSelectedIds(new Set())}
            >
              Clear selection
            </button>
          </div>
        )}

        {/* Scans Table */}
        {tab === "scans" && (
          <div className="beta-table-wrap">
            <table className="beta-table">
              <thead>
                <tr>
                  <SortHeader label="Date" field="scan_date" />
                  <SortHeader label="Doctor" field="doctor" />
                  <SortHeader label="Patient" field="patient_id" />
                  <SortHeader label="INI File" field="ini_filename" />
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
                  <th className="beta-th beta-select-col" style={{ width: "44px", textAlign: "center" }}>
                    <input
                      type="checkbox"
                      checked={sorted.length > 0 && selectedIds.size === sorted.length}
                      ref={(el) => { if (el) el.indeterminate = selectedIds.size > 0 && selectedIds.size < sorted.length; }}
                      onChange={selectAllScans}
                      title="Select all"
                      style={{ cursor: "pointer", width: "18px", height: "18px" }}
                    />
                  </th>
                  <th className="beta-th beta-actions-col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((s) => (
                  <>
                    <tr key={s.scan_id} className="beta-tr">
                      <td className="beta-td">{fmtDate(s.scan_date)}</td>
                      <td className="beta-td">{s.doctor}</td>
                      <td className="beta-td">{s.patient_id}</td>
                      <td className="beta-td"><span style={{ fontSize: "11px", color: "#6b7280", fontFamily: "monospace" }}>{s.ini_filename || "—"}</span></td>
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
                      <td className="beta-td beta-select-col" style={{ textAlign: "center" }} onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(s.scan_id)}
                          onChange={() => toggleSelect(s.scan_id)}
                          style={{ cursor: "pointer", width: "18px", height: "18px" }}
                        />
                      </td>
                      <td className="beta-td beta-actions-col">
                        <button
                          type="button"
                          className="beta-delete-btn"
                          onClick={() => setDeleteConfirmScan(s)}
                          title="Delete scan"
                          disabled={!!deletingScanId}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                    {expandedRow === s.scan_id && (
                      <tr key={`${s.scan_id}-detail`} className="beta-detail-row">
                        <td colSpan={16} className="beta-detail-td">
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
                  <SortHeader label="INI File" field="ini_filename" />
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
                    <td className="beta-td"><span style={{ fontSize: "11px", color: "#6b7280", fontFamily: "monospace" }}>{s.ini_filename || "—"}</span></td>
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
                  <SortHeader label="INI File" field="ini_filename" />
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
                    <td className="beta-td"><span style={{ fontSize: "11px", color: "#6b7280", fontFamily: "monospace" }}>{s.ini_filename || "—"}</span></td>
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

        {/* Model Comparison Tab */}
        {tab === "comparison" && (
          <div className="beta-table-wrap">
            <table className="beta-table">
              <thead>
                <tr>
                  <SortHeader label="Date" field="scan_date" />
                  <SortHeader label="Doctor" field="doctor" />
                  <SortHeader label="Patient" field="patient_id" />
                  <SortHeader label="INI File" field="ini_filename" />
                  <SortHeader label="Eye" field="eye" />
                  <SortHeader label="Pred Size" field="predicted_lens_size" />
                  <SortHeader label="Model" field="model_version" />
                  <th className="beta-th">Compare</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((s) => {
                  const isExpanded = expandedCompareRows.has(s.scan_id);
                  const hasFeatures = scanHasRequiredFeatures(s);
                  const predictions = comparisonCache[s.scan_id];
                  const isLoading = comparisonLoading.has(s.scan_id);

                  return (
                    <React.Fragment key={s.scan_id}>
                      <tr className="beta-tr">
                        <td className="beta-td">{fmtDate(s.scan_date)}</td>
                        <td className="beta-td">{s.doctor}</td>
                        <td className="beta-td">{s.patient_id}</td>
                        <td className="beta-td"><span style={{ fontSize: "11px", color: "#6b7280", fontFamily: "monospace" }}>{s.ini_filename || "—"}</span></td>
                        <td className="beta-td">
                          <span className={`eye-pill ${s.eye === "OD" ? "od" : "os"}`}>{s.eye}</span>
                        </td>
                        <td className="beta-td">{s.predicted_lens_size ? `${s.predicted_lens_size}mm` : "—"}</td>
                        <td className="beta-td">
                          <span style={{ fontSize: "11px", color: "#6b7280", fontFamily: "monospace" }}>{s.model_version || "—"}</span>
                        </td>
                        <td className="beta-td">
                          {hasFeatures ? (
                            <button className="expand-btn" onClick={() => handleCompareExpand(s)}>
                              {isExpanded ? "▾" : "▸"}
                            </button>
                          ) : (
                            <span style={{ fontSize: "11px", color: "#6b7280" }}>Missing data</span>
                          )}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="beta-detail-row">
                          <td colSpan={8} className="beta-detail-td">
                            {isLoading && (
                              <div style={{ textAlign: "center", padding: "24px", color: "#9ca3af" }}>
                                Running predictions across all models...
                              </div>
                            )}
                            {!isLoading && predictions && Object.keys(predictions).length === 0 && (
                              <div style={{ textAlign: "center", padding: "24px", color: "#f87171" }}>
                                Comparison failed — no model results returned.
                              </div>
                            )}
                            {!isLoading && predictions && Object.keys(predictions).length > 0 && (() => {
                              const { main: mainModels, legacy: legacyModels } = sortModels(Object.entries(predictions));
                              const scanLegacyOpen = legacyOpen.has(s.scan_id);
                              return (
                                <>
                                  {/* Main models grid */}
                                  <div style={{
                                    display: "grid",
                                    gridTemplateColumns: mainModels.length === 1 ? "1fr" : `repeat(${Math.min(mainModels.length, 3)}, 1fr)`,
                                    gap: "20px",
                                    padding: "20px",
                                    maxWidth: "1400px",
                                    margin: "0 auto",
                                  }}>
                                    {mainModels.map(([tag, pred]) => {
                                      const featured = FEATURED_MODELS[tag];
                                      const fStyle = featured ? getFeaturedStyle(featured.color) : null;

                                      if (pred.error) {
                                        return (
                                          <div key={tag} style={{
                                            background: fStyle ? fStyle.bg : "#1a1a1a",
                                            borderRadius: "12px", padding: "24px",
                                            border: fStyle ? `1px solid ${fStyle.border}` : "1px solid #374151",
                                            borderTop: fStyle ? `3px solid ${fStyle.topBorder}` : undefined,
                                            boxShadow: fStyle ? fStyle.shadow : undefined,
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
                                          background: fStyle ? fStyle.bg : "#1a1a1a",
                                          borderRadius: "12px", padding: "24px",
                                          border: fStyle ? `1px solid ${fStyle.border}` : "1px solid #374151",
                                          borderTop: fStyle ? `3px solid ${fStyle.topBorder}` : undefined,
                                          boxShadow: fStyle ? fStyle.shadow : undefined,
                                        }}>
                                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "8px" }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                                              <h3 style={{ color: "#fff", fontSize: "16px", fontWeight: 600, margin: 0 }}>{tag}</h3>
                                              {featured && fStyle && (
                                                <span style={{
                                                  padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700,
                                                  background: fStyle.badgeBg, color: fStyle.badgeText,
                                                  border: `1px solid ${fStyle.badgeBorder}`,
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
                                                  <div style={{ fontSize: "24px", fontWeight: 400, color: isBest ? "#4ade80" : isSecond ? "#facc15" : "#fff" }}>{size}</div>
                                                  <div style={{ fontSize: "13px", color: isBest ? "#4ade80" : isSecond ? "#facc15" : "#6b7280" }}>{(prob * 100).toFixed(0)}%</div>
                                                </div>
                                              );
                                            })}
                                          </div>
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
                                              <div style={{ marginTop: "6px", fontSize: "12px", fontWeight: 500, color: pred.vault_flag === "low" ? "#f87171" : "#facc15" }}>
                                                ⚠ {pred.vault_flag === "low" ? "Low vault risk" : "High vault risk"}
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>

                                  {/* Legacy models — collapsible */}
                                  {legacyModels.length > 0 && (
                                    <div style={{ marginTop: "32px", padding: "0 20px", maxWidth: "1400px", margin: "16px auto 0" }}>
                                      <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "16px" }}>
                                        <div style={{ flex: 1, height: "1px", background: "#2a2a2a" }} />
                                        <button
                                          onClick={() => setLegacyOpen((prev) => {
                                            const next = new Set(prev);
                                            if (next.has(s.scan_id)) next.delete(s.scan_id);
                                            else next.add(s.scan_id);
                                            return next;
                                          })}
                                          style={{
                                            background: "#1a1a1a", border: "1px solid #374151",
                                            borderRadius: "20px", cursor: "pointer", color: "#9ca3af",
                                            fontSize: "13px", fontWeight: 500, padding: "8px 20px",
                                            display: "flex", alignItems: "center", gap: "8px",
                                            whiteSpace: "nowrap",
                                          }}
                                        >
                                          <span style={{
                                            display: "inline-block", transition: "transform 0.2s",
                                            transform: scanLegacyOpen ? "rotate(90deg)" : "rotate(0deg)",
                                            fontSize: "10px",
                                          }}>▶</span>
                                          Legacy Models
                                          <span style={{
                                            background: "#374151", color: "#9ca3af", fontSize: "11px",
                                            fontWeight: 600, padding: "1px 7px", borderRadius: "10px",
                                          }}>{legacyModels.length}</span>
                                        </button>
                                        <div style={{ flex: 1, height: "1px", background: "#2a2a2a" }} />
                                      </div>
                                      {scanLegacyOpen && (
                                        <div style={{
                                          display: "grid",
                                          gridTemplateColumns: legacyModels.length === 1 ? "1fr" : `repeat(${Math.min(legacyModels.length, 3)}, 1fr)`,
                                          gap: "20px",
                                        }}>
                                          {legacyModels.map(([tag, pred]) => {
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
                                                border: "1px solid #262626", borderTop: "2px solid #374151",
                                              }}>
                                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "8px" }}>
                                                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                                    <h3 style={{ color: "#d1d5db", fontSize: "16px", fontWeight: 600, margin: 0 }}>{tag}</h3>
                                                    <span style={{
                                                      padding: "3px 10px", borderRadius: "10px", fontSize: "10px", fontWeight: 600,
                                                      background: "rgba(107, 114, 128, 0.2)", color: "#9ca3af",
                                                      textTransform: "uppercase" as const, letterSpacing: "0.05em",
                                                    }}>Legacy</span>
                                                  </div>
                                                  <span style={{
                                                    padding: "3px 8px", borderRadius: "4px", fontSize: "11px",
                                                    background: "rgba(139, 92, 246, 0.1)", color: "#8b7fc7",
                                                  }}>{pred.feature_count} features</span>
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
                                </>
                              );
                            })()}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
