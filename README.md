# mcp-lookup

Lookup MCP servers across the [official MCP Registry](https://registry.modelcontextprotocol.io) and [Smithery](https://smithery.ai) from one CLI and Python library. Stdlib-only, no runtime dependencies.

## Why

Tools that need to enrich raw MCP server detections — e.g. a security dashboard that catalogs which MCP servers developers are running, an IDE assistant that needs canonical install metadata, or an SBOM pipeline — typically resort to HTML-scraping third-party catalogs because most registries don't expose a clean JSON API.

`mcp-lookup` wraps the two main MCP catalogs (`registry.modelcontextprotocol.io` and `api.smithery.ai`) behind a tiny, stable interface. It gives you:

- **Canonical server metadata** by name or repo URL: description, publisher namespace, version, packages (`npm`/`pypi`/`docker`), and remote transports (`stdio`/`sse`/`streamable-http`).
- **Two-source aggregation**: `search` returns results from both the registry and Smithery, each labeled by source. `get` prefers the registry (canonical) and falls back to Smithery automatically.
- **Authoritative tool lists**: Smithery entries include the server's `tools[]` with input schemas, which the registry does not expose.
- **URL → name resolution**: hand it a `https://github.com/owner/repo` (or a vendor domain) and it finds the registered server entry.
- **Verified publisher signal for free**: registry namespace prefixes (`io.github.<user>/…`, `<domain>/…`) are cryptographically verified; Smithery entries carry a `verified` flag.
- **Icon derivation**: returns a usable icon URL for every server — Smithery's own `iconUrl` when available, GitHub owner avatars for repo-backed servers, DuckDuckGo favicons for vendor-hosted remotes.
- **Subprocess-friendly**: designed to be called from a backend service to replace fragile HTML scrapers. Outputs stable JSON with `--json`.

Typical callers:

- Dev-tool discovery agents that detect local MCP configs and want enrichment
- Security / DLP platforms classifying MCP servers by publisher and risk
- Registry-aware IDE extensions
- CI jobs validating MCP server manifests

## Install

```bash
pip install mcp-lookup
```

Or from source:

```bash
git clone <repo-url>
cd mcp-lookup
pip install -e .
```

## CLI

```bash
# Search across both sources
mcp-lookup search github --limit 5
mcp-lookup search https://github.com/owner/repo
mcp-lookup search github --json                     # machine-readable

# Get a single record (registry first, Smithery fallback)
mcp-lookup get app.linear/linear --pretty
mcp-lookup get https://github.com/owner/repo --pretty
mcp-lookup get ai.smithery/<name> --version 1.2.3

# Restrict to one source
mcp-lookup --source registry search linear
mcp-lookup --source smithery get linear --pretty    # includes tools[] with descriptions

# Icon derivation
mcp-lookup icon app.linear/linear
mcp-lookup get app.linear/linear --with-icon        # injects icon_url into JSON output
```

Exit codes: `0` success, `1` no results, `2` registry/network error.

## Library

```python
from mcp_lookup import Aggregator, RegistryClient, SmitheryClient, derive_icon_url

# Combined (default)
agg = Aggregator()
results = agg.search("linear", limit=5)            # merged from both sources
entry = agg.get("app.linear/linear")               # registry first, Smithery fallback

# Single source
registry_only = agg.get("app.linear/linear", source="registry")
smithery_only = agg.get("linear", source="smithery")   # includes tools[] list

# Direct clients
RegistryClient().get("app.linear/linear")
SmitheryClient().get("linear")

# Icon helper
icon_url = derive_icon_url(entry)
```

## Contributing

Contributions are very welcome — this is an open project and we'd love help from the MCP community.

Good first areas to contribute:

- Additional sources (PulseMCP, mcp.so, GitHub topic fallback) behind the existing provider interface
- Live `tools/list` probing so registry-only entries can return authoritative tool lists
- Local caching (SQLite or file-based) with TTL + `--refresh`
- Fuzzy name resolution and cross-source deduping improvements
- Tests and CI coverage

To contribute:

1. Fork the repo and create a feature branch.
2. Keep changes small and focused; match the existing stdlib-only style unless a dependency is strongly justified.
3. Open a pull request describing the motivation and include a quick before/after example where relevant.

Issues and feature requests are equally welcome — file them on GitHub.

## License

Released under the [MIT License](./LICENSE). By contributing, you agree that your contributions will be licensed under the same terms.
