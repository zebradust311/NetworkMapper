import unittest
from datetime import datetime

from networkmapper.core.models import Device
from networkmapper.discovery.lldp_neighbor_provider import LLDP_NEIGHBOR_CATEGORY, SnmpLldpNeighborProvider
from networkmapper.discovery.snmp_client import SnmpClient, SnmpLldpNeighborEntry, SnmpLldpTableResult
from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.runtime.events import RuntimeEvent, RuntimeEventBus, RuntimeEventKind, RuntimePhase

_CREDENTIALS = SnmpCredentials(version=SnmpVersion.V2C, community="s3cr3t-community")


class _StubSnmpClient(SnmpClient):
    def __init__(self, results_by_ip: dict[str, SnmpLldpTableResult]) -> None:
        self._results_by_ip = results_by_ip
        self.queried_ips: list[str] = []

    def get_lldp_neighbors(self, host, credentials, timeout, retries) -> SnmpLldpTableResult:
        self.queried_ips.append(host)
        return self._results_by_ip.get(host, SnmpLldpTableResult(responded=False, failure_reason="timeout"))


class _RaisingSnmpClient(SnmpClient):
    def get_lldp_neighbors(self, host, credentials, timeout, retries) -> SnmpLldpTableResult:
        raise RuntimeError("client defect")


def _entry(
    local_port_num: int = 1,
    rem_index: int = 1,
    chassis_id_subtype: int = 4,
    chassis_id: str = "AA:BB:CC:DD:EE:FF",
    sys_name: str | None = None,
    management_addresses: list[str] | None = None,
) -> SnmpLldpNeighborEntry:
    return SnmpLldpNeighborEntry(
        local_port_num=local_port_num,
        rem_index=rem_index,
        chassis_id_subtype=chassis_id_subtype,
        chassis_id=chassis_id,
        sys_name=sys_name,
        management_addresses=management_addresses or [],
    )


def _mac_identity_observation(subject: str, mac: str) -> IdentityObservation:
    return IdentityObservation(
        subject=subject,
        property_name="mac_address",
        value=mac,
        provenance=ObservationProvenance(
            provider="snmp", collection_method="ipNetToPhysicalTable", observed_at=datetime.now(), source_run="run-1"
        ),
    )


