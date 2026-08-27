from pathlib import Path
import json
import os
import subprocess
import tempfile


ROOT = Path(__file__).parents[1]


def test_scan_signal_keeps_technical_profile_context_next_to_the_decision():
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")

    assert 'const profile = String(row["Teknik Profil"] ?? "").trim();' in workspace
    assert '<small className="scan-signal-profile">Teknik Profil: {profile}</small>' in workspace
    assert 'column === "Nihai Sinyal" && profile ? <><span>{String(row[column] ?? "—")}</span>' in workspace


def test_scan_result_opens_a_structured_stock_decision_motor_below_the_table():
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")
    decision_card_path = ROOT / "web" / "components" / "scan-decision-card.tsx"

    assert decision_card_path.exists(), "Akıllı Tarama hisse karar kartı henüz yok"
    decision_card = decision_card_path.read_text(encoding="utf-8")

    assert "fetchMarketStockDetail(jobId, selectedTicker" in workspace
    assert "<ScanDecisionCard" in workspace
    assert "HİSSE KARAR MOTORU" in decision_card
    assert "Neden alınabilir?" in decision_card
    assert "Neden beklenmeli / alınmamalı?" in decision_card
    for field in ("decision.guven", "decision.risk", "decision.mtf_uyum", "action.entry_quality", "action.profile"):
        assert field in decision_card
    for level in ("panel.destek", "panel.direnc", "panel.stop", "panel.tp1", "panel.tp2", "panel.tp3"):
        assert level in decision_card
    assert "dangerouslySetInnerHTML" not in decision_card


def test_job_scoped_detail_and_projection_links_encode_the_supplied_route_values():
    with tempfile.TemporaryDirectory() as output:
        compiler = ROOT / "web" / "node_modules" / ".bin" / "tsc"
        compiled = subprocess.run(
            [
                str(compiler),
                "web/lib/stock-detail-route.ts",
                "web/lib/projection.ts",
                "web/lib/api.ts",
                "--target", "ES2022",
                "--module", "commonjs",
                "--moduleResolution", "node",
                "--esModuleInterop",
                "--skipLibCheck",
                "--outDir", output,
                "--noEmit", "false",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert compiled.returncode == 0, compiled.stderr
        script = (
            "const stock = require(process.argv[1]);"
            "const projection = require(process.argv[2]);"
            "console.log(stock.stockDetailHref('job id/7', 'thy ao.is'));"
            "console.log(projection.projectionHref('job id/7', 'thy ao.is'));"
        )
        routes = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(Path(output) / "stock-detail-route.js"),
                str(Path(output) / "projection.js"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    assert routes.returncode == 0, routes.stderr
    assert routes.stdout.splitlines() == [
        "/stocks/THY%20AO.IS?job_id=job%20id%2F7",
        "/projection?job_id=job%20id%2F7&ticker=thy%20ao.is",
    ]


def test_structured_decision_card_renders_real_fields_and_job_scoped_actions():
    with tempfile.TemporaryDirectory() as output:
        compiler = ROOT / "web" / "node_modules" / ".bin" / "tsc"
        compiled = subprocess.run(
            [
                str(compiler),
                "web/components/scan-decision-card.tsx",
                "web/lib/market-center.ts",
                "web/lib/projection.ts",
                "web/lib/stock-detail-route.ts",
                "web/lib/api.ts",
                "--target", "ES2022",
                "--module", "commonjs",
                "--moduleResolution", "node",
                "--jsx", "react-jsx",
                "--esModuleInterop",
                "--skipLibCheck",
                "--outDir", output,
                "--noEmit", "false",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert compiled.returncode == 0, compiled.stderr
        detail = {
            "ticker": "THY AO.IS",
            "price": 312.5,
            "signal": "GÜÇLÜ AL",
            "entry_quality": "YÜKSEK",
            "score": {"nihai": 88},
            "decision": {
                "karar": "ALIM",
                "guven": 82,
                "risk": "DÜŞÜK",
                "mtf_uyum": 75,
                "olumlu_metin": "Trend ve para akışı pozitif",
                "risk_metin": "Direnç bölgesi yakın",
                "mtf_metin": "Günlük: Pozitif",
            },
            "action": {"entry_quality": "YÜKSEK", "profile": "UZUN VADELİ ADAY"},
            "panel": {"destek": 300, "direnc": 320, "stop": 294, "tp1": 325, "tp2": 335, "tp3": 348},
        }
        script = (
            "const React=require('react');"
            "const {renderToStaticMarkup}=require('react-dom/server');"
            "const {ScanDecisionCard}=require(process.argv[1]);"
            "console.log(renderToStaticMarkup(React.createElement(ScanDecisionCard,{jobId:'job id/7',detail:JSON.parse(process.argv[2])})));"
        )
        environment = os.environ.copy()
        environment["NODE_PATH"] = str(ROOT / "web" / "node_modules")
        rendered = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(Path(output) / "components" / "scan-decision-card.js"),
                json.dumps(detail, ensure_ascii=False),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    assert rendered.returncode == 0, rendered.stderr
    markup = rendered.stdout
    for expected in (
        "HİSSE KARAR MOTORU",
        "Trend ve para akışı pozitif",
        "Direnç bölgesi yakın",
        "UZUN VADELİ ADAY",
        "/stocks/THY%20AO.IS?job_id=job%20id%2F7",
        "/projection?job_id=job%20id%2F7&amp;ticker=THY%20AO.IS",
    ):
        assert expected in markup
