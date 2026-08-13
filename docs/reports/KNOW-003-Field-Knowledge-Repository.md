# Status

Investigation Complete

Implementation: Completed

Production Code Modified: No — new package only (`networkmapper/knowledge/`).
No existing production module (`DeviceClassifier`, `DiscoveryEngine`,
`Application`, any provider) was changed.

ADR Required: No — this sprint establishes a new, additive storage
subsystem with no consumers wired into the runtime yet. It does not
change any existing architectural decision. If a future sprint wires
automatic capture into the runtime (see Capture Policy, below), that
decision — not this one — is the one that should get an ADR, since it's
the point where this repository starts affecting what happens during a
real run.

Recommended Next Sprint:
A short, explicitly-scoped follow-up to decide *where* automatic capture
hooks into the runtime (see Capture Policy). Until that decision is made,
`capture_unresolved_device()` exists but nothing calls it outside tests.

---

## Summary

KNOW-003 adds a structured, version-controlled repository for preserving
field evidence about devices NetworkMapper's classifier could not
resolve: one compact JSON document per device under
`knowledge/observations/`, plus the code to build, validate, store, and
retrieve those documents.

The repository is deliberately inert. Nothing reads it back into
`DeviceClassifier`, nothing promotes an observation automatically, and as
of this sprint nothing in the application calls the capture function
automatically either — see Capture Policy for why that last piece was
left as an open decision rather than forced into this sprint's scope.

This sprint builds:

- A versioned, dataclass-based `Observation` model
  (`networkmapper/knowledge/models.py`) mirroring
  `Device`/`ServiceEvidence` field-for-field wherever those fields exist.
- `ObservationSerializer` (`networkmapper/knowledge/serializer.py`) —
  explicit JSON dict mapping, following the same pattern as
  `ProjectSerializer`, with schema validation (missing required fields
  and invalid lifecycle states both raise `ObservationSchemaError`).
- `ObservationRepository` (`networkmapper/knowledge/repository.py`) —
  one-file-per-observation storage with stable, sequential, never-reused
  IDs and filenames that encode nothing about the device itself.
- `should_capture()` / `build_observation()` / `capture_unresolved_device()`
  (`networkmapper/knowledge/capture.py`) — pure, callable functions that
  turn an `UNKNOWN` `Device` into a saved `Observation`, evaluated
  against a non-mutated copy per ADR-005.
- One realistic, committed sample observation
  (`knowledge/observations/observation-000001.json`) that stays `UNKNOWN`.
- 33 new regression tests across three test files, all passing, plus a
  clean `python -m devtools validate --all` run (339 tests, 100% accuracy
  on all three benchmark datasets — unchanged from before this sprint,
  confirming runtime classification was not touched).
- `docs/knowledge/OBSERVATION-REPOSITORY.md`, and a link to it from
  `docs/knowledge/README.md`, per this project's own documentation
  checklist ("Knowledge changes update: docs/knowledge/").

## Files Changed

New:
- `networkmapper/knowledge/__init__.py`
- `networkmapper/knowledge/models.py`
- `networkmapper/knowledge/serializer.py`
- `networkmapper/knowledge/repository.py`
- `networkmapper/knowledge/capture.py`
- `knowledge/observations/observation-000001.json`
- `tests/test_observation_serializer.py`
- `tests/test_observation_repository.py`
- `tests/test_observation_capture.py`
- `docs/knowledge/OBSERVATION-REPOSITORY.md`

Modified:
- `docs/knowledge/README.md` — added `OBSERVATION-REPOSITORY.md` to
  Related Documents.

Nothing under `networkmapper/classification/`, `networkmapper/discovery/`,
`networkmapper/core/`, or `networkmapper/application.py` changed.

---

## Repository Structure

```text
knowledge/
    observations/
        observation-000001.json
```

- `knowledge/` sits at the repository root, alongside `benchmarks/` and
  `output/` — a data directory, distinct from `docs/knowledge/`, which is
  documentation *about* the Knowledge Framework. This mirrors the
  existing `docs/architecture/` (docs) vs. implementation split already
  used elsewhere in the project.
- Filenames are `observation-{id:06d}.json` — stable, sequential,
  6-digit, matching the ticket's example exactly. `ObservationRepository`
  computes the next ID as one greater than the highest ID present on
  disk (including `ARCHIVED` observations, which are never deleted), so
  IDs are never reused even after a file is removed — verified by
  `test_next_observation_id_never_reuses_a_gap`.
- No vendor, hostname, IP, or device type is ever encoded in a filename —
  verified by `test_filename_does_not_encode_vendor_hostname_ip_or_device_type`.

