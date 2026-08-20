"""Canonical relationship domain model (ADR-013; ARCH-018 Stage 1; FEAT-009A).

Scope (FEAT-009A Stage 1): these are inert value objects produced by
`RelationshipResolver` (`networkmapper.relationships.resolver`). Nothing in
the existing pipeline constructs or consumes them yet — `Device`,
classification, reporting, and serialization are all unaffected by their
presence, the same posture `networkmapper.identity.models` already
established for canonical identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from networkmapper.observations.models import RelationshipObservation


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

    WEAK: exactly one independent source supports the claim.
    CONFIRMED: two or more independent sources agree on the same
        `related_subject` for the same subject/category.
    CONFLICTING: more than one distinct `related_subject` value is present
        among the group's retained observations. This does not require
        the disagreement to originate from two different independent
        sources — a single source's own internally inconsistent reports
        are sufficient on their own, mirroring
        `IdentityResolver._resolve_property()`'s identical, ungated
        behavior for identity properties exactly (ARCH-018's Confidence
        States finding). Per ADR-013, a conflict is retained and
        surfaced, never silently resolved by picking a winner.
    """

    WEAK = "weak"
    CONFIRMED = "confirmed"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class CanonicalRelationship:
    """One resolved interpretation of one subject's relationships in one
    category (ADR-013).

    `subject` and `category` together are the identity of this record —
    the direct structural analog of `PropertyCorroboration`'s
    `(subject, property_name)` grouping, with `related_subject` playing
    the role `value` plays there. There is no separate field holding "the"
    resolved `related_subject`: when `state` is `WEAK` or `CONFIRMED`,
    exactly one distinct `related_subject` value is present across
    `observations` and is recoverable from there; when `CONFLICTING`, more
    than one is present and none is privileged. This mirrors
    `PropertyCorroboration`'s identical absence of a collapsed value
    field — a consumer reads the value(s) from the retained observations,
    never from a field that would have to silently pick one during a
    conflict.

    Nothing rolls up above this record the way `CanonicalIdentity` rolls
    up several `PropertyCorroboration`s into one identity-level state:
    `connected_to` and `hosts_service` are independent claims about a
    subject, and conflating them would violate ADR-013's explainability
    requirement (a canonical relationship must be traceable to specific
    retained observations, never to an unrelated category's evidence).

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
        state: `WEAK`, `CONFIRMED`, or `CONFLICTING` for this
            subject/category pairing.
        observations: Every retained observation contributing to this
            `(subject, category)` group, preserved in full — never
            collapsed to a single resolved value. Sorted deterministically
            (provider, collection method, related_subject) so this field
            never depends on input order.
    """

    subject: str
    category: str
    state: RelationshipCorroborationState
    observations: tuple[RelationshipObservation, ...]
