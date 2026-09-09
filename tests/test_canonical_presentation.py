import random
import unittest
from datetime import datetime

from networkmapper.core.models import Device
from networkmapper.identity.models import (
    CanonicalIdentity,
    IdentityCorroborationState,
    PropertyCorroboration,
)
from networkmapper.identity.resolver import IdentityResolver
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.project.models import Project
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState
from networkmapper.relationships.resolver import RelationshipResolver
from networkmapper.reporting.canonical_presentation import CanonicalPresentation


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


class CanonicalPresentationEmptyProjectTest(unittest.TestCase):
    def test_empty_project_produces_no_identities_or_relationships(self):
        project = Project(customer_name="Acme")

        presentation = CanonicalPresentation.from_project(project)

        self.assertEqual(presentation.identities, ())
        self.assertEqual(presentation.relationships, ())


class CanonicalPresentationIdentityTest(unittest.TestCase):
    def test_unmatched_subject_falls_back_to_raw_subject_and_is_not_dropped(self):
        identity = CanonicalIdentity(
            subject="10.0.0.1",
            state=IdentityCorroborationState.WEAK,
            properties=(
                PropertyCorroboration(
                    property_name="hostname",
                    state=IdentityCorroborationState.WEAK,
                    observations=(_identity_observation("10.0.0.1", "hostname", "dc-01"),),
                ),
            ),
        )
        project = Project(customer_name="Acme", canonical_identities=(identity,))

        presentation = CanonicalPresentation.from_project(project)

        self.assertEqual(len(presentation.identities), 1)
        rendered = presentation.identities[0]
        self.assertEqual(rendered.subject, "10.0.0.1")
        self.assertIsNone(rendered.device)
        self.assertEqual(rendered.state, IdentityCorroborationState.WEAK)
        self.assertEqual(len(rendered.properties), 1)
        self.assertEqual(rendered.properties[0].property_name, "hostname")
        self.assertEqual(len(rendered.properties[0].values), 1)
        self.assertEqual(rendered.properties[0].values[0].value, "dc-01")
        self.assertEqual(len(rendered.properties[0].values[0].observations), 1)

    def test_matched_subject_is_enriched_with_device(self):
        device = Device(ip_address="10.0.0.1", hostname="DC1")
        identity = CanonicalIdentity(
            subject="10.0.0.1", state=IdentityCorroborationState.CONFIRMED, properties=()
        )
        project = Project(customer_name="Acme", canonical_identities=(identity,))
        project.network_graph.add_device(device)

        presentation = CanonicalPresentation.from_project(project)

        self.assertIs(presentation.identities[0].device, device)

    def test_conflicting_property_preserves_every_distinct_value(self):
        observations = (
            _identity_observation(
                "10.0.0.1", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"
            ),
            _identity_observation(
                "10.0.0.1", "hostname", "dc-99", provider="wmi", collection_method="Win32_ComputerSystem"
            ),
        )
        identity = CanonicalIdentity(
            subject="10.0.0.1",
            state=IdentityCorroborationState.CONFLICTING,
            properties=(
                PropertyCorroboration(
                    property_name="hostname",
                    state=IdentityCorroborationState.CONFLICTING,
                    observations=observations,
                ),
            ),
        )
        project = Project(customer_name="Acme", canonical_identities=(identity,))

        presentation = CanonicalPresentation.from_project(project)

        values = presentation.identities[0].properties[0].values
        self.assertEqual(len(values), 2)
        self.assertEqual({value.value for value in values}, {"dc-01", "dc-99"})

    def test_property_value_grouping_preserves_resolver_order_without_dropping_observations(self):
        observations = (
            _identity_observation(
                "10.0.0.1", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"
            ),
            _identity_observation(
                "10.0.0.1", "hostname", "dc-01", provider="snmp", collection_method="sysName"
            ),
        )
        identity = CanonicalIdentity(
            subject="10.0.0.1",
            state=IdentityCorroborationState.CONFIRMED,
            properties=(
                PropertyCorroboration(
                    property_name="hostname",
                    state=IdentityCorroborationState.CONFIRMED,
                    observations=observations,
                ),
            ),
        )
        project = Project(customer_name="Acme", canonical_identities=(identity,))

        presentation = CanonicalPresentation.from_project(project)

        values = presentation.identities[0].properties[0].values
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].observations, observations)


