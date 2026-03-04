"""Tests for extraction models -- RED phase."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from claude_conversation_kg.extractor.models import (
    Entity,
    EntityType,
    ExtractionResult,
    Relationship,
    RelationshipType,
)


class TestEntity:
    """Specification tests for Entity model."""

    def test_entity_valid(self) -> None:
        """Valid name, type, description creates an Entity."""
        entity = Entity(
            name="FastAPI",
            type=EntityType.TECHNOLOGY,
            description="A modern Python web framework",
        )
        assert entity.name == "FastAPI"
        assert entity.type == EntityType.TECHNOLOGY
        assert entity.description == "A modern Python web framework"
        assert entity.confidence == 1.0
        assert entity.id  # auto-generated, non-empty

    def test_entity_type_must_be_valid(self) -> None:
        """Invalid entity type raises ValidationError."""
        with pytest.raises(ValidationError):
            Entity(name="X", type="InvalidType", description="test")  # type: ignore[arg-type]

    def test_entity_id_auto_generated(self) -> None:
        """Entity id is auto-generated from name and type."""
        e1 = Entity(name="FastAPI", type=EntityType.TECHNOLOGY)
        e2 = Entity(name="FastAPI", type=EntityType.LIBRARY)
        assert e1.id != e2.id  # Different type = different id
        e3 = Entity(name="FastAPI", type=EntityType.TECHNOLOGY)
        assert e1.id == e3.id  # Same name+type = same id


class TestRelationship:
    """Specification tests for Relationship model."""

    def test_relationship_valid(self) -> None:
        """Valid source, target, type creates a Relationship."""
        rel = Relationship(
            source_id="fastapi-technology",
            target_id="sqlalchemy-library",
            type=RelationshipType.USES,
            context="FastAPI uses SQLAlchemy for ORM",
        )
        assert rel.source_id == "fastapi-technology"
        assert rel.target_id == "sqlalchemy-library"
        assert rel.type == RelationshipType.USES
        assert rel.confidence == 0.8

    def test_relationship_type_must_be_valid(self) -> None:
        """Invalid relationship type raises ValidationError."""
        with pytest.raises(ValidationError):
            Relationship(
                source_id="a",
                target_id="b",
                type="INVALID_TYPE",  # type: ignore[arg-type]
            )


class TestExtractionResult:
    """Specification tests for ExtractionResult model."""

    def test_extraction_result_holds_both(self) -> None:
        """ExtractionResult holds entities and relationships."""
        entity = Entity(name="FastAPI", type=EntityType.TECHNOLOGY)
        rel = Relationship(
            source_id=entity.id,
            target_id="pg-technology",
            type=RelationshipType.USES,
        )
        result = ExtractionResult(entities=[entity], relationships=[rel])
        assert len(result.entities) == 1
        assert len(result.relationships) == 1

    def test_extraction_result_defaults_empty(self) -> None:
        """ExtractionResult defaults to empty lists."""
        result = ExtractionResult()
        assert result.entities == []
        assert result.relationships == []
