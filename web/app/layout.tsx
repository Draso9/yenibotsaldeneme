import type { Metadata } from "next";
import { AuthProvider } from "../components/auth-provider";
import { AppShell } from "../components/app-shell";
import "./globals.css";
import "./market-center.css";
import "./component-polish.css";
import "./stock-detail.css";
import "./projection.css";
import "./performance.css";
import "./strategy-lab.css";
import "./account.css";

export const metadata: Metadata = {
  title: "IZFIN | Akıllı BIST Analizi",
  description: "IZFIN piyasa analizi ve karar destek web istemcisi.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body><AuthProvider><AppShell>{children}</AppShell></AuthProvider></body>
    </html>
  );
}
