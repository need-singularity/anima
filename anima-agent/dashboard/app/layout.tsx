import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Anima",
  description: "Consciousness interface",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
