"""Tests for the dashboard FastAPI server."""

from __future__ import annotations

from starlette.testclient import TestClient

from claude_conversation_kg.dashboard.server import (
    app,
    get_nlq_querier,
    get_query_runner,
)


class MockQueryRunner:
    """Mock QueryRunner that returns deterministic data without a database."""

    def get_stats(self) -> dict:
        """Return mock graph statistics."""
        return {
            "total_entities": 100,
            "total_relationships": 200,
            "entities_by_type": {"Technology": 50, "Concept": 30, "Pattern": 20},
            "relationships_by_type": {"USES": 100, "RELATES_TO": 80, "DEPENDS_ON": 20},
        }

    def get_audit(self, limit: int = 10) -> dict:
        """Return mock audit data."""
        return {
            "total_entities": 100,
            "top_entities": [
                {"name": "Python", "type": "Technology", "mention_count": 42},
                {"name": "FastAPI", "type": "Technology", "mention_count": 35},
                {"name": "pytest", "type": "Technology", "mention_count": 28},
            ],
        }

    def search_entities(self, query: str, limit: int = 20) -> list[dict]:
        """Return mock search results filtered by query."""
        entities = [
            {"id": "1", "name": "Python", "type": "Technology", "mention_count": 42},
            {"id": "2", "name": "FastAPI", "type": "Library", "mention_count": 15},
            {"id": "3", "name": "pytest", "type": "Technology", "mention_count": 5},
        ]
        q = query.lower()
        return [e for e in entities if q in e["name"].lower()][:limit]

    def get_entity_connections(self, entity_id: str) -> dict | None:
        """Return mock entity connections."""
        entities = {
            "1": {
                "id": "1",
                "name": "Python",
                "type": "Technology",
                "mention_count": 42,
                "first_seen": "2026-01-15",
            },
        }
        if entity_id not in entities:
            return None
        return {
            "entity": entities[entity_id],
            "connections": [
                {
                    "direction": "outgoing",
                    "relationship": "USES",
                    "entity": {
                        "id": "2",
                        "name": "FastAPI",
                        "type": "Library",
                        "mention_count": 15,
                    },
                }
            ],
        }

    def execute(self, cypher: str) -> list[dict]:
        """Return mock entity and relationship data for graph queries.

        Simulates DB-level filtering by parsing WHERE clauses and LIMIT
        from the Cypher query string.
        """
        if "RETURN e.id, e.name, e.type, e.mention_count" in cypher:
            all_entities = [
                {
                    "e.id": "1",
                    "e.name": "Python",
                    "e.type": "Technology",
                    "e.mention_count": 42,
                },
                {
                    "e.id": "2",
                    "e.name": "FastAPI",
                    "e.type": "Library",
                    "e.mention_count": 15,
                },
                {
                    "e.id": "3",
                    "e.name": "pytest",
                    "e.type": "Technology",
                    "e.mention_count": 5,
                },
            ]
            result = all_entities

            # Simulate type filter
            if "e.type IN" in cypher:
                import re

                type_match = re.search(r"e\.type IN \[([^\]]+)\]", cypher)
                if type_match:
                    types = {
                        t.strip().strip("'") for t in type_match.group(1).split(",")
                    }
                    result = [e for e in result if e["e.type"] in types]

            # Simulate min_mentions filter
            if "e.mention_count >=" in cypher:
                import re

                mc_match = re.search(r"e\.mention_count >= (\d+)", cypher)
                if mc_match:
                    min_mc = int(mc_match.group(1))
                    result = [
                        e for e in result if (e["e.mention_count"] or 0) >= min_mc
                    ]

            # Simulate ORDER BY mention_count DESC (already sorted by default)
            result.sort(key=lambda e: e["e.mention_count"] or 0, reverse=True)

            # Simulate LIMIT
            if "LIMIT" in cypher:
                import re

                lim_match = re.search(r"LIMIT (\d+)", cypher)
                if lim_match:
                    result = result[: int(lim_match.group(1))]

            return result
        if "RETURN a.id, b.id" in cypher:
            return [{"a.id": "1", "b.id": "2"}]
        return []


def _override_runner() -> MockQueryRunner:
    return MockQueryRunner()


