import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from networkmapper.classification.device_classifier import DeviceClassifier
from networkmapper.core.models import Device, DeviceType, ServiceEvidence
from networkmapper.discovery.scan_profile import ScanProfile
from networkmapper.exporters.markdown_exporter import MarkdownExporter
from networkmapper.project.models import Project
from networkmapper.reporting.project_summary import ProjectSummary
from networkmapper.reporting.report_run import RunMetadata


class MarkdownExporterTest(unittest.TestCase):
    def _export(self, project: Project, *, run_metadata: RunMetadata | None = None) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = str(Path(temp_dir) / "project.md")
            MarkdownExporter().export(project, output_path, run_metadata=run_metadata)
            return Path(output_path).read_text(encoding="utf-8")

    def _device_section(self, markdown: str, heading: str) -> str:
        """Return the markdown slice for one device's "### {heading}" block,
        from its heading up to (but not including) the next "### " heading
        or end of document — independent of section/group ordering."""
        start = markdown.index(f"### {heading}")
        next_heading = markdown.find("### ", start + 1)
        end = next_heading if next_heading != -1 else len(markdown)
        return markdown[start:end]

    def _project(self) -> Project:
        return Project(
            customer_name="Acme",
            created_date=datetime(2026, 1, 1, 12, 0, 0),
            modified_date=datetime(2026, 1, 2, 12, 0, 0),
        )

    def test_export_creates_markdown_and_groups_devices_by_type(self):
        project = self._project()

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

        with patch.object(ProjectSummary, "from_project", return_value=fake_summary):
            markdown = self._export(project)

        self.assertIn("# Customer", markdown)
        self.assertIn("# Executive Summary", markdown)
        self.assertIn("# Classification Overview", markdown)
        self.assertIn("# Device Inventory", markdown)
        self.assertIn("# Appendices", markdown)
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

    def test_classification_overview_reports_no_unknown_devices(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(ip_address="10.0.0.5", hostname="dc-01", vendor="Unknown")
            )
        )

        markdown = self._export(project)

        overview = markdown[
            markdown.index("# Classification Overview") : markdown.index("# Device Inventory")
        ]
        self.assertIn("No UNKNOWN devices.", overview)

    def test_classification_overview_summarizes_unknown_devices(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(
                    ip_address="10.0.0.6",
                    hostname="mystery-01",
                    vendor="Acme Corp",
                    operating_system="10.0.14393",
                )
            )
        )
        project.network_graph.add_device(
            classifier.classify(
                Device(ip_address="10.0.0.7", hostname="mystery-02", vendor="Acme Corp")
            )
        )

        markdown = self._export(project)

        overview = markdown[
            markdown.index("# Classification Overview") : markdown.index("# Device Inventory")
        ]
        self.assertIn("Total UNKNOWN Devices: 2", overview)
        self.assertIn("UNKNOWN Devices as % of Total: 100.0%", overview)
        self.assertIn("## UNKNOWN Devices by Vendor", overview)
        self.assertIn("- Acme Corp: 2", overview)
        self.assertIn("## UNKNOWN Devices by Operating System (where known)", overview)
        self.assertIn("- 10.0.14393: 1", overview)
        self.assertIn("- Not Determined: 1", overview)

    def test_device_identity_omits_smb_fields_when_absent_and_shows_them_when_present(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(
                    ip_address="10.0.0.10",
                    hostname="dc-02",
                    mac_address="AA:BB:CC:DD:EE:02",
                    vendor="Unknown",
                    operating_system="Windows Server 2019 Standard 17763",
                    computer_name="DC02",
                    domain="corp.local",
                )
            )
        )
        project.network_graph.add_device(
            classifier.classify(
                Device(ip_address="10.0.0.11", hostname="printer-01", vendor="Brother")
            )
        )

        markdown = self._export(project)
        dc02_section = self._device_section(markdown, "dc-02")
        printer_section = self._device_section(markdown, "printer-01")

        self.assertIn("- Device Type: Server", dc02_section)
        self.assertIn("- IP Address: 10.0.0.10", dc02_section)
        self.assertIn("- Computer Name: DC02", dc02_section)
        self.assertIn("- Operating System: Windows Server 2019 Standard 17763", dc02_section)
        self.assertIn("- Domain: corp.local", dc02_section)
        self.assertIn("- MAC Address: AA:BB:CC:DD:EE:02", dc02_section)

        self.assertNotIn("Computer Name:", printer_section)
        self.assertNotIn("Operating System:", printer_section)
        self.assertNotIn("Domain:", printer_section)

    def test_device_evidence_renders_service_and_smb_signing_details(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(
                    ip_address="10.0.0.20",
                    hostname="fw-01",
                    vendor="Unknown",
                    smb_signing="disabled (dangerous, but default)",
                    services=[
                        ServiceEvidence(
                            port=443,
                            protocol="tcp",
                            service="https",
                            product="SonicOS",
                            version="7.0",
                            http_title="SonicWALL - Network Security Appliance",
                            tls_subject="commonName=SonicWALL",
                            tls_issuer="commonName=SonicWALL",
                            http_auth_realm="SonicWALL",
                        ),
                    ],
                )
            )
        )

        markdown = self._export(project)
        section = markdown[markdown.index("### fw-01") :]

        self.assertIn("**Evidence**", section)
        self.assertIn("Services:", section)
        self.assertIn("- 443/tcp https (SonicOS 7.0)", section)
        self.assertIn("  - HTTP Title: SonicWALL - Network Security Appliance", section)
        self.assertIn("  - TLS Subject: commonName=SonicWALL", section)
        self.assertIn("  - TLS Issuer: commonName=SonicWALL", section)
        self.assertIn("  - HTTP Authentication Realm: SonicWALL", section)
        self.assertIn("SMB Signing: disabled (dangerous, but default)", section)
        self.assertNotIn("No additional evidence collected.", section)

    def test_device_evidence_reports_none_collected_when_empty(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(ip_address="10.0.0.30", hostname="host-30", vendor="Unknown")
            )
        )

        markdown = self._export(project)
        section = markdown[markdown.index("### host-30") :]

        self.assertIn("No additional evidence collected.", section)
        self.assertNotIn("Services:", section)

    def test_classified_device_shows_only_the_matching_rule(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(ip_address="10.0.0.40", hostname="dc-03", vendor="Unknown")
            )
        )

        markdown = self._export(project)
        section = markdown[markdown.index("### dc-03") :]

        self.assertIn("**Classification**", section)
        self.assertIn("Final Device Type: Server", section)
        self.assertIn("Matching Rule: ServerHostnameRule", section)
        self.assertIn(
            "Reason: Hostname 'dc-03' matched known server naming convention.", section
        )
        self.assertNotIn("Evaluated rules:", section)
        self.assertNotIn("HypervisorHostnameRule", section)

    def test_unknown_device_shows_every_evaluated_rules_reason(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(ip_address="10.0.0.50", hostname="mystery-03", vendor="Unknown")
            )
        )

        markdown = self._export(project)
        section = markdown[markdown.index("### mystery-03") :]

        self.assertIn("Final Device Type: Unknown", section)
        self.assertIn("No rule matched. Evaluated rules:", section)
        self.assertIn("- ServerHostnameRule:", section)
        self.assertIn("- HypervisorHostnameRule:", section)
        self.assertIn("- DellWorkstationRule:", section)
        self.assertNotIn("Matching Rule:", section)

    def test_appendices_render_vendor_service_and_coverage_summaries(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(
                    ip_address="10.0.0.60",
                    hostname="dc-04",
                    vendor="Dell",
                    operating_system="Windows Server 2019 Standard 17763",
                    services=[
                        ServiceEvidence(port=445, protocol="tcp", service="microsoft-ds"),
                        ServiceEvidence(
                            port=443,
                            protocol="tcp",
                            service="https",
                            product="Apache httpd",
                            version="2.4.41",
                        ),
                    ],
                )
            )
        )

        markdown = self._export(project)
        appendices = markdown[markdown.index("# Appendices") :]

        self.assertIn("## Vendor Counts", appendices)
        self.assertIn("- Dell: 1", appendices)
        self.assertIn("## Service Counts", appendices)
        self.assertIn("- https: 1", appendices)
        self.assertIn("- microsoft-ds: 1", appendices)
        self.assertIn("## Discovery Evidence Coverage", appendices)
        self.assertIn("- Operating System: 1/1 devices", appendices)
        self.assertIn("- Product: 1/2 services", appendices)
        self.assertIn("- Version: 1/2 services", appendices)

    def test_appendices_handle_empty_vendor_and_service_data(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(Device(ip_address="10.0.0.70", hostname="host-70"))
        )

        markdown = self._export(project)
        appendices = markdown[markdown.index("# Appendices") :]

        self.assertIn("No vendor data collected.", appendices)
        self.assertIn("No service data collected.", appendices)

    def test_run_metadata_section_omitted_when_not_provided(self):
        markdown = self._export(self._project())

        self.assertNotIn("# Run Metadata", markdown)

    def test_run_metadata_section_renders_when_provided(self):
        run_metadata = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 57, 42),
            scan_profile=ScanProfile.STANDARD,
            customer_name="Acme",
            device_count=7,
            version="0.1.0",
        )

        markdown = self._export(self._project(), run_metadata=run_metadata)
        section = markdown[: markdown.index("# Customer")]

        self.assertIn("# Run Metadata", section)
        self.assertIn("- Report Generated: 2026-08-10 13:57:42", section)
        self.assertIn("- Scan Profile: STANDARD", section)
        self.assertIn("- Customer Name: Acme", section)
        self.assertIn("- Device Count: 7", section)
        self.assertIn("- NetworkMapper Version: 0.1.0", section)

    def test_run_metadata_shows_unknown_version_when_version_is_none(self):
        run_metadata = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 57, 42),
            scan_profile=ScanProfile.FAST,
            customer_name="Acme",
            device_count=0,
            version=None,
        )

        markdown = self._export(self._project(), run_metadata=run_metadata)
        section = markdown[: markdown.index("# Customer")]

        self.assertIn("- NetworkMapper Version: Unknown", section)

    def test_existing_report_content_is_unchanged_by_added_metadata(self):
        """REPORT-002: adding the Run Metadata section must not shift or
        alter any existing section's content, only prepend to the document."""
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(ip_address="10.0.0.80", hostname="dc-05", vendor="Unknown")
            )
        )

        without_metadata = self._export(project)
        run_metadata = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 57, 42),
            scan_profile=ScanProfile.STANDARD,
            customer_name="Acme",
            device_count=1,
        )
        with_metadata = self._export(project, run_metadata=run_metadata)

        self.assertTrue(with_metadata.endswith(without_metadata))


if __name__ == "__main__":
    unittest.main()
