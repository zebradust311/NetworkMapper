# NetworkMapper Roadmap

> Last Updated: July 2026

---

# Vision

NetworkMapper is a professional network relationship mapping platform.

The goal is to enable technicians to:

- Discover unfamiliar networks
- Understand device relationships
- Produce professional documentation
- Compare environments over time
- Generate reusable project files

NetworkMapper is not simply a network scanner.

The Project and NetworkGraph are the product.

Everything else is derived from them.

---

# Project Status

## Completed

- Foundation architecture
- Project model
- Discovery framework
- Persistence
- Explainable classification
- Benchmark framework
- Benchmark analytics
- Engineering documentation
- Knowledge framework
- Canonical reporting

---

# Phase 1 — Foundation ✅

## Core Architecture

- ✅ Application framework
- ✅ Project model
- ✅ NetworkGraph
- ✅ Device model
- ✅ Interface model
- ✅ Link model
- ✅ Metadata model

## Persistence

- ✅ Project serialization
- ✅ Project loading
- ✅ JSON persistence

## Discovery

- ✅ Discovery engine
- ✅ Discovery provider framework
- ✅ Provider abstraction

---

# Phase 2 — Classification ✅

## Rule Framework

- ✅ CLASS-001 Rule framework
- ✅ CLASS-002 Rule ordering
- ✅ CLASS-003 Rule registration
- ✅ CLASS-004 Rule contracts
- ✅ CLASS-005 Rule testing
- ✅ CLASS-006 Rule cleanup
- ✅ CLASS-007 RuleResult migration

## Explainable Classification

- ✅ EVID-001 Evidence API
- ✅ RuleResult
- ✅ Per-rule evidence
- ✅ Classification workbench

---

# Phase 3 — Intelligence (Phase 1) ✅

## Heuristic Improvements

- ✅ INTEL-001 RuleResult migration
- ✅ INTEL-002 Expanded heuristics
- ✅ INTEL-003 Multi-evidence classification

Current classifier characteristics:

- Deterministic
- Explainable
- First-match-wins
- Evidence driven
- Fully regression tested

---

# Phase 4 — Developer Tooling

## Benchmark System ✅

- ✅ ACC-001 Benchmark framework
- ✅ ACC-002 Benchmark reports
- ✅ ACC-003 Accuracy analytics
- ✅ ACC-004 Misclassification analytics
- ✅ ACC-005 Confusion matrix

Current benchmark capabilities:

- Overall accuracy
- Device type accuracy
- Misclassification reporting
- Confusion matrix
- Markdown reports
- JSON reports
- Console reports

## Developer Utilities

- ✅ DEV-001 Benchmark CLI

### Planned

- ⬜ DEV-002 Shared evidence helper library
- ⬜ DEV-003 Benchmark comparison utility
- ⬜ DEV-004 Benchmark trend reports
- ⬜ DEV-005 Benchmark dataset validator

---

# Knowledge Framework ✅

## Foundation

- ✅ KNOW-001 Knowledge Framework
- ✅ KNOW-002 Vendor Knowledge Foundation

Establishes how operational knowledge enters, matures within, and influences
NetworkMapper.

Current knowledge documentation:

- Knowledge overview and purpose
- Canonical field observation format
- Reusable observation template
- Observation-to-architecture-review lifecycle
- Vendor Knowledge subsystem overview
- Reusable vendor document template

See [docs/knowledge/](docs/knowledge/) for the current documents.

---

# Phase 5 — Intelligence (Phase 2)

Focus shifts from building heuristics to improving them using benchmark data.

## Planned

- ⬜ INTEL-004 Targeted heuristic improvements
- ⬜ INTEL-005 Shared hostname matching
- ⬜ INTEL-006 Shared vendor matching
- ⬜ INTEL-007 Shared service matching
- ⬜ INTEL-008 Shared port matching
- ⬜ INTEL-009 Confidence diagnostics (reporting only)

---

# Phase 6 — Discovery Expansion

## Planned

### Discovery Providers

- ⬜ SNMP enrichment (architected — ARCH-012/ADR-010; implementation not started)
- ⬜ LLDP discovery
- ⬜ CDP discovery
- ⬜ ARP enrichment
- ⬜ mDNS discovery
- ⬜ DNS enrichment
- ⬜ NetBIOS enrichment

### Device Enrichment

- ⬜ Operating system fingerprinting
- ⬜ MAC vendor enrichment
- ⬜ Service fingerprinting
- ⬜ Interface enrichment

---

# Phase 7 — Visualization

## Planned

- ⬜ Interactive topology viewer
- ⬜ Automatic layout
- ⬜ Draw.io export improvements
- ⬜ Visio export
- ⬜ SVG export
- ⬜ PDF topology export

---

# Phase 8 — Documentation

## Reporting Foundation

- ✅ REPORT-001 Canonical Discovery Report

