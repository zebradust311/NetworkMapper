"""MAC-to-subject reverse index (ARCH-022; FEAT-011A).

Not identity resolution: this runs before `IdentityResolver.resolve()`
has produced anything and returns raw `subject` references, never
`CanonicalIdentity` objects — ARCH-022 Section 3 found the codebase's own
"resolution" vocabulary is reserved for the corroboration-producing
concept ADR-012/013 define, and named this mechanism accordingly.
"""

from __future__ import annotations

from collections.abc import Sequence

from networkmapper.observations.models import IdentityObservation, RelationshipObservation

_MAC_ADDRESS_PROPERTY = "mac_address"


def build_mac_index(
    observations: Sequence[IdentityObservation | RelationshipObservation],
) -> dict[str, frozenset[str]]:
    """Return every observed MAC mapped to the complete set of distinct
    subjects that claimed it.

    Never collapses a conflict into ordinary absence (ARCH-022 Section
    5): a MAC claimed by more than one subject returns a `frozenset` of
    every one of them, not an arbitrarily picked value — a caller reads
    the set's size to distinguish no evidence (key absent), a resolved
    match (`len == 1`), and a conflict (`len > 1`), mirroring
    `CanonicalRelationship`'s identical refusal to silently arbitrate a
    conflict at the point of resolution.

    Never mutates `observations`, never touches `Device`, `NetworkGraph`,
    classification, reporting, or persistence — a pure function over its
    one input, exactly like `IdentityResolver.resolve()`. Deterministic
    and order-independent: `frozenset` equality does not depend on
    insertion order, so the same observations in any order produce an
    equal result, without needing the explicit sort step
    `IdentityResolver`/`RelationshipResolver` use to guarantee the same
    property.
    """
    subjects_by_mac: dict[str, set[str]] = {}

    for observation in observations:
        if not isinstance(observation, IdentityObservation):
            continue
        if observation.property_name != _MAC_ADDRESS_PROPERTY:
            continue

        subjects_by_mac.setdefault(observation.value, set()).add(observation.subject)

    return {mac: frozenset(subjects) for mac, subjects in subjects_by_mac.items()}
