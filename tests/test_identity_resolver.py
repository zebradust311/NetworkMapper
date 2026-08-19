import random
import unittest
from datetime import datetime

from networkmapper.identity.models import IdentityCorroborationState
from networkmapper.identity.resolver import IdentityResolver
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance


def _identity_observation(
    subject: str,
    property_name: str,
    value: str,
    *,
    provider: str = "nmap",
    collection_method: str = "host-discovery",
    source_run: str = "run-001",
) -> IdentityObservation:
    return IdentityObservation(
        subject=subject,
        property_name=property_name,
        value=value,
        provenance=ObservationProvenance(
            provider=provider,
            collection_method=collection_method,
            observed_at=datetime(2026, 8, 19, 9, 0, 0),
            source_run=source_run,
        ),
    )


class IdentityResolverEmptyInputTest(unittest.TestCase):
    def test_no_observations_produces_no_identities(self):
        identities = IdentityResolver().resolve([])

        self.assertEqual(identities, ())


class IdentityResolverSingleObservationTest(unittest.TestCase):
    def test_a_single_observation_produces_a_weak_identity(self):
        observation = _identity_observation("10.0.0.1", "hostname", "dc-01")

        identities = IdentityResolver().resolve([observation])

        self.assertEqual(len(identities), 1)
        identity = identities[0]
        self.assertEqual(identity.subject, "10.0.0.1")
        self.assertEqual(identity.state, IdentityCorroborationState.WEAK)
        self.assertEqual(len(identity.properties), 1)
        self.assertEqual(identity.properties[0].property_name, "hostname")
        self.assertEqual(identity.properties[0].state, IdentityCorroborationState.WEAK)


