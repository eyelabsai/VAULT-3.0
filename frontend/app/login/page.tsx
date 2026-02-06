"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "signup" | "forgot">("login");
  const [message, setMessage] = useState<string | null>(null);
  const router = useRouter();
  
  const getSupabase = async () => {
    const { createClient } = await import("@/lib/supabase");
    return createClient();
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const supabase = await getSupabase();
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;
      router.push("/calculator");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate passwords match
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    // Validate password length
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setLoading(true);

    try {
      const supabase = await getSupabase();
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/welcome`,
          data: {
            first_name: firstName,
            last_name: lastName,
            full_name: `${firstName} ${lastName}`.trim(),
          },
        },
      });

      if (error) throw error;
      
      // Redirect to check-email page
      router.push("/check-email");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const supabase = await getSupabase();
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });

      if (error) throw error;
      setMessage("Check your email for a password reset link!");
      setMode("login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send reset email");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-page">
      <div className="login-container">
        <Link href="/">
          <Image
            src="/images/vault-dark-mode.svg"
            alt="Vault 3"
            width={280}
            height={90}
            priority
            className="login-logo"
          />
        </Link>

        <div className="login-card">
          <h1 className="login-title">
            {mode === "login" && "Welcome Back"}
            {mode === "signup" && "Create Account"}
            {mode === "forgot" && "Reset Password"}
          </h1>

          {message && <p className="login-message success">{message}</p>}
          {error && <p className="login-message error">{error}</p>}

          <form
            onSubmit={
              mode === "login"
                ? handleLogin
                : mode === "signup"
                ? handleSignup
                : handleForgotPassword
            }
            className="login-form"
          >
            <div className="form-field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>

            {mode === "signup" && (
              <>
                <div className="form-field">
                  <label htmlFor="firstName">First Name</label>
                  <input
                    id="firstName"
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="John"
                    required
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="lastName">Last Name</label>
                  <input
                    id="lastName"
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="Smith"
                    required
                  />
                </div>
              </>
            )}

            {mode !== "forgot" && (
              <div className="form-field">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={6}
                />
              </div>
            )}

            {mode === "signup" && (
              <div className="form-field">
                <label htmlFor="confirmPassword">Confirm Password</label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={6}
                />
              </div>
            )}

            <button type="submit" className="login-btn" disabled={loading}>
              {loading
                ? "Loading..."
                : mode === "login"
                ? "Sign In"
                : mode === "signup"
                ? "Create Account"
                : "Send Reset Link"}
            </button>
          </form>

          <div className="login-links">
            {mode === "login" && (
              <>
                <button onClick={() => setMode("forgot")} className="link-btn">
                  Forgot password?
                </button>
                <p>
                  Don't have an account?{" "}
                  <button onClick={() => setMode("signup")} className="link-btn">
                    Sign up
                  </button>
                </p>
              </>
            )}
            {mode === "signup" && (
              <p>
                Already have an account?{" "}
                <button onClick={() => setMode("login")} className="link-btn">
                  Sign in
                </button>
              </p>
            )}
            {mode === "forgot" && (
              <p>
                Remember your password?{" "}
                <button onClick={() => setMode("login")} className="link-btn">
                  Sign in
                </button>
              </p>
            )}
          </div>
        </div>

        <p className="login-disclaimer">
          Beta access for clinical evaluation only
        </p>
      </div>
    </main>
  );
}
