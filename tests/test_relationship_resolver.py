import random
import unittest
from datetime import datetime, timezone

from networkmapper.identity.models import CanonicalIdentity, IdentityCorroborationState
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.discovery.arp_neighbor_provider import ARP_NEIGHBOR_CATEGORY
from networkmapper.discovery.bridge_fdb_provider import BRIDGE_FDB_CATEGORY
from networkmapper.discovery.lldp_neighbor_provider import LLDP_NEIGHBOR_CATEGORY
from networkmapper.relationships.categories import (
    CATEGORY_CARDINALITY,
    DEFAULT_CARDINALITY,
    RelationshipCardinality,
    cardinality_for,
)
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState
from networkmapper.relationships.resolver import RelationshipResolver

# PLAN-028 D1: no production category is single-valued yet, so SINGLE
# semantics are exercised through an injected test-only policy.
_SINGLE_CATEGORY = "test_single_valued"
_SINGLE_POLICY = {_SINGLE_CATEGORY: RelationshipCardinality.SINGLE}


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
    observed_at: datetime = datetime(2026, 8, 20, 9, 0, 0),
) -> RelationshipObservation:
    return RelationshipObservation(
        subject=subject,
        related_subject=related_subject,
        category=category,
        provenance=ObservationProvenance(
            provider=provider,
            collection_method=collection_method,
            observed_at=observed_at,
            source_run=source_run,
        ),
    )


def _edges(relationships):
    """Map each canonical edge's related_subject to the edge (one subject/category)."""
    return {relationship.related_subject: relationship for relationship in relationships}


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
        self.assertEqual(relationship.related_subject, "10.0.0.254")
        self.assertEqual(relationship.cardinality, RelationshipCardinality.MULTIPLE)
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
        self.assertEqual(relationships[0].related_subject, "10.0.0.254")
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
        self.assertEqual(relationships[0].related_subject, "10.0.0.254")
        self.assertEqual(relationships[0].state, RelationshipCorroborationState.WEAK)
        # Both raw observations are still retained, even though neither
        # upgraded the corroboration state.
        self.assertEqual(len(relationships[0].observations), 2)


class RelationshipResolverSingleValuedConflictTest(unittest.TestCase):
    """SINGLE categories preserve today's corroboration semantics, but not
    today's output shape (PLAN-028 Section 2.1): each competing related
    subject is its own edge, and every such edge is CONFLICTING."""

    def test_two_independent_sources_disagreeing_conflict(self):
        observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", _SINGLE_CATEGORY, provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.253", _SINGLE_CATEGORY, provider="snmp", collection_method="cdp-neighbor"
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        relationships = RelationshipResolver(cardinality_policy=_SINGLE_POLICY).resolve(observations, identities)

        self.assertEqual(len(relationships), 2)
        self.assertEqual({r.related_subject for r in relationships}, {"10.0.0.254", "10.0.0.253"})
        for relationship in relationships:
            self.assertEqual(relationship.cardinality, RelationshipCardinality.SINGLE)
            self.assertEqual(relationship.state, RelationshipCorroborationState.CONFLICTING)
        # Neither conflicting observation is discarded.
        retained = {observation for r in relationships for observation in r.observations}
        self.assertEqual(retained, set(observations))

    def test_a_single_source_reporting_two_values_conflicts_on_its_own(self):
        # ARCH-018's Confidence States finding: CONFLICTING mirrors
        # IdentityResolver._resolve_property() field-for-field, which has
        # no independent-source-count gate — more than one distinct value
        # for a single-valued claim is sufficient, regardless of whether it
        # originates from one source or several.
        observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", _SINGLE_CATEGORY, provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.253", _SINGLE_CATEGORY, provider="nmap", collection_method="lldp-neighbor"
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        relationships = RelationshipResolver(cardinality_policy=_SINGLE_POLICY).resolve(observations, identities)

        self.assertEqual(len(relationships), 2)
        self.assertTrue(all(r.state == RelationshipCorroborationState.CONFLICTING for r in relationships))
        self.assertTrue(all(len(r.observations) == 1 for r in relationships))

    def test_a_second_source_agreeing_with_one_value_does_not_soften_the_conflict(self):
        # A second, independent source agreeing with one of the first
        # source's two values does not lift that edge to CONFIRMED: the
        # single-valued group still names more than one related subject,
        # so every edge — including the one two sources support — remains
        # CONFLICTING. All three observations remain retained.
        observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", _SINGLE_CATEGORY, provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.253", _SINGLE_CATEGORY, provider="nmap", collection_method="lldp-neighbor"
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", _SINGLE_CATEGORY, provider="snmp", collection_method="bridge-mib"
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        relationships = RelationshipResolver(cardinality_policy=_SINGLE_POLICY).resolve(observations, identities)

        edges = _edges(relationships)
        self.assertEqual(set(edges), {"10.0.0.254", "10.0.0.253"})
        self.assertEqual(edges["10.0.0.254"].state, RelationshipCorroborationState.CONFLICTING)
        self.assertEqual(edges["10.0.0.253"].state, RelationshipCorroborationState.CONFLICTING)
        self.assertEqual(len(edges["10.0.0.254"].observations), 2)
        retained = {observation for r in relationships for observation in r.observations}
        self.assertEqual(retained, set(observations))

    def test_same_source_repeated_across_runs_stays_weak(self):
        observations = [
            _relationship_observation("10.0.0.1", "10.0.0.254", _SINGLE_CATEGORY, source_run="run-001"),
            _relationship_observation("10.0.0.1", "10.0.0.254", _SINGLE_CATEGORY, source_run="run-002"),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        relationships = RelationshipResolver(cardinality_policy=_SINGLE_POLICY).resolve(observations, identities)

        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0].state, RelationshipCorroborationState.WEAK)
        self.assertEqual(len(relationships[0].observations), 2)

    def test_two_sources_agreeing_on_one_value_confirm_a_single_valued_edge(self):
        observations = [
            _relationship_observation("10.0.0.1", "10.0.0.254", _SINGLE_CATEGORY, provider="nmap"),
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", _SINGLE_CATEGORY, provider="snmp", collection_method="bridge-mib"
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        relationships = RelationshipResolver(cardinality_policy=_SINGLE_POLICY).resolve(observations, identities)

        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0].state, RelationshipCorroborationState.CONFIRMED)


