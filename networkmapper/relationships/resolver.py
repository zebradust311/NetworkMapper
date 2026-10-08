"""Canonical relationship resolver (ADR-013 and its Amendment 1; ARCH-018;
FEAT-009A; PLAN-028).

`RelationshipResolver` is a pure function from retained observations and
canonical identities to canonical relationships. `Application.run()` calls
it once per run (FEAT-009B); it never touches `Device`, `NetworkGraph`,
classification, reporting, or persistence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from networkmapper.identity.models import CanonicalIdentity
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.relationships.categories import (
    CATEGORY_CARDINALITY,
    RelationshipCardinality,
    cardinality_for,
)
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState


class RelationshipResolver:
    """Derives canonical relationships from retained observations and
    canonical identities (ADR-013, as amended by Amendment 1).

    Consumes only `RelationshipObservation`s from whatever mixed
    observation collection it is given (e.g. `Project.observations`); any
    `IdentityObservation` present is ignored, not an error — mirroring
    exactly how `IdentityResolver` already ignores `RelationshipObservation`s
    it is handed. `identities` is `IdentityResolver.resolve()`'s own
    output: this resolver cannot run before identity resolution has, per
    ADR-012's "Relationship with Future ADRs" section naming canonical
    identity a prerequisite for relationship resolution.

    Relationship endpoints are canonical identities (ADR-013's
    Relationship Endpoints section), never raw provider references. A
    `RelationshipObservation` whose `subject` or `related_subject` does
    not resolve to a supplied identity is real, retained evidence that
    simply does not resolve to a canonical relationship this run — it is
    excluded, not erased; it remains exactly where it already was, in
    whatever collection was passed in as `observations`.

    Evaluation key versus output identity (ADR-013 Amendment 1, Decision
    3). Observations are *evaluated* together by `(subject, category)`, so
    that a single-valued category can see more than one distinct
    `related_subject` and report the conflict; grouping by the full
    `(subject, category, related_subject)` triple would make that conflict
    structurally undetectable (ARCH-018). The canonical *output* identity,
    however, is the edge `(subject, category, related_subject)`: one
    `CanonicalRelationship` is emitted per distinct related subject.

    Cardinality (ADR-013 Amendment 1, Decisions 1-2) comes from the
    resolver-owned category policy (`networkmapper.relationships.categories`),
    never from providers or observations:
    - Each edge's independent sources are the distinct
      `(provider, collection_method)` pairs among that edge's own
      observations. One source is `WEAK`; two or more are `CONFIRMED`.
    - `SINGLE`: if the group holds more than one distinct `related_subject`,
      every edge in the group is `CONFLICTING`, regardless of how well any
      one edge is corroborated. This preserves the pre-amendment
      corroboration semantics; only the output shape changed.
    - `MULTIPLE` (and any unregistered category): several related subjects
      are normal, so `CONFLICTING` is never produced.

    Preprocessing (endpoint resolution, unresolved-endpoint exclusion,
    self-loop exclusion) always runs before grouping, never after. This
    ordering is required, not stylistic: a self-loop artifact or an
    unresolved-endpoint observation sharing a subject and category with a
    genuine observation would otherwise add a spurious `related_subject` to
    the group — producing a false `CONFLICTING` for a single-valued
    category. Excluding such observations before any group exists avoids
    this by construction.

    Every category is grouped exactly as reported; `(subject,
    related_subject)` ordering is not canonicalized for symmetric
    categories (e.g. "connected_to" reported from either endpoint). This
    is a known, accepted limitation — a symmetric link reported from both
    ends produces two independent `WEAK` edges rather than one `CONFIRMED`
    one — never a false conflict, since the two directions are separate
    `(subject, category)` groups.

    Deterministic and order-independent: `resolve()` produces identical
    output regardless of either input sequence's order. Output records are
    sorted by `(subject, category, related_subject)`. Observations within
    each record are sorted by `(provider, collection_method,
    related_subject, source_run, observed_at.isoformat())` (PLAN-028 D6).
    `related_subject` is constant within an edge but kept so the key is
    self-documenting. The timestamp is compared through its ISO string so
    the sort is total even if naive and timezone-aware datetimes were ever
    mixed. Observations identical in every sorted field are equal by value,
    so their relative order is not significant: the output is deterministic
    by value, not by object identity.
    """

    def __init__(
        self,
        cardinality_policy: Mapping[str, RelationshipCardinality] | None = None,
    ) -> None:
        """Create a resolver.

        Args:
            cardinality_policy: Category-to-cardinality policy. Defaults to
                the module policy (`CATEGORY_CARDINALITY`). Production code
                never passes one; it exists so tests can exercise
                `SINGLE` semantics before any production category is
                single-valued (PLAN-028 D1).
        """
        self._cardinality_policy = (
            CATEGORY_CARDINALITY if cardinality_policy is None else cardinality_policy
        )

    def resolve(
        self,
        observations: Sequence[IdentityObservation | RelationshipObservation],
        identities: Sequence[CanonicalIdentity],
    ) -> tuple[CanonicalRelationship, ...]:
        """Return one canonical relationship per distinct, resolvable
        `(subject, category, related_subject)` edge observed.

        Never mutates its inputs, never touches `Device`, `NetworkGraph`,
        classification, reporting, or persistence.
        """
        relationship_observations = [
            observation for observation in observations if isinstance(observation, RelationshipObservation)
        ]

        # Order-independent membership test, not a subject -> identity
        # lookup: only whether an endpoint resolves matters, never the
        # CanonicalIdentity object itself (CanonicalRelationship stores
        # subject as a plain str). A dict keyed by subject would be
        # order-dependent under a pathological duplicate-subject input
        # (last write wins), violating the determinism guarantee above; a
        # frozenset has no such failure mode.
        valid_subjects = frozenset(identity.subject for identity in identities)

        preprocessed_observations = [
            observation
            for observation in relationship_observations
            if observation.subject in valid_subjects
            and observation.related_subject in valid_subjects
            and observation.subject != observation.related_subject
        ]

        observations_by_group: dict[tuple[str, str], list[RelationshipObservation]] = {}
        for observation in preprocessed_observations:
            group_key = (observation.subject, observation.category)
            observations_by_group.setdefault(group_key, []).append(observation)

        relationships = [
            relationship
            for (subject, category), group_observations in observations_by_group.items()
            for relationship in self._resolve_group(subject, category, group_observations)
        ]

        return tuple(
            sorted(
                relationships,
                key=lambda relationship: (
                    relationship.subject,
                    relationship.category,
                    relationship.related_subject,
                ),
            )
        )

    def _resolve_group(
        self, subject: str, category: str, observations: list[RelationshipObservation]
    ) -> list[CanonicalRelationship]:
        """Resolve one `(subject, category)` group into one edge per
        distinct `related_subject`.

        Independence is judged per edge by (provider, collection_method),
        per ADR-013's Relationship Independence section — two observations
        sharing both are the same underlying claim and must not count as
        two confirmations.
        """
        cardinality = cardinality_for(category, self._cardinality_policy)

        observations_by_edge: dict[str, list[RelationshipObservation]] = {}
        for observation in observations:
            observations_by_edge.setdefault(observation.related_subject, []).append(observation)

        group_conflicts = (
            cardinality == RelationshipCardinality.SINGLE and len(observations_by_edge) > 1
        )

        relationships: list[CanonicalRelationship] = []
        for related_subject, edge_observations in observations_by_edge.items():
            independent_sources = {
                (observation.provenance.provider, observation.provenance.collection_method)
                for observation in edge_observations
            }

            if group_conflicts:
                state = RelationshipCorroborationState.CONFLICTING
            elif len(independent_sources) >= 2:
                state = RelationshipCorroborationState.CONFIRMED
            else:
                state = RelationshipCorroborationState.WEAK

            relationships.append(
                CanonicalRelationship(
                    subject=subject,
                    category=category,
                    related_subject=related_subject,
                    cardinality=cardinality,
                    state=state,
                    observations=tuple(sorted(edge_observations, key=_edge_observation_sort_key)),
                )
            )

        return relationships


def _edge_observation_sort_key(
    observation: RelationshipObservation,
) -> tuple[str, str, str, str, str]:
    """Total, deterministic order for one edge's observations (PLAN-028 D6).

    The timestamp is compared through its ISO string, never as a
    `datetime`, so mixed naive/aware values can't raise `TypeError`.
    """
    return (
        observation.provenance.provider,
        observation.provenance.collection_method,
        observation.related_subject,
        observation.provenance.source_run,
        observation.provenance.observed_at.isoformat(),
    )
