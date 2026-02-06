"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function WelcomePage() {
  const [userName, setUserName] = useState<string>("");
  const [showDisclaimer, setShowDisclaimer] = useState(true);
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

  const handleGetStarted = () => {
    setShowDisclaimer(true);
  };

  const handleAccept = async () => {
    // Mark disclaimer as accepted in user metadata
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
          
          <div className="welcome-card">
            <h1 className="welcome-title">
              Welcome{userName ? `, ${userName}` : ""}
            </h1>
          </div>
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

      {/* Clinical Disclaimer Modal */}
      {showDisclaimer && (
        <div className="disclaimer-overlay">
          <div className="disclaimer-modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="disclaimer-title">Clinical Disclaimer</h2>
            <p className="disclaimer-text">
              Vault AI is one tool to assist surgeons in selecting ICL size for their patients. 
              It is not intended to replace surgeon judgement, and does not claim to result in 
              zero sizing errors or potential need for additional surgical interventions.
            </p>
            <div className="disclaimer-buttons">
              <button className="disclaimer-accept-btn" onClick={handleAccept}>
                Accept & Continue
              </button>
              <button className="disclaimer-decline-btn" onClick={handleDecline}>
                Decline
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
