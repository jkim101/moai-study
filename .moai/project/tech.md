# Tech: claude-conversation-kg

## Technology Stack

### Core Language

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Primary language; required for modern typing features (StrEnum, Self, etc.) |

### Dependencies

| Library | Version | Purpose | License |
|---------|---------|---------|---------|
| kuzu | 0.8.x (latest stable) | Embedded graph database with Cypher support | MIT |
| anthropic | 0.52.x (latest stable) | Official Claude API client for entity/relationship extraction | MIT |
| typer | 0.21.x (latest stable) | CLI framework built on Click with type hint support | MIT |
| pydantic | 2.x (latest stable) | Data validation and serialization for all models | MIT |
| rich | 13.x (latest stable) | Terminal output formatting (tables, progress bars, colors) | MIT |
| pyvis | 0.3.x (latest stable) | Interactive HTML network graph visualization | BSD |

### Development Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| pytest | 8.x | Testing framework |
| pytest-cov | 6.x | Coverage reporting |
| pytest-asyncio | 0.24.x | Async test support (if needed) |
| ruff | 0.9.x | Linting and formatting (replaces flake8 + black + isort) |
| mypy | 1.14.x | Static type checking |
| pre-commit | 4.x | Git hook management |

## Package Management

- **Package Manager**: uv (primary) or pip (fallback)
- **Build System**: Hatchling via pyproject.toml
- **Lock File**: uv.lock for reproducible installs
- **Virtual Environment**: Managed by uv (`uv venv`)

## Design Decisions

### DD-1: Typer Over Click for CLI

- **Chosen**: Typer 0.21.x
- **Alternative**: Click 8.x
- **Rationale**: Typer provides type-hint-based argument definition, automatic help generation, and shell completion. It wraps Click internally, so all Click features remain accessible. Reduces boilerplate by 40-60% compared to raw Click.

### DD-2: Kuzu Over Neo4j / NetworkX

- **Chosen**: Kuzu (embedded)
- **Alternatives**: Neo4j (client-server), NetworkX (in-memory)
- **Rationale**: Kuzu is embedded and file-based, requiring zero infrastructure. It supports Cypher queries natively, enabling powerful graph traversal. NetworkX lacks persistence and Cypher support. Neo4j requires a running server, which conflicts with the zero-infrastructure goal.

### DD-3: Pydantic v2 for Data Models

- **Chosen**: Pydantic v2
- **Alternative**: dataclasses, attrs
- **Rationale**: Pydantic v2 provides JSON schema generation, validation, and serialization in one package. Already a transitive dependency of both Typer and the Anthropic SDK. v2 offers 5-50x performance improvement over v1.

### DD-4: ruff for Linting and Formatting

- **Chosen**: ruff
- **Alternative**: flake8 + black + isort
- **Rationale**: Single tool replaces three, with 10-100x faster execution. Covers linting (flake8 rules), formatting (black-compatible), and import sorting (isort-compatible). Reduces CI time and developer friction.

### DD-5: Structured Extraction Prompts

- **Chosen**: JSON-mode structured output via Claude API
- **Alternative**: Free-text extraction with regex parsing
- **Rationale**: Claude API supports structured JSON output, eliminating fragile regex parsing. Pydantic models validate the extraction output directly. Enables consistent entity/relationship schema enforcement.

## Development Environment

### Prerequisites

- Python 3.11 or higher
- uv package manager (recommended) or pip
- Claude API key (ANTHROPIC_API_KEY environment variable)

### Setup Commands

```bash
# Clone and setup
uv venv
uv sync

# Run CLI
uv run claude-conversation-kg --help

# Run tests
uv run pytest --cov=claude_conversation_kg

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| ANTHROPIC_API_KEY | Yes | Claude API key for entity extraction |
| CCKG_DB_PATH | No | Custom path for Kuzu database (default: `~/.claude-conversation-kg/graph.db`) |
| CCKG_LOG_LEVEL | No | Logging verbosity: DEBUG, INFO, WARNING, ERROR (default: INFO) |

## Testing Strategy

### Test Pyramid

| Level | Coverage Target | Framework | Description |
|-------|----------------|-----------|-------------|
| Unit | 85%+ | pytest | Individual functions and classes in isolation |
| Integration | 70%+ | pytest | Module interactions (parser + extractor, store + queries) |
| End-to-End | Key paths | pytest | Full pipeline from JSONL to graph query results |

### Testing Patterns

- **Parser tests**: Use fixture JSONL files with known content; validate Pydantic model output
- **Extractor tests**: Mock the Anthropic API client; validate prompt construction and response parsing
- **Graph tests**: Use temporary Kuzu databases (created/destroyed per test); validate schema creation and CRUD operations
- **CLI tests**: Use Typer's CliRunner for command invocation testing
- **Pipeline tests**: Integration tests combining parser + mock extractor + real Kuzu store

### Test Fixtures

- `tests/fixtures/sample_conversation.jsonl`: Representative conversation with multiple message types
- `tests/fixtures/expected_entities.json`: Expected extraction output for validation
- `conftest.py`: Shared fixtures for temporary databases, mock API clients, and sample data

## CI/CD Pipeline

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
```

### GitHub Actions (Future)

- **Lint**: ruff check + ruff format --check
- **Type Check**: mypy with strict mode
- **Test**: pytest with coverage report
- **Build**: uv build to verify package builds cleanly

## Performance Requirements

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Parse 100 JSONL files | < 10s | Wall clock time |
| Extract entities from 1 conversation | < 5s | Claude API round-trip |
| Graph query (single entity lookup) | < 100ms | Kuzu query time |
| Graph query (2-hop traversal) | < 500ms | Kuzu query time |
| HTML visualization (500 nodes) | < 3s | pyvis render time |

## Security Requirements

- **API Key Management**: ANTHROPIC_API_KEY stored in environment variable only; never persisted to disk or logs
- **Input Validation**: All JSONL input validated through Pydantic models before processing
- **No Network Exposure**: Kuzu is embedded with no network listener; only outbound calls are to the Claude API
- **File Access**: Read-only access to `~/.claude/projects/`; write access only to the configured database path

## Technical Constraints

- **Single Process**: Kuzu embedded mode does not support concurrent multi-process access; CLI commands are sequential
- **API Rate Limits**: Claude API has rate limits; extraction must implement retry with exponential backoff
- **Conversation Size**: Large conversations may need to be chunked before sending to Claude API for extraction
- **Disk Space**: Kuzu database grows with the number of entities; provide a `status` command to show database size
