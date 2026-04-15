from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from .pulsemcp import PulseMCPClient
from .registry import RegistryClient, RegistryError
from .smithery import SmitheryClient

SOURCE_PRIORITY = ("registry", "smithery", "pulsemcp")


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

    def get(self, query: str, version: str = "latest", source: str = "all") -> Optional[Dict[str, Any]]:
        for name in self._selected(source):
            entry = self._safe_get(name, query, version)
            if entry:
                entry = dict(entry)
                entry["_source"] = name
                return entry
        return None

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