---

## Observation Schema

Defined as a versioned, "equivalent validated model" (the ticket's own
alternative to a JSON Schema document) — plain Python dataclasses plus
`ObservationSerializer`'s explicit dict mapping, which is exactly the
pattern `networkmapper/project/serializer.py` already uses for `Project`.
No JSON Schema document or `jsonschema` dependency was added:
`requirements.txt` currently has exactly one dependency (`python-nmap`),
and this project's own `docs/DEPENDENCIES.md` treats that as deliberate.
Adding a schema-validation library for one new document type would be a
new dependency to validate what dataclass field types and `StrEnum`
already validate for free.

```json
{
  "schema_version": 1,
  "observation_id": 1,
  "status": "NEW",
  "captured_at": "2026-07-18T09:42:11",

  "network": { "name": "..." },
  "scan": { "profile": "standard", "networkmapper_version": "0.4.0" },
  "device": { "ip": "...", "hostname": "...", "vendor": "...", "mac_address": "..." },

  "evidence": {
    "operating_system": null,
    "computer_name": null,
    "domain": null,
    "smb_signing": null,
    "discovery_sources": ["nmap"],
    "services": [
      { "port": 80, "protocol": "tcp", "service": "http", "product": null,
        "version": null, "http_title": "...", "tls_subject": null,
        "tls_issuer": null, "http_auth_realm": "..." }
    ]
  },

  "classification": { "type": "unknown", "reason": "No rule matched.", "matched_rule": null },

  "technician_notes": "",
  "review_history": []
}
```

Two deliberate deviations from the ticket's illustrative example, both
explained here per the ticket's "explain the need before making the
change" instruction:

1. **Enum values are persisted in their canonical lowercase form**
   (`"unknown"`, `"standard"`) rather than the uppercase display form the
   ticket's example shows (`"UNKNOWN"`, `"STANDARD"`). `DeviceType` and
   `ScanProfile` already have a canonical `.value` (lowercase) used for
   persistence — `ProjectSerializer` persists `device_type.value` the
   same way — and an uppercase display form (`.name`, or `.value.upper()`)
   used only for CLI/report output. This file is data, meant to be
   reloaded via `DeviceType(value)`/`ScanProfile(value)`, not display
   text, so it follows the persistence precedent rather than the display
   one. `ObservationStatus` (a new enum with no prior canonical form) uses
   uppercase values exactly as the ticket specifies, since the ticket
   itself is the only source of truth for that vocabulary.
2. **`classification.matched_rule` and `review_history[].reference` were
   added** beyond the ticket's minimal example. Both are already
   requested in prose: "Future `IMPLEMENTED` entries may reference the
   rule or sprint that incorporated the observation. Keep this structured
   rather than embedding lifecycle history in free-form notes"
   (`reference`); knowing *which* rule almost-or-actually matched is
   evidence already available for free through the same read-only
   `get_last_rule_results()` API `markdown_exporter.py` already uses
   (`matched_rule`) — not new evidence, just not discarding evidence that
   was already computed.

### Evidence Mapping

| Observation field | Canonical source |
|---|---|
| `device.ip` | `Device.ip_address` |
| `device.hostname` | `Device.hostname` |
| `device.vendor` | `Device.vendor` |
| `device.mac_address` | `Device.mac_address` |
| `evidence.operating_system` | `Device.operating_system` |
| `evidence.computer_name` | `Device.computer_name` |
| `evidence.domain` | `Device.domain` |
| `evidence.smb_signing` | `Device.smb_signing` |
| `evidence.discovery_sources` | `Device.discovery_sources` |
| `evidence.services[]` | `Device.services` (`ServiceEvidence`) — every field mirrored 1:1 |
| `scan.profile` / `scan.networkmapper_version` | `RunMetadata.scan_profile` / `RunMetadata.version` |
| `network.name` | `RunMetadata.customer_name` |
| `classification.type` / `.reason` / `.matched_rule` | `Device.device_type` / `RuleResult.reason` / evaluating rule's class name |

`ObservationDevice` deliberately holds only the four identity fields the
ticket's example shows; everything else Discovery observed lives under
`evidence`, so "what identifies this device" and "what we learned about
it" stay separated the same way `docs/ADR.md` (ADR-008) separates
discovery from interpretation generally.
`test_service_evidence_fields_mirror_canonical_service_evidence` asserts
`ObservationServiceEvidence`'s field set is exactly equal to
`ServiceEvidence`'s, so the two can't silently drift apart.

