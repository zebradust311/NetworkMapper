import unittest
from unittest.mock import call, patch

from networkmapper.core.models import ServiceEvidence
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
                        "-Pn -sV --version-light --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode -p "
                        "22,53,80,161,443,445,515,631,9100,3389,5060,5061,8080,8443,902,903"
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
        self.assertEqual(devices[0].services, [])
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
        self.assertEqual(
            devices_by_ip["172.16.100.10"].services,
            [
                ServiceEvidence(port=80, protocol="tcp", service="http"),
                ServiceEvidence(port=161, protocol="udp", service="snmp"),
                ServiceEvidence(port=443, protocol="tcp", service="https"),
            ],
        )
        self.assertEqual(devices_by_ip["172.16.100.11"].services, [])

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
                "-Pn -sV --version-light --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode -p "
                "22,53,80,161,443,445,515,631,9100,3389,5060,5061,8080,8443,902,903"
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
        self.assertEqual(
            devices[0].services,
            [
                ServiceEvidence(port=80, protocol="tcp", service="http"),
                ServiceEvidence(port=161, protocol="udp", service="snmp"),
                ServiceEvidence(port=9100, protocol="tcp", service="jetdirect"),
            ],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_captures_vmware_management_ports(self, port_scanner_mock):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {
                    "scan": {
                        "172.16.100.30": {
                            "hostnames": [{"name": "esxi-mgmt-01"}],
                        }
                    }
                }

            if arguments == (
                "-Pn -sV --version-light --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode -p "
                "22,53,80,161,443,445,515,631,9100,3389,5060,5061,8080,8443,902,903"
            ):
                return {
                    "scan": {
                        "172.16.100.30": {
                            "tcp": {
                                902: {"state": "open", "name": "vmware-auth"},
                                903: {"state": "open", "name": "iss-realsecure"},
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
        self.assertEqual(devices[0].ip_address, "172.16.100.30")
        self.assertEqual(
            devices[0].services,
            [
                ServiceEvidence(port=902, protocol="tcp", service="vmware-auth"),
                ServiceEvidence(port=903, protocol="tcp", service="iss-realsecure"),
            ],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_captures_product_and_version_from_existing_sv_scan(
        self, port_scanner_mock
    ):
        """-sV is already run for STANDARD enrichment; product/version it already
        returns should be captured rather than discarded (FEAT-003A)."""
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {
                    "scan": {
                        "172.16.100.40": {
                            "hostnames": [{"name": "web-01"}],
                        }
                    }
                }

            if arguments == (
                "-Pn -sV --version-light --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode -p "
                "22,53,80,161,443,445,515,631,9100,3389,5060,5061,8080,8443,902,903"
            ):
                return {
                    "scan": {
                        "172.16.100.40": {
                            "tcp": {
                                80: {
                                    "state": "open",
                                    "name": "http",
                                    "product": "Apache httpd",
                                    "version": "2.4.41",
                                },
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

        self.assertEqual(
            devices[0].services,
            [
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    service="http",
                    product="Apache httpd",
                    version="2.4.41",
                ),
            ],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_captures_http_title_from_script_output(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.50": {"hostnames": [{"name": "fw-01"}]}}}

            return {
                "scan": {
                    "172.16.100.50": {
                        "tcp": {
                            443: {
                                "state": "open",
                                "name": "https",
                                "script": {
                                    "http-title": "SonicWALL - Network Security Appliance",
                                },
                            },
                        },
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        self.assertEqual(
            devices[0].services,
            [
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    service="https",
                    http_title="SonicWALL - Network Security Appliance",
                ),
            ],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_captures_tls_subject_and_issuer_from_ssl_cert_script(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.51": {"hostnames": [{"name": "fw-02"}]}}}

            return {
                "scan": {
                    "172.16.100.51": {
                        "tcp": {
                            443: {
                                "state": "open",
                                "name": "https",
                                "script": {
                                    "ssl-cert": (
                                        "Subject: commonName=SonicWALL\n"
                                        "Issuer: commonName=SonicWALL\n"
                                        "Public Key type: rsa\n"
                                        "Not valid before: 2020-01-01T00:00:00\n"
                                        "Not valid after:  2030-01-01T00:00:00"
                                    ),
                                },
                            },
                        },
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        self.assertEqual(
            devices[0].services,
            [
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    service="https",
                    tls_subject="commonName=SonicWALL",
                    tls_issuer="commonName=SonicWALL",
                ),
            ],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_captures_smb_identity_for_domain_joined_host(
        self, port_scanner_mock
    ):
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
                                    "  NetBIOS computer name: DC01\\x00\n"
                                    "  Domain name: corp.local\n"
                                    "  Forest name: corp.local\n"
                                    "  FQDN: DC01.corp.local\n"
                                    "  System time: 2026-01-01T10:00:00-05:00"
                                ),
                            },
                            {
                                "id": "smb-security-mode",
                                "output": (
                                    "\n"
                                    "  account_used: guest\n"
                                    "  authentication_level: user\n"
                                    "  challenge_response: supported\n"
                                    "  message_signing: disabled (dangerous, but default)"
                                ),
                            },
                        ],
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        device = devices[0]
        self.assertEqual(
            device.operating_system,
            "Windows Server 2019 Standard 17763 (Windows Server 2019 Standard 6.3)",
        )
        self.assertEqual(device.computer_name, "DC01")
        self.assertEqual(device.domain, "corp.local")
        self.assertEqual(device.smb_signing, "disabled (dangerous, but default)")

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_falls_back_to_workgroup_for_non_domain_host(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.57": {"hostnames": [{"name": "desktop-01"}]}}}

            return {
                "scan": {
                    "172.16.100.57": {
                        "tcp": {
                            445: {"state": "open", "name": "microsoft-ds"},
                        },
                        "hostscript": [
                            {
                                "id": "smb-os-discovery",
                                "output": (
                                    "\n"
                                    "  OS: Windows 10 Pro 19045 (Windows 10 Pro 6.3)\n"
                                    "  Computer name: DESKTOP-01\n"
                                    "  NetBIOS computer name: DESKTOP-01\\x00\n"
                                    "  Workgroup: WORKGROUP\\x00\n"
                                    "  System time: 2026-01-01T10:00:00-05:00"
                                ),
                            },
                        ],
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        device = devices[0]
        self.assertEqual(device.operating_system, "Windows 10 Pro 19045 (Windows 10 Pro 6.3)")
        self.assertEqual(device.computer_name, "DESKTOP-01")
        self.assertEqual(device.domain, "WORKGROUP\\x00")

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_leaves_smb_identity_none_without_host_scripts(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.58": {"hostnames": [{"name": "printer-05"}]}}}

            return {
                "scan": {
                    "172.16.100.58": {
                        "tcp": {
                            80: {"state": "open", "name": "http"},
                        },
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        device = devices[0]
        self.assertIsNone(device.operating_system)
        self.assertIsNone(device.computer_name)
        self.assertIsNone(device.domain)
        self.assertIsNone(device.smb_signing)

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_captures_rdp_identity_when_smb_absent(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.59": {"hostnames": [{"name": "srv-file01"}]}}}

            return {
                "scan": {
                    "172.16.100.59": {
                        "tcp": {
                            3389: {
                                "state": "open",
                                "name": "ms-wbt-server",
                                "script": {
                                    "rdp-ntlm-info": (
                                        "\n"
                                        "  Target_Name: W2016\n"
                                        "  NetBIOS_Domain_Name: W2016\n"
                                        "  NetBIOS_Computer_Name: W16GA-SRV01\n"
                                        "  DNS_Domain_Name: W2016.lab\n"
                                        "  DNS_Computer_Name: W16GA-SRV01.W2016.lab\n"
                                        "  DNS_Tree_Name: W2016.lab\n"
                                        "  Product_Version: 10.0.14393\n"
                                        "  System_Time: 2026-01-01T10:00:00+00:00"
                                    ),
                                },
                            },
                        },
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        device = devices[0]
        self.assertEqual(device.operating_system, "10.0.14393")
        self.assertEqual(device.computer_name, "W16GA-SRV01")
        self.assertEqual(device.domain, "W2016")
        self.assertIsNone(device.smb_signing)

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_prefers_smb_identity_over_rdp_when_both_present(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.60": {"hostnames": [{"name": "dc-02"}]}}}

            return {
                "scan": {
                    "172.16.100.60": {
                        "tcp": {
                            445: {"state": "open", "name": "microsoft-ds"},
                            3389: {
                                "state": "open",
                                "name": "ms-wbt-server",
                                "script": {
                                    "rdp-ntlm-info": (
                                        "\n"
                                        "  NetBIOS_Domain_Name: RDPDOMAIN\n"
                                        "  NetBIOS_Computer_Name: RDPNAME\n"
                                        "  Product_Version: 10.0.14393"
                                    ),
                                },
                            },
                        },
                        "hostscript": [
                            {
                                "id": "smb-os-discovery",
                                "output": (
                                    "\n"
                                    "  OS: Windows Server 2019 Standard 17763 "
                                    "(Windows Server 2019 Standard 6.3)\n"
                                    "  Computer name: DC02\n"
                                    "  Domain name: corp.local"
                                ),
                            },
                        ],
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        device = devices[0]
        self.assertEqual(
            device.operating_system,
            "Windows Server 2019 Standard 17763 (Windows Server 2019 Standard 6.3)",
        )
        self.assertEqual(device.computer_name, "DC02")
        self.assertEqual(device.domain, "corp.local")

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_falls_back_to_rdp_field_by_field_when_smb_partial(
        self, port_scanner_mock
    ):
        """SMB/RDP precedence is decided per field, not per source: a host
        whose smb-os-discovery output only yields an OS string (e.g. Samba
        blanking its own name) should still take computer_name/domain from
        RDP rather than leaving them empty."""
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.61": {"hostnames": [{"name": "nas-01"}]}}}

            return {
                "scan": {
                    "172.16.100.61": {
                        "tcp": {
                            445: {"state": "open", "name": "microsoft-ds"},
                            3389: {
                                "state": "open",
                                "name": "ms-wbt-server",
                                "script": {
                                    "rdp-ntlm-info": (
                                        "\n"
                                        "  NetBIOS_Domain_Name: WORKGROUP\n"
                                        "  NetBIOS_Computer_Name: NAS-01\n"
                                        "  Product_Version: 10.0.14393"
                                    ),
                                },
                            },
                        },
                        "hostscript": [
                            {
                                "id": "smb-os-discovery",
                                "output": "\n  OS: Unix (Samba 4.15.13)",
                            },
                        ],
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        device = devices[0]
        self.assertEqual(device.operating_system, "Unix (Samba 4.15.13)")
        self.assertEqual(device.computer_name, "NAS-01")
        self.assertEqual(device.domain, "WORKGROUP")

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_captures_http_auth_realm_from_script_output(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.54": {"hostnames": [{"name": "printer-02"}]}}}

            return {
                "scan": {
                    "172.16.100.54": {
                        "tcp": {
                            80: {
                                "state": "open",
                                "name": "http",
                                "script": {
                                    "http-auth": (
                                        "HTTP/1.1 401 Unauthorized\n"
                                        "  Basic realm=NETGEAR R7000"
                                    ),
                                },
                            },
                        },
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        self.assertEqual(
            devices[0].services,
            [
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    service="http",
                    http_auth_realm="NETGEAR R7000",
                ),
            ],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_strips_quotes_from_http_auth_realm(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.55": {"hostnames": [{"name": "router-01"}]}}}

            return {
                "scan": {
                    "172.16.100.55": {
                        "tcp": {
                            8080: {
                                "state": "open",
                                "name": "http-proxy",
                                "script": {
                                    "http-auth": (
                                        'HTTP/1.1 401 Unauthorized\n'
                                        '  Digest realm="D-Link Corp."'
                                    ),
                                },
                            },
                        },
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        self.assertEqual(
            devices[0].services,
            [
                ServiceEvidence(
                    port=8080,
                    protocol="tcp",
                    service="http-proxy",
                    http_auth_realm="D-Link Corp.",
                ),
            ],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_prefers_vmware_version_script_over_sv_guess(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.52": {"hostnames": [{"name": "esxi-01"}]}}}

            return {
                "scan": {
                    "172.16.100.52": {
                        "tcp": {
                            443: {
                                "state": "open",
                                "name": "https",
                                "product": "VMware ESXi Server httpd",
                                "version": "1.0",
                                "script": {
                                    "vmware-version": (
                                        "VMware ESXi\n6.7.0\nBuild 17167734"
                                    ),
                                },
                            },
                        },
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        self.assertEqual(
            devices[0].services,
            [
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    service="https",
                    product="VMware ESXi Server httpd",
                    version="VMware ESXi 6.7.0 Build 17167734",
                ),
            ],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_standard_enrichment_falls_back_to_sv_version_without_vmware_script(
        self, port_scanner_mock
    ):
        scanner = port_scanner_mock.return_value

        def scan_side_effect(*, hosts, arguments):
            if arguments == "-sn":
                return {"scan": {"172.16.100.53": {"hostnames": [{"name": "web-02"}]}}}

            return {
                "scan": {
                    "172.16.100.53": {
                        "tcp": {
                            80: {
                                "state": "open",
                                "name": "http",
                                "product": "nginx",
                                "version": "1.18.0",
                            },
                        },
                    }
                }
            }

        scanner.scan.side_effect = scan_side_effect

        provider = NmapProvider("172.16.100.0/24", scan_profile=ScanProfile.STANDARD)
        devices = provider.discover()

        self.assertEqual(
            devices[0].services,
            [
                ServiceEvidence(port=80, protocol="tcp", service="http", product="nginx", version="1.18.0"),
            ],
        )

    @patch("networkmapper.discovery.nmap_provider.nmap.PortScanner")
    def test_fast_scan_does_not_collect_services(self, port_scanner_mock):
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
        self.assertEqual(devices[0].services, [])


if __name__ == "__main__":
    unittest.main()
