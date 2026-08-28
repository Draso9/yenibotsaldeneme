import type { Metadata } from "next";
import { AuthProvider } from "../components/auth-provider";
import { AnalysisContextProvider } from "../components/analysis-context-provider";
import { AppShell } from "../components/app-shell";
import "./globals.css";
import "./market-center.css";
import "./component-polish.css";
import "./scan.css";
import "./stock-detail.css";
import "./projection.css";
import "./performance.css";
import "./strategy-lab.css";
import "./account.css";
import "./admin-quality.css";
import "./workspace-convergence.css";
import "./usage-guide.css";

export const metadata: Metadata = {
  title: "IZFIN | Akıllı Piyasa Kararları",
  description: "IZFIN piyasa analizi ve karar destek web istemcisi.",
  icons: { icon: "/brand/izfin-logo.png", apple: "/brand/izfin-logo.png" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body>
        <AuthProvider>
          <AnalysisContextProvider>
            <AppShell>{children}</AppShell>
          </AnalysisContextProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
