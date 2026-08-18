import unittest

from networkmapper.core.models import Device
from networkmapper.discovery.snmp_client import SnmpClient, SnmpHostResult
from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion
from networkmapper.discovery.snmp_provider import SnmpEnrichmentProvider
from networkmapper.runtime.events import RuntimeEvent, RuntimeEventBus, RuntimeEventKind, RuntimePhase

_CREDENTIALS = SnmpCredentials(version=SnmpVersion.V2C, community="s3cr3t-community")


class _StubSnmpClient(SnmpClient):
    def __init__(self, results_by_ip: dict[str, SnmpHostResult]) -> None:
        self._results_by_ip = results_by_ip
        self.queried_ips: list[str] = []

    def get_system_group(self, host, credentials, timeout, retries) -> SnmpHostResult:
        self.queried_ips.append(host)
        return self._results_by_ip.get(host, SnmpHostResult(responded=False, failure_reason="timeout"))


class _RaisingSnmpClient(SnmpClient):
    def get_system_group(self, host, credentials, timeout, retries) -> SnmpHostResult:
        raise RuntimeError("client defect")


class SnmpEnrichmentProviderTest(unittest.TestCase):
    def test_new_fields_are_populated_from_a_successful_response(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpHostResult(
                    responded=True,
                    fields={
                        "sysDescr": "Cisco IOS Software, C2960",
                        "sysObjectID": "1.3.6.1.4.1.9.1.516",
                        "sysName": "sw-core-01",
                        "sysUpTime": "12345",
                        "sysContact": "netops@example.com",
                        "sysLocation": "Server Room A",
                    },
                )
            }
        )

        SnmpEnrichmentProvider(_CREDENTIALS, client=client).enrich([device])

        self.assertEqual(device.snmp_sys_descr, "Cisco IOS Software, C2960")
        self.assertEqual(device.snmp_sys_object_id, "1.3.6.1.4.1.9.1.516")
        self.assertEqual(device.hostname, "sw-core-01")
        self.assertEqual(device.snmp_sys_uptime, "12345")
        self.assertEqual(device.snmp_sys_contact, "netops@example.com")
        self.assertEqual(device.snmp_sys_location, "Server Room A")
        self.assertIn("snmp", device.discovery_sources)

    def test_sysname_never_overwrites_an_existing_hostname(self):
        device = Device(ip_address="203.0.113.5", hostname="dns-resolved-name")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpHostResult(responded=True, fields={"sysName": "snmp-name"})}
        )

        SnmpEnrichmentProvider(_CREDENTIALS, client=client).enrich([device])

        self.assertEqual(device.hostname, "dns-resolved-name")

    def test_existing_evidence_is_preserved_when_snmp_times_out(self):
        device = Device(
            ip_address="203.0.113.5",
            hostname="already-known",
            operating_system="Linux",
            discovery_sources=["nmap"],
        )
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpHostResult(responded=False, failure_reason="timeout")}
        )

        SnmpEnrichmentProvider(_CREDENTIALS, client=client).enrich([device])

        self.assertEqual(device.hostname, "already-known")
        self.assertEqual(device.operating_system, "Linux")
        self.assertIsNone(device.snmp_sys_descr)
        self.assertEqual(device.discovery_sources, ["nmap"])

    def test_client_exception_is_caught_and_recorded_as_a_failure(self):
        device = Device(ip_address="203.0.113.5")
        provider = SnmpEnrichmentProvider(_CREDENTIALS, client=_RaisingSnmpClient())

        provider.enrich([device])  # must not raise

        self.assertIsNone(device.snmp_sys_descr)
        self.assertEqual(provider.run_diagnostics.hosts_timed_out, 1)

    def test_run_diagnostics_report_hard_counts(self):
        devices = [Device(ip_address="203.0.113.1"), Device(ip_address="203.0.113.2")]
        client = _StubSnmpClient(
            {
                "203.0.113.1": SnmpHostResult(responded=True, fields={"sysDescr": "desc"}),
                "203.0.113.2": SnmpHostResult(responded=False, failure_reason="timeout"),
            }
        )
        provider = SnmpEnrichmentProvider(_CREDENTIALS, client=client)

        provider.enrich(devices)

        diagnostics = provider.run_diagnostics
        self.assertEqual(diagnostics.hosts_eligible, 2)
        self.assertEqual(diagnostics.hosts_queried, 2)
        self.assertEqual(diagnostics.hosts_responded, 1)
        self.assertEqual(diagnostics.hosts_timed_out, 1)
        self.assertEqual(diagnostics.version, "v2c")
        self.assertEqual(
            diagnostics.host_diagnostics["203.0.113.1"].fields_returned, ["sysDescr"]
        )
        self.assertFalse(diagnostics.host_diagnostics["203.0.113.2"].responded)

    def test_telemetry_events_never_contain_the_community_string(self):
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []
        bus.subscribe(received.append)
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpHostResult(responded=True, fields={"sysDescr": "desc"})}
        )

        SnmpEnrichmentProvider(_CREDENTIALS, client=client, event_bus=bus).enrich([device])

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

        SnmpEnrichmentProvider(_CREDENTIALS, client=_StubSnmpClient({}), event_bus=bus).enrich([])

        self.assertEqual(len(received), 2)
        self.assertEqual(received[0].kind, RuntimeEventKind.PHASE_STARTED)
        self.assertEqual(received[1].kind, RuntimeEventKind.PHASE_COMPLETED)


