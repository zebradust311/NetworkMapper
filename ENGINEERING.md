# NetworkMapper Engineering Guide

**Version:** 0.4.0

---

# Project Philosophy

NetworkMapper exists to reduce the time, effort, and uncertainty required to understand an undocumented network.

Every architectural and implementation decision should support that mission.

NetworkMapper is being developed as a professional network discovery platform.

The goal is **not** to create another network scanner.

The goal is to build a portable application that discovers, understands, documents, and visualizes enterprise networks.

Every feature must provide real value to technicians working in customer environments.

NetworkMapper is not a network scanner.

It is a network relationship mapping platform.

The purpose of discovery is to build an accurate graph of the relationships between devices, networks, interfaces, and services.

All visualizations, reports, exports, and analytics are derived from that graph.

Every new capability should be validated with a real-world workflow before it becomes permanent.

The internal data model is the product.

Every export is a view of that model.

---

# Primary Design Goal

NetworkMapper should require as little manual input as possible.

The technician should provide the minimum information necessary to begin discovery.

The application should automatically discover all reachable networks and build a complete understanding of the environment.

---

# Core Principles

## 1. Build capabilities, not scripts.

Every phase should leave the application more capable than before.

Avoid writing one-off scripts.

---

## 2. Keep the application usable.

At the end of every sprint:

- The application runs.
- Existing functionality continues to work.
- New functionality is tested.
- Documentation is updated when appropriate.

---

## 3. Simplicity wins.

If two solutions solve the same problem:

Choose the solution that is easier to understand and maintain.

Readable code is more valuable than clever code.

---

## 4. One responsibility per class.

Examples:

Application → coordinates the application.

Discovery Engine → discovers devices.

NetworkGraph → stores discovered devices.

Project → owns the network graph.

Exporter → writes external representations.

---

## 5. Models contain data.

Models should not perform discovery.

Examples:

- Device
- Interface
- Link
- Network

---

## 6. Services perform work.

Examples:

- Discovery Engine
- Project Serializer
- Device Classifier
- Exporter
- Topology Engine

---

## 7. Everything starts with a real-world problem.

We only build features that solve actual technician workflows.

---

## 8. The software should never get in the technician's way.

Automation should reduce manual effort without reducing transparency.

---

## 9. Every bug that reaches validation must receive a regression test.

Fixes without tests are incomplete.

---

## 10. Routine inventory should remain fast.

Deep inspection belongs in optional enrichment tools.

---

# Architecture

```
main.py
    │
    ▼
Application
    │
    ▼
Project
    │
    ├── NetworkGraph
    ├── Metadata
    └── Scan History (future)
            │
            ▼
DiscoveryEngine
            │
            ▼
DiscoveryProviders
```

---

# Folder Structure

```
networkmapper/

    application.py

    core/

    discovery/

    classification/

    exporters/

    project/

    ui/

    developer/

    config/

tests/

docs/

examples/

benchmarks/

output/
```

---

# Coding Standards

## Python

- Use type hints.
- Prefer dataclasses for models.
- Prefer explicit names.
- Avoid global variables.
- Prefer dependency injection.

---

## Imports

Use absolute imports whenever practical.

Example:

```python
from networkmapper.core.models import Device
```

---

## Logging

Temporary validation utilities may use `print()`.

Production code should use the Logger service.

---

## Error Handling

Catch expected exceptions.

Allow unexpected exceptions to surface during development.

---

## Comments

Explain **why**, not **what**.

Bad:

```python
i += 1
```

Good:

```python
# Retry after transient network failures.
```

---

# Discovery

Providers contribute facts.

Discovery Engine merges those facts.

Discovery providers must never overwrite unrelated provider data.

---

# Classification

Classification must be:

- Deterministic
- Explainable
- Testable
- Ordered intentionally

Every classification rule must:

- Produce a RuleResult
- Include clear evidence
- Include focused unit tests
- Be registered intentionally
- Preserve first-match-wins behavior

Whenever practical, combine multiple independent observations while remaining fully explainable.

---

# Benchmarking

Benchmarking measures classifier quality.

Benchmark tooling must never change production classification behavior.

