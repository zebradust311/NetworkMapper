import random
import unittest
from datetime import datetime

from networkmapper.identity.models import CanonicalIdentity, IdentityCorroborationState
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState
from networkmapper.relationships.resolver import RelationshipResolver


def _identity(subject: str) -> CanonicalIdentity:
    return CanonicalIdentity(subject=subject, state=IdentityCorroborationState.WEAK, properties=())


def _relationship_observation(
    subject: str,
    related_subject: str,
    category: str,
    *,
    provider: str = "nmap",
    collection_method: str = "lldp-neighbor",
    source_run: str = "run-001",
) -> RelationshipObservation:
    return RelationshipObservation(
        subject=subject,
        related_subject=related_subject,
        category=category,
        provenance=ObservationProvenance(
            provider=provider,
            collection_method=collection_method,
            observed_at=datetime(2026, 8, 20, 9, 0, 0),
            source_run=source_run,
        ),
    )


class RelationshipResolverEmptyInputTest(unittest.TestCase):
    def test_no_observations_produces_no_relationships(self):
        relationships = RelationshipResolver().resolve([], [_identity("10.0.0.1")])

        self.assertEqual(relationships, ())

    def test_no_identities_produces_no_relationships(self):
        observation = _relationship_observation("10.0.0.1", "10.0.0.254", "connected_to")

        relationships = RelationshipResolver().resolve([observation], [])

        self.assertEqual(relationships, ())


class RelationshipResolverSingleObservationTest(unittest.TestCase):
    def test_a_single_resolved_observation_produces_a_weak_relationship(self):
        observation = _relationship_observation("10.0.0.1", "10.0.0.254", "connected_to")
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        relationships = RelationshipResolver().resolve([observation], identities)

        self.assertEqual(len(relationships), 1)
        relationship = relationships[0]
        self.assertEqual(relationship.subject, "10.0.0.1")
        self.assertEqual(relationship.category, "connected_to")
        self.assertEqual(relationship.state, RelationshipCorroborationState.WEAK)
        self.assertEqual(relationship.observations, (observation,))


class RelationshipResolverCorroborationTest(unittest.TestCase):
    def test_two_independent_sources_agreeing_confirm_the_relationship(self):
        observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="snmp", collection_method="bridge-mib"
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0].state, RelationshipCorroborationState.CONFIRMED)
        self.assertEqual(len(relationships[0].observations), 2)

    def test_duplicate_observations_from_the_same_source_do_not_confirm(self):
        # Same (provider, collection_method) reported twice — one
        # independent source, not two. ADR-013 Relationship Independence.
        observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0].state, RelationshipCorroborationState.WEAK)
        # Both raw observations are still retained, even though neither
        # upgraded the corroboration state.
        self.assertEqual(len(relationships[0].observations), 2)


class RelationshipResolverConflictTest(unittest.TestCase):
    def test_two_independent_sources_disagreeing_conflict(self):
        observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.253", "connected_to", provider="snmp", collection_method="cdp-neighbor"
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships), 1)
        relationship = relationships[0]
        self.assertEqual(relationship.state, RelationshipCorroborationState.CONFLICTING)
        # Neither conflicting observation is discarded.
        self.assertEqual(len(relationship.observations), 2)
        related_subjects = {observation.related_subject for observation in relationship.observations}
        self.assertEqual(related_subjects, {"10.0.0.254", "10.0.0.253"})

    def test_a_single_source_reporting_two_values_conflicts_on_its_own(self):
        # ARCH-018's Confidence States finding: CONFLICTING mirrors
        # IdentityResolver._resolve_property() field-for-field, which has
        # no independent-source-count gate — more than one distinct value
        # present among the group's retained observations is sufficient,
        # regardless of whether it originates from one source or several.
        observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.253", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships), 1)
        relationship = relationships[0]
        self.assertEqual(relationship.state, RelationshipCorroborationState.CONFLICTING)
        self.assertEqual(len(relationship.observations), 2)

    def test_a_second_source_agreeing_with_one_value_does_not_soften_the_conflict(self):
        # A second, independent source agreeing with one of the first
        # source's two values does not reduce the state to WEAK or
        # CONFIRMED: the group still has more than one distinct value
        # overall, so it remains CONFLICTING. All three observations
        # remain retained.
        observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.253", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="snmp", collection_method="bridge-mib"
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships), 1)
        relationship = relationships[0]
        self.assertEqual(relationship.state, RelationshipCorroborationState.CONFLICTING)
        self.assertEqual(len(relationship.observations), 3)
        self.assertEqual(set(relationship.observations), set(observations))


