# mcp-lookup

Lookup MCP servers across the [official MCP Registry](https://registry.modelcontextprotocol.io), [Smithery](https://smithery.ai), and [PulseMCP](https://pulsemcp.com) from one CLI and Python library. Stdlib-only, no runtime dependencies.

## Why

Tools that need to enrich raw MCP server detections — e.g. a security dashboard that catalogs which MCP servers developers are running, an IDE assistant that needs canonical install metadata, or an SBOM pipeline — typically resort to HTML-scraping third-party catalogs because most registries don't expose a clean JSON API.

`mcp-lookup` wraps the three main MCP catalogs (`registry.modelcontextprotocol.io`, `api.smithery.ai`, and `api.pulsemcp.com`) behind a tiny, stable interface. It gives you:

- **Canonical server metadata** by name or repo URL: description, publisher namespace, version, packages (`npm`/`pypi`/`docker`), and remote transports (`stdio`/`sse`/`streamable-http`).
- **Three-source aggregation**: `search` fans out to all three sources **in parallel** and returns merged results, each labeled by `_source`. `get` prefers the registry (canonical), then falls back to Smithery, then PulseMCP.
- **Parallel search for low latency**: search latency is bounded by the slowest source (~1.2s) instead of the sum of all three (~5s). One slow or unavailable source never blocks the others.
- **Authoritative tool lists**: Smithery entries include the server's `tools[]` with input schemas, which the registry does not expose.
- **Community coverage**: PulseMCP adds GitHub star counts, package download counts, and long-tail community servers not (yet) in the official registry.
- **URL → name resolution**: hand it a `https://github.com/owner/repo` (or a vendor domain) and every source tries to find the matching entry.
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
# Search across all three sources (in parallel)
mcp-lookup search github --limit 5
mcp-lookup search https://github.com/owner/repo
mcp-lookup search github --json                     # machine-readable

# Get a single record (registry → Smithery → PulseMCP fallback)
mcp-lookup get app.linear/linear --pretty
mcp-lookup get https://github.com/owner/repo --pretty
mcp-lookup get ai.smithery/<name> --version 1.2.3

# Restrict to one source
mcp-lookup --source registry search linear
mcp-lookup --source smithery get linear --pretty    # includes tools[] with descriptions
mcp-lookup --source pulsemcp search linear

# Icon derivation
mcp-lookup icon app.linear/linear
mcp-lookup get app.linear/linear --with-icon        # injects icon_url into JSON output
```

Exit codes: `0` success, `1` no results, `2` registry/network error.

## Library

```python
from mcp_lookup import (
    Aggregator,
    RegistryClient,
    SmitheryClient,
    PulseMCPClient,
    derive_icon_url,
)

# Combined (default) — parallel across all three sources
agg = Aggregator()
results = agg.search("linear", limit=5)
entry = agg.get("app.linear/linear")                # registry first, Smithery/PulseMCP fallback

# Single source
registry_only = agg.get("app.linear/linear", source="registry")
smithery_only = agg.get("linear", source="smithery")    # includes tools[] list
pulsemcp_only = agg.search("linear", source="pulsemcp")

# Direct clients
RegistryClient().get("app.linear/linear")
SmitheryClient().get("linear")
PulseMCPClient().search("linear", limit=3)

# Icon helper
icon_url = derive_icon_url(entry)
```

## Contributing

Contributions are very welcome — this is an open project and we'd love help from the MCP community.

Good first areas to contribute:

- Additional sources (`mcp.so`, Glama.ai, GitHub topic fallback) behind the existing provider interface
- Live `tools/list` probing so registry-only entries can return authoritative tool lists
- Local caching (SQLite or file-based) with TTL + `--refresh`
- Cross-source deduping by normalized repository URL
- Typed response schemas (Pydantic / JSON Schema) for enterprise consumers
- Tests and CI coverage

To contribute:

1. Fork the repo and create a feature branch.
2. Keep changes small and focused; match the existing stdlib-only style unless a dependency is strongly justified.
3. Open a pull request describing the motivation and include a quick before/after example where relevant.

Issues and feature requests are equally welcome — file them on GitHub.

## License

Released under the [MIT License](./LICENSE). By contributing, you agree that your contributions will be licensed under the same terms.
