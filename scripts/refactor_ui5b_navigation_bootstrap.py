from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
ARCH = ROOT / "tests" / "test_core_architecture.py"


def replace_between(source: str, start_anchor: str, end_anchor: str, replacement: str, label: str) -> str:
    start = source.find(start_anchor)
    end = source.find(end_anchor, start + 1 if start >= 0 else 0)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f"{label}: anchors missing start={start} end={end}")
    return source[:start] + replacement + source[end:]


def insert_before_once(source: str, anchor: str, block: str, marker: str, label: str) -> str:
    if marker in source:
        return source
    pos = source.find(anchor)
    if pos < 0:
        raise SystemExit(f"{label}: anchor missing")
    return source[:pos] + block + source[pos:]


def refactor_app() -> None:
    source = APP.read_bytes().decode("utf-8")

    source = insert_before_once(
        source,
        "from izfin_ui.auth_view import (",
        "from izfin_ui.navigation import (\n"
        "    admin_email_listesi_hazirla,\n"
        "    admin_mi as navigation_admin_mi,\n"
        "    navigation_paketi_hazirla,\n"
        ")\n",
        "from izfin_ui.navigation import (",
        "navigation import",
    )
    source = insert_before_once(
        source,
        "from izfin_services.auth_service import (",
        "from izfin_services.bootstrap_service import (\n"
        "    kullanici_liste_doc_id,\n"
        "    kullanici_watchlist_bootstrap_hazirla,\n"
        "    kullanici_watchlist_kaydet,\n"
        "    logout_state_paketi,\n"
        "    session_defaults_hazirla,\n"
        ")\n",
        "from izfin_services.bootstrap_service import (",
        "bootstrap service import",
    )

    if "def _kullanici_liste_doc_id():" in source:
        source = replace_between(
            source,
            "def _kullanici_liste_doc_id():",
            "def _kullanici_profilini_hazirla(uid, email):",
            "",
            "legacy list document id helper",
        )

    admin_block = '''def izfin_admin_email_listesi():
    """Admin e-posta listesini Streamlit Secrets / environment üzerinden güvenle okur."""
    raw = None
    try:
        if "ADMIN_EMAILS" in st.secrets:
            raw = st.secrets.get("ADMIN_EMAILS")
    except Exception:
        raw = None
    if raw in (None, "", []):
        raw = os.getenv("ADMIN_EMAILS", "")
    return admin_email_listesi_hazirla(raw)


def izfin_admin_mi(email=None):
    """Aktif kullanıcının QA/Admin alanlarına erişim yetkisini döndürür."""
    if email is None:
        email = st.session_state.get("user_email", "")
    return navigation_admin_mi(email, izfin_admin_email_listesi())


'''
    if "return navigation_admin_mi(email, izfin_admin_email_listesi())" not in source:
        source = replace_between(
            source,
            "def izfin_admin_email_listesi():",
            "def izfin_admin_erisim_kontrolu():",
            admin_block,
            "admin access presenter extraction",
        )

    if "_SESSION_DEFAULTS = session_defaults_hazirla(VARSAYILAN_TICKERS)" not in source:
        source = replace_between(
            source,
            "_SESSION_DEFAULTS = {",
            "# Kullanıcının Firebase'de kayıtlı özel listesini her oturumda yalnızca bir kez yükle.",
            '''_SESSION_DEFAULTS = session_defaults_hazirla(VARSAYILAN_TICKERS)
for _key, _default in _SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default.copy() if hasattr(_default, "copy") else _default

''',
            "session defaults extraction",
        )

    watchlist_block = '''if st.session_state.user_email and USER_REPOSITORY.available and not st.session_state.kullanici_listesi_yuklendi:
    try:
        _watchlist_bootstrap = kullanici_watchlist_bootstrap_hazirla(
            USER_REPOSITORY,
            uid=st.session_state.get("user_uid"),
            email=st.session_state.get("user_email"),
            default_tickers=VARSAYILAN_TICKERS,
        )
        st.session_state.custom_tickers = _watchlist_bootstrap["tickers"]
        if _watchlist_bootstrap["recovered"]:
            st.session_state["liste_kurtarma_mesaji"] = True
        if st.session_state.aktif_profil == "Kendi Listem":
            st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state.kullanici_listesi_yuklendi = True
    except Exception as _liste_hatasi:
        izfin_hata_logla("kullanici_listesi_yukle", _liste_hatasi)
        st.warning("Kayıtlı listeniz şu anda yüklenemedi. Varsayılan listeyle devam ediliyor.")


def kullanici_listesini_kaydet(raise_on_error=False):
    """Kişisel listeyi kalıcı servis üzerinden yazar ve gerçek başarı durumunu döndürür."""
    try:
        kullanici_watchlist_kaydet(
            USER_REPOSITORY,
            uid=st.session_state.get("user_uid"),
            email=st.session_state.get("user_email"),
            tickers=st.session_state.get("custom_tickers", []),
        )
        return True, None
    except RuntimeError as e:
        mesaj = str(e)
        if mesaj in {
            "Firebase veritabanı bağlantısı kullanılamıyor.",
            "Kullanıcı oturumu bulunamadı.",
        }:
            if raise_on_error:
                raise
            return False, mesaj
        izfin_hata_logla("kullanici_listesi_yaz", e)
        if raise_on_error:
            raise RuntimeError("Firebase liste kaydı tamamlanamadı.") from e
        return False, "Firebase liste kaydı tamamlanamadı."
    except Exception as e:
        izfin_hata_logla("kullanici_listesi_yaz", e)
        if raise_on_error:
            raise RuntimeError("Firebase liste kaydı tamamlanamadı.") from e
        return False, "Firebase liste kaydı tamamlanamadı."

'''
    if "_watchlist_bootstrap = kullanici_watchlist_bootstrap_hazirla(" not in source:
        source = replace_between(
            source,
            "if st.session_state.user_email and USER_REPOSITORY.available and not st.session_state.kullanici_listesi_yuklendi:",
            "@st.cache_data(ttl=90, show_spinner=False)",
            watchlist_block,
            "watchlist bootstrap/save extraction",
        )

    nav_block = '''_izfin_nav_admin = izfin_admin_mi()
_izfin_nav_paketi = navigation_paketi_hazirla(
    st.session_state.get("izfin_nav"),
    is_admin=_izfin_nav_admin,
)
st.session_state.izfin_nav = _izfin_nav_paketi["aktif_sayfa"]


def _izfin_nav_to(hedef):
    st.session_state.izfin_nav = hedef


st.sidebar.markdown('<div class="iz-nav-label" style="margin-top:14px">NAVİGASYON</div>', unsafe_allow_html=True)
_izfin_nav_items = _izfin_nav_paketi["items"]
for _nav_label in _izfin_nav_items:
    st.sidebar.button(
        _nav_label,
        key=f"nav_{_nav_label}",
        type="primary" if st.session_state.izfin_nav == _nav_label else "secondary",
        use_container_width=True,
        on_click=_izfin_nav_to,
        args=(_nav_label,),
    )
aktif_sayfa = st.session_state.izfin_nav
'''
    if "_izfin_nav_paketi = navigation_paketi_hazirla(" not in source:
        source = replace_between(
            source,
            'if "izfin_nav" not in st.session_state:',
            'st.sidebar.markdown("---")',
            nav_block,
            "navigation presenter extraction",
        )

    old_logout_start = 'if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):'
    if "_logout_state = logout_state_paketi(VARSAYILAN_TICKERS)" not in source:
        logout_block = '''if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    try:
        cookie_manager.delete("izfin_session", key="logout_delete_izfin_session")
        cookie_manager.delete("user_email", key="logout_delete_legacy_user_email")
    except Exception:
        pass
    _logout_state = logout_state_paketi(VARSAYILAN_TICKERS)
    for _logout_key, _logout_value in _logout_state["set"].items():
        st.session_state[_logout_key] = (
            _logout_value.copy() if hasattr(_logout_value, "copy") else _logout_value
        )
    for _logout_key in _logout_state["pop"]:
        st.session_state.pop(_logout_key, None)
    time.sleep(.8)
    st.rerun()


'''
        source = replace_between(
            source,
            old_logout_start,
            "def izfin_tarama_overlay_html(",
            logout_block,
            "logout state extraction",
        )

    APP.write_bytes(source.encode("utf-8"))


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")

    if '        "izfin_ui.navigation",\n' not in source:
        anchor = '        "izfin_ui.auth_view",\n'
        if anchor not in source:
            raise SystemExit("architecture UI import anchor missing")
        source = source.replace(anchor, anchor + '        "izfin_ui.navigation",\n', 1)
    if '        "izfin_services.bootstrap_service",\n' not in source:
        anchor = '        "izfin_services.auth_service",\n'
        if anchor not in source:
            raise SystemExit("architecture service import anchor missing")
        source = source.replace(anchor, anchor + '        "izfin_services.bootstrap_service",\n', 1)

    block = '''


def test_navigation_and_bootstrap_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.bootstrap_service import (" in source
    assert "from izfin_ui.navigation import (" in source
    assert "session_defaults_hazirla(VARSAYILAN_TICKERS)" in source
    assert "kullanici_watchlist_bootstrap_hazirla(" in source
    assert "kullanici_watchlist_kaydet(" in source
    assert "navigation_paketi_hazirla(" in source
    assert "logout_state_paketi(VARSAYILAN_TICKERS)" in source
    assert "def _kullanici_liste_doc_id(" not in source
    assert "_varsayilan_set = set(" not in source
    assert "_legacy_set = set(" not in source
    assert "_uid_set = set(" not in source
    assert "_izfin_nav_items = [" not in source
    assert "re.split(r\"[,;\\n]+\", raw)" not in source
'''
    if "def test_navigation_and_bootstrap_orchestration_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
