import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from networkmapper.core.models import Device
from networkmapper.core.network_graph import NetworkGraph
from networkmapper.exporters.csv_exporter import CsvExporter
from networkmapper.project.models import Project


class CsvExporterTest(unittest.TestCase):
    def test_export_writes_expected_csv_rows(self):
        project = Project(customer_name="Acme", created_date=datetime.now(), modified_date=datetime.now())
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.10",
                hostname="DC-01",
                vendor="Cisco",
                device_type="server",
                discovery_sources=["nmap", "snmp"],
            )
        )
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.11",
                hostname=None,
                vendor=None,
                device_type="unknown",
                discovery_sources=[],
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = str(Path(temp_dir) / "inventory.csv")
            CsvExporter().export(project, output_path)

            with open(output_path, newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(
            rows[0],
            ["IP Address", "Hostname", "Vendor", "Device Type", "Discovery Sources"],
        )
        self.assertEqual(rows[1], ["192.168.1.10", "DC-01", "Cisco", "server", "nmap,snmp"])
        self.assertEqual(rows[2], ["192.168.1.11", "", "", "unknown", ""])


if __name__ == "__main__":
    unittest.main()
