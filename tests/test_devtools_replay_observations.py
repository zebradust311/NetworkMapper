"""Replay verification tests for `python -m devtools replay-observations`
(ADR-011 Amendment 1; PLAN-029 Sections 7 and 9.3).

Exact identity replay is proven here, by tests: a run directory holds no
machine-readable canonical identity artifact, so the command itself only
compares relationships and reports identity counts.

Each test builds a run directory in a temporary folder with the real
exporters. All values are synthetic: documentation address ranges and
invented MACs and hostnames only (ARCH-028 Section 8).
"""

from __future__ import annotations

import csv
import io
import json
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from devtools.__main__ import main
from devtools.replay_observations import (
    EXPECTED_CSV_HEADER,
    compare_with_relationships_csv,
    format_replay_report,
    replay_observations,
    run_replay_command,
)
from networkmapper.core.models import Device
from networkmapper.discovery.arp_neighbor_provider import SnmpArpNeighborProvider
from networkmapper.discovery.bridge_fdb_provider import SnmpBridgeFdbProvider
from networkmapper.discovery.lldp_neighbor_provider import SnmpLldpNeighborProvider
from networkmapper.discovery.snmp_client import (
    SnmpArpTableEntry,
    SnmpArpTableResult,
    SnmpBridgeFdbEntry,
    SnmpBridgeFdbResult,
    SnmpClient,
    SnmpLldpNeighborEntry,
    SnmpLldpTableResult,
)
from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion
from networkmapper.exporters.observation_json_exporter import ObservationJsonExporter
from networkmapper.exporters.relationship_csv_exporter import RelationshipCsvExporter
from networkmapper.identity.models import IdentityCorroborationState
from networkmapper.identity.resolver import IdentityResolver
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.project.models import Project
from networkmapper.relationships.models import RelationshipCorroborationState
from networkmapper.relationships.resolver import RelationshipResolver

_A = "192.0.2.1"
_B = "192.0.2.10"
_C = "192.0.2.11"
_D = "192.0.2.12"
_UNDISCOVERED = "198.51.100.77"


def _provenance(provider, collection_method, source_run="run-001", observed_at=None) -> ObservationProvenance:
    return ObservationProvenance(
        provider=provider,
        collection_method=collection_method,
        observed_at=observed_at or datetime(2026, 10, 13, 9, 15, 2, 123456),
        source_run=source_run,
    )


def _identity(subject, property_name, value, provider="nmap", collection_method="host-discovery", **kwargs):
    return IdentityObservation(
        subject=subject,
        property_name=property_name,
        value=value,
        provenance=_provenance(provider, collection_method, **kwargs),
    )


def _relationship(subject, related_subject, category, provider="snmp", collection_method="ipNetToPhysicalTable", **kwargs):
    return RelationshipObservation(
        subject=subject,
        related_subject=related_subject,
        category=category,
        provenance=_provenance(provider, collection_method, **kwargs),
    )


def _identity_observations_covering_every_state():
    return [
        # _A: WEAK (one property, one source).
        _identity(_A, "mac_address", "02:00:5E:00:53:01"),
        # _B: PROBABLE (two properties, each from one source).
        _identity(_B, "mac_address", "02:00:5E:00:53:0A"),
        _identity(_B, "hostname", "host-b.example"),
        # _C: CONFIRMED (two independent sources agree).
        _identity(_C, "hostname", "host-c.example"),
        _identity(_C, "hostname", "host-c.example", provider="snmp", collection_method="sysName"),
        # _D: CONFLICTING (two sources disagree).
        _identity(_D, "hostname", "host-d.example"),
        _identity(_D, "hostname", "other-d.example", provider="snmp", collection_method="sysName"),
    ]


