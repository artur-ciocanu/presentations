"""Remove Chainlit's unused remote font and math stylesheets from the page."""

import re

REMOTE_ASSET = re.compile(
    r'<link\b(?=[^>]*\bhref\s*=\s*["\']https://(?:fonts\.googleapis\.com|fonts\.gstatic\.com|cdn\.jsdelivr\.net)(?:/[^"\']*)?["\'])[^>]*>\s*',
    re.IGNORECASE,
)
REMOTE_META = re.compile(r'<meta\b(?=[^>]*\bproperty=["\']og:(?:image|url)["\'])[^>]*>\s*', re.IGNORECASE)


def localize_html(content: str) -> str:
    return REMOTE_META.sub("", REMOTE_ASSET.sub("", content))


def install_local_template():
    # Chainlit 2.12 loads the app module after its server is initialized. Wrap
    # only HTML generation; leave installed vendor files and all routes intact.
    import chainlit.server as server

    original = server.get_html_template
    if getattr(original, "_stage_local_template", False):
        return

    def local_template(root_path):
        return localize_html(original(root_path))

    local_template._stage_local_template = True
    server.get_html_template = local_template
