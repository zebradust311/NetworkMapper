"""Replay artifact format for retained observations (ADR-011 Amendment 1;
ARCH-028; PLAN-029).

One versioned JSON document holds every retained observation of one run,
so the committed resolvers can later be re-run against exactly the
evidence that run collected. This module owns both directions of the
format: `serialize_observations` (used by `ObservationJsonExporter`) and
`parse_observations`/`load_observations` (used only by replay
verification in `devtools`).

This is a replay artifact, not project persistence. Nothing here builds a
`Project`, touches `ProjectSerializer` or the `.nmproj` format, assigns
observation identifiers, or merges runs, and the reading functions are
never referenced by a normal run, report, comparison, workbench or
benchmark workflow (ADR-011 Amendment 1, Boundaries; PLAN-029 D2).

Guarantees:
- Lossless: every observation is written with every field, verbatim.
  Duplicates stay duplicates, and a relationship observation is written
  whether or not its endpoints ever resolve.
- Deterministic: the same multiset of observations produces the same
  bytes regardless of input order (records are sorted by a total key over
  every field; keys are sorted; whitespace and line endings are fixed).
- Strict: reading rejects an unknown format identifier, an unsupported
  format version, an unknown observation type, and any unknown, missing
  or mistyped content. Nothing is ever skipped (PLAN-029 D4).

Timestamps: `observed_at` is written with `datetime.isoformat()` and is
never normalized, so sub-second precision and the presence or absence of
timezone information survive exactly. A round-tripped value compares
equal to the original, with an identical `isoformat()` and `utcoffset()`.
Two things are not recorded, because neither is part of `isoformat()` or
of `datetime` equality: a named zone object (an aware value comes back
with a fixed-offset `datetime.timezone`) and the `fold` attribute.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance

FORMAT_IDENTIFIER = "networkmapper.retained-observations"
FORMAT_VERSION = 1

_IDENTITY_TYPE = "identity"
_RELATIONSHIP_TYPE = "relationship"

_TOP_LEVEL_KEYS = ("format", "format_version", "observations")
_IDENTITY_KEYS = ("type", "subject", "property_name", "value", "provenance")
_RELATIONSHIP_KEYS = ("type", "subject", "related_subject", "category", "provenance")
_PROVENANCE_KEYS = ("provider", "collection_method", "observed_at", "source_run")


class ObservationReplayFormatError(ValueError):
    """A replay artifact could not be read as format version 1.

    Messages name keys and record positions, never observation values.
    The only values quoted are format metadata: an offending format
    identifier, version or type, and an offending timestamp string.
    """


def serialize_observations(
    observations: Iterable[IdentityObservation | RelationshipObservation],
) -> bytes:
    """Return the replay artifact for `observations` as bytes.

    Never mutates or reorders its input. Never coerces: an object that is
    neither observation type, a non-`str` field, or a non-`datetime`
    `observed_at` raises `TypeError`, because converting it would break
    the lossless guarantee unnoticed (PLAN-029 D6).

    The output is pure ASCII with `\\n` line endings and one trailing
    newline, so it is byte-identical on every platform (PLAN-029 D5).
    """
    records = sorted(
        (_to_record(observation) for observation in observations),
        key=_record_sort_key,
    )
    document = {
        "format": FORMAT_IDENTIFIER,
        "format_version": FORMAT_VERSION,
        "observations": records,
    }
    text = json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    return text.encode("ascii")


def parse_observations(
    data: bytes | str, source: str = "<data>"
) -> list[IdentityObservation | RelationshipObservation]:
    """Reconstruct the observations in a replay artifact, in file order.

    For replay verification only. `source` names the artifact in error
    messages. Raises `ObservationReplayFormatError` on the first invalid
    element; no partial list is ever returned.
    """
    try:
        text = data.decode("utf-8") if isinstance(data, bytes) else data
        document = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ObservationReplayFormatError(f"{source}: not valid JSON: {error}") from None
    except _DuplicateKeyError as error:
        raise ObservationReplayFormatError(f"{source}: duplicate key '{error.key}'") from None

    if not isinstance(document, dict):
        raise ObservationReplayFormatError(
            f"{source}: expected a JSON object at the top level, found {_json_type(document)}"
        )

    if "format" not in document:
        raise ObservationReplayFormatError(f"{source}: missing required key 'format'")
    format_identifier = document["format"]
    if format_identifier != FORMAT_IDENTIFIER:
        shown = format_identifier if isinstance(format_identifier, str) else json.dumps(format_identifier)
        raise ObservationReplayFormatError(
            f"{source}: unknown format identifier '{shown}'; expected '{FORMAT_IDENTIFIER}'"
        )

    if "format_version" not in document:
        raise ObservationReplayFormatError(f"{source}: missing required key 'format_version'")
    format_version = document["format_version"]
    # `type(...) is int`, not `==`: True == 1 and 1.0 == 1 in Python.
    if type(format_version) is not int or format_version != FORMAT_VERSION:
        raise ObservationReplayFormatError(
            f"{source}: unsupported format version {json.dumps(format_version)}; "
            f"this build reads version {FORMAT_VERSION} only"
        )

    for key in sorted(document):
        if key not in _TOP_LEVEL_KEYS:
            raise ObservationReplayFormatError(f"{source}: unknown top-level key '{key}'")

    records = document.get("observations")
    if not isinstance(records, list):
        raise ObservationReplayFormatError(f"{source}: 'observations' must be a JSON array")

    return [_from_record(record, f"{source}: observation {index}") for index, record in enumerate(records)]


def load_observations(path: Path | str) -> list[IdentityObservation | RelationshipObservation]:
    """Read one run's `observations.json` for replay verification only.

    Opens the file for reading and returns plain observation objects. It
    never constructs a `Project` and never writes anything.
    """
    return parse_observations(Path(path).read_bytes(), source=str(path))


def _to_record(observation: object) -> dict[str, Any]:
    if isinstance(observation, IdentityObservation):
        record: dict[str, Any] = {
            "type": _IDENTITY_TYPE,
            "subject": _require_str(observation.subject, "subject"),
            "property_name": _require_str(observation.property_name, "property_name"),
            "value": _require_str(observation.value, "value"),
        }
    elif isinstance(observation, RelationshipObservation):
        record = {
            "type": _RELATIONSHIP_TYPE,
            "subject": _require_str(observation.subject, "subject"),
            "related_subject": _require_str(observation.related_subject, "related_subject"),
            "category": _require_str(observation.category, "category"),
        }
    else:
        raise TypeError(
            "cannot serialize a non-observation object of type "
            f"{type(observation).__name__}"
        )

    provenance = observation.provenance
    if not isinstance(provenance, ObservationProvenance):
        raise TypeError(
            f"observation provenance must be ObservationProvenance, found {type(provenance).__name__}"
        )
    if not isinstance(provenance.observed_at, datetime):
        raise TypeError(
            f"observation field 'observed_at' must be datetime, found {type(provenance.observed_at).__name__}"
        )

    record["provenance"] = {
        "provider": _require_str(provenance.provider, "provider"),
        "collection_method": _require_str(provenance.collection_method, "collection_method"),
        "observed_at": provenance.observed_at.isoformat(),
        "source_run": _require_str(provenance.source_run, "source_run"),
    }
    return record


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"observation field '{field_name}' must be str, found {type(value).__name__}")
    return value


def _record_sort_key(record: dict[str, Any]) -> tuple[str, str, str, str, str, str, str, str]:
    """Total order over every serialized field (PLAN-029 Section 5).

    Two records that tie on all eight positions are byte-identical, so
    their relative order cannot affect the output. The timestamp is
    compared through its ISO string, never as a `datetime`, so mixed
    naive and aware values cannot raise `TypeError`.
    """
    provenance = record["provenance"]
    if record["type"] == _IDENTITY_TYPE:
        third, fourth = record["property_name"], record["value"]
    else:
        third, fourth = record["related_subject"], record["category"]
    return (
        record["type"],
        record["subject"],
        third,
        fourth,
        provenance["provider"],
        provenance["collection_method"],
        provenance["source_run"],
        provenance["observed_at"],
    )


def _from_record(record: object, where: str) -> IdentityObservation | RelationshipObservation:
    if not isinstance(record, dict):
        raise ObservationReplayFormatError(
            f"{where}: expected a JSON object, found {_json_type(record)}"
        )

    if "type" not in record:
        raise ObservationReplayFormatError(f"{where}: missing required key 'type'")
    observation_type = record["type"]
    if observation_type == _IDENTITY_TYPE:
        expected_keys = _IDENTITY_KEYS
    elif observation_type == _RELATIONSHIP_TYPE:
        expected_keys = _RELATIONSHIP_KEYS
    else:
        shown = observation_type if isinstance(observation_type, str) else json.dumps(observation_type)
        raise ObservationReplayFormatError(
            f"{where}: unknown observation type '{shown}'; "
            f"expected '{_IDENTITY_TYPE}' or '{_RELATIONSHIP_TYPE}'"
        )

    _check_keys(record, expected_keys, where)

    provenance_record = record["provenance"]
    if not isinstance(provenance_record, dict):
        raise ObservationReplayFormatError(
            f"{where}: 'provenance' must be a JSON object, found {_json_type(provenance_record)}"
        )
    _check_keys(provenance_record, _PROVENANCE_KEYS, where)

    for key in expected_keys:
        if key != "provenance":
            _check_string(record, key, where)
    for key in _PROVENANCE_KEYS:
        _check_string(provenance_record, key, where)

    provenance = ObservationProvenance(
        provider=provenance_record["provider"],
        collection_method=provenance_record["collection_method"],
        observed_at=_parse_observed_at(provenance_record["observed_at"], where),
        source_run=provenance_record["source_run"],
    )

    if observation_type == _IDENTITY_TYPE:
        return IdentityObservation(
            subject=record["subject"],
            property_name=record["property_name"],
            value=record["value"],
            provenance=provenance,
        )
    return RelationshipObservation(
        subject=record["subject"],
        related_subject=record["related_subject"],
        category=record["category"],
        provenance=provenance,
    )


def _check_keys(record: dict[str, Any], expected_keys: tuple[str, ...], where: str) -> None:
    for key in expected_keys:
        if key not in record:
            raise ObservationReplayFormatError(f"{where}: missing required key '{key}'")
    for key in sorted(record):
        if key not in expected_keys:
            raise ObservationReplayFormatError(f"{where}: unknown key '{key}'")


def _check_string(record: dict[str, Any], key: str, where: str) -> None:
    if not isinstance(record[key], str):
        raise ObservationReplayFormatError(
            f"{where}: '{key}' must be a string, found {_json_type(record[key])}"
        )


def _parse_observed_at(text: str, where: str) -> datetime:
    """Parse a timestamp, accepting only the exact form the writer produces.

    A string that parses but is not canonical (a `Z` suffix, a space
    separator) is rejected rather than normalized, so serializing a loaded
    artifact always reproduces it byte for byte.
    """
    try:
        observed_at = datetime.fromisoformat(text)
    except ValueError:
        observed_at = None
    if observed_at is None or observed_at.isoformat() != text:
        raise ObservationReplayFormatError(
            f"{where}: 'observed_at' is not a canonical ISO-8601 timestamp: '{text}'"
        )
    return observed_at


def _json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


class _DuplicateKeyError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """`json` keeps the last of two duplicate keys and silently drops the
    first. Dropped content must be rejected, never skipped (PLAN-029 D4)."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result