def _mixed_observations():
    return _identity_observations_covering_every_state() + [
        # CONFIRMED edge: two independent sources.
        _relationship(_A, _B, "connected_to", collection_method="lldpRemTable"),
        _relationship(_A, _B, "connected_to", provider="nmap", collection_method="lldp-neighbor"),
        # Fan-out of WEAK edges in one category.
        _relationship(_A, _B, "arp_neighbor"),
        _relationship(_A, _C, "arp_neighbor"),
        _relationship(_A, _D, "arp_neighbor"),
        # Same source repeated across runs: still one source.
        _relationship(_A, _C, "arp_neighbor", source_run="run-002"),
        _relationship(
            _A, _C, "arp_neighbor", source_run="run-003", observed_at=datetime(2026, 10, 13, 9, 15, 2, tzinfo=timezone.utc)
        ),
        # Exact duplicates.
        _relationship(_C, _D, "bridge_fdb", collection_method="dot1dTpFdbTable"),
        _relationship(_C, _D, "bridge_fdb", collection_method="dot1dTpFdbTable"),
        _identity(_A, "mac_address", "02:00:5E:00:53:01"),
        # Self-loop: excluded by the resolver, retained as evidence.
        _relationship(_A, _A, "arp_neighbor"),
        # Unresolved endpoints: excluded by the resolver, retained as evidence.
        _relationship(_A, _UNDISCOVERED, "arp_neighbor"),
        _relationship(_UNDISCOVERED, _B, "connected_to", collection_method="lldpRemTable"),
    ]


def _resolve_project(observations) -> Project:
    identities = IdentityResolver().resolve(observations)
    project = Project(
        customer_name="Synthetic Example",
        observations=list(observations),
        canonical_identities=identities,
        canonical_relationships=RelationshipResolver().resolve(observations, identities),
    )
    for subject in (_A, _B, _C, _D):
        project.network_graph.add_device(Device(ip_address=subject, hostname=f"device-{subject}", vendor="Example"))
    return project


def _write_run(run_dir: Path, observations) -> Project:
    """Write the two artifacts the command reads, with the real exporters."""
    project = _resolve_project(observations)
    ObservationJsonExporter().export(project, str(run_dir / "observations.json"))
    RelationshipCsvExporter().export(project, str(run_dir / "relationships.csv"))
    return project


def _read_csv(run_dir: Path) -> list[list[str]]:
    with open(run_dir / "relationships.csv", "r", newline="", encoding="utf-8") as csv_file:
        return list(csv.reader(csv_file))


def _write_csv(run_dir: Path, rows: list[list[str]]) -> None:
    with open(run_dir / "relationships.csv", "w", newline="", encoding="utf-8") as csv_file:
        csv.writer(csv_file).writerows(rows)


def _snapshot(run_dir: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(run_dir.iterdir())}


def _run_main(arguments: list[str]) -> tuple[int, str]:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(arguments)
    return exit_code, stdout.getvalue()


class _RunDirectoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.run_dir = Path(temp_dir.name) / "2026-10-13_091502_standard"
        self.run_dir.mkdir()


