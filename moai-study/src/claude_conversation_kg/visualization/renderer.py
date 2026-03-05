"""HTML graph visualization renderer."""

from __future__ import annotations

import logging
import math
from pathlib import Path

from pyvis.network import Network

from claude_conversation_kg.extractor.models import RelationshipType
from claude_conversation_kg.graph.queries import QueryRunner
from claude_conversation_kg.visualization.styles import DEFAULT_COLOR, ENTITY_COLORS

logger = logging.getLogger(__name__)


class GraphRenderer:
    """Generate interactive HTML graph visualizations using pyvis."""

    # Node size range (pixels): min=10 for rarely-mentioned, max=60 for hot topics
    _MIN_NODE_SIZE = 10
    _MAX_NODE_SIZE = 60

    @classmethod
    def _mention_count_to_size(cls, mention_count: int) -> int:
        """Map mention_count to a node size within [MIN, MAX].

        Uses a logarithmic scale so that moderate counts are visible
        without letting extremely frequent entities dominate the layout.
        """
        if mention_count <= 0:
            return cls._MIN_NODE_SIZE
        raw = cls._MIN_NODE_SIZE + int(math.log1p(mention_count) * 8)
        return min(raw, cls._MAX_NODE_SIZE)

    def render(self, query_runner: QueryRunner, output_path: Path) -> None:
        """Render the graph to an HTML file.

        Nodes are color-coded by entity type and sized by mention_count.
        Edges are labeled by relationship type.
        """
        net = Network(height="100vh", width="100%", directed=True)

        # Fetch all entities including mention_count for node sizing
        entities = query_runner.execute(
            "MATCH (e:Entity) RETURN e.id, e.name, e.type, e.mention_count"
        )
        for entity in entities:
            eid = entity["e.id"]
            name = entity["e.name"]
            etype = entity["e.type"]
            mention_count = entity.get("e.mention_count") or 1
            color = ENTITY_COLORS.get(etype, DEFAULT_COLOR)
            size = self._mention_count_to_size(mention_count)
            net.add_node(
                eid,
                label=name,
                color=color,
                size=size,
                title=f"{name} ({etype}) — mentioned {mention_count}x",
            )

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
