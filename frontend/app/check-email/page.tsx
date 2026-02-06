"use client";

import Link from "next/link";
import Image from "next/image";

export default function CheckEmailPage() {
  return (
    <main className="landing-page">
      <div className="landing-container">
        <div className="landing-content">
          <Image
            src="/images/vault-dark-mode.svg"
            alt="Vault 3"
            width={400}
            height={130}
            className="landing-logo"
            priority
          />
          
          <div className="check-email-card">
            <div className="check-email-icon">✉️</div>
            <h1 className="check-email-title">Check Your Email</h1>
            <p className="check-email-text">
              We've sent a confirmation link to your email address.
              <br />
              Please click the link to verify your account.
            </p>
            <p className="check-email-hint">
              Didn't receive the email? Check your spam folder.
            </p>
          </div>

          <Link href="/login" className="back-to-login">
            ← Back to Login
          </Link>
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
