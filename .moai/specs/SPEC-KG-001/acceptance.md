---
spec_id: SPEC-KG-001
type: acceptance-criteria
---

# Acceptance Criteria: SPEC-KG-001

## AC-PARSE-001: JSONL File Discovery and Parsing

### Scenario 1: Successful ingestion of valid JSONL files

```gherkin
Given a directory containing 3 valid JSONL conversation files
  And each file contains between 10 and 50 messages with "type", "role", and "content" fields
When the user runs "kg ingest <directory>"
Then the system parses all 3 files without errors
  And the system reports the number of files processed and messages parsed
  And the parsed messages are available as structured ConversationSession objects
```

### Scenario 2: Default path discovery

```gherkin
Given JSONL files exist at "~/.claude/projects/test-project/conversation.jsonl"
When the user runs "kg ingest" without a path argument
Then the system discovers and processes files from "~/.claude/projects/" recursively
```

## AC-PARSE-002: Malformed Data Handling

### Scenario 3: Graceful handling of malformed JSONL lines

```gherkin
Given a JSONL file containing 100 valid lines and 3 malformed lines (invalid JSON, missing fields, truncated)
When the system parses this file
Then the system successfully parses the 100 valid lines
  And the system logs 3 warnings with file path and line number for each malformed line
  And the system does not raise an exception or halt processing
```

### Scenario 4: Empty file handling

```gherkin
Given a directory containing one empty JSONL file and one valid JSONL file
When the user runs "kg ingest <directory>"
Then the system skips the empty file with an informational log
  And the system processes the valid file normally
```

## AC-EXTRACT-001: Entity and Relationship Extraction

### Scenario 5: Successful entity extraction from conversation

```gherkin
Given a parsed conversation containing messages about "FastAPI", "SQLAlchemy", and "PostgreSQL"
When the system sends the messages to the Claude API for extraction
Then the system extracts at least 3 entities with types from {Technology, Library, Pattern, Decision, Problem, Solution, File, Function, Concept}
  And each entity has a non-empty "name", "type", and "description"
  And the system extracts at least 1 relationship between the entities
  And each relationship has "source", "target", "type", and "confidence" fields
```

### Scenario 6: Batched extraction for large conversations

```gherkin
Given a parsed conversation containing 50 messages
When the system processes the conversation for extraction
Then the system batches messages into groups of no more than 10
  And each batch is sent as a separate API call
  And entities and relationships from all batches are aggregated into a single result
```

## AC-EXTRACT-002: API Error Handling

### Scenario 7: Rate limit retry behavior

```gherkin
Given the Claude API returns HTTP 429 (rate limit) on the first attempt
When the system retries the request
Then the system waits at least 2 seconds before the first retry
  And the system retries up to 3 times with exponential backoff
  And if the retry succeeds, the extraction result is returned normally
```

### Scenario 8: Authentication error handling

```gherkin
Given the ANTHROPIC_API_KEY environment variable is invalid or missing
When the system attempts to call the Claude API
Then the system halts immediately with an error message containing "API key"
  And no further API calls are attempted
```

## AC-STORE-001: Graph Schema Initialization

### Scenario 9: First-time database creation

```gherkin
Given no Kuzu database exists at the configured path
When the system initializes the graph store
Then the system creates a new Kuzu database
  And the system creates a node table for Entity with properties: id, name, type, description, source_conversation, source_timestamp, metadata
  And the system creates relationship tables for: USES, DEPENDS_ON, SOLVES, RELATES_TO, DISCUSSED_IN, REPLACES, CONFLICTS_WITH
```

## AC-STORE-002: Incremental Processing

### Scenario 10: Skip already-processed files

```gherkin
Given 5 JSONL files were ingested in a previous run
  And 2 new JSONL files have been added since
  And 1 existing file has been modified
When the user runs "kg ingest"
Then the system processes only the 2 new files and 1 modified file
  And the system skips the 4 unchanged files
  And the system reports "3 files processed, 4 files skipped"
```

