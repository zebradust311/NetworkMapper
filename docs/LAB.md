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

Questions:

- Does this belong inside NetworkMapper?
- Should this become a companion utility?
- Would separation improve maintainability?

---

# Parking Lot

Ideas that appear promising but are not yet mature enough for investigation.

Examples:

- AI-assisted summaries
- Predictive maintenance
- Compliance reporting
- Configuration drift analysis
- Automated remediation suggestions

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