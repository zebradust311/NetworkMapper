import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from networkmapper.core.models import Device, DeviceType
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
                device_type=DeviceType.SERVER,
                discovery_sources=["nmap", "snmp"],
            )
        )
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.11",
                hostname=None,
                vendor=None,
                device_type=DeviceType.UNKNOWN,
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
            [
                "IP Address",
                "Hostname",
                "Vendor",
                "Device Type",
                "Discovery Sources",
                "SNMP Description",
                "SNMP Location",
                "SNMP Contact",
                "SNMP Uptime",
            ],
        )
        self.assertEqual(
            rows[1],
            ["192.168.1.10", "DC-01", "Cisco", "server", "nmap,snmp", "", "", "", ""],
        )
        self.assertEqual(rows[2], ["192.168.1.11", "", "", "unknown", "", "", "", "", ""])

    def test_export_writes_snmp_evidence_columns_when_present(self):
        """REPORT-003: SNMP evidence already stored on Device is surfaced in
        the CSV export. sysObjectID is deliberately not a column — it is
        canonical evidence for future knowledge interpretation, not
        customer presentation."""
        project = Project(customer_name="Acme")
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.20",
                hostname="sw-core-01",
                device_type=DeviceType.SWITCH,
                discovery_sources=["nmap", "snmp"],
                snmp_sys_descr="Cisco IOS Software, C2960 Software",
                snmp_sys_object_id="1.3.6.1.4.1.9.1.516",
                snmp_sys_location="Server Room A",
                snmp_sys_contact="netops@example.com",
                snmp_sys_uptime="391219825",
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = str(Path(temp_dir) / "inventory.csv")
            CsvExporter().export(project, output_path)

            with open(output_path, newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(
            rows[1],
            [
                "192.168.1.20",
                "sw-core-01",
                "",
                "switch",
                "nmap,snmp",
                "Cisco IOS Software, C2960 Software",
                "Server Room A",
                "netops@example.com",
                "391219825",
            ],
        )
        self.assertNotIn("1.3.6.1.4.1.9.1.516", ",".join(rows[0]) + ",".join(rows[1]))

    def test_export_leaves_snmp_columns_blank_when_only_some_fields_present(self):
        project = Project(customer_name="Acme")
        project.network_graph.add_device(
            Device(
                ip_address="192.168.1.21",
                hostname="printer-01",
                device_type=DeviceType.PRINTER,
                snmp_sys_descr="HP LaserJet 4250, Firmware Version: 08.061.3",
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = str(Path(temp_dir) / "inventory.csv")
            CsvExporter().export(project, output_path)

            with open(output_path, newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(rows[1][5], "HP LaserJet 4250, Firmware Version: 08.061.3")
        self.assertEqual(rows[1][6:], ["", "", ""])


if __name__ == "__main__":
    unittest.main()
