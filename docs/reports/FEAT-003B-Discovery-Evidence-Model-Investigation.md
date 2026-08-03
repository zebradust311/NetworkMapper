# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: Yes — the investigation surfaced a genuine, previously
unrecognized structural limit in how `Device` represents per-service
evidence (parallel, positionally-uncorrelated lists), which every richer
evidence type identified in FEAT-003A (service version/product, HTTP
title, TLS certificate metadata) needs to attach to a specific port. This
is exactly the kind of "genuine product-architecture decision that wasn't
anticipated by the sprint" described in
[docs/process/stop-conditions.md](../process/stop-conditions.md), and it
extends the future work ADR-008 explicitly deferred ("a persisted schema
that structurally separates discovery fields from interpretation fields ...
requires its own approved sprint"). See ADR Considerations below for the
proposed scope — narrower than ADR-008's full deferred schema work.

Recommended Next Sprint:
FEAT-003C – Service Version & Metadata Enrichment, preceded by an
Architecture Review stage (per
[docs/process/sprint-lifecycle.md](../process/sprint-lifecycle.md)) that
resolves the ADR identified below before implementation begins.

---

# Executive Summary

This investigation set out to answer where richer discovery evidence
(service product/version, HTTP metadata, TLS certificate data — identified
as the recommended next capability in FEAT-003A) should live on the
`Device` model. It found three things that change the shape of that
answer:

1. **`open_ports` and `detected_services` are already two independent,
   positionally-uncorrelated lists**, each built by its own separate loop
   in `NmapProvider` and independently sorted (`open_ports` numerically,
   `detected_services` alphabetically). No code anywhere in the repository
   ties a specific port to a specific service name today (confirmed by
   repository-wide search). This has never caused a bug because every
   existing classification rule only asks "is port P open?" or "is service
   S present?" as independent yes/no signals — never "what service is
   running on port P?" Any evidence richer than a name (version, product,
   TLS subject, HTTP title) is meaningless without that correlation, which
   the current two-list shape cannot express. This is the central finding
   of this investigation and the reason a modeling decision, not just a
   field addition, is needed before FEAT-003C.
