import unittest
from datetime import datetime

from networkmapper.identity.models import CanonicalIdentity, IdentityCorroborationState
from networkmapper.observations.models import IdentityObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.project.models import Project
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState


class ProjectObservationsTest(unittest.TestCase):
    """FEAT-007A/ARCH-017 Stage 2."""

    def test_observations_default_to_an_empty_list(self):
        project = Project(customer_name="Acme")

        self.assertEqual(project.observations, [])

    def test_project_owns_observations_passed_at_construction(self):
        observation = IdentityObservation(
            subject="10.0.0.1",
            property_name="hostname",
            value="dc-01",
            provenance=ObservationProvenance(
                provider="nmap",
                collection_method="host-discovery",
                observed_at=datetime(2026, 8, 18, 9, 0, 0),
                source_run="run-001",
            ),
        )

        project = Project(customer_name="Acme", observations=[observation])

        self.assertEqual(project.observations, [observation])

    def test_two_projects_do_not_share_the_default_observations_list(self):
        # Guards against the classic mutable-default-argument bug —
        # field(default_factory=list) must produce a fresh list per
        # instance, exactly like network_graph already does.
        first = Project(customer_name="Acme")
        second = Project(customer_name="Widgets")

        first.observations.append("not a real observation, just a sentinel")  # type: ignore[arg-type]

        self.assertEqual(second.observations, [])


class ProjectCanonicalOutputsTest(unittest.TestCase):
    """ARCH-019 Stage 2 / FEAT-009B."""

    def test_canonical_identities_and_relationships_default_to_empty_tuples(self):
        project = Project(customer_name="Acme")

        self.assertEqual(project.canonical_identities, ())
        self.assertEqual(project.canonical_relationships, ())

    def test_project_owns_canonical_identities_and_relationships_passed_at_construction(self):
        identity = CanonicalIdentity(
            subject="10.0.0.1", state=IdentityCorroborationState.WEAK, properties=()
        )
        relationship = CanonicalRelationship(
            subject="10.0.0.1",
            category="connected_to",
            state=RelationshipCorroborationState.WEAK,
            observations=(),
        )

        project = Project(
            customer_name="Acme",
            canonical_identities=(identity,),
            canonical_relationships=(relationship,),
        )

        self.assertEqual(project.canonical_identities, (identity,))
        self.assertEqual(project.canonical_relationships, (relationship,))


if __name__ == "__main__":
    unittest.main()
