import unittest
from datetime import datetime

from networkmapper.core.models import Device, DeviceType
from networkmapper.discovery.discovery_engine import DiscoveryEngine
from networkmapper.discovery.enrichment_provider import EnrichmentProvider
from networkmapper.discovery.provider import DiscoveryProvider
from networkmapper.observations.models import IdentityObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.runtime.events import RuntimeEvent, RuntimeEventBus, RuntimeEventKind, RuntimePhase


def _observation(subject: str, value: str, provider: str = "stub") -> IdentityObservation:
    return IdentityObservation(
        subject=subject,
        property_name="hostname",
        value=value,
        provenance=ObservationProvenance(
            provider=provider,
            collection_method="stub-method",
            observed_at=datetime(2026, 8, 18, 9, 0, 0),
            source_run="run-001",
        ),
    )


class _StubProvider(DiscoveryProvider):
    def __init__(
        self,
        devices: list[Device],
        observations: list[IdentityObservation] | None = None,
    ) -> None:
        self._devices = devices
        self._observations = observations or []

    def discover(self) -> list[Device]:
        return self._devices

    def collect_observations(self) -> list[IdentityObservation]:
        return self._observations


class _StubEnrichmentProvider(EnrichmentProvider):
    def __init__(
        self,
        evidence_by_ip: dict[str, str] | None = None,
        raises: bool = False,
        observations: list[IdentityObservation] | None = None,
    ) -> None:
        self._evidence_by_ip = evidence_by_ip or {}
        self._raises = raises
        self._observations = observations or []
        self.seen_ips: list[str] = []

    def enrich(self, devices) -> None:
        if self._raises:
            raise RuntimeError("enrichment provider defect")

        for device in devices:
            self.seen_ips.append(device.ip_address)
            evidence = self._evidence_by_ip.get(device.ip_address)
            if evidence is not None:
                device.snmp_sys_descr = evidence

    def collect_observations(self) -> list[IdentityObservation]:
        return self._observations


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


class DiscoveryEngineObservationCollectionTest(unittest.TestCase):
    """FEAT-007A/ARCH-017 Stage 2."""

    def test_providers_emitting_no_observations_leave_the_list_empty(self):
        engine = DiscoveryEngine([_StubProvider([Device(ip_address="10.0.0.1")])])

        engine.discover()

        self.assertEqual(engine.observations, [])

    def test_a_provider_that_does_not_override_collect_observations_is_unaffected(self):
        # The real DiscoveryProvider/EnrichmentProvider default (no
        # override) must behave exactly like an empty-list stub.
        class _MinimalProvider(DiscoveryProvider):
            def discover(self) -> list[Device]:
                return [Device(ip_address="10.0.0.1")]

        engine = DiscoveryEngine([_MinimalProvider()])

        graph = engine.discover()

        self.assertEqual(engine.observations, [])
        self.assertEqual(len(graph.all_devices()), 1)

    def test_discovery_engine_collects_observations_from_a_single_provider(self):
        observation = _observation("10.0.0.1", "dc-01")
        engine = DiscoveryEngine(
            [_StubProvider([Device(ip_address="10.0.0.1")], observations=[observation])]
        )

        engine.discover()

        self.assertEqual(engine.observations, [observation])

    def test_discovery_engine_aggregates_observations_from_multiple_providers(self):
        first_observation = _observation("10.0.0.1", "dc-01", provider="first")
        second_observation = _observation("10.0.0.2", "dc-02", provider="second")
        engine = DiscoveryEngine(
            [
                _StubProvider(
                    [Device(ip_address="10.0.0.1")], observations=[first_observation]
                ),
                _StubProvider(
                    [Device(ip_address="10.0.0.2")], observations=[second_observation]
                ),
            ]
        )

        engine.discover()

        self.assertEqual(engine.observations, [first_observation, second_observation])

    def test_discovery_engine_collects_enrichment_provider_observations_too(self):
        discovery_observation = _observation("10.0.0.1", "dc-01", provider="discovery")
        enrichment_observation = _observation("10.0.0.1", "sw-core-01", provider="enrichment")
        engine = DiscoveryEngine(
            [
                _StubProvider(
                    [Device(ip_address="10.0.0.1")], observations=[discovery_observation]
                )
            ],
            enrichment_providers=[
                _StubEnrichmentProvider(observations=[enrichment_observation])
            ],
        )

        engine.discover()

        self.assertEqual(
            engine.observations, [discovery_observation, enrichment_observation]
        )

    def test_a_raising_enrichment_provider_loses_only_its_own_observations(self):
        discovery_observation = _observation("10.0.0.1", "dc-01")
        engine = DiscoveryEngine(
            [
                _StubProvider(
                    [Device(ip_address="10.0.0.1")], observations=[discovery_observation]
                )
            ],
            enrichment_providers=[
                _StubEnrichmentProvider(
                    raises=True, observations=[_observation("10.0.0.1", "unreachable")]
                )
            ],
        )

        engine.discover()

        self.assertEqual(engine.observations, [discovery_observation])

    def test_observations_do_not_affect_device_construction_or_classification(self):
        engine = DiscoveryEngine(
            [
                _StubProvider(
                    [Device(ip_address="10.0.0.1", hostname="dc-01", vendor="Cisco")],
                    observations=[_observation("10.0.0.1", "a-completely-different-name")],
                )
            ]
        )

        graph = engine.discover()

        device = graph.get_device("10.0.0.1")
        self.assertEqual(device.hostname, "dc-01")
        self.assertEqual(device.device_type, DeviceType.SERVER)

    def test_observations_reset_between_discover_calls(self):
        engine = DiscoveryEngine(
            [_StubProvider([Device(ip_address="10.0.0.1")], observations=[_observation("10.0.0.1", "dc-01")])]
        )
        engine.discover()
        self.assertEqual(len(engine.observations), 1)

        engine._providers = [_StubProvider([Device(ip_address="10.0.0.2")])]
        engine.discover()

        self.assertEqual(engine.observations, [])


if __name__ == "__main__":
    unittest.main()
