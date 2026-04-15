import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .registry import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, RegistryClient, RegistryError


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="mcp-lookup", description="Lookup MCP servers in the official MCP Registry.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Registry base URL.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds.")

    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search servers by name or repository URL.")
    p_search.add_argument("query", help="Server name fragment or repository URL.")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--json", action="store_true", help="Emit full JSON list.")

    p_get = sub.add_parser("get", help="Get one server by name or repository URL.")
    p_get.add_argument("query", help="Exact server name or repository URL.")
    p_get.add_argument("--version", default="latest", help="Version (default: latest). Ignored for URL lookup.")
    p_get.add_argument("--pretty", action="store_true", help="Pretty-print summary instead of full JSON.")

    args = parser.parse_args(argv)
    client = RegistryClient(base_url=args.base_url, timeout=args.timeout)

    try:
        if args.command == "search":
            results = client.search(args.query, limit=args.limit)
            if args.json:
                json.dump(results, sys.stdout, indent=2)
                sys.stdout.write("\n")
            else:
                _print_search(results)
            return 0 if results else 1

        if args.command == "get":
            entry = client.get(args.query, version=args.version)
            if not entry:
                print(f"No server found for: {args.query}", file=sys.stderr)
                return 1
            if args.pretty:
                _print_entry(entry)
            else:
                json.dump(entry, sys.stdout, indent=2)
                sys.stdout.write("\n")
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
        s = entry.get("server", {})
        name = s.get("name", "?")
        version = s.get("version", "?")
        repo = (s.get("repository") or {}).get("url", "")
        desc = (s.get("description") or "").splitlines()[0][:100]
        print(f"{name}  v{version}")
        if repo:
            print(f"  repo: {repo}")
        if desc:
            print(f"  {desc}")


def _print_entry(entry: Dict[str, Any]) -> None:
    s = entry.get("server", {})
    print(f"name:        {s.get('name')}")
    print(f"version:     {s.get('version')}")
    print(f"description: {s.get('description', '')}")
    repo = (s.get("repository") or {}).get("url")
    if repo:
        print(f"repository:  {repo}")
    for pkg in s.get("packages", []) or []:
        print(f"package:     {pkg.get('registry')}:{pkg.get('name')}@{pkg.get('version')}")
    for remote in s.get("remotes", []) or []:
        print(f"remote:      {remote.get('type')} {remote.get('url')}")


if __name__ == "__main__":
    raise SystemExit(main())
