import type { Metadata } from "next";
import { AuthProvider } from "../components/auth-provider";
import { AppShell } from "../components/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "IZFIN | Akıllı BIST Analizi",
  description: "IZFIN web istemcisi için başlangıç uygulaması.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body><AuthProvider><AppShell>{children}</AppShell></AuthProvider></body>
    </html>
  );
}
