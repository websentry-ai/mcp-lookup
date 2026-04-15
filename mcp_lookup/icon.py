import base64
import urllib.parse
from typing import Any, Dict, Optional

GITHUB_AVATAR_TEMPLATE = "https://github.com/{owner}.png"
FAVICON_TEMPLATE = "https://icons.duckduckgo.com/ip3/{host}.ico"

COMMON_SUBDOMAINS = {"mcp", "api", "www", "app", "server", "hub"}

DEFAULT_ICON_SVG = (
    b"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' "
    b"fill='none' stroke='#6b7280' stroke-width='4' stroke-linecap='round' "
    b"stroke-linejoin='round'>"
    b"<circle cx='27' cy='27' r='16'/>"
    b"<line x1='38.5' y1='38.5' x2='54' y2='54'/>"
    b"</svg>"
)
DEFAULT_ICON_DATA_URL = (
    "data:image/svg+xml;base64," + base64.b64encode(DEFAULT_ICON_SVG).decode()
)


def derive_icon_url(entry: Dict[str, Any], fallback: bool = True) -> Optional[str]:
    server = entry.get("server", {}) if isinstance(entry, dict) else {}

    if server.get("iconUrl"):
        return server["iconUrl"]

    repo_url = (server.get("repository") or {}).get("url") or server.get("source_code_url") or ""
    owner = _github_owner(repo_url)
    if owner:
        return GITHUB_AVATAR_TEMPLATE.format(owner=owner)

    homepage = server.get("homepage") or server.get("external_url") or ""
    host = _host(homepage)
    if host:
        return FAVICON_TEMPLATE.format(host=_prefer_root(host))

    for remote in server.get("remotes", []) or []:
        host = _host(remote.get("url") or "")
        if host:
            return FAVICON_TEMPLATE.format(host=_prefer_root(host))

    host = _host(repo_url)
    if host:
        return FAVICON_TEMPLATE.format(host=_prefer_root(host))

    return DEFAULT_ICON_DATA_URL if fallback else None


def _github_owner(url: str) -> Optional[str]:
    if not url:
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return None
    parts = [p for p in parsed.path.split("/") if p]
    return parts[0] if parts else None


def _host(url: str) -> Optional[str]:
    if not url:
        return None
    parsed = urllib.parse.urlparse(url)
    return (parsed.netloc or None) and parsed.netloc.lower()


def _prefer_root(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and parts[0] in COMMON_SUBDOMAINS:
        return ".".join(parts[1:])
    return host
