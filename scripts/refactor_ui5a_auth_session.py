from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
ARCH = ROOT / "tests" / "test_core_architecture.py"


def _replace_logical(source: str, old: str, new: str, label: str) -> str:
    """Replace one logical text block without normalizing the rest of the file."""
    if source.count(old) == 1:
        return source.replace(old, new, 1)
    pattern = re.escape(old).replace(r"\
", r"\r?\n")
    updated, count = re.subn(pattern, lambda _m: new, source, count=1)
    if count != 1:
        raise SystemExit(f"{label}: expected one logical match, found {count}")
    return updated


def _replace_between(
    source: str,
    start_anchor: str,
    end_anchor: str,
    replacement: str,
    label: str,
) -> str:
    start = source.find(start_anchor)
    end = source.find(end_anchor, start + 1 if start >= 0 else 0)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f"{label}: anchors missing start={start} end={end}")
    return source[:start] + replacement + source[end:]


def refactor_app() -> None:
    source = APP.read_bytes().decode("utf-8")

    for pattern in (
        r"(?m)^import secrets as pysecrets\r?\n",
        r"(?m)^import hashlib\r?\n",
        r"(?m)^import hmac\r?\n",
        r"(?m)^from urllib\.parse import urlencode\r?\n",
    ):
        source, count = re.subn(pattern, "", source, count=1)
        if count != 1:
            raise SystemExit(f"auth stdlib import extraction failed: {pattern}")

    source = re.sub(
        r"(?m)^\s*firebase_auth_hata_mesaji as _firebase_auth_hata_mesaji,\r?\n",
        "",
        source,
        count=1,
    )

    if "from izfin_ui.auth_view import (" not in source:
        anchor = "from izfin_ui.backtest_results import backtest_sonuc_paketi_hazirla"
        pos = source.find(anchor)
        if pos < 0:
            raise SystemExit("auth_view import anchor missing")
        line_end = source.find("\n", pos) + 1
        source = source[:line_end] + (
            "from izfin_ui.auth_view import (\n"
            "    captcha_paketi_uret,\n"
            "    email_gecerli_mi,\n"
            "    giris_formu_hatalari,\n"
            "    kayit_formu_hatalari,\n"
            ")\n"
        ) + source[line_end:]

    if "from izfin_services.auth_service import (" not in source:
        anchor = "from izfin_services.backtest_service import backtest_calistir"
        pos = source.find(anchor)
        if pos < 0:
            raise SystemExit("auth_service import anchor missing")
        source = source[:pos] + (
            "from izfin_services.auth_service import (\n"
            "    AccountService,\n"
            "    AuthSessionService,\n"
            "    google_oauth_state_dogrula,\n"
            "    google_oauth_url_olustur,\n"
            ")\n"
        ) + source[pos:]

    source, count = re.subn(
        r"\r?\ndef _firebase_auth_post\(action, payload\):\r?\n"
        r"    return FIREBASE_AUTH_CLIENT\.post\(action, payload\)\r?\n",
        "\n",
        source,
        count=1,
    )
    if count != 1:
        raise SystemExit("firebase auth wrapper extraction failed")

    service_anchor = 'GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"'
    if "AUTH_SESSION_SERVICE = AuthSessionService(" not in source:
        pos = source.find(service_anchor)
        if pos < 0:
            raise SystemExit("auth service initialization anchor missing")
        line_end = source.find("\n", pos) + 1
        source = source[:line_end] + (
            "\nAUTH_SESSION_SERVICE = AuthSessionService(\n"
            "    verify_id_token=auth.verify_id_token,\n"
            "    verify_session_cookie=auth.verify_session_cookie,\n"
            "    get_user=auth.get_user,\n"
            "    create_session_cookie=auth.create_session_cookie,\n"
            "    error_handler=lambda context, error: izfin_hata_logla(context, error),\n"
            ")\n"
            "ACCOUNT_SERVICE = AccountService(\n"
            "    FIREBASE_AUTH_CLIENT,\n"
            "    USER_REPOSITORY,\n"
            "    default_tickers=VARSAYILAN_TICKERS,\n"
            "    terms_version=IZFIN_TERMS_VERSION,\n"
            "    privacy_version=IZFIN_PRIVACY_VERSION,\n"
            "    error_handler=lambda context, error: izfin_hata_logla(context, error),\n"
            ")\n"
        ) + source[line_end:]

    source = _replace_between(
        source,
        "def _oturum_ac(data, beni_hatirla=False):",
        "def _captcha_hazirla():",
        '''def _oturum_ac(data, beni_hatirla=False):
    oturum, hata = AUTH_SESSION_SERVICE.id_token_oturumu_hazirla(
        data,
        remember=beni_hatirla,
    )
    if hata:
        return False, hata
    try:
        uid = oturum["uid"]
        email = oturum["email"]
        st.session_state.pop("izfin_yasal_onayli", None)
        st.session_state.pop("izfin_export_json", None)
        st.session_state.user_uid = uid
        st.session_state.user_email = email
        st.session_state.logout_triggered = False
        st.session_state.kullanici_listesi_yuklendi = False
        _kullanici_profilini_hazirla(uid, email)
        if beni_hatirla:
            cookie_manager.set(
                "izfin_session",
                oturum["session_cookie"],
                key="set_izfin_session",
                path="/",
                expires_at=oturum["expires_at"],
                max_age=oturum["max_age"],
                secure=True,
                same_site="lax",
            )
        else:
            try:
                cookie_manager.delete(
                    "izfin_session",
                    key="delete_izfin_session_no_remember",
                )
            except Exception as e:
                izfin_hata_logla("silent_exception_line_249", e)
        return True, None
    except Exception as e:
        izfin_hata_logla("firebase_session_state_uygula", e)
        return False, "Güvenli oturum oluşturulamadı. Lütfen tekrar giriş yapın."


def _captcha_yenile():
    paket = captcha_paketi_uret()
    st.session_state.captcha_a = paket["a"]
    st.session_state.captcha_b = paket["b"]
    st.session_state.captcha_nonce = paket["nonce"]


''',
        "auth session/account helper extraction",
    )

    source = _replace_between(
        source,
        "if (not st.session_state.user_email) and saved_session_cookie and not st.session_state.logout_triggered:",
        "# --- IZFIN STRATEJİ SÜRÜMÜ ---",
        '''if (not st.session_state.user_email) and saved_session_cookie and not st.session_state.logout_triggered:
    oturum, _oturum_hatasi = AUTH_SESSION_SERVICE.session_cookie_oturumu_hazirla(
        saved_session_cookie
    )
    if oturum:
        uid = oturum["uid"]
        email = oturum["email"]
        st.session_state.pop("izfin_yasal_onayli", None)
        st.session_state.pop("izfin_export_json", None)
        st.session_state.user_uid = uid
        st.session_state.user_email = email
        st.session_state.kullanici_listesi_yuklendi = False
        _kullanici_profilini_hazirla(uid, email)
    else:
        try:
            cookie_manager.delete("izfin_session", key="delete_invalid_izfin_session")
        except Exception:
            pass
        st.session_state.user_uid = None
        st.session_state.user_email = None
        st.session_state.pop("izfin_yasal_onayli", None)
        st.session_state.pop("izfin_export_json", None)

''',
        "remembered session restore extraction",
    )

    source = _replace_between(
        source,
        "def _google_state_uret():",
        "def _google_tokenu_firebase_tokenina_cevir(google_id_token):",
        '''def _google_oauth_url():
    return google_oauth_url_olustur(
        client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        redirect_uri=GOOGLE_OAUTH_REDIRECT_URI,
        authorize_url=GOOGLE_OAUTH_AUTHORIZE_URL,
    )


''',
        "google oauth crypto extraction",
    )
    source = _replace_logical(
        source,
        "not GOOGLE_OAUTH_CLIENT_SECRET or not _google_state_dogrula(state)",
        "not GOOGLE_OAUTH_CLIENT_SECRET or not google_oauth_state_dogrula(state, GOOGLE_OAUTH_CLIENT_SECRET)",
        "google oauth callback state validation",
    )

    source = _replace_logical(
        source,
        '''            if login_btn:
                if not email or not password:
                    st.error("E-posta ve şifre gerekli.")
                else:
                    data, err = _firebase_auth_post("signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})
                    if err:
                        st.error(err)
                    else:
                        ok, msg = _oturum_ac(data, beni_hatirla=remember)
                        if ok:
                            st.success("Giriş başarılı.")
                            time.sleep(.2)
                            st.rerun()
                        else:
                            st.error(msg)
''',
        '''            if login_btn:
                login_errors = giris_formu_hatalari(email, password)
                if login_errors:
                    for hata in login_errors:
                        st.error(hata)
                else:
                    data, err = FIREBASE_AUTH_CLIENT.post(
                        "signInWithPassword",
                        {"email": email, "password": password, "returnSecureToken": True},
                    )
                    if err:
                        st.error(err)
                    else:
                        ok, msg = _oturum_ac(data, beni_hatirla=remember)
                        if ok:
                            st.success("Giriş başarılı.")
                            time.sleep(.2)
                            st.rerun()
                        else:
                            st.error(msg)
''',
        "login form wiring",
    )
    source = _replace_logical(
        source,
        '                    if "@" not in reset_email or "." not in reset_email.split("@")[-1]:\n',
        '                    if not email_gecerli_mi(reset_email):\n',
        "reset email validation",
    )
    source = _replace_logical(
        source,
        "                        ok, msg = _sifre_sifirlama_maili(reset_email)\n",
        "                        ok, msg = ACCOUNT_SERVICE.sifre_sifirlama_maili(reset_email)\n",
        "password reset service wiring",
    )
    source = _replace_logical(
        source,
        '''            if register_btn:
                errors = []
                if "@" not in reg_email or "." not in reg_email.split("@")[-1]: errors.append("Geçerli bir e-posta girin.")
                if reg_pass != reg_pass2: errors.append("Şifreler eşleşmiyor.")
                if len(reg_pass) < 8 or not re.search(r"[A-ZÇĞİÖŞÜ]", reg_pass) or not re.search(r"[a-zçğıöşü]", reg_pass) or not re.search(r"\\d", reg_pass): errors.append("Şifre en az 8 karakter, büyük/küçük harf ve rakam içermeli.")
                try: captcha_ok = int(captcha.strip()) == int(st.session_state.captcha_a + st.session_state.captcha_b)
                except Exception: captcha_ok = False
                if not captcha_ok: errors.append("Doğrulama işlemi yanlış.")
                if not terms: errors.append("Kullanım koşulları onaylanmalı.")
                if not privacy_notice_seen: errors.append("KVKK Aydınlatma Metni görüntülenip doğrulanmalı.")
''',
        '''            if register_btn:
                errors = kayit_formu_hatalari(
                    email=reg_email,
                    password=reg_pass,
                    password_repeat=reg_pass2,
                    captcha_answer=captcha,
                    captcha_a=st.session_state.captcha_a,
                    captcha_b=st.session_state.captcha_b,
                    terms_accepted=terms,
                    privacy_notice_seen=privacy_notice_seen,
                )
''',
        "registration validation wiring",
    )
    source = _replace_logical(
        source,
        "                    data, err = _kayit_ol(\n",
        "                    data, err = ACCOUNT_SERVICE.kayit_ol(\n",
        "registration account service wiring",
    )

    APP.write_bytes(source.encode("utf-8"))


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")

    if '        "izfin_ui.auth_view",\n' not in source:
        source = _replace_logical(
            source,
            '        "izfin_ui.backtest_results",\n',
            '        "izfin_ui.backtest_results",\n        "izfin_ui.auth_view",\n',
            "auth ui architecture import",
        )
    if '        "izfin_services.auth_service",\n' not in source:
        source = _replace_logical(
            source,
            '        "izfin_services.backtest_service",\n',
            '        "izfin_services.auth_service",\n        "izfin_services.backtest_service",\n',
            "auth service architecture import",
        )

    block = '''


def test_auth_session_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.auth_service import (" in source
    assert "from izfin_ui.auth_view import (" in source
    assert "AUTH_SESSION_SERVICE.id_token_oturumu_hazirla(" in source
    assert "AUTH_SESSION_SERVICE.session_cookie_oturumu_hazirla(" in source
    assert "ACCOUNT_SERVICE.kayit_ol(" in source
    assert "ACCOUNT_SERVICE.sifre_sifirlama_maili(" in source
    assert "google_oauth_state_dogrula(" in source
    assert "google_oauth_url_olustur(" in source
    assert "captcha_paketi_uret(" in source
    assert "def _google_state_uret(" not in source
    assert "def _google_state_dogrula(" not in source
    assert "def _kayit_ol(" not in source
    assert "def _sifre_sifirlama_maili(" not in source
    assert "hmac.new(" not in source
    assert "hashlib.sha256" not in source
    assert "pysecrets." not in source
    assert "len(reg_pass) < 8" not in source
'''
    if "def test_auth_session_orchestration_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