class RelationshipResolverMultiValuedTest(unittest.TestCase):
    """Inverted twins of the single-valued conflict tests: the same inputs
    under a MULTIPLE category produce per-edge WEAK/CONFIRMED records and
    never CONFLICTING (ADR-013 Amendment 1, Decision 2)."""

    def test_two_sources_naming_different_neighbors_are_two_weak_edges(self):
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

        self.assertEqual(len(relationships), 2)
        for relationship in relationships:
            self.assertEqual(relationship.cardinality, RelationshipCardinality.MULTIPLE)
            self.assertEqual(relationship.state, RelationshipCorroborationState.WEAK)

    def test_one_source_reporting_two_neighbors_is_not_a_conflict(self):
        observations = [
            _relationship_observation("10.0.0.1", "10.0.0.254", "connected_to"),
            _relationship_observation("10.0.0.1", "10.0.0.253", "connected_to"),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships), 2)
        self.assertTrue(all(r.state == RelationshipCorroborationState.WEAK for r in relationships))

    def test_mixed_weak_and_confirmed_edges_within_one_subject_and_category(self):
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

        edges = _edges(relationships)
        self.assertEqual(edges["10.0.0.254"].state, RelationshipCorroborationState.CONFIRMED)
        self.assertEqual(edges["10.0.0.253"].state, RelationshipCorroborationState.WEAK)

    def test_gateway_style_fan_out_produces_one_weak_edge_per_host(self):
        hosts = ["10.0.0.10", "10.0.0.11", "10.0.0.12"]
        observations = [
            _relationship_observation(
                "10.0.0.1", host, "arp_neighbor", provider="snmp", collection_method="ipNetToPhysicalTable"
            )
            for host in hosts
        ]
        identities = [_identity("10.0.0.1")] + [_identity(host) for host in hosts]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual([r.related_subject for r in relationships], hosts)
        self.assertTrue(all(r.state == RelationshipCorroborationState.WEAK for r in relationships))

    def test_each_edge_carries_only_its_own_observations(self):
        observations = [
            _relationship_observation("10.0.0.1", "10.0.0.254", "bridge_fdb", provider="snmp"),
            _relationship_observation("10.0.0.1", "10.0.0.253", "bridge_fdb", provider="snmp"),
            _relationship_observation("10.0.0.1", "10.0.0.253", "bridge_fdb", provider="nmap"),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        relationships = RelationshipResolver().resolve(observations, identities)

        for relationship in relationships:
            self.assertTrue(
                all(o.related_subject == relationship.related_subject for o in relationship.observations)
            )
        edges = _edges(relationships)
        self.assertEqual(len(edges["10.0.0.254"].observations), 1)
        self.assertEqual(len(edges["10.0.0.253"].observations), 2)

    def test_unregistered_category_defaults_to_multiple_and_never_conflicts(self):
        observations = [
            _relationship_observation("10.0.0.1", "10.0.0.254", "routes_through"),
            _relationship_observation("10.0.0.1", "10.0.0.253", "routes_through"),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships), 2)
        for relationship in relationships:
            self.assertEqual(relationship.cardinality, RelationshipCardinality.MULTIPLE)
            self.assertEqual(relationship.state, RelationshipCorroborationState.WEAK)


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
        self.assertEqual(relationship.related_subject, "10.0.0.254")
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

    def test_output_is_sorted_by_subject_category_and_related_subject_regardless_of_input_order(self):
        observations = [
            _relationship_observation("10.0.0.9", "10.0.0.1", "hosts_service"),
            _relationship_observation("10.0.0.1", "10.0.0.9", "connected_to"),
            _relationship_observation("10.0.0.1", "10.0.0.2", "connected_to"),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.2"), _identity("10.0.0.9")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(
            [(r.subject, r.category, r.related_subject) for r in relationships],
            [
                ("10.0.0.1", "connected_to", "10.0.0.2"),
                ("10.0.0.1", "connected_to", "10.0.0.9"),
                ("10.0.0.9", "hosts_service", "10.0.0.1"),
            ],
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


    def test_edge_observations_are_sorted_deterministically_with_ties(self):
        # PLAN-028 D6: within one edge, observations sharing provider and
        # collection_method are ordered by source_run, then by the ISO form
        # of observed_at — never by input order.
        edge_observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "arp_neighbor", provider="snmp",
                collection_method="ipNetToPhysicalTable",
                source_run=run, observed_at=datetime(2026, 8, 20, hour, 0, 0),
            )
            for run, hour in (("run-002", 9), ("run-001", 11), ("run-001", 10), ("run-003", 8))
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        baseline = RelationshipResolver().resolve(edge_observations, identities)

        self.assertEqual(
            [(o.provenance.source_run, o.provenance.observed_at.hour) for o in baseline[0].observations],
            [("run-001", 10), ("run-001", 11), ("run-002", 9), ("run-003", 8)],
        )
        rng = random.Random(28)
        for _ in range(200):
            shuffled = list(edge_observations)
            rng.shuffle(shuffled)
            self.assertEqual(RelationshipResolver().resolve(shuffled, identities), baseline)

    def test_mixed_naive_and_aware_timestamps_sort_without_error(self):
        observations = [
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "arp_neighbor", observed_at=datetime(2026, 8, 20, 9, 0, 0)
            ),
            _relationship_observation(
                "10.0.0.1", "10.0.0.254", "arp_neighbor",
                observed_at=datetime(2026, 8, 20, 9, 0, 0, tzinfo=timezone.utc),
            ),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254")]

        relationships = RelationshipResolver().resolve(observations, identities)

        self.assertEqual(len(relationships[0].observations), 2)


