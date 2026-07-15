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

Inventory → stores discovered devices.

Exporter → writes data to external formats.

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

Logger

Inventory

Exporter

Topology Engine

---

## 7. Everything starts with a real-world problem.

We only build features that solve actual technician workflows.

---

## 8. The software should never get in the technician's way.

---

# Architecture

```
main.py
    │
    ▼
Application
    │
    ├── Configuration
    ├── Logger
    ├── Discovery Engine
    ├── Inventory
    ├── Topology
    └── Exporters
```

---

# Folder Structure

```
networkmapper/

    application.py

    core/

    providers/

    exporters/

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

Do not use print() inside application logic.

Use the Logger service.

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

Phase 3 — Enterprise Discovery

Phase 4 — Network Intelligence

Phase 5 — Draw.io Export

Phase 6 — Project Management

Phase 7 — Production Release

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
- Start with one IP address or subnet.
- Automatically discover the network.
- Generate an editable Draw.io topology.
- Save the discovery as a reusable project.
- Compare future scans against previous discoveries.

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