class SnmpLldpNeighborProviderTest(unittest.TestCase):
    """ARCH-023 / FEAT-012A."""

    def test_macaddress_subtype_resolves_via_fed_mac_index(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True,
                    entries=[_entry(chassis_id_subtype=4, chassis_id="AA:BB:CC:DD:EE:FF")],
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)
        provider.receive_observations(
            (_mac_identity_observation("192.168.1.10", "AA:BB:CC:DD:EE:FF"),)
        )

        provider.enrich([device])

        observations = provider.collect_observations()
        relationship_observations = [o for o in observations if isinstance(o, RelationshipObservation)]
        self.assertEqual(len(relationship_observations), 1)
        self.assertEqual(relationship_observations[0].subject, "203.0.113.5")
        self.assertEqual(relationship_observations[0].related_subject, "192.168.1.10")
        self.assertEqual(relationship_observations[0].category, LLDP_NEIGHBOR_CATEGORY)
        self.assertEqual(relationship_observations[0].provenance.collection_method, "lldp-chassis-mac")

    def test_ambiguous_mac_lookup_skips_the_row(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True,
                    entries=[_entry(chassis_id_subtype=4, chassis_id="AA:BB:CC:DD:EE:FF")],
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)
        provider.receive_observations(
            (
                _mac_identity_observation("192.168.1.10", "AA:BB:CC:DD:EE:FF"),
                _mac_identity_observation("192.168.1.11", "AA:BB:CC:DD:EE:FF"),
            )
        )

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_absent_mac_lookup_skips_the_row(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True,
                    entries=[_entry(chassis_id_subtype=4, chassis_id="AA:BB:CC:DD:EE:FF")],
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])  # no receive_observations() call at all

        self.assertEqual(provider.collect_observations(), [])

    def test_networkaddress_subtype_resolves_directly(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True,
                    entries=[_entry(chassis_id_subtype=5, chassis_id="192.168.1.20")],
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        observations = provider.collect_observations()
        relationship_observations = [o for o in observations if isinstance(o, RelationshipObservation)]
        self.assertEqual(len(relationship_observations), 1)
        self.assertEqual(relationship_observations[0].related_subject, "192.168.1.20")
        self.assertEqual(relationship_observations[0].provenance.collection_method, "lldp-chassis-network-address")

    def test_management_address_row_resolves_directly_no_index_needed(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True,
                    entries=[_entry(chassis_id_subtype=6, management_addresses=["10.0.0.1"])],
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        observations = provider.collect_observations()
        relationship_observations = [o for o in observations if isinstance(o, RelationshipObservation)]
        self.assertEqual(len(relationship_observations), 1)
        self.assertEqual(relationship_observations[0].related_subject, "10.0.0.1")
        self.assertEqual(relationship_observations[0].provenance.collection_method, "lldp-management-address")

    def test_multiple_management_addresses_each_produce_their_own_observation(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True,
                    entries=[_entry(management_addresses=["10.0.0.1", "10.0.0.2"])],
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        observations = provider.collect_observations()
        relationship_observations = [o for o in observations if isinstance(o, RelationshipObservation)]
        self.assertEqual(
            {o.related_subject for o in relationship_observations}, {"10.0.0.1", "10.0.0.2"}
        )
        self.assertEqual(len(relationship_observations), 2)

    def test_management_address_takes_priority_over_chassis_id_fallback(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True,
                    entries=[
                        _entry(
                            chassis_id_subtype=5,
                            chassis_id="192.168.1.20",
                            management_addresses=["10.0.0.1"],
                        )
                    ],
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        observations = provider.collect_observations()
        relationship_observations = [o for o in observations if isinstance(o, RelationshipObservation)]
        self.assertEqual(len(relationship_observations), 1)
        self.assertEqual(relationship_observations[0].related_subject, "10.0.0.1")

    def test_unresolvable_chassis_subtype_produces_no_relationship_observation(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True,
                    entries=[_entry(chassis_id_subtype=6, chassis_id="4769303f31")],  # interfaceName
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_sysname_identity_emitted_only_when_related_subject_is_discovered(self):
        device = Device(ip_address="203.0.113.5")
        discovered_neighbor = Device(ip_address="10.0.0.1")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True,
                    entries=[_entry(management_addresses=["10.0.0.1"], sys_name="switch-01")],
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device, discovered_neighbor])

        observations = provider.collect_observations()
        identity_observations = [o for o in observations if isinstance(o, IdentityObservation)]
        self.assertEqual(len(identity_observations), 1)
        self.assertEqual(identity_observations[0].subject, "10.0.0.1")
        self.assertEqual(identity_observations[0].property_name, "hostname")
        self.assertEqual(identity_observations[0].value, "switch-01")

    def test_sysname_identity_withheld_for_an_undiscovered_neighbor(self):
        # ARCH-023 Section 4: the endpoint-bootstrapping safeguard applied
        # to LLDP's own sysName evidence. 10.0.0.1 is NOT in the devices
        # passed to enrich() — only the queried device itself was
        # independently discovered.
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True,
                    entries=[_entry(management_addresses=["10.0.0.1"], sys_name="switch-01")],
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        observations = provider.collect_observations()
        relationship_observations = [o for o in observations if isinstance(o, RelationshipObservation)]
        identity_observations = [o for o in observations if isinstance(o, IdentityObservation)]
        self.assertEqual(len(relationship_observations), 1)
        self.assertEqual(identity_observations, [])

    def test_device_fields_are_never_mutated(self):
        device = Device(ip_address="203.0.113.5", hostname="already-set", mac_address=None)
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpLldpTableResult(
                    responded=True, entries=[_entry(management_addresses=["10.0.0.1"])]
                )
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(device.hostname, "already-set")
        self.assertIsNone(device.mac_address)
        self.assertEqual(device.discovery_sources, [])

    def test_an_empty_but_responded_table_produces_no_observations_but_no_error(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient({"203.0.113.5": SnmpLldpTableResult(responded=True, entries=[])})
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])
        self.assertTrue(provider.run_diagnostics.host_diagnostics["203.0.113.5"].responded)

    def test_no_observation_when_the_host_times_out(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpLldpTableResult(responded=False, failure_reason="timeout")}
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_client_exception_is_caught_and_recorded_as_a_failure(self):
        device = Device(ip_address="203.0.113.5")
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=_RaisingSnmpClient())

        provider.enrich([device])  # must not raise

        self.assertEqual(provider.collect_observations(), [])
        self.assertEqual(provider.run_diagnostics.hosts_timed_out, 1)

    def test_run_diagnostics_report_hard_counts(self):
        devices = [Device(ip_address="203.0.113.1"), Device(ip_address="203.0.113.2")]
        client = _StubSnmpClient(
            {
                "203.0.113.1": SnmpLldpTableResult(
                    responded=True,
                    entries=[_entry(management_addresses=["10.0.0.1", "10.0.0.2"])],
                ),
                "203.0.113.2": SnmpLldpTableResult(responded=False, failure_reason="timeout"),
            }
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)

        provider.enrich(devices)

        diagnostics = provider.run_diagnostics
        self.assertEqual(diagnostics.hosts_eligible, 2)
        self.assertEqual(diagnostics.hosts_responded, 1)
        self.assertEqual(diagnostics.hosts_timed_out, 1)
        self.assertEqual(diagnostics.version, "v2c")
        self.assertEqual(diagnostics.host_diagnostics["203.0.113.1"].entries_returned, 1)
        self.assertEqual(diagnostics.host_diagnostics["203.0.113.1"].management_addresses_returned, 2)
        self.assertFalse(diagnostics.host_diagnostics["203.0.113.2"].responded)

    def test_observations_reset_between_enrich_calls(self):
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpLldpTableResult(responded=True, entries=[_entry(management_addresses=["10.0.0.1"])])}
        )
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=client)
        provider.enrich([Device(ip_address="203.0.113.5")])
        self.assertEqual(len(provider.collect_observations()), 1)

        provider.enrich([])

        self.assertEqual(provider.collect_observations(), [])

    def test_no_observations_before_enrich_is_called(self):
        provider = SnmpLldpNeighborProvider(_CREDENTIALS, client=_StubSnmpClient({}))

        self.assertEqual(provider.collect_observations(), [])

    def test_telemetry_events_use_snmp_enrichment_phase_and_never_contain_the_community_string(self):
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []
        bus.subscribe(received.append)
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpLldpTableResult(responded=True, entries=[_entry(management_addresses=["10.0.0.1"])])}
        )

        SnmpLldpNeighborProvider(_CREDENTIALS, client=client, event_bus=bus).enrich([device])

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

        SnmpLldpNeighborProvider(_CREDENTIALS, client=_StubSnmpClient({}), event_bus=bus).enrich([])

        self.assertEqual(len(received), 2)
        self.assertEqual(received[0].kind, RuntimeEventKind.PHASE_STARTED)
        self.assertEqual(received[1].kind, RuntimeEventKind.PHASE_COMPLETED)


if __name__ == "__main__":
    unittest.main()
