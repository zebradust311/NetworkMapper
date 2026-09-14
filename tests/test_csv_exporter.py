import csv
import random
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from networkmapper.core.models import Device, DeviceType
from networkmapper.core.network_graph import NetworkGraph
from networkmapper.exporters import csv_exporter as csv_exporter_module
from networkmapper.exporters.csv_exporter import CsvExporter
from networkmapper.identity.models import CanonicalIdentity, IdentityCorroborationState, PropertyCorroboration
from networkmapper.identity.resolver import IdentityResolver
from networkmapper.observations.models import IdentityObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.project.models import Project


def _provenance(*, provider: str = "nmap", collection_method: str = "host-discovery") -> ObservationProvenance:
    return ObservationProvenance(
        provider=provider,
        collection_method=collection_method,
        observed_at=datetime(2026, 8, 19, 9, 0, 0),
        source_run="run-001",
    )


def _identity_observation(subject: str, property_name: str, value: str, **kwargs) -> IdentityObservation:
    return IdentityObservation(
        subject=subject, property_name=property_name, value=value, provenance=_provenance(**kwargs)
    )


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
                "Canonical Identity State",
                "Conflicting Identity Properties",
            ],
        )
        self.assertEqual(
            rows[1],
            ["192.168.1.10", "DC-01", "Cisco", "server", "nmap,snmp", "", "", "", "", "", ""],
        )
        self.assertEqual(rows[2], ["192.168.1.11", "", "", "unknown", "", "", "", "", "", "", ""])

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
                "",
                "",
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
        self.assertEqual(rows[1][6:9], ["", "", ""])


