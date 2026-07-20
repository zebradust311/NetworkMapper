# NetworkMapper Roadmap

## Vision

NetworkMapper is a portable Windows application that discovers, documents, and maintains an MSP's understanding of a customer's network throughout its lifecycle.

It produces accurate, portable, and AI-friendly documentation that supports customer onboarding, operational support, recurring inventory audits, and long-term network management.

NetworkMapper exists to reduce the time, effort, and uncertainty required to understand an undocumented network. Every architectural and implementation decision should support that mission.

---

## Current Sprint 🚧

### Theme

Classification Intelligence

### Current Objective

Reduce the number of **Unknown** devices through validated MSP classification rules while maintaining high classification confidence.

### Success Metric

- Decrease the Unknown device count on real customer scans.
- Improve Markdown documentation without modifying the reporting layer.
- Ensure every new classification rule is backed by:
  - Field observations
  - Unit tests
  - Integration tests
  - Real-world validation

---

## Version 0.1.0 – Foundation ✅

### Goals

- ✅ Application framework
- ✅ Domain model
- ✅ Network graph
- ✅ Project model
- ✅ Discovery framework

---

## Version 0.2.0 – Discovery 🚧

### Goals

- ✅ Nmap host discovery
- ✅ MAC address discovery
- ✅ Vendor lookup
- ⏳ OS detection
- ⏳ Automatic subnet detection

---

## Version 0.3.0 – Persistence ✅

### Goals

- ✅ Project serialization
- ✅ Project loading
- ✅ Project saving
- ✅ Project comparison
- ⏳ Scan history

---

## Version 0.4.0 – Intelligence 🚧

### Goals

- ✅ Rule engine
- ✅ Device classification
- 🚧 Vendor classification rules
- 🚧 Hostname classification rules
- ⏳ Confidence scoring
- ⏳ Evidence-based classification
- ⏳ Vendor normalization
- ⏳ Classification reporting
- ⏳ Inventory intelligence

---

## Version 0.5.0 – Enterprise Discovery

### Goals

- SNMP
- LLDP/CDP
- VLAN discovery
- Routing tables

---

## Version 0.5.5 – Data Enrichment

### Goals

- DNS enrichment
- SNMP enrichment
- Active Directory enrichment
- VMware integration
- UniFi API integration
- Meraki API integration

---

## Version 0.6.0 – Project Intelligence

### Goals

- Inventory comparison
- Device lifecycle tracking
- Network change detection
- Asset history

---

## Version 0.7.0 – Reporting & Exports

### Goals

- ✅ CSV
- ✅ Markdown
- ⏳ PDF
- ⏳ Draw.io
- ⏳ GraphML
- ⏳ Executive Summary report
- ⏳ Technician report
- ⏳ Change report

---

## Version 0.8.0 – MSP Workflows

### Goals

- Customer onboarding workflow
- Monthly inventory audit
- Change reporting
- Billing support
- Technician handoff

---

## Version 1.0.0 – Production

### Goals

- Windows GUI
- Portable EXE
- Documentation complete
- Stable project format
- Production release

---

## Beyond Version 1.0

These ideas are intentionally out of scope until Version 1.0.

- AI-assisted documentation
- PSA integrations
- OneNote / Markdown documentation packages
- Inventory reconciliation
- Multi-site organizations
- Scheduled recurring scans

---

## Design Principles

- The Project is the source of truth.
- The NetworkGraph is the canonical network model.
- Discovery providers collect data.
- Intelligence interprets data.
- Classification rules encode validated MSP knowledge.
- Exporters present data.
- Workflows solve technician problems.
- Preserve open, portable data formats whenever practical.

---

## Engineering Philosophy

NetworkMapper is built around layered responsibilities.

```
Discovery
    ↓
Project
    ↓
Classification
    ↓
Enrichment
    ↓
Reporting
```

Each layer should have a single responsibility.

New functionality should improve the appropriate layer without tightly coupling it to others.

This architecture allows discovery, classification, reporting, and future integrations to evolve independently while sharing the same underlying Project model.