class ExactReplayTest(_RunDirectoryTestCase):
    def test_identity_only_run_replays_canonical_identities_exactly(self):
        project = _write_run(self.run_dir, _identity_observations_covering_every_state())

        replay = replay_observations(self.run_dir)

        self.assertEqual(replay.identities, project.canonical_identities)
        self.assertEqual(replay.relationships, ())
        self.assertEqual(project.canonical_relationships, ())

    def test_mixed_run_replays_identities_and_relationships_exactly(self):
        project = _write_run(self.run_dir, _mixed_observations())

        replay = replay_observations(self.run_dir)

        self.assertEqual(replay.identities, project.canonical_identities)
        self.assertEqual(replay.relationships, project.canonical_relationships)
        self.assertEqual(len(replay.observations), len(project.observations))

        # The fixture really exercises what it claims to.
        states = {relationship.state for relationship in replay.relationships}
        self.assertEqual(
            states, {RelationshipCorroborationState.WEAK, RelationshipCorroborationState.CONFIRMED}
        )
        edges = {(r.subject, r.category, r.related_subject) for r in replay.relationships}
        self.assertNotIn((_A, "arp_neighbor", _A), edges)
        self.assertNotIn((_A, "arp_neighbor", _UNDISCOVERED), edges)
        self.assertIn(
            _relationship(_A, _UNDISCOVERED, "arp_neighbor"), replay.observations
        )

    def test_every_identity_state_is_reproduced(self):
        project = _write_run(self.run_dir, _identity_observations_covering_every_state())

        replay = replay_observations(self.run_dir)

        self.assertEqual(
            {identity.subject: identity.state for identity in replay.identities},
            {
                _A: IdentityCorroborationState.WEAK,
                _B: IdentityCorroborationState.PROBABLE,
                _C: IdentityCorroborationState.CONFIRMED,
                _D: IdentityCorroborationState.CONFLICTING,
            },
        )
        self.assertEqual(replay.identities, project.canonical_identities)

    def test_replay_is_exact_for_identity_observations_that_tie_on_source_and_value(self):
        # Same subject, property, provider, collection method and value,
        # told apart only by source_run or observed_at. The artifact stores
        # them in its own sorted order, not the order the run collected them
        # in, so replay is exact only if the identity resolver orders such
        # ties by value rather than by input position (ADR-012).
        tied = [
            _identity(_A, "hostname", "host-a.example", source_run="run-c"),
            _identity(_A, "hostname", "host-a.example", source_run="run-a"),
            _identity(_A, "hostname", "host-a.example", source_run="run-b"),
            _identity(
                _A, "hostname", "host-a.example", source_run="run-a", observed_at=datetime(2026, 10, 13, 9, 15, 3)
            ),
            _identity(
                _A,
                "hostname",
                "host-a.example",
                source_run="run-a",
                observed_at=datetime(2026, 10, 13, 9, 15, 2, tzinfo=timezone.utc),
            ),
            _identity(_B, "mac_address", "02:00:5E:00:53:0A", source_run="run-b"),
            _identity(_B, "mac_address", "02:00:5E:00:53:0A", source_run="run-a"),
        ]
        rng = random.Random(29)

        for _ in range(50):
            collected = list(tied)
            rng.shuffle(collected)
            project = _write_run(self.run_dir, collected)

            replay = replay_observations(self.run_dir)

            self.assertEqual(replay.identities, project.canonical_identities)
            self.assertEqual(
                [o.provenance.source_run for o in replay.identities[0].properties[0].observations],
                ["run-a", "run-a", "run-a", "run-b", "run-c"],
            )

    def test_replay_is_exact_whatever_order_the_run_collected_observations_in(self):
        observations = _mixed_observations()
        expected = _resolve_project(observations)
        rng = random.Random(29)

        for _ in range(25):
            shuffled = list(observations)
            rng.shuffle(shuffled)
            _write_run(self.run_dir, shuffled)

            replay = replay_observations(self.run_dir)

            self.assertEqual(replay.identities, expected.canonical_identities)
            self.assertEqual(replay.relationships, expected.canonical_relationships)

    def test_replay_is_exact_end_to_end_from_real_providers(self):
        observations = _collect_provider_observations()
        project = _write_run(self.run_dir, observations)
        self.assertTrue(project.canonical_relationships)

        replay = replay_observations(self.run_dir)

        self.assertEqual(replay.identities, project.canonical_identities)
        self.assertEqual(replay.relationships, project.canonical_relationships)
        self.assertEqual(run_replay_command(self.run_dir).exit_code, 0)

    def test_replay_does_not_build_a_project_or_touch_the_serializer(self):
        _write_run(self.run_dir, _mixed_observations())
        source = (Path(__file__).resolve().parent.parent / "devtools" / "replay_observations.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("import Project", source)
        self.assertNotIn("networkmapper.project", source)
        self.assertNotIn("Project(", source)


class ComparisonTest(_RunDirectoryTestCase):
    def test_untouched_run_matches(self):
        # Also the parity test for provenance tokens: the CSV comes from the
        # real RelationshipCsvExporter, the replayed rows from devtools.
        project = _write_run(self.run_dir, _mixed_observations())

        result = run_replay_command(self.run_dir)

        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.error)
        self.assertTrue(result.comparison.matches)
        self.assertEqual(len(result.comparison.csv_rows), len(project.canonical_relationships))
        self.assertEqual(result.comparison.missing_from_replay, 0)
        self.assertEqual(result.comparison.not_in_csv, 0)
        self.assertEqual(result.comparison.differing, ())
        # A multi-source edge has a multi-token provenance cell on both sides.
        self.assertTrue(any("," in row.provenance for row in result.comparison.csv_rows))

    def test_changed_state_is_a_mismatch(self):
        _write_run(self.run_dir, _mixed_observations())
        rows = _read_csv(self.run_dir)
        rows[1][5] = "confirmed" if rows[1][5] == "weak" else "weak"
        _write_csv(self.run_dir, rows)

        result = run_replay_command(self.run_dir)

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(len(result.comparison.differing), 1)
        self.assertEqual(result.comparison.missing_from_replay, 0)
        self.assertEqual(result.comparison.not_in_csv, 0)
        self.assertFalse(result.comparison.order_differs)

    def test_changed_provenance_is_a_mismatch(self):
        _write_run(self.run_dir, _mixed_observations())
        rows = _read_csv(self.run_dir)
        rows[1][6] = "snmp/somethingElse"
        _write_csv(self.run_dir, rows)

        result = run_replay_command(self.run_dir)

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(len(result.comparison.differing), 1)

    def test_row_removed_from_the_csv_is_a_mismatch(self):
        _write_run(self.run_dir, _mixed_observations())
        rows = _read_csv(self.run_dir)
        del rows[2]
        _write_csv(self.run_dir, rows)

        result = run_replay_command(self.run_dir)

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.comparison.not_in_csv, 1)
        self.assertEqual(result.comparison.missing_from_replay, 0)
        self.assertEqual(result.comparison.differing, ())

    def test_row_added_to_the_csv_is_a_mismatch(self):
        _write_run(self.run_dir, _mixed_observations())
        rows = _read_csv(self.run_dir)
        rows.append([_D, "", "arp_neighbor", _A, "", "weak", "snmp/ipNetToPhysicalTable"])
        _write_csv(self.run_dir, rows)

        result = run_replay_command(self.run_dir)

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.comparison.missing_from_replay, 1)
        self.assertEqual(result.comparison.not_in_csv, 0)
        self.assertEqual(result.comparison.differing, ())

    def test_reordered_rows_are_a_mismatch(self):
        _write_run(self.run_dir, _mixed_observations())
        rows = _read_csv(self.run_dir)
        rows[1], rows[2] = rows[2], rows[1]
        _write_csv(self.run_dir, rows)

        result = run_replay_command(self.run_dir)

        self.assertEqual(result.exit_code, 1)
        self.assertTrue(result.comparison.order_differs)
        self.assertEqual(result.comparison.missing_from_replay, 0)
        self.assertEqual(result.comparison.not_in_csv, 0)
        self.assertEqual(result.comparison.differing, ())

    def test_hostname_columns_are_not_compared(self):
        _write_run(self.run_dir, _mixed_observations())
        rows = _read_csv(self.run_dir)
        self.assertTrue(rows[1][1])  # the exporter really wrote a hostname
        for row in rows[1:]:
            row[1] = "renamed.example"
            row[4] = ""
        _write_csv(self.run_dir, rows)

        self.assertEqual(run_replay_command(self.run_dir).exit_code, 0)

    def test_run_with_no_relationships_matches_a_header_only_csv(self):
        _write_run(self.run_dir, _identity_observations_covering_every_state())
        self.assertEqual(_read_csv(self.run_dir), [list(EXPECTED_CSV_HEADER)])

        result = run_replay_command(self.run_dir)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.comparison.csv_rows, ())

    def test_run_with_no_observations_at_all_matches(self):
        _write_run(self.run_dir, [])

        result = run_replay_command(self.run_dir)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.replay.observations, ())

    def test_compare_function_takes_replayed_relationships_and_a_csv_path(self):
        project = _write_run(self.run_dir, _mixed_observations())

        comparison = compare_with_relationships_csv(
            project.canonical_relationships, self.run_dir / "relationships.csv"
        )

        self.assertTrue(comparison.matches)


