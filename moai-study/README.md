# Claude Conversation Knowledge Graph

A CLI tool that parses Claude Code conversation logs, extracts entities and relationships using the Claude API, stores them in a Kuzu embedded graph database, and generates interactive HTML visualizations.

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd moai-study

# Using uv (recommended)
uv venv
uv sync

# Using pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key for entity extraction |
| `CCKG_DB_PATH` | No | `~/.claude-conversation-kg/graph.db` | Path to the Kuzu database |
| `CCKG_LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CCKG_BATCH_SIZE` | No | `10` | Number of messages per extraction batch |

## Usage

### Ingest conversation files

```bash
# Ingest from default path (~/.claude/projects/)
kg ingest

# Ingest from a specific directory
kg ingest /path/to/conversations/
```

### Query the graph

```bash
# Find all technologies
kg query "MATCH (n:Entity) WHERE n.type = 'Technology' RETURN n.name, n.description"

# Find relationships
kg query "MATCH (a:Entity)-[r]->(b:Entity) RETURN a.name, type(r), b.name LIMIT 20"
```

### View statistics

```bash
kg stats
```

### Generate visualization

```bash
# Generate HTML visualization
kg visualize output.html

# Open in browser
open output.html
```

## Development

```bash
# Run tests
python -m pytest tests/ --cov=claude_conversation_kg

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

## Architecture

```
CLI (typer) -> Pipeline -> Parser -> Extractor -> Graph Store -> Visualization
```

- **Parser**: Discovers and reads JSONL conversation files
- **Extractor**: Uses Claude API to identify entities and relationships
- **Graph Store**: Persists data in Kuzu embedded graph database
- **Visualization**: Generates interactive HTML network graphs with pyvis

## Entity Types

Technology, Library, Pattern, Decision, Problem, Solution, File, Function, Concept

## Relationship Types

USES, DEPENDS_ON, SOLVES, RELATES_TO, DISCUSSED_IN, REPLACES, CONFLICTS_WITH

## License

MIT
