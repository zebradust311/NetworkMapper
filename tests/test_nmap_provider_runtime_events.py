import unittest
from unittest.mock import patch

from networkmapper.discovery.nmap_provider import NmapProvider
from networkmapper.discovery.scan_profile import ScanProfile
from networkmapper.runtime.events import RuntimeEvent, RuntimeEventBus, RuntimeEventKind, RuntimePhase


class NmapProviderRuntimeEventsTest(unittest.TestCase):
    def _bus_with_recorder(self) -> tuple[RuntimeEventBus, list[RuntimeEvent]]:
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []
        bus.subscribe(received.append)
        return bus, received

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_fast_profile_publishes_host_discovery_start_and_completion_only(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {
            "scan": {
                "172.16.100.10": {"hostnames": [{"name": "host-01"}]},
                "172.16.100.11": {"hostnames": [{"name": "host-02"}]},
            },
            "nmap": {"scanstats": {"elapsed": "1.50"}},
        }
        bus, received = self._bus_with_recorder()

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.FAST, event_bus=bus)
        provider.discover()

        self.assertEqual(len(received), 2)
        self.assertTrue(all(event.phase == RuntimePhase.HOST_DISCOVERY for event in received))
        self.assertEqual(received[0].kind, RuntimeEventKind.PHASE_STARTED)
        self.assertIn("172.16.100.0/24", received[0].activity)
        self.assertEqual(received[1].kind, RuntimeEventKind.PHASE_COMPLETED)
        self.assertEqual(received[1].progress.completed, 2)
        self.assertEqual(received[1].progress.unit_label, "Hosts Found")
        self.assertIsNone(received[1].progress.total)

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_discover_without_an_event_bus_does_not_raise(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {"scan": {}, "nmap": {"scanstats": {"elapsed": "0.10"}}}

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.FAST)
        provider.discover()

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_profile_with_no_hosts_publishes_only_host_discovery_events(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {"scan": {}, "nmap": {"scanstats": {"elapsed": "0.80"}}}
        bus, received = self._bus_with_recorder()

        provider = NmapProvider(
            "172.16.100.0/24", scan_profile=ScanProfile.STANDARD, event_bus=bus
        )
        provider.discover()

        self.assertEqual(len(received), 2)
        self.assertTrue(all(event.phase == RuntimePhase.HOST_DISCOVERY for event in received))
        self.assertEqual(received[1].progress.completed, 0)

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_profile_publishes_host_progress_during_enrichment(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {
                    "scan": {
                        "172.16.100.20": {"hostnames": [{"name": "web-01"}]},
                        "172.16.100.21": {"hostnames": [{"name": "web-02"}]},
                        "172.16.100.22": {"hostnames": [{"name": "web-03"}]},
                    },
                    "nmap": {"scanstats": {"elapsed": "2.10"}},
                }

            return {
                "scan": {
                    "172.16.100.20": {"tcp": {80: {"state": "open", "name": "http"}}},
                },
                "nmap": {"scanstats": {"elapsed": "9.75"}},
            }

        scanner.scan.side_effect = scan_side_effect
        bus, received = self._bus_with_recorder()

        provider = NmapProvider(
            "172.16.100.0/24", scan_profile=ScanProfile.STANDARD, event_bus=bus
        )
        provider.discover()

        phases = [event.phase for event in received]
        kinds = [event.kind for event in received]
        self.assertEqual(
            phases,
            [
                RuntimePhase.HOST_DISCOVERY,
                RuntimePhase.HOST_DISCOVERY,
                RuntimePhase.SERVICE_ENRICHMENT,
                RuntimePhase.SERVICE_ENRICHMENT,
                RuntimePhase.SERVICE_ENRICHMENT,
                RuntimePhase.SERVICE_ENRICHMENT,
                RuntimePhase.SERVICE_ENRICHMENT,
            ],
        )
        self.assertEqual(
            kinds,
            [
                RuntimeEventKind.PHASE_STARTED,
                RuntimeEventKind.PHASE_COMPLETED,
                RuntimeEventKind.PHASE_STARTED,
                RuntimeEventKind.PROGRESS,
                RuntimeEventKind.PROGRESS,
                RuntimeEventKind.PROGRESS,
                RuntimeEventKind.PHASE_COMPLETED,
            ],
        )

        host_discovery_completed = received[1]
        self.assertEqual(host_discovery_completed.progress.completed, 3)
        self.assertIsNone(host_discovery_completed.progress.total)

        progress_events = received[3:6]
        self.assertEqual(
            [event.progress.completed for event in progress_events], [1, 2, 3]
        )
        self.assertTrue(all(event.progress.total == 3 for event in progress_events))
        self.assertTrue(
            all(event.progress.unit_label == "Hosts Completed" for event in progress_events)
        )

        enrichment_completed = received[6]
        self.assertEqual(enrichment_completed.progress.completed, 3)
        self.assertEqual(enrichment_completed.progress.total, 3)

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_deep_profile_also_publishes_service_enrichment_events(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.side_effect = [
            {"scan": {"172.16.100.40": {"hostnames": [{"name": "host-40"}]}}},
            {"scan": {}},
        ]
        bus, received = self._bus_with_recorder()

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.DEEP, event_bus=bus)
        provider.discover()

        enrichment_events = [
            event for event in received if event.phase == RuntimePhase.SERVICE_ENRICHMENT
        ]
        self.assertEqual(len(enrichment_events), 3)
        self.assertEqual(enrichment_events[0].kind, RuntimeEventKind.PHASE_STARTED)
        self.assertEqual(enrichment_events[-1].kind, RuntimeEventKind.PHASE_COMPLETED)


if __name__ == "__main__":
    unittest.main()
