---
id: SPEC-KG-001
version: 1.0.0
status: completed
created: 2026-02-27
updated: 2026-02-27
author: jkim101
priority: high
---

## HISTORY

| Version | Date       | Author  | Description                              |
|---------|------------|---------|------------------------------------------|
| 1.0.0   | 2026-02-27 | jkim101 | Initial SPEC creation for Knowledge Graph CLI tool |

---

# SPEC-KG-001: Claude Conversation Knowledge Graph CLI

## 1. Environment

- **Runtime**: Python 3.11+
- **Database**: Kuzu embedded graph database (file-based, no server)
- **API**: Anthropic Claude API for entity/relationship extraction
- **CLI Framework**: Typer with Rich for terminal formatting
- **Visualization**: pyvis for HTML network graph generation
- **Data Source**: Claude Code conversation logs at `~/.claude/projects/**/*.jsonl`
- **Package Management**: uv (primary), pip (fallback)
- **Build System**: Hatchling via pyproject.toml

## 2. Assumptions

- Users have a valid `ANTHROPIC_API_KEY` environment variable configured
- Claude Code conversation logs follow the standard JSONL format with `type`, `role`, and `content` fields
- JSONL files are readable from `~/.claude/projects/` without elevated permissions
- Kuzu database is stored locally at `~/.claude-conversation-kg/graph.db` by default
- The CLI is used by a single user at a time (no concurrent multi-process access to the Kuzu database)
- Internet connectivity is available for Claude API calls during entity extraction
- Conversation files may range from a few KB to several MB in size

## 3. Requirements

### REQ-PARSE-001: JSONL File Discovery and Parsing

**WHEN** the user runs the `ingest` command with a path argument,
**THEN** the system **shall** discover all `.jsonl` files under the specified path recursively and parse each file line by line into structured conversation message objects.

**WHEN** the user runs the `ingest` command without a path argument,
**THEN** the system **shall** default to scanning `~/.claude/projects/` for all `.jsonl` files.

### REQ-PARSE-002: Malformed Data Handling

**IF** a JSONL line is malformed, truncated, or fails Pydantic validation,
**THEN** the system **shall** log a warning with the file path and line number and continue processing remaining lines without interruption.

### REQ-EXTRACT-001: Entity Extraction via Claude API

**WHEN** conversation messages have been parsed successfully,
**THEN** the system **shall** send batched message content to the Claude API using structured JSON output mode and extract entities of the following types: Technology, Library, Pattern, Decision, Problem, Solution, File, Function, Concept.

### REQ-EXTRACT-002: Relationship Extraction

**WHEN** entities are extracted from conversation messages,
**THEN** the system **shall** also extract relationships between entities of the following types: USES, DEPENDS_ON, SOLVES, RELATES_TO, DISCUSSED_IN, REPLACES, CONFLICTS_WITH.

### REQ-EXTRACT-003: API Error Handling and Rate Limiting

**IF** the Claude API returns a rate limit error (HTTP 429) or a transient server error (HTTP 5xx),
**THEN** the system **shall** retry with exponential backoff (base 2 seconds, max 3 retries) before failing the batch.

**IF** the Claude API returns an authentication error (HTTP 401),
**THEN** the system **shall** halt processing immediately and display an actionable error message about the API key.

### REQ-STORE-001: Graph Schema Initialization

**WHEN** the Kuzu database is accessed for the first time or the schema does not exist,
**THEN** the system **shall** create node tables for Entity (with properties: id, name, type, description, source_conversation, source_timestamp, metadata) and relationship tables for all defined relationship types (with properties: context, confidence).

### REQ-STORE-002: Incremental Storage

**WHILE** the system is ingesting conversations,
**THEN** the system **shall** track processed files by their path and modification timestamp, and only process new or modified files on subsequent runs.

### REQ-QUERY-001: Cypher Query Interface

**WHEN** the user runs the `query` command with a Cypher query string,
**THEN** the system **shall** execute the query against the Kuzu database and display results in a formatted table.

### REQ-QUERY-002: Graph Statistics

**WHEN** the user runs the `stats` command,
**THEN** the system **shall** display a summary of the graph including: total entity count, entity count by type, total relationship count, relationship count by type, database file size, and last ingestion timestamp.

### REQ-VIS-001: HTML Visualization Generation

**WHERE** visualization capability is available,
**THEN** the system **shall** generate an interactive HTML file using pyvis with nodes color-coded by entity type and edges labeled by relationship type.

**WHEN** the user runs the `visualize` command with an output path argument,
**THEN** the system **shall** write the generated HTML to the specified path.

