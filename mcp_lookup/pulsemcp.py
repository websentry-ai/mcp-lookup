import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .registry import USER_AGENT, RegistryError, classify_input

DEFAULT_BASE_URL = "https://api.pulsemcp.com/v0beta"
DEFAULT_TIMEOUT = 15


class PulseMCPClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        kind, value = classify_input(query)
        q = _query_from_url(value) if kind == "url" else value
        params = {"query": q, "count_per_page": str(max(1, min(limit, 50)))}
        data = self._request(f"/servers?{urllib.parse.urlencode(params)}")
        servers = data.get("servers", []) or []
        if kind == "url":
            normalized = _normalize(value)
            filtered = [s for s in servers if _matches_url(s, normalized)]
            servers = filtered or servers
        return [_wrap(s) for s in servers[:limit]]

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        matches = self.search(query, limit=1)
        return matches[0] if matches else None

    def _request(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
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


def _wrap(record: Dict[str, Any]) -> Dict[str, Any]:
    return {"_source": "pulsemcp", "server": record}


def _query_from_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value if "://" in value else f"https://{value}")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2:
        return parts[-1]
    return (parsed.netloc or value).lower()


def _normalize(url: str) -> str:
    u = url.strip()
    if u.startswith("git@"):
        u = u.replace(":", "/").replace("git@", "https://", 1)
    if u.endswith(".git"):
        u = u[:-4]
    return u.rstrip("/").lower()


def _matches_url(record: Dict[str, Any], normalized: str) -> bool:
    for field in ("source_code_url", "external_url", "url"):
        value = record.get(field) or ""
        if _normalize(value) == normalized:
            return True
    return False
