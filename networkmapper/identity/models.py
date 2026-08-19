"""Canonical identity domain model (ADR-012; ARCH-017 Stage 3; FEAT-008A).

Scope (FEAT-008A / ARCH-017 Stage 1 of identity resolution): these are
inert value objects produced by `IdentityResolver`
(`networkmapper.identity.resolver`). Nothing in the existing pipeline
constructs or consumes them yet — `Device`, classification, reporting,
and serialization are all unaffected by their presence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from networkmapper.observations.models import IdentityObservation


class IdentityCorroborationState(StrEnum):
    """A discrete, explainable corroboration state — never a numeric score.

    ADR-012's Corroboration section names this exact shape (weak,
    probable, confirmed, conflicting) as an illustration ARCH-015
    Section 7 first proposed, explicitly without freezing it as final.
    FEAT-008A is the first concrete resolver and adopts it here.

    WEAK: exactly one independent source supports the fact in question.
    PROBABLE: identity-level only (see `CanonicalIdentity`) — breadth of
        evidence across multiple properties without depth on any one.
    CONFIRMED: two or more independent sources agree.
    CONFLICTING: two or more independent sources disagree. Per ADR-012,
        a conflict is retained and surfaced, never silently resolved by
        picking a winner.
    """

    WEAK = "weak"
    PROBABLE = "probable"
    CONFIRMED = "confirmed"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class PropertyCorroboration:
    """The corroboration outcome for one identity-bearing property of one subject.

    Never `PROBABLE` — that state describes breadth across a subject's
    properties (see `CanonicalIdentity.state`), not the depth of
    evidence behind any single property.

    Attributes:
        property_name: Which property was observed (e.g. "hostname").
        state: `WEAK`, `CONFIRMED`, or `CONFLICTING` for this property
            alone.
        observations: Every retained observation contributing to this
            property, preserved in full — never collapsed to a single
            resolved value, per ADR-011/ADR-012's explainability
            requirement. Sorted deterministically (provider, collection
            method, value) so this field never depends on input order.
    """

    property_name: str
    state: IdentityCorroborationState
    observations: tuple[IdentityObservation, ...]


@dataclass(frozen=True)
class CanonicalIdentity:
    """One resolved, deterministic interpretation of a subject's identity (ADR-012).

    `CanonicalIdentity` is never itself an observation and is never
    constructed directly from a single field's presence — it is always
    the output of `IdentityResolver.resolve()` evaluating a subject's
    full retained observation set.

    Attributes:
        subject: The raw discovery-time reference this identity was
            resolved for (today, an IP address — see
            `networkmapper.identity.resolver` for why this is a
            practical grouping key, not a claim about canonical
            identity semantics).
        state: The identity-level corroboration state, rolled up from
            every property's own `PropertyCorroboration.state`:
            `CONFLICTING` if any property conflicts, else `CONFIRMED` if
            any property is independently confirmed, else `PROBABLE` if
            more than one property has at least weak support, else
            `WEAK`.
        properties: Per-property corroboration detail, sorted
            deterministically by `property_name` so this field never
            depends on input order.
    """

    subject: str
    state: IdentityCorroborationState
    properties: tuple[PropertyCorroboration, ...]
