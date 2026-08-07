import unittest
from unittest.mock import patch

from networkmapper.discovery.nmap_provider import NmapProvider
from networkmapper.discovery.scan_profile import ScanProfile


class NmapProviderRunDiagnosticsTest(unittest.TestCase):
    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_fast_profile_records_single_phase_with_enrichment_disabled(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {
            "scan": {"172.16.100.10": {"hostnames": [{"name": "host-01"}]}},
            "nmap": {"scanstats": {"elapsed": "1.50"}},
        }

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.FAST)
        provider.discover()

        diagnostics = provider.run_diagnostics
        self.assertEqual(diagnostics.scan_profile, ScanProfile.FAST)
        self.assertEqual(diagnostics.hosts_discovered, 1)
        self.assertFalse(diagnostics.enrichment_enabled)
        self.assertIsNone(diagnostics.enrichment_arguments)
        self.assertEqual(len(diagnostics.phases), 1)
        self.assertEqual(diagnostics.phases[0].name, "Host Discovery")
        self.assertEqual(diagnostics.phases[0].arguments, "-sn")
        self.assertEqual(diagnostics.phases[0].elapsed_seconds, 1.5)
        self.assertEqual(diagnostics.host_diagnostics, {})
        self.assertEqual(diagnostics.expanded_capabilities, [])

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_missing_scanstats_leaves_elapsed_seconds_none(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {"scan": {}}

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.FAST)
        provider.discover()

        self.assertIsNone(provider.run_diagnostics.phases[0].elapsed_seconds)

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_profile_with_no_discovered_hosts_records_only_discovery_phase(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {"scan": {}, "nmap": {"scanstats": {"elapsed": "0.80"}}}

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        provider.discover()

        diagnostics = provider.run_diagnostics
        self.assertEqual(diagnostics.hosts_discovered, 0)
        self.assertTrue(diagnostics.enrichment_enabled)
        self.assertIsNotNone(diagnostics.enrichment_arguments)
        self.assertEqual(len(diagnostics.phases), 1)
        self.assertEqual(diagnostics.host_diagnostics, {})
        # Only one scan call: enrichment never runs against zero hosts.
        scanner.scan.assert_called_once()

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_profile_records_both_phases_and_per_host_diagnostics(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {
                    "scan": {
                        "172.16.100.20": {"hostnames": [{"name": "web-01"}]},
                        "172.16.100.21": {"hostnames": [{"name": "dark-01"}]},
                    },
                    "nmap": {"scanstats": {"elapsed": "2.10"}},
                }

            return {
                "scan": {
                    "172.16.100.20": {
                        "tcp": {
                            80: {
                                "state": "open",
                                "name": "http",
                                "script": {"http-title": "Example"},
                            },
                        },
                    }
                },
                "nmap": {"scanstats": {"elapsed": "9.75"}},
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        provider.discover()

        diagnostics = provider.run_diagnostics
        self.assertEqual(diagnostics.hosts_discovered, 2)
        self.assertTrue(diagnostics.enrichment_enabled)
        self.assertEqual(len(diagnostics.phases), 2)
        self.assertEqual(diagnostics.phases[0].elapsed_seconds, 2.1)
        self.assertEqual(diagnostics.phases[1].name, "Service Enrichment")
        self.assertEqual(diagnostics.phases[1].elapsed_seconds, 9.75)

        enriched_host = diagnostics.host_diagnostics["172.16.100.20"]
        self.assertTrue(enriched_host.enriched)
        self.assertTrue(enriched_host.has_http_title)

        dark_host = diagnostics.host_diagnostics["172.16.100.21"]
        self.assertFalse(dark_host.enriched)
        self.assertIn("No curated ports open.", dark_host.missing_evidence_reasons)
        self.assertEqual(diagnostics.expanded_capabilities, [])

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_deep_profile_records_enrichment_enabled_with_expanded_capabilities(
        self, port_scanner_mock
    ):
        """FEAT-004: DEEP no longer behaves like FAST — it performs the
        same two-phase enrichment STANDARD does, extended through
        configuration (ARCH-010), and reports what was extended."""
        scanner = port_scanner_mock.return_value
        scanner.scan.side_effect = [
            {"scan": {"172.16.100.40": {"hostnames": [{"name": "host-40"}]}}},
            {"scan": {}},
        ]

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.DEEP)
        provider.discover()

        diagnostics = provider.run_diagnostics
        self.assertEqual(diagnostics.scan_profile, ScanProfile.DEEP)
        self.assertTrue(diagnostics.enrichment_enabled)
        self.assertEqual(len(diagnostics.phases), 2)
        self.assertEqual(diagnostics.phases[1].name, "Service Enrichment")
        self.assertTrue(diagnostics.expanded_capabilities)
        self.assertIn("172.16.100.40", diagnostics.host_diagnostics)


if __name__ == "__main__":
    unittest.main()
