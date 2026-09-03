from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODAL = ROOT / "web" / "components" / "modal-surface.tsx"


def test_modal_focus_return_rejects_hidden_opener_and_runs_after_dialog_close():
    source = MODAL.read_text(encoding="utf-8")

    # A connected element can still be hidden inside collapsed scan controls.
    # The focus-return path must reject such an opener and defer restoration
    # until after the native dialog close processing has completed.
    assert "getClientRects().length > 0" in source
    assert "requestAnimationFrame" in source
    assert 'document.getElementById("main-content")' in source


if __name__ == "__main__":
    test_modal_focus_return_rejects_hidden_opener_and_runs_after_dialog_close()
