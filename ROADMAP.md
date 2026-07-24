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

- ⬜ SNMP enrichment
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

**DEV-002 — Shared Evidence Helper Library**

Goals:

- Eliminate duplicated rule helper logic
- Preserve all classifier behavior
- Preserve RuleResult evidence
- Reduce maintenance cost
- Improve consistency

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