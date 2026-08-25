from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from networkmapper.core.models import Device
from networkmapper.observations.models import IdentityObservation, RelationshipObservation


class EnrichmentProvider(ABC):
    """Adds evidence to already-discovered devices; never discovers them.

    ADR-010: structurally distinct from `DiscoveryProvider`. An
    `EnrichmentProvider` receives the device set `DiscoveryEngine` has
    already assembled from every registered `DiscoveryProvider` and adds
    evidence to it in place — it never introduces a `Device` for an IP
    not already present, and never removes one.
    """

    @abstractmethod
    def enrich(self, devices: Sequence[Device]) -> None:
        """Add evidence to devices in place.

        Implementations must never raise for an expected per-device
        failure (a timeout, a malformed response, a missing credential)
        — such a failure must be recorded as per-device diagnostics and
        must not stop enrichment of the remaining devices.
        """
        raise NotImplementedError

    def collect_observations(self) -> list[IdentityObservation | RelationshipObservation]:
        """Return retained observations gathered during the most recent enrich() call.

        FEAT-007A/ARCH-017 Stage 2: additive and optional, the same
        default as `DiscoveryProvider.collect_observations()`. Never
        influences `enrich()`'s own effect on any `Device`.
        """
        return []

    def receive_observations(
        self, observations: tuple[IdentityObservation | RelationshipObservation, ...]
    ) -> None:
        """Receive an immutable snapshot of observations collected so far
        this run (ARCH-022; FEAT-011A).

        Optional and additive, the same no-op-by-default pattern
        `collect_observations()` already establishes. `DiscoveryEngine`
        calls this immediately before `enrich()`, with a fresh snapshot
        reflecting whatever has been collected up to that point — never a
        live, mutable reference.

        Provider ordering is not a guaranteed dependency mechanism
        (ARCH-022 Section 7): a provider must remain correct when this
        snapshot lacks evidence another optional provider would have
        contributed had it run first — absence may reduce coverage, never
        correctness.
        """
        return None
