"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function Home() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const { createClient } = await import("@/lib/supabase");
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (session) {
        const hasAccepted = session.user?.user_metadata?.disclaimer_accepted === true;
        router.push(hasAccepted ? "/calculator" : "/welcome");
      } else {
        setChecking(false);
      }
    };
    checkAuth();
  }, [router]);

  const handleStartClick = () => {
    router.push("/login");
  };

  if (checking) {
    return (
      <main className="landing-page">
        <div className="landing-container">
          <div className="landing-content" />
        </div>
      </main>
    );
  }

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