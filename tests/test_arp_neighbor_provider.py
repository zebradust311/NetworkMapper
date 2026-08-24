import unittest

from networkmapper.core.models import Device
from networkmapper.discovery.arp_neighbor_provider import ARP_NEIGHBOR_CATEGORY, SnmpArpNeighborProvider
from networkmapper.discovery.snmp_client import SnmpArpTableEntry, SnmpArpTableResult, SnmpClient
from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion
from networkmapper.observations.models import RelationshipObservation
from networkmapper.runtime.events import RuntimeEvent, RuntimeEventBus, RuntimeEventKind, RuntimePhase

_CREDENTIALS = SnmpCredentials(version=SnmpVersion.V2C, community="s3cr3t-community")


class _StubSnmpClient(SnmpClient):
    def __init__(self, results_by_ip: dict[str, SnmpArpTableResult]) -> None:
        self._results_by_ip = results_by_ip
        self.queried_ips: list[str] = []

    def get_arp_table(self, host, credentials, timeout, retries) -> SnmpArpTableResult:
        self.queried_ips.append(host)
        return self._results_by_ip.get(host, SnmpArpTableResult(responded=False, failure_reason="timeout"))


class _RaisingSnmpClient(SnmpClient):
    def get_arp_table(self, host, credentials, timeout, retries) -> SnmpArpTableResult:
        raise RuntimeError("client defect")


def _entry(ip_address: str, mac_address: str = "AA:BB:CC:DD:EE:FF", entry_type: str = "dynamic") -> SnmpArpTableEntry:
    return SnmpArpTableEntry(
        interface_index=1, ip_address=ip_address, mac_address=mac_address, entry_type=entry_type
    )