class RelationshipCardinalityPolicyTest(unittest.TestCase):
    def test_existing_relationship_categories_are_registered_as_multiple(self):
        self.assertEqual(CATEGORY_CARDINALITY["arp_neighbor"], RelationshipCardinality.MULTIPLE)
        self.assertEqual(CATEGORY_CARDINALITY["bridge_fdb"], RelationshipCardinality.MULTIPLE)
        self.assertEqual(CATEGORY_CARDINALITY["connected_to"], RelationshipCardinality.MULTIPLE)

    def test_default_gateway_is_not_registered(self):
        # ADR-013 Amendment 1: not registered before a provider exists.
        self.assertNotIn("default_gateway", CATEGORY_CARDINALITY)

    def test_unknown_category_defaults_to_multiple(self):
        self.assertEqual(DEFAULT_CARDINALITY, RelationshipCardinality.MULTIPLE)
        self.assertEqual(cardinality_for("not_a_registered_category"), RelationshipCardinality.MULTIPLE)

    def test_module_policy_cannot_be_mutated(self):
        with self.assertRaises(TypeError):
            CATEGORY_CARDINALITY["arp_neighbor"] = RelationshipCardinality.SINGLE  # type: ignore[index]

    def test_custom_policy_does_not_mutate_the_module_policy(self):
        before = dict(CATEGORY_CARDINALITY)
        custom_policy = {"connected_to": RelationshipCardinality.SINGLE}
        observations = [
            _relationship_observation("10.0.0.1", "10.0.0.254", "connected_to"),
            _relationship_observation("10.0.0.1", "10.0.0.253", "connected_to"),
        ]
        identities = [_identity("10.0.0.1"), _identity("10.0.0.254"), _identity("10.0.0.253")]

        custom = RelationshipResolver(cardinality_policy=custom_policy).resolve(observations, identities)
        default = RelationshipResolver().resolve(observations, identities)

        self.assertTrue(all(r.state == RelationshipCorroborationState.CONFLICTING for r in custom))
        self.assertTrue(all(r.state == RelationshipCorroborationState.WEAK for r in default))
        self.assertEqual(dict(CATEGORY_CARDINALITY), before)
        self.assertEqual(custom_policy, {"connected_to": RelationshipCardinality.SINGLE})

    def test_every_relationship_provider_category_is_registered(self):
        """PLAN-028 Section 2.2, note 3: checks only the known relationship
        provider category constants, listed explicitly. A future
        relationship-provider sprint must add its category constant to this
        list, so a new category cannot silently fall back to the default."""
        relationship_provider_categories = (
            ARP_NEIGHBOR_CATEGORY,
            BRIDGE_FDB_CATEGORY,
            LLDP_NEIGHBOR_CATEGORY,
        )

        for category in relationship_provider_categories:
            with self.subTest(category=category):
                self.assertIn(category, CATEGORY_CARDINALITY)


