from typing import Any, Dict, List, Optional

from .registry import RegistryClient, RegistryError
from .smithery import SmitheryClient


class Aggregator:
    def __init__(self, registry: Optional[RegistryClient] = None, smithery: Optional[SmitheryClient] = None):
        self.registry = registry or RegistryClient()
        self.smithery = smithery or SmitheryClient()

    def search(self, query: str, limit: int = 10, source: str = "all") -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if source in {"all", "registry"}:
            try:
                for entry in self.registry.search(query, limit=limit):
                    entry = dict(entry)
                    entry["_source"] = "registry"
                    results.append(entry)
            except RegistryError:
                pass
        if source in {"all", "smithery"}:
            try:
                results.extend(self.smithery.search(query, limit=limit))
            except RegistryError:
                pass
        return _dedupe(results)[: limit * (2 if source == "all" else 1)]

    def get(self, query: str, version: str = "latest", source: str = "all") -> Optional[Dict[str, Any]]:
        if source in {"all", "registry"}:
            try:
                entry = self.registry.get(query, version=version)
                if entry:
                    entry = dict(entry)
                    entry["_source"] = "registry"
                    return entry
            except RegistryError:
                pass
        if source in {"all", "smithery"}:
            try:
                return self.smithery.get(query)
            except RegistryError:
                pass
        return None


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
    return f"{source}:{server.get('name') or server.get('qualifiedName','')}"
