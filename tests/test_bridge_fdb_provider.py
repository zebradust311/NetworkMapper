import unittest
from datetime import datetime

from networkmapper.core.models import Device
from networkmapper.discovery.bridge_fdb_provider import BRIDGE_FDB_CATEGORY, SnmpBridgeFdbProvider
from networkmapper.discovery.snmp_client import SnmpBridgeFdbEntry, SnmpBridgeFdbResult, SnmpClient
from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.runtime.events import RuntimeEvent, RuntimeEventBus, RuntimeEventKind, RuntimePhase

_CREDENTIALS = SnmpCredentials(version=SnmpVersion.V2C, community="s3cr3t-community")


class _StubSnmpClient(SnmpClient):
    def __init__(self, results_by_ip: dict[str, SnmpBridgeFdbResult]) -> None:
        self._results_by_ip = results_by_ip
        self.queried_ips: list[str] = []

    def get_bridge_fdb(self, host, credentials, timeout, retries) -> SnmpBridgeFdbResult:
        self.queried_ips.append(host)
        return self._results_by_ip.get(host, SnmpBridgeFdbResult(responded=False, failure_reason="timeout"))


class _RaisingSnmpClient(SnmpClient):
    def get_bridge_fdb(self, host, credentials, timeout, retries) -> SnmpBridgeFdbResult:
        raise RuntimeError("client defect")


def _entry(
    mac_address: str = "AA:BB:CC:DD:EE:FF",
    port: int = 4,
    status: str | None = "learned",
) -> SnmpBridgeFdbEntry:
    return SnmpBridgeFdbEntry(mac_address=mac_address, port=port, status=status)


def _mac_identity_observation(subject: str, mac: str) -> IdentityObservation:
    return IdentityObservation(
        subject=subject,
        property_name="mac_address",
        value=mac,
        provenance=ObservationProvenance(
            provider="snmp", collection_method="ipNetToPhysicalTable", observed_at=datetime.now(), source_run="run-1"
        ),
    )


