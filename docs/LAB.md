# NetworkMapper Lab

**Status:** Active Research  
**Purpose:** Product Research & Long-Term Vision  
**Implementation Status:** No roadmap commitment  
**Owner:** Engineering

---

# Mission

NetworkMapper Lab is the research branch of the NetworkMapper project.

Its purpose is to explore future capabilities, workflows, and companion
tools without affecting the implementation roadmap.

Ideas recorded here are observations, hypotheses, and product concepts.

They are **not** approved features.

Nothing in this document represents a commitment to implement.

Ideas graduate into the implementation roadmap only after architectural
investigation, engineering review, and an explicit roadmap decision.

---

# Guiding Philosophy

The Lab exists to answer one question:

> **What problems are worth solving for MSPs and IT professionals?**

The implementation project answers a different question:

> **How should those problems be solved?**

The Lab intentionally separates exploration from execution.

---

# Current Project State

The implementation project has completed Phase 2.

The current architecture provides:

- Canonical evidence model
- Deterministic rule engine
- Knowledge repository
- Runtime telemetry
- Discovery Provider architecture
- Enrichment Provider architecture
- SNMP enrichment
- Benchmark-driven engineering
- Customer-facing reporting
- Versioned project serialization
- Canonical identity and relationship resolution, wired into the runtime
  (FEAT-009B) — single-scan only; cross-scan/cross-subject correlation
  remains open research (see Stable Device & Identity Correlation, below)

The Lab assumes this architectural foundation already exists.

The purpose of the Lab is **not** to redesign it.

---

# Promotion Process

Ideas mature through the following lifecycle:

```text
Customer Problem
        │
        ▼
Research
        │
        ▼
Discussion
        │
        ▼
Architectural Investigation
        │
        ▼
ADR
        │
        ▼
Roadmap
        │
        ▼
Implementation
```

Ideas remain in the Lab until they become the highest-value justified
engineering decision.

---

# Engineering Principles

The Lab follows the same engineering philosophy as NetworkMapper itself.

## Evidence before conclusions

Avoid assumptions.

Prefer measurable observations.

---

## Solve problems, not features

Document customer pain before proposing solutions.

---

## Preserve ideas

Interesting ideas should never be discarded simply because they are not
appropriate for the current roadmap.

---

## No implementation bias

The Lab should remain implementation-agnostic whenever practical.

Avoid discussing classes, APIs, protocols, or sprint planning unless they
are necessary to evaluate an idea.

---

## Deterministic over magical

Future ideas should favor explainable, deterministic systems over opaque
automation.

---

## Architecture earns implementation

Ideas do not become roadmap items because they are exciting.

They become roadmap items because they represent the highest-value,
architecturally justified engineering decision.

---

# Research Categories

## Customer Lifecycle Management

**Problem**

Customers often have little visibility into unsupported operating systems,
aging infrastructure, obsolete firmware, or approaching vendor end-of-support.

Potential research topics:

- Windows lifecycle intelligence
- Server lifecycle intelligence
- Network equipment lifecycle
- Firmware lifecycle
- Vendor support tracking

Questions:

- What evidence is required?
- How can lifecycle data remain accurate?
- What information is most valuable to technicians?
- What information is most valuable to customers?

---

## Customer Onboarding

**Problem**

Inherited customer environments frequently contain incomplete documentation,
unknown administrative access, inconsistent naming, and aging infrastructure.

Potential research topics:

- Access Assessment
- Configuration collection
- Documentation generation
- Environment baselining
- Inventory validation
- Credential intake and transition handoff (see Credential Intake
  Companion Utility)

Questions:

- Which information saves technicians the most time?
- Which tasks consume the largest amount of onboarding effort?
- Which findings are currently manual?

---

## Asset Intelligence

**Problem**

Discovery identifies devices.

Customers ultimately care about the operational significance of those devices.

Potential research topics:

- Operating system inventory
- Firmware inventory
- Hardware inventory
- Virtualization inventory
- Warranty tracking
- Lifecycle reporting

Questions:

- Which evidence creates meaningful operational insight?
- Which evidence supports planning?
- Which evidence supports budgeting?

---

## Stable Device & Identity Correlation

**Problem**

Discovery today keys visibility to point-in-time, transient signals —
most notably IP address. A laptop that receives a new IP on DHCP
renewal, a server that is reimaged, or a device rescanned weeks later
can each appear to be a brand-new device rather than the one already
known. This undermines every capability that assumes continuity
discovery does not currently guarantee: multi-visit onboarding, asset
lifecycle tracking, warranty/support-window reporting, and executive
trend reporting all depend on recognizing "the same asset" over time.

The engineering foundation for addressing this — retained observations
and a first, single-scan canonical identity interpretation — already
exists. That foundation deliberately stops at grouping evidence within
one scan; it does not attempt to recognize the same real-world device
across different subjects (different IPs, different scans, different
visits), and it assigns nothing resembling a durable identifier.

Potential research topics:

