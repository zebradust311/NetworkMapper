"""Replay artifact format tests (ADR-011 Amendment 1; PLAN-029 Sections 4-6,
8, 9.1 and 9.4).

All values are synthetic: documentation address ranges and invented
hostnames only (ARCH-028 Section 8).
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
import tempfile
import unittest
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.observations.replay_format import (
    FORMAT_IDENTIFIER,
    FORMAT_VERSION,
    ObservationReplayFormatError,
    load_observations,
    parse_observations,
    serialize_observations,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_NAIVE = datetime(2026, 10, 13, 9, 15, 2, 123456)


def _provenance(
    provider: str = "nmap",
    collection_method: str = "host-discovery",
    observed_at: datetime = _NAIVE,
    source_run: str = "run-001",
) -> ObservationProvenance:
    return ObservationProvenance(
        provider=provider,
        collection_method=collection_method,
        observed_at=observed_at,
        source_run=source_run,
    )


def _identity(subject="192.0.2.10", property_name="hostname", value="host-a.example", **provenance):
    return IdentityObservation(
        subject=subject, property_name=property_name, value=value, provenance=_provenance(**provenance)
    )


def _relationship(subject="192.0.2.1", related_subject="192.0.2.10", category="arp_neighbor", **provenance):
    return RelationshipObservation(
        subject=subject,
        related_subject=related_subject,
        category=category,
        provenance=_provenance(**provenance),
    )


def _round_trip(observations):
    return parse_observations(serialize_observations(observations))


def _mixed_observations():
    return [
        _identity(),
        _identity(subject="192.0.2.11", property_name="mac_address", value="02:00:5E:00:53:0B"),
        _identity(provider="snmp", collection_method="sysName", source_run="run-002"),
        _relationship(provider="snmp", collection_method="ipNetToPhysicalTable"),
        _relationship(related_subject="192.0.2.11", provider="snmp", collection_method="ipNetToPhysicalTable"),
        _relationship(category="connected_to", provider="snmp", collection_method="lldpRemTable"),
    ]


def _document(observations=None, **overrides) -> dict:
    """The parsed JSON document for a valid artifact, ready to be corrupted."""
    document = json.loads(serialize_observations(_mixed_observations() if observations is None else observations))
    document.update(overrides)
    return document


class RoundTripTest(unittest.TestCase):
    def test_mixed_identity_and_relationship_observations_round_trip_as_a_multiset(self):
        observations = _mixed_observations()

        loaded = _round_trip(observations)

        self.assertEqual(Counter(loaded), Counter(observations))
        self.assertEqual(len(loaded), len(observations))

    def test_empty_input_is_a_valid_artifact(self):
        payload = serialize_observations([])

        document = json.loads(payload)
        self.assertEqual(document["format"], FORMAT_IDENTIFIER)
        self.assertEqual(document["format_version"], FORMAT_VERSION)
        self.assertEqual(document["observations"], [])
        self.assertEqual(parse_observations(payload), [])

    def test_duplicate_observations_are_preserved(self):
        observations = [_identity(), _identity(), _identity(), _relationship(), _relationship()]

        payload = serialize_observations(observations)
        loaded = parse_observations(payload)

        self.assertEqual(len(json.loads(payload)["observations"]), 5)
        self.assertEqual(len(loaded), 5)
        self.assertEqual(Counter(loaded), Counter(observations))
        self.assertEqual(Counter(loaded)[_identity()], 3)

    def test_relationship_observation_with_an_unresolved_endpoint_is_preserved(self):
        # 198.51.100.77 has no identity observation, so no resolver would
        # ever turn this into a canonical relationship. It is still evidence.
        unresolved = _relationship(related_subject="198.51.100.77")
        observations = [_identity(subject="192.0.2.1"), unresolved]

        payload = serialize_observations(observations)
        loaded = parse_observations(payload)

        self.assertIn(unresolved, loaded)
        self.assertIn("198.51.100.77", payload.decode("ascii"))

    def test_awkward_strings_round_trip_exactly(self):
        for value in ("sw-été", 'quote " backslash \\ end', "line one\nline two\r\n", "", "  padded  ", "\ud800"):
            with self.subTest(value=value):
                observations = [
                    _identity(value=value),
                    _relationship(related_subject=value, category=value),
                ]
                self.assertEqual(Counter(_round_trip(observations)), Counter(observations))

    def test_load_observations_reads_a_file_written_from_the_serialized_bytes(self):
        observations = _mixed_observations()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "observations.json"
            path.write_bytes(serialize_observations(observations))
            loaded = load_observations(path)

        self.assertEqual(Counter(loaded), Counter(observations))

    def test_every_field_is_written_verbatim(self):
        payload = serialize_observations([_identity(), _relationship()])

        self.assertEqual(
            json.loads(payload)["observations"],
            [
                {
                    "type": "identity",
                    "subject": "192.0.2.10",
                    "property_name": "hostname",
                    "value": "host-a.example",
                    "provenance": {
                        "provider": "nmap",
                        "collection_method": "host-discovery",
                        "observed_at": "2026-10-13T09:15:02.123456",
                        "source_run": "run-001",
                    },
                },
                {
                    "type": "relationship",
                    "subject": "192.0.2.1",
                    "related_subject": "192.0.2.10",
                    "category": "arp_neighbor",
                    "provenance": {
                        "provider": "nmap",
                        "collection_method": "host-discovery",
                        "observed_at": "2026-10-13T09:15:02.123456",
                        "source_run": "run-001",
                    },
                },
            ],
        )


class ObservedAtFidelityTest(unittest.TestCase):
    def _assert_exact(self, observed_at: datetime) -> datetime:
        (loaded,) = _round_trip([_identity(observed_at=observed_at)])
        restored = loaded.provenance.observed_at

        self.assertEqual(restored, observed_at)
        self.assertEqual(restored.isoformat(), observed_at.isoformat())
        self.assertEqual(restored.tzinfo is None, observed_at.tzinfo is None)
        self.assertEqual(restored.utcoffset(), observed_at.utcoffset())
        self.assertEqual(restored.microsecond, observed_at.microsecond)
        return restored

    def test_naive_timestamp_with_microseconds(self):
        restored = self._assert_exact(datetime(2026, 10, 13, 9, 15, 2, 123456))

        self.assertIsNone(restored.tzinfo)
        self.assertEqual(restored.microsecond, 123456)

    def test_naive_timestamp_with_zero_microseconds_writes_no_fractional_part(self):
        observed_at = datetime(2026, 10, 13, 9, 15, 2)

        payload = serialize_observations([_identity(observed_at=observed_at)])

        self.assertEqual(
            json.loads(payload)["observations"][0]["provenance"]["observed_at"], "2026-10-13T09:15:02"
        )
        self._assert_exact(observed_at)

    def test_single_microsecond_is_not_rounded_away(self):
        self._assert_exact(datetime(2026, 10, 13, 9, 15, 2, 1))

    def test_aware_utc_timestamp(self):
        restored = self._assert_exact(datetime(2026, 10, 13, 9, 15, 2, 123456, tzinfo=timezone.utc))

        self.assertEqual(restored.utcoffset(), timedelta(0))

    def test_aware_timestamp_with_a_negative_offset(self):
        restored = self._assert_exact(
            datetime(2026, 10, 13, 9, 15, 2, 500000, tzinfo=timezone(timedelta(hours=-5)))
        )

        self.assertEqual(restored.utcoffset(), timedelta(hours=-5))

    def test_aware_timestamp_with_a_non_whole_hour_offset(self):
        restored = self._assert_exact(
            datetime(2026, 10, 13, 9, 15, 2, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        )

        self.assertEqual(restored.utcoffset(), timedelta(hours=5, minutes=30))

    def test_aware_timestamp_is_never_normalized_to_utc(self):
        observed_at = datetime(2026, 10, 13, 9, 15, 2, tzinfo=timezone(timedelta(hours=-5)))

        payload = serialize_observations([_identity(observed_at=observed_at)])

        self.assertEqual(
            json.loads(payload)["observations"][0]["provenance"]["observed_at"],
            "2026-10-13T09:15:02-05:00",
        )

    def test_naive_and_aware_values_with_the_same_wall_clock_stay_distinct(self):
        naive = datetime(2026, 10, 13, 9, 15, 2, 123456)
        aware = naive.replace(tzinfo=timezone.utc)

        loaded = _round_trip([_identity(observed_at=naive), _identity(observed_at=aware)])

        restored = sorted(
            (observation.provenance.observed_at for observation in loaded),
            key=lambda value: value.isoformat(),
        )
        self.assertEqual(len(restored), 2)
        self.assertIsNone(restored[0].tzinfo)
        self.assertIsNotNone(restored[1].tzinfo)
        self.assertEqual(restored[0].isoformat(), naive.isoformat())
        self.assertEqual(restored[1].isoformat(), aware.isoformat())


class SourceRunFidelityTest(unittest.TestCase):
    def test_source_run_round_trips_exactly_as_an_opaque_string(self):
        for source_run in (uuid.uuid4().hex, "", "  Mixed-Case Run ID  ", str(uuid.uuid4()).upper()):
            with self.subTest(source_run=source_run):
                loaded = _round_trip([_identity(source_run=source_run), _relationship(source_run=source_run)])

                self.assertEqual(
                    [observation.provenance.source_run for observation in loaded],
                    [source_run, source_run],
                )

    def test_observations_differing_only_in_source_run_stay_distinct(self):
        observations = [_relationship(source_run="run-a"), _relationship(source_run="run-b")]

        self.assertEqual(Counter(_round_trip(observations)), Counter(observations))


class DeterminismTest(unittest.TestCase):
    def _shuffle_set(self):
        return _mixed_observations() + [
            _identity(),
            _identity(),
            _relationship(provider="snmp", collection_method="ipNetToPhysicalTable"),
            _identity(observed_at=datetime(2026, 10, 13, 9, 15, 2, 123456, tzinfo=timezone.utc)),
            _identity(observed_at=datetime(2026, 10, 13, 9, 15, 2)),
            _relationship(source_run="run-zzz"),
            _relationship(observed_at=datetime(2026, 10, 13, 9, 15, 3, tzinfo=timezone(timedelta(hours=-5)))),
        ]

    def test_output_is_byte_identical_across_many_random_input_orders(self):
        observations = self._shuffle_set()
        expected = serialize_observations(observations)
        rng = random.Random(29)

        for _ in range(200):
            shuffled = list(observations)
            rng.shuffle(shuffled)
            self.assertEqual(serialize_observations(shuffled), expected)

    def test_serializing_a_loaded_artifact_reproduces_it_byte_for_byte(self):
        payload = serialize_observations(self._shuffle_set())

        self.assertEqual(serialize_observations(parse_observations(payload)), payload)

    def test_bytes_are_ascii_with_lf_line_endings_and_one_trailing_newline(self):
        payload = serialize_observations([_identity(value="sw-été")] + self._shuffle_set())

        self.assertTrue(payload.endswith(b"}\n"))
        self.assertFalse(payload.endswith(b"\n\n"))
        self.assertNotIn(b"\r", payload)
        payload.decode("ascii")

    def test_serializing_does_not_mutate_or_reorder_its_input(self):
        observations = list(reversed(self._shuffle_set()))
        snapshot = list(observations)

        serialize_observations(observations)

        self.assertEqual(len(observations), len(snapshot))
        for original, current in zip(snapshot, observations):
            self.assertIs(current, original)

    def test_records_are_sorted_by_type_then_fields(self):
        payload = serialize_observations(
            [
                _relationship(subject="192.0.2.1"),
                _identity(subject="192.0.2.20"),
                _identity(subject="192.0.2.10"),
            ]
        )

        records = json.loads(payload)["observations"]
        self.assertEqual(
            [(record["type"], record["subject"]) for record in records],
            [("identity", "192.0.2.10"), ("identity", "192.0.2.20"), ("relationship", "192.0.2.1")],
        )

    def test_artifact_has_no_fields_beyond_the_format_and_the_observations(self):
        document = json.loads(serialize_observations(_mixed_observations()))

        self.assertEqual(sorted(document), ["format", "format_version", "observations"])


class RejectionTest(unittest.TestCase):
    def _assert_rejected(self, document, expected_message: str) -> None:
        data = document if isinstance(document, (str, bytes)) else json.dumps(document)
        with self.assertRaises(ObservationReplayFormatError) as raised:
            parse_observations(data, source="run/observations.json")
        self.assertEqual(str(raised.exception), expected_message)

    def test_unknown_format_identifier_is_rejected(self):
        self._assert_rejected(
            _document(format="someone.elses-format"),
            "run/observations.json: unknown format identifier 'someone.elses-format'; "
            "expected 'networkmapper.retained-observations'",
        )

    def test_missing_format_identifier_is_rejected(self):
        document = _document()
        del document["format"]

        self._assert_rejected(document, "run/observations.json: missing required key 'format'")

    def test_unknown_format_versions_are_rejected(self):
        for version in (2, 0, -1):
            with self.subTest(version=version):
                self._assert_rejected(
                    _document(format_version=version),
                    f"run/observations.json: unsupported format version {version}; "
                    "this build reads version 1 only",
                )

    def test_non_integer_format_versions_are_rejected(self):
        for version, shown in (("1", '"1"'), (1.0, "1.0"), (True, "true"), (None, "null")):
            with self.subTest(version=version):
                self._assert_rejected(
                    _document(format_version=version),
                    f"run/observations.json: unsupported format version {shown}; "
                    "this build reads version 1 only",
                )

    def test_missing_format_version_is_rejected(self):
        document = _document()
        del document["format_version"]

        self._assert_rejected(document, "run/observations.json: missing required key 'format_version'")

    def test_unknown_format_is_reported_before_any_other_problem(self):
        self._assert_rejected(
            {"format": "other", "unexpected": True},
            "run/observations.json: unknown format identifier 'other'; "
            "expected 'networkmapper.retained-observations'",
        )

    def test_unknown_observation_type_fails_the_whole_load(self):
        document = _document()
        document["observations"][2]["type"] = "lifecycle"

        self._assert_rejected(
            document,
            "run/observations.json: observation 2: unknown observation type 'lifecycle'; "
            "expected 'identity' or 'relationship'",
        )

    def test_missing_observation_type_is_rejected(self):
        document = _document()
        del document["observations"][0]["type"]

        self._assert_rejected(document, "run/observations.json: observation 0: missing required key 'type'")

    def test_missing_keys_are_rejected(self):
        for key in ("subject", "property_name", "value", "provenance"):
            with self.subTest(key=key):
                document = _document([_identity()])
                del document["observations"][0][key]
                self._assert_rejected(
                    document, f"run/observations.json: observation 0: missing required key '{key}'"
                )

        for key in ("provider", "collection_method", "observed_at", "source_run"):
            with self.subTest(key=key):
                document = _document([_relationship()])
                del document["observations"][0]["provenance"][key]
                self._assert_rejected(
                    document, f"run/observations.json: observation 0: missing required key '{key}'"
                )

    def test_unknown_keys_are_rejected_not_dropped(self):
        document = _document([_identity()])
        document["observations"][0]["observation_id"] = "abc"
        self._assert_rejected(document, "run/observations.json: observation 0: unknown key 'observation_id'")

        document = _document([_identity()])
        document["observations"][0]["provenance"]["host"] = "scanner"
        self._assert_rejected(document, "run/observations.json: observation 0: unknown key 'host'")

    def test_a_relationship_key_on_an_identity_record_is_rejected(self):
        document = _document([_identity()])
        document["observations"][0]["category"] = "arp_neighbor"

        self._assert_rejected(document, "run/observations.json: observation 0: unknown key 'category'")

    def test_non_string_values_are_rejected(self):
        for value, found in ((None, "null"), (7, "number"), (True, "boolean"), ([], "array"), ({}, "object")):
            with self.subTest(value=value):
                document = _document([_identity()])
                document["observations"][0]["value"] = value
                self._assert_rejected(
                    document,
                    f"run/observations.json: observation 0: 'value' must be a string, found {found}",
                )

        document = _document([_identity()])
        document["observations"][0]["provenance"]["source_run"] = 12
        self._assert_rejected(
            document, "run/observations.json: observation 0: 'source_run' must be a string, found number"
        )

    def test_non_object_provenance_and_record_are_rejected(self):
        document = _document([_identity()])
        document["observations"][0]["provenance"] = "nmap"
        self._assert_rejected(
            document,
            "run/observations.json: observation 0: 'provenance' must be a JSON object, found string",
        )

        document = _document([_identity()])
        document["observations"].append("not-a-record")
        self._assert_rejected(
            document, "run/observations.json: observation 1: expected a JSON object, found string"
        )

    def test_unknown_top_level_key_is_rejected(self):
        self._assert_rejected(
            _document(generated_at="2026-10-13T09:00:00"),
            "run/observations.json: unknown top-level key 'generated_at'",
        )

    def test_missing_or_non_array_observations_is_rejected(self):
        document = _document()
        del document["observations"]
        self._assert_rejected(document, "run/observations.json: 'observations' must be a JSON array")

        document = _document()
        document["observations"] = {}
        self._assert_rejected(document, "run/observations.json: 'observations' must be a JSON array")

    def test_non_canonical_and_unparseable_timestamps_are_rejected(self):
        for text in ("2026-10-13T09:15:02Z", "2026-10-13 09:15:02", "2026-10-13T09:15:02.5", "yesterday", ""):
            with self.subTest(text=text):
                document = _document([_identity()])
                document["observations"][0]["provenance"]["observed_at"] = text
                self._assert_rejected(
                    document,
                    "run/observations.json: observation 0: 'observed_at' is not a canonical "
                    f"ISO-8601 timestamp: '{text}'",
                )

    def test_invalid_json_is_rejected(self):
        with self.assertRaises(ObservationReplayFormatError) as raised:
            parse_observations("{not json", source="run/observations.json")

        self.assertTrue(str(raised.exception).startswith("run/observations.json: not valid JSON: "))

    def test_top_level_array_is_rejected(self):
        self._assert_rejected(
            "[]", "run/observations.json: expected a JSON object at the top level, found array"
        )

    def test_duplicate_keys_are_rejected_not_silently_collapsed(self):
        self._assert_rejected(
            '{"format": "networkmapper.retained-observations", "format_version": 1, '
            '"observations": [], "observations": []}',
            "run/observations.json: duplicate key 'observations'",
        )

    def test_error_is_a_value_error_and_load_reports_the_file_path(self):
        self.assertTrue(issubclass(ObservationReplayFormatError, ValueError))

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "observations.json"
            path.write_text(json.dumps(_document(format="other")), encoding="utf-8")
            with self.assertRaises(ObservationReplayFormatError) as raised:
                load_observations(path)

        self.assertTrue(str(raised.exception).startswith(f"{path}: unknown format identifier 'other'"))

    def test_error_messages_do_not_quote_observation_values(self):
        document = _document([_identity(subject="192.0.2.99", value="secret-host.example")])
        document["observations"][0]["unexpected"] = "192.0.2.98"

        with self.assertRaises(ObservationReplayFormatError) as raised:
            parse_observations(json.dumps(document))

        for sensitive in ("192.0.2.99", "192.0.2.98", "secret-host.example"):
            self.assertNotIn(sensitive, str(raised.exception))


class WriterStrictnessTest(unittest.TestCase):
    def test_non_observation_objects_are_not_serialized(self):
        for candidate in ("not an observation", {"type": "identity"}, None, _provenance()):
            with self.subTest(candidate=candidate):
                with self.assertRaises(TypeError):
                    serialize_observations([_identity(), candidate])

    def test_non_string_fields_are_never_coerced(self):
        candidates = [
            _identity(value=None),
            _identity(value=42),
            _identity(subject=None),
            _relationship(related_subject=None),
            _relationship(category=7),
            _identity(source_run=None),
            _identity(provider=None),
            _identity(observed_at="2026-10-13T09:15:02"),
            IdentityObservation(subject="192.0.2.10", property_name="hostname", value="x", provenance=None),
        ]
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                with self.assertRaises(TypeError):
                    serialize_observations([candidate])


class ArchitectureTest(unittest.TestCase):
    def test_format_module_does_not_import_resolvers_or_project(self):
        script = (
            "import sys\n"
            "import networkmapper.observations.replay_format\n"
            "forbidden = ('networkmapper.identity', 'networkmapper.relationships', 'networkmapper.project')\n"
            "loaded = [name for name in sys.modules if name.startswith(forbidden)]\n"
            "print(','.join(sorted(loaded)))\n"
        )

        completed = subprocess.run(
            [sys.executable, "-c", script], cwd=_REPO_ROOT, capture_output=True, text=True, check=True
        )

        self.assertEqual(completed.stdout.strip(), "")

    def test_no_production_path_references_or_invokes_replay_loading(self):
        """Architectural guard (ADR-011 Amendment 1, Boundaries; PLAN-029 D2).

        Replay is the artifact's only consumer. No module under
        `networkmapper/`, other than the format module that defines the
        loader and the exporter module that is its one sanctioned
        production client, may import or use replay loading. A failure
        here means a normal run, report, comparison, workbench or
        benchmark workflow has started reading `observations.json`, which
        the amendment does not authorize.

        This proves no production path references or invokes the loader.
        It does not prove the loader is unreachable: it remains an
        importable function, used by `devtools` for replay verification.
        """
        package_root = _REPO_ROOT / "networkmapper"
        exempt = {
            package_root / "observations" / "replay_format.py",
            package_root / "exporters" / "observation_json_exporter.py",
        }
        for path in exempt:
            self.assertTrue(path.is_file(), f"guard is stale: {path} does not exist")

        offenders = []
        scanned = 0
        for path in sorted(package_root.rglob("*.py")):
            if path in exempt:
                continue
            scanned += 1
            source = path.read_text(encoding="utf-8")
            for name in ("load_observations", "parse_observations"):
                if name in source:
                    offenders.append(f"{path.relative_to(_REPO_ROOT)}: {name}")

        self.assertGreater(scanned, 20)
        self.assertEqual(offenders, [])

    def test_exporter_module_uses_only_the_serializer(self):
        source = (_REPO_ROOT / "networkmapper" / "exporters" / "observation_json_exporter.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("serialize_observations", source)
        self.assertNotIn("load_observations", source)
        self.assertNotIn("parse_observations", source)


if __name__ == "__main__":
    unittest.main()