## AC-QUERY-001: Cypher Query Execution

### Scenario 11: Execute a Cypher query

```gherkin
Given the knowledge graph contains entities of type Technology
When the user runs "kg query 'MATCH (n:Entity) WHERE n.type = \"Technology\" RETURN n.name'"
Then the system executes the Cypher query against the Kuzu database
  And the system displays results in a formatted table
  And the table includes column headers matching the query return clause
```

## AC-QUERY-002: Graph Statistics

### Scenario 12: Display graph statistics

```gherkin
Given the knowledge graph contains 50 entities and 30 relationships
When the user runs "kg stats"
Then the system displays:
  | Metric                    | Value    |
  | Total entities            | 50       |
  | Total relationships       | 30       |
  | Entity count by type      | (breakdown) |
  | Relationship count by type| (breakdown) |
  | Database size             | (in MB)  |
  | Last ingestion            | (timestamp) |
```

## AC-VIS-001: HTML Visualization

### Scenario 13: Generate HTML visualization

```gherkin
Given the knowledge graph contains at least 10 entities and 5 relationships
When the user runs "kg visualize output.html"
Then the system generates a self-contained HTML file at "output.html"
  And the HTML file contains an interactive network graph
  And nodes are color-coded by entity type
  And edges are labeled by relationship type
  And the file is viewable in a standard web browser without additional dependencies
```

## Edge Case Scenarios

### Scenario 14: Empty graph query

```gherkin
Given the knowledge graph is empty (no entities or relationships)
When the user runs "kg query 'MATCH (n:Entity) RETURN n'"
Then the system displays "No results found"
  And the system exits with code 0
```

### Scenario 15: Very large JSONL file

```gherkin
Given a JSONL file containing 10,000+ lines
When the system processes this file
Then the system processes the file without running out of memory
  And the system displays a progress indicator during processing
```

### Scenario 16: Concurrent access attempt

```gherkin
Given the Kuzu database is currently being written to by an "ingest" command
When another process attempts to access the same database
Then the system displays a clear error message about the database being locked
  And the system does not corrupt the database
```

### Scenario 17: Unicode and special characters in conversations

```gherkin
Given a JSONL file containing messages with Unicode characters, emoji, and code blocks with special characters
When the system parses and extracts entities from these messages
Then the system handles all character encodings correctly
  And extracted entity names preserve the original text
```

## Performance Criteria

| Operation                          | Target           | Measurement Method         |
|------------------------------------|------------------|----------------------------|
| Parse 100 JSONL files              | < 10 seconds     | Wall clock time            |
| Extract entities (per conversation)| < 5 seconds      | Claude API round-trip      |
| Graph query (single lookup)        | < 100 ms         | Kuzu query execution time  |
| Graph query (2-hop traversal)      | < 500 ms         | Kuzu query execution time  |
| HTML visualization (500 nodes)     | < 3 seconds      | pyvis render time          |

## Quality Gate Criteria

| Gate                    | Requirement                                           |
|-------------------------|-------------------------------------------------------|
| Test Coverage           | >= 85% line coverage across all modules               |
| Ruff Lint               | Zero errors on `ruff check .`                         |
| Ruff Format             | Zero violations on `ruff format --check .`            |
| Mypy Type Check         | Zero errors on `mypy src/ --strict`                   |
| Pydantic Validation     | All data boundaries use Pydantic models               |
| Error Handling          | All external boundaries have explicit try/except       |
| Documentation           | All public functions have docstrings                  |

## Definition of Done

- [ ] All 17 acceptance test scenarios pass
- [ ] Test coverage >= 85% with `pytest --cov`
- [ ] Zero `ruff check` errors
- [ ] Zero `ruff format --check` violations
- [ ] Zero `mypy --strict` errors
- [ ] CLI help text is complete and accurate for all 4 commands
- [ ] README.md includes installation, configuration, and usage instructions
- [ ] All environment variables are documented
- [ ] Database schema is created automatically on first use
- [ ] Incremental processing works correctly across multiple runs
