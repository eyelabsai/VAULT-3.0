import "./globals.css";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "ICL Vault",
  description: "Pentacam-Based, AI-Driven ICL Sizing Nomogram for lens size and vault prediction",
  metadataBase: new URL("https://iclvault.com"),
  openGraph: {
    title: "ICL Vault",
    description: "Pentacam-Based, AI-Driven ICL Sizing Nomogram for lens size and vault prediction",
    url: "https://iclvault.com",
    siteName: "ICL Vault",
    images: [
      {
        url: "/images/vault-dark-mode.svg",
        width: 676,
        height: 216,
        alt: "ICL Vault Logo",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "ICL Vault",
    description: "Pentacam-Based, AI-Driven ICL Sizing Nomogram for lens size and vault prediction",
    images: ["/images/vault-dark-mode.svg"],
  },
  icons: {
    icon: "/images/vault flavicon.svg",
  },
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
