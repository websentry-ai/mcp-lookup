# mcp-lookup

Lookup MCP servers in the [official MCP Registry](https://registry.modelcontextprotocol.io) by name or repository URL. Stdlib-only, no runtime dependencies.

## Why

Tools that need to enrich raw MCP server detections — e.g. a security dashboard that catalogs which MCP servers developers are running, an IDE assistant that needs canonical install metadata, or an SBOM pipeline — typically resort to HTML-scraping third-party catalogs because most registries don't expose a clean JSON API.

`mcp-lookup` wraps the official MCP Registry's JSON API (`registry.modelcontextprotocol.io`) behind a tiny CLI and Python library. It gives you:

- **Canonical server metadata** by name or repo URL: description, publisher namespace, version, packages (`npm`/`pypi`/`docker`), and remote transports (`stdio`/`sse`/`streamable-http`).
- **URL → name resolution**: hand it a `https://github.com/owner/repo` and it finds the registered server entry.
- **Verified publisher signal for free**: namespace prefixes (`io.github.<user>/…`, `<domain>/…`) are cryptographically verified by the registry, giving you a trust signal without extra work.
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
mcp-lookup search github --limit 5
mcp-lookup search https://github.com/owner/repo
mcp-lookup get ai.smithery/Hint-Services-obsidian-github-mcp --pretty
mcp-lookup get https://github.com/owner/repo --pretty
mcp-lookup get <name> --version 1.2.3
mcp-lookup search github --json          # machine-readable
```

Exit codes: `0` success, `1` no results, `2` registry/network error.

## Library

```python
from mcp_lookup import RegistryClient

client = RegistryClient()
results = client.search("github", limit=5)
entry = client.get("ai.smithery/Hint-Services-obsidian-github-mcp")
entry = client.get("https://github.com/owner/repo")
```

## Publishing

```bash
python -m build
twine upload dist/*
```

Or cut a GitHub release — the `.github/workflows/publish.yml` workflow publishes to PyPI via trusted publishing (no secret required once the publisher is configured on PyPI).

## Contributing

Contributions are very welcome — this is an open project and we'd love help from the MCP community.

Good first areas to contribute:

- Additional registry sources (PulseMCP, mcp.so, GitHub topic fallback) behind a provider interface
- Live `tools/list` probing so `get` can return authoritative tool lists
- Local caching (SQLite or file-based) with TTL + `--refresh`
- Fuzzy name resolution and ranking improvements
- Tests and CI coverage

To contribute:

1. Fork the repo and create a feature branch.
2. Keep changes small and focused; match the existing stdlib-only style unless a dependency is strongly justified.
3. Open a pull request describing the motivation and include a quick before/after example where relevant.

Issues and feature requests are equally welcome — file them on GitHub.

## License

Released under the [MIT License](./LICENSE). By contributing, you agree that your contributions will be licensed under the same terms.
