# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: Yes — Section 8 recommends a future ADR formalizing
canonical identity as a derived interpretation (an `IdentityResult`
analog to `RuleResult`), following the same Investigation → Architecture
Review → ADR sequence ADR-009/ADR-010/ARCH-014 already used. Per this
sprint's explicit scope ("Do not create ADRs. Wait for engineering
review."), no ADR is recorded here.

Recommended Next Sprint:
Not pre-selected, per this investigation's own scope constraint. Two
candidates emerge from the findings below, in either order: (a) design
of the identity-evidence retention/provenance mechanism Section 8
recommends, ideally coordinated with ARCH-014's own deferred
relationship-evidence provenance work rather than built twice, or (b)
the canonical-identity ADR itself, which several findings here (Section
3's asset-vs-instance split in particular) suggest should be decided
before either mechanism is designed in detail. That sequencing choice is
an engineering-review decision, not this investigation's to make.

---

## 1. Executive Summary

ARCH-014 concluded that relationship identity cannot be resolved before
device identity, because `NetworkGraph.add_device`
(`networkmapper/core/network_graph.py:15-19`) keys devices by IP address
alone and NetworkMapper has no concept of "the same device, seen again."
This investigation is the direct follow-up: which observations
legitimately establish that two observations describe the same device,
which are merely correlated with it, and which should never be trusted
to establish identity at all.

The central finding is that **no single field NetworkMapper collects
today, or is likely to collect from any near-term provider, is
unconditionally safe as sole identity evidence** — including fields that
intuitively feel like strong identifiers. IP address is already known to
be transient (ARCH-014, ADR-008's own deferred Future Work). This
investigation finds MAC address is only *conditionally* stable — modern
client operating systems (iOS, Android, Windows, macOS) randomize MAC
addresses by default for privacy, meaning MAC is reliable identity
evidence for fixed infrastructure (switches, printers, servers, access
points) but not for the client endpoints that make up the majority of a
typical network. Even hardware serial numbers and SMBIOS UUIDs — the
strongest category evaluated — are not immutable in every lifecycle
event: cloning and imaging workflows are documented to sometimes fail to
regenerate them, producing two live devices that legitimately share what
should be a unique identifier. No field is safe unconditionally; every
field's trustworthiness depends on device role, collection method, and
lifecycle context.

The second finding is that **"device identity" is not one question but
at least two, and current NetworkMapper implicitly conflates them.**
Some identity-shaped facts (chassis serial number) survive OS reinstall,
motherboard-adjacent NIC swaps, and even some board replacements — they
track a physical asset. Others (a Windows machine SID, a Linux
`/etc/machine-id`) are regenerated on reimage even when the physical
hardware, hostname, and IP are all unchanged — they track an OS/software
instance, not the box it runs on. A reimaged PC is "the same device" by
asset identity and "a new device" by instance identity, and both answers
are correct for different purposes. This investigation finds
`ObservationDevice`'s existing docstring
(`networkmapper/knowledge/models.py:44-56`, "Stable device-identity
fields... ip/hostname/vendor/mac") already asserts a stability claim
this investigation cannot fully confirm — worth reconciling once a
canonical identity model exists, not a defect in KNOW-003's narrower,
already-scoped use of those fields today.

The third finding is architectural, not evidentiary: canonical identity
should be **derived, not assigned** — an interpretation resolved from
retained, individually-attributed identity observations, structurally
the same shape ADR-008 already establishes for `device_type`
(evidence → interpretation) and the same shape ARCH-014 Section 5
already concluded relationship evidence needs (retained observations,
not one collapsed value). This investigation finds no reason identity
resolution should diverge from that lineage, and finds that
`first_matching_identifier`
(`networkmapper/classification/evidence_helpers.py:67-104`) — an
ordered, deterministic, explainable evidence-hierarchy check already
proven in classification — is a directly reusable pattern for identity
corroboration, not a new mechanism to invent.

No production code, data model, or provider is proposed for change by
this report, and no numeric confidence score is introduced anywhere
below.

---

## 2. Identity Philosophy

The charter states the conclusion this section is asked to justify:
"Identity is not a single field. Identity is an interpretation derived
from corroborated observations. No single observation should
automatically become canonical identity unless the architecture can
justify that decision." This investigation finds that framing directly
consistent with, rather than an addition to, decisions NetworkMapper has
already made twice:

- **ADR-008** separates discovery (immutable, observed) from
  interpretation (adjustable, derived) for `device_type`. Canonical
  identity is the same shape one layer earlier: identity *evidence*
  (a MAC address, a chassis serial, a reported hostname) is discovery —
  observed, immutable once recorded. Canonical *identity* — the
  conclusion "this evidence set describes device X" — is interpretation,
  adjustable as more evidence arrives, exactly as `device_type` is
  adjustable as classification rules or evidence change.
- **ARCH-014 Section 2** reached the identical structural conclusion one
  layer later, for relationships: "a Relationship Observation is
  discovery, immutable and provider-attributed; a Corroborated
  Relationship is interpretation, derived from one or more observations
  and adjustable." Identity sits *between* ADR-008's device-evidence
  layer and ARCH-014's relationship-evidence layer in this same lineage:
  a relationship's endpoints are only meaningful once identity itself is
  resolved (ARCH-014 Section 7's own finding), and identity itself
  follows the same observation → interpretation shape ADR-008 already
  established for device_type and ARCH-014 already re-confirmed for
  relationships.

This is not a coincidence worth treating lightly: three independent
investigations, each scoped narrowly to a different subject
(classification, relationships, now identity), have each independently
arrived at the same evidence/interpretation split. That convergence is
itself evidence the pattern is structural to how NetworkMapper reasons
about discovered facts, not specific to any one subsystem.

One further implication follows directly: if identity is interpretation,
then **canonical identity can be wrong, and revising it must not corrupt
the underlying evidence** — the same non-negotiable property ADR-008
already establishes for `device_type` re-classification. A future
identity resolver concluding "these two observations are not, after all,
the same device" must be able to un-corroborate without deleting or
rewriting either observation, exactly as re-running the classifier never
edits `Device.hostname` or `Device.vendor`.

---

## 3. Identity Evidence Assessment

Each candidate is evaluated for stability and architectural value against
what NetworkMapper collects today or has already investigated collecting
(ARCH-012, ARCH-013, FEAT-003 series), not against a hypothetical
provider — per the charter, existence of future evidence is not assumed,
only its architectural implications where a source is already named.

### Network

**IPv4 address.** Currently the *only* field `NetworkGraph.add_device`
uses to distinguish devices (`networkmapper/core/network_graph.py:15-19`).
Already established by ADR-008's deferred Future Work and ARCH-014 as
unstable under DHCP reassignment. This investigation reconfirms it
belongs in a **Transient/Contextual** category (Section 4): it describes
where a device currently is, not what it is, and must never be sufficient
alone to establish identity — it is the exact field whose current
overloaded use as identity is this investigation's motivating problem.

**IPv6 address.** Intuitively feels more permanent than IPv4, but this
investigation finds the opposite is often true in practice: IPv6 privacy
extensions (RFC 4941), enabled by default on most modern client
operating systems, generate temporary addresses that rotate on a
schedule specifically *to* avoid being a stable identifier — the
protocol's own design goal is the inverse of what identity evidence
needs. An EUI-64-derived IPv6 address (embedding the interface's MAC)
can indirectly corroborate a MAC address, but only when privacy
extensions are disabled, which is increasingly not the default case.
Category: **Transient**, and a case where the field's name ("address")
suggests more stability than its real-world deployment behavior
delivers.

**MAC address.** Already collected today (`Device.mac_address`, sourced
from Nmap's ARP-based discovery,
`networkmapper/discovery/nmap_provider.py:428-431`). This investigation's
clearest finding of *conditional* rather than unconditional stability:
MAC address randomization is the current default behavior for Wi-Fi
client connections on iOS, Android, Windows, and macOS — a deliberate
privacy feature, not a rare misconfiguration — meaning a MAC address
observed for a laptop or phone today may not recur on that same device's
next connection. For fixed infrastructure (switches, printers, servers,
access points, most IoT/embedded devices), MAC remains reliably stable,
because randomization is a client-Wi-Fi-stack behavior these device
classes don't implement. **The same field name therefore requires two
different stability classifications depending on device role** —
Persistent for infrastructure, Transient-to-Contextual for modern client
endpoints — which no flat category list captures without also knowing
what kind of device produced the observation (Section 4 addresses this
directly).

### Operating System

**Hostname.** Human-assigned, mutable at will, with no uniqueness
guarantee outside a scoped directory (two devices on different subnets
can share a hostname trivially; DHCP/DNS environments routinely reuse
short-lived names). `evidence_helpers.normalize_hostname`
(`networkmapper/classification/evidence_helpers.py:115-120`) already
normalizes hostname text for classification matching, but that is a
text-comparison concern, not a stability guarantee — normalization makes
two spellings of the same claim comparable, it does not make the
underlying claim more trustworthy as identity. Category:
**Human-assigned**, weak alone, valuable as corroboration.

**Computer name.** The NetBIOS name reported by SMB negotiation
(`NmapProvider._extract_smb_identity`,
`networkmapper/discovery/nmap_provider.py:545-564`). Conceptually the
same claim as hostname, but sourced differently — queried directly from
the host's own protocol stack rather than potentially-stale DNS —
making it a higher-trust *instance* of the same Human-assigned category,
not a structurally different one.

**Domain membership.** Alone, describes organizational context, not
device identity — two devices in the same domain are not the same
device. Combined with computer name, however, it becomes materially
stronger: Active Directory enforces computer-account-name uniqueness
*within* a domain, so `(domain, computer_name)` as a pair carries a real
uniqueness guarantee bare `hostname` does not. This is a concrete,
protocol-backed reason to treat a domain-qualified computer name as
meaningfully stronger corroboration than an unqualified hostname, not
merely "more data points."

### Hardware

**Serial number / chassis serial.** Not collected by any current
NetworkMapper provider. Architecturally the strongest category
evaluated for surviving OS reinstall, hostname change, and IP change —
but not unconditionally immutable across every event this investigation
was asked to consider: motherboard replacement can change a
*motherboard-level* serial while the *chassis-level* serial (factory-set
on the enclosure, read via DMI/SMBIOS Type 1/Type 2) persists — these
are two independently-mutable identifiers commonly conflated under one
name. A second, well-documented caveat: many generic/DIY-built systems
report a literal placeholder string (e.g. "To Be Filled By O.E.M.")
where a real serial should be — a collection-time garbage value that a
future implementation would need to detect and discard rather than trust
at face value. Category: **Immutable** for genuine chassis-affixed
serials, with a known, real-world validity caveat.

**System UUID / SMBIOS UUID.** DMI/SMBIOS Type 1 system UUID.
Persistent under normal operation, and — for virtual machines —
deliberately preserved across live migration (vMotion and equivalents)
by hypervisor design, since migration must be transparent to the guest.
It is *not* reliably preserved across VM cloning: a template clone is
expected to receive a new UUID, but improperly prepared templates
(a known, documented VMware/Hyper-V operational hazard, not a
theoretical one) can produce two running VMs that report the identical
UUID. Category: **Immutable under normal operation and migration, not
guaranteed distinct across cloning** — the same conditional-stability
pattern as MAC address, arising from a different mechanism.

### Virtualization

**Hypervisor UUID / VMware Managed Object Reference (MoRef, e.g.
`vm-1234`).** Not a device-intrinsic identifier at all — it is scoped to
one vCenter/ESXi management plane's own inventory. It is stable within
that plane, but migrating a VM's management to a different vCenter (or
re-adding a host under a different vCenter) can change or invalidate it.
This is the first category evaluated that is **provider-scoped rather
than device-scoped**: it identifies a VM *to its managing vCenter*, not
to NetworkMapper or to any other system observing the same VM by a
different path. Valuable corroboration input, but this investigation
finds it should never itself become canonical identity, because it says
nothing meaningful outside its owning management plane's scope.

### Directory

**SID (Windows machine account Security Identifier).** Domain-scoped;
regenerated when a computer is removed and rejoined to a domain, and
critically — a *reimaged* Windows machine that rejoins Active Directory
under the identical computer name still receives a new machine SID. This
is the clearest concrete case in this investigation demonstrating that
"same hostname, same domain" does not imply "same SID": reimage-and-
rejoin-with-identical-name is a routine, intentional IT operational
pattern, not an edge case. SID is therefore evidence that would
correctly argue *against* continued identity across a reimage — directly
motivating the asset-identity/instance-identity distinction raised in
Section 1 and expanded in Section 6.

**Machine GUID** (Windows: `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid`;
Linux equivalent: `/etc/machine-id`). Same category and same caveat as
SID — regenerated on OS reinstall/reimage on most platforms — and not
reachable by any current or already-scoped-for-Phase-3 NetworkMapper
provider (ARCH-013 Section 8's WMI scope named OS/computer-name/domain/
inventory, not registry-level identifiers; reaching this field would be
new provider scope, not evaluated further here per the charter).

### Cloud

**Azure device identifiers / Entra object identifiers.** Structurally
identical in kind to SID/Machine GUID — directory-scoped (to a cloud
tenant rather than an on-prem domain) and dependent on join/hybrid-join
state — but reached through a fundamentally different mechanism: a
Graph API query against a tenant, not a network-reachable probe against
an IP. This is the first category evaluated that **cannot be discovered
by scanning a device on the network at all**; it could only ever be
correlated onto an already-identified device after the fact (matched by
hostname/domain), never used as a primary discovery path for identity.
This has a direct architectural implication for Section 5 (Provider
Interaction): cloud/directory identity evidence is corroborating-only by
construction, not a peer of network-discoverable evidence.

---

## 4. Identity Categories

The charter's candidate category list — Immutable, Persistent,
Contextual, Transient, Human-assigned, Provider-generated — is useful,
but Section 3's findings show it conflates two independent questions: **how
stable is this value** (Immutable/Persistent/Contextual/Transient) and
**who or what assigns it** (Human-assigned/Provider-generated/
Hardware-intrinsic). A single flat list forces every observation into
one bucket even when, as Section 3 repeatedly found, the same field's
correct stability classification depends on device role (MAC) or
lifecycle event (SMBIOS UUID) — information the origin axis, not the
stability axis, actually carries.

This investigation finds a two-axis classification is a better fit for
the evidence evaluated:

| Field | Stability axis | Origin axis |
|---|---|---|
| IPv4/IPv6 address | Transient/Contextual | Provider-generated (DHCP/SLAAC) |
| MAC address (infrastructure) | Persistent | Hardware-intrinsic |
| MAC address (modern client) | Transient/Contextual | Hardware-intrinsic, but deliberately randomized |
| Hostname / computer name | Human-assigned (weak alone) | Human-assigned |
| Domain + computer name (pair) | Persistent (AD-enforced uniqueness) | Human-assigned + Provider-generated (AD) |
| Chassis serial number | Immutable (with validity caveat) | Hardware-intrinsic |
| SMBIOS UUID | Immutable under normal operation; not guaranteed distinct after cloning | Hardware-intrinsic / hypervisor-assigned |
| VMware MoRef | Persistent within one vCenter only | Provider-generated, provider-scoped |
| Windows SID / Machine GUID | Persistent under normal operation; regenerated on reimage | Provider-generated (OS/directory) |
| Azure/Entra device ID | Persistent within one tenant only | Provider-generated, tenant-scoped |

The practical value of separating these axes: **stability alone tells a
resolver how much to trust a value staying the same; origin tells it
what kind of change would legitimately invalidate it** (a hardware
replacement invalidates hardware-intrinsic evidence; a domain rejoin
invalidates directory-scoped evidence; a DHCP lease renewal invalidates
provider-generated network evidence — three different triggers, not
interchangeable). Section 6 (Identity Lifecycle) uses exactly this
distinction to explain which lifecycle events preserve which evidence.

This investigation recommends the two-axis model over the charter's
flat six-category list as the more useful classification, while noting
the flat list's categories are not wrong — they are exactly the values
the stability axis should take.

---

## 5. Provider Analysis

Evaluated for architectural implications only, per the charter — no
provider is designed.

**WMI.** The richest near-term source evaluated: `Win32_ComputerSystemProduct`
(UUID, `IdentifyingNumber` — vendor serial), `Win32_BIOS` (`SerialNumber`),
and `Win32_ComputerSystem` (`Domain`, `Name`) together reach both the
Hardware-intrinsic and Human-assigned/directory-scoped categories from a
single credentialed connection. Consistent with ARCH-013 Section 8
already naming WMI as architecturally the closest fit for a second
credential-based `EnrichmentProvider` — this investigation adds that WMI
may deliver **identity** value independent of, and prior to, any
relationship-evidence value, since it is the only near-term source that
reaches genuine hardware-intrinsic identity fields at all.

**SNMP.** `snmp_sys_object_id` (`Device.snmp_sys_object_id`, already
collected per FEAT-005/ARCH-012) identifies a device's **product
model**, not the individual unit — every Cisco 2960 switch on a network
reports the identical `sysObjectID`. This investigation finds it
important to state plainly: `sysObjectID` is correctly used today as
classification evidence (RULE-004) and must **not** be mistaken for
identity evidence — it answers "what kind of device is this," never
"which specific device is this." `sysName` (already merged into
`hostname` as a fallback per FEAT-005) is Human-assigned-category
identity evidence, no stronger than any other hostname source. Some
vendors expose per-unit serial numbers via ENTITY-MIB
(`entPhysicalSerialNum`), a distinct, not-yet-evaluated MIB this
investigation names as a possible future source without designing
collection for it.

**VMware.** Uniquely able to report both a provider-scoped identifier
(MoRef) and a guest-hardware identifier (BIOS UUID, via guest info APIs)
for the same VM — the clearest concrete case where a single source
answers both the asset-identity and instance-identity questions
differently for the same device, per Section 3's Virtualization and
Directory findings.

**Redfish.** `Chassis.SerialNumber` and `ComputerSystem.UUID` are
standard, always-present Redfish resource fields on any compliant BMC.
Architecturally, this makes Redfish the strongest single near-term
source of Hardware-intrinsic identity evidence evaluated in this
investigation — reported out-of-band by the BMC itself, not by the
host OS, so it is not subject to OS-level tampering or virtualization
the way a WMI-reported value can be — but narrower in reach than WMI,
since it applies only to server/BMC-managed hardware, not general
endpoints.

**SSH.** Consistent with ARCH-014's own finding for SSH as a
relationship-evidence source: SSH is a channel, not an identity
category by itself. Whatever command is executed over it (`dmidecode`,
`cat /etc/machine-id`, `ip link`) determines which Section 3/4 category
applies, inheriting that field's exact caveats — a `machine-id` read
over SSH is exactly as reimage-fragile as the same field read any other
way.

**Active Directory.** Structurally distinct from every other source
evaluated: querying AD for computer objects (`Name`, `objectSid`,
`whenCreated`, `lastLogonTimestamp`) is a directory query correlated to
a domain, not a network-reachable probe correlated to an IP. Like
Entra/Azure device identifiers (Section 3), this can only be
corroborating evidence layered onto an already-identified device after
the fact, never a primary discovery path — it has no IP to scan.

**Is provider-independent identity achievable?** Partially, and this
investigation finds it important not to overstate the answer. For
server/infrastructure-class hardware, chassis serial and SMBIOS UUID
sourced via WMI, Redfish, or SSH+`dmidecode` all converge on the same
underlying physical fact — three different collection paths corroborating
one device-intrinsic truth, which is the strongest form of
provider-independence this investigation found. But this convergence
does not hold universally: cloud instances have no physical chassis to
report a serial from at all, and modern client endpoints may present
only randomized, Transient-category network evidence with no
Hardware-intrinsic anchor reachable by any evaluated provider. A future
identity model should expect to degrade gracefully — to a lower
corroboration tier (Section 7) — for these device classes, rather than
assuming a hardware anchor is always eventually available.

---

## 6. Identity Lifecycle

Each event is evaluated against the two-axis model from Section 4: does
it invalidate Hardware-intrinsic evidence, Provider-generated/
directory-scoped evidence, or neither.

**Device replacement** (a failed unit swapped for a new one, same role,
IP, and hostname reused by IT convention). Every Hardware-intrinsic
identifier changes (serial, MAC, SMBIOS UUID); only the
Provider-generated/Transient evidence (IP, hostname) is deliberately
kept the same by the technician. This is the single clearest case
demonstrating why IP and hostname continuity must never be sufficient
for identity: it is *exactly* the scenario where naive IP-or-hostname
matching produces the wrong answer with high confidence. Should create a
new identity.

**Motherboard replacement.** Demonstrates that "hardware serial" is not
monolithic: a motherboard-level serial and possibly the SMBIOS UUID
(often read from board-level DMI, not the chassis) can change, while the
chassis serial (affixed to the enclosure, not the board) typically does
not. Whether this preserves identity depends entirely on which
identifier a future model treats as canonical — this is the concrete
event that makes the asset-vs-instance distinction (Section 1, Section 3
Directory) practically, not just philosophically, necessary: by asset
identity (the chassis persists) this is the same device; by a
UUID-anchored instance identity, it may not be.

**NIC replacement.** MAC address changes; chassis serial and SMBIOS
UUID do not. A straightforward case supporting Section 3's finding that
MAC alone must never be sufficient identity evidence. Should preserve
identity, if any Hardware-intrinsic evidence beyond MAC is available to
corroborate.

**Hostname changes.** A pure Human-assigned rename with no hardware or
OS-instance change. Should trivially preserve identity whenever any
Persistent/Immutable evidence still corroborates — the clean case
demonstrating why hostname must never be a required identity anchor,
since otherwise every rename would present as a new device.

**IP changes** (DHCP lease renewal, static reassignment). The
originating motivating case for this entire investigation (ARCH-014,
ADR-008's deferred Future Work). Should trivially preserve identity
whenever any Persistent-category evidence (MAC for infrastructure,
hostname, or stronger) still corroborates. This is also, per real-world
frequency, the single most common event any future resolver will
actually need to handle correctly — it is not an edge case among the
events evaluated here, it is the ordinary case.

**Virtualization migration** (live migration / vMotion). Designed by
the hypervisor platform to be transparent to the guest: SMBIOS UUID and
MoRef (within the same vCenter) are both explicitly preserved across
this event. One of the cleanest cases evaluated — strong evidence
survives this event by platform design, not by chance.

**Cloning.** Should **not** preserve identity in the general case — a
clone is correctly a new device that happens to share a point-in-time
evidence snapshot with its source. But Section 3 already found this is
not merely theoretical: improperly prepared VM templates are documented
to fail to regenerate SMBIOS UUID (and, on Windows guests, Machine GUID/
SID), producing two independently-running, independently-reachable
devices that legitimately report identical "immutable" identifiers. A
future identity model must be able to represent this as a genuine
**conflict** between two live devices (Section 7), not assume it away as
a data-quality bug to be silently resolved.

**Imaging** (OS reinstalled on unchanged physical hardware). The
clearest practical demonstration that asset identity and instance
identity diverge on a routine, real event: chassis serial and
(usually) MAC are unchanged, so this preserves identity **by asset**;
Machine GUID, `/etc/machine-id`, and AD machine SID are all regenerated,
so this does **not** preserve identity **by instance** — both answers
are simultaneously correct, for different questions, about the same
event.

**Cloud reprovisioning** (an instance or Entra/Arc device object
deleted and recreated). Behaves like Device Replacement, not like a
lifecycle event that preserves identity: nothing Hardware-intrinsic
persists, because there is no physical chassis at all. This is the
hardest case evaluated — cloud device identity has no available
asset-identity anchor in the traditional sense, only Provider-generated,
tenant-scoped identifiers (Section 3, Cloud) — meaning cloud identity
may need to be treated as a structurally different, weaker-anchored
category rather than assumed to fit the same model as on-prem hardware.
This investigation names the gap; it does not resolve it.

---

## 7. Corroboration Strategy

Per the charter, no numeric confidence score is introduced. This
investigation instead recommends directly reusing a pattern already
proven in the codebase: `first_matching_identifier`
(`networkmapper/classification/evidence_helpers.py:67-104`) checks an
ordered sequence of evidence types — product, HTTP title, TLS subject,
TLS issuer, HTTP auth realm, and (checked last, per RULE-004's
evidence-hierarchy principle) SNMP `sysDescr` — stopping at the first
match and returning which evidence type matched, so the caller can
explain *why* in terms of a named field, never a score. Identity
corroboration is the same shape one level up: an ordered check across
identity-evidence categories, strongest first, that produces an
explainable label rather than a number.

Consistent with Section 4's two-axis model, the ordering should check
Hardware-intrinsic/Immutable evidence before Persistent evidence before
Human-assigned/Contextual evidence — mirroring the same "stronger,
earlier-checked evidence wins" directional bias ARCH-013 Section 5
already found demonstrated independently at two other layers (ADR-010's
merge-layer fallback-only rule, RULE-004's classification-layer
evidence-hierarchy). This investigation is a third, independent
instance of the same convergent principle, not a new one.

A discrete-tier outcome, not a score, is recommended:

- **Confirmed** — two or more independent Hardware-intrinsic/Immutable
  observations agree (e.g., same chassis serial *and* same SMBIOS UUID).
- **Probable** — one Hardware-intrinsic/Persistent observation matches
  (e.g., same MAC on infrastructure-class hardware), or two independent
  Human-assigned/Contextual observations agree.
- **Weak** — only Human-assigned or Contextual evidence agrees (e.g.,
  hostname alone) — exactly the charter's own named example.
- **Conflicting** — Hardware-intrinsic/Immutable-category evidence
  *disagrees* between two candidate matches (e.g., same IP and hostname,
  but different chassis serial). Per ARCH-014 Section 5's already-
  established principle ("corroborate rather than override... retained,
  not silently resolved"), a Conflicting result must never be silently
  arbitrated — this applies to identity evidence exactly as it applies
  to relationship evidence, and Section 6's Cloning case shows this is a
  real scenario the architecture must represent, not a hypothetical one.

**A necessary refinement this investigation surfaces that
`first_matching_identifier`'s existing use case does not need:**
corroboration strength depends on the *independence* of the observations
being compared, not merely their count. Two fields that both originate
from the same underlying negotiation (for example, if a future WMI
provider's reported `Domain`/`ComputerSystem.Name` and a separately-
labeled "hostname" field both trace back to the identical WMI query)
would not constitute two independent confirmations, even though they
occupy two named fields. Evaluating independence requires knowing *how*
each observation was obtained, not just *what* it reports — which
requires the per-observation provenance ARCH-014 Section 6 already
recommended for relationship evidence (originating provider, method,
timestamp, retained per observation rather than collapsed). This
investigation finds the same provenance mechanism ARCH-014 already
motivated is a direct prerequisite for correct identity corroboration
too — a second, independent reason to build it, not a new requirement.

---

## 8. Architectural Recommendations

Findings offered for engineering review, not implemented or authorized.
Consistent with `ENGINEERING.md`'s AI Execution Policy, nothing below is
an approved architecture change.

1. **Treat canonical identity as an interpretation derived from
   retained identity evidence**, mirroring `device_type`'s evidence →
   interpretation shape (ADR-008) and ARCH-014's identical conclusion
   for relationships (Section 2). Recommend a future ADR formalize an
   `IdentityResult`-shaped concept, structurally analogous to
   `RuleResult` (ADR-002): a match/no-match outcome, a discrete
   corroboration tier (Section 7), and an explainable reason naming
   which evidence matched — never a bare boolean or a score.

2. **Never treat IP address, hostname, or computer name — alone — as
   sufficient to establish canonical identity.** Section 3's Identity
   Evidence Assessment and Section 6's Device Replacement case are the
   concrete justification: these fields are exactly the ones a
   technician deliberately keeps unchanged across a replacement, making
   them actively misleading as sole identity anchors, not merely weak
   ones.

3. **Identity evidence needs per-observation retention distinct from
   `Device`'s current collapsed, fallback-merged fields**, for the same
   reason ARCH-014 Section 6 already reached for relationship evidence:
   corroboration (Section 7) needs to inspect and count individual
   contributing observations, including their independence, which a
   single merged `Device` field cannot represent once collapsed. This
   investigation recommends whoever designs the eventual ADR strongly
   consider **one shared retained-observation/provenance mechanism**
   serving both identity evidence (this investigation) and relationship
   evidence (ARCH-014), rather than building two parallel ones for what
   is architecturally the same underlying need.

4. **Explicitly decide whether canonical device identity tracks asset
   identity, instance identity, or models both, before designing
   corroboration in detail.** Section 6 shows these diverge on routine,
   common events (reimaging preserves the former, not the latter;
   motherboard replacement is ambiguous depending on which hardware
   identifier is treated as canonical). This is a real design fork this
   investigation surfaces but does not resolve — recommend the future
   ADR make this decision explicitly rather than leaving it implicit in
   whichever evidence field happens to be checked first.

5. **Reuse `first_matching_identifier`'s ordered, deterministic,
   explainable evidence-hierarchy pattern for identity corroboration**
   (Section 7) rather than inventing a new resolution mechanism — a
   direct extension of an already-proven pattern, not new architecture.

6. **Corroboration strength must account for evidence independence, not
   just evidence count** (Section 7) — a second, independent motivation
   (beyond ARCH-014's own) for building the per-observation provenance
   mechanism recommendation 3 already calls for.

7. **Conflicting identity evidence must be retained and surfaced, never
   silently arbitrated** — the same posture ARCH-014 already established
   for relationship evidence (a second independent instance of the same
   principle), and directly motivated by a real, documented scenario
   (Section 6, Cloning) rather than a hypothetical one.

8. **Provider-independent identity should be assumed achievable for
   server/infrastructure-class hardware and explicitly not assumed
   universal.** Cloud instances and MAC-randomizing client endpoints may
   have no available Hardware-intrinsic anchor (Section 5); a future
   identity model should degrade to a lower corroboration tier for these
   cases rather than requiring a hardware anchor to function at all.

---

## 9. Technical Debt

Scoped to debt affecting maintainability, correctness, or extensibility
today, confirmed against current repository state — not created by this
investigation, only surfaced or reconfirmed by it.

**1. `NetworkGraph`'s IP-only device keying has no rescan-reconciliation
path in any form, confirmed directly in this investigation.**
`ProjectSerializer.load()` (`networkmapper/project/serializer.py:62`) is
called exactly once in the runtime, from `application.py:188`, solely to
verify a just-saved project round-trips correctly for a console
confirmation message — never to merge a new scan's results against a
previously persisted project. ADR-008's Future Work deferral of "a
mechanism for reconciling... rescans" is therefore not merely
unresolved in principle, as ADR-008 itself already stated, but confirmed
unimplemented in any form as of this investigation — a stronger,
directly-verified claim than ADR-008's own more general deferral.

**2. `Device.mac_address`, `hostname`, `computer_name`, and `domain` are
persisted and surfaced today as though they functioned as stable
identity**, while Section 3 finds none of them safe as sole identity
evidence under real, common lifecycle events. This is not a defect in
any shipped behavior — nothing currently claims these fields provide
canonical identity — but it is a latent risk for whichever future
rescan/merge feature (Technical Debt item 1) eventually consumes them
naively, and this investigation exists specifically so that feature
does not repeat the IP-address mistake with a different field.

**3. `ObservationDevice`'s docstring
(`networkmapper/knowledge/models.py:44-56`) names ip/hostname/vendor/
mac_address as "Stable device-identity fields," a claim this
investigation finds only partially accurate.** `vendor` in particular is
not identity evidence in any category evaluated here — it identifies a
NIC manufacturer, shared across every device using hardware from that
maker, structurally the same "identifies the model, not the unit"
problem this investigation found for SNMP `sysObjectID` (Section 5).
This is not counted as a defect in KNOW-003's own scope — the Knowledge
Framework uses these fields to recognize observations for human review,
a narrower and different purpose than canonical device identity — but it
is a naming/assumption mismatch worth reconciling explicitly once a
canonical identity model exists (Future Work), so a future reader does
not mistake KNOW-003's narrower usage for this investigation's broader
identity findings.

---

## 10. Future Work

Explicitly deferred, and not authorized by this investigation:

- The ADR formalizing canonical identity as a derived interpretation
  (Section 8, item 1) — requires its own sprint, following the
  ADR-009/ADR-010/ARCH-014 precedent.
- Design of the identity-evidence retention/provenance mechanism
  (Section 8, item 3) — recommended to be coordinated with, or shared
  with, ARCH-014's own deferred relationship-evidence provenance
  mechanism rather than designed twice.
- The explicit asset-identity-versus-instance-identity decision (Section
  8, item 4) — this investigation frames the fork; it does not resolve
  it.
- Any concrete provider-specific identity-collection design (WMI
  serial/UUID, Redfish chassis/UUID, SNMP ENTITY-MIB, SSH `dmidecode`/
  `machine-id`, AD/Entra correlation) — none designed here, per the
  charter.
- A rescan/merge mechanism that actually applies canonical identity once
  resolved — ADR-008's original deferred Future Work, now confirmed
  fully unimplemented (Section 9, item 1), still not designed here.
- Reconciling `ObservationDevice`'s "stable device-identity fields"
  docstring against this investigation's findings once a canonical
  identity model exists (Section 9, item 3).
- The relationship-evidence architecture ARCH-014 deferred pending this
  investigation — unblocked, per ARCH-014's own recommendation, once a
  future ADR formalizes canonical identity resolution.
