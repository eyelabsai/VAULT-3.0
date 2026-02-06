"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";

export default function UserMenu() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user);
      setLoading(false);
    };

    getUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setUser(session?.user ?? null);
      }
    );

    return () => subscription.unsubscribe();
  }, [supabase.auth]);

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

  const initials = user.email
    ? user.email.substring(0, 2).toUpperCase()
    : "U";

  return (
    <div className="user-menu" ref={dropdownRef}>
      <button 
        className="user-btn" 
        onClick={() => setShowDropdown(!showDropdown)}
      >
        <div className="user-avatar">{initials}</div>
        <span>{user.email?.split("@")[0]}</span>
      </button>

      {showDropdown && (
        <div className="user-dropdown">
          <button className="dropdown-item" onClick={() => router.push("/dashboard")}>
            My Scans
          </button>
          <button className="dropdown-item danger" onClick={handleSignOut}>
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
