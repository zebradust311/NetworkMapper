import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from networkmapper.classification.device_classifier import DeviceClassifier
from networkmapper.core.models import Device, DeviceType, ServiceEvidence
from networkmapper.discovery.scan_profile import ScanProfile
from networkmapper.exporters.markdown_exporter import MarkdownExporter
from networkmapper.identity.models import (
    CanonicalIdentity,
    IdentityCorroborationState,
    PropertyCorroboration,
)
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.project.models import Project
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState
from networkmapper.reporting.project_summary import ProjectSummary
from networkmapper.reporting.report_run import RunMetadata


def _provenance(
    *,
    provider: str = "nmap",
    collection_method: str = "host-discovery",
    source_run: str = "run-001",
) -> ObservationProvenance:
    return ObservationProvenance(
        provider=provider,
        collection_method=collection_method,
        observed_at=datetime(2026, 8, 19, 9, 0, 0),
        source_run=source_run,
    )


def _identity_observation(subject: str, property_name: str, value: str, **kwargs) -> IdentityObservation:
    return IdentityObservation(
        subject=subject, property_name=property_name, value=value, provenance=_provenance(**kwargs)
    )


def _relationship_observation(
    subject: str, related_subject: str, category: str, **kwargs
) -> RelationshipObservation:
    return RelationshipObservation(
        subject=subject,
        related_subject=related_subject,
        category=category,
        provenance=_provenance(**kwargs),
    )


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

    def test_device_evidence_renders_snmp_fields_when_present(self):
        """REPORT-003: SNMP evidence already stored on Device is surfaced
        alongside the device it describes, using user-facing labels
        rather than OID/protocol-centric names."""
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(
                    ip_address="10.0.0.25",
                    hostname="sw-core-02",
                    vendor="Unknown",
                    snmp_sys_descr="Cisco IOS Software, C2960 Software",
                    snmp_sys_object_id="1.3.6.1.4.1.9.1.516",
                    snmp_sys_location="Server Room A",
                    snmp_sys_contact="netops@example.com",
                    snmp_sys_uptime="391219825",
                )
            )
        )

        markdown = self._export(project)
        section = self._device_section(markdown, "sw-core-02")

        self.assertIn("SNMP Description: Cisco IOS Software, C2960 Software", section)
        self.assertIn("SNMP Location: Server Room A", section)
        self.assertIn("SNMP Contact: netops@example.com", section)
        self.assertIn("SNMP Uptime: 391219825", section)
        self.assertNotIn("No additional evidence collected.", section)
        # sysObjectID is canonical evidence for future knowledge
        # interpretation, not customer presentation -- must never appear.
        self.assertNotIn("1.3.6.1.4.1.9.1.516", section)
        self.assertNotIn("sysObjectID", section)
        self.assertNotIn("sys_object_id", section)

    def test_device_evidence_renders_only_populated_snmp_fields(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(
                    ip_address="10.0.0.26",
                    hostname="printer-02",
                    vendor="Unknown",
                    snmp_sys_descr="HP LaserJet 4250, Firmware Version: 08.061.3",
                )
            )
        )

        markdown = self._export(project)
        section = self._device_section(markdown, "printer-02")

        self.assertIn("SNMP Description: HP LaserJet 4250, Firmware Version: 08.061.3", section)
        self.assertNotIn("SNMP Location:", section)
        self.assertNotIn("SNMP Contact:", section)
        self.assertNotIn("SNMP Uptime:", section)

    def test_device_without_snmp_evidence_is_unaffected(self):
        project = self._project()
        classifier = DeviceClassifier()
        project.network_graph.add_device(
            classifier.classify(
                Device(ip_address="10.0.0.27", hostname="host-27", vendor="Unknown")
            )
        )

        markdown = self._export(project)
        section = self._device_section(markdown, "host-27")

        self.assertIn("No additional evidence collected.", section)
        self.assertNotIn("SNMP", section)

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

    # ------------------------------------------------------------------
    # Canonical Identity / Relationships (PLAN-025 Slice 1)
    # ------------------------------------------------------------------

    def test_canonical_identity_section_reports_no_evidence_when_empty(self):
        """A `Project` with the default, empty `canonical_identities` tuple
        (every pre-existing test in this file, implicitly) must render the
        new section gracefully rather than error or imply a resolved-empty
        conclusion (PLAN-025 Section 5's reachable empty case)."""
        markdown = self._export(self._project())

        self.assertIn("# Canonical Identity", markdown)
        self.assertIn("No canonical identity evidence collected.", markdown)

    def test_canonical_relationships_section_reports_no_evidence_when_empty(self):
        markdown = self._export(self._project())

        self.assertIn("# Canonical Relationships", markdown)
        self.assertIn("No canonical relationship evidence collected.", markdown)

    def test_canonical_identity_section_renders_state_value_device_and_provenance(self):
        project = self._project()
        project.network_graph.add_device(Device(ip_address="10.0.0.1", hostname="DC1"))
        project.canonical_identities = (
            CanonicalIdentity(
                subject="10.0.0.1",
                state=IdentityCorroborationState.CONFIRMED,
                properties=(
                    PropertyCorroboration(
                        property_name="hostname",
                        state=IdentityCorroborationState.CONFIRMED,
                        observations=(
                            _identity_observation(
                                "10.0.0.1", "hostname", "DC1", provider="nmap", collection_method="host-discovery"
                            ),
                            _identity_observation(
                                "10.0.0.1", "hostname", "DC1", provider="snmp", collection_method="sysName"
                            ),
                        ),
                    ),
                ),
            ),
        )

        markdown = self._export(project)
        section = markdown[markdown.index("# Canonical Identity") : markdown.index("# Canonical Relationships")]

        self.assertIn("## DC1 (10.0.0.1)", section)
        self.assertIn("- Corroboration State: Confirmed", section)
        self.assertIn("### hostname", section)
        self.assertIn("- Value: DC1", section)
        self.assertIn("nmap / host-discovery", section)
        self.assertIn("snmp / sysName", section)

    def test_canonical_identity_section_shows_unmatched_subject_and_all_conflicting_values(self):
        project = self._project()
        project.canonical_identities = (
            CanonicalIdentity(
                subject="10.0.0.9",
                state=IdentityCorroborationState.CONFLICTING,
                properties=(
                    PropertyCorroboration(
                        property_name="hostname",
                        state=IdentityCorroborationState.CONFLICTING,
                        observations=(
                            _identity_observation(
                                "10.0.0.9", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"
                            ),
                            _identity_observation(
                                "10.0.0.9", "hostname", "dc-99", provider="wmi", collection_method="Win32_ComputerSystem"
                            ),
                        ),
                    ),
                ),
            ),
        )

        markdown = self._export(project)
        section = markdown[markdown.index("# Canonical Identity") : markdown.index("# Canonical Relationships")]

        # No matching Device — the raw subject is the heading, never dropped.
        self.assertIn("## 10.0.0.9", section)
        self.assertNotIn("## 10.0.0.9 (", section)
        self.assertIn("- Corroboration State: Conflicting", section)
        # Both distinct conflicting values render; neither is collapsed away.
        self.assertIn("- Value: dc-01", section)
        self.assertIn("- Value: dc-99", section)

    def test_canonical_relationships_section_renders_direction_category_and_device_enrichment(self):
        project = self._project()
        project.network_graph.add_device(Device(ip_address="10.0.0.1", hostname="SW1"))
        project.network_graph.add_device(Device(ip_address="10.0.0.2", hostname="SW2"))
        project.canonical_relationships = (
            CanonicalRelationship(
                subject="10.0.0.1",
                category="connected_to",
                state=RelationshipCorroborationState.WEAK,
                observations=(
                    _relationship_observation(
                        "10.0.0.1", "10.0.0.2", "connected_to", provider="lldp", collection_method="lldp-neighbor"
                    ),
                ),
            ),
        )

        markdown = self._export(project)
        section = markdown[markdown.index("# Canonical Relationships") :]

        self.assertIn("## SW1 (10.0.0.1) — Connected To", section)
        self.assertIn("- Corroboration State: Weak", section)
        self.assertIn("SW1 (10.0.0.1) → SW2 (10.0.0.2)", section)
        self.assertIn("lldp / lldp-neighbor", section)
        # Architect-review correction: the label must not bake the current
        # evidence provider (LLDP) into the canonical category label itself.
        self.assertNotIn("Connected To (LLDP)", section)

    def test_canonical_relationships_section_shows_all_conflicting_related_subjects(self):
        project = self._project()
        project.canonical_relationships = (
            CanonicalRelationship(
                subject="10.0.0.1",
                category="arp_neighbor",
                state=RelationshipCorroborationState.CONFLICTING,
                observations=(
                    _relationship_observation(
                        "10.0.0.1", "10.0.0.2", "arp_neighbor", provider="nmap", collection_method="arp-scan"
                    ),
                    _relationship_observation(
                        "10.0.0.1", "10.0.0.9", "arp_neighbor", provider="snmp", collection_method="ipNetToMediaTable"
                    ),
                ),
            ),
        )

        markdown = self._export(project)
        section = markdown[markdown.index("# Canonical Relationships") :]

        self.assertIn("## 10.0.0.1 — ARP Neighbor", section)
        self.assertIn("- Corroboration State: Conflicting", section)
        self.assertIn("10.0.0.1 → 10.0.0.2", section)
        self.assertIn("10.0.0.1 → 10.0.0.9", section)

    def test_unknown_relationship_category_falls_back_to_generic_label(self):
        project = self._project()
        project.canonical_relationships = (
            CanonicalRelationship(
                subject="10.0.0.1",
                category="cdp_neighbor",
                state=RelationshipCorroborationState.WEAK,
                observations=(_relationship_observation("10.0.0.1", "10.0.0.2", "cdp_neighbor"),),
            ),
        )

        markdown = self._export(project)
        section = markdown[markdown.index("# Canonical Relationships") :]

        self.assertIn("Cdp Neighbor", section)

    def test_canonical_sections_do_not_move_or_alter_existing_report_content(self):
        """Adding the two new sections must be purely additive — every
        existing section's content is byte-for-byte unchanged."""
        project_without_canonical_data = self._project()
        classifier = DeviceClassifier()
        project_without_canonical_data.network_graph.add_device(
            classifier.classify(Device(ip_address="10.0.0.80", hostname="dc-05", vendor="Unknown"))
        )
        without_canonical_data = self._export(project_without_canonical_data)

        project_with_canonical_data = self._project()
        project_with_canonical_data.network_graph.add_device(
            classifier.classify(Device(ip_address="10.0.0.80", hostname="dc-05", vendor="Unknown"))
        )
        project_with_canonical_data.canonical_identities = (
            CanonicalIdentity(
                subject="10.0.0.80",
                state=IdentityCorroborationState.WEAK,
                properties=(
                    PropertyCorroboration(
                        property_name="hostname",
                        state=IdentityCorroborationState.WEAK,
                        observations=(_identity_observation("10.0.0.80", "hostname", "dc-05"),),
                    ),
                ),
            ),
        )
        with_canonical_data = self._export(project_with_canonical_data)

        pre_canonical_without = without_canonical_data[: without_canonical_data.index("# Canonical Identity")]
        pre_canonical_with = with_canonical_data[: with_canonical_data.index("# Canonical Identity")]
        self.assertEqual(pre_canonical_without, pre_canonical_with)

        post_canonical_without = without_canonical_data[without_canonical_data.index("# Appendices") :]
        post_canonical_with = with_canonical_data[with_canonical_data.index("# Appendices") :]
        self.assertEqual(post_canonical_without, post_canonical_with)


if __name__ == "__main__":
    unittest.main()
