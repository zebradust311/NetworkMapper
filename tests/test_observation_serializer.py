import json
import unittest

from networkmapper.knowledge.models import (
    Observation,
    ObservationClassification,
    ObservationDevice,
    ObservationEvidence,
    ObservationNetwork,
    ObservationReviewEntry,
    ObservationScan,
    ObservationServiceEvidence,
    ObservationStatus,
)
from networkmapper.knowledge.serializer import ObservationSchemaError, ObservationSerializer


def _build_observation(**overrides) -> Observation:
    defaults = dict(
        observation_id=1,
        captured_at="2026-07-18T09:42:11",
        network=ObservationNetwork(name="Riverside Manufacturing"),
        scan=ObservationScan(profile="standard", networkmapper_version="0.4.0"),
        device=ObservationDevice(
            ip="192.168.10.55",
            hostname="AP9631",
            vendor="APC",
            mac_address="00:C0:B7:4E:19:2A",
        ),
        evidence=ObservationEvidence(
            discovery_sources=["nmap"],
            services=[
                ObservationServiceEvidence(
                    port=80,
                    protocol="tcp",
                    service="http",
                    http_title="APC Network Management Card AOS v6.9.6",
                    http_auth_realm="Network Management Card",
                ),
                ObservationServiceEvidence(
                    port=443,
                    protocol="tcp",
                    service="https",
                    tls_subject="CN=AP9631",
                    tls_issuer="CN=AP9631",
                ),
            ],
        ),
        classification=ObservationClassification(type="unknown", reason="No rule matched."),
    )
    defaults.update(overrides)
    return Observation(**defaults)


class ObservationSerializerRoundTripTest(unittest.TestCase):
    def test_round_trips_a_fully_populated_observation(self):
        observation = _build_observation(
            status=ObservationStatus.VALIDATED,
            technician_notes="Found in the UPS closet, same switch as the rack PDUs.",
            review_history=[
                ObservationReviewEntry(
                    reviewed_at="2026-07-25T14:00:00",
                    action=ObservationStatus.VALIDATED,
                    notes="Confirmed APC network management interface.",
                )
            ],
        )

        round_tripped = ObservationSerializer.from_json(ObservationSerializer.to_json(observation))

        self.assertEqual(round_tripped, observation)

    def test_json_serialization_produces_valid_json(self):
        observation = _build_observation()

        text = ObservationSerializer.to_json(observation)

        parsed = json.loads(text)
        self.assertEqual(parsed["observation_id"], 1)
        self.assertEqual(parsed["device"]["vendor"], "APC")

    def test_multiple_service_entries_round_trip_independently(self):
        observation = _build_observation()

        round_tripped = ObservationSerializer.from_json(ObservationSerializer.to_json(observation))

        self.assertEqual(len(round_tripped.evidence.services), 2)
        self.assertEqual(round_tripped.evidence.services[0].port, 80)
        self.assertEqual(round_tripped.evidence.services[1].port, 443)
        self.assertEqual(
            round_tripped.evidence.services[0].http_auth_realm, "Network Management Card"
        )
        self.assertEqual(round_tripped.evidence.services[1].tls_subject, "CN=AP9631")

    def test_review_history_round_trips_multiple_entries(self):
        observation = _build_observation(
            status=ObservationStatus.IMPLEMENTED,
            review_history=[
                ObservationReviewEntry(
                    reviewed_at="2026-07-25T14:00:00",
                    action=ObservationStatus.VALIDATED,
                    notes="Confirmed APC network management interface.",
                ),
                ObservationReviewEntry(
                    reviewed_at="2026-08-01T10:15:00",
                    action=ObservationStatus.IMPLEMENTED,
                    notes="Encoded as a new classification rule.",
                    reference="RULE-004",
                ),
            ],
        )

        round_tripped = ObservationSerializer.from_json(ObservationSerializer.to_json(observation))

        self.assertEqual(len(round_tripped.review_history), 2)
        self.assertEqual(round_tripped.review_history[1].reference, "RULE-004")
        self.assertEqual(round_tripped.review_history[1].action, ObservationStatus.IMPLEMENTED)


class ObservationSerializerDefaultsTest(unittest.TestCase):
    def test_technician_notes_is_optional_and_defaults_to_empty_string(self):
        observation = _build_observation()

        self.assertEqual(observation.technician_notes, "")

        round_tripped = ObservationSerializer.from_json(ObservationSerializer.to_json(observation))
        self.assertEqual(round_tripped.technician_notes, "")

    def test_review_history_is_optional_and_defaults_to_empty_list(self):
        observation = _build_observation()

        self.assertEqual(observation.review_history, [])

    def test_status_defaults_to_new(self):
        observation = _build_observation()

        self.assertEqual(observation.status, ObservationStatus.NEW)

    def test_schema_version_defaults_to_current_version(self):
        observation = _build_observation()

        self.assertEqual(observation.schema_version, 1)


class ObservationSerializerValidationTest(unittest.TestCase):
    def test_missing_required_field_raises_schema_error(self):
        payload = ObservationSerializer.to_dict(_build_observation())
        del payload["classification"]

        with self.assertRaises(ObservationSchemaError):
            ObservationSerializer.from_dict(payload)

    def test_missing_network_raises_schema_error(self):
        payload = ObservationSerializer.to_dict(_build_observation())
        del payload["network"]

        with self.assertRaises(ObservationSchemaError):
            ObservationSerializer.from_dict(payload)

    def test_invalid_status_is_rejected(self):
        payload = ObservationSerializer.to_dict(_build_observation())
        payload["status"] = "APPROVED_FOREVER"

        with self.assertRaises(ObservationSchemaError):
            ObservationSerializer.from_dict(payload)

    def test_invalid_review_history_action_is_rejected(self):
        payload = ObservationSerializer.to_dict(_build_observation())
        payload["review_history"] = [
            {"reviewed_at": "2026-08-01T00:00:00", "action": "MAYBE", "notes": ""}
        ]

        with self.assertRaises(ObservationSchemaError):
            ObservationSerializer.from_dict(payload)

    def test_every_defined_lifecycle_status_is_accepted(self):
        for status in ObservationStatus:
            payload = ObservationSerializer.to_dict(_build_observation())
            payload["status"] = status.value

            observation = ObservationSerializer.from_dict(payload)

            self.assertEqual(observation.status, status)


class ObservationEvidenceIsProviderIndependentTest(unittest.TestCase):
    def test_service_evidence_fields_mirror_canonical_service_evidence(self):
        from networkmapper.core.models import ServiceEvidence

        canonical_fields = {
            field_name
            for field_name in ServiceEvidence.__dataclass_fields__
        }
        observation_fields = {
            field_name
            for field_name in ObservationServiceEvidence.__dataclass_fields__
        }

        self.assertEqual(canonical_fields, observation_fields)

    def test_no_provider_specific_field_names_leak_into_evidence(self):
        payload = ObservationSerializer.to_dict(_build_observation())

        serialized_text = json.dumps(payload).lower()
        for provider_specific_term in ("nmap_xml", "raw_output", "xml_blob"):
            self.assertNotIn(provider_specific_term, serialized_text)


if __name__ == "__main__":
    unittest.main()