2. **`open_ports` and `detected_services` are not persisted at all.**
   `ProjectSerializer.save()`
   ([serializer.py:18-34](../../networkmapper/project/serializer.py#L18-L34))
   writes only `ip_address`, `hostname`, `mac_address`, `vendor`,
   `operating_system`, `device_type`, and `discovery_sources` — the two
   fields STANDARD-profile enrichment already populates today vanish the
   moment a project is saved and reloaded. No test in the repository
   exercises a real save/load round trip for these fields (only mocked
   `ProjectSerializer` calls exist in `test_application_cli.py`). Any new,
   richer evidence added without addressing this would inherit the same
   gap immediately.
3. **`operating_system` — the concrete precedent for "evidence added and
   never used" — was added in the very first commit that created the
   `Device` model** (`cb0d415`, "Implement core network graph," before any
   discovery provider or classification rule existed), not accumulated as
   later technical debt. It was speculative from day one: added ahead of
   both a producer and a consumer, and has sat idle for the entire project
   history since. The lesson is procedural, not just technical: a field
   should not be added to `Device` without an identified producer
   (discovery code that will set it) and consumer (a classification rule
   that will read it) in the same or an immediately adjacent sprint.

The recommendation is a narrow ADR — not the full discovery/interpretation
schema split ADR-008 already deferred — establishing that **discovery
evidence for a network service is represented per-port/per-service, not as
independent parallel lists**, before FEAT-003C adds the first evidence type
that actually needs that correlation.

---

# Investigation

## How `Device` Represents Evidence Today

`Device` ([core/models.py](../../networkmapper/core/models.py)) is a flat
dataclass. Every discovery fact added since the model's creation has been
added the same way — a new optional flat field or a new flat list:

| Field | Shape | Added in |
|---|---|---|
| `ip_address`, `hostname`, `mac_address`, `vendor`, `operating_system` | scalar `Optional[str]` | `cb0d415` (initial model) |
| `device_type`, `discovery_sources` | scalar / flat list | `cb0d415` (initial model) |
| `open_ports` | `list[int]` | `2b552cf` (scan-profile refactor) |
| `detected_services` | `list[str]` | `2b552cf` (scan-profile refactor) |

This pattern has worked because, so far, every field has been either a
single device-level fact (hostname, vendor, MAC) or a simple presence list
consumed only for membership testing. `evidence_helpers.py`'s
`first_matching_port()` and `first_matching_service()`
([evidence_helpers.py:22-48](../../networkmapper/classification/evidence_helpers.py#L22-L48))
confirm this: both search their respective list independently and return a
single matched value; neither takes the other list as an argument. Every
classification rule that was read for FEAT-003A calls these two helpers
independently, never together in a way that would require them to be
correlated (e.g. `SonicWallFirewallRule` checks "is 443 or 8443 open?" and
separately "is `https` or `ssl/http` present?" — never "is 443 specifically
running `https`?").

## Why This Breaks for the Evidence FEAT-003A Recommended

FEAT-003A's recommended sprint (FEAT-003C) is to capture, per open port:
the Nmap-reported product/version string, and for a subset of ports, an
NSE script result (`http-title` for 80/8080, `ssl-cert` subject/issuer for
443/8443, `smb-os-discovery` for 445). All of this evidence is inherently
**per-port**. A device with both port 80 (`http-title: "pfSense - Login"`)
and port 443 (`ssl-cert CN: "SonicWALL"`) open cannot correctly express
"which title/cert belongs to which port" as two more parallel lists next
to `open_ports` — the ambiguity is exactly the same shape as the
pre-existing, currently-harmless ambiguity between `open_ports` and
`detected_services` described above, except no longer harmless: a rule
reading "TLS subject contains SonicWALL" needs to know it came from port
443, not port 8443, to reason about it correctly, and a future technician
inspecting the Classification Workbench needs the same association to
trust the evidence at all.

## Persistence Gap

`ProjectSerializer.save()` and `.load()`
([serializer.py](../../networkmapper/project/serializer.py)) round-trip
`operating_system` but not `open_ports` or `detected_services`. This is
verifiable directly from the field list in the `payload["devices"]` dict
comprehension at `save()` — there is no line writing either field. Because
classification runs once, immediately after discovery, inside
`DiscoveryEngine.discover()`
([discovery_engine.py:19-30](../../networkmapper/discovery/discovery_engine.py#L19-L30)),
and the *result* of classification (`device_type`) is what downstream
consumers actually need long-term, this gap has not surfaced as a visible
defect — a saved-and-reloaded project still shows correct device types.
But it means:

- The raw evidence a rule's `reason` string refers to (e.g. "Detected
  `https` service indicates printer networking") is not recoverable after
  a save/load cycle for re-inspection, re-classification with updated
  rules, or Classification Workbench review of a reloaded project.
- ADR-008's principle that discovery is an immutable, replayable record is
  not actually true for `open_ports`/`detected_services` in the persisted
  format today, even though the in-memory `Device` object carries them
  correctly immediately after a scan.

This was not previously documented and is a direct, evidence-based finding
of this investigation, not something FEAT-003A identified.

## The `operating_system` Precedent, in Full

Git history for `networkmapper/core/models.py` shows `operating_system`
was present in commit `cb0d415` ("Implement core network graph"), the
commit that created the `Device` dataclass itself — before `NmapProvider`
existed, before any `ClassificationRule` existed, before
`ScanProfile` existed. It was added speculatively, as an obviously-useful
field for a device model, not in response to any discovery capability or
classification need that existed at the time. Every later consumer that
now touches it — `ProjectSerializer`, `BenchmarkRunner.load_inventory()`,
`ClassificationWorkbench` — was built to pass it through generically
because it was already on the model, not because any of them needed OS
data specifically. No classification rule has ever read it, and FEAT-003A
confirmed no discovery provider has ever set it.

**The lesson for this investigation:** the failure mode is not "the field
existed and nobody got to it yet." It is "the field was added with no
identified producer or consumer at all, at the very foundation of the
model, and every later piece of infrastructure treated its mere presence
as sufficient reason to plumb it through." Avoiding a repeat is a sprint-
sequencing discipline, not a schema discipline: new evidence fields should
land in the same or an adjacent sprint as both the discovery code that
populates them and the classification rule that reads them.

---

# Findings — Answers to the Investigation Questions

## 1. Where should richer discovery evidence live?

On `Device`, consistent with every discovery fact added so far — this
investigation found no reason to introduce a separate object graph,
repository, or storage boundary. `Device` remains the single record of
what was observed, per ADR-008. What changes is the **shape** of the
service-evidence portion of that record (see Question 2), not its location.

## 2. Should `Device` gain additional fields, or should evidence be modeled differently?

Both, in a specific way: the *scalar* discovery facts already on `Device`
(hostname, vendor, MAC, OS) can continue to gain new scalar fields the same
way they always have — that pattern has no structural problem. But
**per-service evidence should stop being represented as additional
parallel lists.** `open_ports: list[int]` and `detected_services:
list[str]` should be treated as the last instance of that pattern, not the
template for FEAT-003C's version/product/title/cert data. The
architectural question this investigation surfaces for an ADR is narrowly:
*should per-service evidence (port, name, and now version/product/title/
cert) be represented as one correlated record per observed port, rather
than as independent flat lists keyed only by coincidental list position?*
This report does not prescribe the resulting field names or types — that
is implementation detail reserved for FEAT-003C's own investigation phase
— only that the current two-list shape cannot correctly carry the evidence
FEAT-003A recommended collecting.

## 3. How should classification consume richer evidence?

The existing rule contract already anticipates this without requiring
changes to `ClassificationRule` or `DeviceClassifier`. `RuleResult`
([rule_result.py](../../networkmapper/classification/rule_result.py)) is
the classifier's evidence-reporting unit (ADR-002), and
`docs/architecture/classification.md` already notes that a `matched_fields`
concept was considered and intentionally not implemented — "the current
implementation does not expose `matched_fields`... because this document
describes implemented behavior only." Richer per-service evidence
naturally extends `evidence_helpers.py`'s existing pattern (add a
correlated-lookup helper analogous to `first_matching_port`/
`first_matching_service`, once the underlying `Device` representation
supports the correlation) and strengthens `reason` text — it does not
require a new consumption mechanism, a new rule interface, or a change to
first-match-wins ordering (ADR-003). This is a downstream implementation
decision for FEAT-003C, not this investigation.

## 4. How can new evidence avoid repeating the dormant `operating_system` pattern?

Sequence the work so a field is never added without both ends landing
together: no new `Device` evidence field should be introduced in a sprint
that does not also either (a) wire a discovery provider to populate it, or
(b) wire at least one classification rule to read it — ideally both in the
same sprint, as FEAT-003A's own recommendation already does (the
product/version/title/cert evidence is proposed specifically because
existing rules like `SonicWallFirewallRule`, `HypervisorHostnameRule`, and
`CiscoSwitchRule` can immediately use it to corroborate matches they
already attempt with weaker hostname/port-only evidence). `operating_system`
itself remains an open item: it has a model slot and full plumbing but no
producer or consumer. This investigation does not recommend addressing it
now — doing so is exactly the kind of scope expansion ("OS fingerprinting")
FEAT-003A already identified as a separate, higher-cost option with its own
open dependencies — but it should not be extended further (e.g. exposed in
new tooling) without a plan to populate and consume it.

## 5. Should exporters expose richer discovery evidence, or remain focused on classification results?

Out of scope for this investigation to decide, and this report does not
recommend a direction. FEAT-003A already established that neither exporter
(`CsvExporter`, `MarkdownExporter`) surfaces `open_ports`, `detected_services`,
or `operating_system` today — both are classification-result-focused. That
is a separate, later product decision (what a customer-facing document
should show) distinct from the discovery-evidence-model question this
investigation was scoped to answer. Raising it here only to note that
answering Question 2 does not implicitly answer Question 5 — a richer,
correlated per-service evidence structure does not obligate exporters to
change; that remains a distinct future sprint if pursued.

---

# ADR Considerations

**Proposed boundary for the ADR** (not drafted here — this is investigation
only, and drafting the ADR is Architecture Review work per
`docs/process/sprint-lifecycle.md`):

- **Decision to record:** Per-service discovery evidence (port, service
  name, and any richer attributes such as version, product, or protocol-
  specific metadata) is represented as a correlated record per observed
  port, not as independent parallel lists on `Device`.
- **Why it rises to ADR level rather than routine model evolution:** every
  future discovery capability identified in FEAT-003A that is more granular
  than "device-level fact" — service version/product (this sprint), SNMP
  per-interface data, LLDP/CDP per-neighbor data — depends on the same
  correlation problem this investigation found. Deciding it once, now,
  avoids each future sprint re-deriving (or inconsistently re-solving) the
  same structural question, and ADR-008 already named this category of
  decision ("a persisted schema that structurally separates discovery
  fields... requires its own approved sprint") as deliberately deferred
  rather than absent-mindedly skipped.
- **What this ADR is explicitly not:** it is not the full discovery/
  interpretation schema separation ADR-008 deferred (that remains
  future work, unaffected by this recommendation), and it does not mandate
  a specific implementation (field names, whether `open_ports`/
  `detected_services` are removed, replaced, or kept as derived
  convenience views). Those are FEAT-003C implementation decisions once
  the ADR settles the modeling principle.
- **Consequence for FEAT-003C:** per the sprint lifecycle, FEAT-003C should
  begin with an Architecture Review stage that resolves this ADR before
  implementation, rather than a plain investigation-to-implementation
  transition.

This investigation does not modify `docs/ADR.md`. It documents that a
decision is needed and describes its boundary, consistent with this
sprint's constraint against drafting or updating ADRs directly.

---

# Risks

- **Under-scoping the ADR** into the full ADR-008 schema-separation work
  would violate this sprint's own scope constraint and stall FEAT-003C
  indefinitely. The recommendation above is deliberately narrower.
- **Over-scoping the ADR** into a generic "redesign Device" exercise would
  repeat the `operating_system` mistake at architecture-decision scale:
  designing structure ahead of a concrete need. The proposed boundary is
  anchored specifically to the per-service evidence FEAT-003A already
  identified as the next sprint's content.
- **The persistence gap** (open_ports/detected_services not saved) is a
  pre-existing defect, not something this investigation or FEAT-003C
  introduces. It is noted here because it is directly relevant to "where
  evidence lives," but fixing it is a separate concern from the ADR's
  in-memory representation question and should not be silently folded into
  FEAT-003C's scope without being named as its own decision.

---

# Assumptions

- FEAT-003A's recommended evidence set (product/version strings already
  returned by `-sV`, plus `http-title`, `ssl-cert`, and `smb-os-discovery`
  NSE output) is taken as given; this investigation did not re-evaluate
  that choice.
- No live Nmap scan was executed during this investigation; all findings
  are based on static reading of `nmap_provider.py`, its tests, the
  `Device` model, the classification rules, the serializer, the benchmark
  runner, and git history — consistent with FEAT-003A's own evidence
  standard.

---

# Conclusion

The `Device` model does not need a fundamental rebuild to support richer
discovery evidence, and this investigation is not recommending one. But it
does need one specific, scoped architectural decision before FEAT-003C: how
per-service evidence is correlated to the port it came from — a question
the current `open_ports`/`detected_services` shape cannot answer and that
every version/product/title/certificate field FEAT-003A recommended would
otherwise inherit. That decision belongs in a narrow ADR at the start of
FEAT-003C's Architecture Review stage, not in this investigation and not
smuggled in as an implementation detail once coding starts. Separately,
this investigation surfaced a real, previously undocumented persistence
gap (`open_ports`/`detected_services` are not saved by `ProjectSerializer`)
that FEAT-003C's implementers should be aware of even though fixing it is
not part of this recommendation, and reconfirmed — with a fuller history
than FEAT-003A had — that `operating_system`'s dormancy traces to a
sequencing failure at the very founding of the model, which is the
concrete pattern future evidence work should not repeat.
