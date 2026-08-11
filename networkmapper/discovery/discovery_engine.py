from __future__ import annotations

from datetime import datetime
from typing import Iterable

from networkmapper.classification.classifier import DeviceClassifier
from networkmapper.core.models import Device
from networkmapper.core.network_graph import NetworkGraph
from networkmapper.discovery.provider import DiscoveryProvider
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
        event_bus: RuntimeEventBus | None = None,
    ) -> None:
        """Initialize the engine with one or more discovery providers.

        Args:
            providers: The discovery providers to run, in order.
            event_bus: OBS-002 runtime event bus. Defaults to a fresh,
                subscriber-less bus, so publishing is always a safe
                no-op when no caller wires one up.
        """
        self._providers = list(providers)
        self._classifier = DeviceClassifier()
        self._event_bus = event_bus if event_bus is not None else RuntimeEventBus()

    def discover(self) -> NetworkGraph:
        """Run each provider, classify discovered devices, and return the graph.

        Discovery (and, for `NmapProvider`, enrichment) is run for every
        provider first; classification is then a distinct phase over the
        combined result, published as its own OBS-002 Classification
        phase, so a device is only ever classified after all discovery
        it depends on has actually finished.
        """
        graph = NetworkGraph()

        all_devices: list[Device] = []
        for provider in self._providers:
            discovered_devices = provider.discover()
            all_devices.extend(
                device for device in discovered_devices if isinstance(device, Device)
            )

        self._classify_devices(all_devices, graph)

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
