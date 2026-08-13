# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — this sprint adds no new rule, no new evidence field,
and no new `ClassificationRule`/`RuleResult` shape. It extends one
existing, already-shared evidence helper (`first_matching_identifier`)
with one optional parameter and wires five existing rules to pass their
already-established keyword lists against `Device.snmp_sys_descr`. Same
shape of change as RULE-002/RULE-003 (neither required an ADR).

Recommended Next Sprint: No single sprint is pre-selected. Section 8
names two concrete candidates gated on future evidence: an evidence-
gated `sysObjectID` interpretation rule (explicitly deferred by
ARCH-012's own Implementation Sequence item 2, and still ungrounded —
see Section 8), and a UPS/PDU classification capability if a future
benchmark or field observation corroborates one (today `DeviceType` has
no UPS category and no observation exists to justify adding one).

Wait for architecture review before committing, per sprint instructions.

---

## Summary

FEAT-005 collected six SNMP system-group fields into `Device`
(`snmp_sys_descr`, `snmp_sys_object_id`, `snmp_sys_uptime`,
`snmp_sys_contact`, `snmp_sys_location`, and `sysName` folded into
`hostname`) but no classification rule ever read any of them. RULE-004
closes that gap for the one field with a proven classification role:
`snmp_sys_descr`.

`snmp_sys_descr` is a device's own free-text self-description over SNMP
(ARCH-012's own examples: `"Cisco IOS Software, C2960 Software..."`,
`"HP LaserJet 4250, Firmware Version: 08.061.3"`) — the same shape of
evidence as an Nmap product string or an HTTP page title, just reported
by a different protocol. `first_matching_identifier`, the shared helper
every identifier-tier classification rule already uses to check product
string / HTTP title / TLS certificate subject / TLS certificate issuer /
HTTP authentication realm against a rule's own vetted keyword list, now
optionally also checks `snmp_sys_descr` against that same list, checked
last (after every Nmap-derived field), so a stronger service-derived
match is always preferred for the reported reason label — the
evidence-hierarchy principle this sprint's brief calls "corroborates,
does not override" made concrete.

Five existing rules were wired to pass `snmp_sys_descr=device.
snmp_sys_descr`, using their own already-evidence-backed keyword lists
(no new keyword was invented): `SwitchVendorRule` (`procurve`,
`edgeswitch`), `PrinterVendorRule` (the fifteen-vendor printer keyword
list), `SonicWallFirewallRule` (`sonicwall`), `NetworkApplianceRule`
(`readynas`), and `HypervisorHostnameRule` (`vmware`, corroboration-only
— see Section 4). No new `ClassificationRule` was added; no `DeviceType`
was added; no keyword list was widened beyond what each rule already
trusted from other evidence types.

`snmp_sys_object_id`, `snmp_sys_uptime`, `snmp_sys_contact`, and
`snmp_sys_location` are deliberately **not** consumed this sprint — see
Section 4 for why each was left alone, and Section 8 for what would
change that.

---

## Files Changed

Production code:

- `networkmapper/classification/evidence_helpers.py` —
  `first_matching_identifier` gained one new optional keyword-only
  parameter, `snmp_sys_descr: str | None = None`, checked last in the
  existing five-field priority chain under a new `"SNMP sysDescr"`
  label. Default `None` means every pre-existing call site (there were
  none passing this argument before this sprint) is behaviorally
  unchanged unless a caller opts in.
- `networkmapper/classification/rules/switch_vendor_rule.py` — the
  identifier-tier call now passes `snmp_sys_descr=device.
  snmp_sys_descr`, checked against the existing `SWITCH_IDENTIFIER_
  KEYWORDS = {"procurve", "edgeswitch"}`. A code comment explains why a
  bare `"cisco"` keyword was deliberately **not** added here despite
  ARCH-012's Cisco IOS example — see Section 6 (Risk Assessment).
- `networkmapper/classification/rules/printer_vendor_rule.py` —
  `_find_printer_vendor_identifier` now passes `snmp_sys_descr=device.
  snmp_sys_descr`, checked against the existing `SUPPORTED_PRINTER_
  VENDOR_KEYWORDS` (all fifteen vendor names, unchanged).
- `networkmapper/classification/rules/sonicwall_firewall_rule.py` — the
  identifier-tier call now passes `snmp_sys_descr=device.
  snmp_sys_descr`, checked against the existing `FIREWALL_IDENTIFIER_
  KEYWORDS = {"sonicwall"}`.
