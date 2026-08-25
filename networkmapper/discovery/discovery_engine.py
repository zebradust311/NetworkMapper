from __future__ import annotations

from datetime import datetime
from typing import Iterable

from networkmapper.classification.classifier import DeviceClassifier
from networkmapper.core.models import Device
from networkmapper.core.network_graph import NetworkGraph
from networkmapper.discovery.enrichment_provider import EnrichmentProvider
from networkmapper.discovery.provider import DiscoveryProvider
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.runtime.events import (
    ProgressMeasurement,
    RuntimeEvent,
    RuntimeEventBus,
    RuntimeEventKind,
    RuntimePhase,
)


class DiscoveryEngine:
    """Coordinate multiple discovery providers and build a network graph."""

    def __init__(
        self,
        providers: Iterable[DiscoveryProvider],
        enrichment_providers: Iterable[EnrichmentProvider] = (),
        event_bus: RuntimeEventBus | None = None,
    ) -> None:
        """Initialize the engine with one or more discovery providers.

        Args:
            providers: The discovery providers to run, in order.
            enrichment_providers: ADR-010 enrichment providers to run, in
                order, against the already-discovered device set — after
                every `DiscoveryProvider` has run, before classification.
                Empty by default: an enrichment provider (e.g. SNMP) is
                only ever present here when its own prerequisites (e.g.
                credentials) were actually supplied, per ADR-010's
                "optional by construction" requirement.
            event_bus: OBS-002 runtime event bus. Defaults to a fresh,
                subscriber-less bus, so publishing is always a safe
                no-op when no caller wires one up.
        """
        self._providers = list(providers)
        self._enrichment_providers = list(enrichment_providers)
        self._classifier = DeviceClassifier()
        self._event_bus = event_bus if event_bus is not None else RuntimeEventBus()
        self.observations: list[IdentityObservation | RelationshipObservation] = []

    def discover(self) -> NetworkGraph:
        """Run discovery, then enrichment, then classification, and return the graph.

        Per ADR-010, this is a three-phase pipeline: every
        `DiscoveryProvider` runs first and builds the authoritative,
        IP-deduplicated device set; every `EnrichmentProvider` then adds
        evidence to that same set; classification is a distinct final
        phase over the result, published as its own OBS-002
        Classification phase, so a device is only ever classified after
        all discovery and enrichment it depends on has actually finished.

        FEAT-007A/ARCH-017 Stage 2: alongside this unchanged pipeline,
        `self.observations` collects every retained observation each
        provider optionally reports via `collect_observations()` — an
        additive side channel that never influences device construction,
        enrichment, or classification (Section 4, ARCH-017: the
        existing pipeline and the observation layer are decoupled).
        """
        graph = NetworkGraph()
        self.observations = []

        devices_by_ip: dict[str, Device] = {}
        for provider in self._providers:
            discovered_devices = provider.discover()
            self.observations.extend(provider.collect_observations())
            for device in discovered_devices:
                if isinstance(device, Device):
                    devices_by_ip.setdefault(device.ip_address, device)

        devices = list(devices_by_ip.values())

        for enrichment_provider in self._enrichment_providers:
            # ADR-010: an EnrichmentProvider must never raise for an
            # expected per-device failure, but this is the run-level
            # safety net for an unexpected one (a provider defect, not a
            # protocol-level failure) — it must degrade to "this provider
            # contributed nothing," never abort discovery for every
            # other provider and the devices already found. Observation
            # collection shares the same fallback: a provider defect
            # after enrich() has already mutated devices in place only
            # loses that provider's observations, never the evidence
            # already written to Device. ARCH-022/FEAT-011A:
            # receive_observations() shares this same safety net — a
            # defect there degrades to "this provider consulted nothing,"
            # never aborts the run, and provider ordering is never a
            # guaranteed dependency (ARCH-022 Section 7): a fresh,
            # immutable snapshot of self.observations is passed on every
            # iteration, so a provider simply sees less if an earlier
            # optional provider hasn't run or contributed nothing.
            try:
                enrichment_provider.receive_observations(tuple(self.observations))
                enrichment_provider.enrich(devices)
                self.observations.extend(enrichment_provider.collect_observations())
            except Exception:
                pass

        self._classify_devices(devices, graph)

        return graph

    def _classify_devices(self, devices: list[Device], graph: NetworkGraph) -> None:
        """Classify each device in order, publishing OBS-002 Classification
        phase events around and during the pass."""
        self._event_bus.publish(
            RuntimeEvent(
                phase=RuntimePhase.CLASSIFICATION,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime.now(),
                activity=f"Classifying {len(devices)} discovered device(s)...",
            )
        )

        for index, device in enumerate(devices, start=1):
            classified_device = self._classifier.classify(device)
            graph.add_device(classified_device)
            self._event_bus.publish(
                RuntimeEvent(
                    phase=RuntimePhase.CLASSIFICATION,
                    kind=RuntimeEventKind.PROGRESS,
                    timestamp=datetime.now(),
                    progress=ProgressMeasurement(
                        completed=index, unit_label="Devices Classified"
                    ),
                )
            )

        self._event_bus.publish(
            RuntimeEvent(
                phase=RuntimePhase.CLASSIFICATION,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime.now(),
                progress=ProgressMeasurement(
                    completed=len(devices), unit_label="Devices Classified"
                ),
            )
        )
