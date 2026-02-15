"use client";

import { useState, useCallback, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";

type Step = "intro" | "name" | "email" | "practice" | "thank-you";
const STEPS: Step[] = ["intro", "name", "email", "practice", "thank-you"];
const FORM_STEPS = STEPS.filter((s) => s !== "intro" && s !== "thank-you");
const TOTAL_FORM_STEPS = FORM_STEPS.length;

const ROTATING_LINES = [
  "Faster sizing. More confidence.",
  "A new layer of certainty for ICL sizing.",
  "Data-driven sizing.",
  "Intelligence for ICL sizing.",
];

export default function WaitlistPage() {
  const [step, setStep] = useState<Step>("intro");
  const [lineIndex, setLineIndex] = useState(0);
  const [fade, setFade] = useState(true);
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    practiceInfo: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentIndex = STEPS.indexOf(step);
  const progress = step === "intro" ? 0 : step === "thank-you" ? 100 : (currentIndex / TOTAL_FORM_STEPS) * 100;

  useEffect(() => {
    if (step !== "intro") return;
    const FADE_MS = 900;
    const interval = setInterval(() => {
      setFade(false);
      setTimeout(() => {
        setLineIndex((prev) => (prev + 1) % ROTATING_LINES.length);
        setFade(true);
      }, FADE_MS);
    }, 5500);
    return () => clearInterval(interval);
  }, [step]);

  const validateStep = useCallback((s: Step): boolean => {
    if (s === "name") {
      const trimmed = form.fullName.trim();
      if (!trimmed || trimmed.split(/\s+/).length < 2) {
        setError("Please enter your first and last name");
        return false;
      }
    }
    if (s === "email") {
      const email = form.email.trim();
      const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!email || !re.test(email)) {
        setError("Please enter a valid email address");
        return false;
      }
    }
    if (s === "practice") {
      const practice = form.practiceInfo.trim();
      if (!practice) {
        setError("Please enter your practice name and location");
        return false;
      }
    }
    setError(null);
    return true;
  }, [form.fullName, form.email, form.practiceInfo]);

  const handleNext = useCallback(() => {
    if (step === "intro") {
      setStep("name");
      setError(null);
      return;
    }
    if (step === "name" && validateStep("name")) {
      setStep("email");
      return;
    }
    if (step === "email" && validateStep("email")) {
      setStep("practice");
      return;
    }
    if (step === "practice" && validateStep("practice")) {
      handleSubmit();
    }
  }, [step, validateStep]);

  const handleBack = useCallback(() => {
    if (step === "name") setStep("intro");
    else if (step === "email") setStep("name");
    else if (step === "practice") setStep("email");
  }, [step]);

  const handleSubmit = () => {
    setSubmitting(true);
    setError(null);
    // Frontend-only for now — no backend; show thank you
    setTimeout(() => {
      setStep("thank-you");
      setSubmitting(false);
    }, 300);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleNext();
    }
  };

  return (
    <main className="landing-page">
      <div className="landing-container">
        <div className="landing-content">
          <Link href="/">
            <div className="logo-container">
              <Image
                src="/images/vault-dark-mode.svg"
                alt="ICL Vault"
                width={800}
                height={280}
                className="landing-logo"
                priority
              />
            </div>
          </Link>

          {step === "intro" && (
            <>
              <p className="landing-tagline">
                Pentacam-Based, AI-Driven ICL Sizing Nomogram
              </p>
              <p className={`rotating-line ${fade ? "fade-in" : "fade-out"}`}>
                {ROTATING_LINES[lineIndex]}
              </p>
              <div className="waitlist-intro">
                <button onClick={handleNext} className="landing-button">
                  Join
                </button>
                <p className="waitlist-hint">This will take about a minute.</p>
              </div>
            </>
          )}

          {step === "name" && (
            <div className="waitlist-form">
              <label className="waitlist-label">What&apos;s your name?</label>
              <input
                type="text"
                value={form.fullName}
                onChange={(e) => setForm((f) => ({ ...f, fullName: e.target.value }))}
                onKeyDown={handleKeyDown}
                placeholder="First and last name"
                className="waitlist-input"
                autoFocus
                autoComplete="name"
              />
              {error && <p className="waitlist-error">{error}</p>}
              <div className="waitlist-status">
                <div className="waitlist-status-bar" style={{ width: `${(1 / TOTAL_FORM_STEPS) * 100}%` }} />
              </div>
            </div>
          )}

          {step === "email" && (
            <div className="waitlist-form">
              <label className="waitlist-label">What&apos;s your email?</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                onKeyDown={handleKeyDown}
                placeholder="you@practice.com"
                className="waitlist-input"
                autoFocus
                autoComplete="email"
              />
              {error && <p className="waitlist-error">{error}</p>}
              <div className="waitlist-status">
                <div className="waitlist-status-bar" style={{ width: `${(2 / TOTAL_FORM_STEPS) * 100}%` }} />
              </div>
            </div>
          )}

          {step === "practice" && (
            <div className="waitlist-form">
              <label className="waitlist-label">Your practice name and location?</label>
              <input
                type="text"
                value={form.practiceInfo}
                onChange={(e) => setForm((f) => ({ ...f, practiceInfo: e.target.value }))}
                onKeyDown={handleKeyDown}
                placeholder="e.g. Parkhurst NuVision, San Antonio, TX"
                className="waitlist-input"
                autoFocus
                autoComplete="organization"
              />
              {error && <p className="waitlist-error">{error}</p>}
              <div className="waitlist-status">
                <div className="waitlist-status-bar" style={{ width: "100%" }} />
              </div>
            </div>
          )}

          {step === "thank-you" && (
            <div className="waitlist-thanks">
              <h1 className="waitlist-thanks-title">Thank you</h1>
              <p className="waitlist-thanks-text">We&apos;ll be in touch soon.</p>
              <Link href="/" className="waitlist-back-link">
                ← Back to home
              </Link>
            </div>
          )}

          {step !== "intro" && step !== "thank-you" && (
            <div className="waitlist-nav">
              <button
                type="button"
                onClick={handleBack}
                className="waitlist-back-btn"
              >
                ← Back
              </button>
              <button
                type="button"
                onClick={handleNext}
                disabled={submitting}
                className="waitlist-next-btn"
              >
                {step === "practice" ? (submitting ? "Submitting…" : "Submit") : "Next →"}
              </button>
            </div>
          )}
        </div>
      </div>

      <footer className="landing-footer">
        <a href="https://biminiai.com/" target="_blank" rel="noopener noreferrer">
          <Image
            src="/images/bimini-darkmode.svg"
            alt="Bimini AI"
            width={140}
            height={48}
            className="footer-logo"
          />
        </a>
      </footer>
    </main>
  );
}
