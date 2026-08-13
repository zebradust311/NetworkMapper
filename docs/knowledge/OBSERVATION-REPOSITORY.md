# Observation Repository

KNOW-003 introduced a structured, version-controlled repository for
preserving field evidence NetworkMapper could not yet classify: one
compact JSON document per device, under `knowledge/observations/`.

This complements, and does not replace, [FIELD-OBSERVATIONS.md](./FIELD-OBSERVATIONS.md).
The two operate at different levels:

| | [FIELD-OBSERVATIONS.md](./FIELD-OBSERVATIONS.md) | `knowledge/observations/` |
|---|---|---|
| Records | A curated pattern, written by a technician, after reflection | Raw discovery/classification evidence for one device, from one run |
| Format | Prose, Markdown | Structured JSON |
| Granularity | One entry per observed *pattern* (a vendor/product's typical deployment) | One file per *device instance* |
| Populated by | A technician deciding a pattern is worth recording | A capture step, run against an unresolved (`UNKNOWN`) device |

A `knowledge/observations/*.json` file is expected to be the more granular,
mechanical layer underneath [FIELD-OBSERVATIONS.md](./FIELD-OBSERVATIONS.md):
once the same device/vendor pattern shows up across several such JSON
observations, that is exactly the kind of cross-environment corroboration
[KNOWLEDGE-LIFECYCLE.md](./KNOWLEDGE-LIFECYCLE.md) already asks for before
writing a `FIELD-OBSERVATIONS.md` entry. Recording a JSON observation does
not, by itself, advance anything past the Observation stage of that
lifecycle.

## Repository Structure

```text
knowledge/
    observations/
        observation-000001.json
        observation-000002.json
```

IDs are stable, sequential, and never derived from vendor, hostname, IP
address, or assumed device type — so a filename stays valid even if later
review changes what the device is understood to be. IDs are also never
reused, even if an earlier observation is later removed.

## Schema

Each file is one `Observation` (see
`networkmapper/knowledge/models.py`), serialized by
`networkmapper.knowledge.serializer.ObservationSerializer`. The schema is
versioned (`schema_version`) and mirrors NetworkMapper's canonical
`Device`/`ServiceEvidence` model field-for-field wherever those fields
exist, rather than inventing a parallel evidence representation — see
`docs/reports/KNOW-003-Field-Knowledge-Repository.md` for the full field
mapping and the reasoning behind it.

## Lifecycle

Every observation carries an explicit, human-controlled `status`:

```text
NEW → UNDER_REVIEW → VALIDATED → IMPLEMENTED → ARCHIVED
```

State transitions never happen automatically. An observation existing, or
being read, never influences runtime classification — see ADR-008
(Discovery is Immutable, Interpretation is Adjustable) and
`docs/reports/KNOW-003-Field-Knowledge-Repository.md`.

## Capture

`networkmapper.knowledge.capture` provides `should_capture()`,
`build_observation()`, and `capture_unresolved_device()` — callable,
side-effect-free (except for the explicit repository write) functions
that turn an `UNKNOWN` `Device` into a saved `Observation`. As of KNOW-003,
nothing in NetworkMapper calls these automatically; see
`docs/reports/KNOW-003-Field-Knowledge-Repository.md`'s Capture Policy
section for the architectural options considered for wiring this into a
real run, and why that wiring was left as an open decision rather than
implemented in this sprint.
