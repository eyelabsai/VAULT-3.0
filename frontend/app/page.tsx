"use client";

import { useRouter } from "next/navigation";
import Image from "next/image";

export default function Home() {
  const router = useRouter();

  const handleEnterClick = async () => {
    try {
      const { createClient } = await import("@/lib/supabase");
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (session) {
        const hasAccepted = session.user?.user_metadata?.disclaimer_accepted === true;
        if (hasAccepted) {
          router.push("/calculator");
        } else {
          router.push("/welcome");
        }
      } else {
        router.push("/login");
      }
    } catch (error) {
      console.error("Auth check failed:", error);
      router.push("/login");
    }
  };

  return (
    <main className="landing-page">
      <div className="landing-container">
        <div className="landing-content">
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
          
          <p className="landing-tagline">
            Pentacam-Based, AI-Driven ICL Sizing Nomogram
          </p>
          
          <button onClick={handleEnterClick} className="landing-button">
            Enter
          </button>
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
      </div>

    </main>
  );
}