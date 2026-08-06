# Architecture Overview

This document describes the currently implemented architecture of NetworkMapper.

It focuses on the runtime and developer subsystems that exist today and complements the broader project context in [README.md](../../README.md), the engineering principles in [ENGINEERING.md](../../ENGINEERING.md), the delivery status in [ROADMAP.md](../../ROADMAP.md), and the existing architecture narrative in [docs/ARCHITECTURE.md](../ARCHITECTURE.md).

## System Perspective

NetworkMapper is organized around a reusable project model.

At a high level, the implemented system can be understood as the following relationship chain:

Application

↓

Project

↓

NetworkGraph

↓

Discovery

↓

Classification

↓

Exporters

↓

Developer Platform

This sequence is best read as an architecture relationship map rather than a literal call order. In the current runtime flow, the application invokes discovery first, discovery classifies devices while building a graph, and the resulting graph is then wrapped in a Project. From that point forward, the Project and its NetworkGraph become the authoritative inputs for persistence, export, and developer tooling.

## Core Responsibilities

### Application

The Application is the top-level coordinator for the current runtime workflow.

Its implemented responsibilities are:

- parse a small set of runtime arguments
- choose the discovery provider configuration
- invoke discovery
- summarize resulting classifications for console output
- create the Project object
- invoke exporters and persistence
- optionally generate developer-oriented workbench output

The Application does not implement discovery, classification, export, or persistence logic itself. It orchestrates those subsystems.

### Project

The Project is the root domain object for a captured NetworkMapper snapshot.

Its implemented responsibilities are:

- hold project identity such as customer name
- hold creation and modification timestamps
- own the NetworkGraph for the snapshot

The Project is the source of truth for downstream outputs. Exporters, summaries, persistence, and developer reports consume the Project rather than reconstructing state from raw discovery output.

### NetworkGraph

The NetworkGraph is the in-memory container for discovered devices.

Its implemented responsibilities are:

- store devices keyed by IP address
- prevent duplicate insertion for the same IP address
- provide inventory access for downstream consumers
- provide simple graph-level counts

In the current implementation, NetworkGraph is a lightweight inventory model rather than a rich topology engine. It is still the central shared structure passed between discovery, classification results, persistence, export, and developer tooling.

### Discovery

The discovery subsystem is responsible for obtaining raw device evidence and turning it into Device objects.

Its implemented architecture has two layers:

- DiscoveryProvider defines the provider contract.
- DiscoveryEngine coordinates one or more providers.

The implemented provider abstraction allows discovery data to come from different sources while keeping the engine independent of a specific scanner. The current concrete provider is NmapProvider.

NmapProvider currently supports profile-driven scanning and returns Device objects containing evidence such as:

- IP address
- hostname
- MAC address
- vendor
- device-level identity evidence, where available (operating system, computer name, domain/workgroup, SMB signing posture). Operating system, computer name, and domain can each be produced by two independent, unauthenticated sources — SMB negotiation on port 445 and RDP NTLM negotiation on port 3389 — with SMB preferred when both are present, since it reports a full OS caption where RDP reports only a bare build number. SMB signing posture has no RDP equivalent. Per ADR-009.
- correlated per-service evidence (port, protocol, service name, product, version, and, where available, self-identifying evidence such as HTTP page title, TLS certificate subject/issuer, and HTTP authentication realm, per ADR-009)
- discovery sources

The current discovery system is under active development. It already supports provider abstraction and a working Nmap-based path, but broader provider coverage described elsewhere in the roadmap is not yet implemented.

### Classification

The classification subsystem is responsible for assigning a DeviceType to discovered devices.

Its implemented responsibilities are:

- evaluate devices against an ordered rule set
- preserve deterministic first-match-wins behavior
- produce explainable results through RuleResult-based evidence
- expose rule evidence for developer inspection

In the current runtime architecture, classification is performed inside DiscoveryEngine as devices are accepted from discovery providers. The graph therefore stores classified devices, not an unclassified raw inventory.

This design keeps classification close to the ingestion path while still allowing the resulting Project and NetworkGraph to act as the stable shared model for later stages.

### Exporters

