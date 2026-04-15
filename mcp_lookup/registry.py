import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_BASE_URL = "https://registry.modelcontextprotocol.io"
DEFAULT_TIMEOUT = 15
USER_AGENT = "mcp-lookup/0.1"


class RegistryError(Exception):
    pass


class RegistryClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        kind, value = classify_input(query)
        if kind == "url":
            return self._search_by_url(value, limit)
        return self._search_by_name(value, limit)

    def get(self, query: str, version: str = "latest") -> Optional[Dict[str, Any]]:
        kind, value = classify_input(query)
        if kind == "url":
            matches = self._search_by_url(value, limit=1)
            return matches[0] if matches else None
        try:
            return self._get_version(value, version)
        except RegistryError:
            matches = self._search_by_name(value, limit=1)
            return matches[0] if matches else None

    def _search_by_name(self, name: str, limit: int) -> List[Dict[str, Any]]:
        params = {"search": name, "limit": str(limit)}
        data = self._request(f"/v0/servers?{urllib.parse.urlencode(params)}")
        return data.get("servers", []) or []

    def _search_by_url(self, url: str, limit: int) -> List[Dict[str, Any]]:
        normalized = normalize_repo_url(url)
        token = repo_search_token(normalized) or url
        params = {"search": token, "limit": "50"}
        data = self._request(f"/v0/servers?{urllib.parse.urlencode(params)}")
        servers = data.get("servers", []) or []
        matches = [s for s in servers if matches_repo(s, normalized)]
        return matches[:limit] if matches else servers[:limit]

    def _get_version(self, name: str, version: str) -> Dict[str, Any]:
        encoded = urllib.parse.quote(name, safe="")
        version_segment = urllib.parse.quote(version, safe="")
        return self._request(f"/v0/servers/{encoded}/versions/{version_segment}")

    def _request(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            raise RegistryError(f"HTTP {e.code} for {url}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise RegistryError(f"Network error for {url}: {e.reason}") from e
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise RegistryError(f"Invalid JSON from {url}: {e}") from e


def classify_input(value: str) -> Tuple[str, str]:
    v = value.strip()
    if v.startswith(("http://", "https://", "git@")):
        return "url", v
    return "name", v


def normalize_repo_url(url: str) -> str:
    u = url.strip()
    if u.startswith("git@"):
        u = u.replace(":", "/").replace("git@", "https://", 1)
    if u.endswith(".git"):
        u = u[:-4]
    return u.rstrip("/").lower()


def repo_search_token(url: str) -> Optional[str]:
    parsed = urllib.parse.urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2:
        return parts[-1]
    if parts:
        return parts[0]
    return None


def matches_repo(entry: Dict[str, Any], normalized_url: str) -> bool:
    server = entry.get("server", {})
    repo = (server.get("repository") or {}).get("url") or ""
    if normalize_repo_url(repo) == normalized_url:
        return True
    for remote in server.get("remotes", []) or []:
        if normalize_repo_url(remote.get("url") or "") == normalized_url:
            return True
    return False
