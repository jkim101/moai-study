---
spec_id: SPEC-KG-001
type: implementation-plan
---

# Implementation Plan: SPEC-KG-001

## Technology Stack

| Category         | Technology               | Version          | Purpose                                    |
|------------------|--------------------------|------------------|--------------------------------------------|
| Language         | Python                   | 3.11+            | Core runtime                               |
| Graph Database   | kuzu                     | 0.8.x (latest)   | Embedded graph storage with Cypher support  |
| API Client       | anthropic                | 0.52.x (latest)  | Claude API for entity extraction            |
| CLI Framework    | typer                    | 0.21.x (latest)  | Command-line interface with type hints      |
| Data Validation  | pydantic                 | 2.x (latest)     | Model validation and serialization          |
| Terminal Output  | rich                     | 13.x (latest)    | Formatted tables, progress bars             |
| Visualization    | pyvis                    | 0.3.x (latest)   | Interactive HTML graph rendering            |
| Testing          | pytest                   | 8.x              | Test framework                             |
| Coverage         | pytest-cov               | 6.x              | Coverage reporting                         |
| Linting          | ruff                     | 0.9.x            | Linting and formatting                     |
| Type Checking    | mypy                     | 1.14.x           | Static type analysis                       |
| Package Manager  | uv                       | latest            | Fast dependency management                 |

## Task Decomposition

### TASK-PROJ: Project Scaffolding (Primary Goal)

- Initialize Python project with `pyproject.toml` (Hatchling build system)
- Configure `ruff`, `mypy`, `pytest` settings in `pyproject.toml`
- Create directory structure per `structure.md`
- Set up `conftest.py` with shared test fixtures
- Create `.gitignore` for Python projects

**Dependencies**: None
**Output**: Buildable and testable project skeleton

### TASK-PARSE: JSONL Parser Module (Primary Goal)

- Implement `parser/reader.py`: Glob-based file discovery, line-by-line JSONL reading
- Implement `parser/models.py`: Pydantic models for `ConversationMessage`, `ToolCall`, `ToolResult`, `ConversationSession`
- Implement `parser/transformer.py`: Raw dict to Pydantic model conversion with validation
- Handle edge cases: empty files, truncated lines, encoding issues, mixed message types
- Implement incremental processing state tracking (file path + mtime)

**Dependencies**: TASK-PROJ
**Output**: Reliable JSONL parsing with graceful error handling

### TASK-EXTRACT: Entity Extraction Module (Primary Goal)

- Implement `extractor/client.py`: Anthropic API wrapper with retry logic and rate limit handling
- Implement `extractor/prompts.py`: System and user prompt templates for entity/relationship extraction
- Implement `extractor/models.py`: Pydantic models for `Entity`, `Relationship`, `ExtractionResult`
- Implement `extractor/processor.py`: Batch processing orchestration with progress reporting
- Design extraction prompt that produces structured JSON with entity and relationship arrays
- Implement file-hash-based caching to skip already-processed conversations

**Dependencies**: TASK-PARSE
**Output**: Structured entities and relationships from conversation text

### TASK-GRAPH: Kuzu Graph Store Module (Primary Goal)

- Implement `graph/connection.py`: Database connection lifecycle management
- Implement `graph/schema.py`: Node table and relationship table creation DDL
- Implement `graph/store.py`: CRUD operations for entities and relationships (upsert semantics)
- Implement `graph/queries.py`: Pre-built Cypher query templates for common operations

**Dependencies**: TASK-PROJ
**Output**: Working graph storage with schema initialization and CRUD

### TASK-CLI: CLI Commands (Secondary Goal)

- Implement `cli.py`: Typer application with `ingest`, `query`, `visualize`, `stats` commands
- Implement `pipeline.py`: Orchestrate parse-extract-store workflow
- Add Rich progress bars for ingestion and extraction
- Add formatted table output for query results and stats
- Implement `config.py`: Configuration from environment variables with defaults
- Implement `exceptions.py`: Custom exception hierarchy

