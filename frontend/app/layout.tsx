import "./globals.css";

export const metadata = {
  title: "ICL Vault",
  description: "ICL lens size and vault prediction"
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
