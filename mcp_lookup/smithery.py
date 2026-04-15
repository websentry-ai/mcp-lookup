import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .registry import USER_AGENT, RegistryError, classify_input

DEFAULT_BASE_URL = "https://api.smithery.ai"
DEFAULT_TIMEOUT = 15


class SmitheryClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        kind, value = classify_input(query)
        q = _host_for_url(value) if kind == "url" else value
        params = {"q": q}
        data = self._request(f"/servers?{urllib.parse.urlencode(params)}")
        servers = data.get("servers", []) or []
        if kind == "url":
            target_host = _host_for_url(value)
            filtered = [s for s in servers if target_host and target_host in (s.get("homepage") or "")]
            servers = filtered or servers
        return [_wrap(s) for s in servers[:limit]]

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        kind, value = classify_input(query)
        if kind == "url":
            matches = self.search(value, limit=1)
            return matches[0] if matches else None
        try:
            data = self._request(f"/servers/{urllib.parse.quote(value, safe='/')}")
        except RegistryError:
            return None
        return _wrap(data)

    def _request(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(url, headers=headers)
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
    return {"_source": "smithery", "server": record}


def _host_for_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value if "://" in value else f"https://{value}")
    return (parsed.netloc or value).lower()
