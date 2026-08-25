import unittest
from datetime import datetime

from networkmapper.identity.mac_index import build_mac_index
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance


def _identity_observation(
    subject: str, property_name: str, value: str, provider: str = "nmap", collection_method: str = "host-discovery"
) -> IdentityObservation:
    return IdentityObservation(
        subject=subject,
        property_name=property_name,
        value=value,
        provenance=ObservationProvenance(
            provider=provider,
            collection_method=collection_method,
            observed_at=datetime(2026, 8, 25, 9, 0, 0),
            source_run="mac-index-test-run",
        ),
    )


def _relationship_observation(subject: str, related_subject: str, category: str = "arp_neighbor") -> RelationshipObservation:
    return RelationshipObservation(
        subject=subject,
        related_subject=related_subject,
        category=category,
        provenance=ObservationProvenance(
            provider="snmp",
            collection_method="ipNetToPhysicalTable",
            observed_at=datetime(2026, 8, 25, 9, 0, 0),
            source_run="mac-index-test-run",
        ),
    )


class BuildMacIndexTest(unittest.TestCase):
    def test_empty_input_produces_an_empty_index(self):
        self.assertEqual(build_mac_index([]), {})

    def test_one_mac_maps_to_one_subject(self):
        observation = _identity_observation("10.0.0.1", "mac_address", "AA:BB:CC:DD:EE:FF")

        index = build_mac_index([observation])

        self.assertEqual(index, {"AA:BB:CC:DD:EE:FF": frozenset({"10.0.0.1"})})

    def test_same_mac_corroborated_by_multiple_observations_for_the_same_subject_stays_size_one(self):
        observations = [
            _identity_observation("10.0.0.1", "mac_address", "AA:BB:CC:DD:EE:FF", provider="nmap", collection_method="host-discovery"),
            _identity_observation("10.0.0.1", "mac_address", "AA:BB:CC:DD:EE:FF", provider="snmp", collection_method="ipNetToPhysicalTable"),
        ]

        index = build_mac_index(observations)

        self.assertEqual(index["AA:BB:CC:DD:EE:FF"], frozenset({"10.0.0.1"}))
        self.assertEqual(len(index["AA:BB:CC:DD:EE:FF"]), 1)

    def test_same_mac_claimed_by_multiple_subjects_is_never_collapsed(self):
        observations = [
            _identity_observation("10.0.0.1", "mac_address", "AA:BB:CC:DD:EE:FF"),
            _identity_observation("10.0.0.2", "mac_address", "AA:BB:CC:DD:EE:FF"),
        ]

        index = build_mac_index(observations)

        self.assertEqual(index["AA:BB:CC:DD:EE:FF"], frozenset({"10.0.0.1", "10.0.0.2"}))
        self.assertEqual(len(index["AA:BB:CC:DD:EE:FF"]), 2)

    def test_a_subject_with_no_mac_observation_is_simply_absent(self):
        observations = [
            _identity_observation("10.0.0.1", "mac_address", "AA:BB:CC:DD:EE:FF"),
            _identity_observation("10.0.0.2", "hostname", "dc-02"),
        ]

        index = build_mac_index(observations)

        self.assertEqual(list(index.keys()), ["AA:BB:CC:DD:EE:FF"])
        self.assertNotIn("dc-02", index)

    def test_relationship_observations_are_ignored_not_erroring(self):
        observations = [
            _identity_observation("10.0.0.1", "mac_address", "AA:BB:CC:DD:EE:FF"),
            _relationship_observation("10.0.0.1", "10.0.0.2"),
        ]

        index = build_mac_index(observations)

        self.assertEqual(index, {"AA:BB:CC:DD:EE:FF": frozenset({"10.0.0.1"})})

    def test_non_mac_property_observations_are_ignored(self):
        observations = [_identity_observation("10.0.0.1", "hostname", "dc-01")]

        index = build_mac_index(observations)

        self.assertEqual(index, {})

    def test_order_independence(self):
        forward = [
            _identity_observation("10.0.0.1", "mac_address", "AA:BB:CC:DD:EE:FF"),
            _identity_observation("10.0.0.2", "mac_address", "AA:BB:CC:DD:EE:FF"),
        ]
        reversed_order = list(reversed(forward))

        self.assertEqual(build_mac_index(forward), build_mac_index(reversed_order))


if __name__ == "__main__":
    unittest.main()