class SnmpBridgeFdbProviderTest(unittest.TestCase):
    """ARCH-024 / PLAN-012B / FEAT-012B."""

    def test_learned_status_row_resolves_via_fed_mac_index(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpBridgeFdbResult(
                    responded=True,
                    entries=[_entry(mac_address="AA:BB:CC:DD:EE:FF", status="learned")],
                )
            }
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)
        provider.receive_observations(
            (_mac_identity_observation("192.168.1.10", "AA:BB:CC:DD:EE:FF"),)
        )

        provider.enrich([device])

        observations = provider.collect_observations()
        relationship_observations = [o for o in observations if isinstance(o, RelationshipObservation)]
        self.assertEqual(len(relationship_observations), 1)
        self.assertEqual(relationship_observations[0].subject, "203.0.113.5")
        self.assertEqual(relationship_observations[0].related_subject, "192.168.1.10")
        self.assertEqual(relationship_observations[0].category, BRIDGE_FDB_CATEGORY)
        self.assertEqual(relationship_observations[0].provenance.collection_method, "dot1dTpFdbTable")

    def test_ambiguous_mac_lookup_skips_the_row(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpBridgeFdbResult(
                    responded=True,
                    entries=[_entry(mac_address="AA:BB:CC:DD:EE:FF", status="learned")],
                )
            }
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)
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
                "203.0.113.5": SnmpBridgeFdbResult(
                    responded=True,
                    entries=[_entry(mac_address="AA:BB:CC:DD:EE:FF", status="learned")],
                )
            }
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)

        provider.enrich([device])  # no receive_observations() call at all

        self.assertEqual(provider.collect_observations(), [])

    def test_self_status_row_produces_no_observation_at_all(self):
        # ARCH-024 Section 6: a self(4) row must never emit any
        # observation of either kind, even when its MAC happens to
        # resolve unambiguously via the fed index — the full-exclusion
        # shape, distinct from ARP's own partial-gating precedent.
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpBridgeFdbResult(
                    responded=True,
                    entries=[_entry(mac_address="AA:BB:CC:DD:EE:FF", status="self")],
                )
            }
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)
        provider.receive_observations(
            (_mac_identity_observation("203.0.113.5", "AA:BB:CC:DD:EE:FF"),)
        )

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_mgmt_status_row_produces_no_observation(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpBridgeFdbResult(
                    responded=True,
                    entries=[_entry(mac_address="AA:BB:CC:DD:EE:FF", status="mgmt")],
                )
            }
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)
        provider.receive_observations(
            (_mac_identity_observation("192.168.1.10", "AA:BB:CC:DD:EE:FF"),)
        )

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_unresolved_status_row_produces_no_observation(self):
        # ARCH-024 Section 7: a row whose status walk failed at the
        # client layer (status=None) is excluded the same way other/
        # invalid/self/mgmt already are — never treated as "learned" by
        # default.
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpBridgeFdbResult(
                    responded=True,
                    entries=[_entry(mac_address="AA:BB:CC:DD:EE:FF", status=None)],
                )
            }
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)
        provider.receive_observations(
            (_mac_identity_observation("192.168.1.10", "AA:BB:CC:DD:EE:FF"),)
        )

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_other_and_invalid_status_rows_produce_no_observation(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpBridgeFdbResult(
                    responded=True,
                    entries=[
                        _entry(mac_address="AA:BB:CC:DD:EE:FF", status="other"),
                        _entry(mac_address="BB:CC:DD:EE:FF:00", status="invalid"),
                    ],
                )
            }
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)
        provider.receive_observations(
            (
                _mac_identity_observation("192.168.1.10", "AA:BB:CC:DD:EE:FF"),
                _mac_identity_observation("192.168.1.11", "BB:CC:DD:EE:FF:00"),
            )
        )

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_no_identity_observation_is_ever_emitted(self):
        # ARCH-024 Section 5: dot1dTpFdbTable carries no identity-bearing
        # field about the resolved neighbor at all — this provider must
        # never emit an IdentityObservation, unlike ARP/LLDP.
        device = Device(ip_address="203.0.113.5")
        discovered_neighbor = Device(ip_address="192.168.1.10")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpBridgeFdbResult(
                    responded=True,
                    entries=[_entry(mac_address="AA:BB:CC:DD:EE:FF", status="learned")],
                )
            }
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)
        provider.receive_observations(
            (_mac_identity_observation("192.168.1.10", "AA:BB:CC:DD:EE:FF"),)
        )

        provider.enrich([device, discovered_neighbor])

        observations = provider.collect_observations()
        self.assertEqual([o for o in observations if isinstance(o, IdentityObservation)], [])
        self.assertEqual(len([o for o in observations if isinstance(o, RelationshipObservation)]), 1)

    def test_device_fields_are_never_mutated(self):
        device = Device(ip_address="203.0.113.5", hostname="already-set", mac_address=None)
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpBridgeFdbResult(
                    responded=True, entries=[_entry(status="learned")]
                )
            }
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(device.hostname, "already-set")
        self.assertIsNone(device.mac_address)
        self.assertEqual(device.discovery_sources, [])

    def test_an_empty_but_responded_table_produces_no_observations_but_no_error(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient({"203.0.113.5": SnmpBridgeFdbResult(responded=True, entries=[])})
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])
        self.assertTrue(provider.run_diagnostics.host_diagnostics["203.0.113.5"].responded)

    def test_no_observation_when_the_host_times_out(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpBridgeFdbResult(responded=False, failure_reason="timeout")}
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_client_exception_is_caught_and_recorded_as_a_failure(self):
        device = Device(ip_address="203.0.113.5")
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=_RaisingSnmpClient())

        provider.enrich([device])  # must not raise

        self.assertEqual(provider.collect_observations(), [])
        self.assertEqual(provider.run_diagnostics.hosts_timed_out, 1)

    def test_run_diagnostics_report_hard_counts(self):
        devices = [Device(ip_address="203.0.113.1"), Device(ip_address="203.0.113.2")]
        client = _StubSnmpClient(
            {
                "203.0.113.1": SnmpBridgeFdbResult(
                    responded=True,
                    entries=[_entry(status="learned"), _entry(mac_address="BB:CC:DD:EE:FF:00", status="self")],
                ),
                "203.0.113.2": SnmpBridgeFdbResult(responded=False, failure_reason="timeout"),
            }
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)

        provider.enrich(devices)

        diagnostics = provider.run_diagnostics
        self.assertEqual(diagnostics.hosts_eligible, 2)
        self.assertEqual(diagnostics.hosts_responded, 1)
        self.assertEqual(diagnostics.hosts_timed_out, 1)
        self.assertEqual(diagnostics.version, "v2c")
        self.assertEqual(diagnostics.host_diagnostics["203.0.113.1"].entries_returned, 2)
        self.assertFalse(diagnostics.host_diagnostics["203.0.113.2"].responded)

    def test_observations_reset_between_enrich_calls(self):
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpBridgeFdbResult(responded=True, entries=[_entry(status="learned")])}
        )
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=client)
        provider.receive_observations(
            (_mac_identity_observation("192.168.1.10", "AA:BB:CC:DD:EE:FF"),)
        )
        provider.enrich([Device(ip_address="203.0.113.5")])
        self.assertEqual(len(provider.collect_observations()), 1)

        provider.enrich([])

        self.assertEqual(provider.collect_observations(), [])

    def test_no_observations_before_enrich_is_called(self):
        provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=_StubSnmpClient({}))

        self.assertEqual(provider.collect_observations(), [])

    def test_telemetry_events_use_snmp_enrichment_phase_and_never_contain_the_community_string(self):
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []
        bus.subscribe(received.append)
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpBridgeFdbResult(responded=True, entries=[_entry(status="learned")])}
        )

        SnmpBridgeFdbProvider(_CREDENTIALS, client=client, event_bus=bus).enrich([device])

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

        SnmpBridgeFdbProvider(_CREDENTIALS, client=_StubSnmpClient({}), event_bus=bus).enrich([])

        self.assertEqual(len(received), 2)
        self.assertEqual(received[0].kind, RuntimeEventKind.PHASE_STARTED)
        self.assertEqual(received[1].kind, RuntimeEventKind.PHASE_COMPLETED)


if __name__ == "__main__":
    unittest.main()
