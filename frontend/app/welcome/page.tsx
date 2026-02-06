"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function WelcomePage() {
  const [userName, setUserName] = useState<string>("");
  const [step, setStep] = useState<"welcome" | "disclaimer">("welcome");
  const [accepting, setAccepting] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const checkAuthAndGetName = async () => {
      const { createClient } = await import("@/lib/supabase");
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        router.push("/login");
        return;
      }

      const firstName = session.user.user_metadata?.first_name || "";
      setUserName(firstName);
    };
    checkAuthAndGetName();
  }, [router]);

  const handleAccept = async () => {
    setAccepting(true);
    const { createClient } = await import("@/lib/supabase");
    const supabase = createClient();
    await supabase.auth.updateUser({
      data: { disclaimer_accepted: true },
    });
    router.push("/calculator");
  };

  const handleDecline = async () => {
    const { createClient } = await import("@/lib/supabase");
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
  };

  return (
    <main className="landing-page">
      <div className="landing-container">
        <div className="landing-content">
          <Image
            src="/images/vault-dark-mode.svg"
            alt="Vault 3"
            width={500}
            height={165}
            className="landing-logo"
            priority
          />
          
          {step === "welcome" && (
            <div className="welcome-card" style={{ animation: "fadeIn 0.5s ease-out" }}>
              <h1 className="welcome-title">
                Welcome{userName ? `, ${userName}` : ""}
              </h1>
              <p className="welcome-subtitle">
                Thank you for joining ICL Vault
              </p>
              <button onClick={() => setStep("disclaimer")} className="landing-button welcome-btn">
                CONTINUE
              </button>
            </div>
          )}

          {step === "disclaimer" && (
            <div className="disclaimer-card" style={{ animation: "fadeIn 0.5s ease-out" }}>
              <h2 className="disclaimer-card-title">Clinical Disclaimer</h2>
              <p className="disclaimer-card-text">
                Vault AI is one tool to assist surgeons in selecting ICL size for their patients. 
                It is not intended to replace surgeon judgement, and does not claim to result in 
                zero sizing errors or potential need for additional surgical interventions.
              </p>
              <p className="disclaimer-card-prompt">
                Please review and accept to continue.
              </p>
              <div className="disclaimer-card-actions">
                <button className="disclaimer-accept-btn" onClick={handleAccept} disabled={accepting}>
                  {accepting ? "Loading..." : "Accept & Continue"}
                </button>
                <button className="disclaimer-decline-btn" onClick={handleDecline}>
                  Decline
                </button>
              </div>
            </div>
          )}
        </div>
        
        <footer className="landing-footer">
          <a href="https://biminiai.com/" target="_blank" rel="noopener noreferrer">
            <Image
              src="/images/bimini-darkmode.svg"
              alt="Bimini"
              width={120}
              height={40}
              className="footer-logo"
            />
          </a>
        </footer>
      </div>
    </main>
  );
}
