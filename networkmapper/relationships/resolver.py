"""Canonical relationship resolver (ADR-013; ARCH-018 Stage 1; FEAT-009A).

`RelationshipResolver` is a pure function from retained observations and
canonical identities to canonical relationships. It is not wired into
`DiscoveryEngine`, `Application`, classification, reporting, or
persistence — nothing in the existing pipeline calls it. It exists as
standalone, inert, independently testable code, per this sprint's explicit
scope, the same posture `IdentityResolver` already established.
"""

from __future__ import annotations

from collections.abc import Sequence

from networkmapper.identity.models import CanonicalIdentity
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState


class RelationshipResolver:
    """Derives canonical relationships from retained observations and
    canonical identities (ADR-013).

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

    Groups by `(subject, category)`, not the naive `(subject,
    related_subject, category)` triple: `RelationshipObservation` carries
    no `value` field two observations can disagree about the way
    `IdentityObservation.value` does — `subject`, `related_subject`, and
    `category` together are the claim, not a value under a claim. Grouping
    by the full triple would put every observation sharing that triple in
    the same group by construction, making conflicting evidence (e.g. LLDP
    and CDP naming different neighbors for the same local claim)
    structurally undetectable. Grouping by `(subject, category)` instead,
    with `related_subject` as the value under evaluation, restores the
    identical independent-source-counting mechanism `IdentityResolver`
    already uses for identity properties.

    Preprocessing (endpoint resolution, unresolved-endpoint exclusion,
    self-loop exclusion) always runs before Grouping, never after. This
    ordering is required, not stylistic: because the grouping key does not
    include `related_subject`, a self-loop artifact or an
    unresolved-endpoint observation sharing a subject and category with a
    genuine observation would otherwise present more than one distinct
    `related_subject` value under the group's corroboration count —
    incorrectly producing `CONFLICTING` for a relationship that has only
    one genuine, single-source claim behind it. Excluding such
    observations before any group exists avoids this by construction.

    Stage 1 does not canonicalize `(subject, related_subject)` ordering
    for symmetric categories (e.g. "connected_to" reported from either
    endpoint): every category is grouped exactly as reported. This is a
    known, accepted limitation — a symmetric category's evidence produces
    two independent, non-corroborating `WEAK` relationships rather than
    one `CONFIRMED` one — never a false conflict, since the two directions
    land in separate `(subject, category)` groups rather than colliding.

    Deterministic and order-independent: `resolve()` produces
    byte-identical output regardless of either input sequence's order, by
    grouping into sets/dicts and then explicitly sorting every output
    collection rather than relying on incidental input or iteration order.
    """

    def resolve(
        self,
        observations: Sequence[IdentityObservation | RelationshipObservation],
        identities: Sequence[CanonicalIdentity],
    ) -> tuple[CanonicalRelationship, ...]:
        """Return one canonical relationship per distinct, resolvable
        `(subject, category)` pairing observed.

        Never mutates its inputs, never touches `Device`, `NetworkGraph`,
        classification, reporting, or persistence.
        """
        relationship_observations = [
            observation for observation in observations if isinstance(observation, RelationshipObservation)
        ]

        # Order-independent membership test, not a subject -> identity
        # lookup: Stage 1 only needs to know whether an endpoint resolves,
        # never the CanonicalIdentity object itself (CanonicalRelationship
        # stores subject as a plain str). A dict keyed by subject would be
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
            self._resolve_group(subject, category, group_observations)
            for (subject, category), group_observations in observations_by_group.items()
        ]

        return tuple(
            sorted(relationships, key=lambda relationship: (relationship.subject, relationship.category))
        )

    def _resolve_group(
        self, subject: str, category: str, observations: list[RelationshipObservation]
    ) -> CanonicalRelationship:
        """Determine one `(subject, category)` group's corroboration state.

        Independence is judged by (provider, collection_method), per
        ADR-013's Relationship Independence section — two observations
        sharing both are the same underlying claim and must not count as
        two confirmations, even if they happen to disagree.
        """
        values_by_independent_source: dict[tuple[str, str], set[str]] = {}
        for observation in observations:
            source_key = (observation.provenance.provider, observation.provenance.collection_method)
            values_by_independent_source.setdefault(source_key, set()).add(observation.related_subject)

        distinct_values = {
            value for values in values_by_independent_source.values() for value in values
        }
        independent_source_count = len(values_by_independent_source)

        if len(distinct_values) > 1:
            state = RelationshipCorroborationState.CONFLICTING
        elif independent_source_count >= 2:
            state = RelationshipCorroborationState.CONFIRMED
        else:
            state = RelationshipCorroborationState.WEAK

        sorted_observations = tuple(
            sorted(
                observations,
                key=lambda observation: (
                    observation.provenance.provider,
                    observation.provenance.collection_method,
                    observation.related_subject,
                ),
            )
        )

        return CanonicalRelationship(
            subject=subject,
            category=category,
            state=state,
            observations=sorted_observations,
        )
