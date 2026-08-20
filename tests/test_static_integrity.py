import ast
import re
from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "app2.py"
CSS = Path(__file__).resolve().parents[1] / "styles" / "izfin.css"


def test_app_python_syntax():
    ast.parse(APP.read_text(encoding="utf-8"))


def test_css_braces_are_balanced():
    css = CSS.read_text(encoding="utf-8")
    assert css.count("{") == css.count("}")


def test_design_tokens_are_defined_and_not_self_referencing():
    css = CSS.read_text(encoding="utf-8")
    definitions = {
        name: value.strip()
        for name, value in re.findall(
            r"(--iz-[A-Za-z0-9_-]+)\s*:\s*([^;}]+)", css
        )
    }
    uses = set(re.findall(r"var\((--iz-[A-Za-z0-9_-]+)", css))

    undefined = uses - set(definitions)
    self_referencing = {
        name for name, value in definitions.items()
        if f"var({name})" in value
    }

    assert not undefined, f"Undefined IZFIN design tokens: {sorted(undefined)}"
    assert not self_referencing, (
        f"Self-referencing IZFIN design tokens: {sorted(self_referencing)}"
    )


def test_no_old_bist_tickers_in_presets():
    source = APP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in {"BIST_30", "BIST_100"}:
                values[target.id] = ast.literal_eval(node.value)

    all_preset = set(values["BIST_30"]) | set(values["BIST_100"])
    assert not {"KOZAA.IS", "KOZAL.IS", "IPEKE.IS"} & all_preset


def test_version_identifier_exists_and_is_valid():
    source = APP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    version = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == "IZFIN_APP_SURUMU":
                version = ast.literal_eval(node.value)
                break
    assert isinstance(version, str)
    assert version.startswith("v1.")
    assert len(version) >= 6


def test_how_to_use_guide_uses_current_user_facing_language():
    source = APP.read_text(encoding="utf-8")
    guide_start = source.index('with st.expander("📘 IZFIN Rehberi')
    guide_end = source.index('if "izfin_nav" not in st.session_state:', guide_start)
    guide = source[guide_start:guide_end]

    for current_label in (
        "IZFIN SKORU",
        "GÜVEN",
        "GİRİŞ KALİTESİ",
        "MTF UYUM",
        "MERKEZİ KARAR SÖZLÜĞÜ",
        "Sat / Kaçın",
    ):
        assert current_label in guide

    for stale_label in (
        "eski cezalı skor",
        "Eski skorun ana kalemleri",
        "Hibrit / Cezalı Skor",
        "Derin Taramayı çalıştırın",
    ):
        assert stale_label not in guide

    assert "%80 başarı ihtimali anlamına gelmez" in guide
