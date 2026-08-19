"""Canonical identity resolver (ADR-012; ARCH-017 Stage 3; FEAT-008A).

`IdentityResolver` is a pure function from retained observations to
canonical identities. It is not wired into `DiscoveryEngine`,
`Application`, classification, reporting, or persistence — nothing in
the existing pipeline calls it. It exists as standalone, inert,
independently testable code, per this sprint's explicit scope.
"""

from __future__ import annotations

from collections.abc import Sequence

from networkmapper.identity.models import (
    CanonicalIdentity,
    IdentityCorroborationState,
    PropertyCorroboration,
)
from networkmapper.observations.models import IdentityObservation, RelationshipObservation


class IdentityResolver:
    """Derives canonical identities from retained `IdentityObservation`s (ADR-012).

    Stage 1 scoping (ARCH-017 Stage 3 / this sprint): groups observations
    by `subject` only. This is a practical starting grouping key, not a
    claim that `subject` (today, an IP address) *is* canonical identity
    — ADR-012 explicitly rejects "Use IP address as canonical identity"
    as an alternative. Recognizing two different subject values as the
    same real-world device (cross-subject correlation via matching
    hardware-intrinsic evidence, once such evidence exists) is out of
    this stage's scope and remains genuinely unsolved, consistent with
    ARCH-015's own finding that stable device identity is a harder,
    still-open problem.

    Consumes only `IdentityObservation`s from whatever mixed observation
    collection it is given (e.g. `Project.observations`); any
    `RelationshipObservation` present is ignored, not an error —
    relationship resolution is ADR-013's own future work, gated on this
    resolver existing (ADR-013's "Relationship with Future ADRs").

    Deterministic and order-independent, per ADR-012's Identity
    Principles: `resolve()` produces byte-identical output regardless of
    the input sequence's order, by grouping into sets/dicts and then
    explicitly sorting every output collection rather than relying on
    incidental input or iteration order.
    """

    def resolve(
        self,
        observations: Sequence[IdentityObservation | RelationshipObservation],
    ) -> tuple[CanonicalIdentity, ...]:
        """Return one canonical identity per distinct subject observed.

        Never mutates its input, never touches `Device`, classification,
        reporting, or persistence.
        """
        identity_observations = [
            observation for observation in observations if isinstance(observation, IdentityObservation)
        ]

        observations_by_subject: dict[str, list[IdentityObservation]] = {}
        for observation in identity_observations:
            observations_by_subject.setdefault(observation.subject, []).append(observation)

        identities = [
            self._resolve_subject(subject, subject_observations)
            for subject, subject_observations in observations_by_subject.items()
        ]

        return tuple(sorted(identities, key=lambda identity: identity.subject))

    def _resolve_subject(
        self, subject: str, observations: list[IdentityObservation]
    ) -> CanonicalIdentity:
        observations_by_property: dict[str, list[IdentityObservation]] = {}
        for observation in observations:
            observations_by_property.setdefault(observation.property_name, []).append(observation)

        properties = tuple(
            sorted(
                (
                    self._resolve_property(property_name, property_observations)
                    for property_name, property_observations in observations_by_property.items()
                ),
                key=lambda property_corroboration: property_corroboration.property_name,
            )
        )

        return CanonicalIdentity(
            subject=subject,
            state=self._roll_up_identity_state(properties),
            properties=properties,
        )

    def _resolve_property(
        self, property_name: str, observations: list[IdentityObservation]
    ) -> PropertyCorroboration:
        """Determine one property's corroboration state.

        Independence is judged by (provider, collection_method), per
        ADR-012's Observation Independence section — two observations
        sharing both are the same underlying claim and must not count as
        two confirmations, even if they happen to disagree.
        """
        values_by_independent_source: dict[tuple[str, str], set[str]] = {}
        for observation in observations:
            source_key = (observation.provenance.provider, observation.provenance.collection_method)
            values_by_independent_source.setdefault(source_key, set()).add(observation.value)

        distinct_values = {
            value for values in values_by_independent_source.values() for value in values
        }
        independent_source_count = len(values_by_independent_source)

        if len(distinct_values) > 1:
            state = IdentityCorroborationState.CONFLICTING
        elif independent_source_count >= 2:
            state = IdentityCorroborationState.CONFIRMED
        else:
            state = IdentityCorroborationState.WEAK

        sorted_observations = tuple(
            sorted(
                observations,
                key=lambda observation: (
                    observation.provenance.provider,
                    observation.provenance.collection_method,
                    observation.value,
                ),
            )
        )

        return PropertyCorroboration(
            property_name=property_name,
            state=state,
            observations=sorted_observations,
        )

    def _roll_up_identity_state(
        self, properties: tuple[PropertyCorroboration, ...]
    ) -> IdentityCorroborationState:
        """Roll up per-property states into one identity-level state.

        A conflict on any single property is significant enough to mark
        the whole identity CONFLICTING — per ADR-012, a conflict must
        never be silently hidden behind other, agreeing evidence.
        """
        if any(
            property_corroboration.state == IdentityCorroborationState.CONFLICTING
            for property_corroboration in properties
        ):
            return IdentityCorroborationState.CONFLICTING

        if any(
            property_corroboration.state == IdentityCorroborationState.CONFIRMED
            for property_corroboration in properties
        ):
            return IdentityCorroborationState.CONFIRMED

        if len(properties) >= 2:
            return IdentityCorroborationState.PROBABLE

        return IdentityCorroborationState.WEAK
