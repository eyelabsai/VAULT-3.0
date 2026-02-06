"use client";

import { useRouter } from "next/navigation";
import Image from "next/image";

export default function Home() {
  const router = useRouter();

  const handleStartClick = () => {
    router.push("/login");
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
            LOGIN
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

    </main>
  );
}