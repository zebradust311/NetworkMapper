import csv
import random
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from networkmapper.core.models import Device
from networkmapper.exporters import relationship_csv_exporter as relationship_csv_exporter_module
from networkmapper.exporters.relationship_csv_exporter import RelationshipCsvExporter
from networkmapper.identity.models import CanonicalIdentity, IdentityCorroborationState
from networkmapper.observations.models import RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.project.models import Project
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState
from networkmapper.relationships.resolver import RelationshipResolver


def _resolvable_identity(subject: str) -> CanonicalIdentity:
    """A minimal CanonicalIdentity whose only role is making `subject`
    a valid relationship endpoint for RelationshipResolver.resolve()."""
    return CanonicalIdentity(subject=subject, state=IdentityCorroborationState.WEAK, properties=())


def _provenance(*, provider: str = "lldp", collection_method: str = "lldp-neighbor") -> ObservationProvenance:
    return ObservationProvenance(
        provider=provider,
        collection_method=collection_method,
        observed_at=datetime(2026, 8, 19, 9, 0, 0),
        source_run="run-001",
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


class RelationshipCsvExporterTest(unittest.TestCase):
    def _export_rows(self, project: Project) -> list[list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = str(Path(temp_dir) / "relationships.csv")
            RelationshipCsvExporter().export(project, output_path)
            with open(output_path, newline="", encoding="utf-8") as csv_file:
                return list(csv.reader(csv_file))

    def test_header_row(self):
        project = Project(customer_name="Acme")

        rows = self._export_rows(project)

        self.assertEqual(
            rows[0],
            [
                "Subject",
                "Subject Hostname",
                "Category",
                "Related Subject",
                "Related Subject Hostname",
                "Corroboration State",
                "Provenance",
            ],
        )

    def test_empty_relationship_set_emits_header_only_file(self):
        project = Project(customer_name="Acme")

        rows = self._export_rows(project)

        self.assertEqual(len(rows), 1)

    def test_one_canonical_relationship_one_related_subject_produces_one_row(self):
        relationship = CanonicalRelationship(
            subject="192.168.1.10",
            category="connected_to",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("192.168.1.10", "192.168.1.20", "connected_to"),),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        rows = self._export_rows(project)

        self.assertEqual(len(rows), 2)
        self.assertEqual(
            rows[1],
            ["192.168.1.10", "", "connected_to", "192.168.1.20", "", "weak", "lldp/lldp-neighbor"],
        )

    def test_confirmed_state_passes_through_unmodified(self):
        relationship = CanonicalRelationship(
            subject="192.168.1.10",
            category="connected_to",
            state=RelationshipCorroborationState.CONFIRMED,
            observations=(
                _relationship_observation(
                    "192.168.1.10", "192.168.1.20", "connected_to", provider="lldp"
                ),
                _relationship_observation(
                    "192.168.1.10", "192.168.1.20", "connected_to", provider="snmp"
                ),
            ),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        rows = self._export_rows(project)

        self.assertEqual(rows[1][5], "confirmed")

    def test_conflicting_relationship_expands_to_one_row_per_distinct_related_subject(self):
        relationship = CanonicalRelationship(
            subject="192.168.1.10",
            category="connected_to",
            state=RelationshipCorroborationState.CONFLICTING,
            observations=(
                _relationship_observation(
                    "192.168.1.10", "192.168.1.20", "connected_to", provider="lldp"
                ),
                _relationship_observation(
                    "192.168.1.10", "192.168.1.30", "connected_to", provider="snmp"
                ),
            ),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        rows = self._export_rows(project)

        self.assertEqual(len(rows), 3)
        related_subjects = {row[3] for row in rows[1:]}
        self.assertEqual(related_subjects, {"192.168.1.20", "192.168.1.30"})
        for row in rows[1:]:
            self.assertEqual(row[0], "192.168.1.10")
            self.assertEqual(row[2], "connected_to")
            self.assertEqual(row[5], "conflicting")

    def test_multiple_observations_for_one_related_subject_do_not_create_duplicate_rows(self):
        relationship = CanonicalRelationship(
            subject="192.168.1.10",
            category="connected_to",
            state=RelationshipCorroborationState.CONFIRMED,
            observations=(
                _relationship_observation(
                    "192.168.1.10", "192.168.1.20", "connected_to", provider="lldp"
                ),
                _relationship_observation(
                    "192.168.1.10", "192.168.1.20", "connected_to", provider="snmp"
                ),
            ),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        rows = self._export_rows(project)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][6], "lldp/lldp-neighbor,snmp/lldp-neighbor")

    def test_provenance_deduplicates_exact_provider_collection_method_pairs(self):
        relationship = CanonicalRelationship(
            subject="192.168.1.10",
            category="connected_to",
            state=RelationshipCorroborationState.CONFIRMED,
            observations=(
                _relationship_observation(
                    "192.168.1.10", "192.168.1.20", "connected_to", provider="lldp"
                ),
                _relationship_observation(
                    "192.168.1.10", "192.168.1.20", "connected_to", provider="lldp"
                ),
            ),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        rows = self._export_rows(project)

        self.assertEqual(rows[1][6], "lldp/lldp-neighbor")

    def test_subject_hostname_enrichment_when_device_exists(self):
        relationship = CanonicalRelationship(
            subject="192.168.1.10",
            category="connected_to",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("192.168.1.10", "192.168.1.20", "connected_to"),),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))
        project.network_graph.add_device(Device(ip_address="192.168.1.10", hostname="SW-01"))

        rows = self._export_rows(project)

        self.assertEqual(rows[1][1], "SW-01")

    def test_related_subject_hostname_enrichment_when_device_exists(self):
        relationship = CanonicalRelationship(
            subject="192.168.1.10",
            category="connected_to",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("192.168.1.10", "192.168.1.20", "connected_to"),),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))
        project.network_graph.add_device(Device(ip_address="192.168.1.20", hostname="SW-02"))

        rows = self._export_rows(project)

        self.assertEqual(rows[1][4], "SW-02")

    def test_missing_device_enrichment_leaves_hostname_blank(self):
        relationship = CanonicalRelationship(
            subject="192.168.1.10",
            category="connected_to",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("192.168.1.10", "192.168.1.20", "connected_to"),),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        rows = self._export_rows(project)

        self.assertEqual(rows[1][1], "")
        self.assertEqual(rows[1][4], "")

    def test_unknown_category_exports_safely(self):
        relationship = CanonicalRelationship(
            subject="192.168.1.10",
            category="future_category",
            state=RelationshipCorroborationState.WEAK,
            observations=(
                _relationship_observation("192.168.1.10", "192.168.1.20", "future_category"),
            ),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        rows = self._export_rows(project)

        self.assertEqual(rows[1][2], "future_category")

    def test_symmetric_double_weak_relationships_remain_two_separate_row_groups(self):
        forward = CanonicalRelationship(
            subject="192.168.1.10",
            category="connected_to",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("192.168.1.10", "192.168.1.20", "connected_to"),),
        )
        reverse = CanonicalRelationship(
            subject="192.168.1.20",
            category="connected_to",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("192.168.1.20", "192.168.1.10", "connected_to"),),
        )
        project = Project(customer_name="Acme", canonical_relationships=(forward, reverse))

        rows = self._export_rows(project)

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][5], "weak")
        self.assertEqual(rows[2][5], "weak")
        subjects = {(row[0], row[3]) for row in rows[1:]}
        self.assertEqual(subjects, {("192.168.1.10", "192.168.1.20"), ("192.168.1.20", "192.168.1.10")})

    def test_provenance_determinism_independent_of_observation_input_order(self):
        observations = (
            _relationship_observation("192.168.1.10", "192.168.1.20", "connected_to", provider="lldp"),
            _relationship_observation("192.168.1.10", "192.168.1.30", "connected_to", provider="snmp"),
        )
        identities = (
            _resolvable_identity("192.168.1.10"),
            _resolvable_identity("192.168.1.20"),
            _resolvable_identity("192.168.1.30"),
        )

        def _build_rows(ordered_observations):
            relationships = RelationshipResolver().resolve(ordered_observations, identities)
            project = Project(customer_name="Acme", canonical_relationships=relationships)
            return self._export_rows(project)

        unshuffled_rows = _build_rows(observations)
        shuffled = list(observations)
        random.Random(42).shuffle(shuffled)
        shuffled_rows = _build_rows(tuple(shuffled))

        unshuffled_provenance = {(row[0], row[2], row[3]): row[6] for row in unshuffled_rows[1:]}
        shuffled_provenance = {(row[0], row[2], row[3]): row[6] for row in shuffled_rows[1:]}
        self.assertEqual(unshuffled_provenance, shuffled_provenance)


class RelationshipCsvExporterNoReResolutionGuardTest(unittest.TestCase):
    """Mirrors CsvExporterNoReResolutionGuardTest (FEAT-026, PLAN-027 Section 11
    item 14): RelationshipCsvExporter must never import either resolver."""

    def test_module_does_not_import_either_resolver(self):
        self.assertFalse(hasattr(relationship_csv_exporter_module, "IdentityResolver"))
        self.assertFalse(hasattr(relationship_csv_exporter_module, "RelationshipResolver"))


if __name__ == "__main__":
    unittest.main()
