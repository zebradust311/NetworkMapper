import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime

from networkmapper.observations import (
    IdentityObservation,
    ObservationProvenance,
    RelationshipObservation,
)


def _provenance(**overrides) -> ObservationProvenance:
    defaults = dict(
        provider="nmap",
        collection_method="smb-os-discovery",
        observed_at=datetime(2026, 8, 18, 9, 30, 0),
        source_run="run-001",
    )
    defaults.update(overrides)
    return ObservationProvenance(**defaults)


class ObservationProvenanceTest(unittest.TestCase):
    def test_construction_preserves_every_field(self):
        provenance = _provenance()

        self.assertEqual(provenance.provider, "nmap")
        self.assertEqual(provenance.collection_method, "smb-os-discovery")
        self.assertEqual(provenance.observed_at, datetime(2026, 8, 18, 9, 30, 0))
        self.assertEqual(provenance.source_run, "run-001")

    def test_is_immutable(self):
        provenance = _provenance()

        with self.assertRaises(FrozenInstanceError):
            provenance.provider = "snmp"

    def test_equality_is_value_based(self):
        self.assertEqual(_provenance(), _provenance())
        self.assertNotEqual(_provenance(), _provenance(provider="snmp"))

    def test_repr_includes_class_name_and_field_values(self):
        text = repr(_provenance())

        self.assertIn("ObservationProvenance", text)
        self.assertIn("nmap", text)
        self.assertIn("smb-os-discovery", text)

    def test_is_hashable(self):
        # Frozen dataclasses are hashable by default (ADR-011
        # Immutability) — a future retained-observation store could
        # rely on this for set/dict membership.
        {_provenance()}  # noqa: B018 - exercised for its side effect (hash())


class IdentityObservationTest(unittest.TestCase):
    def _observation(self, **overrides) -> IdentityObservation:
        defaults = dict(
            subject="192.168.1.10",
            property_name="mac_address",
            value="AA:BB:CC:DD:EE:FF",
            provenance=_provenance(),
        )
        defaults.update(overrides)
        return IdentityObservation(**defaults)

    def test_construction_preserves_every_field(self):
        provenance = _provenance()
        observation = self._observation(provenance=provenance)

        self.assertEqual(observation.subject, "192.168.1.10")
        self.assertEqual(observation.property_name, "mac_address")
        self.assertEqual(observation.value, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(observation.provenance, provenance)

    def test_is_immutable(self):
        observation = self._observation()

        with self.assertRaises(FrozenInstanceError):
            observation.value = "00:11:22:33:44:55"

    def test_equality_is_value_based(self):
        provenance = _provenance()
        first = self._observation(provenance=provenance)
        second = self._observation(provenance=provenance)
        different_subject = self._observation(provenance=provenance, subject="192.168.1.11")

        self.assertEqual(first, second)
        self.assertNotEqual(first, different_subject)

    def test_repr_includes_class_name_and_field_values(self):
        text = repr(self._observation())

        self.assertIn("IdentityObservation", text)
        self.assertIn("192.168.1.10", text)
        self.assertIn("mac_address", text)

    def test_is_hashable(self):
        {self._observation()}  # noqa: B018 - exercised for its side effect (hash())


class RelationshipObservationTest(unittest.TestCase):
    def _observation(self, **overrides) -> RelationshipObservation:
        defaults = dict(
            subject="192.168.1.1",
            related_subject="192.168.1.254",
            category="connected_to",
            provenance=_provenance(provider="lldp", collection_method="lldp-neighbor"),
        )
        defaults.update(overrides)
        return RelationshipObservation(**defaults)

    def test_construction_preserves_every_field(self):
        provenance = _provenance(provider="lldp", collection_method="lldp-neighbor")
        observation = self._observation(provenance=provenance)

        self.assertEqual(observation.subject, "192.168.1.1")
        self.assertEqual(observation.related_subject, "192.168.1.254")
        self.assertEqual(observation.category, "connected_to")
        self.assertEqual(observation.provenance, provenance)

    def test_is_immutable(self):
        observation = self._observation()

        with self.assertRaises(FrozenInstanceError):
            observation.category = "routes_through"

    def test_equality_is_value_based(self):
        provenance = _provenance(provider="lldp", collection_method="lldp-neighbor")
        first = self._observation(provenance=provenance)
        second = self._observation(provenance=provenance)
        different_category = self._observation(provenance=provenance, category="routes_through")

        self.assertEqual(first, second)
        self.assertNotEqual(first, different_category)

    def test_repr_includes_class_name_and_field_values(self):
        text = repr(self._observation())

        self.assertIn("RelationshipObservation", text)
        self.assertIn("192.168.1.1", text)
        self.assertIn("connected_to", text)

    def test_is_hashable(self):
        {self._observation()}  # noqa: B018 - exercised for its side effect (hash())


class NamingCollisionTest(unittest.TestCase):
    """Confirms the ADR-011 naming collision is actually resolved, not just documented."""

    def test_no_type_in_this_module_is_named_observation(self):
        import networkmapper.observations.models as observations_models

        self.assertFalse(hasattr(observations_models, "Observation"))

    def test_identity_and_relationship_observation_are_distinct_from_knowledge_observation(self):
        from networkmapper.knowledge.models import Observation as KnowledgeObservation

        self.assertNotEqual(IdentityObservation, KnowledgeObservation)
        self.assertNotEqual(RelationshipObservation, KnowledgeObservation)
        self.assertFalse(issubclass(IdentityObservation, KnowledgeObservation))
        self.assertFalse(issubclass(RelationshipObservation, KnowledgeObservation))


if __name__ == "__main__":
    unittest.main()