class SnmpEnrichmentProviderObservationTest(unittest.TestCase):
    """FEAT-007A/ARCH-017 Stage 2."""

    def test_no_observations_before_enrich_is_called(self):
        provider = SnmpEnrichmentProvider(_CREDENTIALS, client=_StubSnmpClient({}))

        self.assertEqual(provider.collect_observations(), [])

    def test_sysname_produces_a_hostname_identity_observation(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpHostResult(responded=True, fields={"sysName": "sw-core-01"})}
        )
        provider = SnmpEnrichmentProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        observations = provider.collect_observations()
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].subject, "203.0.113.5")
        self.assertEqual(observations[0].property_name, "hostname")
        self.assertEqual(observations[0].value, "sw-core-01")
        self.assertEqual(observations[0].provenance.provider, "snmp")
        self.assertEqual(observations[0].provenance.collection_method, "sysName")

    def test_sysname_observation_is_retained_even_when_the_merge_does_not_use_it(self):
        # Mirrors test_sysname_never_overwrites_an_existing_hostname:
        # the fallback-only merge leaves Device.hostname untouched, but
        # the observation must still exist — SNMP's own report is
        # retained as corroborating/conflicting evidence regardless of
        # whether the merge needed it (ADR-012).
        device = Device(ip_address="203.0.113.5", hostname="dns-resolved-name")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpHostResult(responded=True, fields={"sysName": "snmp-name"})}
        )
        provider = SnmpEnrichmentProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(device.hostname, "dns-resolved-name")
        observations = provider.collect_observations()
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].value, "snmp-name")

    def test_sysobjectid_and_other_non_identity_fields_produce_no_observation(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {
                "203.0.113.5": SnmpHostResult(
                    responded=True,
                    fields={
                        "sysDescr": "Cisco IOS Software, C2960",
                        "sysObjectID": "1.3.6.1.4.1.9.1.516",
                        "sysUpTime": "12345",
                        "sysContact": "netops@example.com",
                        "sysLocation": "Server Room A",
                    },
                )
            }
        )
        provider = SnmpEnrichmentProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_no_observation_when_the_host_times_out(self):
        device = Device(ip_address="203.0.113.5")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpHostResult(responded=False, failure_reason="timeout")}
        )
        provider = SnmpEnrichmentProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(provider.collect_observations(), [])

    def test_multiple_devices_each_produce_their_own_observation(self):
        devices = [Device(ip_address="203.0.113.1"), Device(ip_address="203.0.113.2")]
        client = _StubSnmpClient(
            {
                "203.0.113.1": SnmpHostResult(responded=True, fields={"sysName": "sw-01"}),
                "203.0.113.2": SnmpHostResult(responded=True, fields={"sysName": "sw-02"}),
            }
        )
        provider = SnmpEnrichmentProvider(_CREDENTIALS, client=client)

        provider.enrich(devices)

        observations = provider.collect_observations()
        self.assertEqual({o.subject for o in observations}, {"203.0.113.1", "203.0.113.2"})
        self.assertEqual({o.value for o in observations}, {"sw-01", "sw-02"})

    def test_observations_reset_between_enrich_calls(self):
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpHostResult(responded=True, fields={"sysName": "sw-01"})}
        )
        provider = SnmpEnrichmentProvider(_CREDENTIALS, client=client)
        provider.enrich([Device(ip_address="203.0.113.5")])
        self.assertEqual(len(provider.collect_observations()), 1)

        provider.enrich([])

        self.assertEqual(provider.collect_observations(), [])

    def test_observations_do_not_affect_device_fields(self):
        device = Device(ip_address="203.0.113.5", hostname="already-set")
        client = _StubSnmpClient(
            {"203.0.113.5": SnmpHostResult(responded=True, fields={"sysName": "snmp-name"})}
        )
        provider = SnmpEnrichmentProvider(_CREDENTIALS, client=client)

        provider.enrich([device])

        self.assertEqual(device.hostname, "already-set")
        self.assertEqual(len(provider.collect_observations()), 1)


if __name__ == "__main__":
    unittest.main()