- `networkmapper/classification/rules/network_appliance_rule.py` — the
  identifier-tier call now passes `snmp_sys_descr=device.
  snmp_sys_descr`, checked against the existing `NETWORK_APPLIANCE_
  IDENTIFIER_KEYWORDS = {"readynas"}`.
- `networkmapper/classification/rules/hypervisor_hostname_rule.py` — the
  corroboration-only product-identifier call now passes `snmp_sys_descr=
  device.snmp_sys_descr`, checked against the existing `HYPERVISOR_
  PRODUCT_KEYWORDS = {"vmware"}`. Unlike the four rules above, this
  check remains strictly corroboration text — `HYPERVISOR_HOSTNAME_
  KEYWORDS` is still the sole match gate, unchanged by this sprint.

No change to `Device`, `ServiceEvidence`, `DeviceType`, `DiscoveryProvider`,
`EnrichmentProvider`, `SnmpEnrichmentProvider`, `ScanProfile`,
`DeviceClassifier`'s rule ordering, or any exporter/reporting code — all
explicitly out of scope per this sprint's brief, and confirmed untouched
by the diff.

Tests:

- `tests/test_classifier.py` — five new `EvidenceHelpersTest` cases
  directly exercising `first_matching_identifier`'s new parameter
  (fallback when no service evidence matches, precedence when both
  service evidence and `snmp_sys_descr` match, and the unchanged-default
  case), plus two new full-pipeline `DeviceClassifierTest` cases: a
  vendor/hostname/service-evidence-free device now resolves to `SWITCH`
  from `snmp_sys_descr` alone (previously `UNKNOWN`), and a device whose
  `snmp_sys_descr` matches no rule's keyword list correctly stays
  `UNKNOWN` (guards against over-reach).
- `tests/test_switch_vendor_rule.py` — three new cases: independent
  match via `snmp_sys_descr` alone, service evidence taking precedence
  over `snmp_sys_descr` when both are present, and an unrelated
  `snmp_sys_descr` (a generic Linux banner) not matching.
- `tests/test_printer_vendor_rule.py` — two new cases: the ARCH-012 "HP
  LaserJet 4250" example matching alone, and service evidence taking
  precedence when both are present.
- `tests/test_sonicwall_firewall_rule.py` — two new cases, same shape.
- `tests/test_network_appliance_rule.py` — two new cases, same shape.
- `tests/test_hypervisor_hostname_rule.py` — two new cases: `snmp_sys_
  descr` corroborating an already-hostname-matched device's reason text,
  and (the important negative case) a `"vmware"`-matching `snmp_sys_
  descr` on a device with **no** qualifying hostname correctly **not**
  triggering a match — proving this rule's SNMP consumption stayed
  corroboration-only rather than becoming a sixth independent trigger.
- `tests/test_devtools_validate.py` — hardcoded fast-validation count
  updated from 130 to 146 (16 new tests, all within modules already in
  `STANDARD_REGRESSION_TESTS`).

16 new tests total. No test file was added; every new case lives inside
an existing rule's test module, following RULE-003's own precedent that
a corroboration/identifier-tier extension doesn't need a dedicated test
file.

---

## Evidence Consumed

Only `Device.snmp_sys_descr`. The other three FEAT-005 fields with no
existing classification role remain unconsumed by design — see Section 4
below for the reasoning behind each, since the sprint brief specifically
asks that this not be silently skipped without justification.

`sysName` (folded into `Device.hostname` as a fallback by
`SnmpEnrichmentProvider` itself, per ARCH-012's Canonical Evidence
Mapping) required no new consumption this sprint: every hostname-reading
rule (`ServerHostnameRule`, `HypervisorHostnameRule`,
`DellWorkstationRule`, `UbiquitiAccessPointRule`, and the hostname
fallback paths in `SwitchVendorRule`/`SonicWallFirewallRule`) already
reads `device.hostname` unconditionally — it has no way to know whether
that value came from SMB/RDP or an SNMP `sysName` fallback, and doesn't
need to. This is FEAT-005's own design working as intended, not a gap
RULE-004 needed to close.

---

## Rule Changes

All five changes follow the same shape: a rule's existing identifier
keyword list — never a new one — is now also checked against
`snmp_sys_descr`, via `first_matching_identifier`'s new optional
parameter. No rule's match *logic* changed; only the set of evidence
fields feeding an already-existing check grew by one.

