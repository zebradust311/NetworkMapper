"""Read-only replay verification for one run's `observations.json`
(ADR-011 Amendment 1; PLAN-029 Section 7).

`python -m devtools replay-observations <run_dir>` loads the run's
retained observations, re-runs the committed `IdentityResolver` and
`RelationshipResolver` against them, and compares the replayed canonical
relationships with the run's `relationships.csv`.

Limitation: a run directory holds no machine-readable canonical identity
artifact, so this command does NOT prove exact production identity
equality by comparison. It reports replayed identity counts only, and a
MATCH result is a statement about relationship rows only. Exact identity
replay is proven by tests (`tests/test_devtools_replay_observations.py`).

The command opens both files for reading and creates, modifies and
deletes nothing. It never constructs a `Project` and never touches
`ProjectSerializer`.

Sanitization: on a mismatch the report prints raw subjects from the run.
That output is local console output only and must never be pasted into
committed material (OPS-001 D4).
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from networkmapper.identity.models import CanonicalIdentity, IdentityCorroborationState
from networkmapper.identity.resolver import IdentityResolver
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.replay_format import (
    FORMAT_IDENTIFIER,
    FORMAT_VERSION,
    ObservationReplayFormatError,
    load_observations,
)
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState
from networkmapper.relationships.resolver import RelationshipResolver

OBSERVATIONS_FILE_NAME = "observations.json"
RELATIONSHIPS_CSV_FILE_NAME = "relationships.csv"

# The header `RelationshipCsvExporter` writes. The two hostname columns
# come from `Device` data, which is not in the artifact, so they are read
# but never compared.
EXPECTED_CSV_HEADER = (
    "Subject",
    "Subject Hostname",
    "Category",
    "Related Subject",
    "Related Subject Hostname",
    "Corroboration State",
    "Provenance",
)

MAX_DIFFERING_ROWS_SHOWN = 10

EXIT_MATCH = 0
EXIT_MISMATCH = 1
EXIT_CANNOT_REPLAY = 2


class ReplayInputError(Exception):
    """The replay could not run: the run directory or one of its files is
    missing or unusable."""


@dataclass(frozen=True)
class ReplayResult:
    """One run's observations and the canonical records replayed from them."""

    observations: tuple[IdentityObservation | RelationshipObservation, ...]
    identities: tuple[CanonicalIdentity, ...]
    relationships: tuple[CanonicalRelationship, ...]


@dataclass(frozen=True)
class RelationshipRow:
    """The compared columns of one `relationships.csv` row."""

    subject: str
    category: str
    related_subject: str
    state: str
    provenance: str

    @property
    def edge(self) -> tuple[str, str, str]:
        return (self.subject, self.category, self.related_subject)


@dataclass(frozen=True)
class DifferingEdge:
    """One edge present on both sides whose state or provenance differs."""

    edge: tuple[str, str, str]
    csv_rows: tuple[RelationshipRow, ...]
    replayed_rows: tuple[RelationshipRow, ...]


@dataclass(frozen=True)
class RelationshipComparison:
    """The ordered comparison of replayed rows with `relationships.csv`."""

    replayed_rows: tuple[RelationshipRow, ...]
    csv_rows: tuple[RelationshipRow, ...]
    missing_from_replay: int
    not_in_csv: int
    differing: tuple[DifferingEdge, ...]

    @property
    def matches(self) -> bool:
        return self.replayed_rows == self.csv_rows

    @property
    def order_differs(self) -> bool:
        """Same rows on both sides, in a different order."""
        return not self.matches and Counter(self.replayed_rows) == Counter(self.csv_rows)


@dataclass(frozen=True)
class ReplayCommandResult:
    run_dir: Path
    exit_code: int
    replay: ReplayResult | None = None
    comparison: RelationshipComparison | None = None
    error: str | None = None


