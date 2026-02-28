"""HTML graph visualization renderer."""
from __future__ import annotations

import logging
from pathlib import Path

from pyvis.network import Network

from claude_conversation_kg.extractor.models import RelationshipType
from claude_conversation_kg.graph.queries import QueryRunner
from claude_conversation_kg.visualization.styles import DEFAULT_COLOR, ENTITY_COLORS

logger = logging.getLogger(__name__)


class GraphRenderer:
    """Generate interactive HTML graph visualizations using pyvis."""

    def render(self, query_runner: QueryRunner, output_path: Path) -> None:
        """Render the graph to an HTML file.

        Nodes are color-coded by entity type.
        Edges are labeled by relationship type.
        """
        net = Network(height="750px", width="100%", directed=True)

        # Fetch all entities
        entities = query_runner.execute(
            "MATCH (e:Entity) RETURN e.id, e.name, e.type"
        )
        for entity in entities:
            eid = entity["e.id"]
            name = entity["e.name"]
            etype = entity["e.type"]
            color = ENTITY_COLORS.get(etype, DEFAULT_COLOR)
            net.add_node(eid, label=name, color=color, title=f"{name} ({etype})")

        # Fetch all relationships
        for rel_type in RelationshipType:
            try:
                rels = query_runner.execute(
                    f"MATCH (a:Entity)-[r:{rel_type.value}]->(b:Entity) "
                    f"RETURN a.id, b.id"
                )
                for rel in rels:
                    net.add_edge(
                        rel["a.id"],
                        rel["b.id"],
                        label=rel_type.value,
                        title=rel_type.value,
                    )
            except Exception:  # noqa: BLE001
                logger.debug("No %s relationships found", rel_type.value)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        net.save_graph(str(output_path))
        logger.info("Graph visualization saved to %s", output_path)