Benchmarks exist to measure:

- Accuracy
- Regression
- Coverage

Benchmark reports are developer tooling.

They are not part of production classification.

---

# AI-Assisted Development

AI accelerates implementation.

Humans remain responsible for architecture.

Implementation engineers do not make architecture decisions.

Architecture changes require explicit sprint approval.

When architectural uncertainty is discovered:

- stop
- report
- await direction

Every implementation sprint should have one objective.

Avoid unrelated cleanup.

Avoid opportunistic refactoring.

If additional work is discovered, report it separately.

---

# Sprint Workflow

The canonical sprint lifecycle is defined in
[docs/process/sprint-lifecycle.md](docs/process/sprint-lifecycle.md):
Investigation → Architecture Review → Implementation → Validation → Human
Review → Commit.

Never combine multiple unrelated objectives into one sprint.

See also [docs/process/engineering-principles.md](docs/process/engineering-principles.md)
and [docs/process/role-definitions.md](docs/process/role-definitions.md).

---

# Validation Workflow

Validation commands and when to use each — `validate`, `validate --all`,
`benchmark`, `diagnostics` — are defined in
[docs/process/validation-workflow.md](docs/process/validation-workflow.md).

---

# AI Execution Policy

AI assistants must:

- Read only required project files.
- Modify only sprint-scoped files.
- Update only directly affected tests.
- Run only the smallest appropriate regression target.
- Summarize results.
- Stop.

Never inspect IDE implementation files.

Never inspect:

- workspaceStorage
- chat-session-resources
- content.txt
- editor cache
- temporary transcript files

Never validate software behavior using IDE artifacts.

Project source files and current test execution are the authoritative sources.

Before implementation:

1. Read ROADMAP.md.
2. Verify the requested sprint has not already been implemented.
3. If a discrepancy is found:
   - stop
   - report the discrepancy
   - do not modify ROADMAP.md
   - do not implement duplicate work

See also [docs/process/stop-conditions.md](docs/process/stop-conditions.md) for
the complete, mandatory set of stop conditions, and
[docs/process/role-definitions.md](docs/process/role-definitions.md) for how
this policy maps onto the AI Investigator/Implementer/Reviewer roles.

---

# Developer Platform

The `devtools` package is the canonical interface for developer automation.

Developer workflows should be implemented through `devtools` rather than
standalone scripts or ad hoc command sequences.

Current commands include:

```text
python -m devtools validate

python -m devtools validate --all

python -m devtools benchmark

python -m devtools compare
```

`validate` runs the fast, classifier-only regression suite. `validate --all`
runs every test module and every benchmark dataset, discovered
automatically, without changing what `validate` alone does.

Future developer automation should extend this interface whenever practical.

Developer automation should:

- Reuse existing project services.
- Avoid duplicating production logic.
- Produce deterministic output.
- Be suitable for both human developers and AI assistants.

The Developer Platform exists to make engineering workflows repeatable,
measurable, and project-owned.

Future developer tooling should provide a Review Package suitable for architecture review.

A Review Package should include:

- Changed files
- Diagnostics summary
- Benchmark summary
- Compare summary
- Git status
- Git diff

The Review Package is the primary artifact for post-implementation architecture review.

---

# Architecture Policy

Do not modify architecture unless the sprint explicitly requires it.

Do not introduce compatibility layers unless they are part of an approved migration.

Do not refactor unrelated systems.

---

# Documentation

Architectural changes update:

- ROADMAP.md
- docs/architecture/
- docs/ADR.md

Implementation changes update documentation when appropriate.

---

# Git Workflow

Every completed sprint receives:

- One focused commit.
- One meaningful commit message.
- Appropriate regression tests.
- Updated documentation when necessary.
- A narrow implementation scope.

Avoid mixing unrelated work.

Good:

```
DEV-001: Add benchmark CLI

ACC-001: Add benchmark framework

INTEL-003: Expand Cisco heuristics
```

Bad:

```
Update

Fix

Stuff

Misc changes
```

---

# Development Phases

Phase 1 — Foundation

Phase 2 — Discovery

Phase 3 — Persistence

Phase 4 — Intelligence

