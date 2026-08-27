from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_next_web_uses_same_origin_api_proxy_for_browser_requests():
    config = (ROOT / "web" / "next.config.ts").read_text(encoding="utf-8")
    api_source = (ROOT / "web" / "lib" / "api.ts").read_text(encoding="utf-8")

    assert 'source: "/izfin-api/:path*"' in config
    assert "izfin-api-469145462773.europe-west1.run.app" in config
    assert 'return "/izfin-api"' in api_source
