import unittest
from unittest.mock import patch

from networkmapper.discovery.nmap_provider import NmapProvider
from networkmapper.discovery.scan_profile import ScanProfile


class NmapProviderObservationTest(unittest.TestCase):
    """FEAT-007A/ARCH-017 Stage 2."""

    def test_no_observations_before_discover_is_called(self):
        provider = NmapProvider("172.16.100.0/24")

        self.assertEqual(provider.collect_observations(), [])

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_fast_profile_emits_hostname_and_mac_address_observations(self, port_scanner_mock):
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

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.FAST)
        devices = provider.discover()

        observations = provider.collect_observations()
        by_property = {observation.property_name: observation for observation in observations}
        self.assertEqual(set(by_property), {"hostname", "mac_address"})
        self.assertEqual(by_property["hostname"].value, "host-01")
        self.assertEqual(by_property["hostname"].subject, "172.16.100.10")
        self.assertEqual(by_property["hostname"].provenance.provider, "nmap")
        self.assertEqual(by_property["hostname"].provenance.collection_method, "host-discovery")
        self.assertEqual(by_property["mac_address"].value, "AA:BB:CC:DD:EE:FF")

        # Device construction is unaffected by observation emission.
        self.assertEqual(devices[0].hostname, "host-01")
        self.assertEqual(devices[0].mac_address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(devices[0].vendor, "Cisco")

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_vendor_and_operating_system_are_never_emitted_as_identity_observations(
        self, port_scanner_mock
    ):
        # ARCH-016/ARCH-015: vendor identifies a NIC manufacturer, not a
        # unit; the OS caption is not identity-bearing evidence. Neither
        # should ever appear as a property_name.
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {
            "scan": {
                "172.16.100.10": {
                    "hostnames": [{"name": "host-01"}],
                    "vendor": {"AA:BB:CC": "Cisco"},
                }
            }
        }

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.FAST)
        provider.discover()

        property_names = {o.property_name for o in provider.collect_observations()}
        self.assertNotIn("vendor", property_names)
        self.assertNotIn("operating_system", property_names)

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_a_host_with_no_hostname_or_mac_emits_no_identity_observations(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {"scan": {"172.16.100.10": {}}}

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.FAST)
        provider.discover()

        self.assertEqual(provider.collect_observations(), [])

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_profile_emits_smb_sourced_computer_name_and_domain(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.56": {"hostnames": [{"name": "dc-01"}]}}}

            return {
                "scan": {
                    "172.16.100.56": {
                        "tcp": {445: {"state": "open", "name": "microsoft-ds"}},
                        "hostscript": [
                            {
                                "id": "smb-os-discovery",
                                "output": (
                                    "\n"
                                    "  OS: Windows Server 2019 Standard 17763\n"
                                    "  Computer name: DC01\n"
                                    "  Domain name: corp.local\n"
                                ),
                            }
                        ],
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        provider.discover()

        observations = provider.collect_observations()
        computer_name_observations = [o for o in observations if o.property_name == "computer_name"]
        domain_observations = [o for o in observations if o.property_name == "domain"]

        self.assertEqual(len(computer_name_observations), 1)
        self.assertEqual(computer_name_observations[0].value, "DC01")
        self.assertEqual(computer_name_observations[0].provenance.collection_method, "smb-os-discovery")

        self.assertEqual(len(domain_observations), 1)
        self.assertEqual(domain_observations[0].value, "corp.local")
        self.assertEqual(domain_observations[0].provenance.collection_method, "smb-os-discovery")

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_profile_emits_rdp_sourced_computer_name_when_smb_is_absent(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.60": {"hostnames": [{"name": "ws-01"}]}}}

            return {
                "scan": {
                    "172.16.100.60": {
                        "tcp": {
                            3389: {
                                "state": "open",
                                "name": "ms-wbt-server",
                                "script": {
                                    "rdp-ntlm-info": (
                                        "NetBIOS_Computer_Name: DESKTOP-02\n"
                                        "NetBIOS_Domain_Name: CORP\n"
                                        "Product_Version: 10.0.19045\n"
                                    )
                                },
                            }
                        },
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        provider.discover()

        observations = provider.collect_observations()
        computer_name_observations = [o for o in observations if o.property_name == "computer_name"]

        self.assertEqual(len(computer_name_observations), 1)
        self.assertEqual(computer_name_observations[0].value, "DESKTOP-02")
        self.assertEqual(computer_name_observations[0].provenance.collection_method, "rdp-ntlm-info")

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_smb_and_rdp_both_present_produce_two_independent_computer_name_observations(
        self, port_scanner_mock
    ):
        # The corroboration/conflict case ADR-012 describes: both
        # sources reported something, so both are retained, even though
        # the fallback-only Device merge only keeps SMB's value.
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.61": {"hostnames": [{"name": "dual-01"}]}}}

            return {
                "scan": {
                    "172.16.100.61": {
                        "tcp": {
                            3389: {
                                "state": "open",
                                "name": "ms-wbt-server",
                                "script": {
                                    "rdp-ntlm-info": "NetBIOS_Computer_Name: RDP-NAME\n"
                                },
                            }
                        },
                        "hostscript": [
                            {
                                "id": "smb-os-discovery",
                                "output": "\n  Computer name: SMB-NAME\n",
                            }
                        ],
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        computer_name_observations = [
            o for o in provider.collect_observations() if o.property_name == "computer_name"
        ]
        self.assertEqual(len(computer_name_observations), 2)
        values_by_method = {
            o.provenance.collection_method: o.value for o in computer_name_observations
        }
        self.assertEqual(values_by_method, {"smb-os-discovery": "SMB-NAME", "rdp-ntlm-info": "RDP-NAME"})

        # The fallback-only Device merge still only keeps SMB's value.
        self.assertEqual(devices[0].computer_name, "SMB-NAME")

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_observations_reset_between_discover_calls(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value
        scanner.scan.return_value = {
            "scan": {"172.16.100.10": {"hostnames": [{"name": "host-01"}]}}
        }

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.FAST)
        provider.discover()
        self.assertEqual(len(provider.collect_observations()), 1)

        scanner.scan.return_value = {"scan": {}}
        provider.discover()

        self.assertEqual(provider.collect_observations(), [])


if __name__ == "__main__":
    unittest.main()
