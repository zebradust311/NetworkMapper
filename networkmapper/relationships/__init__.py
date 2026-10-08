"""Canonical relationship resolution (ADR-013 and its Amendment 1; ARCH-018;
FEAT-009A; PLAN-028).

`Application.run()` calls `RelationshipResolver` once per run (FEAT-009B).
Category cardinality is resolver-owned (`categories`), never provider-owned.
"""

from networkmapper.relationships.categories import (
    CATEGORY_CARDINALITY,
    DEFAULT_CARDINALITY,
    RelationshipCardinality,
    cardinality_for,
)
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState
from networkmapper.relationships.resolver import RelationshipResolver

__all__ = [
    "CATEGORY_CARDINALITY",
    "CanonicalRelationship",
    "DEFAULT_CARDINALITY",
    "RelationshipCardinality",
    "RelationshipCorroborationState",
    "RelationshipResolver",
    "cardinality_for",
]
