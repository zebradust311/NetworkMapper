"""Resolver-owned relationship category cardinality (ADR-013 Amendment 1).

Cardinality is part of the *interpretation* of a relationship category, so
it lives here in the relationship-resolution layer — never on a provider and
never on a `RelationshipObservation`. Providers keep emitting free-text
`category` strings exactly as before; this table only says how many related
subjects one subject may legitimately have in each category.

Keyed by string literals on purpose (PLAN-028 D2): importing the providers'
`*_CATEGORY` constants here would make the interpretation layer depend on
the discovery layer. The policy-completeness test in
`tests/test_relationship_resolver.py` cross-checks the two instead.

`default_gateway` is deliberately absent: ADR-013 Amendment 1 forbids
registering it before a provider for it exists.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType


class RelationshipCardinality(StrEnum):
    """How many related subjects one subject may have in a category.

    SINGLE: at most one related subject per `(subject, category)` — more
        than one distinct related subject is a conflict.
    MULTIPLE: any number of related subjects per `(subject, category)` is
        normal — several related subjects are never a conflict.
    """

    SINGLE = "single"
    MULTIPLE = "multiple"


CATEGORY_CARDINALITY: Mapping[str, RelationshipCardinality] = MappingProxyType(
    {
        "arp_neighbor": RelationshipCardinality.MULTIPLE,
        "bridge_fdb": RelationshipCardinality.MULTIPLE,
        "connected_to": RelationshipCardinality.MULTIPLE,
    }
)

# An unregistered category can never manufacture a conflict (ADR-013
# Amendment 1, Decision 1).
DEFAULT_CARDINALITY = RelationshipCardinality.MULTIPLE


def cardinality_for(
    category: str,
    policy: Mapping[str, RelationshipCardinality] = CATEGORY_CARDINALITY,
) -> RelationshipCardinality:
    """Return `category`'s cardinality under `policy`, or
    `DEFAULT_CARDINALITY` when the category is not registered."""
    return policy.get(category, DEFAULT_CARDINALITY)
