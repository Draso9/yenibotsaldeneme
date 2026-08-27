import { ScanQuickControls } from "../../components/scan-quick-controls";
import { ScanWorkspace } from "../../components/scan-workspace";

export default function ScanPage() {
  return (
    <main className="scan-page">
      <div className="scan-path"><a href="/">← Piyasa Merkezi</a><span>Analiz araçları / Akıllı Tarama</span></div>
      <ScanQuickControls />
      <ScanWorkspace />
    </main>
  );
}
