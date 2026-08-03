# Status

Implementation Complete

Production Code Modified: Yes

ADR Required: No

Recommended Next Sprint:
FEAT-003E – NSE-Script Discovery Evidence Collection (http-title, ssl-cert,
smb-os-discovery), per ADR-009's deferred Future Work — see Recommended
Next Sprint below for the reasoning.

---

## Summary

Every one of the 8 classification rules was evaluated for whether the
`ServiceEvidence.product`/`.version` fields FEAT-003C introduced (and left
unconsumed — see FEAT-003C's Known Issues) could improve confidence,
specificity, or explainability. Three rules received targeted, evidence-
supported changes; five were deliberately left unchanged, each with a
documented reason. No discovery, scan-profile, or architecture change was
made; ADR-009 required no revision.

A new generic helper, `first_matching_product()`, was added to
`evidence_helpers.py` alongside the existing `first_matching_port`/
`first_matching_service`. It performs substring matching (not exact
membership), because Nmap product strings are free-text descriptions
(e.g. `"VMware ESXi Server httpd"`), unlike the fixed port numbers and
service names the existing helpers match against.

**Implemented:**

- **`HypervisorHostnameRule`** — if any service's `product` contains
  `"vmware"`, the reason text is enriched with that product string as
  additional corroboration. This does not change *when* the rule
  matches (the hostname-keyword gate is unchanged); it only strengthens
  *why* an already-matching device is explained as a hypervisor. Chosen
  because VMware's ESXi/vCenter management httpd is one of the most
  reliably product-fingerprinted services in Nmap's default probe
  database.
- **`CiscoSwitchRule`** — if any service's `product` contains `"cisco"`,
  the reason text is enriched the same way, appended only when the
  existing hostname-plus-management-signal match already fired. Product
  evidence alone (without a port/service signal) does **not** trigger a
  match — verified by a new test asserting exactly that. Chosen because
  Cisco IOS/IOS-XE SSH daemons are commonly identified by product string
  in Nmap's banner-based detection.
- **`PrinterVendorRule`** — reuses the *existing*, already-trusted
  `SUPPORTED_PRINTER_VENDOR_KEYWORDS` list (previously checked only
  against the `vendor` field) against service `product` strings too, as
  a new independent match tier between the vendor check and the
  networking-protocol fallback. Chosen because Nmap's IPP (port 631)
  probe commonly returns the exact printer make/model as the product
  string (e.g. `"HP LaserJet 4250"`), which is at least as strong an
  identifier as the vendor field, and because reusing an already-
  accepted keyword list — rather than introducing a new one — avoids
  inventing an unsupported fingerprint.

**Deliberately not implemented** (see Rule-by-Rule Evaluation for full
reasoning): `ServerHostnameRule`, `DellWorkstationRule`,
`UbiquitiAccessPointRule`, `SonicWallFirewallRule`, `VoiceVendorRule`.

All three benchmark datasets remain at 100% accuracy — none of the
curated fixture devices populate `product`, so no existing classification
outcome changed. Full validation (`python -m devtools validate --all`)
shows zero regressions; the one error present is the pre-existing,
unrelated CSV exporter defect documented in TEST-001 and reconfirmed in
FEAT-003C.

---

## Rule-by-Rule Evaluation

| Rule | Product/version evidence used? | Reasoning |
|---|---|---|
| `ServerHostnameRule` | No | Pure hostname-keyword rule (`"dc"`, `"cam"`, `"srv"`, `"server"`) with no vendor or service concept at all. "Server" is not a product-identifiable category — no product string would discriminate it. |
| `HypervisorHostnameRule` | **Yes** | See Summary. `"vmware"` in `product` is a well-established, reliable Nmap fingerprint family. |
| `UbiquitiAccessPointRule` | No | Ubiquiti's web management interface does not reliably expose a `"Ubiquiti"`-branded product string via plain `-sV` (no NSE scripts were added in FEAT-003C or this sprint). Implementing this would mean guessing at a fingerprint not actually verified against Nmap's behavior — explicitly prohibited by this sprint's scope. |
| `SonicWallFirewallRule` | No | Genuine uncertainty: I could not verify, with the confidence the "strong, deterministic evidence" bar requires, that Nmap's default `-sV --version-light` probe reliably identifies SonicWall products by name without deeper probe intensity or NSE scripts (neither of which this sprint may add). Per the constraint against inventing unsupported fingerprints, this was left unimplemented rather than guessed at. Listed explicitly here because SonicWall was named as an example in this sprint's scope — the omission is a deliberate evidentiary decision, not an oversight. |
| `PrinterVendorRule` | **Yes** | See Summary. IPP product-string detection for exact printer make/model is one of Nmap's best-documented "product" detections for office hardware. |
| `ServerHostnameRule` | (listed above) | |
| `CiscoSwitchRule` | **Yes** | See Summary. Cisco SSH banner detection is well-established. |
| `DellWorkstationRule` | No | No realistic Dell-branded network service exists for a general-purpose Windows workstation for Nmap to fingerprint. Vendor/hostname-keyword matching remains the only viable signal. |
| `VoiceVendorRule` | No | SIP service detection in Nmap's default probe set (port 5060/5061) typically returns a generic `"sip"` service name without a reliable phone vendor/model product string absent deeper SIP-specific probing. Left unimplemented for the same reason as SonicWall: insufficient confidence to meet the "strong, deterministic evidence" bar. |

**On the sprint's example list** (`VMware products`, `Apache HTTP
Server`, `Microsoft IIS`, `JetDirect`, `SonicWall products`, `Cisco
service banners`): two examples were deliberately not pursued for reasons
distinct from the "insufficient confidence" cases above, worth stating
explicitly:

- **Apache HTTP Server / Microsoft IIS** — Nmap's product detection for
  these is extremely reliable, but neither is a *device-type-specific*
  identifier. Both run on servers, printers, hypervisor management
  interfaces, routers, and firewalls alike. Reliable detection alone
  does not make a signal useful to a *specific* classification rule when
  it doesn't discriminate between device types. No rule was extended
  with generic web-server product matching for this reason.
- **JetDirect** — already effectively handled. Port 9100's JetDirect/
  AppSocket protocol is a raw binary protocol with no application-layer
  handshake, so Nmap's `-sV` typically cannot populate a `product` field
  for it at all; the existing `service` name check (`"jetdirect"` /
  `"pdl-datastream"` in `PRINTER_SERVICE_KEYWORDS`) is already the
  correct and only realistic signal available over that port. No
  additional product-based work was needed or added.

---

## Files Changed

**Production code**

- `networkmapper/classification/evidence_helpers.py` — added
  `first_matching_product()`.
- `networkmapper/classification/rules/hypervisor_hostname_rule.py` —
  added `HYPERVISOR_PRODUCT_KEYWORDS`; appends product corroboration to
  the reason text when present.
- `networkmapper/classification/rules/cisco_switch_rule.py` — added
  `SWITCH_PRODUCT_KEYWORDS`; appends product corroboration to the reason
  text only when the existing hostname-plus-management-signal match
  already fired.
- `networkmapper/classification/rules/printer_vendor_rule.py` —
  restructured `classify()` into a single linear flow (vendor → product →
  networking → no match), removing duplicate branching that existed
  before this sprint; added `_find_printer_vendor_product()`.

**Tests**

- `tests/test_hypervisor_hostname_rule.py` — 3 new tests: product
  corroboration with a port/service match, product corroboration with
  neither, and confirmation that a non-VMware product leaves the reason
  unaffected.
- `tests/test_cisco_switch_rule.py` — 2 new tests: product corroboration
  when the existing management-signal gate is satisfied, and confirmation
  that product evidence alone (no port/service) does **not** trigger a
  match.
- `tests/test_printer_vendor_rule.py` — 3 new tests: product-only match,
  product taking precedence over a simultaneous networking-only signal,
  and a non-printer product correctly falling back to the existing
  networking-signal path.
- `tests/test_devtools_validate.py` — updated the fast-validation
  test-count pin (`75` → `83`) to reflect the 8 new tests added to files
  already inside `STANDARD_REGRESSION_TESTS`. This is a deliberate,
  expected update to a literal test-count assertion whose purpose is to
  catch *unexpected* changes to the fast classification-only regression
  surface — this sprint's change to that count is intended and verified,
  not a regression it should have caught.

No production code outside `networkmapper/classification/` was touched.
No discovery code, scan profile, benchmark fixture, serializer, or
documentation file was modified — none needed a change, since this
sprint's evidence source (`ServiceEvidence.product`) already existed in
full from FEAT-003C.

## Validation Performed

`python -m devtools validate --all`:

```
Unit Tests: 151 run, 0 failures, 1 error
Benchmarks: enterprise PASS (100.0%), homelab PASS (100.0%), small_office PASS (100.0%)
Overall Status: FAIL
Runtime: 0.59s
```

The single error is the same pre-existing, unrelated
`tests.test_csv_exporter.CsvExporterTest.test_export_writes_expected_csv_rows`
defect documented in TEST-001 and reconfirmed in FEAT-003C
(`AttributeError: 'str' object has no attribute 'name'` in
`csv_exporter.py`, untouched by this sprint).

One regression surfaced during validation and was fixed within this
sprint, not left as a known issue: `test_devtools_validate.py`'s
hardcoded fast-validation test count (`75`) no longer matched reality
after this sprint added 8 new tests to already-fast-listed rule test
files. This was a expected consequence of intentionally adding tests to
already-included files, confirmed by checking that all three modified
test files (`test_cisco_switch_rule`, `test_hypervisor_hostname_rule`,
`test_printer_vendor_rule`) are already members of
`STANDARD_REGRESSION_TESTS` — not evidence of scope creep into the fast
path. The pin was updated to `83` accordingly.

All three benchmark datasets remain at 100% accuracy, unchanged from
before this sprint — none of the curated fixture devices populate
`product`, so none of this sprint's new evidence paths fire against
existing benchmark data. This was expected and is not, by itself, strong
validation that the new rules work; correctness is established by the
new unit tests, which construct `ServiceEvidence` entries with `product`
set directly.

## Known Issues

- **No benchmark case exercises the new product-based evidence paths.**
  All three benchmark datasets predate `product` capture and none was
  updated, per this sprint's instruction to update fixtures "only when
  behavior intentionally changes" — no existing fixture device's
  classification outcome changed. Adding a benchmark case that
  specifically exercises product-based classification (e.g. a device
  identifiable only by product string, with no matching vendor or
  hostname) would be a reasonable follow-up but was not required by this
  sprint's validation instructions, which named unit tests, not new
  benchmark cases, as the required coverage.
- **`ServiceEvidence.version` remains fully unconsumed.** This sprint
  used `.product` but not `.version` (e.g. distinguishing an outdated
  vs. current firmware/software version is a monitoring/risk concern,
  not a device-type classification signal, so no rule needed it). This
  is a deliberate scope decision, not an oversight — flagged for
  visibility rather than as a defect.
- **The `"hp"` keyword in `SUPPORTED_PRINTER_VENDOR_KEYWORDS`** is a
  short, two-character substring, now also matched against free-text
  product strings (previously only against the shorter `vendor` field).
  This carries a small false-positive risk against product text
  containing an incidental `"hp"` substring (e.g. a hypothetical
  service naming itself something containing "...hp..."). This risk is
  inherited from the pre-existing, already-accepted keyword list — not
  newly introduced — and no realistic false positive was found during
  this sprint's evaluation of common service/product strings (Apache
  httpd, OpenSSH, lighttpd, SonicWALL, Microsoft-IIS, and vsftpd were all
  checked and do not contain `"hp"` as a substring).

## Next Recommended Sprint

**FEAT-003E — NSE-Script Discovery Evidence Collection**
(`http-title`, `ssl-cert`, `smb-os-discovery`), per ADR-009's Future Work
and FEAT-003A's original recommendation. This sprint closed the loop on
the product/version evidence FEAT-003C already collected from the
existing `-sV` scan (per FEAT-003C's own recommended next sprint). The
next incremental, well-justified step is on the *discovery* side again:
adding a small number of targeted NSE scripts on ports already inside
`CLASSIFICATION_PORTS` would surface materially stronger identifiers
(e.g. an HTTP title of "SonicWALL Network Security Appliance" or a TLS
certificate CN) for exactly the rules this sprint had to skip
(`SonicWallFirewallRule`, `UbiquitiAccessPointRule`) due to insufficient
confidence in what `-sV` alone provides — those gaps would not need to
remain gaps once NSE-derived evidence exists to evaluate. This was
explicitly deferred by ADR-009 as future work and is not blocked by
anything in this sprint.
