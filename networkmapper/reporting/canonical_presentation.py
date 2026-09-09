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
  `CanonicalRelationship.state` as authoritative and never recomputes them.
- Never collapses a `CONFLICTING` group to one value — every distinct value
  (identity) or distinct `related_subject` (relationship) is preserved.
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
    """One distinct `related_subject` claimed under a `CanonicalRelationship`,
    grouped with every observation that reported it, and enriched with an
    optional matching `Device` the same way `IdentityPresentation.device` is."""

    related_subject: str
    device: Optional[Device]
    observations: tuple[RelationshipObservation, ...]


@dataclass(frozen=True)
class RelationshipPresentation:
    """One `CanonicalRelationship`, enriched with an optional matching
    `Device` for `subject`, plus a deterministic friendly `category_label`.

    `related` holds every distinct `related_subject` the group's
    observations report — exactly one for `WEAK`/`CONFIRMED`, more than one
    for `CONFLICTING` (never collapsed to a single value).
    """

    subject: str
    device: Optional[Device]
    category: str
    category_label: str
    state: RelationshipCorroborationState
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
            relationships=tuple(
                _present_relationship(relationship, project)
                for relationship in project.canonical_relationships
            ),
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


def _present_relationship(
    relationship: CanonicalRelationship, project: Project
) -> RelationshipPresentation:
    return RelationshipPresentation(
        subject=relationship.subject,
        device=project.network_graph.get_device(relationship.subject),
        category=relationship.category,
        category_label=_category_label(relationship.category),
        state=relationship.state,
        related=_group_related_subjects(relationship.observations, project),
    )


def _group_related_subjects(
    observations: tuple[RelationshipObservation, ...], project: Project
) -> tuple[RelatedSubjectPresentation, ...]:
    """Group observations by their distinct `related_subject`, preserving
    the resolver's own deterministic observation order, and enrich each
    distinct related subject with an optional matching `Device`."""
    observations_by_related_subject: dict[str, list[RelationshipObservation]] = {}
    for observation in observations:
        observations_by_related_subject.setdefault(observation.related_subject, []).append(observation)

    return tuple(
        RelatedSubjectPresentation(
            related_subject=related_subject,
            device=project.network_graph.get_device(related_subject),
            observations=tuple(related_observations),
        )
        for related_subject, related_observations in observations_by_related_subject.items()
    )
