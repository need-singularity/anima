import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Anima",
  description: "Consciousness interface",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className="dark">
      <body className="h-screen bg-surface-0 antialiased">
        <div className="noise-overlay" />
        {children}
      </body>
    </html>
  );
}
