from izfin_services.quality_service import qa_release_status, qa_static_metrics


def test_static_metrics_detect_token_and_style_contracts():
    app = '<div style="color:red"></div>\nst.markdown(x, unsafe_allow_html=True)'
    css = ":root{--iz-ok:#fff}.x{color:var(--iz-ok);font-size:9px!important}"
    metrics = qa_static_metrics(app, css)
    assert metrics["python_satir"] == 2
    assert metrics["important"] == 1
    assert metrics["10px_alti_font"] == 1
    assert metrics["inline_style"] == 1
    assert metrics["unsafe_html"] == 1
    assert metrics["gecersiz_design_token"] == 0


def test_static_metrics_detect_invalid_tokens_and_release_blocker():
    metrics = qa_static_metrics("", ".x{color:var(--iz-missing)}")
    status = qa_release_status(metrics)
    assert metrics["gecersiz_design_token"] == 1
    assert status["durum"] == "KONTROL GEREKİYOR"


def test_release_status_separates_debt_from_blockers():
    status = qa_release_status({
        "gecersiz_design_token": 0,
        "10px_alti_font": 2,
        "important": 0,
        "media_query": 0,
        "hardcoded_hex": 0,
        "design_token_kullanimi": 1,
    })
    assert status["durum"] == "SAĞLIKLI · TEKNİK BORÇ VAR"
    assert "2 adet" in status["notlar"][0]

