# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — this sprint adds one new classification rule using
the existing `ClassificationRule`/`RuleResult` contract and the
existing evidence model, in the existing first-match-wins classifier.
No discovery, scan profile, reporting, or evidence-collection code was
touched. It is the same shape of change as RULE-002 (which also added
no ADR).

Recommended Next Sprint:
No single sprint is pre-selected. This sprint's own Future Opportunities
(Section 7) name two candidates: a general-purpose "identifier-tier
keyword table" refactor if a third or fourth similarly narrow,
BENCH-002-style-justified appliance rule accumulates, and a possible
follow-up benchmark once real network telemetry (rather than this
sprint's synthetic/localhost data) is available to check whether other
NAS/appliance brands appear often enough in the field to justify
expanding `NETWORK_APPLIANCE_IDENTIFIER_KEYWORDS`.

---

## Summary

BENCH-002 found one concrete, reproducible case of evidence being
collected at real cost and then discarded: a synthetic Netgear ReadyNAS
device (`netgear-nas-01`) whose HTTP Authentication Realm evidence
("NETGEAR ReadyNAS", from the `http-auth` NSE script already run
against an already-scanned port) unambiguously identified it as
network-attached storage, but which stayed `UNKNOWN` across all three
scan profiles because no classification rule read HTTP auth realm
evidence for anything outside printer/firewall identification.

This sprint adds one new rule, `NetworkApplianceRule`, that recognizes
Netgear's `ReadyNAS` product-line identifier — via product string, HTTP
title, TLS certificate subject/issuer, or HTTP authentication realm,
using the same `first_matching_identifier` helper every other
identifier-tier rule already uses — and classifies matching devices as
`SERVER` (the closest existing `DeviceType` fit for a dedicated
storage/file appliance; no new device category was added).

The rule is deliberately narrow. BENCH-002 produced corroborated
evidence for exactly one appliance identity (Netgear ReadyNAS); this
sprint recognizes exactly that one, and no other. It does not add a
bare-vendor trigger for "Netgear" (Netgear also makes routers, switches,
and access points — vendor alone would be a false-positive risk), and
it does not attempt to resolve BENCH-002's other UNKNOWN devices
(`mystery-box-01`, `web-app-01`) because neither has evidence specific
enough to corroborate a classification without guessing — see Section 6
for why each was deliberately left alone.

---

## Files Changed

Production code:

- `networkmapper/classification/rules/network_appliance_rule.py` — new.
  `NetworkApplianceRule`: one identifier-tier check
  (`NETWORK_APPLIANCE_IDENTIFIER_KEYWORDS = {"readynas"}`) that
  independently triggers a `SERVER` match, with `NETWORK_APPLIANCE_
  VENDOR_KEYWORDS = {"netgear"}` and `NETWORK_APPLIANCE_HOSTNAME_HINTS
  = ("nas",)` used only to *enrich the reason text* when they're also
  present — never as independent or alternative triggers.
- `networkmapper/classification/rules/__init__.py` — import/`__all__`
  updated to include `NetworkApplianceRule`.
- `networkmapper/classification/device_classifier.py` — `NetworkApplianceRule`
  inserted immediately after `ServerHostnameRule` in the ordered rule
  list, with a docstring note explaining why (both suggest `SERVER`, so
  there's no precedence conflict to resolve between them, unlike
  RULE-002's Printer/Switch case).
- `devtools/validate.py` — `STANDARD_REGRESSION_TESTS` updated to
  include the new `tests.test_network_appliance_rule` module, following
  the existing convention that every rule gets its own entry in the
  fast-validation subset.

Tests:

- `tests/test_network_appliance_rule.py` — new. 10 tests: the exact
  BENCH-002 evidence shape (HTTP auth realm alone), HTTP title alone,
  product string alone, case-insensitivity, vendor corroboration text,
  hostname corroboration text, the full three-signal BENCH-002 shape,
  and three explicit negative tests — bare Netgear vendor without an
  identifier, bare "nas" hostname without an identifier, and an
  unrelated NAS brand ("Synology") not in the keyword list — all
  confirming the rule does not over-reach.
- `tests/test_classifier.py` — three new full-pipeline tests: the exact
  BENCH-002 `netgear-nas-01` device now resolves to `SERVER` (was
  `UNKNOWN`); a bare-vendor Netgear router without NAS evidence stays
  `UNKNOWN` (guards against the false-positive risk this design
  deliberately avoids); BENCH-002's `web-app-01` device (generic HTTP
  title, no vendor) stays `UNKNOWN` (guards against scope creep into
  resolving evidence that isn't actually specific enough).
- `tests/test_classification_workbench.py` — one assertion added
  (`Rule: NetworkApplianceRule` is now evaluated, and shown, ahead of
  `PrinterVendorRule`'s match for the existing Brother-vendor test
  case) — an ordering-list update only, not a behavior change.
- `tests/test_devtools_validate.py` — hardcoded fast-validation count
  updated from 117 to 130 (13 new tests: 10 in the new rule test file,
  3 in `test_classifier.py`).

---

## Evidence Consumed

Both evidence types named in this sprint's Background were already
being collected by STANDARD/DEEP; neither required any new collection
logic. What changed is that both are now checked by `first_matching_
identifier` for the `NetworkApplianceRule` tier, exactly the same
mechanism `PrinterVendorRule`/`SonicWallFirewallRule`/`SwitchVendorRule`
already use for their own identifier tiers:

- **HTTP Authentication Realm** — `ServiceEvidence.http_auth_realm`,
  populated by the `http-auth` NSE script (FEAT-003G). This is the
  evidence field that actually carries `"NETGEAR ReadyNAS"` in the
  BENCH-002 fixture.
- **HTTP Title** — `ServiceEvidence.http_title`, populated by the
  `http-title` NSE script (FEAT-003F). Not present in BENCH-002's
  concrete NAS example, but included because a NAS device's web
  management UI plausibly carries the same `"ReadyNAS"` identity in its
  page title as well as its auth challenge — the same reasoning
  `PrinterVendorRule`'s identifier tier already applies across multiple
  evidence types for the same brand identity.
- **Product string, TLS certificate subject/issuer** — included only
  because `first_matching_identifier` checks all five fields uniformly;
  no BENCH-002 evidence specifically demonstrated a NAS device
  presenting its identity through these, but there's no reason to
  special-case them out, and doing so would mean re-implementing a
  narrower version of a helper that already exists and is already
  tested.

No new evidence field was added to `ServiceEvidence`/`Device`. No
discovery or scan-profile code was touched — confirmed by re-running
BENCH-002's synthetic benchmark scenario end-to-end (see Regression
Tests) with zero changes to how evidence is collected, only to how it's
interpreted.

---

## Classification Improvements

Re-running BENCH-002's exact synthetic 12-device fixture through the
updated classifier (no changes to the fixture itself):

| Metric | FAST | STANDARD (before → after) | DEEP (before → after) |
|---|---:|---:|---:|
| SERVER | 2 (unchanged) | 2 → **3** | 2 → **3** |
| UNKNOWN | 4 (unchanged) | 3 → **2** | 3 → **2** |

`netgear-nas-01` now resolves to `SERVER` under STANDARD and DEEP —
both profiles that actually collect HTTP evidence. It correctly
**remains `UNKNOWN` under FAST**, because FAST performs no service
enrichment at all (confirmed directly: `PROFILE_MESSAGES[ScanProfile.
FAST]` — "Service enrichment disabled by design") and therefore has no
HTTP evidence for `NetworkApplianceRule`'s identifier tier to read. This
is the expected, correct outcome, not a gap — it demonstrates the
improvement is a pure interpretation change with no new information
manufactured out of evidence FAST never collected.

Every other device in the fixture — the two other pre-existing
`UNKNOWN`s (`mystery-box-01`, `web-app-01`), and all eight previously
non-`UNKNOWN` classifications (`SERVER`/`SWITCH`/`PRINTER`/`PHONE`/
`FIREWALL`/`HYPERVISOR`/`ACCESS_POINT`/`WORKSTATION`) — classify
identically before and after this sprint, confirmed by re-running the
fixture (see Regression Tests) and by the full existing test suite
passing unmodified.

---

## Regression Tests

`python -m unittest discover -s tests -p "test_*.py"`: **306 passed, 0
failed** (293 before this sprint + 13 new: 10 in
`test_network_appliance_rule.py`, 3 in `test_classifier.py`).

`devtools.validate.run_full_validation()`: **PASS** — 306/306 unit
tests, and all three benchmark datasets (enterprise, homelab,
small_office) **unchanged at 100.0% accuracy** — none of their fixture
devices carry `"readynas"` evidence, so none were affected, and none
regressed.

BENCH-002's synthetic 12-device benchmark scenario was re-executed
end-to-end (same fixture script, same mocked-`nmap.PortScanner`
methodology, zero changes) against the updated classifier:

- FAST: `SERVER: 2, UNKNOWN: 4` — **unchanged**, `netgear-nas-01`
  correctly still `UNKNOWN` (no enrichment evidence under FAST).
- STANDARD: `SERVER: 2 → 3, UNKNOWN: 3 → 2` —
  `netgear-nas-01` resolved; every other device unchanged.
- DEEP: `SERVER: 2 → 3, UNKNOWN: 3 → 2` — same resolution, every other
  device (including the DEEP-only port-8090 `web-app-01` evidence)
  unchanged in outcome.

This confirms both "BENCH-002 benchmark scenarios continue to execute
successfully" and "previously UNKNOWN benchmark devices are correctly
classified when justified" directly against the actual benchmark
artifact, not just a newly-written unit test asserting the same thing
in isolation.

Every newly introduced heuristic has direct regression coverage:

- Independent match trigger (identifier alone, no corroboration) — 3
  tests (auth realm, HTTP title, product string), plus case-
  insensitivity.
- Corroboration enrichment (vendor, hostname) — 2 tests, plus the
  combined three-signal BENCH-002 shape.
- Deliberate non-triggers (the false-positive guards this design
  depends on) — 4 tests: bare vendor, bare hostname, unrelated NAS
  brand, no evidence at all.

---

## Risk Assessment

**False-positive risk: low, by design.** The only independent trigger
is a specific, brand-committed product-line keyword (`"readynas"`) that
cannot plausibly appear in unrelated evidence. Vendor (`"netgear"`) and
hostname (`"nas"`) substrings — the genuinely risky, ambiguous signals —
are used exclusively as reason-text corroboration after the identifier
has already matched, never as alternative triggers. This was verified
directly, not just asserted: `test_bare_netgear_vendor_without_identifier_
does_not_match` and `test_bare_nas_hostname_without_identifier_does_not_
match` both confirm a device with only the weak signal, and no
identifier, is correctly left unmatched.

**Regression risk to existing classifications: low.** `NetworkApplianceRule`'s
one keyword doesn't overlap with any existing rule's vendor or
identifier keyword lists (checked directly against
`PrinterVendorRule`/`SonicWallFirewallRule`/`SwitchVendorRule`/
`VoiceVendorRule`'s keyword sets), so it cannot preempt or conflict with
any of them. It shares its target `DeviceType` (`SERVER`) with
`ServerHostnameRule`, so even in the unlikely case both matched the
same device, there is no precedence question to get wrong — both agree.
This was the deciding factor in placing it directly after
`ServerHostnameRule` rather than needing careful precedence analysis
the way RULE-002's Printer/Switch conflict required.

**Coverage risk: real, and intentionally not addressed here.** This
rule resolves exactly one appliance identity out of a much larger real-
world population (other NAS brands, print servers, KVM-over-IP,
UPS/PDU management interfaces, etc.). That's a deliberate scope
boundary, not an oversight — see Future Opportunities.

**Naming risk: `NetworkApplianceRule` currently only recognizes NAS
devices.** RULE-002 flagged this exact trap once already (`CiscoSwitchRule`
outgrowing its name). This rule's docstring says explicitly that its
name reflects the evidence *family* RULE-003 investigated, not current
keyword coverage, and that future extensions belong in this rule rather
than a new one — but if a future sprint adds a genuinely different
appliance family (say, UPS/PDU identification) without also broadening
this docstring's framing, the same naming-drift risk RULE-002 corrected
once could recur. Worth a naming sanity-check whenever this rule is
next touched.

---

## Future Opportunities

Deliberately not implemented here, consistent with "do not invent new
relationships simply because they seem reasonable":

1. **Other NAS/appliance brands** (Synology, QNAP, Buffalo, etc.) were
   explicitly considered and excluded. BENCH-002 did not observe any of
   them — adding their product names would be guessing at a plausible-
   sounding relationship, exactly what this sprint's engineering
   principles forbid. If a future benchmark (against a real network,
   unlike BENCH-002's synthetic/localhost data) observes one of these
   in the field, extending `NETWORK_APPLIANCE_IDENTIFIER_KEYWORDS` is a
   one-line, low-risk change following the same pattern established
   here.
2. **BENCH-002's `web-app-01` device remains genuinely unresolved, and
   should stay that way** until stronger evidence exists. Its only
   signal is a generic HTTP title ("Internal Web App - Login") with no
   vendor, product, or hostname corroboration — attempting to match
   generic words like "web" or "app" or "login" would be exactly the
   "broad keyword list" this sprint's engineering principles prohibit,
   and would materially increase false-positive risk across every other
   device with an unrelated login page. Correctly `UNKNOWN`, not a rule
   gap.
3. **BENCH-002's `mystery-box-01` device likewise remains genuinely
   unresolved.** Its vendor ("Generic Manufacturing Co") is intentionally
   uninformative and it carries no HTTP evidence at all in the fixture —
   there is no BENCH-002-observed relationship to extend a rule from.
   This is BENCH-002's own "insufficient evidence" category, not a
   missing-rule category, and RULE-003's scope (evidence
   *interpretation*) has nothing further to interpret here.
4. **A shared identifier-tier keyword table**, if a third or fourth
   similarly narrow, single-brand appliance rule accumulates in the
   codebase (this one, plus any future UPS/PDU/KVM-style rule) — right
   now, with exactly one such rule, that abstraction would be premature
   (three near-identical 90-line rule files is not yet a pattern that
   needs its own infrastructure; RULE-002's printer/firewall/switch
   rules already establish that duplication at this scale is acceptable
   and explicit rather than abstracted away).