class SnmpArpNeighborProviderTest(unittest.TestCase):
    """ARCH-020 / FEAT-010A."""

    def test_one_entry_produces_one_relationship_observation(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpArpTableResult(responded=True, entries=[_entry("192.168.1.10")])}
        )
        provider = SnmpArpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        observations = provider.collect_observations()
        self.assertEqual(len(observations), 1)
        observation = observations[0]
        self.assertIsInstance(observation, RelationshipObservation)
        self.assertEqual(observation.subject, "203.0.113.5")
        self.assertEqual(observation.related_subject, "192.168.1.10")
        self.assertEqual(observation.category, ARP_NEIGHBOR_CATEGORY)
        self.assertEqual(observation.provenance.provider, "snmp")
        self.assertEqual(observation.provenance.collection_method, "ipNetToPhysicalTable")

    def test_multiple_entries_from_one_device_each_produce_an_observation(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpArpTableResult(
                    responded=True,
                    entries=[_entry("192.168.1.10"), _entry("192.168.1.11")],
                )
            }
        )
        provider = SnmpArpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        observations = provider.collect_observations()
        self.assertEqual(
            {observation.related_subject for observation in observations},
            {"192.168.1.10", "192.168.1.11"},
        )
        self.assertTrue(all(observation.subject == "203.0.113.5" for observation in observations))

    def test_multiple_devices_each_produce_their_own_observations(self):
        devices = [Device(ip_address="203.0.113.1"), Device(ip_address="203.0.113.2")]
        client = _StubSnmpClient(
            {
                "203.0.113.1": SnmpArpTableResult(responded=True, entries=[_entry("192.168.1.10")]),
                "203.0.113.2": SnmpArpTableResult(responded=True, entries=[_entry("192.168.1.11")]),
            }
        )
        provider = SnmpArpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich(devices)

        observations = provider.collect_observations()
        self.assertEqual(
            {(o.subject, o.related_subject) for o in observations},
            {("203.0.113.1", "192.168.1.10"), ("203.0.113.2", "192.168.1.11")},
        )

    def test_an_empty_but_responded_table_produces_no_observations_but_no_error(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient({"203.0.113.5": SnmpArpTableResult(responded=True, entries=[])})
        provider = SnmpArpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])
        self.assertTrue(provider.run_diagnostics.host_diagnostics["203.0.113.5"].responded)

    def test_no_observation_when_the_host_times_out(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpArpTableResult(responded=False, failure_reason="timeout")}
        )
        provider = SnmpArpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_client_exception_is_caught_and_recorded_as_a_failure(self):
        device = Device(ip_address="203.0.113.5")
        provider = SnmpArpNeighborProvider(_CREDENTIALS, client=_RaisingSnmpClient())

        provider.enrich([device])  # must not raise

        self.assertEqual(provider.collect_observations(), [])
        self.assertEqual(provider.run_diagnostics.hosts_timed_out, 1)

    def test_run_diagnostics_report_hard_counts(self):
        devices = [Device(ip_address="203.0.113.1"), Device(ip_address="203.0.113.2")]
        client = _StubSnmpClient(
            {
                "203.0.113.1": SnmpArpTableResult(
                    responded=True, entries=[_entry("192.168.1.10"), _entry("192.168.1.11")]
                ),
                "203.0.113.2": SnmpArpTableResult(responded=False, failure_reason="timeout"),
            }
        )
        provider = SnmpArpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich(devices)

        diagnostics = provider.run_diagnostics
        self.assertEqual(diagnostics.hosts_eligible, 2)
        self.assertEqual(diagnostics.hosts_queried, 2)
        self.assertEqual(diagnostics.hosts_responded, 1)
        self.assertEqual(diagnostics.hosts_timed_out, 1)
        self.assertEqual(diagnostics.version, "v2c")
        self.assertEqual(diagnostics.host_diagnostics["203.0.113.1"].entries_returned, 2)
        self.assertFalse(diagnostics.host_diagnostics["203.0.113.2"].responded)

    def test_observations_reset_between_enrich_calls(self):
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpArpTableResult(responded=True, entries=[_entry("192.168.1.10")])}
        )
        provider = SnmpArpNeighborProvider(_CREDENTIALS, client=client)
        provider.enrich([Device(ip_address="203.0.113.5")])
        self.assertEqual(len(provider.collect_observations()), 1)

        provider.enrich([])

        self.assertEqual(provider.collect_observations(), [])

    def test_no_observations_before_enrich_is_called(self):
        provider = SnmpArpNeighborProvider(_CREDENTIALS, client=_StubSnmpClient({}))

        self.assertEqual(provider.collect_observations(), [])

    def test_device_fields_are_never_mutated(self):
        device = Device(ip_address="203.0.113.5", hostname="already-set", mac_address=None)
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpArpTableResult(responded=True, entries=[_entry("192.168.1.10")])}
        )
        provider = SnmpArpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(device.hostname, "already-set")
        self.assertIsNone(device.mac_address)
        self.assertEqual(device.discovery_sources, [])

    def test_telemetry_events_use_snmp_enrichment_phase_and_never_contain_the_community_string(self):
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []
        bus.subscribe(received.append)
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpArpTableResult(responded=True, entries=[_entry("192.168.1.10")])}
        )

        SnmpArpNeighborProvider(_CREDENTIALS, client=client, event_bus=bus).enrich([device])

        self.assertTrue(received)
        self.assertTrue(all(event.phase == RuntimePhase.SNMP_ENRICHMENT for event in received))
        for event in received:
            self.assertNotIn("s3cr3t-community", event.activity or "")
        self.assertEqual(received[0].kind, RuntimeEventKind.PHASE_STARTED)
        self.assertEqual(received[-1].kind, RuntimeEventKind.PHASE_COMPLETED)

    def test_enrich_with_zero_devices_still_publishes_phase_events(self):
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []
        bus.subscribe(received.append)

        SnmpArpNeighborProvider(_CREDENTIALS, client=_StubSnmpClient({}), event_bus=bus).enrich([])

        self.assertEqual(len(received), 2)
        self.assertEqual(received[0].kind, RuntimeEventKind.PHASE_STARTED)
        self.assertEqual(received[1].kind, RuntimeEventKind.PHASE_COMPLETED)


if __name__ == "__main__":
    unittest.main()