**Four rules treat `snmp_sys_descr` as an independent trigger tier**,
exactly as they already treat product string / HTTP title / TLS
subject / TLS issuer / HTTP authentication realm — `SwitchVendorRule`,
`PrinterVendorRule`, `SonicWallFirewallRule`, `NetworkApplianceRule`.
This is a deliberate, not incidental, choice: `first_matching_
identifier`'s five pre-existing fields already treat these keyword
lists as safe independent triggers, and `snmp_sys_descr` is evidentially
the same shape of data (a device's own free-text self-description) as
the fields already trusted at that tier. Extending the trust boundary to
a sixth field using the *same already-accepted keyword lists* is a
narrower, lower-risk change than adding a new keyword to any existing
field would have been.

**One rule, `HypervisorHostnameRule`, treats it as corroboration-only**,
matching how that rule already treats its own `HYPERVISOR_PRODUCT_
KEYWORDS` check — `snmp_sys_descr` can only enrich the reason text of a
match the hostname check already made; it can never independently
trigger `HYPERVISOR`. This wasn't an oversight of consistency — it's
this rule's own pre-existing, unchanged design, and RULE-004 extended it
using the same posture it already had.

**No rule gained a new independent trigger keyword.** `SwitchVendorRule`
deliberately did **not** gain a bare `"cisco"` `snmp_sys_descr` trigger
despite ARCH-012 citing `"Cisco IOS Software, C2960..."` as a realistic
example — see Section 6 for why that specific case was excluded even
though the sprint brief's own example seems to invite it.

**No new `DeviceType`, no new rule file, no rule reordering.** Every
change is additive at the parameter level inside existing rules; none
required reconsidering `DeviceClassifier`'s ordering docstring, since no
rule's precedence relationship to any other rule changed.

---

## Classification Improvements

None of the three benchmark datasets (`enterprise`, `homelab`,
`small_office`) carry SNMP evidence in their fixtures — their SNMP
service entries are `{"port": 161, "protocol": "tcp/udp", "service":
"snmp"}` port records only, not enriched `sysDescr`/`sysObjectID`
values, because no benchmark was ever run with `--snmp` against a real
or simulated agent. Consequently **all three benchmarks classify
identically before and after this sprint, at 100.0% accuracy** — this is
the expected, correct outcome (a pure interpretation-layer change with
no new evidence manufactured for fixtures that never had SNMP evidence
to begin with), not a gap.

The improvement this sprint delivers is demonstrated directly against a
synthetic device that has *only* SNMP evidence (`test_snmp_only_
procurve_sys_descr_classifies_as_switch_not_unknown` in
`tests/test_classifier.py`): a device with no vendor, no hostname, and
no Nmap service evidence — which would classify `UNKNOWN` under every
pre-RULE-004 rule — now correctly resolves to `SWITCH` from `snmp_sys_
descr` alone, using the exact same `"procurve"` keyword `SwitchVendorRule`
already trusted from an Nmap product string or HTTP title. The paired
negative test (`test_snmp_only_generic_sys_descr_remains_unknown`)
confirms a device whose `snmp_sys_descr` matches nothing in any rule's
keyword list correctly stays `UNKNOWN` — the improvement is bounded to
evidence that was already trusted, not a general new source of matches.

No real-world or benchmark dataset was available this sprint to quantify
the improvement against actual field SNMP responses (see Section 8) —
this is a stated, deliberate limitation, not an oversight.

---

## Regression Tests

`python -m unittest discover -s tests -p "test_*.py"`: **379 passed, 0
failed** (363 before this sprint + 16 new).

`devtools.validate.run_full_validation()`: **PASS** — 379/379 unit
tests, and all three benchmark datasets **unchanged at 100.0% accuracy**
(enterprise: 9/9, homelab: 5/5, small_office: 5/5) — none of their
fixture devices carry `snmp_sys_descr` evidence, so none were affected
and none regressed.

Every newly introduced heuristic has direct regression coverage:

- **Independent-trigger behavior** (`SwitchVendorRule`,
  `PrinterVendorRule`, `SonicWallFirewallRule`, `NetworkApplianceRule`):
  one positive test per rule (SNMP evidence alone triggers the existing
  match, with no vendor/hostname/service evidence present) plus one
  precedence test per rule (service evidence — a stronger, pre-existing
  source — is preferred over SNMP evidence for the reported reason label
  when both are present), directly exercising "SNMP evidence
  corroborates, it does not override."
- **Corroboration-only behavior** (`HypervisorHostnameRule`): one
  positive test (SNMP evidence enriches an already-hostname-triggered
  match's reason text) and one explicit negative test proving SNMP
  evidence alone, without the hostname gate, does **not** trigger a
  match — the test that most directly guards this sprint's "prefer
  corroboration over replacement" principle from silently eroding on a
  future edit.
- **Helper-level coverage** (`first_matching_identifier` directly, in
  `tests/test_classifier.py`'s `EvidenceHelpersTest`): the fallback
  case, the precedence case, and — importantly — a test asserting
  behavior is **identical to before this sprint** when `snmp_sys_descr`
  is not supplied, protecting every one of `first_matching_identifier`'s
  pre-existing callers from an unnoticed behavior change.
- **Full-pipeline coverage** (`tests/test_classifier.py`'s
  `DeviceClassifierTest`): one previously-`UNKNOWN`-shaped device now
  resolving via `DeviceClassifier` end-to-end, and one explicit negative
  case confirming an unrelated `snmp_sys_descr` does not manufacture a
  classification.
- **Graceful absence**: every existing test in every modified rule's
  test file that constructs a `Device` without `snmp_sys_descr` (the
  dataclass default, `None`) continues to pass unmodified — `None` was
  already the field's default before this sprint, and `first_containing`
  already skips `None`/empty values, so "SNMP evidence ignored
  gracefully when unavailable" required no new code, only verification
  that the existing default-`None` behavior still holds (confirmed by
  the full suite passing with zero fixture changes to any pre-existing
  test).

---

## Risk Assessment

**False-positive risk: low, by design, with one specific exclusion
called out.** Every keyword list reused against `snmp_sys_descr` is a
list a different evidence type (product string, HTTP title, TLS
subject/issuer, HTTP auth realm) already trusted as an independent
trigger — no new keyword was invented, and no existing list was
widened. The one case seriously considered and explicitly **not**
implemented: a bare `"cisco"` `snmp_sys_descr` trigger for
`SwitchVendorRule`, despite ARCH-012 citing a Cisco IOS `sysDescr`
example directly. Reasoning: `"cisco"` alone is not switch-specific text
— Cisco also makes phones, access points, and firewalls — and unlike
`SWITCH_IDENTIFIER_KEYWORDS`'s existing `"procurve"`/`"edgeswitch"`
(brand-*and*-product-line-specific, unambiguous), a bare vendor
substring risks exactly the cross-rule collision RULE-002 already
documented once for the vendor field. Concretely: `VoiceVendorRule`
does not consume `snmp_sys_descr` for its own phone identification, so
a Cisco IP Phone with an uninformative hostname and a `sysDescr`
containing `"Cisco IP Phone..."` could have been misclassified as
`SWITCH` before `VoiceVendorRule` (which runs earlier in
`DeviceClassifier`'s ordering, but only actually *catches* phones via
hostname/SIP-port signals, not via `sysDescr`) ever had a chance to
claim it correctly. This was identified during implementation, not
after a test failure, and resolved by simply not adding that keyword
rather than adding compensating logic elsewhere — the narrower, safer
choice.

**Regression risk to existing classifications: none observed.** Every
keyword list touched is exactly as narrow after this sprint as before
it; `first_matching_identifier`'s new parameter defaults to `None` and
is additive-only for callers that don't opt in. The full 379-test suite
and all three benchmark datasets confirm zero behavior change for every
device that carries no `snmp_sys_descr` evidence — which, given no
benchmark fixture has any, is every currently-benchmarked device.

**Coverage risk: real, and intentionally bounded.** This sprint resolves
`snmp_sys_descr` corroboration for exactly the five rules whose existing
keyword lists plausibly appear in a device's own SNMP self-description
(switch, printer, firewall, NAS, hypervisor). `VoiceVendorRule`,
`ServerHostnameRule`, `DellWorkstationRule`, and `UbiquitiAccessPointRule`
were each considered and deliberately excluded — see Section 8 for why
each specifically. This is a scope boundary, not an oversight.

**Validation risk: no field or synthetic SNMP dataset exists yet.**
Every test fixture's `snmp_sys_descr` value in this sprint is a literal
string taken directly from ARCH-012's own architecture document, not
from an actual SNMP response captured against a real or simulated
device. This is the same "synthetic/localhost data" caveat RULE-003's
report already flagged for its own HTTP evidence testing, now inherited
by SNMP evidence too — see Section 8.

---

## Future Knowledge Opportunities

Per the sprint brief's explicit instruction not to promote observations
into rules speculatively, the following are recorded as opportunities
only:

1. **`sysObjectID` interpretation remains genuinely unimplemented, not
   just deferred.** ARCH-012's own Implementation Sequence already named
   this as `RULE-00X (follow-on, evidence-gated)` — "a classification
   rule consuming `sysObjectID`/`sysDescr`, written only after FEAT-005
   has produced corroborated field observations." That precondition
   still hasn't been met: no `Observation` record in `docs/knowledge/
   FIELD-OBSERVATIONS.md` documents an actual `sysObjectID` value for
   any real device, and this sprint's brief itself repeats the
   instruction not to embed a vendor/enterprise OID database. RULE-004
   correctly leaves `sysObjectID` completely uninterpreted — it is
   collected and persisted, but no rule reads it, and no rule should
   until KNOW-003's Observation → Knowledge → Rule lifecycle produces at
   least one corroborated OID-to-vendor mapping to interpret narrowly,
   exactly as `NETWORK_APPLIANCE_IDENTIFIER_KEYWORDS` was grown from one
   BENCH-002 observation, not a lookup table.
2. **UPS/PDU identification was explicitly considered and excluded**,
   despite being named as an example category in this sprint's brief.
   `DeviceType` has no UPS/PDU category today, and — as important — no
   field or benchmark observation of a real UPS `sysDescr`/`sysObjectID`
   value exists anywhere in this repository to ground a keyword list
   against. Adding one now would be inventing a classification from the
   sprint brief's own example list rather than from observed evidence,
   which Section 3 of the sprint brief explicitly prohibits ("Do not
   invent classifications solely because SNMP exists"). If a future
   observation (real or a deliberately-constructed, clearly-labeled
   synthetic fixture, following BENCH-002's own precedent) produces a
   concrete UPS `sysDescr`/`sysObjectID` example, both a `DeviceType.UPS`
   addition and a corresponding rule become a well-grounded, low-risk
   follow-on sprint.
3. **No real or simulated SNMP dataset exists to validate this sprint's
   five keyword extensions against.** Every test in this sprint uses a
   `sysDescr` string taken from ARCH-012's own architecture document,
   not a captured or lab-verified device response. A future BENCH-00X-
   style sprint that runs `--snmp` against a real or containerized
   `net-snmp` agent (ARCH-012's own Testing Strategy names this as
   "acknowledged as valuable future integration-test infrastructure,
   but explicitly not added" in FEAT-005 either) would meaningfully
   strengthen confidence in the five extensions this sprint made,
   independent of whether it changes any of them.
4. **`snmp_sys_uptime`/`snmp_sys_contact`/`snmp_sys_location` remain
   correctly unconsumed.** Re-confirming ARCH-012's own conclusion
   without new information: these three fields are inventory/
   documentation value only (a measured uptime, administrator-entered
   free text), with no classification-relevant content observed or
   plausible. No future rule should read them for classification
   purposes without first identifying concrete evidence that changes
   this — this sprint found none, and did not go looking further than
   the fields themselves warrant.
5. **`VoiceVendorRule`, `ServerHostnameRule`, `DellWorkstationRule`, and
   `UbiquitiAccessPointRule` were each considered and left alone**, for
   different reasons worth recording so a future sprint doesn't re-derive
   them from scratch:
   - `VoiceVendorRule` — enterprise VoIP handsets are not commonly
     SNMP-managed appliances in the way switches/printers/firewalls are;
     no field or architecture-document evidence in this repository
     describes a phone's `sysDescr` shape, unlike ARCH-012's concrete
     switch/printer examples.
   - `ServerHostnameRule` — its existing OS-based corroboration
     (`SERVER_OPERATING_SYSTEM_KEYWORDS = {"server"}`) is deliberately
     sourced from `smb-os-discovery`'s *structured* OS caption field, not
     a free-text banner; a generic `"server"` substring match against
     `sysDescr`'s comparatively unstructured text carries materially
     higher ambiguity risk (many non-server device `sysDescr` strings
     could plausibly contain the word "server" incidentally, e.g. "print
     server", "DHCP server appliance"), and no concrete example
     justifies accepting that risk yet.
   - `DellWorkstationRule` — general-purpose workstations are not
     "infrastructure devices" in the sense this sprint's brief scopes
     SNMP corroboration around, and are rarely SNMP-managed in practice;
     no evidence suggests otherwise.
   - `UbiquitiAccessPointRule` — its existing keywords
     (`"nanohd"`/`"ac-pro"`/`"ac-lr"`/`"unifi-ap"`) are hostname-naming
     conventions, not the kind of text a device's own `sysDescr` banner
     would typically echo verbatim (UniFi's SNMP `sysDescr` is not
     standardized the way Cisco's/HP's/SonicWall's are, and no example
     exists in this repository to confirm what it would actually say).
