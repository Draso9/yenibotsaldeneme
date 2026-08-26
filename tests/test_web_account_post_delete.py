from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_account_delete_logs_out_then_leaves_the_protected_account_surface():
    """Successful irreversible deletion must not strand a signed-out user on /account."""
    account = _read("web/components/account-page.tsx")

    assert 'import { useRouter } from "next/navigation"' in account
    assert "const router = useRouter()" in account
    assert "await logout();" in account
    assert 'router.replace("/auth?next=%2Fscan&deleted=1")' in account


def test_auth_surface_acknowledges_a_completed_account_deletion():
    """The safe destination should explain why the previous authenticated session ended."""
    auth = _read("web/components/auth-page.tsx")

    assert 'search.get("deleted") === "1"' in auth
    assert "Hesabın ve kullanıcı verilerin kalıcı olarak silindi." in auth
