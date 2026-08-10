# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — this sprint changes rule composition, evidence-tier
ordering within one rule, and classifier rule-list ordering. It does not
change the `ClassificationRule` contract, the `RuleResult` contract, the
first-match-wins evaluation model, or the evidence model, so ADR-002,
ADR-003, and ADR-004 (see [docs/ADR.md](../ADR.md)) remain accurate as
written.

Recommended Next Sprint:
No single sprint is pre-selected. Two candidates surfaced during this
investigation but were deliberately left out of scope: (1) an
authenticated/SNMP-`sysDescr`-based evidence sprint, which is the only
path to resolving vendor-ambiguous UNKNOWN devices (e.g. bare "Lenovo"
vendor with no other signal) that this reasoning-only sprint could not
address without new evidence collection; (2) a documentation cleanup pass
on `docs/classification-rules.md`, which ARCH-001A already flagged as
stale/overlapping with `docs/architecture/classification.md` and which
this sprint did not touch.

---

## Summary

This was a reasoning sprint: no discovery providers, evidence fields, or
the evidence-collection pipeline changed. All changes are confined to how
`DeviceClassifier` interprets evidence it already receives.

Two concrete misclassifications named in scope were fixed:

1. Devices identified only by an HTTP title such as `"Ubiquiti
   EdgeSwitch"` — with no vendor/hostname signal a rule previously
   recognized — fell through every rule to `UNKNOWN`. No rule read
   product/HTTP-title/TLS identity evidence for switches at all; only
   `PrinterVendorRule` and `SonicWallFirewallRule` had that identifier
   tier.
2. HP ProCurve switches classified as `PRINTER`. Root cause:
   `PrinterVendorRule` (position 5) matched on a bare `"hp"` vendor
   substring before the switch rule (formerly `CiscoSwitchRule`, position
   7) ever ran. The vendor string `"HP"`/`"Hewlett-Packard"` is inherently
   ambiguous between printers and ProCurve switches, so no vendor-only
   check can resolve it — only stronger identity evidence (an HTTP
   title/product string containing `"ProCurve"`) can, and that evidence
   was never being checked for switches at all.

Both were fixed by the same underlying change: giving the switch rule an
identifier-evidence tier (mirroring the tier `PrinterVendorRule` and
`SonicWallFirewallRule` already use) and moving it ahead of
`PrinterVendorRule` in the classifier's rule list, so explicit switch
identity evidence is checked before a weaker, ambiguous vendor keyword can
intercept the device.

The rule was also renamed from `CiscoSwitchRule` to `SwitchVendorRule`
(file `cisco_switch_rule.py` → `switch_vendor_rule.py`) because it now
matches Ubiquiti and HP product identity strings in addition to Cisco —
keeping the old name would have misrepresented its scope to the next
engineer reading the rule list, which is exactly the kind of rule-clarity
problem this sprint was chartered to fix.

No other UNKNOWN-reduction opportunities were implemented. All three
benchmark datasets (`enterprise`, `homelab`, `small_office`) already
classify at 100% accuracy before and after this change, and the one
benchmark device that stays `UNKNOWN` (homelab's `media-center`, vendor
`Lenovo`, no other evidence) is a genuine insufficient-evidence case, not
a missing/misordered rule — see Known Limitations.

---

## Files Changed

Production code:

- `networkmapper/classification/rules/switch_vendor_rule.py` — new file,
  replaces `cisco_switch_rule.py`. Same class body as before plus a new
  identifier-evidence tier.
- `networkmapper/classification/rules/cisco_switch_rule.py` — deleted
  (renamed).
- `networkmapper/classification/rules/__init__.py` — import/`__all__`
  updated for the rename.
- `networkmapper/classification/device_classifier.py` — import updated
  for the rename; rule list reordered (see Rule Ordering Changes); added
  a docstring explaining the new ordering rationale.
- `devtools/validate.py` — `STANDARD_REGRESSION_TESTS` updated to
  reference `tests.test_switch_vendor_rule` instead of the deleted
  `tests.test_cisco_switch_rule` (this was a hardcoded module list; the
  rename would have silently dropped switch-rule coverage from fast
  validation otherwise).

Tests:

- `tests/test_switch_vendor_rule.py` — new file, replaces
  `test_cisco_switch_rule.py`. Retains all six original test cases
  unchanged (still passing against the renamed class) and adds five new
  cases covering the identifier tier: EdgeSwitch-by-HTTP-title,
  ProCurve-by-product, ProCurve-by-HTTP-title, and an explicit
  bare-HP-vendor-without-identifier non-match to prove the new tier
  doesn't over-match.
- `tests/test_cisco_switch_rule.py` — deleted (renamed).
- `tests/test_classifier.py` — four new full-pipeline precedence tests
  (EdgeSwitch → SWITCH, ProCurve → SWITCH, plain HP printer still →
  PRINTER, Cisco IP Phone still → PHONE not SWITCH).
- `tests/test_rule_result_framework.py` — `CiscoSwitchRule` references
  updated to `SwitchVendorRule` (behavior of those tests is unchanged).
- `tests/test_classification_workbench.py` — rule-evaluation-order
  assertions updated: `VoiceVendorRule` and `SwitchVendorRule` are now
  asserted present (they run, and don't match, before `PrinterVendorRule`
  matches a Brother-vendor device), where the old test asserted them
  absent under the previous ordering. `DellWorkstationRule` remains
  asserted absent — it's still ordered after `PrinterVendorRule`.
- `tests/test_devtools_validate.py` — hardcoded expected count for the
  fast-validation regression subset updated from 109 to 117 (reflects the
  9 new tests added to modules already in that subset:
  `test_switch_vendor_rule` and `test_classifier`).

