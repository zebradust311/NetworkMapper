"""Retained observation domain model (ADR-011, ADR-012, ADR-013; ARCH-017 Stage 1).

Naming, resolved (ADR-011 "Existing Observation Naming Collision"):
`networkmapper.knowledge.models.Observation` already exists and is a
distinct, narrower concept — a whole-device, episodic snapshot captured
only for `DeviceType.UNKNOWN` devices, built from already-collapsed
`Device` state, for human review (KNOW-003). The types in this module
are per-claim, provider-originated, and retained independently of
classification outcome — the concept ADR-011 formalized as the shared
foundation for identity resolution (ADR-012) and relationship resolution
(ADR-013). Per ADR-011's explicit instruction, that collision is
resolved here by naming, not by reuse: neither type below is named
`Observation`, and neither extends or wraps
`networkmapper.knowledge.models.Observation`. The two concepts remain
deliberately distinct.

Scope (ARCH-017 Stage 1): these are inert value objects. Nothing in the
codebase constructs or consumes them yet — no provider emits them, no
resolver reads them, nothing persists them. Existing discovery,
classification, serialization, and reporting behavior is unchanged by
their presence.
"""

from __future__ import annotations

from dataclasses import dataclass

from networkmapper.observations.provenance import ObservationProvenance


@dataclass(frozen=True)
class IdentityObservation:
    """One retained, immutable claim about a single subject's identity-bearing property.

    Represents one direct observation contributed by an evidence source
    — e.g. a chassis serial, a MAC address, a reported hostname —
    retained as evidence for a future identity resolver (ADR-012). An
    `IdentityObservation` is never itself a canonical identity; per
    ADR-012, canonical identity is an interpretation a future resolver
    derives from a corroborated set of observations like this one.

    Attributes:
        subject: A raw, discovery-time reference to what was observed
            (e.g. an IP address at observation time) — not a resolved
            canonical identity. No identity resolver exists yet
            (ARCH-017 Stage 1 scope); the resolver that eventually
            consumes this type is what establishes canonical identity
            from observations, not the reverse.
        property_name: Which identity-bearing property was observed
            (e.g. "mac_address", "chassis_serial", "hostname").
            Deliberately a free-text field rather than an enumerated
            taxonomy — ADR-012's Identity Categories section explicitly
            declines to freeze one, since ARCH-015 found stability is
            often conditional on device role or lifecycle event rather
            than fixed per field.
        value: The observed value of that property.
        provenance: Per-ADR-011, the provenance this observation was
            collected under.
    """

    subject: str
    property_name: str
    value: str
    provenance: ObservationProvenance


@dataclass(frozen=True)
class RelationshipObservation:
    """One retained, immutable claim that two subjects are related.

    Represents one direct observation that two subjects appear related
    in some way — e.g. "connected to," "hosts service" — retained as
    evidence for a future relationship resolver (ADR-013). A
    `RelationshipObservation` is never itself a canonical relationship;
    per ADR-013, a canonical relationship is an interpretation a future
    resolver derives from a corroborated set of observations like this
    one, and only once both endpoints resolve to canonical identities.

    Attributes:
        subject: A raw, discovery-time reference to one endpoint (e.g.
            an IP address) — not a resolved canonical identity.
        related_subject: A raw, discovery-time reference to the other
            endpoint. Per ADR-013's Relationship Endpoints section, an
            observation's endpoints are not required to already resolve
            to canonical identities — a canonical *relationship* is,
            but the retained *observation* may exist ahead of that
            resolution (e.g. an LLDP neighbor not yet independently
            discovered).
        category: The kind of relationship observed (e.g.
            "connected_to", "hosts_service", "routes_through").
            Deliberately a free-text field rather than an enumerated
            taxonomy — ADR-013's Relationship Categories section
            explicitly declines to freeze an implementation taxonomy
            beyond what ARCH-014 justified, since categories were found
            to vary sharply in how ready they are for corroboration.
        provenance: Per-ADR-011, the provenance this observation was
            collected under.
    """

    subject: str
    related_subject: str
    category: str
    provenance: ObservationProvenance
