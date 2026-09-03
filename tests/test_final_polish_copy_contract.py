from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_performance_horizon_copy_matches_actual_selector():
    source = read("web/components/performance-view.tsx")
    assert "1 / 5 / 10 / 20 / 45G" in source
    assert "20G / 60G / 120G" not in source


def test_projection_confidence_is_a_score_not_probability_like_percent():
    source = read("web/components/projection-model-view.tsx")
    guide = read("web/components/usage-guide.tsx")
    assert "Model güven skoru" in source or "Model Güven Skoru" in source
    assert "Güven %" not in source
    assert "Model güveni %" not in source
    assert "Olasılık, merkez yol" not in guide


def test_market_center_copy_truthfully_refers_to_latest_scan():
    source = read("web/components/market-center.tsx")
    assert "Son taramada dikkat çekenler" in source
    assert "SON TARAMADA ÖNE ÇIKAN" in source
    assert "BUGÜNÜN ÖNE ÇIKAN HİSSESİ" not in source
    assert "<b>LIVE</b>" not in source


def test_ordinary_user_surfaces_hide_stack_and_provider_jargon():
    shell = read("web/components/app-shell.tsx")
    account = read("web/components/account-page.tsx")
    auth = read("web/components/auth-page.tsx")
    strategy = read("web/components/strategy-lab-page.tsx")

    assert "FastAPI · Next.js" not in shell
    assert '"Strateji Laboratuvarı"' not in shell

    assert "Firebase hesabın" not in account
    assert "Firebase ID token" not in account
    assert "UID ve e-postasıyla" not in account

    assert "Firebase Auth · kişisel veri alanı" not in auth
    assert "Firebase ayarlarını kontrol etmelisin" not in auth

    assert "STRATEJİ LABORATUVARI" not in strategy