class CanonicalRelationshipInvariantTest(unittest.TestCase):
    def test_conflicting_is_rejected_for_a_multiple_category(self):
        observation = _relationship_observation("10.0.0.1", "10.0.0.254", "arp_neighbor")

        with self.assertRaises(ValueError):
            CanonicalRelationship(
                subject="10.0.0.1",
                category="arp_neighbor",
                related_subject="10.0.0.254",
                cardinality=RelationshipCardinality.MULTIPLE,
                state=RelationshipCorroborationState.CONFLICTING,
                observations=(observation,),
            )

    def test_conflicting_is_accepted_for_a_single_category(self):
        observation = _relationship_observation("10.0.0.1", "10.0.0.254", _SINGLE_CATEGORY)

        relationship = CanonicalRelationship(
            subject="10.0.0.1",
            category=_SINGLE_CATEGORY,
            related_subject="10.0.0.254",
            cardinality=RelationshipCardinality.SINGLE,
            state=RelationshipCorroborationState.CONFLICTING,
            observations=(observation,),
        )

        self.assertEqual(relationship.state, RelationshipCorroborationState.CONFLICTING)

    def test_empty_observations_are_rejected(self):
        with self.assertRaises(ValueError):
            CanonicalRelationship(
                subject="10.0.0.1",
                category="arp_neighbor",
                related_subject="10.0.0.254",
                cardinality=RelationshipCardinality.MULTIPLE,
                state=RelationshipCorroborationState.WEAK,
                observations=(),
            )

    def test_mismatched_observation_fields_are_rejected(self):
        mismatches = {
            "related_subject": _relationship_observation("10.0.0.1", "10.0.0.253", "arp_neighbor"),
            "subject": _relationship_observation("10.0.0.2", "10.0.0.254", "arp_neighbor"),
            "category": _relationship_observation("10.0.0.1", "10.0.0.254", "bridge_fdb"),
        }

        for field_name, observation in mismatches.items():
            with self.subTest(mismatched=field_name):
                with self.assertRaises(ValueError):
                    CanonicalRelationship(
                        subject="10.0.0.1",
                        category="arp_neighbor",
                        related_subject="10.0.0.254",
                        cardinality=RelationshipCardinality.MULTIPLE,
                        state=RelationshipCorroborationState.WEAK,
                        observations=(observation,),
                    )


if __name__ == "__main__":
    unittest.main()
