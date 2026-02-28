# Structure: claude-conversation-kg

## Architecture Overview

The project follows a **modular CLI application** architecture with clear separation between parsing, extraction, storage, and presentation layers. Each layer is independently testable and loosely coupled through well-defined interfaces.

```
+------------------+     +---------------------+     +------------------+
|   CLI Layer      | --> |  Orchestration      | --> |  Output Layer    |
|   (Typer)        |     |  (Pipeline)         |     |  (CLI / HTML)    |
+------------------+     +---------------------+     +------------------+
                               |         |
                    +----------+         +----------+
                    |                               |
              +-----v------+               +--------v-------+
              |  Parser    |               |  Graph Store   |
              |  (JSONL)   |               |  (Kuzu)        |
              +-----------+                +----------------+
                    |
              +-----v------+
              |  Extractor |
              |  (Claude)  |
              +------------+
```

### Design Principles

1. **Single Responsibility**: Each module handles one concern (parsing, extraction, storage, presentation)
2. **Dependency Injection**: Core services are injected rather than imported directly, enabling testing with mocks
3. **Incremental Processing**: All operations support delta processing to avoid redundant work
4. **Fail-Safe Parsing**: Malformed data is logged and skipped, never crashes the pipeline

## Directory Structure

```
claude-conversation-kg/
|
|-- src/
|   |-- claude_conversation_kg/        # Main package (22 source files)
|   |   |-- __init__.py
|   |   |-- cli.py                     # Typer CLI entry point: ingest, query, visualize, stats
|   |   |-- pipeline.py               # Orchestration: parse -> extract -> store
|   |   |-- config.py                 # Pydantic-settings based configuration
|   |   |-- exceptions.py             # Custom exception hierarchy
|   |   |
|   |   |-- parser/                   # JSONL conversation parsing
|   |   |   |-- __init__.py
|   |   |   |-- reader.py             # Glob-based file discovery, generator JSONL reading
|   |   |   |-- models.py             # Pydantic models: ConversationMessage, ConversationSession
|   |   |   |-- transformer.py        # Raw JSONL dict to Pydantic model conversion
|   |   |
|   |   |-- extractor/                # Entity/relationship extraction via Claude API
|   |   |   |-- __init__.py
|   |   |   |-- client.py             # Anthropic API wrapper with exponential backoff retry
|   |   |   |-- prompts.py            # System and user prompt templates for extraction
|   |   |   |-- models.py             # Pydantic models: Entity, Relationship, ExtractionResult
|   |   |   |-- processor.py          # Batch orchestration with content-hash caching
|   |   |
|   |   |-- graph/                    # Kuzu graph database operations
|   |   |   |-- __init__.py
|   |   |   |-- schema.py             # DDL for node tables (Entity) and relationship tables
|   |   |   |-- store.py              # Upsert CRUD for entities and relationships
|   |   |   |-- queries.py            # Pre-built Cypher templates (stats, traversal, lookup)
|   |   |   |-- connection.py         # Kuzu database connection lifecycle management
|   |   |
|   |   |-- visualization/            # HTML graph visualization
|   |   |   |-- __init__.py
|   |   |   |-- renderer.py           # pyvis Network generation from graph query results
|   |   |   |-- styles.py             # Color palette and node/edge sizes per entity type
|
|-- tests/                            # 16 test files, 68 tests, 92% coverage
|   |-- __init__.py
|   |-- conftest.py                    # Shared fixtures: sample JSONL, mock API, temp Kuzu DB
|   |-- test_cli.py                    # CLI command tests via Typer CliRunner
|   |-- test_pipeline.py              # Integration tests: parser + mock extractor + Kuzu store
|   |-- test_parser/
|   |   |-- __init__.py
|   |   |-- test_reader.py             # File discovery and JSONL line reading
|   |   |-- test_models.py             # ConversationMessage and ConversationSession models
|   |   |-- test_transformer.py        # JSONL dict to Pydantic model conversion
|   |-- test_extractor/
|   |   |-- __init__.py
|   |   |-- test_client.py             # API client retry and error handling
|   |   |-- test_prompts.py            # Prompt template construction
|   |   |-- test_processor.py          # Batch extraction with mock API responses
|   |-- test_graph/
|   |   |-- __init__.py
|   |   |-- test_schema.py             # Schema DDL creation
|   |   |-- test_store.py              # Entity and relationship upsert operations
|   |   |-- test_queries.py            # Cypher query execution and stats
|   |-- test_visualization/
|   |   |-- __init__.py
|   |   |-- test_renderer.py           # pyvis HTML generation
|   |-- fixtures/                      # Sample JSONL files and expected outputs
|       |-- sample_conversation.jsonl
|       |-- expected_entities.json
|
|-- pyproject.toml                     # Project metadata, Hatchling build, ruff, pytest config
|-- README.md                          # Installation, configuration, and usage instructions
|-- LICENSE
|-- .gitignore
|-- .venv/                             # Virtual environment (uv-managed)
|-- uv.lock                            # Dependency lock file
```

