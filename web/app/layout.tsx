import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IZFIN | Akıllı BIST Analizi",
  description: "IZFIN web istemcisi için başlangıç uygulaması.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
