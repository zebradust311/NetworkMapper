import unittest
from datetime import datetime

from networkmapper.core.models import Device, DeviceType
from networkmapper.developer.classification_workbench import ClassificationWorkbench
from networkmapper.project.models import Project


class ClassificationWorkbenchTest(unittest.TestCase):
    def test_generate_lists_only_unknown_devices_with_clean_values(self):
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


if __name__ == "__main__":
    unittest.main()
