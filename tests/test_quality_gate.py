from __future__ import annotations
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
CSS = ROOT / "styles" / "izfin.css"
BASELINE = ROOT / "qa" / "quality_baseline.json"
MARKET_UNIVERSE = ROOT / "izfin_core" / "market_universe.py"
HOME_DASHBOARD = ROOT / "izfin_ui" / "home_dashboard.py"

def _metrics():
    app = APP.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    sub10 = [
        float(x) for x in re.findall(r"font-size\s*:\s*([0-9]+(?:\.[0-9]+)?)px", css, flags=re.I)
        if float(x) < 10
    ]
    token_definitions = {
        name: value.strip()
        for name, value in re.findall(
            r"(--iz-[A-Za-z0-9_-]+)\s*:\s*([^;}]+)", css
        )
    }
    token_uses = set(re.findall(r"var\((--iz-[A-Za-z0-9_-]+)", css))
    invalid_tokens = (token_uses - set(token_definitions)) | {
        name for name, value in token_definitions.items()
        if f"var({name})" in value
    }
    return {
        "css_lines": css.count("\n") + 1,
        "important_count": css.count("!important"),
        "media_query_count": len(re.findall(r"@media\s*\(", css)),
        "hex_color_count": len(re.findall(r"#[0-9a-fA-F]{3,8}\b", css)),
        "sub_10px_font_declarations": len(sub10),
        "inline_style_attributes_in_app": len(re.findall(r'style="[^"]+"', app)),
        "unsafe_allow_html_count": app.count("unsafe_allow_html=True"),
        "invalid_design_token_count": len(invalid_tokens),
    }

def test_quality_baseline_file_is_valid():
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert "qa_center_baseline" in data
    assert "budgets" in data

def test_quality_budgets_do_not_regress():
    budgets = json.loads(BASELINE.read_text(encoding="utf-8"))["budgets"]
    m = _metrics()
    for key, value in m.items():
        budget_key = key + "_max"
        assert value <= budgets[budget_key], f"{key}: {value} > budget {budgets[budget_key]}"

def test_qa_helpers_and_renderer_exist():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    fn_names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    for fn in ("izfin_qa_static_metrics", "izfin_qa_release_status", "izfin_qa_center_render"):
        assert fn in fn_names


def test_invalid_design_tokens_are_release_blockers():
    source = APP.read_text(encoding="utf-8")
    assert 'metrics.get("gecersiz_design_token", 0)' in source
    assert '"durum": "KONTROL GEREKİYOR"' in source

def test_critical_ui_markers_remain_present():
    source = (
        APP.read_text(encoding="utf-8")
        + HOME_DASHBOARD.read_text(encoding="utf-8")
    ).upper()
    for marker in ("AKILLI TARAMA", "ANA SAYFA", "IZFIN", "TEYİT BEKLE", "GÜÇLÜ AL", "BÜYÜK HAREKETLER"):
        assert marker in source

def test_no_legacy_koza_codes_return_to_presets():
    tree = ast.parse(MARKET_UNIVERSE.read_text(encoding="utf-8"))
    vals = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in {"BIST_30","BIST_100"}:
                vals[node.targets[0].id] = ast.literal_eval(node.value)
    all_values = set(vals["BIST_30"]) | set(vals["BIST_100"])
    assert not {"KOZAA.IS","KOZAL.IS","IPEKE.IS"} & all_values


def test_qa_center_is_wired_to_navigation():
    source = APP.read_text(encoding="utf-8")
    assert '"🛠️ Sistem Sağlığı"' in source
    assert 'if aktif_sayfa == "🛠️ Sistem Sağlığı":' in source
    assert "izfin_qa_center_render()" in source
