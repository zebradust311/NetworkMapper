"""Canonical relationship resolution (ADR-013; ARCH-018 Stage 1; FEAT-009A).

Inert and unwired: nothing in the existing discovery, classification,
reporting, or persistence pipeline calls `RelationshipResolver` yet.
"""

from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState
from networkmapper.relationships.resolver import RelationshipResolver

__all__ = [
    "CanonicalRelationship",
    "RelationshipCorroborationState",
    "RelationshipResolver",
]
