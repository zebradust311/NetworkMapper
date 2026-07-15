from __future__ import annotations

from typing import Iterable

from networkmapper.classification.classifier import DeviceClassifier
from networkmapper.core.models import Device
from networkmapper.core.network_graph import NetworkGraph
from networkmapper.discovery.provider import DiscoveryProvider


class DiscoveryEngine:
    """Coordinate multiple discovery providers and build a network graph."""

    def __init__(self, providers: Iterable[DiscoveryProvider]) -> None:
        """Initialize the engine with one or more discovery providers."""
        self._providers = list(providers)
        self._classifier = DeviceClassifier()

    def discover(self) -> NetworkGraph:
        """Run each provider, classify discovered devices, and return the graph."""
        graph = NetworkGraph()

        for provider in self._providers:
            discovered_devices = provider.discover()
            for device in discovered_devices:
                if isinstance(device, Device):
                    classified_device = self._classifier.classify(device)
                    graph.add_device(classified_device)

        return graph
