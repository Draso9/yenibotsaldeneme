import Link from "next/link";
import { ScanWorkspace } from "../../components/scan-workspace";

export default function ScanPage() {
  return (
    <main className="scan-page">
      <div className="scan-path"><Link href="/">← Piyasa Merkezi</Link><span>Analiz araçları / Akıllı Tarama</span></div>
      <ScanWorkspace />
    </main>
  );
}
