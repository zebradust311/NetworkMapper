# Architecture Documentation

This directory contains architecture-focused documentation for NetworkMapper.

Its purpose is to explain the current system structure, subsystem responsibilities, component interactions, and data flow without duplicating code-level implementation details.

These documents complement the broader project references in the repository root and the main documentation set:

- [README.md](../../README.md) explains project purpose and current capabilities.
- [ENGINEERING.md](../../ENGINEERING.md) defines engineering principles and design constraints.
- [ROADMAP.md](../../ROADMAP.md) tracks completed milestones and planned work.
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md) provides an existing high-level architecture narrative.
- [docs/knowledge/](../knowledge/) explains how field observations mature into knowledge, benchmarks, and classification changes.

## Current Documents

- [overview.md](./overview.md)
  High-level overview of the implemented architecture, including subsystem responsibilities, interactions, and data flow.

- [classification.md](./classification.md)
  Architecture of the implemented classification subsystem, including rule evaluation, explainability, evidence exposure, and its relationship to benchmarking.

## Planned Documentation

The following architecture documents are planned and intentionally deferred. They are listed here to establish the documentation structure, not to imply that their content has already been written.

- `discovery.md` (planned)
  Intended to document the implemented discovery subsystem and provider boundaries.

- `benchmarking.md` (planned)
  Intended to document the implemented benchmarking and benchmark-reporting architecture.

- `developer-platform.md` (planned)
  Intended to document the implemented developer tooling, including `networkmapper.developer` and `devtools`.

## Documentation Scope

Architecture documents in this directory describe implemented behavior only.

They should:

- explain responsibilities and boundaries
- describe how subsystems interact
- describe data flow and source-of-truth relationships
- cross-reference existing documentation when that document already answers a different question well

They should not:

- speculate about planned architecture
- restate individual methods or functions
- duplicate roadmap content
- describe code that does not exist