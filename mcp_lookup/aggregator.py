import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Set

from .pulsemcp import PulseMCPClient
from .registry import RegistryClient, RegistryError
from .smithery import SmitheryClient

SOURCE_PRIORITY = ("registry", "smithery", "pulsemcp")
COMMON_SUBDOMAINS = {"mcp", "api", "www", "app", "server", "hub"}


class Aggregator:
    def __init__(
        self,
        registry: Optional[RegistryClient] = None,
        smithery: Optional[SmitheryClient] = None,
        pulsemcp: Optional[PulseMCPClient] = None,
    ):
        self.clients = {
            "registry": registry or RegistryClient(),
            "smithery": smithery or SmitheryClient(),
            "pulsemcp": pulsemcp or PulseMCPClient(),
        }

    def search(self, query: str, limit: int = 10, source: str = "all") -> List[Dict[str, Any]]:
        sources = self._selected(source)
        results_by_source: Dict[str, List[Dict[str, Any]]] = {}

        with ThreadPoolExecutor(max_workers=len(sources) or 1) as ex:
            futures = {ex.submit(self._safe_search, name, query, limit): name for name in sources}
            for future in as_completed(futures):
                name = futures[future]
                results_by_source[name] = future.result()

        ordered: List[Dict[str, Any]] = []
        for name in SOURCE_PRIORITY:
            if name in results_by_source:
                for entry in results_by_source[name]:
                    entry = dict(entry)
                    entry["_source"] = name
                    ordered.append(entry)
        return _dedupe(ordered)

    def get(
        self,
        query: str,
        version: str = "latest",
        source: str = "all",
        enrich: bool = True,
    ) -> Optional[Dict[str, Any]]:
        sources = self._selected(source)

        tasks: Dict[Any, Any] = {}
        with ThreadPoolExecutor(max_workers=(len(sources) + 1) or 1) as ex:
            for name in sources:
                tasks[ex.submit(self._safe_get, name, query, version)] = ("get", name)
            if enrich and source != "smithery":
                tasks[ex.submit(self._safe_search, "smithery", query, 5)] = ("search", "smithery")
            results: Dict[Any, Any] = {}
            for future in as_completed(tasks):
                results[tasks[future]] = future.result()

        primary = None
        for name in SOURCE_PRIORITY:
            if name in sources and results.get(("get", name)):
                entry = dict(results[("get", name)])
                entry["_source"] = name
                primary = entry
                break
        if primary is None:
            return None

        if enrich and primary["_source"] != "smithery":
            self._enrich_with_smithery_search(primary, results.get(("search", "smithery")) or [])
        return primary

    def _enrich_with_smithery_search(
        self, primary: Dict[str, Any], smithery_search_results: List[Dict[str, Any]]
    ) -> None:
        primary_hosts = _url_hosts(primary)
        if not primary_hosts:
            return
        for sm_summary in smithery_search_results:
            sm_hosts = _url_hosts(sm_summary)
            overlap = primary_hosts & sm_hosts
            if not overlap:
                continue
            qname = (sm_summary.get("server") or {}).get("qualifiedName")
            if not qname:
                continue
            full = self._safe_get("smithery", qname, "latest")
            if not full:
                continue
            tools = (full.get("server") or {}).get("tools") or []
            if not tools:
                continue
            primary["tools"] = tools
            primary["_enriched_by"] = "smithery"
            primary["_enrichment_match"] = sorted(overlap)
            primary["_enrichment_source_name"] = qname
            return

    def _selected(self, source: str) -> List[str]:
        if source == "all":
            return list(SOURCE_PRIORITY)
        return [source] if source in self.clients else []

    def _safe_search(self, source: str, query: str, limit: int) -> List[Dict[str, Any]]:
        return _swallow(lambda: self.clients[source].search(query, limit=limit), default=[])

    def _safe_get(self, source: str, query: str, version: str) -> Optional[Dict[str, Any]]:
        client = self.clients[source]
        if source == "registry":
            return _swallow(lambda: client.get(query, version=version), default=None)
        return _swallow(lambda: client.get(query), default=None)

def _swallow(fn: Callable[[], Any], default: Any) -> Any:
    try:
        return fn()
    except RegistryError:
        return default
    except Exception:
        return default


def _dedupe(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for e in entries:
        key = _identity_key(e)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def _identity_key(entry: Dict[str, Any]) -> str:
    server = entry.get("server", {}) or {}
    source = entry.get("_source", "?")
    if source == "registry":
        return f"registry:{server.get('name','')}".lower()
    if source == "smithery":
        return f"smithery:{server.get('qualifiedName','')}".lower()
    if source == "pulsemcp":
        return f"pulsemcp:{server.get('url') or server.get('name','')}".lower()
    return f"{source}:{server.get('name') or server.get('qualifiedName','')}"


def _url_hosts(entry: Dict[str, Any]) -> Set[str]:
    server = entry.get("server", {}) or {}
    urls: List[Optional[str]] = []
    if isinstance(server.get("repository"), dict):
        urls.append(server["repository"].get("url"))
    for r in server.get("remotes", []) or []:
        urls.append(r.get("url"))
    for c in server.get("connections", []) or []:
        urls.append(c.get("deploymentUrl") or c.get("url"))
    urls.append(server.get("homepage"))
    urls.append(server.get("source_code_url"))
    urls.append(server.get("external_url"))
    urls.append(server.get("url"))

    hosts: Set[str] = set()
    for u in urls:
        host = _normalize_host(u or "")
        if host:
            hosts.add(host)
    return hosts


def _normalize_host(url: str) -> Optional[str]:
    if not url:
        return None
    parsed = urllib.parse.urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or "").lower()
    if not host:
        return None
    parts = host.split(".")
    if len(parts) >= 3 and parts[0] in COMMON_SUBDOMAINS:
        host = ".".join(parts[1:])
    return host
