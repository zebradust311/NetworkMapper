import unittest
from unittest.mock import call, patch

from networkmapper.core.models import ServiceEvidence
from networkmapper.discovery.nmap_provider import NmapProvider
from networkmapper.discovery.scan_profile import ScanProfile

DEEP_ENRICHMENT_ARGUMENTS = (
    "-Pn -sV --version-all --script "
    "http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,"
    "smb-os-discovery,smb-security-mode,sip-methods "
    "--top-ports 1000 --max-retries 6 --host-timeout 15m"
)


class NmapProviderDeepProfileTest(unittest.TestCase):
    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_deep_profile_preserves_two_phase_discovery(self, port_scanner_mock):
        """DEEP must retain ADR-001's two-phase shape (FEAT-004
        requirement), not fall back to a single-pass scan the way FAST
        does — verified by confirming host discovery (-sn) runs before
        DEEP's expanded enrichment call, exactly like STANDARD."""
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

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.DEEP)
        provider.discover()

        self.assertEqual(scanner.scan.call_count, 2)
        scanner.scan.assert_has_calls(
            [
                call(hosts="172.16.100.0/24", arguments="-sn"),
                call(
                    hosts="172.16.100.10 172.16.100.11",
                    arguments=DEEP_ENRICHMENT_ARGUMENTS,
                ),
            ]
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_deep_enrichment_arguments_extend_standard_script_set(self, port_scanner_mock):
        """DEEP's script list must be STANDARD's full set plus exactly one
        addition (sip-methods, ARCH-010's approved pilot) — not a
        redefinition, so STANDARD's evidence pipeline stays intact."""
        scanner = port_scanner_mock.return_value
        scanner.scan.side_effect = [
            {"scan": {"172.16.100.20": {"hostnames": [{"name": "host-20"}]}}},
            {"scan": {}},
        ]

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.DEEP)
        provider.discover()

        enrichment_call_arguments = scanner.scan.call_args_list[1].kwargs["arguments"]
        self.assertIn("--top-ports 1000", enrichment_call_arguments)
        self.assertIn("--version-all", enrichment_call_arguments)
        self.assertIn("--max-retries 6", enrichment_call_arguments)
        self.assertIn("--host-timeout 15m", enrichment_call_arguments)
        self.assertIn("sip-methods", enrichment_call_arguments)
        for standard_script in (
            "http-title",
            "ssl-cert",
            "vmware-version",
            "http-auth",
            "rdp-ntlm-info",
            "smb-os-discovery",
            "smb-security-mode",
        ):
            self.assertIn(standard_script, enrichment_call_arguments)
        self.assertNotIn("-p 22,53", enrichment_call_arguments)
        self.assertNotIn("--version-light", enrichment_call_arguments)

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_deep_profile_with_zero_hosts_skips_enrichment_phase(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {"scan": {}}

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.DEEP)
        devices = provider.discover()

        self.assertEqual(devices, [])
        scanner.scan.assert_called_once()
        diagnostics = provider.run_diagnostics
        self.assertEqual(diagnostics.hosts_discovered, 0)
        self.assertTrue(diagnostics.enrichment_enabled)
        self.assertEqual(len(diagnostics.phases), 1)
        self.assertTrue(diagnostics.expanded_capabilities)

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_deep_profile_merges_smb_identity_same_as_standard(self, port_scanner_mock):
        """DEEP must reuse STANDARD's exact extraction/merge logic, not a
        duplicate implementation — proven by feeding DEEP the same SMB
        host-script fixture STANDARD's own tests use and expecting an
        identical result."""
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.56": {"hostnames": [{"name": "dc-01"}]}}}

            return {
                "scan": {
                    "172.16.100.56": {
                        "tcp": {
                            445: {"state": "open", "name": "microsoft-ds"},
                        },
                        "hostscript": [
                            {
                                "id": "smb-os-discovery",
                                "output": (
                                    "\n"
                                    "  OS: Windows Server 2019 Standard 17763 "
                                    "(Windows Server 2019 Standard 6.3)\n"
                                    "  Computer name: DC01\n"
                                    "  Domain name: corp.local"
                                ),
                            },
                            {
                                "id": "smb-security-mode",
                                "output": (
                                    "\n  message_signing: disabled (dangerous, but default)"
                                ),
                            },
                        ],
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.DEEP)
        devices = provider.discover()

        device = devices[0]
        self.assertEqual(
            device.operating_system,
            "Windows Server 2019 Standard 17763 (Windows Server 2019 Standard 6.3)",
        )
        self.assertEqual(device.computer_name, "DC01")
        self.assertEqual(device.domain, "corp.local")
        self.assertEqual(device.smb_signing, "disabled (dangerous, but default)")
        self.assertEqual(
            device.services,
            [ServiceEvidence(port=445, protocol="tcp", service="microsoft-ds")],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_deep_profile_populates_expanded_capabilities(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.side_effect = [
            {"scan": {"172.16.100.30": {"hostnames": [{"name": "host-30"}]}}},
            {"scan": {}},
        ]

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.DEEP)
        provider.discover()

        capabilities = " ".join(provider.run_diagnostics.expanded_capabilities)
        self.assertIn("top 1000", capabilities)
        self.assertIn("--version-all", capabilities)
        self.assertIn("sip-methods", capabilities)
        self.assertIn("--max-retries 6", capabilities)
        self.assertIn("--host-timeout 15m", capabilities)


if __name__ == "__main__":
    unittest.main()
