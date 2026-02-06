"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function WelcomePage() {
  const [userName, setUserName] = useState<string>("");
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

      // Get user's name from metadata
      const firstName = session.user.user_metadata?.first_name || "";
      setUserName(firstName);
    };
    checkAuthAndGetName();
  }, [router]);

  const handleContinue = () => {
    router.push("/calculator");
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
              Welcome{userName ? `, ${userName}` : ""}! 🎉
            </h1>
            <p className="welcome-text">
              Your account has been verified successfully.
              <br />
              You're ready to start using ICL Vault.
            </p>
            
            <button onClick={handleContinue} className="landing-button welcome-btn">
              GET STARTED
            </button>
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
    </main>
  );
}
