"""Canonical relationship domain model (ADR-013 and its Amendment 1; ARCH-018;
FEAT-009A; PLAN-028).

These are immutable value objects produced by `RelationshipResolver`
(`networkmapper.relationships.resolver`). `Device`, classification, and
serialization are unaffected by their presence, the same posture
`networkmapper.identity.models` already established for canonical identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from networkmapper.observations.models import RelationshipObservation
from networkmapper.relationships.categories import RelationshipCardinality


class RelationshipCorroborationState(StrEnum):
    """A discrete, explainable corroboration state — never a numeric score.

    Mirrors `IdentityCorroborationState`
    (`networkmapper.identity.models`), with one deliberate omission:
    there is no `PROBABLE` analog. `PROBABLE` exists for identity because
    a subject's several distinct properties (hostname, domain,
    computer_name) can each be individually weak yet jointly increase
    confidence in the same subject's identity. A relationship has no
    equivalent breadth dimension — `connected_to` and `hosts_service` are
    unrelated claims about a subject, and one being weakly observed says
    nothing about the other's truth, so no rollup across categories is
    introduced here.

    WEAK: exactly one independent source supports this edge.
    CONFIRMED: two or more independent sources support this edge.
    CONFLICTING: single-valued categories only (ADR-013 Amendment 1,
        Decision 2). More than one distinct `related_subject` is claimed
        for the same `(subject, category)`, so every competing edge carries
        this state. This does not require the disagreement to originate
        from two different independent sources — a single source's own
        internally inconsistent reports are sufficient on their own,
        mirroring `IdentityResolver._resolve_property()`'s identical,
        ungated behavior for identity properties (ARCH-018's Confidence
        States finding). Per ADR-013, a conflict is retained and surfaced,
        never silently resolved by picking a winner. A multi-valued
        category never produces this state: several related subjects are
        its normal condition, not a disagreement.
    """

    WEAK = "weak"
    CONFIRMED = "confirmed"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class CanonicalRelationship:
    """One canonical relationship: a single edge from `subject` to
    `related_subject` in one `category` (ADR-013 Amendment 1, Decision 3).

    The record's identity is `(subject, category, related_subject)`. That is
    the canonical *output* identity; the resolver still *evaluates*
    observations together by `(subject, category)` so that a conflict in a
    single-valued category stays detectable. For a single-valued conflict,
    each competing related subject is its own record, every one marked
    `CONFLICTING`, and the conflict is explained by the set of records
    sharing `(subject, category)` — never by picking one of them.

    Nothing rolls up above this record the way `CanonicalIdentity` rolls
    up several `PropertyCorroboration`s into one identity-level state:
    `connected_to` and `hosts_service` are independent claims about a
    subject, and conflating them would violate ADR-013's explainability
    requirement (a canonical relationship must be traceable to specific
    retained observations, never to an unrelated category's evidence).

    Invariants (PLAN-028 D3), enforced at construction:
    - `CONFLICTING` is only valid when `cardinality` is `SINGLE`.
    - `observations` is never empty.
    - Every observation's `subject`, `category`, and `related_subject`
      match this record's.

    Attributes:
        subject: The raw discovery-time reference (today, an IP address)
            this relationship's evidence was observed for — the same
            reference `CanonicalIdentity.subject` uses, not a claim about
            canonical identity semantics beyond what `IdentityResolver`
            itself already makes.
        category: Which kind of relationship was observed (e.g.
            "connected_to", "hosts_service"). Deliberately a free-text
            field rather than an enumerated taxonomy, per ADR-013's own
            refusal to freeze one.
        related_subject: The other endpoint of this edge, in the same raw
            reference namespace as `subject`.
        cardinality: The resolver-owned cardinality of `category`
            (`networkmapper.relationships.categories`), carried on every
            record so consumers never consult the policy themselves.
        state: `WEAK`, `CONFIRMED`, or (single-valued categories only)
            `CONFLICTING` for this edge.
        observations: Every retained observation supporting this edge,
            preserved in full. Sorted deterministically by
            `(provider, collection_method, related_subject, source_run,
            observed_at)` — see `RelationshipResolver` — so this field never
            depends on input order.
    """

    subject: str
    category: str
    related_subject: str
    cardinality: RelationshipCardinality
    state: RelationshipCorroborationState
    observations: tuple[RelationshipObservation, ...]

    def __post_init__(self) -> None:
        if (
            self.state == RelationshipCorroborationState.CONFLICTING
            and self.cardinality != RelationshipCardinality.SINGLE
        ):
            raise ValueError(
                "CONFLICTING is only valid for SINGLE-cardinality categories "
                f"(category {self.category!r} is {self.cardinality.value})."
            )
        if not self.observations:
            raise ValueError("A canonical relationship requires at least one supporting observation.")
        for observation in self.observations:
            if (
                observation.subject != self.subject
                or observation.category != self.category
                or observation.related_subject != self.related_subject
            ):
                raise ValueError(
                    "Every supporting observation must match the relationship's "
                    "subject, category, and related_subject."
                )
