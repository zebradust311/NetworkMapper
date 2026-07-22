import unittest
from datetime import datetime

from networkmapper.core.models import Device, DeviceType
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
                open_ports=[],
                detected_services=[],
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
                open_ports=[],
                detected_services=[],
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

    def test_generate_renders_populated_open_ports_one_per_line(self):
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
                open_ports=[80, 161, 9100],
                detected_services=[],
                device_type=DeviceType.UNKNOWN,
            )
        )

        report = ClassificationWorkbench().generate(project)

        self.assertIn("Open Ports:\n80\n161\n9100", report)
        self.assertIn("Detected Services:\nUnknown", report)

    def test_generate_renders_populated_detected_services_one_per_line(self):
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
                open_ports=[],
                detected_services=["http", "https", "snmp"],
                device_type=DeviceType.UNKNOWN,
            )
        )

        report = ClassificationWorkbench().generate(project)

        self.assertIn("Open Ports:\nUnknown", report)
        self.assertIn("Detected Services:\nhttp\nhttps\nsnmp", report)

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
        self.assertIn("Reason:\nPrinter vendor rule: vendor keyword matched", report)

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
            "Reason:\nHostname did not match known server naming conventions.",
            report,
        )


if __name__ == "__main__":
    unittest.main()