The exporter subsystem is responsible for turning a Project snapshot into external representations.

The implemented exporters are:

- CSV exporter for flat inventory output
- Markdown exporter for human-readable documentation

These exporters do not perform discovery or classification. They consume the Project and its NetworkGraph as already-resolved state.

### Developer Platform

The developer platform is the implemented tooling around the core runtime model.

It currently has two primary areas:

- `networkmapper.developer`
- `devtools`

`networkmapper.developer` contains developer-facing reporting and inspection utilities built on the same classifier and project model used by the application. Implemented examples include the classification workbench and the benchmark runner.

`devtools` provides standardized command-line automation for validation, benchmark execution, and benchmark comparison. It uses the existing project developer utilities rather than replacing them with separate implementations.

## Component Interactions

### Runtime Path

The current runtime path is:

1. Application configures a discovery provider.
2. DiscoveryEngine requests Device objects from each provider.
3. DiscoveryEngine classifies each discovered device.
4. DiscoveryEngine inserts classified devices into NetworkGraph.
5. Application creates a Project around the graph.
6. Exporters, persistence, and optional developer reports consume the Project.

This keeps the runtime coordination in one place while preserving clear subsystem boundaries.

### Persistence Path

ProjectSerializer persists and reloads Project snapshots.

The implemented persistence boundary is important architecturally because it confirms that the Project is not just a transient runtime wrapper. It is the portable representation of the discovered and classified environment.

### Reporting Path

ProjectSummary derives reusable summary data from a Project. Exporters then render that data into presentation-specific output.

This separation keeps reporting concerns distinct from the core model and supports multiple output formats from the same source data.

## Data Flow

The implemented data flow can be summarized as:

1. Discovery providers gather evidence.
2. DiscoveryEngine turns provider output into classified devices.
3. NetworkGraph stores the resulting device inventory.
4. Project owns the graph as the canonical snapshot.
5. Persistence, exporters, summaries, and developer tooling read from that snapshot.

This is consistent with the engineering principle in [ENGINEERING.md](../../ENGINEERING.md) that the internal data model is the product and that every export is a view of that model.

## Project as Source of Truth

The Project is the source of truth for the documented environment.

That role matters because multiple subsystems depend on a shared, stable representation:

- exporters render from Project
- serializer saves and restores Project
- project summaries derive counts from Project
- developer workbench inspects Project

The current architecture avoids giving each subsystem its own separate copy of network state. Instead, the Project provides one reusable snapshot that can be persisted, exported, reviewed, and benchmarked.

## Role of NetworkGraph

NetworkGraph is the core inventory structure inside the Project.

Its role is narrower than the long-term product vision described in [README.md](../../README.md), but it is already central to the implemented system because it:

- holds the discovered device set
- preserves uniqueness by IP address
- acts as the handoff boundary between discovery/classification and downstream consumers

In the current implementation, the graph is intentionally simple. That simplicity matches the engineering guidance in [ENGINEERING.md](../../ENGINEERING.md): prefer clear, maintainable structures that support the current product capabilities.

## Relationship Between Discovery, Classification, Benchmarking, and Developer Platform

These subsystems are related through shared use of the same device model and classifier behavior.

- Discovery produces device evidence.
- Classification interprets that evidence and assigns device types.
- Benchmarking replays curated inventory data through the same classifier to measure classification quality.
- The developer platform exposes validation, benchmarking, and comparison workflows around that existing behavior.

Benchmarking is therefore not a separate classification system. It is an evaluation layer over the implemented classifier. Likewise, the developer platform is not a separate runtime architecture. It is an automation and reporting layer built around the current discovery, classification, and project model.

## Current Boundaries and Incomplete Areas

Some subsystem boundaries are already established even where implementation depth is still limited.

- Discovery provider abstraction exists, but only the Nmap provider path is currently implemented.
- NetworkGraph is implemented as an inventory container, not a full topology-analysis system.
- Export and reporting support is implemented for CSV, Markdown, and project summaries.
- Benchmarking and developer automation are implemented as developer tooling rather than production runtime features.

Where a subsystem is still under development, this document describes only the implemented boundary and current role, not speculative future design.