class RelationshipResolverEndpointResolutionTest(unittest.TestCase):
    def test_an_observation_with_an_unresolved_related_subject_produces_no_relationship(self):
        observation = _relationship_observation("10.0.0.1", "10.0.0.254", "connected_to")
        identities = [_identity("10.0.0.1")]  # 10.0.0.254 never resolves.

        relationships = RelationshipResolver().resolve([observation], identities)

        self.assertEqual(relationships, ())

    def test_an_observation_with_an_unresolved_subject_produces_no_relationship(self):
        observation = _relationship_observation("10.0.0.1", "10.0.0.254", "connected_to")
        identities = [_identity("10.0.0.254")]  # 10.0.0.1 never resolves.

        relationships = RelationshipResolver().resolve([observation], identities)

        self.assertEqual(relationships, ())

    def test_a_self_loop_observation_produces_no_relationship(self):
        observation = _relationship_observation("10.0.0.1", "10.0.0.1", "connected_to")
        identities = [_identity("10.0.0.1")]

        relationships = RelationshipResolver().resolve([observation], identities)

        self.assertEqual(relationships, ())

    def test_unresolved_and_self_loop_observations_do_not_contaminate_a_genuine_relationship(self):
        # Regression case for the ordering defect the ARCH-018 adversarial
        # review found: preprocessing must exclude these before grouping,
        # or they would land in the same (subject, category) group as the
        # genuine observation below and produce a false CONFLICTING state.
        observations = [
            _relationship_observation("10.0.0.1", "10.0.0.254", "connected_to"),
            _relationship_observation("10.0.0.1", "10.0.0.1", "connected_to"),
            _relationship_observation("10.0.0.1", "10.0.0.253", "connected_to"),  # 10.0.0.253 unresolved
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships), 1)
        relationship = relationships[0]
        self.assertEqual(relationship.state, RelationshipCorroborationState.WEAK)
        self.assertEqual(len(relationship.observations), 1)
        self.assertEqual(relationship.observations[0].related_subject, "10.0.0.254")


class RelationshipResolverDirectionalityTest(unittest.TestCase):
    def test_a_symmetric_category_reported_from_both_endpoints_does_not_corroborate_in_stage_1(self):
        # Known, accepted Stage 1 limitation (ARCH-018's Directionality
        # finding): no canonicalization exists yet, so a "connected_to"
        # claim reported from A's perspective and from B's perspective
        # land in two separate (subject, category) groups rather than
        # one. This is under-corroboration, never mis-corroboration — the
        # positive test proving that behavior is deliberate, not an
        # accidental gap.
        observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.254", "10.0.0.1", "connected_to", provider="snmp", collection_method="bridge-mib"
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships), 2)
        self.assertTrue(all(r.state == RelationshipCorroborationState.WEAK for r in relationships))
        subjects = {relationship.subject for relationship in relationships}
        self.assertEqual(subjects, {"10.0.0.1", "10.0.0.254"})


class RelationshipResolverGroupingTest(unittest.TestCase):
    def test_identity_observations_are_ignored_not_erroring(self):
        identity_observation = IdentityObservation(
            subject="10.0.0.1",
            property_name="hostname",
            value="dc-01",
            provenance=ObservationProvenance(
                provider="nmap",
                collection_method="host-discovery",
                observed_at=datetime(2026, 8, 20, 9, 0, 0),
                source_run="run-001",
            ),
        )
        relationship_observation = _relationship_observation("10.0.0.1", "10.0.0.254", "connected_to")
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        relationships = RelationshipResolver().resolve(
            [identity_observation, relationship_observation], identities
        )

        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0].subject, "10.0.0.1")
        self.assertEqual(len(relationships[0].observations), 1)

    def test_observations_are_grouped_by_subject_and_category_into_separate_relationships(self):
        observations = [
            _relationship_observation("10.0.0.1", "10.0.0.254", "connected_to"),
            _relationship_observation("10.0.0.1", "10.0.0.253", "hosts_service"),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships), 2)
        categories = {relationship.category for relationship in relationships}
        self.assertEqual(categories, {"connected_to", "hosts_service"})

    def test_output_is_sorted_by_subject_then_category_regardless_of_input_order(self):
        observations = [
            _relationship_observation("10.0.0.9", "10.0.0.1", "hosts_service"),
            _relationship_observation("10.0.0.1", "10.0.0.9", "connected_to"),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.9")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(
            [(r.subject, r.category) for r in relationships],
            [("10.0.0.1", "connected_to"), ("10.0.0.9", "hosts_service")],
        )


class RelationshipResolverProvenanceRetentionTest(unittest.TestCase):
    def test_original_observation_objects_are_preserved_unmodified(self):
        observation = _relationship_observation("10.0.0.1", "10.0.0.254", "connected_to", provider="nmap")
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        relationships = RelationshipResolver().resolve([observation], identities)

        retained = relationships[0].observations[0]
        self.assertIs(retained, observation)
        self.assertEqual(retained.provenance.provider, "nmap")


class RelationshipResolverDeterminismTest(unittest.TestCase):
    def test_resolve_is_order_independent_across_many_random_permutations(self):
        base_observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "connected_to", provider="snmp", collection_method="bridge-mib"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.253", "hosts_service", provider="nmap", collection_method="port-scan"
            ),
            _relationship_observation(
                "10.0.0.9", "10.0.0.1", "connected_to", provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.9", "10.0.0.2", "connected_to", provider="snmp", collection_method="cdp-neighbor"
            ),
        ]
        base_identities = [
            _identity("10.0.0.1"),
            _identity("10.0.0.254"),
            _identity("10.0.0.253"),
            _identity("10.0.0.9"),
            _identity("10.0.0.2"),
        ]

        baseline = RelationshipResolver().resolve(base_observations, base_identities)

        rng = random.Random(1234)
        for _ in range(20):
            shuffled_observations = list(base_observations)
            shuffled_identities = list(base_identities)
            rng.shuffle(shuffled_observations)
            rng.shuffle(shuffled_identities)

            result = RelationshipResolver().resolve(shuffled_observations, shuffled_identities)

            self.assertEqual(result, baseline)


if __name__ == "__main__":
    unittest.main()
