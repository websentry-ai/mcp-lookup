import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .aggregator import Aggregator
from .icon import derive_icon_url
from .pulsemcp import PulseMCPClient
from .registry import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, RegistryClient, RegistryError
from .smithery import SmitheryClient

SOURCES = ("all", "registry", "smithery", "pulsemcp")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="mcp-lookup", description="Lookup MCP servers across the official MCP Registry and Smithery.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Registry base URL.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds.")
    parser.add_argument("--source", choices=SOURCES, default="all", help="Which source to query (default: all).")

    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search servers by name or repository URL.")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--json", action="store_true")
    p_search.add_argument("--with-icon", action="store_true")

    p_get = sub.add_parser("get", help="Get one server by name or repository URL.")
    p_get.add_argument("query")
    p_get.add_argument("--version", default="latest", help="Registry version (ignored by Smithery).")
    p_get.add_argument("--pretty", action="store_true")
    p_get.add_argument("--with-icon", action="store_true")
    p_get.add_argument("--no-enrich", action="store_true", help="Skip Smithery tools enrichment when URL matches.")

    p_icon = sub.add_parser("icon", help="Print the derived icon URL for a server.")
    p_icon.add_argument("query")

    args = parser.parse_args(argv)
    agg = Aggregator(
        registry=RegistryClient(base_url=args.base_url, timeout=args.timeout),
        smithery=SmitheryClient(timeout=args.timeout),
        pulsemcp=PulseMCPClient(timeout=args.timeout),
    )

    try:
        if args.command == "search":
            results = agg.search(args.query, limit=args.limit, source=args.source)
            if args.with_icon:
                for r in results:
                    r["icon_url"] = derive_icon_url(r)
            if args.json:
                json.dump(results, sys.stdout, indent=2)
                sys.stdout.write("\n")
            else:
                _print_search(results)
            return 0 if results else 1

        if args.command == "get":
            entry = agg.get(args.query, version=args.version, source=args.source, enrich=not args.no_enrich)
            if not entry:
                print(f"No server found for: {args.query}", file=sys.stderr)
                return 1
            if args.with_icon:
                entry["icon_url"] = derive_icon_url(entry)
            if args.pretty:
                _print_entry(entry)
            else:
                json.dump(entry, sys.stdout, indent=2)
                sys.stdout.write("\n")
            return 0

        if args.command == "icon":
            entry = agg.get(args.query, source=args.source)
            if not entry:
                print(f"No server found for: {args.query}", file=sys.stderr)
                return 1
            url = derive_icon_url(entry)
            if not url:
                return 1
            print(url)
            return 0
    except RegistryError as e:
        print(f"registry error: {e}", file=sys.stderr)
        return 2

    return 0


def _print_search(results: List[Dict[str, Any]]) -> None:
    if not results:
        print("(no results)")
        return
    for entry in results:
        source = entry.get("_source", "?")
        s = entry.get("server", {})
        name = s.get("name") or s.get("qualifiedName") or "?"
        version = s.get("version") or ""
        desc = (s.get("description") or s.get("short_description") or "").splitlines()[0][:100]
        repo = (
            (s.get("repository") or {}).get("url")
            or s.get("homepage")
            or s.get("source_code_url")
            or s.get("external_url")
            or ""
        )
        print(f"[{source}] {name}" + (f"  v{version}" if version else ""))
        if repo:
            print(f"  repo: {repo}")
        if desc:
            print(f"  {desc}")


def _print_entry(entry: Dict[str, Any]) -> None:
    source = entry.get("_source", "?")
    s = entry.get("server", {})
    print(f"source:      {source}")
    name = s.get("name") or s.get("qualifiedName")
    print(f"name:        {name}")
    if s.get("displayName"):
        print(f"display:     {s.get('displayName')}")
    if s.get("version"):
        print(f"version:     {s.get('version')}")
    print(f"description: {s.get('description', '')}")
    repo = (s.get("repository") or {}).get("url")
    if repo:
        print(f"repository:  {repo}")
    if s.get("homepage"):
        print(f"homepage:    {s.get('homepage')}")
    for pkg in s.get("packages", []) or []:
        print(f"package:     {pkg.get('registry')}:{pkg.get('name')}@{pkg.get('version')}")
    for remote in s.get("remotes", []) or []:
        print(f"remote:      {remote.get('type')} {remote.get('url')}")
    for conn in s.get("connections", []) or []:
        url = conn.get("deploymentUrl") or conn.get("url")
        print(f"connection:  {conn.get('type')} {url}")
    enriched_by = entry.get("_enriched_by")
    tools = entry.get("tools") or s.get("tools") or []
    if tools and enriched_by:
        match = entry.get("_enrichment_match") or []
        print(f"tools:       {len(tools)}  (enriched via {enriched_by} on {', '.join(match)})")
        for t in tools[:5]:
            print(f"  - {t.get('name')}: {(t.get('description') or '').splitlines()[0][:70]}")
        if len(tools) > 5:
            print(f"  ... {len(tools) - 5} more")
    elif tools:
        print(f"tools:       {len(tools)}")
        for t in tools[:5]:
            print(f"  - {t.get('name')}: {(t.get('description') or '').splitlines()[0][:70]}")
        if len(tools) > 5:
            print(f"  ... {len(tools) - 5} more")
    icon = entry.get("icon_url") or derive_icon_url(entry)
    if icon:
        print(f"icon:        {icon}")


if __name__ == "__main__":
    raise SystemExit(main())
