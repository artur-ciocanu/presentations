from pathlib import Path

from offline_chainlit import localize_html


def test_chainlit_template_drops_remote_fonts_and_katex():
    path = Path(__file__).parent / ".venv/lib/python3.11/site-packages/chainlit/frontend/dist/index.html"
    original = path.read_text()
    assert "fonts.googleapis.com" in original and "cdn.jsdelivr.net" in original
    local = localize_html(original)
    assert "fonts.googleapis.com" not in local
    assert "fonts.gstatic.com" not in local
    assert "cdn.jsdelivr.net" not in local
    assert 'src="/assets/' in local
