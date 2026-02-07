"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import dynamic from "next/dynamic";

const UserMenu = dynamic(() => import("@/components/UserMenu"), { ssr: false });

type Scan = {
  id: string;
  patient_anonymous_id: string;
  eye: string;
  predicted_lens_size: string | null;
  predicted_vault: number | null;
  actual_lens_size: string | null;
  vault_1day: number | null;
  vault_1week: number | null;
  vault_1month: number | null;
  created_at: string;
};

type Stats = {
  total_patients: number;
  total_scans: number;
  scans_with_outcomes: number;
};

export default function DashboardPage() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedScan, setSelectedScan] = useState<Scan | null>(null);
  const [outcomeForm, setOutcomeForm] = useState({
    actual_lens_size: "",
    vault_1day: "",
    vault_1week: "",
    vault_1month: "",
    surgery_date: "",
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const router = useRouter();

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  useEffect(() => {
    const checkAuthAndFetch = async () => {
      const { createClient } = await import("@/lib/supabase");
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        router.push("/login");
        return;
      }

      try {
        // Fetch scans
        const scansRes = await fetch(`${apiBase}/beta/scans`, {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        if (scansRes.ok) {
          const scansData = await scansRes.json();
          setScans(scansData);
        }

        // Fetch stats
        const statsRes = await fetch(`${apiBase}/beta/stats`, {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setStats(statsData);
        }
      } catch (err) {
        setError("Failed to load data");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    checkAuthAndFetch();
  }, [router, apiBase]);

  const openOutcomeModal = (scan: Scan) => {
    setSelectedScan(scan);
    setOutcomeForm({
      actual_lens_size: scan.actual_lens_size || "",
      vault_1day: scan.vault_1day != null ? String(scan.vault_1day) : "",
      vault_1week: scan.vault_1week != null ? String(scan.vault_1week) : "",
      vault_1month: scan.vault_1month != null ? String(scan.vault_1month) : "",
      surgery_date: "",
      notes: "",
    });
    setSubmitError(null);
  };

  const handleSubmitOutcome = async () => {
    if (!selectedScan) return;
    if (!outcomeForm.vault_1day) {
      setSubmitError("Vault at 1 day is required");
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    try {
      const { createClient } = await import("@/lib/supabase");
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        router.push("/login");
        return;
      }

      const body: Record<string, unknown> = {
        vault_1day: parseFloat(outcomeForm.vault_1day),
      };
      if (outcomeForm.actual_lens_size) body.actual_lens_size = outcomeForm.actual_lens_size;
      if (outcomeForm.vault_1week) body.vault_1week = parseFloat(outcomeForm.vault_1week);
      if (outcomeForm.vault_1month) body.vault_1month = parseFloat(outcomeForm.vault_1month);
      if (outcomeForm.surgery_date) body.surgery_date = outcomeForm.surgery_date;
      if (outcomeForm.notes) body.notes = outcomeForm.notes;

      const res = await fetch(`${apiBase}/beta/scans/${selectedScan.id}/outcome`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || "Failed to submit outcome");
      }

      const updated = await res.json();
      setScans((prev) =>
        prev.map((s) => (s.id === selectedScan.id ? { ...s, ...updated } : s))
      );
      setSelectedScan(null);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to submit outcome");
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  if (loading) {
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
      {/* Header */}
      <header className="calc-header" style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <Link href="/">
          <Image
            src="/images/vault-dark-mode.svg"
            alt="Vault 3"
            width={200}
            height={65}
            priority
            className="vault-logo-link"
          />
        </Link>
        <UserMenu />
      </header>

      <div style={{ padding: "20px 40px", maxWidth: "1200px", margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "32px" }}>
          <h1 style={{ fontSize: "28px", fontWeight: "600", color: "#ffffff", margin: 0 }}>
            My Scans
          </h1>
          <Link href="/calculator" className="calc-btn-primary" style={{ width: "auto", marginTop: 0, padding: "12px 24px" }}>
            + New Scan
          </Link>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "20px", marginBottom: "32px" }}>
            <div style={{ background: "#1a1a1a", borderRadius: "12px", padding: "24px" }}>
              <p style={{ color: "#9ca3af", fontSize: "14px", margin: "0 0 8px" }}>Total Patients</p>
              <p style={{ color: "#ffffff", fontSize: "32px", fontWeight: "600", margin: 0 }}>{stats.total_patients}</p>
            </div>
            <div style={{ background: "#1a1a1a", borderRadius: "12px", padding: "24px" }}>
              <p style={{ color: "#9ca3af", fontSize: "14px", margin: "0 0 8px" }}>Total Scans</p>
              <p style={{ color: "#ffffff", fontSize: "32px", fontWeight: "600", margin: 0 }}>{stats.total_scans}</p>
            </div>
            <div style={{ background: "#1a1a1a", borderRadius: "12px", padding: "24px" }}>
              <p style={{ color: "#9ca3af", fontSize: "14px", margin: "0 0 8px" }}>With Outcomes</p>
              <p style={{ color: "#4ade80", fontSize: "32px", fontWeight: "600", margin: 0 }}>{stats.scans_with_outcomes}</p>
            </div>
          </div>
        )}

        {error && (
          <p style={{ color: "#f87171", marginBottom: "16px" }}>{error}</p>
        )}

        {/* Scans Table */}
        {scans.length === 0 ? (
          <div style={{ background: "#1a1a1a", borderRadius: "12px", padding: "48px", textAlign: "center" }}>
            <p style={{ color: "#9ca3af", fontSize: "16px", margin: "0 0 16px" }}>
              No scans yet. Upload your first INI file to get started.
            </p>
            <Link href="/calculator" className="calc-btn-primary" style={{ width: "auto", display: "inline-block", marginTop: 0 }}>
              Upload INI File
            </Link>
          </div>
        ) : (
          <div style={{ background: "#1a1a1a", borderRadius: "12px", overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #374151" }}>
                  <th style={{ padding: "16px", textAlign: "left", color: "#9ca3af", fontWeight: "500", fontSize: "14px" }}>Patient</th>
                  <th style={{ padding: "16px", textAlign: "left", color: "#9ca3af", fontWeight: "500", fontSize: "14px" }}>Eye</th>
                  <th style={{ padding: "16px", textAlign: "left", color: "#9ca3af", fontWeight: "500", fontSize: "14px" }}>Predicted Size</th>
                  <th style={{ padding: "16px", textAlign: "left", color: "#9ca3af", fontWeight: "500", fontSize: "14px" }}>Predicted Vault</th>
                  <th style={{ padding: "16px", textAlign: "left", color: "#9ca3af", fontWeight: "500", fontSize: "14px" }}>Actual</th>
                  <th style={{ padding: "16px", textAlign: "left", color: "#9ca3af", fontWeight: "500", fontSize: "14px" }}>Date</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((scan) => (
                  <tr
                    key={scan.id}
                    onClick={() => openOutcomeModal(scan)}
                    style={{ borderBottom: "1px solid #262626", cursor: "pointer", transition: "background 0.15s" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "#262626")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <td style={{ padding: "16px", color: "#ffffff" }}>{scan.patient_anonymous_id}</td>
                    <td style={{ padding: "16px" }}>
                      <span style={{
                        padding: "4px 12px",
                        borderRadius: "4px",
                        fontSize: "13px",
                        fontWeight: "500",
                        background: scan.eye === "OD" ? "rgba(59, 130, 246, 0.2)" : "rgba(168, 85, 247, 0.2)",
                        color: scan.eye === "OD" ? "#60a5fa" : "#c084fc",
                      }}>
                        {scan.eye}
                      </span>
                    </td>
                    <td style={{ padding: "16px", color: "#ffffff" }}>
                      {scan.predicted_lens_size ? `${scan.predicted_lens_size}mm` : "—"}
                    </td>
                    <td style={{ padding: "16px", color: "#ffffff" }}>
                      {scan.predicted_vault ? `${scan.predicted_vault}µm` : "—"}
                    </td>
                    <td style={{ padding: "16px" }}>
                      {scan.actual_lens_size || scan.vault_1day != null ? (
                        <span style={{ color: "#4ade80" }}>
                          {scan.actual_lens_size && `${scan.actual_lens_size}mm`}
                          {scan.actual_lens_size && scan.vault_1day != null && " / "}
                          {scan.vault_1day != null && `${scan.vault_1day}µm`}
                        </span>
                      ) : (
                        <span style={{ color: "#6b7280" }}>Click to record</span>
                      )}
                    </td>
                    <td style={{ padding: "16px", color: "#9ca3af" }}>{formatDate(scan.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Outcome Recording Modal */}
      {selectedScan && (
        <div
          onClick={() => setSelectedScan(null)}
          style={{
            position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
            background: "rgba(0, 0, 0, 0.7)", display: "flex",
            justifyContent: "center", alignItems: "center", zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "#1a1a1a", borderRadius: "16px", padding: "32px",
              width: "100%", maxWidth: "520px", maxHeight: "90vh", overflowY: "auto",
              border: "1px solid #374151",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
              <h2 style={{ color: "#ffffff", fontSize: "20px", fontWeight: "600", margin: 0 }}>Record Outcome</h2>
              <button
                onClick={() => setSelectedScan(null)}
                style={{ background: "none", border: "none", color: "#9ca3af", fontSize: "24px", cursor: "pointer", padding: "4px" }}
              >
                ×
              </button>
            </div>

            {/* Scan Info */}
            <div style={{ background: "#262626", borderRadius: "8px", padding: "16px", marginBottom: "24px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <p style={{ color: "#9ca3af", fontSize: "12px", margin: "0 0 4px" }}>Patient</p>
                  <p style={{ color: "#ffffff", fontSize: "14px", margin: 0 }}>{selectedScan.patient_anonymous_id}</p>
                </div>
                <div>
                  <p style={{ color: "#9ca3af", fontSize: "12px", margin: "0 0 4px" }}>Eye</p>
                  <p style={{ color: "#ffffff", fontSize: "14px", margin: 0 }}>{selectedScan.eye}</p>
                </div>
                <div>
                  <p style={{ color: "#9ca3af", fontSize: "12px", margin: "0 0 4px" }}>Predicted Size</p>
                  <p style={{ color: "#ffffff", fontSize: "14px", margin: 0 }}>{selectedScan.predicted_lens_size ? `${selectedScan.predicted_lens_size}mm` : "—"}</p>
                </div>
                <div>
                  <p style={{ color: "#9ca3af", fontSize: "12px", margin: "0 0 4px" }}>Predicted Vault</p>
                  <p style={{ color: "#ffffff", fontSize: "14px", margin: 0 }}>{selectedScan.predicted_vault ? `${selectedScan.predicted_vault}µm` : "—"}</p>
                </div>
              </div>
            </div>

            {/* Form Fields */}
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div>
                <label style={{ color: "#9ca3af", fontSize: "13px", display: "block", marginBottom: "6px" }}>Lens Size Implanted</label>
                <select
                  value={outcomeForm.actual_lens_size}
                  onChange={(e) => setOutcomeForm({ ...outcomeForm, actual_lens_size: e.target.value })}
                  style={{
                    width: "100%", padding: "10px 12px", background: "#262626", border: "1px solid #374151",
                    borderRadius: "8px", color: "#ffffff", fontSize: "14px", outline: "none",
                  }}
                >
                  <option value="">Select size...</option>
                  <option value="12.1">12.1mm</option>
                  <option value="12.6">12.6mm</option>
                  <option value="13.2">13.2mm</option>
                  <option value="13.7">13.7mm</option>
                </select>
              </div>

              <div>
                <label style={{ color: "#9ca3af", fontSize: "13px", display: "block", marginBottom: "6px" }}>
                  Vault at 1 Day (µm) <span style={{ color: "#f87171" }}>*</span>
                </label>
                <input
                  type="number"
                  value={outcomeForm.vault_1day}
                  onChange={(e) => setOutcomeForm({ ...outcomeForm, vault_1day: e.target.value })}
                  placeholder="e.g. 480"
                  style={{
                    width: "100%", padding: "10px 12px", background: "#262626", border: "1px solid #374151",
                    borderRadius: "8px", color: "#ffffff", fontSize: "14px", outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ color: "#9ca3af", fontSize: "13px", display: "block", marginBottom: "6px" }}>Vault at 1 Week (µm)</label>
                <input
                  type="number"
                  value={outcomeForm.vault_1week}
                  onChange={(e) => setOutcomeForm({ ...outcomeForm, vault_1week: e.target.value })}
                  placeholder="Optional"
                  style={{
                    width: "100%", padding: "10px 12px", background: "#262626", border: "1px solid #374151",
                    borderRadius: "8px", color: "#ffffff", fontSize: "14px", outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ color: "#9ca3af", fontSize: "13px", display: "block", marginBottom: "6px" }}>Vault at 1 Month (µm)</label>
                <input
                  type="number"
                  value={outcomeForm.vault_1month}
                  onChange={(e) => setOutcomeForm({ ...outcomeForm, vault_1month: e.target.value })}
                  placeholder="Optional"
                  style={{
                    width: "100%", padding: "10px 12px", background: "#262626", border: "1px solid #374151",
                    borderRadius: "8px", color: "#ffffff", fontSize: "14px", outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ color: "#9ca3af", fontSize: "13px", display: "block", marginBottom: "6px" }}>Surgery Date</label>
                <input
                  type="date"
                  value={outcomeForm.surgery_date}
                  onChange={(e) => setOutcomeForm({ ...outcomeForm, surgery_date: e.target.value })}
                  style={{
                    width: "100%", padding: "10px 12px", background: "#262626", border: "1px solid #374151",
                    borderRadius: "8px", color: "#ffffff", fontSize: "14px", outline: "none",
                    colorScheme: "dark",
                  }}
                />
              </div>

              <div>
                <label style={{ color: "#9ca3af", fontSize: "13px", display: "block", marginBottom: "6px" }}>Notes</label>
                <textarea
                  value={outcomeForm.notes}
                  onChange={(e) => setOutcomeForm({ ...outcomeForm, notes: e.target.value })}
                  placeholder="Optional notes..."
                  rows={3}
                  style={{
                    width: "100%", padding: "10px 12px", background: "#262626", border: "1px solid #374151",
                    borderRadius: "8px", color: "#ffffff", fontSize: "14px", outline: "none", resize: "vertical",
                  }}
                />
              </div>
            </div>

            {submitError && (
              <p style={{ color: "#f87171", fontSize: "13px", margin: "12px 0 0" }}>{submitError}</p>
            )}

            <div style={{ display: "flex", gap: "12px", marginTop: "24px" }}>
              <button
                onClick={() => setSelectedScan(null)}
                style={{
                  flex: 1, padding: "12px", background: "transparent", border: "1px solid #374151",
                  borderRadius: "8px", color: "#9ca3af", fontSize: "14px", cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitOutcome}
                disabled={submitting}
                className="calc-btn-primary"
                style={{
                  flex: 1, width: "auto", marginTop: 0, padding: "12px",
                  opacity: submitting ? 0.6 : 1, cursor: submitting ? "not-allowed" : "pointer",
                }}
              >
                {submitting ? "Submitting..." : "Save Outcome"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
