import urllib.parse
from typing import Any, Dict, Optional

GITHUB_AVATAR_TEMPLATE = "https://github.com/{owner}.png"
FAVICON_TEMPLATE = "https://icons.duckduckgo.com/ip3/{host}.ico"

COMMON_SUBDOMAINS = {"mcp", "api", "www", "app", "server", "hub"}


def derive_icon_url(entry: Dict[str, Any]) -> Optional[str]:
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

    return None


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