class MockNLQuerier:
    """Mock NaturalLanguageQuerier for testing the /api/ask endpoint."""

    def __init__(self) -> None:
        self.usage = type(
            "Usage",
            (),
            {
                "api_calls": 2,
                "input_tokens": 500,
                "output_tokens": 100,
                "estimated_cost_usd": 0.005,
            },
        )()

    def ask(self, question: str) -> tuple[str, str]:
        """Return deterministic Cypher and answer."""
        return (
            "MATCH (e:Entity) RETURN e.name LIMIT 5",
            "Here are some entities in your graph.",
        )


def _override_nlq() -> MockNLQuerier:
    return MockNLQuerier()


app.dependency_overrides[get_query_runner] = _override_runner
app.dependency_overrides[get_nlq_querier] = _override_nlq
client = TestClient(app)


class TestDashboardApp:
    """Tests for the FastAPI dashboard application."""

    def test_app_exists(self) -> None:
        """The FastAPI app instance should exist."""
        assert app is not None

    def test_root_route_exists(self) -> None:
        """GET / route should be registered on the app."""
        routes = [route.path for route in app.routes]
        assert "/" in routes

    def test_root_returns_200(self) -> None:
        """GET / should return HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_kg_dashboard(self) -> None:
        """GET / response should contain 'KG Dashboard' text."""
        response = client.get("/")
        assert "KG Dashboard" in response.text


class TestStatsAPI:
    """Tests for the GET /api/stats endpoint."""

    def test_stats_returns_200(self) -> None:
        """GET /api/stats should return HTTP 200."""
        response = client.get("/api/stats")
        assert response.status_code == 200

    def test_stats_returns_json(self) -> None:
        """GET /api/stats should return JSON content type."""
        response = client.get("/api/stats")
        assert response.headers["content-type"] == "application/json"

    def test_stats_has_expected_keys(self) -> None:
        """GET /api/stats response should contain all expected keys."""
        response = client.get("/api/stats")
        data = response.json()
        assert "total_entities" in data
        assert "total_relationships" in data
        assert "entities_by_type" in data

    def test_stats_values_match_mock(self) -> None:
        """GET /api/stats should return values from the mock runner."""
        response = client.get("/api/stats")
        data = response.json()
        assert data["total_entities"] == 100
        assert data["total_relationships"] == 200
        assert data["entities_by_type"]["Technology"] == 50


class TestAuditAPI:
    """Tests for the GET /api/audit endpoint."""

    def test_audit_returns_200(self) -> None:
        """GET /api/audit should return HTTP 200."""
        response = client.get("/api/audit")
        assert response.status_code == 200

    def test_audit_returns_json(self) -> None:
        """GET /api/audit should return JSON content type."""
        response = client.get("/api/audit")
        assert response.headers["content-type"] == "application/json"

    def test_audit_has_expected_keys(self) -> None:
        """GET /api/audit response should contain all expected keys."""
        response = client.get("/api/audit")
        data = response.json()
        assert "total_entities" in data
        assert "top_entities" in data

    def test_audit_top_entities_structure(self) -> None:
        """GET /api/audit top_entities should have correct structure."""
        response = client.get("/api/audit")
        data = response.json()
        top = data["top_entities"]
        assert len(top) == 3
        assert top[0]["name"] == "Python"
        assert top[0]["type"] == "Technology"
        assert top[0]["mention_count"] == 42

    def test_audit_accepts_limit_param(self) -> None:
        """GET /api/audit should accept a limit query parameter."""
        response = client.get("/api/audit?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "top_entities" in data


class TestSearchAPI:
    """Tests for the GET /api/search endpoint."""

    def test_search_returns_200(self) -> None:
        """GET /api/search?q=Python should return HTTP 200."""
        response = client.get("/api/search?q=Python")
        assert response.status_code == 200

    def test_search_returns_json_list(self) -> None:
        """GET /api/search?q=Python should return a JSON list."""
        response = client.get("/api/search?q=Python")
        data = response.json()
        assert isinstance(data, list)

    def test_search_results_have_required_keys(self) -> None:
        """GET /api/search results should have name, type, mention_count, id keys."""
        response = client.get("/api/search?q=Python")
        data = response.json()
        assert len(data) > 0
        item = data[0]
        assert "id" in item
        assert "name" in item
        assert "type" in item
        assert "mention_count" in item

    def test_search_filters_by_query(self) -> None:
        """GET /api/search?q=Fast should only return matching entities."""
        response = client.get("/api/search?q=Fast")
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "FastAPI"

    def test_search_case_insensitive(self) -> None:
        """GET /api/search?q=python should match Python (case-insensitive)."""
        response = client.get("/api/search?q=python")
        data = response.json()
        names = [e["name"] for e in data]
        assert "Python" in names

    def test_search_no_match_returns_empty(self) -> None:
        """GET /api/search?q=nonexistent should return empty list."""
        response = client.get("/api/search?q=nonexistent")
        data = response.json()
        assert data == []

    def test_search_missing_q_returns_422(self) -> None:
        """GET /api/search without q param should return 422."""
        response = client.get("/api/search")
        assert response.status_code == 422


class TestEntityConnectionsAPI:
    """Tests for the GET /api/entity/{id}/connections endpoint."""

    def test_connections_returns_200(self) -> None:
        """GET /api/entity/1/connections should return HTTP 200."""
        response = client.get("/api/entity/1/connections")
        assert response.status_code == 200

    def test_connections_has_entity_and_connections(self) -> None:
        """Response should have entity info and connections list."""
        response = client.get("/api/entity/1/connections")
        data = response.json()
        assert "entity" in data
        assert "connections" in data
        assert isinstance(data["connections"], list)

    def test_connections_entity_has_required_keys(self) -> None:
        """Entity in response should have id, name, type, mention_count, first_seen."""
        response = client.get("/api/entity/1/connections")
        data = response.json()
        entity = data["entity"]
        assert "id" in entity
        assert "name" in entity
        assert "type" in entity
        assert "mention_count" in entity
        assert "first_seen" in entity

    def test_connections_items_have_required_keys(self) -> None:
        """Each connection should have direction, relationship, entity keys."""
        response = client.get("/api/entity/1/connections")
        data = response.json()
        assert len(data["connections"]) > 0
        conn = data["connections"][0]
        assert "direction" in conn
        assert "relationship" in conn
        assert "entity" in conn

    def test_connections_nonexistent_returns_404(self) -> None:
        """GET /api/entity/nonexistent/connections should return 404."""
        response = client.get("/api/entity/nonexistent/connections")
        assert response.status_code == 404


class TestGraphDataAPI:
    """Tests for the GET /api/graph/data endpoint."""

    def test_graph_data_returns_200(self) -> None:
        """GET /api/graph/data should return 200 with JSON content."""
        response = client.get("/api/graph/data")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_graph_data_has_nodes_and_edges(self) -> None:
        """GET /api/graph/data response should contain nodes and edges keys."""
        response = client.get("/api/graph/data")
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_graph_data_node_keys(self) -> None:
        """Each node should have id, label, type, and mentions keys."""
        response = client.get("/api/graph/data")
        data = response.json()
        assert len(data["nodes"]) > 0
        node = data["nodes"][0]
        assert "id" in node
        assert "label" in node
        assert "type" in node
        assert "mentions" in node

    def test_graph_data_edge_keys(self) -> None:
        """Each edge should have from, to, and label keys."""
        response = client.get("/api/graph/data")
        data = response.json()
        assert len(data["edges"]) > 0
        edge = data["edges"][0]
        assert "from" in edge
        assert "to" in edge
        assert "label" in edge

    def test_graph_data_with_types_filter(self) -> None:
        """Filtering by types=Technology should only include Technology nodes."""
        response = client.get("/api/graph/data?types=Technology")
        assert response.status_code == 200
        data = response.json()
        node_names = [n["label"] for n in data["nodes"]]
        node_types = [n["type"] for n in data["nodes"]]
        # Python and pytest are Technology; FastAPI is Library
        assert "Python" in node_names
        assert "pytest" in node_names
        assert "FastAPI" not in node_names
        assert all(t == "Technology" for t in node_types)

    def test_graph_data_with_min_mentions_filter(self) -> None:
        """GET /api/graph/data?min_mentions=10 should exclude low-mention entities."""
        response = client.get("/api/graph/data?min_mentions=10")
        assert response.status_code == 200
        data = response.json()
        node_names = [n["label"] for n in data["nodes"]]
        # Python (42) and FastAPI (15) pass; pytest (5) should be excluded
        assert "Python" in node_names
        assert "FastAPI" in node_names
        assert "pytest" not in node_names

    def test_graph_data_with_combined_filters(self) -> None:
        """Combined type and min_mentions filters should apply both."""
        response = client.get("/api/graph/data?types=Technology&min_mentions=10")
        assert response.status_code == 200
        data = response.json()
        node_names = [n["label"] for n in data["nodes"]]
        # Only Python (Technology, 42) passes both filters
        assert "Python" in node_names
        assert "FastAPI" not in node_names
        assert "pytest" not in node_names

    def test_graph_data_limit_parameter(self) -> None:
        """GET /api/graph/data?limit=1 should limit the number of returned nodes."""
        response = client.get("/api/graph/data?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        # Should return the highest mention_count entity (Python, 42)
        assert data["nodes"][0]["label"] == "Python"

    def test_graph_data_default_limit(self) -> None:
        """GET /api/graph/data without limit should use default of 100."""
        response = client.get("/api/graph/data")
        assert response.status_code == 200
        data = response.json()
        # Mock has 3 entities, all should be returned (< 100 default limit)
        assert len(data["nodes"]) == 3


class TestAskAPI:
    """Tests for the POST /api/ask endpoint."""

    def test_ask_returns_200(self) -> None:
        """POST /api/ask with a valid question should return HTTP 200."""
        payload = {"question": "What technologies exist?"}
        response = client.post("/api/ask", json=payload)
        assert response.status_code == 200

    def test_ask_response_has_expected_keys(self) -> None:
        """POST /api/ask response should contain answer, cypher, usage keys."""
        payload = {"question": "What technologies exist?"}
        response = client.post("/api/ask", json=payload)
        data = response.json()
        assert "answer" in data
        assert "cypher" in data
        assert "usage" in data

    def test_ask_response_values(self) -> None:
        """POST /api/ask should return values from the mock querier."""
        payload = {"question": "What technologies exist?"}
        response = client.post("/api/ask", json=payload)
        data = response.json()
        assert data["answer"] == "Here are some entities in your graph."
        assert data["cypher"] == "MATCH (e:Entity) RETURN e.name LIMIT 5"
        assert data["usage"]["api_calls"] == 2
        assert data["usage"]["input_tokens"] == 500
        assert data["usage"]["output_tokens"] == 100
        assert data["usage"]["estimated_cost_usd"] == 0.005

    def test_ask_missing_question_returns_422(self) -> None:
        """POST /api/ask without question field should return 422."""
        response = client.post("/api/ask", json={})
        assert response.status_code == 422

    def test_ask_no_api_key_returns_503(self) -> None:
        """POST /api/ask when API key is missing should return 503."""
        app.dependency_overrides[get_nlq_querier] = lambda: None
        try:
            response = client.post(
                "/api/ask", json={"question": "What technologies exist?"}
            )
            assert response.status_code == 503
        finally:
            # Restore the mock override
            app.dependency_overrides[get_nlq_querier] = _override_nlq

    def test_ask_query_error_returns_200_with_error_flag(self) -> None:
        """POST /api/ask should return 200 with error=true on QueryError."""
        from claude_conversation_kg.exceptions import QueryError

        class ErrorNLQuerier:
            """Mock querier that raises QueryError."""

            def __init__(self) -> None:
                self.usage = type(
                    "Usage",
                    (),
                    {
                        "api_calls": 1,
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "estimated_cost_usd": 0.001,
                    },
                )()

            def ask(self, question: str) -> tuple[str, str]:
                raise QueryError("Failed to extract a valid Cypher query")

        app.dependency_overrides[get_nlq_querier] = lambda: ErrorNLQuerier()
        try:
            response = client.post(
                "/api/ask", json={"question": "some Korean question"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["error"] is True
            assert "Failed to extract" in data["answer"]
            assert data["cypher"] == ""
            assert "usage" in data
        finally:
            app.dependency_overrides[get_nlq_querier] = _override_nlq