def replay_observations(run_dir: Path | str) -> ReplayResult:
    """Load `<run_dir>/observations.json` and re-run the committed resolvers.

    The relationship resolver is given no cardinality policy, so the
    module policy applies exactly as it does in `Application.run()`.
    """
    observations = load_observations(Path(run_dir) / OBSERVATIONS_FILE_NAME)
    identities = IdentityResolver().resolve(observations)
    relationships = RelationshipResolver().resolve(observations, identities)
    return ReplayResult(
        observations=tuple(observations),
        identities=identities,
        relationships=relationships,
    )


def relationship_rows(relationships: tuple[CanonicalRelationship, ...]) -> tuple[RelationshipRow, ...]:
    """One comparable row per replayed canonical relationship, in resolver order."""
    return tuple(
        RelationshipRow(
            subject=relationship.subject,
            category=relationship.category,
            related_subject=relationship.related_subject,
            state=relationship.state.value,
            provenance=_provenance_tokens(relationship),
        )
        for relationship in relationships
    )


def _provenance_tokens(relationship: CanonicalRelationship) -> str:
    """Comma-joined `provider/collection_method` tokens, deduplicated in
    the resolver's observation order: the same rule as
    `RelationshipCsvExporter`'s Provenance column. Kept in step with the
    exporter by a parity test rather than by importing its private helper.
    """
    seen: set[tuple[str, str]] = set()
    tokens: list[str] = []
    for observation in relationship.observations:
        key = (observation.provenance.provider, observation.provenance.collection_method)
        if key not in seen:
            seen.add(key)
            tokens.append(f"{key[0]}/{key[1]}")
    return ",".join(tokens)


def read_relationships_csv(csv_path: Path) -> tuple[RelationshipRow, ...]:
    """Read the compared columns of a run's `relationships.csv`, in file order."""
    with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
        rows = list(csv.reader(csv_file))

    if not rows or tuple(rows[0]) != EXPECTED_CSV_HEADER:
        raise ReplayInputError(f"{RELATIONSHIPS_CSV_FILE_NAME} has an unexpected header; cannot compare")

    parsed: list[RelationshipRow] = []
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != len(EXPECTED_CSV_HEADER):
            raise ReplayInputError(
                f"{RELATIONSHIPS_CSV_FILE_NAME} row {line_number} has {len(row)} columns, "
                f"expected {len(EXPECTED_CSV_HEADER)}; cannot compare"
            )
        parsed.append(
            RelationshipRow(
                subject=row[0],
                category=row[2],
                related_subject=row[3],
                state=row[5],
                provenance=row[6],
            )
        )
    return tuple(parsed)


def compare_with_relationships_csv(
    relationships: tuple[CanonicalRelationship, ...], csv_path: Path
) -> RelationshipComparison:
    """Compare replayed relationships with a run's `relationships.csv`.

    The comparison is over ordered rows: both sides follow the resolver's
    `(subject, category, related_subject)` order.
    """
    replayed_rows = relationship_rows(relationships)
    csv_rows = read_relationships_csv(csv_path)

    replayed_edges = Counter(row.edge for row in replayed_rows)
    csv_edges = Counter(row.edge for row in csv_rows)

    differing: list[DifferingEdge] = []
    for edge in sorted(replayed_edges.keys() & csv_edges.keys()):
        edge_csv_rows = tuple(row for row in csv_rows if row.edge == edge)
        edge_replayed_rows = tuple(row for row in replayed_rows if row.edge == edge)
        if Counter(edge_csv_rows) != Counter(edge_replayed_rows):
            differing.append(
                DifferingEdge(edge=edge, csv_rows=edge_csv_rows, replayed_rows=edge_replayed_rows)
            )

    return RelationshipComparison(
        replayed_rows=replayed_rows,
        csv_rows=csv_rows,
        missing_from_replay=sum((csv_edges - replayed_edges).values()),
        not_in_csv=sum((replayed_edges - csv_edges).values()),
        differing=tuple(differing),
    )