Establishes the Markdown report as NetworkMapper's canonical
human-readable output of a discovery and classification run. Documents,
retroactively, the completed reporting deliverables: Markdown report
generation, CSV export, Discovery Summary, Classification Summary,
per-device evidence, discovery diagnostics, and human-readable report
formatting. See
[docs/reports/REPORT-001-Evidence-Rich-Engineering-Report.md](docs/reports/REPORT-001-Evidence-Rich-Engineering-Report.md)
for the implementation detail.

### Planned

- ⬜ REPORT-002 Versioned reports, historical report preservation, and
  run-to-run comparison support

## Planned

- ⬜ Asset inventory reports
- ⬜ Executive reports
- ⬜ Site documentation package
- ⬜ VLAN documentation
- ⬜ Interface documentation
- ⬜ Device summaries

---

# Phase 9 — Project Intelligence

## Planned

- ⬜ Historical comparison
- ⬜ Project diff
- ⬜ Change tracking
- ⬜ Device lifecycle
- ⬜ Configuration drift detection

---

# Phase 10 — Enterprise Features

## Planned

- ⬜ Multi-site projects
- ⬜ Customer management
- ⬜ Site grouping
- ⬜ Enterprise reporting
- ⬜ Role-based workflows

---

# Phase 11 — Production

## Planned

### Packaging

- ⬜ Standalone Windows executable
- ⬜ Installer
- ⬜ Automatic updates

### Performance

- ⬜ Discovery optimization
- ⬜ Large network optimization
- ⬜ Memory optimization

### Quality

- ⬜ Full regression suite
- ⬜ Continuous benchmarking
- ⬜ Release validation

---

# Engineering Goals

Every sprint should improve one of:

- Capability
- Maintainability
- Performance
- Accuracy
- Documentation

---

# Development Workflow

Every sprint follows:

1. Planning
2. Implementation
3. Focused tests
4. Focused regression
5. Human review
6. Commit
7. Push

---

# Current Priority

## Next Sprint

DEV-002 was completed as part of the DEV-003 sprint (shared evidence helpers
landed alongside the developer automation framework) but was never marked
complete here.

FEAT-003G (HTTP Authentication Realm discovery) is complete.

FEAT-003H (SMB Identity Discovery — SMB OS Discovery + SMB Security
Mode, filed as FEAT-003H rather than ARCH-003's provisional "FEAT-003G"
label, which FEAT-003G's own sprint claimed first) is complete.
`smb2-time` was considered and excluded — ARCH-003's original
description of it as a source of SMB2 dialect evidence was a factual
error, corrected during FEAT-003H implementation; the script reports
only server date/time, which has no classification consumer.

FEAT-003I (RDP NTLM Identity Discovery, ARCH-003 Tier 3) is complete.
`rdp-ntlm-info` populates the same `Device.operating_system`/
`computer_name`/`domain` fields SMB discovery already populates
(FEAT-003H), with SMB preferred field-by-field when both sources are
present — RDP only fills in fields SMB left empty. No classification
rule changes were needed: `ServerHostnameRule`/`HypervisorHostnameRule`
already corroborate on `Device.operating_system` generically, regardless
of which discovery path produced it.

Per ARCH-003's roadmap, this completes Tiers 1–3 (the passive
HTTP/TLS/SMB/RDP identity work). Tier 4 (SNMP `sysDescr`/`sysObjectID`)
was the next candidate, previously blocked on confirming and fixing the
`-sU` UDP scanning gap first (see ARCH-003 Section 2.7).

ARCH-012 (SNMP Provider Architecture) is complete and approved. It found
SNMP needs a provider role the existing `DiscoveryProvider` contract
can't safely express (enrichment of already-discovered hosts, not host
discovery), and recommended a new `EnrichmentProvider` abstraction —
formalized as ADR-010. Scope for the first implementation is
SNMPv2c-only, the MIB-2 system group (`sysDescr`/`sysObjectID`/`sysName`/
`sysUpTime`/`sysContact`/`sysLocation`), explicit opt-in (not bundled
into FAST/STANDARD/DEEP), and runtime-only credentials never persisted
to reports, projects, or the knowledge repository. SNMPv3 and interface/
topology evidence are explicitly deferred to later, independently
reviewed sprints. Next sprint: FEAT-005 (`EnrichmentProvider` +
`SnmpEnrichmentProvider` per ARCH-012) — see ARCH-012's Open Questions
for what still needs deciding before implementation starts (notably,
which SNMP client library to standardize on).

See `docs/reports/` for recent investigation and implementation history.

---

# Long-Term Vision

NetworkMapper should become the easiest professional tool for:

- Discovering networks
- Understanding infrastructure
- Producing documentation
- Tracking change
- Managing customer environments

using a single reusable Project model.

---

# Definition of Success

NetworkMapper should allow a technician to:

1. Walk into an undocumented network.
2. Discover the environment.
3. Understand relationships.
4. Produce professional documentation.
5. Return months later and compare changes.

Everything in the project should support that workflow.