"""FastAPI server for the KG Dashboard."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from claude_conversation_kg.config import Settings
from claude_conversation_kg.exceptions import QueryError
from claude_conversation_kg.extractor.models import RelationshipType
from claude_conversation_kg.graph.connection import KuzuConnection
from claude_conversation_kg.graph.queries import QueryRunner
from claude_conversation_kg.graph.schema import initialize_schema
from claude_conversation_kg.nlq import NaturalLanguageQuerier

logger = logging.getLogger(__name__)

_SAFE_TYPE_RE = re.compile(r"^[A-Za-z0-9_ ]+$")

app = FastAPI(title="KG Dashboard")

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


class AskRequest(BaseModel):
    """Request body for the /api/ask endpoint."""

    question: str


def get_query_runner() -> QueryRunner:
    """Dependency that provides a QueryRunner instance."""
    settings = Settings()
    conn = KuzuConnection(settings.db_path)
    initialize_schema(conn.conn)
    return QueryRunner(conn.conn)


def get_nlq_querier() -> NaturalLanguageQuerier | None:
    """Dependency that provides a NaturalLanguageQuerier instance."""
    settings = Settings()
    if not settings.anthropic_api_key:
        return None
    conn = KuzuConnection(settings.db_path)
    initialize_schema(conn.conn)
    return NaturalLanguageQuerier(api_key=settings.anthropic_api_key, conn=conn.conn)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main dashboard page."""
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/stats")
async def api_stats(runner: QueryRunner = Depends(get_query_runner)) -> dict:
    """Return graph statistics."""
    return runner.get_stats()


@app.get("/api/audit")
async def api_audit(
    runner: QueryRunner = Depends(get_query_runner),
    limit: int = 10,
) -> dict:
    """Return top entities by mention count."""
    return runner.get_audit(limit=limit)


def _build_graph_data(
    runner: QueryRunner,
    type_filter: set[str] | None = None,
    min_mentions: int = 0,
    limit: int = 0,
    since_days: int = 0,
) -> dict:
    """Build filtered graph data as JSON-serialisable nodes and edges.

    Filtering is done via Cypher WHERE clauses so the DB handles the
    heavy lifting instead of fetching all entities into Python.
    When limit is 0, all matching entities are returned.
    When since_days > 0, only entities first seen within the
    last N days are included.
    """
    # Build WHERE clause with validated inline values
    conditions: list[str] = []
    if type_filter:
        # Validate type names to prevent Cypher injection.
        safe_types = {t for t in type_filter if _SAFE_TYPE_RE.match(t)}
        if safe_types:
            quoted = ", ".join(f"'{t}'" for t in safe_types)
            conditions.append(f"e.type IN [{quoted}]")
    if min_mentions > 0:
        conditions.append(f"e.mention_count >= {min_mentions}")
    if since_days > 0:
        since = datetime.now(tz=UTC) - timedelta(days=since_days)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")
        conditions.append(f"e.first_seen >= timestamp('{since_str}')")

    where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_sql = f" LIMIT {limit}" if limit > 0 else ""

    entity_query = (
        f"MATCH (e:Entity){where_sql} "
        f"RETURN e.id, e.name, e.type, e.mention_count "
        f"ORDER BY e.mention_count DESC{limit_sql}"
    )
    entities = runner.execute(entity_query)

    valid_ids: set[str] = {e["e.id"] for e in entities}

    nodes: list[dict] = []
    for e in entities:
        raw_count = e.get("e.mention_count")
        mention_count = raw_count if raw_count is not None else 1
        nodes.append(
            {
                "id": e["e.id"],
                "label": e["e.name"],
                "type": e["e.type"],
                "mentions": mention_count,
            }
        )

    # Fetch edges -- only keep those between valid nodes
    edges: list[dict] = []
    for rel_type in RelationshipType:
        try:
            rels = runner.execute(
                f"MATCH (a:Entity)-[r:{rel_type.value}]->(b:Entity) RETURN a.id, b.id"
            )
            for rel in rels:
                if rel["a.id"] in valid_ids and rel["b.id"] in valid_ids:
                    edges.append(
                        {
                            "from": rel["a.id"],
                            "to": rel["b.id"],
                            "label": rel_type.value,
                        }
                    )
        except Exception:  # noqa: BLE001
            logger.debug("No %s relationships found", rel_type.value)

    return {"nodes": nodes, "edges": edges}


@app.get("/api/search")
async def api_search(
    q: str,
    runner: QueryRunner = Depends(get_query_runner),
    limit: int = 20,
) -> list[dict]:
    """Search entities by name."""
    return runner.search_entities(q, limit=limit)


@app.get("/api/entity/{entity_id}/connections")
async def api_entity_connections(
    entity_id: str,
    runner: QueryRunner = Depends(get_query_runner),
) -> dict:
    """Get entity details and connections."""
    result = runner.get_entity_connections(entity_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return result


@app.get("/api/graph/data")
async def api_graph_data(
    runner: QueryRunner = Depends(get_query_runner),
    types: str | None = None,
    min_mentions: int = 0,
    limit: int = 0,
    since_days: int = 0,
) -> dict:
    """Return filtered graph data as JSON nodes and edges.

    Limit=0 means all. since_days=0 means no time filter.
    """
    type_filter = set(types.split(",")) if types else None
    return _build_graph_data(
        runner,
        type_filter=type_filter,
        min_mentions=min_mentions,
        limit=limit,
        since_days=since_days,
    )


@app.post("/api/ask")
async def api_ask(
    body: AskRequest,
    querier: NaturalLanguageQuerier | None = Depends(get_nlq_querier),
) -> dict:
    """Ask a natural language question about the knowledge graph."""
    if querier is None:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY is not configured",
        )

    try:
        cypher, answer = querier.ask(body.question)
    except QueryError as e:
        # Return error as a normal response so the chat UI shows it nicely.
        return {
            "answer": str(e),
            "cypher": "",
            "usage": {
                "api_calls": querier.usage.api_calls,
                "input_tokens": querier.usage.input_tokens,
                "output_tokens": querier.usage.output_tokens,
                "estimated_cost_usd": querier.usage.estimated_cost_usd,
            },
            "error": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    usage = querier.usage
    return {
        "answer": answer,
        "cypher": cypher,
        "usage": {
            "api_calls": usage.api_calls,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "estimated_cost_usd": usage.estimated_cost_usd,
        },
    }


# Static files mount MUST come after all route definitions
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
