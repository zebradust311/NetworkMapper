import unittest

from networkmapper.core.models import Device, DeviceType
from networkmapper.discovery.discovery_engine import DiscoveryEngine
from networkmapper.discovery.enrichment_provider import EnrichmentProvider
from networkmapper.discovery.provider import DiscoveryProvider
from networkmapper.runtime.events import RuntimeEvent, RuntimeEventBus, RuntimeEventKind, RuntimePhase


class _StubProvider(DiscoveryProvider):
    def __init__(self, devices: list[Device]) -> None:
        self._devices = devices

    def discover(self) -> list[Device]:
        return self._devices


class _StubEnrichmentProvider(EnrichmentProvider):
    def __init__(self, evidence_by_ip: dict[str, str] | None = None, raises: bool = False) -> None:
        self._evidence_by_ip = evidence_by_ip or {}
        self._raises = raises
        self.seen_ips: list[str] = []

    def enrich(self, devices) -> None:
        if self._raises:
            raise RuntimeError("enrichment provider defect")

        for device in devices:
            self.seen_ips.append(device.ip_address)
            evidence = self._evidence_by_ip.get(device.ip_address)
            if evidence is not None:
                device.snmp_sys_descr = evidence


class DiscoveryEngineTest(unittest.TestCase):
    def test_discovered_devices_are_classified_and_added_to_the_graph(self):
        engine = DiscoveryEngine(
            [_StubProvider([Device(ip_address="10.0.0.1", hostname="dc-01", vendor="Cisco")])]
        )

        graph = engine.discover()

        devices = list(graph.all_devices())
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].device_type, DeviceType.SERVER)

    def test_multiple_providers_contribute_to_the_same_graph(self):
        engine = DiscoveryEngine(
            [
                _StubProvider([Device(ip_address="10.0.0.1", hostname="dc-01", vendor="Cisco")]),
                _StubProvider([Device(ip_address="10.0.0.2", hostname="dc-02", vendor="Cisco")]),
            ]
        )

        graph = engine.discover()

        ip_addresses = {device.ip_address for device in graph.all_devices()}
        self.assertEqual(ip_addresses, {"10.0.0.1", "10.0.0.2"})

    def test_discover_without_an_event_bus_does_not_raise(self):
        engine = DiscoveryEngine([_StubProvider([Device(ip_address="10.0.0.1")])])

        engine.discover()

    def test_classification_phase_events_are_published_in_order(self):
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []
        bus.subscribe(received.append)
        engine = DiscoveryEngine(
            [
                _StubProvider(
                    [
                        Device(ip_address="10.0.0.1", hostname="dc-01", vendor="Cisco"),
                        Device(ip_address="10.0.0.2", hostname="dc-02", vendor="Cisco"),
                    ]
                )
            ],
            event_bus=bus,
        )

        engine.discover()

        self.assertEqual(len(received), 4)
        self.assertTrue(all(event.phase == RuntimePhase.CLASSIFICATION for event in received))
        self.assertEqual(received[0].kind, RuntimeEventKind.PHASE_STARTED)
        self.assertEqual(received[1].kind, RuntimeEventKind.PROGRESS)
        self.assertEqual(received[1].progress.completed, 1)
        self.assertEqual(received[2].kind, RuntimeEventKind.PROGRESS)
        self.assertEqual(received[2].progress.completed, 2)
        self.assertEqual(received[3].kind, RuntimeEventKind.PHASE_COMPLETED)
        self.assertEqual(received[3].progress.completed, 2)

    def test_classification_events_still_published_for_zero_devices(self):
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []
        bus.subscribe(received.append)
        engine = DiscoveryEngine([_StubProvider([])], event_bus=bus)

        engine.discover()

        self.assertEqual(len(received), 2)
        self.assertEqual(received[0].kind, RuntimeEventKind.PHASE_STARTED)
        self.assertEqual(received[1].kind, RuntimeEventKind.PHASE_COMPLETED)
        self.assertEqual(received[1].progress.completed, 0)

    def test_non_device_results_are_ignored(self):
        engine = DiscoveryEngine([_StubProvider(["not a device"])])  # type: ignore[list-item]

        graph = engine.discover()

        self.assertEqual(list(graph.all_devices()), [])

    def test_duplicate_ip_across_discovery_providers_is_deduplicated(self):
        engine = DiscoveryEngine(
            [
                _StubProvider([Device(ip_address="10.0.0.1", hostname="first")]),
                _StubProvider([Device(ip_address="10.0.0.1", hostname="second")]),
            ]
        )

        graph = engine.discover()

        devices = graph.all_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].hostname, "first")

    def test_enrichment_provider_adds_evidence_before_classification(self):
        enrichment = _StubEnrichmentProvider({"10.0.0.1": "Linux appliance"})
        engine = DiscoveryEngine(
            [_StubProvider([Device(ip_address="10.0.0.1")])],
            enrichment_providers=[enrichment],
        )

        graph = engine.discover()

        self.assertEqual(enrichment.seen_ips, ["10.0.0.1"])
        self.assertEqual(graph.get_device("10.0.0.1").snmp_sys_descr, "Linux appliance")

    def test_absent_enrichment_providers_do_not_change_existing_behavior(self):
        engine = DiscoveryEngine([_StubProvider([Device(ip_address="10.0.0.1", hostname="dc-01", vendor="Cisco")])])

        graph = engine.discover()

        self.assertEqual(len(graph.all_devices()), 1)

    def test_enrichment_provider_exception_does_not_abort_discovery(self):
        engine = DiscoveryEngine(
            [_StubProvider([Device(ip_address="10.0.0.1", hostname="dc-01", vendor="Cisco")])],
            enrichment_providers=[_StubEnrichmentProvider(raises=True)],
        )

        graph = engine.discover()

        devices = graph.all_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].device_type, DeviceType.SERVER)


if __name__ == "__main__":
    unittest.main()
