"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import dynamic from "next/dynamic";

const UserMenu = dynamic(() => import("@/components/UserMenu"), { ssr: false });

type UserProfile = {
  email: string;
  firstName: string;
  lastName: string;
  createdAt: string;
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const loadProfile = async () => {
      const { createClient } = await import("@/lib/supabase");
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        router.push("/login");
        return;
      }

      const user = session.user;
      setProfile({
        email: user.email || "",
        firstName: user.user_metadata?.first_name || "",
        lastName: user.user_metadata?.last_name || "",
        createdAt: user.created_at || "",
      });
      setFirstName(user.user_metadata?.first_name || "");
      setLastName(user.user_metadata?.last_name || "");
      setLoading(false);
    };
    loadProfile();
  }, [router]);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      const { createClient } = await import("@/lib/supabase");
      const supabase = createClient();
      
      const { error } = await supabase.auth.updateUser({
        data: {
          first_name: firstName,
          last_name: lastName,
          full_name: `${firstName} ${lastName}`.trim(),
        },
      });

      if (error) throw error;

      setProfile(prev => prev ? {
        ...prev,
        firstName,
        lastName,
      } : null);
      setEditing(false);
      setMessage("Profile updated successfully!");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "long",
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
        <Link href="/calculator">
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

      <div className="profile-container">
        <div className="profile-card">
          <div className="profile-avatar-large">
            {profile?.firstName?.[0]?.toUpperCase() || profile?.email?.[0]?.toUpperCase() || "U"}
          </div>
          
          <h1 className="profile-name">
            {profile?.firstName && profile?.lastName 
              ? `${profile.firstName} ${profile.lastName}`
              : profile?.email?.split("@")[0]}
          </h1>
          
          <p className="profile-email">{profile?.email}</p>
          
          {profile?.createdAt && (
            <p className="profile-joined">Member since {formatDate(profile.createdAt)}</p>
          )}

          {message && (
            <p className={`profile-message ${message.includes("success") ? "success" : "error"}`}>
              {message}
            </p>
          )}

          {!editing ? (
            <button onClick={() => setEditing(true)} className="profile-edit-btn">
              Edit Profile
            </button>
          ) : (
            <div className="profile-edit-form">
              <div className="form-field">
                <label>First Name</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="First name"
                />
              </div>
              <div className="form-field">
                <label>Last Name</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Last name"
                />
              </div>
              <div className="profile-edit-actions">
                <button onClick={() => setEditing(false)} className="profile-cancel-btn">
                  Cancel
                </button>
                <button onClick={handleSave} className="profile-save-btn" disabled={saving}>
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="profile-stats">
          <Link href="/dashboard" className="profile-stat-card">
            <span className="stat-label">My Scans</span>
            <span className="stat-arrow">→</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
