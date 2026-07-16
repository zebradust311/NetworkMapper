import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from networkmapper.core.models import Device, DeviceType
from networkmapper.exporters.markdown_exporter import MarkdownExporter
from networkmapper.project.models import Project
from networkmapper.reporting.project_summary import ProjectSummary


class MarkdownExporterTest(unittest.TestCase):
    def test_export_creates_markdown_and_groups_devices_by_type(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )

        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.10",
                hostname="DC1",
                vendor="Cisco",
                device_type=DeviceType.SERVER,
                discovery_sources=["nmap", "snmp"],
            )
        )
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.11",
                hostname="Desk-01",
                vendor="Ubiquiti",
                device_type=DeviceType.WORKSTATION,
                discovery_sources=["nmap"],
            )
        )
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.12",
                hostname="Desk-02",
                vendor="Ubiquiti",
                device_type=DeviceType.WORKSTATION,
                discovery_sources=["nmap"],
            )
        )
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.13",
                hostname="Printer-01",
                vendor="Brother",
                device_type=DeviceType.SERVER,
                discovery_sources=["nmap"],
            )
        )

        fake_summary = ProjectSummary(
            customer_name="Acme",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime(2026, 1, 2, 12, 0, 0),
            total_devices=99,
            device_type_counts={DeviceType.SERVER: 2, DeviceType.WORKSTATION: 1},
            vendor_counts={"Brother": 1, "Cisco": 1},
            discovered_networks=[],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = str(Path(temp_dir) / "project.md")
            with patch.object(ProjectSummary, "from_project", return_value=fake_summary):
                MarkdownExporter().export(project, output_path)

            self.assertTrue(Path(output_path).exists())
            markdown = Path(output_path).read_text(encoding="utf-8")

        self.assertIn("# Customer", markdown)
        self.assertIn("# Executive Summary", markdown)
        self.assertIn("# Device Inventory", markdown)
        self.assertIn("## Servers", markdown)
        self.assertIn("## Workstations", markdown)
        self.assertIn("Total Devices", markdown)
        self.assertIn("99", markdown)
        self.assertNotIn("## Vendors", markdown)
        self.assertIn("Manufacturers", markdown)
        self.assertIn("Manufacturer", markdown)
        self.assertIn("Ubiquiti", markdown)
        self.assertIn("### DC1", markdown)
        self.assertIn("### Printer-01", markdown)


if __name__ == "__main__":
    unittest.main()