class CommandTest(_RunDirectoryTestCase):
    def test_matching_run_prints_the_report_and_exits_zero(self):
        project = _write_run(self.run_dir, _mixed_observations())
        relationship_count = len(project.canonical_relationships)
        identity_observations = sum(isinstance(o, IdentityObservation) for o in project.observations)

        exit_code, output = _run_main(["replay-observations", str(self.run_dir)])

        self.assertEqual(exit_code, 0)
        lines = output.splitlines()
        self.assertEqual(lines[1], "NetworkMapper Observation Replay")
        self.assertIn(f"Run directory          : {self.run_dir}", lines)
        self.assertIn("Format                 : networkmapper.retained-observations v1", lines)
        self.assertIn(
            f"Observations           : {len(project.observations)} "
            f"({identity_observations} identity, {len(project.observations) - identity_observations} relationship)",
            lines,
        )
        self.assertIn(
            "Canonical identities   : 4 (not compared: no machine-readable identity artifact)", lines
        )
        self.assertIn("  weak 1 / probable 1 / confirmed 1 / conflicting 1", lines)
        self.assertIn(
            f"Canonical relationships: {relationship_count} replayed, {relationship_count} in relationships.csv",
            lines,
        )
        self.assertIn(f"  weak {relationship_count - 1} / confirmed 1 / conflicting 0", lines)
        self.assertIn("Result                 : MATCH", lines)

    def test_mismatching_run_prints_counts_and_exits_one(self):
        _write_run(self.run_dir, _mixed_observations())
        rows = _read_csv(self.run_dir)
        rows[1][5] = "conflicting"
        del rows[3]
        _write_csv(self.run_dir, rows)

        exit_code, output = _run_main(["replay-observations", str(self.run_dir)])

        self.assertEqual(exit_code, 1)
        self.assertIn("Result                 : MISMATCH", output)
        self.assertIn("  Rows missing from the replay: 0", output)
        self.assertIn("  Rows not in the CSV         : 1", output)
        self.assertIn("  Rows that differ            : 1", output)
        self.assertIn("      csv   : conflicting [", output)

    def test_at_most_ten_differing_rows_are_shown(self):
        hosts = [f"192.0.2.{index}" for index in range(100, 115)]
        observations = [_identity(_A, "mac_address", "02:00:5E:00:53:01")]
        observations += [_identity(host, "hostname", f"h{index}.example") for index, host in enumerate(hosts)]
        observations += [_relationship(_A, host, "arp_neighbor") for host in hosts]
        _write_run(self.run_dir, observations)
        rows = _read_csv(self.run_dir)
        for row in rows[1:]:
            row[5] = "confirmed"
        _write_csv(self.run_dir, rows)

        result = run_replay_command(self.run_dir)
        report = format_replay_report(result)

        self.assertEqual(result.exit_code, 1)
        self.assertIn("  Rows that differ            : 15", report)
        self.assertEqual(report.count("      csv   : "), 10)
        self.assertIn("  ... and 5 more differing row(s)", report)

    def test_missing_run_directory_exits_two(self):
        missing = self.run_dir / "does-not-exist"

        exit_code, output = _run_main(["replay-observations", str(missing)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(output.strip(), f"Error: run directory not found: {missing}")

    def test_missing_observations_json_exits_two(self):
        _write_run(self.run_dir, _mixed_observations())
        (self.run_dir / "observations.json").unlink()

        exit_code, output = _run_main(["replay-observations", str(self.run_dir)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            output.strip(),
            f"Error: no observations.json in {self.run_dir}; the run predates "
            "FEAT-OBSERVATION-JSON-EXPORT or the export failed",
        )

    def test_missing_relationships_csv_exits_two(self):
        _write_run(self.run_dir, _mixed_observations())
        (self.run_dir / "relationships.csv").unlink()

        exit_code, output = _run_main(["replay-observations", str(self.run_dir)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            output.strip(),
            f"Error: no relationships.csv in {self.run_dir}; cannot compare replayed relationships",
        )

    def test_unexpected_csv_header_exits_two(self):
        _write_run(self.run_dir, _mixed_observations())
        rows = _read_csv(self.run_dir)
        rows[0][5] = "State"
        _write_csv(self.run_dir, rows)

        exit_code, output = _run_main(["replay-observations", str(self.run_dir)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(output.strip(), "Error: relationships.csv has an unexpected header; cannot compare")

    def test_empty_csv_exits_two(self):
        _write_run(self.run_dir, _mixed_observations())
        (self.run_dir / "relationships.csv").write_bytes(b"")

        exit_code, output = _run_main(["replay-observations", str(self.run_dir)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(output.strip(), "Error: relationships.csv has an unexpected header; cannot compare")

    def test_malformed_csv_row_exits_two(self):
        _write_run(self.run_dir, _mixed_observations())
        rows = _read_csv(self.run_dir)
        rows[1] = rows[1][:4]
        _write_csv(self.run_dir, rows)

        exit_code, output = _run_main(["replay-observations", str(self.run_dir)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            output.strip(), "Error: relationships.csv row 2 has 4 columns, expected 7; cannot compare"
        )

    def _corrupt_artifact(self, mutate) -> Path:
        _write_run(self.run_dir, _mixed_observations())
        path = self.run_dir / "observations.json"
        document = json.loads(path.read_bytes())
        mutate(document)
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def test_unknown_format_identifier_exits_two_with_the_loader_message(self):
        path = self._corrupt_artifact(lambda document: document.update(format="other.format"))

        exit_code, output = _run_main(["replay-observations", str(self.run_dir)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            output.strip(),
            f"Error: {path}: unknown format identifier 'other.format'; "
            "expected 'networkmapper.retained-observations'",
        )

    def test_unknown_format_version_exits_two_with_the_loader_message(self):
        path = self._corrupt_artifact(lambda document: document.update(format_version=2))

        exit_code, output = _run_main(["replay-observations", str(self.run_dir)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            output.strip(),
            f"Error: {path}: unsupported format version 2; this build reads version 1 only",
        )

    def test_unknown_observation_type_exits_two_with_the_loader_message(self):
        path = self._corrupt_artifact(lambda document: document["observations"][3].update(type="lifecycle"))

        exit_code, output = _run_main(["replay-observations", str(self.run_dir)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            output.strip(),
            f"Error: {path}: observation 3: unknown observation type 'lifecycle'; "
            "expected 'identity' or 'relationship'",
        )

    def test_wrong_argument_count_prints_usage_and_exits_one(self):
        for arguments in (["replay-observations"], ["replay-observations", "one", "two"]):
            with self.subTest(arguments=arguments):
                exit_code, output = _run_main(arguments)

                self.assertEqual(exit_code, 1)
                self.assertIn("Usage: python -m devtools <command>", output)
                self.assertIn("replay-observations <run_dir>", output)

    def test_command_is_read_only(self):
        _write_run(self.run_dir, _mixed_observations())
        (self.run_dir / "report.md").write_text("# report\n", encoding="utf-8")

        before = _snapshot(self.run_dir)
        exit_code, _ = _run_main(["replay-observations", str(self.run_dir)])
        self.assertEqual(exit_code, 0)
        self.assertEqual(_snapshot(self.run_dir), before)

        rows = _read_csv(self.run_dir)
        rows[1][5] = "conflicting"
        _write_csv(self.run_dir, rows)
        before = _snapshot(self.run_dir)
        exit_code, _ = _run_main(["replay-observations", str(self.run_dir)])
        self.assertEqual(exit_code, 1)
        self.assertEqual(_snapshot(self.run_dir), before)

        (self.run_dir / "observations.json").write_text("{", encoding="utf-8")
        before = _snapshot(self.run_dir)
        exit_code, _ = _run_main(["replay-observations", str(self.run_dir)])
        self.assertEqual(exit_code, 2)
        self.assertEqual(_snapshot(self.run_dir), before)
        self.assertEqual(sorted(path.name for path in self.run_dir.parent.iterdir()), [self.run_dir.name])


# --- end-to-end provider fixture -------------------------------------------

_SWITCH = "192.0.2.2"
_PROVIDER_MACS = {
    _A: "02:00:5E:00:53:01",
    _SWITCH: "02:00:5E:00:53:02",
    _B: "02:00:5E:00:53:0A",
    _C: "02:00:5E:00:53:0B",
}


class _StubSnmpClient(SnmpClient):
    """Canned synthetic ARP, forwarding-table and LLDP answers; any other
    host times out."""

    def get_arp_table(self, host, credentials, timeout, retries) -> SnmpArpTableResult:
        if host != _A:
            return SnmpArpTableResult(responded=False, failure_reason="timeout")
        return SnmpArpTableResult(
            responded=True,
            entries=[
                SnmpArpTableEntry(
                    interface_index=1, ip_address=address, mac_address=_PROVIDER_MACS[address], entry_type="dynamic"
                )
                for address in (_B, _C)
            ]
            + [
                SnmpArpTableEntry(
                    interface_index=1,
                    ip_address=_UNDISCOVERED,
                    mac_address="02:00:5E:00:53:FF",
                    entry_type="dynamic",
                )
            ],
        )

    def get_bridge_fdb(self, host, credentials, timeout, retries) -> SnmpBridgeFdbResult:
        if host != _SWITCH:
            return SnmpBridgeFdbResult(responded=False, failure_reason="timeout")
        return SnmpBridgeFdbResult(
            responded=True,
            entries=[
                SnmpBridgeFdbEntry(mac_address=_PROVIDER_MACS[address], port=port, status="learned")
                for port, address in enumerate((_B, _C), start=1)
            ],
        )

    def get_lldp_neighbors(self, host, credentials, timeout, retries) -> SnmpLldpTableResult:
        if host != _SWITCH:
            return SnmpLldpTableResult(responded=False, failure_reason="timeout")
        return SnmpLldpTableResult(
            responded=True,
            entries=[
                SnmpLldpNeighborEntry(
                    local_port_num=1,
                    rem_index=1,
                    chassis_id_subtype=4,
                    chassis_id=_PROVIDER_MACS[_A],
                    sys_name="device-a.example",
                    management_addresses=[_A],
                )
            ],
        )


def _collect_provider_observations():
    credentials = SnmpCredentials(version=SnmpVersion.V2C, community="synthetic-community")
    devices = [Device(ip_address=address) for address in sorted(_PROVIDER_MACS)]
    observations: list[IdentityObservation | RelationshipObservation] = [
        _identity(subject, "mac_address", mac) for subject, mac in sorted(_PROVIDER_MACS.items())
    ]

    for provider_class in (SnmpArpNeighborProvider, SnmpLldpNeighborProvider, SnmpBridgeFdbProvider):
        provider = provider_class(credentials, client=_StubSnmpClient())
        provider.receive_observations(tuple(observations))
        provider.enrich(devices)
        observations.extend(provider.collect_observations())

    return observations


if __name__ == "__main__":
    unittest.main()
