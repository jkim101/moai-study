# KG Dashboard Project Plan

## Overview

Build a web-based dashboard for the Claude Conversation Knowledge Graph using FastAPI + HTML/CSS/JS.
The dashboard combines graph visualization, statistics, search, and natural language chat in one interface.

**Backend**: FastAPI (Python — already familiar from KG project)
**Frontend**: HTML + CSS + JavaScript (learn from scratch)
**Deployment**: localhost first, cloud deployment later if needed
**Data source**: Existing Kuzu graph DB (~2,709 entities, ~5,257 relationships)

**Why FastAPI + HTML?**: To learn web development properly — understanding how backend and frontend work together, rather than using a shortcut framework.

---

## Architecture Overview

```
Browser (Frontend)                    Server (Backend)
┌─────────────────────┐              ┌─────────────────────┐
│  HTML/CSS/JS        │  ← HTTP →   │  FastAPI             │
│                     │              │                      │
│  - Graph canvas     │  GET /api/   │  - REST API routes   │
│  - Stats cards      │  stats       │  - QueryRunner       │
│  - Search box       │  GET /api/   │  - Kuzu DB           │
│  - Chat area        │  entities    │  - NLQ (Claude API)  │
│                     │  POST /api/  │                      │
│                     │  ask         │                      │
└─────────────────────┘              └─────────────────────┘
```

**How it works**:
1. `kg dashboard` starts a FastAPI server on localhost:8000
2. Browser loads HTML page (the "frontend")
3. Frontend calls API endpoints to get data
4. FastAPI queries Kuzu DB and returns JSON
5. JavaScript updates the page with the data

**Key learning**: This is how most web apps work — a frontend that talks to a backend API.

---

## Phase 1: Dashboard Foundation

### Step 1: FastAPI Server Setup

**Goal**: `kg dashboard` opens a browser with a basic page that says "KG Dashboard"

**What you'll learn**:
- What is a web server and what does it do?
- What is an API endpoint?
- How does a browser load a page from a server?
- Basic HTML structure

**Tasks**:
- [ ] Install FastAPI + uvicorn as project dependencies
- [ ] Create `src/claude_conversation_kg/dashboard/` directory
- [ ] Create `dashboard/server.py` — FastAPI app with one route: `GET /` returns HTML
- [ ] Create `dashboard/templates/index.html` — basic HTML page
- [ ] Add `dashboard` command to `cli.py` that starts uvicorn server
- [ ] Verify: `kg dashboard` opens browser at localhost:8000

**File structure**:
```
src/claude_conversation_kg/dashboard/
  __init__.py
  server.py              ← FastAPI app
  templates/
    index.html           ← Main HTML page
  static/
    style.css            ← Styles (later)
    app.js               ← JavaScript (later)
```

