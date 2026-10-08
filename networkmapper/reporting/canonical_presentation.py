"""Canonical identity/relationship presentation view-model (PLAN-025 Slice 1).

Projects `Project.canonical_identities` and `Project.canonical_relationships`
(ADR-012, ADR-013) into technician-legible records for `MarkdownExporter`
(and, later, any additional renderer), without re-resolving, reinterpreting,
or recomputing anything the resolvers already concluded. Sibling to
`ProjectSummary` (`networkmapper.reporting.project_summary`) — same
"derive reusable data, then let exporters render it" pattern, scoped to
per-entity canonical detail rather than aggregate counts.

Read-only and side-effect free throughout:

- Iterates `project.canonical_identities` / `project.canonical_relationships`
  directly as its primary axis (never `project.network_graph.all_devices()`
  — ARCH-025 Section 6/7).
- Reads `CanonicalIdentity.state` / `PropertyCorroboration.state` /
  `CanonicalRelationship.state` / `CanonicalRelationship.cardinality` as
  authoritative and never recomputes them.
- Never collapses a `CONFLICTING` group to one value — every distinct value
  (identity) or distinct `related_subject` (relationship) is preserved.
- Relationships arrive from the resolver as one record per edge (ADR-013
  Amendment 1); they are regrouped by `(subject, category)` for display only
  (PLAN-028 D4), each related subject keeping its own edge's state.
- Uses `NetworkGraph.get_device(ip_address)` only as optional, read-only
  enrichment; a lookup miss falls back to the raw subject string, never
  drops the record and never invents a placeholder `Device`.
- Never imports or calls `IdentityResolver` / `RelationshipResolver`.

See `docs/plans/PLAN-025-Canonical-Identity-Relationship-Presentation-Implementation.md`
Sections 3-5 for the exact contract this module implements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from networkmapper.core.models import Device
from networkmapper.identity.models import CanonicalIdentity, IdentityCorroborationState
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.project.models import Project
from networkmapper.relationships.categories import RelationshipCardinality
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState

# PLAN-025 Section 4, item 3 / architect-review correction: a category label
# describes the canonical category itself, never the evidence provider
# currently producing it — "connected_to" is deliberately unlabeled with any
# protocol suffix (LLDP today; a future CDP provider would corroborate the
# same canonical category, not a different one). Provider/collection-method
# provenance remains available on each rendered observation instead.
_CATEGORY_LABELS: dict[str, str] = {
    "arp_neighbor": "ARP Neighbor",
    "connected_to": "Connected To",
    "bridge_fdb": "Bridge Forwarding Entry",
}


def _category_label(category: str) -> str:
    """Return the known friendly label for `category`, or a deterministic
    title-cased fallback for any category absent from the mapping — so a
    future relationship category renders with zero code changes."""
    return _CATEGORY_LABELS.get(category, category.replace("_", " ").title())


@dataclass(frozen=True)
class PropertyValuePresentation:
    """One distinct observed value for an identity property, grouped with
    every observation that reported it.

    Grouping observations by their already-decided `value` is purely a
    display convenience over data `PropertyCorroboration.observations`
    already contains in full (PLAN-025 Section 4, item 2) — it introduces
    no new value and never picks a "winner" among distinct values.
    """

    value: str
    observations: tuple[IdentityObservation, ...]


@dataclass(frozen=True)
class IdentityPropertyPresentation:
    """One property's corroboration state and its distinct observed value(s),
    read directly from `PropertyCorroboration` — never recomputed."""

    property_name: str
    state: IdentityCorroborationState
    values: tuple[PropertyValuePresentation, ...]


@dataclass(frozen=True)
class IdentityPresentation:
    """One `CanonicalIdentity`, enriched with an optional matching `Device`.

    `device` is `None` whenever `subject` does not match any device in
    `NetworkGraph` — this is never treated as a reason to omit the record;
    `subject` itself remains renderable regardless.
    """

    subject: str
    state: IdentityCorroborationState
    device: Optional[Device]
    properties: tuple[IdentityPropertyPresentation, ...]


@dataclass(frozen=True)
class RelatedSubjectPresentation:
    """One edge's related subject: its own `CanonicalRelationship.state`
    (copied, never recomputed), every observation supporting that edge, and
    an optional matching `Device` the same way `IdentityPresentation.device`
    is enriched."""

    related_subject: str
    device: Optional[Device]
    state: RelationshipCorroborationState
    observations: tuple[RelationshipObservation, ...]


@dataclass(frozen=True)
class RelationshipPresentation:
    """Every canonical relationship edge sharing one `(subject, category)`,
    grouped for display, enriched with an optional matching `Device` for
    `subject`, plus a deterministic friendly `category_label`.

    There is no group-level state (PLAN-028 D4): each entry in `related`
    carries its own edge's state. `cardinality` is the category's
    resolver-owned cardinality, read from the edges, never looked up here.
    A `SINGLE` category with more than one entry is a conflict, and every
    entry is then `CONFLICTING`; a `MULTIPLE` category may list any number
    of entries, none of them conflicting.
    """

    subject: str
    device: Optional[Device]
    category: str
    category_label: str
    cardinality: RelationshipCardinality
    related: tuple[RelatedSubjectPresentation, ...]


@dataclass(frozen=True)
class CanonicalPresentation:
    """The full projection of one `Project`'s canonical identities and
    relationships, ready for a renderer to format.

    Construct only via `from_project()` — this type takes no other inputs
    and performs no resolution of its own.
    """

    identities: tuple[IdentityPresentation, ...]
    relationships: tuple[RelationshipPresentation, ...]

    @classmethod
    def from_project(cls, project: Project) -> CanonicalPresentation:
        """Project `project.canonical_identities` / `canonical_relationships`
        into presentation records.

        Reads only `project.canonical_identities`, `project.canonical_relationships`,
        and `project.network_graph.get_device()` (for enrichment) — never
        `project.observations` directly, and never `network_graph.all_devices()`.
        """
        return cls(
            identities=tuple(
                _present_identity(identity, project) for identity in project.canonical_identities
            ),
            relationships=_present_relationships(project.canonical_relationships, project),
        )


def _present_identity(identity: CanonicalIdentity, project: Project) -> IdentityPresentation:
    properties = tuple(
        IdentityPropertyPresentation(
            property_name=property_corroboration.property_name,
            state=property_corroboration.state,
            values=_group_property_values(property_corroboration.observations),
        )
        for property_corroboration in identity.properties
    )

    return IdentityPresentation(
        subject=identity.subject,
        state=identity.state,
        device=project.network_graph.get_device(identity.subject),
        properties=properties,
    )


def _group_property_values(
    observations: tuple[IdentityObservation, ...],
) -> tuple[PropertyValuePresentation, ...]:
    """Group observations by their distinct `value`, preserving the
    resolver's own deterministic observation order (first-seen order, not
    re-sorted) — never introducing a new order dependency."""
    observations_by_value: dict[str, list[IdentityObservation]] = {}
    for observation in observations:
        observations_by_value.setdefault(observation.value, []).append(observation)

    return tuple(
        PropertyValuePresentation(value=value, observations=tuple(value_observations))
        for value, value_observations in observations_by_value.items()
    )


def _present_relationships(
    relationships: tuple[CanonicalRelationship, ...], project: Project
) -> tuple[RelationshipPresentation, ...]:
    """Group edges by their shared `(subject, category)` into one
    `RelationshipPresentation` each. Groups appear in the order their first
    edge appears, and edges within a group keep their input order, so the
    resolver's deterministic `(subject, category, related_subject)` sort is
    preserved. No state is recomputed; each edge's state is copied onto its
    entry."""
    edges_by_group: dict[tuple[str, str], list[CanonicalRelationship]] = {}
    for relationship in relationships:
        edges_by_group.setdefault((relationship.subject, relationship.category), []).append(relationship)

    return tuple(
        _present_relationship_group(subject, category, edges, project)
        for (subject, category), edges in edges_by_group.items()
    )


def _present_relationship_group(
    subject: str, category: str, edges: list[CanonicalRelationship], project: Project
) -> RelationshipPresentation:
    # Cardinality belongs to the category, so every edge sharing
    # (subject, category) must agree. The resolver guarantees this; anything
    # else is inconsistent input and is rejected rather than resolved by
    # silently picking one edge's value.
    cardinalities = {edge.cardinality for edge in edges}
    if len(cardinalities) != 1:
        raise ValueError(
            f"Relationship edges for subject {subject!r} and category {category!r} "
            f"have inconsistent cardinality: {sorted(c.value for c in cardinalities)}."
        )
    (cardinality,) = cardinalities

    return RelationshipPresentation(
        subject=subject,
        device=project.network_graph.get_device(subject),
        category=category,
        category_label=_category_label(category),
        cardinality=cardinality,
        related=tuple(
            RelatedSubjectPresentation(
                related_subject=edge.related_subject,
                device=project.network_graph.get_device(edge.related_subject),
                state=edge.state,
                observations=edge.observations,
            )
            for edge in edges
        ),
    )
