+------------------------------------------------------+
|                  NetworkMapper                       |
|------------------------------------------------------|
|                                                      |
|      [ Network Topology Diagram Screenshot ]         |
|                                                      |
+------------------------------------------------------+

# NetworkMapper

> Automatically discover, understand, and document networks with little or no existing documentation.

---

# Overview

NetworkMapper is a professional network discovery, inventory, and documentation platform designed for technicians, consultants, and managed service providers.

Its purpose is to rapidly discover customer environments, build an accurate understanding of the relationships between devices, networks, interfaces, and services, and generate professional documentation that can be maintained throughout the customer lifecycle.

The goal is simple:

> **Walk into an unfamiliar network and leave with documentation that didn't exist when you arrived.**

---

# Why NetworkMapper?

One of the biggest challenges technicians face is a lack of documentation.

Common scenarios include:

- "The previous IT guy retired."
- "We don't have a network diagram."
- "I think it's in that closet."
- "Everything just connects to Wi-Fi."

Instead of spending hours manually tracing connections and building diagrams from scratch, NetworkMapper automatically discovers the environment and creates the foundation for professional network documentation.

---

# Project Philosophy

## Minimal Input. Maximum Discovery.

The technician should provide as little information as possible.

NetworkMapper should discover everything it can automatically.

---

## Assume Zero Documentation.

The application should never require existing documentation.

If documentation already exists, it should enhance discovery—not be required for it.

---

## Function Over Form.

The discovery engine comes first.

A polished graphical interface will follow once the core functionality has been proven.

---

# Vision

NetworkMapper is **not** simply a network scanner.

It is a **network relationship mapping platform**.

Discovery gathers facts.

Classification interprets those facts.

The reusable Project becomes the source of truth for documentation, reporting, visualization, and future analysis.

```
Discover
        │
        ▼
Understand
        │
        ▼
Document
        │
        ▼
Maintain
        │
        ▼
Compare
```

The long-term goal is to help technicians understand unfamiliar environments quickly while producing documentation that continues to provide value long after the initial site visit.

---

# Current Capabilities

## Discovery

- Multi-provider discovery architecture
- Offline project workflow
- Portable project files
- Network inventory generation

### Classification

- Deterministic rule-based classifier
- Explainable RuleResult framework
- Evidence-driven classification
- Multi-evidence heuristics
- Classification workbench
- Per-rule evidence reporting

### Documentation

- Markdown inventory export
- CSV export
- JSON project serialization

### Benchmarking

- Benchmark framework
- Benchmark CLI
- Accuracy measurement
- Regression datasets

---

# Project Architecture

Everything in NetworkMapper is built around a reusable project model.

```
Discovery Providers
          │
          ▼
Discovery Engine
          │
          ▼
Project
          │
          ▼
NetworkGraph
          │
          ├── Devices
          ├── Networks
          ├── Interfaces
          ├── Links
          └── Metadata
                  │
                  ▼
Classification
                  │
                  ▼
Exports / Reports / Visualizations
```

The Project is the canonical representation of the discovered environment.

Discovery gathers facts.

Classification interprets those facts.

Exporters present those facts.

---

# Current Development Status

NetworkMapper is under active development.

Recent milestones include:

- Explainable device classification
- RuleResult framework
- Evidence API
- Classification workbench
- Multi-evidence classification heuristics
- Benchmark framework
- Benchmark CLI
- Regression testing infrastructure

Current development focuses on:

- Benchmark reporting
- Classification analytics
- Enterprise discovery
- Historical comparison
- Visualization

See **ROADMAP.md** for upcoming milestones.

---

# Planned Features

- Automatic network discovery
- Nmap-based host detection
- Device identification
- Network relationship mapping
- Draw.io topology generation
- Device inventory export
- Change detection between scans
- Professional documentation package generation
- Offline operation
- Portable Windows executable

---

# Intended Users

NetworkMapper is designed for:

- Managed Service Providers (MSPs)
- Network Engineers
- Field Technicians
- IT Consultants
- Systems Administrators

---

# Documentation

| Document | Purpose |
|----------|---------|
| ENGINEERING.md | Engineering philosophy and development workflow |
| ROADMAP.md | Project roadmap |
| docs/AI-DEVELOPMENT-GUIDE.md | AI-assisted development workflow |
| docs/architecture/ | Architecture documentation |
| docs/ADR.md | Architectural Decision Records |
| docs/classification-rules.md | Classification rule reference |
| docs/DEPENDENCIES.md | Project dependencies |
| docs/field-notes.md | Real-world networking observations |

---

# Repository Structure

```
NetworkMapper/

├── benchmarks/
├── docs/
├── examples/
├── networkmapper/
├── output/
├── scans/
├── tests/

├── ENGINEERING.md
├── README.md
├── ROADMAP.md
└── requirements.txt
```

---

# Development Workflow

NetworkMapper is developed using small, focused engineering sprints.

Each sprint follows the same workflow:

1. Plan one objective.
2. Implement one capability.
3. Add focused regression tests.
4. Run the smallest appropriate validation target.
5. Perform human architectural review.
6. Commit.
7. Push.

Architecture remains under human review.

---

# AI-Assisted Development

NetworkMapper is developed with AI-assisted engineering.

AI accelerates implementation.

Humans remain responsible for:

- Architecture
- Scope
- Design
- Code review
- Acceptance

See:

```
docs/AI-DEVELOPMENT-GUIDE.md
```

for the complete development methodology.

---

# Engineering Principles

NetworkMapper emphasizes:

- Deterministic behavior
- Explainable decisions
- Regression testing
- Benchmark-driven improvements
- Long-term maintainability
- Documentation-first engineering

---

# Benchmarks

Classification quality is measured using curated benchmark datasets.

Example:

```
benchmarks/

    homelab/

    enterprise/

    small_office/
```

Benchmark reports measure:

- Accuracy
- Correct classifications
- Incorrect classifications
- Regression performance

---

# Contributing

Before contributing, please review:

1. ENGINEERING.md
2. docs/AI-DEVELOPMENT-GUIDE.md
3. docs/architecture/
4. ROADMAP.md

These documents define the engineering standards expected for all contributions.

---

# Design Goals

NetworkMapper should:

- Require minimal configuration.
- Operate completely offline.
- Produce professional documentation.
- Be understandable by technicians.
- Be maintainable by engineers.

---

# Long-Term Vision

The long-term goal is to build a professional network relationship mapping platform capable of:

- Discovery
- Documentation
- Inventory
- Visualization
- Change tracking
- Historical comparison
- Enterprise reporting

using a single reusable project model.

---

# License

This project is currently under active development.

Licensing will be finalized prior to the first public production release.