def run_replay_command(run_dir: Path | str) -> ReplayCommandResult:
    """Replay one run directory and compare. Never raises for bad input:
    anything that stops the replay becomes exit code 2 with a message."""
    run_dir = Path(run_dir)
    try:
        if not run_dir.is_dir():
            raise ReplayInputError(f"run directory not found: {run_dir}")
        if not (run_dir / OBSERVATIONS_FILE_NAME).is_file():
            raise ReplayInputError(
                f"no {OBSERVATIONS_FILE_NAME} in {run_dir}; the run predates "
                "FEAT-OBSERVATION-JSON-EXPORT or the export failed"
            )
        csv_path = run_dir / RELATIONSHIPS_CSV_FILE_NAME
        if not csv_path.is_file():
            raise ReplayInputError(
                f"no {RELATIONSHIPS_CSV_FILE_NAME} in {run_dir}; cannot compare replayed relationships"
            )

        replay = replay_observations(run_dir)
        comparison = compare_with_relationships_csv(replay.relationships, csv_path)
    except (ReplayInputError, ObservationReplayFormatError) as error:
        return ReplayCommandResult(run_dir=run_dir, exit_code=EXIT_CANNOT_REPLAY, error=str(error))

    return ReplayCommandResult(
        run_dir=run_dir,
        exit_code=EXIT_MATCH if comparison.matches else EXIT_MISMATCH,
        replay=replay,
        comparison=comparison,
    )


def format_replay_report(result: ReplayCommandResult) -> str:
    """Format deterministic replay output."""
    if result.error is not None or result.replay is None or result.comparison is None:
        return f"Error: {result.error}"

    replay = result.replay
    comparison = result.comparison

    identity_observation_count = sum(
        1 for observation in replay.observations if isinstance(observation, IdentityObservation)
    )
    relationship_observation_count = len(replay.observations) - identity_observation_count

    identity_states = Counter(identity.state for identity in replay.identities)
    relationship_states = Counter(relationship.state for relationship in replay.relationships)

    lines = [
        "========================================",
        "NetworkMapper Observation Replay",
        "========================================",
        f"Run directory          : {result.run_dir}",
        f"Format                 : {FORMAT_IDENTIFIER} v{FORMAT_VERSION}",
        (
            f"Observations           : {len(replay.observations)} "
            f"({identity_observation_count} identity, {relationship_observation_count} relationship)"
        ),
        (
            f"Canonical identities   : {len(replay.identities)} "
            "(not compared: no machine-readable identity artifact)"
        ),
        "  " + " / ".join(f"{state.value} {identity_states[state]}" for state in IdentityCorroborationState),
        (
            f"Canonical relationships: {len(comparison.replayed_rows)} replayed, "
            f"{len(comparison.csv_rows)} in {RELATIONSHIPS_CSV_FILE_NAME}"
        ),
        "  "
        + " / ".join(
            f"{state.value} {relationship_states[state]}" for state in RelationshipCorroborationState
        ),
        f"Result                 : {'MATCH' if comparison.matches else 'MISMATCH'}",
    ]

    if not comparison.matches:
        lines.extend(
            [
                f"  Rows missing from the replay: {comparison.missing_from_replay}",
                f"  Rows not in the CSV         : {comparison.not_in_csv}",
                f"  Rows that differ            : {len(comparison.differing)}",
                f"  Row order differs           : {'yes' if comparison.order_differs else 'no'}",
            ]
        )
        for differing in comparison.differing[:MAX_DIFFERING_ROWS_SHOWN]:
            subject, category, related_subject = differing.edge
            lines.append(f"  - {subject} {category} {related_subject}")
            lines.append(f"      csv   : {_describe_rows(differing.csv_rows)}")
            lines.append(f"      replay: {_describe_rows(differing.replayed_rows)}")
        remaining = len(comparison.differing) - MAX_DIFFERING_ROWS_SHOWN
        if remaining > 0:
            lines.append(f"  ... and {remaining} more differing row(s)")

    lines.append("========================================")
    return "\n".join(lines)


def _describe_rows(rows: tuple[RelationshipRow, ...]) -> str:
    return "; ".join(f"{row.state} [{row.provenance}]" for row in rows)