Phase 5 — Enterprise Discovery

Phase 6 — Project Intelligence

Phase 7 — Exports

Phase 8 — MSP Workflows

Phase 9 — Production

---

# Definition of Done

A sprint is complete when:

- The application runs.
- The requested capability works.
- Existing functionality still works.
- Appropriate regression tests pass.
- Documentation has been updated.
- Changes have been reviewed.
- Changes have been committed.
- Changes have been pushed.

---

# Product Vision

NetworkMapper enables a technician to:

- Walk into a customer site.
- Discover the environment.
- Build a reusable project.
- Compare future discoveries.
- Produce professional documentation.

---

# Information Model

The NetworkGraph is the canonical representation of discovered information.

Discovery gathers facts.

Intelligence interprets facts.

Exporters present facts.

The Project is the source of truth.

---

# Deployment Philosophy

The final application should:

- Require no development tools.
- Run completely offline.
- Be distributed as a self-contained Windows executable.
- Require minimal configuration.

---

# Documentation First

Discovery is not the final product.

Documentation is.

---

# Data Philosophy

Projects are portable.

Projects are complete.

Projects should allow work to resume without rediscovery.

Open formats are preferred whenever practical.

---

# Evidence-Driven Engineering

Engineering decisions should be supported by measurable evidence whenever practical.

Sources of evidence include:

- Regression tests
- Benchmarks
- Diagnostics
- Architecture reviews
- Field observations

Avoid speculative implementation.

Benchmark before optimizing.

Measure before refactoring.

---

# Field Observations

Real-world technician observations are first-class engineering inputs.

Field observations should:

- identify the vendor
- identify the product
- describe the deployment environment
- describe the observed operational role
- avoid assumptions beyond observed behavior

Field observations should guide future benchmark datasets and classification improvements.

---

# Product Personas

## Technician

Needs:

- Discovery
- Troubleshooting
- Documentation
- Accurate inventory

---

## Account Manager

Needs:

- Managed device counts
- Inventory changes
- Billing deltas

---

## Customer

Needs:

- Documentation
- Network diagrams
- Asset inventory

Every feature should identify its primary audience.

---

# Engineering Philosophy

Every sprint should leave NetworkMapper:

- More capable
- Better tested
- Better documented
- Easier to maintain

Engineering quality is a feature.

Long-term maintainability is as important as new functionality.

Measure improvements whenever practical.

Benchmark before optimizing.

Prefer deterministic behavior over cleverness.

Prefer explainability over complexity.

---

## Architecture Reviews

Major milestones should conclude with an Architecture Review.

An Architecture Review should include:

- Executive Summary
- Completed Objectives
- Architecture Assessment
- Testing Assessment
- Documentation Assessment
- Technical Debt
- Risks
- Recommendations
- Overall Grade
- Approval Status

Architecture Reviews are intended to guide future engineering decisions,
not merely summarize completed work.

---

# Architectural Decision Records

Major architectural decisions should be recorded as Architecture Decision
Records (ADRs).

An ADR should capture:

- The problem being solved.
- The selected solution.
- Alternatives considered.
- Consequences of the decision.

Architecture Reviews evaluate the current state of the project.

ADRs explain why significant architectural decisions were made.

When practical, architectural changes should update:

- ROADMAP.md
- docs/architecture/
- docs/ADR.md

Architecture Reviews and ADRs complement one another and together provide the
historical context for future engineering decisions.

---

## Canonical Developer Commands

Implementation engineers should prefer these commands. See
[docs/process/validation-workflow.md](docs/process/validation-workflow.md) for
guidance on which validation command to use for a given sprint.

Validation (fast, classifier-only)

python -m devtools validate

Validation (comprehensive — every test module, every benchmark dataset)

python -m devtools validate --all

Diagnostics

python -m devtools diagnostics

Benchmark

python -m devtools benchmark

Comparison

python -m devtools compare

Review

python -m devtools review (planned)

---

## Sprint Scope

Every sprint has one primary objective.

Tests, documentation, and validation supporting that objective are encouraged.

Unrelated features, roadmap changes, and opportunistic cleanup belong in separate sprints.