"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";

export default function UserMenu() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const initAuth = async () => {
      const { createClient } = await import("@/lib/supabase");
      const supabase = createClient();
      
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user);
      setLoading(false);

      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        (_event, session) => {
          setUser(session?.user ?? null);
        }
      );

      return () => subscription.unsubscribe();
    };
    
    initAuth();
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    const { createClient } = await import("@/lib/supabase");
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  };

  if (loading) {
    return null;
  }

  if (!user) {
    return (
      <button 
        onClick={() => router.push("/login")} 
        className="user-btn"
      >
        Sign In
      </button>
    );
  }

  // Get first initial only from name or email
  const firstName = user.user_metadata?.first_name || "";
  const initials = firstName
    ? firstName[0].toUpperCase()
    : user.email?.[0]?.toUpperCase() || "U";
  
  const displayName = firstName || user.email?.split("@")[0] || "User";

  return (
    <div className="user-menu" ref={dropdownRef}>
      <button 
        className="user-btn" 
        onClick={() => setShowDropdown(!showDropdown)}
      >
        <div className="user-avatar">{initials}</div>
        <span>{displayName}</span>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" style={{ marginLeft: "4px", opacity: 0.6 }}>
          <path d="M2.5 4.5L6 8L9.5 4.5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {showDropdown && (
        <div className="user-dropdown">
          <div className="dropdown-header">
            <div className="dropdown-avatar">{initials}</div>
            <div className="dropdown-user-info">
              <span className="dropdown-name">{firstName || displayName}</span>
              <span className="dropdown-email">{user.email}</span>
            </div>
          </div>
          <div className="dropdown-divider" />
          <button className="dropdown-item" onClick={() => { setShowDropdown(false); router.push("/calculator"); }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="4" y="4" width="16" height="16" rx="2" />
              <path d="M9 9h6M9 13h6M9 17h4" />
            </svg>
            Calculator
          </button>
          <button className="dropdown-item" onClick={() => { setShowDropdown(false); router.push("/dashboard"); }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
            My Scans
          </button>
          <button className="dropdown-item" onClick={() => { setShowDropdown(false); router.push("/profile"); }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            Profile
          </button>
          <div className="dropdown-divider" />
          <button className="dropdown-item danger" onClick={handleSignOut}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