- Cross-subject correlation: recognizing that two different
  discovery-time references (e.g., two IP addresses seen weeks apart)
  describe the same underlying device.
- Stable, durable canonical identity — an identifier for "this device"
  that survives rescans, IP changes, and hostname changes, independent
  of any single scan's transient references.
- What "the same device" should mean when physical/asset continuity and
  software/instance continuity genuinely diverge (a reimaged PC, a
  cloned VM, a replaced NIC) — whether the product needs one answer or
  must expose both.
- How correlation confidence should be communicated to a technician when
  evidence is incomplete or contradictory, without implying certainty
  the evidence doesn't support.
- Multi-visit and long-term project workflows: what a technician should
  see when returning to a customer environment after weeks or months.

Questions:

- Which customer workflows are actually blocked by the lack of stable
  identity today, versus merely inconvenienced?
- How much correlation risk (a false match — treating two different
  devices as one) is acceptable relative to the cost of
  under-correlation (a technician re-documenting the same device
  repeatedly)?
- Should a canonical identity ever be asserted automatically, or should
  early correlation always require technician confirmation?
- What would make a technician trust a "this is the same device" claim
  enough to act on it?

---

## Executive Reporting

**Problem**

Technical reports often communicate implementation details rather than
business impact.

Potential research topics:

- Executive summaries
- Lifecycle dashboards
- Upgrade planning
- Infrastructure health
- Risk summaries
- Transition and handoff documentation exports (see Credential Intake
  Companion Utility)

Questions:

- Which metrics matter to decision makers?
- Which findings require no technical explanation?
- How can technical evidence support business decisions?

---

## Knowledge Expansion

**Problem**

The Knowledge Repository currently focuses on classification.

Future opportunities may extend knowledge into operational intelligence.

Potential research topics:

- Hardware model database
- Firmware recommendations
- Vendor lifecycle information
- Product family identification
- Credential-group data modeling (see Credential Intake Companion Utility)

Questions:

- Which knowledge should be curated?
- Which knowledge should remain runtime observations?
- How should knowledge be versioned?

---

## Companion Utilities

**Problem**

Not every operational workflow belongs inside NetworkMapper.

Potential research topics:

- Access Assessment
- Configuration Collector
- Change Auditor
- Fleet comparison
- Multi-site management
- Credential Intake Companion Utility (see below)

Questions:

- Does this belong inside NetworkMapper?
- Should this become a companion utility?
- Would separation improve maintainability?

---

## Credential Intake Companion Utility

**Problem**

MSP onboarding and offboarding transitions routinely surface credential
information in inconsistent, unstructured formats — Word documents, Excel
workbooks, CSVs, PDFs, email attachments, scanned or handwritten notes, and
files scattered across mapped drives, SMB shares, or SharePoint libraries.
Technicians currently absorb the cost of finding, reading, and manually
transcribing this material. Credential handling is also a distinct security
boundary and should not be casually merged into NetworkMapper's discovery
and reporting responsibilities.

This concept explores whether a **separate, in-house companion
application** — not a NetworkMapper subsystem — could reduce this workload
while keeping credential handling architecturally isolated from
NetworkMapper's core credential-handling code.

**Concept**

NetworkMapper would expose a simple UI button, "Credential Intake," that
launches the companion utility and passes only non-secret context:

- Customer ID
- Project ID
- Site ID
- Device IDs
- Technician identity
- Authorization scope

No credential values would pass through NetworkMapper. The utility is a
distinct security boundary with its own launch contract, not a feature of
NetworkMapper's credential-handling code.

**Candidate source discovery**

The utility would scan only technician-selected and explicitly authorized
roots, and place discovered files into a technician review queue rather
than importing anything automatically. Candidate sources would be
identified using explainable signals: filename, folder path, file type,
spreadsheet sheet names, column headers, document headings, metadata, and
prior processing history.

Each queue item would show file name, source location, file type, modified
date, reason it was selected, confidence, review status, and processing
history. The technician could inspect, accept, reject, defer, or mark a
source as already processed.

**Evidence-first processing**

The utility would follow the same evidence-first, explainable principles as
NetworkMapper's discovery engine:

```text
Selected source
    ↓
Parser/OCR provider
    ↓
Candidate evidence
    ↓
Normalization and correlation
    ↓
Deterministic confidence and conflict rules
    ↓
Technician review
    ↓
Accepted credential group
    ↓
Keeper and documentation exports
```

Extracted values would remain observations until a technician confirms
them. If the same account appears with multiple different password
candidates, the system must surface a conflict rather than silently
selecting one — for example: "Administrator@Firewall — three password
candidates found; source dates conflict; technician decision required."

**Credential grouping**

The preferred model is credential-centric rather than application-centric.
Exact repeated username/password observations would group into one
credential group with multiple associated locations — for example, a
single `admin@xyz.com` group referencing Microsoft 365, Active Directory, a
Hyper-V host, and an RMM platform as separate locations rather than four
unrelated records.

The system would need to:

