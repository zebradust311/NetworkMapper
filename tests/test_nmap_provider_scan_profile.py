import unittest
from unittest.mock import call, patch

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
        scanner.scan.side_effect = [
            {
                "scan": {
                    "172.16.100.10": {"hostnames": [{"name": "host-01"}]},
                    "172.16.100.11": {"hostnames": [{"name": "host-02"}]},
                }
            },
            {"scan": {}},
        ]

        provider = NmapProvider(
            "172.16.100.0/24",
            scan_profile=ScanProfile.STANDARD,
        )
        provider.discover()

        self.assertEqual(scanner.scan.call_count, 2)
        scanner.scan.assert_has_calls(
            [
                call(hosts="172.16.100.0/24", arguments="-sn"),
                call(
                    hosts="172.16.100.10 172.16.100.11",
                    arguments=(
                        "-Pn -sV --version-light -p "
                        "22,53,80,161,443,445,515,631,9100,3389,5060,5061,8080,8443"
                    ),
                ),
            ]
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
    def test_standard_discovers_same_hosts_as_fast_and_merges_enrichment_by_ip(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.side_effect = [
            {
                "scan": {
                    "172.16.100.10": {
                        "hostnames": [{"name": "host-01"}],
                        "addresses": {"mac": "AA:BB:CC:DD:EE:FF"},
                        "vendor": {"AA:BB:CC": "Cisco"},
                    },
                    "172.16.100.11": {
                        "hostnames": [{"name": "host-02"}],
                        "addresses": {"mac": "AA:BB:CC:DD:EE:11"},
                        "vendor": {"AA:BB:CC": "HP"},
                    },
                }
            },
            {
                "scan": {
                    "172.16.100.10": {
                        "tcp": {
                            80: {"state": "open", "name": "http"},
                            443: {"state": "open", "name": "https"},
                        },
                        "udp": {
                            161: {"state": "open", "name": "snmp"},
                        },
                    }
                }
            },
        ]

        provider = NmapProvider(
            "172.16.100.0/24",
            scan_profile=ScanProfile.STANDARD,
        )
        devices = provider.discover()

        self.assertEqual(len(devices), 2)
        devices_by_ip = {device.ip_address: device for device in devices}
        self.assertEqual(
            set(devices_by_ip),
            {"172.16.100.10", "172.16.100.11"},
        )
        self.assertEqual(devices_by_ip["172.16.100.10"].open_ports, [80, 161, 443])
        self.assertEqual(
            devices_by_ip["172.16.100.10"].detected_services,
            ["http", "https", "snmp"],
        )
        self.assertEqual(devices_by_ip["172.16.100.11"].open_ports, [])
        self.assertEqual(devices_by_ip["172.16.100.11"].detected_services, [])

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_populates_device_from_tcp_service_data(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {
                    "scan": {
                        "172.16.100.20": {
                            "hostnames": [{"name": "printer-01"}],
                        }
                    }
                }

            if arguments == (
                "-Pn -sV --version-light -p "
                "22,53,80,161,443,445,515,631,9100,3389,5060,5061,8080,8443"
            ):
                return {
                    "scan": {
                        "172.16.100.20": {
                            "tcp": {
                                80: {"state": "open", "name": "http"},
                                9100: {"state": "open", "name": "jetdirect"},
                            },
                            "udp": {
                                161: {"state": "open", "name": "snmp"},
                            },
                        }
                    }
                }

            return {"scan": {}}

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider(
            "172.16.100.0/24",
            scan_profile=ScanProfile.STANDARD,
        )
        devices = provider.discover()

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].ip_address, "172.16.100.20")
        self.assertEqual(devices[0].open_ports, [80, 161, 9100])
        self.assertEqual(
            devices[0].detected_services,
            ["http", "jetdirect", "snmp"],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_fast_scan_does_not_collect_ports_or_services(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {
            "scan": {
                "172.16.100.12": {
                    "hostnames": [{"name": "host-02"}],
                    "tcp": {
                        80: {"state": "open", "name": "http"},
                    },
                }
            }
        }

        provider = NmapProvider(
            "172.16.100.0/24",
            scan_profile=ScanProfile.FAST,
        )
        devices = provider.discover()

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].open_ports, [])
        self.assertEqual(devices[0].detected_services, [])


if __name__ == "__main__":
    unittest.main()