## 4. Specifications

### SPEC-CLI: Command Line Interface

The CLI **shall** provide the following commands via Typer:

| Command                   | Description                                    |
|---------------------------|------------------------------------------------|
| `kg ingest [path]`        | Ingest JSONL files into the Kuzu knowledge graph |
| `kg query <cypher>`       | Execute a Cypher query and display results      |
| `kg visualize [output]`   | Generate HTML visualization of the graph        |
| `kg stats`                | Display graph statistics and metadata           |

### SPEC-SCHEMA: Graph Schema

**Node Types:**

| Type       | Description                                      |
|------------|--------------------------------------------------|
| Technology | Programming languages, frameworks, platforms     |
| Library    | Third-party packages and modules                 |
| Pattern    | Design patterns, architectural patterns          |
| Decision   | Technical decisions made during conversations    |
| Problem    | Bugs, issues, challenges discussed               |
| Solution   | Fixes, workarounds, approaches to problems       |
| File       | Source code files referenced in conversations    |
| Function   | Functions, methods, classes mentioned            |
| Concept    | Abstract concepts, ideas, principles             |

**Relationship Types:**

| Type           | Description                                     |
|----------------|-------------------------------------------------|
| USES           | Entity uses or depends on another entity        |
| DEPENDS_ON     | Hard dependency relationship                    |
| SOLVES         | Solution that addresses a problem               |
| RELATES_TO     | General semantic relationship                   |
| DISCUSSED_IN   | Entity discussed in a conversation context      |
| REPLACES       | Entity supersedes another entity                |
| CONFLICTS_WITH | Incompatibility or tension between entities     |

### SPEC-EXTRACTION: Claude API Extraction Strategy

- Batch conversation messages in groups of 5-10 messages to reduce API call volume
- Use Claude API structured JSON output mode for consistent extraction
- Cache extraction results by conversation file hash to avoid re-processing
- Extraction prompt returns a JSON object with `entities` and `relationships` arrays

### SPEC-CONFIG: Configuration

| Setting           | Default                                  | Env Variable       |
|-------------------|------------------------------------------|-------------------|
| Database path     | `~/.claude-conversation-kg/graph.db`     | `CCKG_DB_PATH`    |
| Log level         | `INFO`                                   | `CCKG_LOG_LEVEL`  |
| API key           | (none)                                   | `ANTHROPIC_API_KEY`|
| Batch size        | 10 messages                              | `CCKG_BATCH_SIZE` |

## 5. Traceability

| Requirement     | Plan Reference    | Acceptance Criteria  |
|-----------------|-------------------|----------------------|
| REQ-PARSE-001   | TASK-PARSE        | AC-PARSE-001         |
| REQ-PARSE-002   | TASK-PARSE        | AC-PARSE-002         |
| REQ-EXTRACT-001 | TASK-EXTRACT      | AC-EXTRACT-001       |
| REQ-EXTRACT-002 | TASK-EXTRACT      | AC-EXTRACT-001       |
| REQ-EXTRACT-003 | TASK-EXTRACT      | AC-EXTRACT-002       |
| REQ-STORE-001   | TASK-GRAPH        | AC-STORE-001         |
| REQ-STORE-002   | TASK-GRAPH        | AC-STORE-002         |
| REQ-QUERY-001   | TASK-CLI          | AC-QUERY-001         |
| REQ-QUERY-002   | TASK-CLI          | AC-QUERY-002         |
| REQ-VIS-001     | TASK-VIS          | AC-VIS-001           |

---

## Implementation Notes

- **Implementation date**: 2026-02-27
- **Source files created**: 22 files in `src/claude_conversation_kg/` across cli, pipeline, config, exceptions, parser/, extractor/, graph/, visualization/ modules
- **Test files created**: 16 files in `tests/` with 68 tests passing
- **Test coverage**: 92% (exceeds 85% target)
- **Lint status**: 0 ruff errors

### Requirements Implemented

All 10 requirements implemented and verified:

| Requirement     | Status      |
|-----------------|-------------|
| REQ-PARSE-001   | Implemented |
| REQ-PARSE-002   | Implemented |
| REQ-EXTRACT-001 | Implemented |
| REQ-EXTRACT-002 | Implemented |
| REQ-EXTRACT-003 | Implemented |
| REQ-STORE-001   | Implemented |
| REQ-STORE-002   | Implemented |
| REQ-QUERY-001   | Implemented |
| REQ-QUERY-002   | Implemented |
| REQ-VIS-001     | Implemented |
