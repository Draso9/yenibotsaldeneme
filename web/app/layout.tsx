import type { Metadata } from "next";
import { AuthProvider } from "../components/auth-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "IZFIN | Akıllı BIST Analizi",
  description: "IZFIN web istemcisi için başlangıç uygulaması.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body><AuthProvider>{children}</AuthProvider></body>
    </html>
  );
}
