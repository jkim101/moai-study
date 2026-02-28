# Product: claude-conversation-kg

## Mission

Transform Claude Code conversation history into an explorable knowledge graph, enabling developers to discover patterns, recall decisions, and trace the evolution of ideas across their development sessions.

## Vision

Provide developers with a powerful yet simple tool that turns ephemeral conversation logs into a persistent, queryable, and visual knowledge base -- bridging the gap between AI-assisted coding sessions and long-term project knowledge management.

## Problem Statement

Developers using Claude Code accumulate a wealth of knowledge across conversations stored as JSONL files at `~/.claude/projects/**/*.jsonl`. This knowledge is:

1. **Ephemeral**: Conversations are linear and difficult to search after the session ends
2. **Siloed**: Related discussions across different sessions are disconnected
3. **Unstructured**: Raw JSONL lacks semantic relationships between concepts
4. **Inaccessible**: No tooling exists to extract, connect, or visualize insights across conversations

## User Personas

### Primary: Solo Developer Using Claude Code

- **Profile**: Individual developer who uses Claude Code daily for coding, debugging, architecture decisions, and learning
- **Pain Points**: Cannot recall which conversation discussed a specific library, pattern, or design decision; loses track of recurring themes across sessions
- **Goal**: Quickly find past decisions, patterns, and knowledge accumulated over weeks or months of Claude Code usage

### Secondary: Team Lead / Technical Architect

- **Profile**: Technical lead reviewing multiple project conversations to understand team decisions and patterns
- **Pain Points**: Cannot aggregate knowledge across team members' Claude Code sessions; decisions are scattered across dozens of conversation files
- **Goal**: Build a unified knowledge base from team conversation history to improve onboarding and decision tracking

## Core Features

### F1: JSONL Conversation Parser

- Parse Claude Code conversation log files (`~/.claude/projects/**/*.jsonl`)
- Handle message types: user messages, assistant responses, tool calls, and tool results
- Support incremental parsing (process only new or updated files since last run)
- Validate and gracefully handle malformed or truncated log entries

### F2: Entity and Relationship Extraction (Claude API)

- Use the Claude API to extract structured entities from conversation text
- Entity types: Technology, Library, Pattern, Decision, Problem, Solution, File, Function, Concept
- Relationship types: USES, DEPENDS_ON, SOLVES, RELATES_TO, DISCUSSED_IN, REPLACES, CONFLICTS_WITH
- Support configurable extraction prompts for domain-specific customization

### F3: Kuzu Knowledge Graph Storage

- Store entities and relationships in a Kuzu embedded graph database (no server required)
- Define a clear graph schema with typed node and edge tables
- Support incremental graph updates without full rebuild
- Provide Cypher query interface for advanced exploration

### F4: CLI Query Interface

- List entities by type with filtering and sorting
- Search entities by name or properties
- Query relationships between entities
- Show conversation context for any entity (trace back to source)
- Export subgraphs as JSON or CSV

### F5: HTML Visualization (Optional)

- Generate interactive network graphs using pyvis
- Color-code nodes by entity type
- Support filtering by entity type, date range, or conversation source
- Export as self-contained HTML file for sharing

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Parse accuracy | 99%+ of valid JSONL entries processed without error | Automated test suite |
| Extraction quality | 80%+ precision on entity/relationship extraction | Manual review of sample set |
| Query latency | < 500ms for typical graph queries | CLI benchmark |
| Graph build time | < 60s for 100 conversation files | End-to-end benchmark |
| User satisfaction | Tool provides actionable insights from past conversations | Qualitative feedback |

## Competitive Landscape

| Solution | Limitation |
|----------|-----------|
| Manual grep/search of JSONL files | No semantic understanding, no relationship mapping |
| Generic note-taking tools | Require manual curation, no automation |
| LLM chat history viewers | Linear view only, no graph relationships |
| General knowledge graph tools (Neo4j, etc.) | Require server setup, not tailored to conversation logs |

## Differentiation

- **Zero infrastructure**: Kuzu is embedded and file-based -- no database server to install or maintain
- **Claude-native**: Purpose-built for Claude Code conversation format with deep understanding of message types
- **AI-powered extraction**: Uses Claude API for intelligent entity/relationship extraction rather than simple keyword matching
- **Developer-first CLI**: Fast, scriptable interface for developers who live in the terminal
- **Incremental processing**: Only processes new conversations, enabling efficient repeated use

## Scope Boundaries

### In Scope (MVP)

- JSONL parsing from Claude Code conversation logs
- Entity and relationship extraction using Claude API
- Kuzu graph storage with Cypher query support
- CLI for querying and exploring the graph
- Basic pyvis HTML visualization

### Out of Scope (Future)

- Real-time conversation monitoring
- Multi-user collaboration features
- Web-based UI (beyond static HTML export)
- Integration with other AI assistant conversation formats
- Natural language query interface (Cypher only for MVP)