**Dependencies**: TASK-PARSE, TASK-EXTRACT, TASK-GRAPH
**Output**: Complete CLI interface for all user-facing operations

### TASK-VIS: Visualization Module (Optional Goal)

- Implement `visualization/renderer.py`: Generate pyvis Network from graph data
- Implement `visualization/styles.py`: Color palette and sizing per entity type
- Support entity type filtering for focused visualizations
- Generate self-contained HTML output

**Dependencies**: TASK-GRAPH
**Output**: Interactive HTML visualization

## Architecture Design Direction

### Layered Architecture

```
CLI Layer (typer)
    |
    v
Orchestration Layer (pipeline.py)
    |
    +---> Parser Layer (parser/)
    |         |
    |         v
    +---> Extraction Layer (extractor/)
    |
    v
Storage Layer (graph/)
    |
    v
Presentation Layer (visualization/)
```

### Key Design Decisions

1. **Dependency Injection**: Core services (API client, graph store) are injected into the pipeline, enabling test mocks
2. **Pydantic Everywhere**: All data boundaries use Pydantic models for validation and serialization
3. **Fail-Safe Processing**: Malformed data is logged and skipped; the pipeline never crashes on bad input
4. **Incremental by Default**: Processing state is tracked per-file to avoid redundant work
5. **Configuration via Environment**: All settings configurable through environment variables with sensible defaults

### Entity Extraction Prompt Strategy

- System prompt defines the entity types and relationship types as a schema
- User prompt provides batched conversation messages as context
- Response format: structured JSON with `entities` and `relationships` arrays
- Each entity includes: `name`, `type`, `description`
- Each relationship includes: `source`, `target`, `type`, `context`, `confidence`

## Risk Analysis

### Risk 1: Claude API Rate Limits

- **Impact**: High -- extraction halts if rate limited
- **Likelihood**: Medium -- depends on conversation volume
- **Mitigation**: Implement exponential backoff retry (base 2s, max 3 retries); batch messages to reduce call count; cache results by file hash to avoid re-processing

### Risk 2: Large Conversation Files

- **Impact**: Medium -- API token limits may be exceeded for very long conversations
- **Likelihood**: Medium -- some conversations can span thousands of messages
- **Mitigation**: Chunk conversations into windows of 5-10 messages per API call; track chunk boundaries for relationship continuity

### Risk 3: JSONL Format Variations

- **Impact**: Medium -- parsing failures on unexpected formats
- **Likelihood**: Low -- Claude Code uses a consistent format, but edge cases exist
- **Mitigation**: Pydantic validation with `model_validate` and graceful fallback; comprehensive test fixtures covering message types (user, assistant, tool_call, tool_result)

### Risk 4: Kuzu API Stability

- **Impact**: Low -- Kuzu is pre-1.0 and API may change
- **Likelihood**: Low -- core Cypher interface is stable
- **Mitigation**: Isolate all Kuzu interactions in the `graph/` module; pin version in `pyproject.toml`

### Risk 5: Extraction Quality Variance

- **Impact**: Medium -- low-quality extractions reduce graph usefulness
- **Likelihood**: Medium -- extraction quality depends on prompt design and conversation content
- **Mitigation**: Include confidence scores in relationships; provide configurable extraction prompts; include manual review workflow for low-confidence extractions

## Reference Patterns

- **Repository Pattern**: `graph/store.py` follows repository pattern for data access abstraction
- **Pipeline Pattern**: `pipeline.py` implements a sequential processing pipeline with error aggregation
- **Factory Pattern**: `parser/transformer.py` uses factory methods to construct model instances from raw data
- **Adapter Pattern**: `extractor/client.py` adapts the Anthropic SDK to the application's needs

## Quality Requirements

- **Test Coverage**: Minimum 85% line coverage across all modules
- **Linting**: Zero ruff errors, zero ruff format violations
- **Type Safety**: Zero mypy errors with strict mode
- **Documentation**: All public functions have docstrings
- **Error Handling**: All external boundaries (file I/O, API calls, database operations) have explicit error handling