No raw Nmap XML, no provider-specific field names, and no fields that
don't already exist somewhere on `Device`/`ServiceEvidence`/`RuleResult`
were introduced.

---

## Lifecycle Design

```text
NEW → UNDER_REVIEW → VALIDATED → IMPLEMENTED → ARCHIVED
```

`ObservationStatus` is a `StrEnum`, so `ObservationSerializer.from_dict()`
rejects any other value automatically — deserializing a payload with
`"status": "APPROVED_FOREVER"` raises `ObservationSchemaError`
(`test_invalid_status_is_rejected`), and every one of the five defined
statuses round-trips correctly
(`test_every_defined_lifecycle_status_is_accepted`).

No code anywhere sets `status` to anything other than its default `NEW`
on capture. Nothing in this sprint reads `status` to make a decision —
`ObservationRepository` and `capture.py` treat it as opaque payload, the
same way `ProjectSerializer` treats `device_type` as opaque payload
rather than acting on it. Changing an observation's status is something
only a future human-facing review tool would do, and no such tool exists
yet — this sprint is storage and lifecycle *definition* only, per the
Objective.

Review history is a list of structured entries
(`ObservationReviewEntry`: `reviewed_at`, `action`, `notes`, `reference`)
rather than free-form text appended to `technician_notes`, so a future
tool can answer "when did this change status, and why" without parsing
prose.

---

## Evidence Mapping

See the Evidence Mapping table under Observation Schema, above.

---

## Sample Observation

`knowledge/observations/observation-000001.json` — an APC Network
Management Card (the network interface built into a rack-mount UPS)
found on an isolated UPS-closet switch. It has rich HTTP/TLS evidence
(an `http_title` and `http_auth_realm` on port 80, a self-signed
certificate on 443) and a real, OUI-correct APC MAC address prefix
(`00:C0:B7`), but no classification rule recognizes it —
`NetworkApplianceRule` currently only recognizes NETGEAR ReadyNAS
identifiers (RULE-003), and no rule targets APC network management
interfaces specifically. It correctly remains `"classification": {"type":
"unknown", "reason": "No rule matched."}` — no rule was invented to make
it resolvable, per the ticket's explicit instruction.

Its `status` is `VALIDATED` (not `NEW`), with one `review_history` entry
—`{"action": "VALIDATED", "notes": "Confirmed APC network management
interface."}` — using the ticket's own worked example verbatim, to
demonstrate the review-history structure and the fact that an
observation's lifecycle `status` (a human review of the *observation's
usefulness*) is independent of its `classification.type` (which stays
`unknown` regardless — validating the observation didn't validate a
classification, because none exists yet). This is intentional: it shows
the repository doing exactly what it's for — preserving a validated,
citable case for a possible future `APCNetworkManagementCardRule`,
without that rule existing yet.

`ShippedSampleObservationTest.test_sample_observation_loads_and_remains_unknown`
loads this exact file (not a synthetic copy) so a future schema change
that silently breaks the shipped example fails CI.

---

## Testing Performed

33 new tests across three files, all passing:

- `tests/test_observation_serializer.py` (18 tests) — round-trip
  preservation of a fully populated observation; JSON validity; multiple
  service entries preserved independently; multiple review-history
  entries preserved with `reference`; optional `technician_notes`
  defaults to `""`; optional `review_history` defaults to `[]`; `status`
  defaults to `NEW`; `schema_version` defaults to `1`; missing required
  fields (`classification`, `network`) raise `ObservationSchemaError`;
  invalid `status` and invalid `review_history[].action` are rejected;
  every defined lifecycle status is accepted; `ObservationServiceEvidence`
  field set is asserted equal to `ServiceEvidence`'s (provider-independent
  evidence representation); no provider-specific field names appear in
  serialized output.
- `tests/test_observation_repository.py` (10 tests) — stable sequential
  IDs starting at 1; IDs increment after a save; IDs are never reused
  after a gap; save/load round-trips an `Observation`; filenames encode
  nothing about the device; filenames are the stable 6-digit form;
  loading a missing observation raises `ObservationNotFoundError`; an
  empty/nonexistent repository directory reports no observations; the
  shipped sample observation loads and remains `UNKNOWN`.
- `tests/test_observation_capture.py` (10 tests) — `should_capture()`
  returns `True` only for `UNKNOWN` devices; `build_observation()` maps
  identity/evidence/scan/network fields correctly from a canonical
  `Device`+`RunMetadata`; an `UNKNOWN` device gets `"No rule matched."`
  with `matched_rule=None`; a device a real rule matches
  (`NetworkApplianceRule`, reusing the exact fixture from
  `tests/test_network_appliance_rule.py`) gets the real matched rule name
  and reason, not a hardcoded default; the original `Device` is never
  mutated (ADR-005); `capture_unresolved_device()` persists an `UNKNOWN`
  device and returns `None` without writing anything for a classified
  one; successive captures get sequential IDs.

