import Link from "next/link";
import Image from "next/image";

export default function Home() {
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
          
          <Link href="/calculator" className="landing-button">
            START
          </Link>
        </div>
        
        <footer className="landing-footer">
          <Image
            src="/images/bimini-darkmode.svg"
            alt="Bimini"
            width={120}
            height={40}
            className="footer-logo"
          />
        </footer>
      </div>
    </main>
  );
}