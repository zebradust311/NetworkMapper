import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from networkmapper.core.models import Device, DeviceType, ServiceEvidence
from networkmapper.project.models import Project
from networkmapper.project.serializer import ProjectSerializer


class ProjectSerializerTest(unittest.TestCase):
    def test_save_and_load_round_trips_correlated_service_evidence(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )
        project.network_graph.add_device(
            Device(
                ip_address="10.0.0.10",
                hostname="web-01",
                vendor="Unknown",
                operating_system=None,
                services=[
                    ServiceEvidence(port=80, protocol="tcp", service="http"),
                    ServiceEvidence(
                        port=443,
                        protocol="tcp",
                        service="https",
                        product="Apache httpd",
                        version="2.4.41",
                    ),
                ],
                device_type=DeviceType.SERVER,
                discovery_sources=["nmap"],
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "project.json"
            ProjectSerializer.save(project, str(file_path))
            loaded_project = ProjectSerializer.load(str(file_path))

        loaded_device = loaded_project.network_graph.get_device("10.0.0.10")

        self.assertIsNotNone(loaded_device)
        self.assertEqual(
            loaded_device.services,
            [
                ServiceEvidence(port=80, protocol="tcp", service="http"),
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    service="https",
                    product="Apache httpd",
                    version="2.4.41",
                ),
            ],
        )
        self.assertEqual(loaded_device.device_type, DeviceType.SERVER)

    def test_save_and_load_round_trips_device_with_no_services(self):
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )
        project.network_graph.add_device(
            Device(ip_address="10.0.0.20", hostname="host-20", vendor="Unknown")
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "project.json"
            ProjectSerializer.save(project, str(file_path))
            loaded_project = ProjectSerializer.load(str(file_path))

        loaded_device = loaded_project.network_graph.get_device("10.0.0.20")

        self.assertIsNotNone(loaded_device)
        self.assertEqual(loaded_device.services, [])


if __name__ == "__main__":
    unittest.main()