## Module Responsibilities

### cli.py -- Command Line Interface

- Define Typer application with commands: `build`, `query`, `search`, `visualize`, `status`
- Handle argument parsing, validation, and error display
- Delegate all business logic to pipeline and service modules

### pipeline.py -- Orchestration

- Coordinate the full parse-extract-store workflow
- Manage incremental processing state (track last processed file/timestamp)
- Handle progress reporting and error aggregation

### parser/ -- JSONL Parsing

| File | Responsibility |
|------|---------------|
| reader.py | Discover JSONL files using glob patterns, read and yield raw entries |
| models.py | Pydantic models: ConversationMessage, ToolCall, ToolResult, ConversationSession |
| transformer.py | Convert raw JSONL dicts into validated Pydantic model instances |

### extractor/ -- Entity Extraction

| File | Responsibility |
|------|---------------|
| client.py | Thin wrapper around `anthropic.Anthropic` with retry and rate limiting |
| prompts.py | Prompt templates for entity/relationship extraction (system + user prompts) |
| models.py | Pydantic models: Entity, Relationship, ExtractionResult |
| processor.py | Batch conversations through Claude API, aggregate extraction results |

### graph/ -- Knowledge Graph Storage

| File | Responsibility |
|------|---------------|
| schema.py | Define Kuzu node tables (Entity types) and relationship tables |
| store.py | Insert/update/delete entities and relationships in Kuzu |
| queries.py | Pre-built Cypher queries for common operations (find, filter, traverse) |
| connection.py | Manage Kuzu database connection lifecycle and path configuration |

### visualization/ -- Graph Visualization

| File | Responsibility |
|------|---------------|
| renderer.py | Generate pyvis Network objects from graph query results |
| styles.py | Color palette, node sizes, and edge styles per entity/relationship type |

## Data Flow

```
1. Discovery
   ~/.claude/projects/**/*.jsonl
   |
   v
2. Parsing (parser/)
   Raw JSONL -> ConversationSession[]
   |
   v
3. Extraction (extractor/)
   ConversationSession[] -> Entity[] + Relationship[]
   (via Claude API)
   |
   v
4. Storage (graph/)
   Entity[] + Relationship[] -> Kuzu DB
   (file-based, local)
   |
   v
5. Query/Visualize (cli.py + visualization/)
   Cypher Queries -> Results -> Terminal / HTML
```

## Graph Schema

### Node Tables

| Table | Properties |
|-------|-----------|
| Entity | id, name, type, description, source_conversation, source_timestamp, metadata |

Entity types: Technology, Library, Pattern, Decision, Problem, Solution, File, Function, Concept

### Relationship Tables

| Table | From | To | Properties |
|-------|------|----|-----------|
| USES | Entity | Entity | context, confidence |
| DEPENDS_ON | Entity | Entity | version_constraint |
| SOLVES | Entity | Entity | approach |
| RELATES_TO | Entity | Entity | description |
| DISCUSSED_IN | Entity | Entity | message_index |
| REPLACES | Entity | Entity | reason |
| CONFLICTS_WITH | Entity | Entity | description |

## Architecture Decisions

### AD-1: Embedded Database (Kuzu) Over Client-Server (Neo4j)

- **Decision**: Use Kuzu embedded graph database
- **Rationale**: Zero infrastructure requirement aligns with CLI tool philosophy; developers should not need to run a separate database server
- **Trade-off**: Limited to single-process access (acceptable for a CLI tool)

### AD-2: Modular Package Structure Over Flat Layout

- **Decision**: Organize code into `parser/`, `extractor/`, `graph/`, `visualization/` subpackages
- **Rationale**: Clear separation enables independent testing and future replacement of components (e.g., swap Claude for a different LLM)
- **Trade-off**: Slightly more boilerplate for a small project

### AD-3: Pydantic Models for Data Validation

- **Decision**: Use Pydantic v2 for all data models
- **Rationale**: Strong typing, automatic validation, and JSON serialization built-in; aligns well with both JSONL parsing and API responses
- **Trade-off**: Additional dependency, but already required by Typer and Anthropic SDK

### AD-4: Incremental Processing by Default

- **Decision**: Track processed files and only process new/modified conversations
- **Rationale**: Users may have hundreds of conversation files; full rebuild would be slow and wasteful
- **Trade-off**: Additional state management complexity
