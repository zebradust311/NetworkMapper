from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from networkmapper.core.models import Device


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