---

## Rules Added

None. No new `ClassificationRule` subclass was introduced.

## Rules Modified

- **`SwitchVendorRule`** (formerly `CiscoSwitchRule`): added an
  independent identifier-evidence match tier. It checks product, HTTP
  title, TLS certificate subject/issuer, and HTTP auth realm (via the
  existing shared `first_matching_identifier` helper, in that existing
  priority order) for `"procurve"` or `"edgeswitch"`. This tier sits
  between the existing vendor tier (`"cisco"` in vendor) and the existing
  hostname-plus-management-port heuristic tier — the same three-tier
  shape `PrinterVendorRule` and `SonicWallFirewallRule` already use
  (vendor → identifier → hostname/network heuristic). No other tier's
  logic changed; all six pre-existing test cases pass unmodified against
  the renamed class.

  The keyword set was deliberately kept to the two vendors named in
  scope. It was not generalized to other switch product lines (Cisco
  Catalyst/Nexus, Aruba, Netgear, etc.) because no concrete
  misclassification or evidence example justified them — adding
  speculative keywords would be evidence-free rule expansion, which this
  sprint's own engineering principles ("prefer stronger evidence over
  weaker evidence", not "prefer more rules") argue against.

## Rule Ordering Changes

Old order:

```
ServerHostnameRule → HypervisorHostnameRule → UbiquitiAccessPointRule →
SonicWallFirewallRule → PrinterVendorRule → VoiceVendorRule →
CiscoSwitchRule → DellWorkstationRule
```

New order:

```
ServerHostnameRule → HypervisorHostnameRule → UbiquitiAccessPointRule →
SonicWallFirewallRule → VoiceVendorRule → SwitchVendorRule →
PrinterVendorRule → DellWorkstationRule
```

Two changes, both required together:

1. **`SwitchVendorRule` moved ahead of `PrinterVendorRule`.** This is the
   direct fix for HP ProCurve: without it, `PrinterVendorRule`'s bare
   `"hp"` vendor-keyword match (weak evidence) always wins before the
   switch rule's `"procurve"` identifier match (strong evidence) is ever
   evaluated, regardless of the identifier tier added above.
2. **`VoiceVendorRule` stays ahead of `SwitchVendorRule`** (it already
   was, in the old order — position 6 vs. 7). This had to be preserved
   explicitly when reordering, because `SwitchVendorRule`'s vendor tier
   is a bare `"cisco" in vendor` substring match, which would otherwise
   match a Cisco IP Phone (vendor string `"Cisco IP Phone"`, which also
   satisfies `VoiceVendorRule`'s more specific `"cisco ip phone"`
   keyword) as `SWITCH` if voice evidence were checked after switch
   evidence. `test_cisco_ip_phone_still_classifies_as_phone_not_switch`
   in `test_classifier.py` regression-tests this directly.

No other rule's relative position changed.

---

## Regression Results

Full suite (`python -m unittest discover -s tests`): **248 passed, 0
failed** (240 before this sprint + 9 new: 5 in `test_switch_vendor_rule`,
4 in `test_classifier`).

Fast validation subset (`devtools.validate.run_validation()`): **117
passed, 0 failed** (109 before this sprint, +8 from the two modules in
that subset that gained tests).

Full validation including all three benchmarks
(`devtools.validate.run_full_validation()`): **PASS** — 248/248 unit
tests, and:

| Dataset | Devices | Accuracy | Result |
|---|---|---|---|
| enterprise | 9 | 100.0% | PASS |
| homelab | 5 | 100.0% | PASS |
| small_office | 5 | 100.0% | PASS |

No existing benchmark device's classification changed. In particular,
`enterprise`'s `switch-core-01` (hostname-plus-SNMP-only evidence,
`vendor: "Unknown"`) and every printer/firewall/hypervisor/server
benchmark entry were re-verified to classify identically before and after
the reorder.

---

## Known Limitations

Remaining `UNKNOWN` categories that need more evidence, not more rules:

- **Vendor-ambiguous devices with no corroborating signal.** The
  homelab benchmark's `media-center` (vendor `Lenovo`, no hostname
  keyword, no services) correctly stays `UNKNOWN`. `Lenovo` alone doesn't
  distinguish a workstation from a NUC-style media appliance or a
  thin client, and there is no hostname, port, or identifier evidence to
  disambiguate. This is an **insufficient evidence** case, not a missing
  or misordered rule — inventing a rule to force a classification here
  would be guessing, not interpreting evidence, which is explicitly out
  of scope for a reasoning sprint.
- **Devices whose only distinguishing evidence lives in fields this
  sprint was scoped not to touch.** For example, a switch with no
  open curated port (22/23/161), no vendor match, and no HTTP/TLS
  evidence exposed (e.g. management interface on a non-curated port, or
  SNMP disabled) has no reachable evidence for any existing rule to act
  on. This is a collection-scope limitation already documented in
  DISC-001, not something rule reinterpretation can fix.
- **Vendor keyword coverage is intentionally narrow.** `SwitchVendorRule`
  now recognizes `"procurve"` and `"edgeswitch"` specifically because
  those were the named cases with concrete evidence. Other switch
  product lines (Aruba, Netgear, Juniper non-vendor-string identifiers,
  Cisco Catalyst/Nexus product strings beyond the existing bare
  `"cisco"` vendor check) remain unrecognized by identifier evidence
  until a similar concrete example justifies adding them — expanding the
  keyword list further without a real observed case would be scope
  creep this sprint deliberately avoided.
