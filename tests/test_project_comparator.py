import unittest
from datetime import datetime

from networkmapper.comparison.project_comparator import ComparisonResult, ProjectComparator
from networkmapper.core.models import Device
from networkmapper.project.models import Project


class ProjectComparatorTest(unittest.TestCase):
    def test_compare_reports_added_removed_and_changed_devices(self):
        old_project = Project(customer_name="Old", created_date=datetime.now(), modified_date=datetime.now())
        new_project = Project(customer_name="New", created_date=datetime.now(), modified_date=datetime.now())

        old_project.network_graph.add_device(
            Device(
                ip_address="192.168.1.10",
                hostname="old-host",
                mac_address="AA:BB:CC:DD:EE:01",
                vendor="Cisco",
                discovery_sources=["nmap"],
            )
        )
        old_project.network_graph.add_device(
            Device(
                ip_address="192.168.1.20",
                hostname="removed-host",
                mac_address="AA:BB:CC:DD:EE:02",
                vendor="Dell",
                discovery_sources=["nmap"],
            )
        )
        old_project.network_graph.add_device(
            Device(
                ip_address="192.168.1.40",
                hostname="ip-changed-host-old",
                mac_address="AA:BB:CC:DD:EE:04",
                vendor="Dell",
                discovery_sources=["nmap"],
            )
        )

        new_project.network_graph.add_device(
            Device(
                ip_address="192.168.1.10",
                hostname="new-host",
                mac_address="AA:BB:CC:DD:EE:01",
                vendor="Cisco",
                discovery_sources=["nmap"],
            )
        )
        new_project.network_graph.add_device(
            Device(
                ip_address="192.168.1.30",
                hostname="added-host",
                mac_address="AA:BB:CC:DD:EE:03",
                vendor="Brother",
                discovery_sources=["snmp"],
            )
        )
        new_project.network_graph.add_device(
            Device(
                ip_address="192.168.1.50",
                hostname="ip-changed-host-new",
                mac_address="AA:BB:CC:DD:EE:04",
                vendor="Dell",
                discovery_sources=["nmap"],
            )
        )

        result = ProjectComparator().compare(old_project, new_project)

        self.assertIsInstance(result, ComparisonResult)
        self.assertEqual(len(result.added_devices), 1)
        self.assertEqual(len(result.removed_devices), 1)
        self.assertEqual(len(result.hostname_changed_devices), 2)
        self.assertEqual(len(result.ip_changed_devices), 1)
        self.assertEqual(result.summary_counts["added"], 1)
        self.assertEqual(result.summary_counts["removed"], 1)
        self.assertEqual(result.summary_counts["hostname_changed"], 2)
        self.assertEqual(result.summary_counts["ip_changed"], 1)


if __name__ == "__main__":
    unittest.main()