class IdentityResolverCorroborationTest(unittest.TestCase):
    def test_two_independent_sources_agreeing_confirm_the_property_and_identity(self):
        observations = [
            _identity_observation(
                "10.0.0.1", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"
            ),
            _identity_observation(
                "10.0.0.1", "hostname", "dc-01", provider="snmp", collection_method="sysName"
            ),
        ]

        identities = IdentityResolver().resolve(observations)

        identity = identities[0]
        self.assertEqual(identity.state, IdentityCorroborationState.CONFIRMED)
        self.assertEqual(identity.properties[0].state, IdentityCorroborationState.CONFIRMED)
        self.assertEqual(len(identity.properties[0].observations), 2)

    def test_duplicate_observations_from_the_same_source_do_not_confirm(self):
        # Same (provider, collection_method) reported twice — one
        # independent source, not two. ADR-012 Observation Independence.
        observations = [
            _identity_observation(
                "10.0.0.1", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"
            ),
            _identity_observation(
                "10.0.0.1", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"
            ),
        ]

        identities = IdentityResolver().resolve(observations)

        identity = identities[0]
        self.assertEqual(identity.state, IdentityCorroborationState.WEAK)
        self.assertEqual(identity.properties[0].state, IdentityCorroborationState.WEAK)
        # Both raw observations are still retained, even though neither
        # upgraded the corroboration state.
        self.assertEqual(len(identity.properties[0].observations), 2)

    def test_three_independent_sources_two_agreeing_one_conflicting_still_conflicts(self):
        observations = [
            _identity_observation("10.0.0.1", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"),
            _identity_observation("10.0.0.1", "hostname", "dc-01", provider="snmp", collection_method="sysName"),
            _identity_observation("10.0.0.1", "hostname", "dc-99", provider="wmi", collection_method="Win32_ComputerSystem"),
        ]

        identities = IdentityResolver().resolve(observations)

        # A conflict is never silently outvoted by the agreeing majority.
        self.assertEqual(identities[0].state, IdentityCorroborationState.CONFLICTING)
        self.assertEqual(identities[0].properties[0].state, IdentityCorroborationState.CONFLICTING)


class IdentityResolverConflictTest(unittest.TestCase):
    def test_two_independent_sources_disagreeing_conflict(self):
        observations = [
            _identity_observation(
                "10.0.0.1", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"
            ),
            _identity_observation(
                "10.0.0.1", "hostname", "sw-core-01", provider="snmp", collection_method="sysName"
            ),
        ]

        identities = IdentityResolver().resolve(observations)

        identity = identities[0]
        self.assertEqual(identity.state, IdentityCorroborationState.CONFLICTING)
        self.assertEqual(identity.properties[0].state, IdentityCorroborationState.CONFLICTING)
        # Neither conflicting observation is discarded.
        self.assertEqual(len(identity.properties[0].observations), 2)
        values = {o.value for o in identity.properties[0].observations}
        self.assertEqual(values, {"dc-01", "sw-core-01"})

    def test_a_conflict_on_one_property_does_not_hide_confirmation_on_another(self):
        observations = [
            _identity_observation("10.0.0.1", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"),
            _identity_observation("10.0.0.1", "hostname", "sw-01", provider="snmp", collection_method="sysName"),
            _identity_observation("10.0.0.1", "domain", "corp.local", provider="nmap", collection_method="smb-os-discovery"),
            _identity_observation("10.0.0.1", "domain", "corp.local", provider="nmap", collection_method="rdp-ntlm-info"),
        ]

        identities = IdentityResolver().resolve(observations)

        identity = identities[0]
        properties_by_name = {p.property_name: p for p in identity.properties}
        self.assertEqual(properties_by_name["hostname"].state, IdentityCorroborationState.CONFLICTING)
        self.assertEqual(properties_by_name["domain"].state, IdentityCorroborationState.CONFIRMED)
        # A conflict anywhere makes the whole identity CONFLICTING —
        # it is never hidden behind an unrelated confirmed property.
        self.assertEqual(identity.state, IdentityCorroborationState.CONFLICTING)


class IdentityResolverProbableRollupTest(unittest.TestCase):
    def test_two_single_sourced_properties_roll_up_to_probable(self):
        observations = [
            _identity_observation("10.0.0.1", "hostname", "dc-01"),
            _identity_observation("10.0.0.1", "computer_name", "DC01", collection_method="smb-os-discovery"),
        ]

        identities = IdentityResolver().resolve(observations)

        identity = identities[0]
        self.assertEqual(identity.state, IdentityCorroborationState.PROBABLE)
        self.assertTrue(
            all(p.state == IdentityCorroborationState.WEAK for p in identity.properties)
        )


class IdentityResolverGroupingTest(unittest.TestCase):
    def test_observations_are_grouped_by_subject_into_separate_identities(self):
        observations = [
            _identity_observation("10.0.0.1", "hostname", "dc-01"),
            _identity_observation("10.0.0.2", "hostname", "dc-02"),
        ]

        identities = IdentityResolver().resolve(observations)

        self.assertEqual(len(identities), 2)
        self.assertEqual({identity.subject for identity in identities}, {"10.0.0.1", "10.0.0.2"})

    def test_relationship_observations_are_ignored_not_erroring(self):
        relationship = RelationshipObservation(
            subject="10.0.0.1",
            related_subject="10.0.0.254",
            category="connected_to",
            provenance=ObservationProvenance(
                provider="lldp",
                collection_method="lldp-neighbor",
                observed_at=datetime(2026, 8, 19, 9, 0, 0),
                source_run="run-001",
            ),
        )
        identity_observation = _identity_observation("10.0.0.1", "hostname", "dc-01")

        identities = IdentityResolver().resolve([relationship, identity_observation])

        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0].subject, "10.0.0.1")
        self.assertEqual(len(identities[0].properties[0].observations), 1)

    def test_output_subjects_are_sorted_regardless_of_input_order(self):
        observations = [
            _identity_observation("10.0.0.9", "hostname", "z-host"),
            _identity_observation("10.0.0.1", "hostname", "a-host"),
        ]

        identities = IdentityResolver().resolve(observations)

        self.assertEqual([identity.subject for identity in identities], ["10.0.0.1", "10.0.0.9"])


class IdentityResolverProvenanceRetentionTest(unittest.TestCase):
    def test_original_observation_objects_are_preserved_unmodified(self):
        observation = _identity_observation("10.0.0.1", "hostname", "dc-01", provider="nmap")

        identities = IdentityResolver().resolve([observation])

        retained = identities[0].properties[0].observations[0]
        self.assertIs(retained, observation)
        self.assertEqual(retained.provenance.provider, "nmap")
        self.assertEqual(retained.provenance.collection_method, "host-discovery")


class IdentityResolverDeterminismTest(unittest.TestCase):
    def test_resolve_is_order_independent_across_many_random_permutations(self):
        base_observations = [
            _identity_observation("10.0.0.1", "hostname", "dc-01", provider="nmap", collection_method="host-discovery"),
            _identity_observation("10.0.0.1", "hostname", "dc-01", provider="snmp", collection_method="sysName"),
            _identity_observation("10.0.0.1", "domain", "corp.local", provider="nmap", collection_method="smb-os-discovery"),
            _identity_observation("10.0.0.2", "hostname", "ws-01", provider="nmap", collection_method="host-discovery"),
            _identity_observation("10.0.0.2", "hostname", "ws-99", provider="snmp", collection_method="sysName"),
        ]

        baseline = IdentityResolver().resolve(base_observations)

        rng = random.Random(1234)
        for _ in range(20):
            shuffled = list(base_observations)
            rng.shuffle(shuffled)

            result = IdentityResolver().resolve(shuffled)

            self.assertEqual(result, baseline)


if __name__ == "__main__":
    unittest.main()
