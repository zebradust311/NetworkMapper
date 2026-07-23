# NetworkMapper Architecture

## Overview

NetworkMapper is a deterministic network discovery and classification tool
designed for Managed Service Providers (MSPs), IT professionals, and network
administrators.

Unlike many network inventory tools, NetworkMapper emphasizes deterministic,
explainable behavior. Every discovery decision and every classification is
intended to be reproducible, testable, and understandable.

The project is built around the following design principles:

- Deterministic discovery
- Explainable classification
- Incremental architecture
- Comprehensive regression testing
- Provider-agnostic discovery
- Human-readable diagnostics

Architecture evolves only when it enables meaningful user-visible
capabilities.

---

# High-Level Architecture

```
                 Network
                     │
                     ▼
      +-----------------------------+
      | Discovery Providers         |
      |-----------------------------|
      | Nmap                        |
      | Future: SNMP, WMI, SSH ...  |
      +-----------------------------+
                     │
                     ▼
      +-----------------------------+
      | NetworkGraph                |
      |-----------------------------|
      | Device                      |
      | Connection                  |
      +-----------------------------+
                     │
                     ▼
      +-----------------------------+
      | DeviceClassifier            |
      +-----------------------------+
                     │
                     ▼
      +-----------------------------+
      | RuleResult                  |
      +-----------------------------+
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
+-------------------+   +-------------------+
| Developer         |   | Exporters         |
| Workbench         |   | CSV / Markdown    |
+-------------------+   +-------------------+
```

---

# Core Data Flow

NetworkMapper follows a simple processing pipeline.

```
Network
    ↓
Discovery
    ↓
NetworkGraph
    ↓
Classification
    ↓
RuleResult
    ↓
Workbench / Exports
```

Each subsystem builds upon the results of the previous stage without
modifying earlier stages. This separation of responsibilities simplifies
testing, maintenance, and future expansion.

---

# Discovery

## Purpose

The discovery subsystem is responsible for identifying devices on a network
and collecting evidence describing those devices.

Discovery is provider-agnostic.

The current implementation uses Nmap, but the architecture is designed to
support additional discovery providers in the future.

Examples include:

- SNMP
- WMI
- SSH
- WinRM
- LLDP
- CDP
- mDNS
- NetBIOS

---

## Scan Profiles

NetworkMapper currently supports two scan profiles.

### FAST

The FAST profile is optimized for speed.

It performs:

- Host discovery
- Hostname collection
- MAC address collection
- Vendor lookup

FAST is intended for rapid inventory collection.

---

### STANDARD

The STANDARD profile performs discovery in two phases.

### Phase 1

Host discovery.

```
-sn
```

This pass determines the authoritative list of discovered hosts.

### Phase 2

Service enrichment.

This pass performs curated service detection against discovered hosts,
collecting:

- Open ports
- Detected services
- Additional device evidence

Discovery remains authoritative.

Enrichment augments existing devices but never removes them.

---

## Discovery Evidence

Discovery providers may contribute evidence including:

- IP address
- MAC address
- Vendor
- Hostname
- Open ports
- Detected services

Future providers may contribute additional evidence while preserving the same
device model.

---

# Network Graph

The NetworkGraph represents the discovered network.

It stores:

- Devices
- Connections
- Project metadata

The NetworkGraph acts as the central model shared by discovery,
classification, persistence, and export components.

---

# Classification

## Purpose

Classification assigns a DeviceType to each discovered device.

Classification is deterministic.

Devices are evaluated against an ordered sequence of rules.

The first matching rule determines the current device type.

---

## Rule Evaluation

Each classification rule evaluates one aspect of a device.

Examples include:

- Vendor
- Hostname
- Open ports
- Services
- Future evidence providers

Rules are intentionally small and focused.

This simplifies testing and allows incremental improvements without affecting
unrelated rules.

---

## RuleResult

Every classification rule returns a RuleResult.

RuleResult contains:

- matched
- suggested_device_type
- confidence_contribution
- reason

RuleResult provides structured evidence describing why a rule matched or did
not match.

The RuleResult model forms the foundation for explainable classification.

---

## Evidence API

DeviceClassifier exposes:

```
get_last_rule_results()
```

This returns an immutable collection of RuleResults generated during the most
recent classification.

Consumers use this API rather than accessing classifier internals.

---

# Developer Workbench

The Classification Workbench is intended for development, diagnostics, and
rule tuning.

For unknown devices it displays:

- Device information
- Discovery evidence
- Rule evaluation results
- Match status
- Suggested device types
- Rule reasoning

The workbench classifies temporary copies of devices.

Report generation never modifies project state.

The workbench exists to answer questions such as:

- Why was this device classified?
- Why did this device remain unknown?
- Which rules were evaluated?
- What evidence was considered?

---

# Persistence

Projects may be serialized and restored.

Persistence preserves:

- Devices
- Connections
- Discovery evidence
- Classification information
- Project metadata

Persistence validation ensures data integrity after every save/load cycle.

---

# Exports

Current export formats include:

- CSV
- Markdown
- Classification Workbench

Future export formats may include:

- JSON
- Rich evidence reports
- Diagnostic reports

Exports consume existing project information and never modify project state.

---

# Testing Philosophy

NetworkMapper emphasizes comprehensive regression testing.

Architectural changes are accompanied by focused regression tests that verify:

- Discovery behavior
- Classification behavior
- Rule evaluation
- Persistence
- Export functionality

Small, isolated changes are preferred over large-scale rewrites.

---

# Key Architectural Decisions

NetworkMapper intentionally follows several important architectural
principles.

## Discovery is Authoritative

Device discovery establishes the authoritative host list.

Enrichment augments devices but never removes them.

---

## Classification is Deterministic

Given identical discovery evidence, classification should always produce the
same result.

---

## Classification is Explainable

Every classification decision should be supported by structured evidence.

Unknown devices should provide enough diagnostic information to understand why
classification failed.

---

## Architecture Evolves Incrementally

Large architectural rewrites are avoided.

Infrastructure is introduced only when it enables meaningful new features.

---

## Regression Testing is Required

Significant architectural changes are expected to include regression tests.

Maintaining behavioral stability is considered a primary project objective.

---

# Current Development Focus

The current phase of development focuses on improving classification quality
rather than introducing new infrastructure.

Near-term priorities include:

- Richer RuleResult evidence
- Improved classification heuristics
- Confidence scoring
- Evidence aggregation
- Confidence-based decision making

---

# Long-Term Vision

NetworkMapper is evolving into an explainable network discovery and
classification engine.

The long-term goal is to ensure that every device classification is:

- Deterministic
- Transparent
- Reproducible
- Supported by structured evidence
- Easy for humans to understand

As discovery providers and classification rules evolve, these core principles
remain unchanged.