Full suite: `python -m devtools validate --all` — 339 tests run, 0
failures, 0 errors; Enterprise/Homelab/Small Office benchmarks all at
100.0% accuracy, unchanged from this sprint's starting state. This
confirms the Objective's "do not modify runtime classification"
constraint held — nothing about `DeviceClassifier`'s behavior or any
existing benchmark's accuracy moved.

---

## Risk Assessment

**Low risk, additive only.** No existing file under `networkmapper/`
(other than the new `networkmapper/knowledge/` package) or
`networkmapper/application.py` was modified. `discover_benchmark_datasets`
scans `benchmarks/` specifically and does not see `knowledge/`, so this
addition can't be mistaken for a benchmark dataset by existing tooling.

**Deliberately incomplete: no wiring into a real run (Capture Policy).**
The Objective states "This sprint establishes the storage format and
lifecycle only," and separately: "If automatic capture would require
meaningful runtime behavior changes, stop and report the architectural
options rather than expanding scope." Wiring `capture_unresolved_device()`
into an actual run means writing to disk as a side effect of running
NetworkMapper, with no existing way to announce it or disable it — that
is a real, user-visible runtime behavior change, not a storage-format
detail, so per the ticket's own instruction this was intentionally left
undone rather than forced in. Three integration points were considered:

1. **`Application.run()`**, after the existing device loop, calling
   `capture_unresolved_device()` for each `UNKNOWN` device. Smallest
   diff, but `Application.run()`'s own docstring calls it "the temporary
   persistence validation harness" — wiring a real feature into
   explicitly-temporary scaffolding risks the wiring getting silently
   dropped whenever that harness is eventually replaced, and there's
   currently no CLI flag to opt in/out or to name the network (it's
   hardcoded to `"Test Network"` today).
2. **`DiscoveryEngine`**, immediately after it classifies each device.
   Rejected without much consideration: this would put a knowledge-layer
   concern (which is explicitly supposed to stay decoupled from
   classification per this sprint's "do not modify runtime
   classification") directly inside the classification/discovery path
   itself, rather than downstream of it.
3. **A new `devtools` command** (e.g. `python -m devtools capture
   <project-file>`) that loads an already-saved `Project`
   (`ProjectSerializer.load`) and captures every `UNKNOWN` device in it.
   Explicit, opt-in, and consistent with `ENGINEERING.md`'s Developer
   Platform principle ("Developer automation should reuse existing
   project services... avoid duplicating production logic") — it
   wouldn't touch the runtime path at all, working entirely from data
   the runtime already produces.

Recommendation for the follow-up sprint: option 3. It gets real
observations flowing into the repository without touching
`Application.run()` or `DiscoveryEngine`, and it's the only option that
doesn't require answering "should every run silently write files to
disk?" before it can ship.

**Terminology overlap: "observation."** `docs/knowledge/FIELD-OBSERVATIONS.md`
already uses "Field Observation #NNN" for its curated, prose-format
entries. This sprint's `Observation` JSON records are a different,
lower-level thing (raw per-device evidence vs. curated cross-environment
pattern) but share the same word. `docs/knowledge/OBSERVATION-REPOSITORY.md`
added by this sprint explains the relationship directly rather than
silently letting two same-named-but-different concepts coexist
unexplained.

---

## Future Opportunities

(Explicitly out of this sprint's scope, per its own "Out of Scope"
section — listed here only as forward pointers, not as recommendations
to act on now.)

- Automatic capture wiring (see Risk Assessment, above) — the clearest,
  most load-bearing next step; without it, the repository has no source
  of real observations other than manual/test-authored ones.
- A human review CLI/workflow for walking `NEW` observations to
  `UNDER_REVIEW`/`VALIDATED`/`ARCHIVED` and writing `review_history`
  entries — today, changing an observation's status means hand-editing
  JSON or writing a script against `ObservationRepository` directly.
- A path from a `VALIDATED` observation (or a cluster of them) into a
  `docs/knowledge/FIELD-OBSERVATIONS.md` entry, formalizing the
  relationship this sprint's documentation describes.
- A path from `VALIDATED` observations into new benchmark fixtures
  (`benchmarks/*/inventory.json`), which is the step
  `docs/knowledge/KNOWLEDGE-LIFECYCLE.md` already defines as required
  before an observation may justify a classification change.
