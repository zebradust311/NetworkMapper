# NetworkMapper Engineering Guide

**Version:** 0.1.0

---

# Project Philosophy

NetworkMapper exists to reduce the time, effort, and uncertainty required to understand an undocumented network. Every architectural and implementation decision should support that mission.

NetworkMapper is being developed as a professional network discovery platform.

The goal is **not** to create another network scanner.

The goal is to build a portable application that discovers, understands, documents, and visualizes enterprise networks.

Every feature must provide real value to technicians working in customer environments.

NetworkMapper is not a network scanner.

It is a network relationship mapping platform.

The purpose of discovery is to build an accurate graph of the relationships between devices, networks, interfaces, and services. All visualizations, reports, and exports are derived from that graph.

Every new capability should be validated with a real-world workflow before it becomes permanent.

The internal data model is the product. Every export is a view of that model.

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

At the end of every phase:

- The application must run.
- Existing functionality must continue to work.
- New functionality must be tested.

---

## 3. Simplicity wins.

If two solutions solve the same problem:

Choose the one that is easier to understand and maintain.

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

Device

Interface

Link

Network

---

## 6. Services perform work.

Examples:

Discovery Engine

Project Serializer

Device Classifier

Exporter

Topology Engine

---

## 7. Everything starts with a real-world problem.

We only build features that solve actual technician workflows.

---

## 8. The software should never get in the technician's way.

---

## 9. Every bug that reaches a validation environment should be accompanied by a regression test before it is fixed.

---

## 10. Routine inventory should remain fast, deterministic, and minimally intrusive. Deep inspection belongs in optional utilities that can enrich a project without slowing the core workflow.

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

    exporters/

    project/

    ui/

    config/

tests/

docs/
```

---

# Coding Standards

## Python

- Use type hints.
- Use dataclasses for models.
- Use descriptive variable names.
- Avoid global variables.
- Use dependency injection where practical.

---

## Imports

Use absolute imports whenever possible.

Example:

```python
from networkmapper.core.models import Device
```

---

## Logging

Temporary validation harnesses may use print().

Production application logic should use the Logger service.

---

## Error Handling

Catch expected errors.

Allow unexpected errors to surface during development.

---

## Comments

Write comments explaining **why**, not **what**.

Bad:

```python
i += 1
```

Good:

```python
# Retry after transient network failures.
```
Providers contribute facts and the Discovery Engine merges them into a unified view of the network
---

# Git Workflow

Each completed task receives:

- One commit.
- One meaningful commit message.

Examples:

```
Implement logger service

Add inventory manager

Implement Draw.io exporter
```

Avoid generic messages like:

```
Update

Fix

Stuff
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

A phase is complete when:

- The application runs.
- The new capability works.
- Existing functionality still works.
- Documentation has been updated.
- Changes have been committed to Git.

---

# Product Vision

NetworkMapper should enable a technician to:

- Walk into a customer site.
- Discover the environment.
- Create a reusable customer project.
- Compare future discoveries.
- Produce documentation for technicians and customers.

---

## Information Model

NetworkMapper is built around relationships.

Devices are important.

Networks are important.

Interfaces are important.

The relationships between them are the primary source of value.

Everything discovered should strengthen the network graph.

---

## Deployment Philosophy

NetworkMapper should require no development tools on the technician's laptop.

The final product will be distributed as a self-contained Windows executable.

The application should function completely offline and require minimal configuration.

---

## Documentation First

The primary purpose of NetworkMapper is to create accurate network documentation where none exists.

Discovery is not the final product.

Documentation is.

---

## Data Philosophy

The Project is the source of truth.

The NetworkGraph is the canonical representation of the discovered environment.

Discovery providers collect facts.

Intelligence interprets those facts.

Exporters present those facts.

Open, portable formats should be preferred whenever practical.

The Project should be complete enough that a technician can resume work without rediscovering the network.

# Product Personas

NetworkMapper serves multiple audiences.

## Technician

Needs:
- Discovery
- Troubleshooting
- Documentation
- Accurate inventory

## Account Manager

Needs:
- Managed device counts
- Inventory changes
- Billing deltas

## Customer

Needs:
- Documentation
- Network diagrams
- Asset inventory

Each feature should identify its primary audience.

## Classification Rules

Every new classification rule must include:

- A focused unit test for the rule.
- An integration test through DeviceClassifier.
- Registration in the ordered rule list.