# zbmath-mcp

MCP server for [zbMath Open](https://zbmath.org) — the world's most comprehensive reviewed database of mathematical literature.

This server exposes the [zbMath Open REST API](https://api.zbmath.org/v1/) as [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools, enabling AI assistants such as Claude to search and retrieve mathematical publications, author profiles, and software entries directly.

## Tools

| Tool | Description |
| ------ | ------------- |
| `search_documents` | Free-text search across 4.5 M+ zbMath documents |
| `get_document` | Fetch full metadata for a document by its zbMath ID |
| `structured_search` | Field-filtered search (author, title, MSC code, year range, journal) |
| `get_author` | Fetch an author profile by zbMath author ID |
| `get_software` | Fetch a software / swMath entry by its numeric ID |

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`

This server uses the MCP SDK 2.x `MCPServer` API (2.3.0 or newer).
MCP SDK 1.x is not supported. Client connections still use standard MCP over
stdio; existing client configurations do not need to change.

## Installation

### Using uv (recommended)

Installs a global `zbmath-mcp` command:

```bash
uv tool install git+https://github.com/iwaokimura/zbmath-mcp.git
```

### Using pip

```bash
pip install git+https://github.com/iwaokimura/zbmath-mcp.git
```

### From source

```bash
git clone https://github.com/iwaokimura/zbmath-mcp.git
cd zbmath-mcp
uv sync
```

(With plain `pip` instead of `uv`, run `pip install -e .` in place of `uv sync`.)

To install the current local source as an isolated tool, run this from the
source directory:

```bash
uv tool install .
```

If `zbmath-mcp` is already installed, use `uv tool install --reinstall .` to
replace it with the local version and refresh its dependencies. Tool installation
resolves dependencies from `pyproject.toml`; it does not use the project's
`uv.lock`.

## Usage

### Running the server

If you installed it as a tool (uv) or with pip:

```bash
zbmath-mcp
```

From a source checkout:

```bash
uv run zbmath-mcp
```

The server communicates over **stdio** using the MCP protocol, so running it
in a plain terminal just waits for a client to connect — that is expected.
Normally an MCP client (see below) launches it for you.

### Connecting with Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zbmath": {
      "command": "zbmath-mcp"
    }
  }
}
```

Or, to run from a source checkout without installing (replace the path with
your clone location):

```json
{
  "mcpServers": {
    "zbmath": {
      "command": "uv",
      "args": ["--directory", "/path/to/zbmath-mcp", "run", "zbmath-mcp"]
    }
  }
}
```

### Connecting with Claude Code (CLI)

If installed as a command:

```bash
claude mcp add zbmath -- zbmath-mcp
```

Or from a source checkout (replace the path with your clone location):

```bash
claude mcp add zbmath -- uv --directory /path/to/zbmath-mcp run zbmath-mcp
```

## Example interactions

Once connected, you can ask an AI assistant:

- *"Search zbMath for papers on the Langlands program from the last 5 years."*
- *"Get the zbMath document with ID 7192477."*
- *"Find all papers by Euler in zbMath."*
- *"Search for papers in MSC class 11 (Number Theory) published between 2000 and 2010."*
- *"Look up the software entry for Macaulay2 on swMath."*

## Development

```bash
git clone https://github.com/iwaokimura/zbmath-mcp.git
cd zbmath-mcp
uv sync          # installs runtime + dev dependencies
uv run pytest    # run the test suite
```

## License

MIT — see [LICENSE](LICENSE).