class CanonicalPresentationRelationshipTest(unittest.TestCase):
    def test_unmatched_endpoints_fall_back_to_raw_subjects(self):
        relationship = CanonicalRelationship(
            subject="10.0.0.1",
            category="arp_neighbor",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("10.0.0.1", "10.0.0.2", "arp_neighbor"),),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        presentation = CanonicalPresentation.from_project(project)

        rendered = presentation.relationships[0]
        self.assertEqual(rendered.subject, "10.0.0.1")
        self.assertIsNone(rendered.device)
        self.assertEqual(rendered.category, "arp_neighbor")
        self.assertEqual(rendered.category_label, "ARP Neighbor")
        self.assertEqual(len(rendered.related), 1)
        self.assertEqual(rendered.related[0].related_subject, "10.0.0.2")
        self.assertIsNone(rendered.related[0].device)

    def test_matched_endpoints_are_enriched_with_devices(self):
        subject_device = Device(ip_address="10.0.0.1", hostname="SW1")
        related_device = Device(ip_address="10.0.0.2", hostname="SW2")
        relationship = CanonicalRelationship(
            subject="10.0.0.1",
            category="connected_to",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("10.0.0.1", "10.0.0.2", "connected_to"),),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))
        project.network_graph.add_device(subject_device)
        project.network_graph.add_device(related_device)

        presentation = CanonicalPresentation.from_project(project)

        rendered = presentation.relationships[0]
        self.assertIs(rendered.device, subject_device)
        self.assertIs(rendered.related[0].device, related_device)

    def test_conflicting_relationship_preserves_every_distinct_related_subject(self):
        observations = (
            _relationship_observation(
                "10.0.0.1", "10.0.0.2", "arp_neighbor", provider="nmap", collection_method="arp-scan"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.9", "arp_neighbor", provider="snmp", collection_method="ipNetToMediaTable"
            ),
        )
        relationship = CanonicalRelationship(
            subject="10.0.0.1",
            category="arp_neighbor",
            state=RelationshipCorroborationState.CONFLICTING,
            observations=observations,
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        presentation = CanonicalPresentation.from_project(project)

        related_subjects = {related.related_subject for related in presentation.relationships[0].related}
        self.assertEqual(related_subjects, {"10.0.0.2", "10.0.0.9"})

    def test_unknown_category_falls_back_to_deterministic_generic_label(self):
        relationship = CanonicalRelationship(
            subject="10.0.0.1",
            category="cdp_neighbor",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("10.0.0.1", "10.0.0.2", "cdp_neighbor"),),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        presentation = CanonicalPresentation.from_project(project)

        self.assertEqual(presentation.relationships[0].category_label, "Cdp Neighbor")

    def test_connected_to_label_carries_no_provider_suffix(self):
        """Architect-review correction (PLAN-025): the category label
        describes the canonical category, never the evidence provider
        currently producing it — no "(LLDP)" suffix, even though LLDP is
        the only current provider resolving to this category."""
        relationship = CanonicalRelationship(
            subject="10.0.0.1",
            category="connected_to",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("10.0.0.1", "10.0.0.2", "connected_to"),),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        presentation = CanonicalPresentation.from_project(project)

        self.assertEqual(presentation.relationships[0].category_label, "Connected To")

    def test_bridge_fdb_label(self):
        relationship = CanonicalRelationship(
            subject="10.0.0.1",
            category="bridge_fdb",
            state=RelationshipCorroborationState.WEAK,
            observations=(_relationship_observation("10.0.0.1", "10.0.0.2", "bridge_fdb"),),
        )
        project = Project(customer_name="Acme", canonical_relationships=(relationship,))

        presentation = CanonicalPresentation.from_project(project)

        self.assertEqual(presentation.relationships[0].category_label, "Bridge Forwarding Entry")


class CanonicalPresentationDeterminismTest(unittest.TestCase):
    def test_presentation_is_independent_of_input_observation_order(self):
        observations = [
            _identity_observation(
                "10.0.0.1", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"
            ),
            _identity_observation(
                "10.0.0.1", "hostname", "dc-01", provider="snmp", collection_method="sysName"
            ),
            _identity_observation("10.0.0.2", "hostname", "sw-01"),
            _relationship_observation(
                "10.0.0.1", "10.0.0.2", "arp_neighbor", provider="nmap", collection_method="arp-scan"
            ),
        ]

        def build_presentation(ordered_observations):
            identities = IdentityResolver().resolve(ordered_observations)
            relationships = RelationshipResolver().resolve(ordered_observations, identities)
            project = Project(
                customer_name="Acme",
                canonical_identities=identities,
                canonical_relationships=relationships,
            )
            return CanonicalPresentation.from_project(project)

        baseline = build_presentation(observations)

        shuffled = list(observations)
        random.Random(7).shuffle(shuffled)
        shuffled_presentation = build_presentation(shuffled)

        self.assertEqual(shuffled_presentation, baseline)


class CanonicalPresentationNoReResolutionGuardTest(unittest.TestCase):
    def test_module_does_not_import_either_resolver(self):
        import networkmapper.reporting.canonical_presentation as module

        self.assertFalse(hasattr(module, "IdentityResolver"))
        self.assertFalse(hasattr(module, "RelationshipResolver"))


if __name__ == "__main__":
    unittest.main()