class CsvExporterCanonicalIdentityTest(unittest.TestCase):
    """FEAT-026 Slice 1: canonical identity summary columns, sourced from
    CanonicalPresentation and matched to device rows by subject == ip_address
    only (PLAN-026 Section 3.3)."""

    def _export_rows(self, project: Project) -> list[list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = str(Path(temp_dir) / "inventory.csv")
            CsvExporter().export(project, output_path)
            with open(output_path, newline="", encoding="utf-8") as csv_file:
                return list(csv.reader(csv_file))

    def test_matching_confirmed_identity_populates_state_and_leaves_conflicts_blank(self):
        project = Project(
            customer_name="Acme",
            canonical_identities=(
                CanonicalIdentity(
                    subject="192.168.1.10",
                    state=IdentityCorroborationState.CONFIRMED,
                    properties=(
                        PropertyCorroboration(
                            property_name="hostname",
                            state=IdentityCorroborationState.CONFIRMED,
                            observations=(_identity_observation("192.168.1.10", "hostname", "dc-01"),),
                        ),
                    ),
                ),
            ),
        )
        project.network_graph.add_device(Device(ip_address="192.168.1.10", hostname="DC-01"))

        rows = self._export_rows(project)

        self.assertEqual(rows[1][9], "confirmed")
        self.assertEqual(rows[1][10], "")

    def test_conflicting_property_is_named_but_its_values_are_not_emitted(self):
        project = Project(
            customer_name="Acme",
            canonical_identities=(
                CanonicalIdentity(
                    subject="192.168.1.10",
                    state=IdentityCorroborationState.CONFLICTING,
                    properties=(
                        PropertyCorroboration(
                            property_name="hostname",
                            state=IdentityCorroborationState.CONFLICTING,
                            observations=(
                                _identity_observation(
                                    "192.168.1.10", "hostname", "dc-01", provider="nmap"
                                ),
                                _identity_observation(
                                    "192.168.1.10", "hostname", "dc-99", provider="wmi"
                                ),
                            ),
                        ),
                        PropertyCorroboration(
                            property_name="domain",
                            state=IdentityCorroborationState.WEAK,
                            observations=(_identity_observation("192.168.1.10", "domain", "corp.local"),),
                        ),
                    ),
                ),
            ),
        )
        project.network_graph.add_device(Device(ip_address="192.168.1.10", hostname="DC-01"))

        rows = self._export_rows(project)

        self.assertEqual(rows[1][9], "conflicting")
        self.assertEqual(rows[1][10], "hostname")
        joined_csv_text = ",".join(rows[1])
        self.assertNotIn("dc-01", joined_csv_text)
        self.assertNotIn("dc-99", joined_csv_text)

    def test_multiple_conflicting_properties_preserve_tuple_order_without_resorting(self):
        project = Project(
            customer_name="Acme",
            canonical_identities=(
                CanonicalIdentity(
                    subject="192.168.1.10",
                    state=IdentityCorroborationState.CONFLICTING,
                    properties=(
                        PropertyCorroboration(
                            property_name="zeta_prop",
                            state=IdentityCorroborationState.CONFLICTING,
                            observations=(
                                _identity_observation("192.168.1.10", "zeta_prop", "a", provider="nmap"),
                                _identity_observation("192.168.1.10", "zeta_prop", "b", provider="wmi"),
                            ),
                        ),
                        PropertyCorroboration(
                            property_name="alpha_prop",
                            state=IdentityCorroborationState.CONFLICTING,
                            observations=(
                                _identity_observation("192.168.1.10", "alpha_prop", "c", provider="nmap"),
                                _identity_observation("192.168.1.10", "alpha_prop", "d", provider="wmi"),
                            ),
                        ),
                    ),
                ),
            ),
        )
        project.network_graph.add_device(Device(ip_address="192.168.1.10", hostname="DC-01"))

        rows = self._export_rows(project)

        # zeta_prop precedes alpha_prop in the identity's own properties
        # tuple order (as CanonicalPresentation exposes it) — asserting this
        # exact, non-alphabetical order proves CsvExporter applies no sort.
        self.assertEqual(rows[1][10], "zeta_prop,alpha_prop")

    def test_device_with_no_matching_canonical_identity_leaves_both_columns_blank(self):
        project = Project(
            customer_name="Acme",
            canonical_identities=(
                CanonicalIdentity(
                    subject="192.168.1.99",
                    state=IdentityCorroborationState.CONFIRMED,
                    properties=(),
                ),
            ),
        )
        project.network_graph.add_device(Device(ip_address="192.168.1.10", hostname="DC-01"))

        rows = self._export_rows(project)

        self.assertEqual(rows[1][9], "")
        self.assertEqual(rows[1][10], "")

    def test_canonical_identity_with_no_matching_device_creates_no_extra_row(self):
        project = Project(
            customer_name="Acme",
            canonical_identities=(
                CanonicalIdentity(
                    subject="192.168.1.99",
                    state=IdentityCorroborationState.CONFIRMED,
                    properties=(),
                ),
            ),
        )
        project.network_graph.add_device(Device(ip_address="192.168.1.10", hostname="DC-01"))

        rows = self._export_rows(project)

        # header + exactly one device row — no synthetic row for the
        # unmatched canonical identity (PLAN-026 Section 3.3).
        self.assertEqual(len(rows), 2)

    def test_matching_is_by_subject_equals_ip_address_only_not_hostname_or_mac(self):
        project = Project(
            customer_name="Acme",
            canonical_identities=(
                # Subject equals the device's hostname/MAC, not its IP —
                # must not match under PLAN-026 Section 3.3's sole rule.
                CanonicalIdentity(
                    subject="DC-01",
                    state=IdentityCorroborationState.CONFIRMED,
                    properties=(),
                ),
                CanonicalIdentity(
                    subject="AA:BB:CC:DD:EE:FF",
                    state=IdentityCorroborationState.CONFIRMED,
                    properties=(),
                ),
            ),
        )
        project.network_graph.add_device(
            Device(ip_address="192.168.1.10", hostname="DC-01", mac_address="AA:BB:CC:DD:EE:FF")
        )

        rows = self._export_rows(project)

        self.assertEqual(rows[1][9], "")
        self.assertEqual(rows[1][10], "")

    def test_determinism_new_columns_independent_of_observation_input_order(self):
        device = Device(ip_address="192.168.1.10", hostname="DC-01")
        observations = (
            _identity_observation("192.168.1.10", "hostname", "dc-01", provider="nmap"),
            _identity_observation("192.168.1.10", "hostname", "dc-99", provider="wmi"),
            _identity_observation("192.168.1.10", "domain", "corp.local", provider="nmap"),
        )

        def _build_rows(ordered_observations):
            identities = IdentityResolver().resolve(ordered_observations)
            project = Project(customer_name="Acme", canonical_identities=identities)
            project.network_graph.add_device(device)
            return self._export_rows(project)

        unshuffled_rows = _build_rows(observations)
        shuffled = list(observations)
        random.Random(42).shuffle(shuffled)
        shuffled_rows = _build_rows(tuple(shuffled))

        self.assertEqual(unshuffled_rows[1][9], shuffled_rows[1][9])
        self.assertEqual(unshuffled_rows[1][10], shuffled_rows[1][10])


class CsvExporterNoReResolutionGuardTest(unittest.TestCase):
    """Mirrors CanonicalPresentationNoReResolutionGuardTest (PLAN-026 Section 7):
    CsvExporter must never import either resolver directly."""

    def test_module_does_not_import_either_resolver(self):
        self.assertFalse(hasattr(csv_exporter_module, "IdentityResolver"))
        self.assertFalse(hasattr(csv_exporter_module, "RelationshipResolver"))


if __name__ == "__main__":
    unittest.main()
