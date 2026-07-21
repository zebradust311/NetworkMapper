import unittest
from unittest.mock import patch

from networkmapper.discovery.nmap_provider import NmapProvider
from networkmapper.discovery.scan_profile import ScanProfile


class NmapProviderScanProfileTest(unittest.TestCase):
    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_fast_profile_maps_to_sn(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {"scan": {}}

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.FAST)
        provider.discover()

        scanner.scan.assert_called_once_with(
            hosts="172.16.100.0/24",
            arguments="-sn",
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_provider_defaults_to_fast_profile(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {"scan": {}}

        provider = NmapProvider("172.16.100.0/24")
        provider.discover()

        scanner.scan.assert_called_once_with(
            hosts="172.16.100.0/24",
            arguments="-sn",
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_profile_maps_to_service_detection_arguments(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {"scan": {}}

        provider = NmapProvider(
            "172.16.100.0/24",
            scan_profile=ScanProfile.STANDARD,
        )
        provider.discover()

        scanner.scan.assert_called_once_with(
            hosts="172.16.100.0/24",
            arguments="-sV",
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_existing_discovery_behavior_is_preserved(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {
            "scan": {
                "172.16.100.10": {
                    "hostnames": [{"name": "host-01"}],
                    "addresses": {"mac": "AA:BB:CC:DD:EE:FF"},
                    "vendor": {"AA:BB:CC": "Cisco"},
                }
            }
        }

        provider = NmapProvider("172.16.100.0/24")
        devices = provider.discover()

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].ip_address, "172.16.100.10")
        self.assertEqual(devices[0].hostname, "host-01")
        self.assertEqual(devices[0].mac_address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(devices[0].vendor, "Cisco")
        self.assertEqual(devices[0].open_ports, [])
        self.assertEqual(devices[0].detected_services, [])
        self.assertEqual(devices[0].discovery_sources, ["nmap"])

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_scan_collects_open_ports_and_services(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {
            "scan": {
                "172.16.100.11": {
                    "hostnames": [{"name": "voice-gw-01"}],
                    "tcp": {
                        22: {"state": "closed", "name": "ssh"},
                        80: {"state": "open", "name": "http"},
                        443: {"state": "open", "name": "https"},
                    },
                    "udp": {
                        161: {"state": "open", "name": "snmp"},
                    },
                }
            }
        }

        provider = NmapProvider(
            "172.16.100.0/24",
            scan_profile=ScanProfile.STANDARD,
        )
        devices = provider.discover()

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].open_ports, [80, 161, 443])
        self.assertEqual(devices[0].detected_services, ["http", "https", "snmp"])


if __name__ == "__main__":
    unittest.main()
