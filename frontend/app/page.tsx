"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function Home() {
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const router = useRouter();

  const handleStartClick = () => {
    setShowDisclaimer(true);
  };

  const handleAccept = () => {
    router.push("/calculator");
  };

  return (
    <main className="landing-page">
      <div className="landing-container">
        <div className="landing-content">
          <Image
            src="/images/vault-dark-mode.svg"
            alt="Vault 3"
            width={600}
            height={200}
            className="landing-logo"
            priority
          />
          
          <p className="landing-tagline">
            Pentacam-Based, AI-Driven ICL Sizing Nomogram
          </p>
          
          <button onClick={handleStartClick} className="landing-button">
            START
          </button>
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

      {/* Disclaimer Modal */}
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
              <button className="disclaimer-decline-btn" onClick={() => window.location.href = "https://google.com"}>
                Decline
              </button>
              <button className="disclaimer-accept-btn" onClick={handleAccept}>
                Accept & Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}