- Group exact repeated username/password observations
- Preserve every source reference
- Maintain a list of associated locations
- Track validation status per location
- Track observed dates
- Detect conflicting values
- Distinguish the same username with different passwords as separate
  credential versions or groups
- Avoid forcing the technician to assign every occurrence to one
  application
- Never assume a credential observed in one location is valid everywhere
  else

**Offline AI assistance**

An offline, local AI model could help contextualize and format extracted
information into coherent tables — mapping inconsistent labels to
username/password/URL/hostname/location, suggesting credential-group
membership or duplicate relationships, highlighting missing fields,
formatting records into structured JSON, and explaining confidence and
conflicts.

The AI would be an optional suggestion layer, never the security boundary
and never the authority on credential validity. It must run
locally/offline, produce structured output with confidence and reasoning,
never silently resolve conflicts, never determine whether a credential is
valid, never bypass technician review, use only synthetic or redacted data
for training or tuning, and have a deterministic fallback if unavailable.

GobboNet may be worth evaluating as an experimental local-model frontend or
benchmark target, but it should not be treated as a production security
boundary without additional review, hardening, and integration work.

**Export targets**

Eventual export targets could include a Keeper-compatible JSON/CSV import,
an XLSX workbook for documentation and OneNote insertion, an encrypted
credential handoff PDF, a customer transition runbook, and a non-secret
audit and evidence report. Native `.one` generation is not required for an
initial design; an XLSX workbook is a simpler first documentation output.

A documentation workbook might include sheets such as Executive Summary,
Sites and Network, Main Topology, VLAN Inventory, Assets and
Infrastructure, Administrative Access, Credential Groups, Services and
Dependencies, Backup and Recovery, Risks and Open Issues, Transition
Checklist, and Evidence Sources. A Main Topology sheet would show primary
structure only — major sites, WAN links, firewalls, core/distribution
switches, major servers, and VLAN relationships — not every endpoint.

**Security and lifecycle requirements**

This is strictly for authorized customer transitions. Research here would
need to cover explicit authorization and scope, secure temporary staging,
keeping secret values out of logs, telemetry, crash dumps, and ordinary
NetworkMapper evidence, protected handling of OCR output, separate
encryption-key delivery, recipient verification, audit logging without
exposing secret values, defined retention and destruction, credential
rotation after handoff, and deletion of working copies after confirmed
transfer. NetworkMapper should not retain live credentials unless
contractually required — the credential utility must remain a separate
security boundary from NetworkMapper's core credential-handling code.

Potential research topics:

- Source discovery across files, documents, and authorized shares
- File and document parsing, and OCR requirements for scanned or
  handwritten notes
- Credential-group data modeling
- Offline AI benchmarking (including GobboNet as an experimental target)
- Technician review workflow
- Keeper and XLSX export design
- Secure handoff lifecycle and retention/destruction rules
- NetworkMapper launch/context contract (non-secret handoff only)
- Documentation/reporting model shared with executive reporting
- Threat model for the companion utility as a distinct security boundary

Questions:

- Which minimal changes, if any, does NetworkMapper need now — such as a
  launch contract or non-secret context passing — to avoid a costly
  retrofit later if this graduates?
- What does "confidence" mean for an OCR- or parser-derived credential
  candidate, and how should conflicting candidates be presented?
- How should the utility prove it never becomes a second, informal
  credential store inside NetworkMapper?
- What would an ADR need to establish before any code is written — data
  model, launch contract, or threat model first?

If this concept eventually leaves the Lab, it is expected to enter as a
distinct **research and architecture workstream** — tentatively,
"Credential Intake Companion Utility — Feasibility and Architecture" —
producing architecture investigation, ADR candidates, data-model
recommendations, launch-contract recommendations, a synthetic-document
benchmark plan, parser/OCR/AI feasibility results, export-format prototype
recommendations, and identification of any minimal NetworkMapper-side
changes needed to avoid a future retrofit. This is a research and
architecture proposal only — not a production implementation commitment,
and not a roadmap placement.

---

# Parking Lot

Ideas that appear promising but are not yet mature enough for investigation.

Examples:

- AI-assisted summaries
- Predictive maintenance
- Compliance reporting
- Configuration drift analysis
- Automated remediation suggestions
- Offline/local AI credential contextualization (see Credential Intake
  Companion Utility)

No implementation planning should occur until these ideas have matured
through research.

---

# Graduated Ideas

This section records ideas that have left the Lab and entered formal
engineering.

| Idea | Promoted To | Status |
|------|-------------|--------|
| *(None yet)* | | |

---

# Working Rules

The Lab is intentionally optimistic.

Ideas are encouraged to be ambitious.

The purpose of the Lab is to preserve valuable insights while separating
research from implementation.

Not every idea should become a roadmap item.

No worthwhile idea should be lost because the current roadmap is focused
elsewhere.

---

# Definition of Success

A successful Lab entry does **not** produce code.

A successful Lab entry produces:

- Better understanding
- Better questions
- Better architectural direction
- Better future engineering decisions

The implementation project exists to build software.

The Lab exists to determine **what is worth building.**