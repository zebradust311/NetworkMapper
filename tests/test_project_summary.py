import unittest
from datetime import datetime

from networkmapper.core.models import Device, DeviceType
from networkmapper.project.models import Project
from networkmapper.reporting.project_summary import ProjectSummary


class ProjectSummaryTest(unittest.TestCase):
    def test_from_project_builds_expected_summary(self):
        created_at = datetime(2026, 1, 1, 12, 0, 0)
        updated_at = datetime(2026, 1, 2, 12, 0, 0)

        project = Project(
            customer_name="Acme",
            created_date=created_at,
            modified_date=updated_at,
        )
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.10",
                hostname="dc-01",
                vendor="Cisco",
                device_type=DeviceType.SERVER,
                discovery_sources=["nmap"],
            )
        )
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.11",
                hostname="desk-01",
                vendor="Dell",
                device_type=DeviceType.WORKSTATION,
                discovery_sources=["nmap", "snmp"],
            )
        )
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.12",
                hostname="printer-01",
                vendor="Brother",
                device_type=DeviceType.PRINTER,
                discovery_sources=["nmap"],
            )
        )

        summary = ProjectSummary.from_project(project)

        self.assertEqual(summary.customer_name, "Acme")
        self.assertEqual(summary.created_at, created_at)
        self.assertEqual(summary.updated_at, updated_at)
        self.assertEqual(summary.total_devices, 3)
        self.assertEqual(summary.device_type_counts[DeviceType.SERVER], 1)
        self.assertEqual(summary.device_type_counts[DeviceType.WORKSTATION], 1)
        self.assertEqual(summary.device_type_counts[DeviceType.PRINTER], 1)
        self.assertEqual(summary.vendor_counts["Cisco"], 1)
        self.assertEqual(summary.vendor_counts["Dell"], 1)
        self.assertEqual(summary.vendor_counts["Brother"], 1)
        self.assertEqual(summary.discovered_networks, [])


if __name__ == "__main__":
    unittest.main()
