import unittest
from datetime import datetime

from networkmapper.core.models import Device, DeviceType, ServiceEvidence
from networkmapper.developer.classification_workbench import ClassificationWorkbench
from networkmapper.project.models import Project


class ClassificationWorkbenchTest(unittest.TestCase):
    def test_generate_lists_only_unknown_devices_with_empty_evidence_rendered_cleanly(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )

        project.network_graph.add_device(
            Device(
                ip_address="172.16.100.4",
                hostname="Unknown",
                vendor="Ubiquiti",
                mac_address="24:5A:4C:AA:BB:CC",
                operating_system=None,
                services=[],
                device_type=DeviceType.UNKNOWN,
                discovery_sources=["nmap"],
            )
        )
        project.network_graph.add_device(
            Device(
                ip_address="172.16.100.5",
                hostname="Known-Host",
                vendor="Cisco",
                mac_address="AA:BB:CC:DD:EE:01",
                operating_system="Linux",
                device_type=DeviceType.SWITCH,
                discovery_sources=["nmap"],
            )
        )
        project.network_graph.add_device(
            Device(
                ip_address="172.16.100.6",
                hostname=None,
                vendor=None,
                mac_address=None,
                operating_system=None,
                services=[],
                device_type=DeviceType.UNKNOWN,
                discovery_sources=[],
            )
        )

        report = ClassificationWorkbench().generate(project)

        self.assertIn("UNKNOWN DEVICE", report)
        self.assertIn("IP Address:", report)
        self.assertIn("172.16.100.4", report)
        self.assertIn("Vendor:", report)
        self.assertIn("Ubiquiti", report)
        self.assertIn("Current DeviceType:", report)
        self.assertIn("unknown", report)
        self.assertNotIn("Known-Host", report)
        self.assertNotIn("Linux", report)
        self.assertIn("Unknown", report)

    def test_generate_renders_populated_services_one_per_line(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )
        project.network_graph.add_device(
            Device(
                ip_address="172.16.100.7",
                hostname="host-ports",
                vendor="Brother",
                services=[
                    ServiceEvidence(port=80, protocol="tcp"),
                    ServiceEvidence(port=161, protocol="udp"),
                    ServiceEvidence(port=9100, protocol="tcp"),
                ],
                device_type=DeviceType.UNKNOWN,
            )
        )

        report = ClassificationWorkbench().generate(project)

        self.assertIn("Services:\n80/tcp\n161/udp\n9100/tcp", report)

    def test_generate_renders_service_names_and_product_version(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )
        project.network_graph.add_device(
            Device(
                ip_address="172.16.100.8",
                hostname="host-services",
                vendor="Cisco",
                services=[
                    ServiceEvidence(port=80, protocol="tcp", service="http"),
                    ServiceEvidence(
                        port=443,
                        protocol="tcp",
                        service="https",
                        product="Apache httpd",
                        version="2.4.41",
                    ),
                    ServiceEvidence(port=161, protocol="udp", service="snmp"),
                ],
                device_type=DeviceType.UNKNOWN,
            )
        )

        report = ClassificationWorkbench().generate(project)

        self.assertIn(
            "Services:\n80/tcp http\n443/tcp https (Apache httpd 2.4.41)\n161/udp snmp",
            report,
        )

    def test_generate_renders_http_title_and_tls_evidence(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )
        project.network_graph.add_device(
            Device(
                ip_address="172.16.100.10",
                hostname="fw-01",
                vendor="Unknown",
                services=[
                    ServiceEvidence(
                        port=443,
                        protocol="tcp",
                        service="https",
                        http_title="SonicWALL - Network Security Appliance",
                        tls_subject="commonName=SonicWALL",
                        tls_issuer="commonName=SonicWALL",
                    ),
                ],
                device_type=DeviceType.UNKNOWN,
            )
        )

        report = ClassificationWorkbench().generate(project)

        self.assertIn(
            "Services:\n443/tcp https | title: 'SonicWALL - Network Security "
            "Appliance' | tls subject: 'commonName=SonicWALL' | tls issuer: "
            "'commonName=SonicWALL'",
            report,
        )

    def test_generate_renders_http_auth_realm_evidence(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )
        project.network_graph.add_device(
            Device(
                ip_address="172.16.100.12",
                hostname="printer-03",
                vendor="Unknown",
                services=[
                    ServiceEvidence(
                        port=80,
                        protocol="tcp",
                        service="http",
                        http_auth_realm="HP LaserJet 4250",
                    ),
                ],
                device_type=DeviceType.UNKNOWN,
            )
        )

        report = ClassificationWorkbench().generate(project)

        self.assertIn(
            "Services:\n80/tcp http | auth realm: 'HP LaserJet 4250'",
            report,
        )

    def test_generate_renders_unknown_for_empty_services(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )
        project.network_graph.add_device(
            Device(
                ip_address="172.16.100.11",
                hostname="host-no-services",
                vendor="Cisco",
                services=[],
                device_type=DeviceType.UNKNOWN,
            )
        )

        report = ClassificationWorkbench().generate(project)

        self.assertIn("Services:\nUnknown", report)

    def test_generate_renders_rule_result_evidence_for_evaluated_rules(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )
        project.network_graph.add_device(
            Device(
                ip_address="172.16.100.9",
                hostname="host-unknown",
                vendor="Brother",
                device_type=DeviceType.UNKNOWN,
            )
        )

        report = ClassificationWorkbench().generate(project)

        self.assertIn("Rule Evidence:", report)
        self.assertIn("----------------------------------------", report)
        self.assertIn("Rule: ServerHostnameRule", report)
        self.assertIn("Rule: HypervisorHostnameRule", report)
        self.assertIn("Rule: UbiquitiAccessPointRule", report)
        self.assertIn("Rule: SonicWallFirewallRule", report)
        self.assertIn("Rule: PrinterVendorRule", report)
        self.assertNotIn("Rule: VoiceVendorRule", report)
        self.assertNotIn("Rule: CiscoSwitchRule", report)
        self.assertNotIn("Rule: DellWorkstationRule", report)
        self.assertIn("Matched: Yes", report)
        self.assertIn("Suggested Type: PRINTER", report)
        self.assertIn("Reason:\nVendor 'Brother' matched known printer vendor.", report)

    def test_generate_renders_non_matching_rule_result_fields(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )
        project.network_graph.add_device(
            Device(
                ip_address="172.16.100.10",
                hostname="workstation-01",
                vendor="Unknown Vendor",
                device_type=DeviceType.UNKNOWN,
            )
        )

        report = ClassificationWorkbench().generate(project)

        self.assertIn("Rule: ServerHostnameRule", report)
        self.assertIn("Matched: No", report)
        self.assertIn("Suggested Type: None", report)
        self.assertIn(
            "Reason:\nHostname 'workstation-01' did not match known server naming patterns.",
            report,
        )


if __name__ == "__main__":
    unittest.main()
