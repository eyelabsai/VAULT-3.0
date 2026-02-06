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
  actual_vault: number | null;
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
                  <tr key={scan.id} style={{ borderBottom: "1px solid #262626" }}>
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
                      {scan.actual_lens_size || scan.actual_vault ? (
                        <span style={{ color: "#4ade80" }}>
                          {scan.actual_lens_size && `${scan.actual_lens_size}mm`}
                          {scan.actual_lens_size && scan.actual_vault && " / "}
                          {scan.actual_vault && `${scan.actual_vault}µm`}
                        </span>
                      ) : (
                        <span style={{ color: "#6b7280" }}>Not recorded</span>
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
    </main>
  );
}