**Concepts explained**:
- **FastAPI**: A Python library that listens for web requests and sends responses
- **uvicorn**: A web server that runs FastAPI (like a waiter that serves food)
- **HTML**: The language that describes what a web page looks like
- **GET /**: When browser visits localhost:8000, it sends a "GET" request to "/"

---

### Step 2: Stats API + Display

**Goal**: Show KG statistics on the dashboard

**What you'll learn**:
- What is a REST API?
- What is JSON and how does the frontend use it?
- How JavaScript fetches data from an API
- Basic CSS for layout

**Backend tasks** (Python/FastAPI):
- [ ] Create `GET /api/stats` endpoint that returns entity/relationship counts as JSON
- [ ] Create `GET /api/audit` endpoint that returns top entities as JSON
- [ ] Connect endpoints to existing QueryRunner

**Frontend tasks** (HTML/CSS/JS):
- [ ] Display metric cards (Entities count, Relationships count)
- [ ] Display bar chart for entity type distribution
- [ ] Display table for top 10 entities
- [ ] Style with CSS (cards, colors, layout)

**API response example**:
```json
GET /api/stats
{
  "total_entities": 2709,
  "total_relationships": 5257,
  "entities_by_type": {
    "Technology": 341,
    "Concept": 478,
    "Pattern": 427
  }
}
```

**Layout**:
```
┌──────────────────────────────────────────────┐
│  My Knowledge Graph Dashboard                │
├──────────┬──────────┬──────────┬─────────────┤
│  2,709   │  5,257   │  44      │             │
│ Entities │Relations │Top Mention│             │
├──────────┴──────────┴──────────┴─────────────┤
│  Entity Type Distribution                    │
│  Concept     ████████████████ 478            │
│  Pattern     ██████████████ 427              │
│  Function    █████████████ 369               │
├──────────────────────────────────────────────┤
│  Top 10 Most Mentioned                       │
│  | Entity         | Type       | Mentions |  │
│  | pyproject.toml | File       | 44       |  │
│  | pytest         | Technology | 42       |  │
└──────────────────────────────────────────────┘
```

**Concepts explained**:
- **REST API**: A set of URLs (endpoints) that return data instead of web pages
- **JSON**: A text format for data exchange (like a dictionary in Python)
- **fetch()**: JavaScript function to call an API and get data
- **CSS**: The language that describes how HTML elements look (colors, sizes, spacing)

---

### Step 3: Interactive Graph Visualization

**Goal**: Embed the interactive graph in the dashboard with filters

**What you'll learn**:
- How to embed interactive content in a web page (iframe)
- Event handling in JavaScript (checkbox clicks)
- Passing parameters to API calls

**Backend tasks**:
- [ ] Create `GET /api/graph?types=Technology,Library&min_mentions=3` endpoint
- [ ] Generate filtered pyvis HTML dynamically
- [ ] Serve the generated HTML at `/api/graph/render`

**Frontend tasks**:
- [ ] Add filter checkboxes for entity types
- [ ] Add slider for minimum mention count
- [ ] Embed graph in an iframe that reloads when filters change
- [ ] Style the filter panel

**Layout**:
```
┌──────────┬──────────────────────────────────┐
│ Filters  │                                  │
│          │    Interactive Graph              │
│ Types:   │    (nodes + edges)               │
│ ☑ Tech   │                                  │
│ ☑ Library│    - Colored by type             │
│ ☐ File   │    - Sized by mentions           │
│          │    - Hover for details            │
│ Min:     │                                  │
│ [===3==] │                                  │
└──────────┴──────────────────────────────────┘
```

**Concepts explained**:
- **iframe**: A way to embed one HTML page inside another
- **Query parameters**: `?types=Technology&min_mentions=3` — passing options in a URL
- **Event listener**: JavaScript code that runs when the user clicks/changes something

---

### Step 4: Entity Search

**Goal**: Search entities and see their details + connections

**What you'll learn**:
- Form submission in HTML
- Dynamic page updates without page reload (AJAX)
- Graph traversal queries in Cypher

**Backend tasks**:
- [ ] Create `GET /api/search?q=FastAPI` endpoint — fuzzy name search
- [ ] Create `GET /api/entity/{id}/connections` endpoint — related entities
- [ ] Add new QueryRunner methods: `search_entities()`, `get_entity_connections()`

**Frontend tasks**:
- [ ] Add search input with live-search (type and results appear)
- [ ] Display entity detail card when selected
- [ ] Display connected entities list with relationship types
- [ ] Clicking a connected entity navigates to its details

**Layout**:
```
Search: [FastAPI________]

┌──────────────────────────────────────────────┐
│  FastAPI                                     │
│  Type: Technology | Mentions: 31             │
│  First seen: 2026-01-15                      │
│  Last seen: 2026-03-01                       │
├──────────────────────────────────────────────┤
│  Connections:                                │
│  ──USES──→ Pydantic (Library, 18x)           │
│  ──USES──→ pytest (Technology, 42x)          │
│  ──DEPENDS_ON──→ Python (Technology, 28x)    │
│  ──SOLVES──→ API Design (Problem, 5x)        │
└──────────────────────────────────────────────┘
```

**Concepts explained**:
- **AJAX**: Updating part of a page without reloading the whole thing
- **Debounce**: Waiting a moment after typing before searching (to avoid too many API calls)
- **REST resource**: `/api/entity/{id}` — each entity has its own URL

---

## Phase 2: Chat Interface

### Step 5: Natural Language Chat

**Goal**: Chat with your knowledge graph in natural language

**What you'll learn**:
- WebSocket or polling for real-time communication
- Chat UI patterns
- Managing conversation state

**Backend tasks**:
- [ ] Create `POST /api/ask` endpoint — accepts question, returns answer + Cypher
- [ ] Connect to existing `NaturalLanguageQuerier`
- [ ] Return usage stats with each response

**Frontend tasks**:
- [ ] Build chat UI (message bubbles, input area)
- [ ] Send messages and display responses
- [ ] Show generated Cypher in collapsible section
- [ ] Show cost per query
- [ ] Maintain chat history in browser

**Layout**:
```
┌──────────────────────────────────────────────┐
│ 💬 Ask about your knowledge graph            │
├──────────────────────────────────────────────┤
│                                              │
│  You: FastAPI와 관련된 기술들은?                │
│                                              │
│  AI: FastAPI는 주로 다음 기술들과 함께          │
│      논의되었습니다:                            │
│      - Pydantic (18회)                        │
│      - pytest (15회)                          │
│      ▶ Show Cypher query                     │
│      Cost: $0.005                            │
│                                              │
├──────────────────────────────────────────────┤
│  [Type your question...            ] [Send]  │
└──────────────────────────────────────────────┘
```

---

## Phase 3: Polish (Future)

Ideas for later improvement:
- [ ] Node click in graph → entity detail panel
- [ ] Time range filter (last 7d / 30d / all)
- [ ] Relationship type filter on graph
- [ ] Export graph as image
- [ ] Dark mode toggle
- [ ] Deploy to cloud (Railway / Vercel)
- [ ] Mobile-responsive layout
- [ ] Real-time graph updates after new ingest

---

## Technical Decisions Log

| Decision | Choice | Reason | Date |
|----------|--------|--------|------|
| Backend framework | FastAPI | Learn web dev properly, Python-based | 2026-03-06 |
| Frontend | HTML + CSS + JS | Learn fundamentals from scratch | 2026-03-06 |
| Graph library | pyvis (reuse existing) | Already works, serve via iframe | 2026-03-06 |
| Deployment | localhost first | Simplest starting point | 2026-03-06 |
| NLQ engine | Existing kg ask (Claude Haiku) | Already built and tested | 2026-03-06 |

---

## Learning Path

Each step introduces new web concepts progressively:

| Step | Python (Backend) | Web (Frontend) |
|------|-----------------|----------------|
| 1 | FastAPI routes, uvicorn | HTML basics |
| 2 | REST API, JSON responses | CSS layout, JavaScript fetch() |
| 3 | Query parameters, dynamic content | iframe, event listeners |
| 4 | Path parameters, search | AJAX, dynamic DOM updates |
| 5 | POST requests, NLQ integration | Chat UI, session state |

---

## Dependencies to Add

```
fastapi >= 0.115.0
uvicorn >= 0.34.0
jinja2 >= 3.1.0    # HTML template rendering
```

---

Created: 2026-03-06
Updated: 2026-03-06
Status: PLANNED (not started)
