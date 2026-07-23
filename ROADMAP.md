# NetworkMapper Roadmap

> **Current Version:** 2.x  
> **Current Phase:** Explainable Classification  
> **Development Model:** Incremental, deterministic, regression-driven

---

# ============================================================================
# PROJECT PHILOSOPHY
# ============================================================================

NetworkMapper is designed around a few core principles:

- Deterministic discovery
- Explainable classification
- Incremental architecture
- Comprehensive regression testing
- Provider-agnostic discovery
- Human-readable diagnostics

New infrastructure should exist only when it enables future user-visible
features.

---

# ============================================================================
# COMPLETED MILESTONES
# ============================================================================

## Discovery
- ✅ DISC-001: Scan Profiles
- ✅ DISC-002: Two-Phase STANDARD Discovery

## Classification Framework
- ✅ CLASS-001: RuleResult Framework
- ✅ CLASS-002: Printer Rule Migration
- ✅ CLASS-003: Evidence API
- ✅ CLASS-004: SonicWall Rule Migration
- ✅ CLASS-005: Vendor Rule Migration
- ✅ CLASS-006: Hostname Rule Migration
- ✅ CLASS-007: Remove RuleResult Compatibility Adapter

## Evidence
- ✅ EVID-001: Classification Workbench Rule Evidence

---

# ============================================================================
# CURRENT DEVELOPMENT
# ============================================================================

## INTEL-001: Improve RuleResult Evidence Messages
**Status:** 🚧 In Progress

### Objective

Improve the diagnostic quality of RuleResult.reason across all
classification rules.

### Goals

- Include actual values evaluated.
- Produce human-readable explanations.
- Improve workbench usefulness.
- Preserve all existing classification behavior.

### Examples

Instead of:

```
Vendor did not match.
```

Prefer:

```
Vendor 'Ubiquiti' is not a known Cisco switch vendor.
```

Instead of:

```
Hostname did not match.
```

Prefer:

```
Hostname 'planning.wrf.scterm.com' did not match
known server naming patterns.
```

### Constraints

- No behavioral changes.
- No classifier changes.
- No discovery changes.
- No serialization changes.
- Update only rule implementations and dedicated rule tests.

---

# ============================================================================
# PHASE 1 - DISCOVERY
# ============================================================================

## DISC-001: Scan Profiles
**Status:** ✅ Complete

### Completed

- ScanProfile enum
- FAST profile
- STANDARD profile
- CLI integration
- Regression coverage

---

## DISC-002: Two-Phase STANDARD Discovery
**Status:** ✅ Complete

### Completed

- Host-authoritative discovery
- Curated enrichment scan
- IP-based evidence merge
- Host retention when enrichment returns no data
- Provider regression coverage

---

# ============================================================================
# PHASE 2 - CLASSIFICATION FRAMEWORK
# ============================================================================

## CLASS-001: RuleResult Framework
**Status:** ✅ Complete

### Completed

- RuleResult dataclass
- Structured rule output
- Framework regression tests

---

## CLASS-002: Printer Rule Migration
**Status:** ✅ Complete

### Completed

- PrinterVendorRule migrated
- Dedicated rule tests

---

## CLASS-003: Evidence API
**Status:** ✅ Complete

### Completed

- DeviceClassifier.get_last_rule_results()
- Immutable public API
- Evidence regression tests

---

## CLASS-004: SonicWall Rule Migration
**Status:** ✅ Complete

### Completed

- SonicWallFirewallRule migrated
- Dedicated regression tests

---

## CLASS-005: Vendor Rule Migration
**Status:** ✅ Complete

### Completed

- CiscoSwitchRule
- UbiquitiAccessPointRule
- VoiceVendorRule
- Dedicated regression tests

---

## CLASS-006: Hostname Rule Migration
**Status:** ✅ Complete

### Completed

- ServerHostnameRule
- HypervisorHostnameRule
- DellWorkstationRule
- Dedicated regression tests

---

## CLASS-007: Remove Compatibility Adapter
**Status:** ✅ Complete

### Completed

- Removed RuleResult compatibility layer
- Simplified DeviceClassifier
- Unified rule contract
- Full classifier regression suite

---

# ============================================================================
# PHASE 3 - EVIDENCE
# ============================================================================

## EVID-001: Classification Workbench Evidence
**Status:** ✅ Complete

### Completed

- Rule Evidence section
- Rule name
- Match status
- Suggested device type
- Reason rendering
- Developer-focused diagnostics
- Workbench regression tests

---

# ============================================================================
# PHASE 4 - EXPLAINABLE CLASSIFICATION
# ============================================================================

## INTEL-001: Improve RuleResult Evidence Messages
**Status:** 🚧 In Progress

Improve every RuleResult reason so that it explains the actual evidence
examined by the rule.

---

## INTEL-002: RuleResult Metadata
**Status:** Planned

### Objective

Include metadata describing which rule produced each RuleResult.

### Goals

- Add rule_name (or source_rule)
- Remove workbench dependency on classifier internals
- Improve portability of RuleResult consumers

### Constraints

- No behavioral changes
- Preserve public API where practical

---

## INTEL-003: Improve Classification Rules
**Status:** Planned

### Objective

Use evidence gathered from the workbench to improve weak heuristics.

### Initial Targets

- Ubiquiti devices
- Microsoft infrastructure hosts
- Dell workstation/server differentiation
- Additional vendor heuristics
- Improved hostname patterns

### Constraints

- Small focused improvements
- Fully regression tested
- No architectural changes

---

## INTEL-004: Confidence Scoring
**Status:** Planned

### Objective

Assign meaningful confidence values to RuleResults.

### Example

Hostname match

+40

Vendor match

+20

Known service

+15

Known port

+10

### Constraints

- First-match-wins remains unchanged.
- Confidence is informational only.

---

## INTEL-005: Evidence Aggregation
**Status:** Planned

### Objective

Evaluate every rule instead of stopping after the first successful match.

### Goals

- Collect every RuleResult
- Preserve all supporting evidence
- Enable richer diagnostics

### Notes

Decision logic remains unchanged.

---

## INTEL-006: Confidence-Based Decision Engine
**Status:** Planned

### Objective

Replace first-match-wins with confidence-based classification.

### Goals

- Aggregate evidence
- Score candidate device types
- Select highest-confidence result
- Resolve conflicting evidence deterministically

---

## INTEL-007: Enhanced Classification Workbench
**Status:** Planned

### Planned Features

- Confidence display
- Closest candidate classifications
- Rule evaluation statistics
- Evidence summaries
- Improved formatting
- Optional verbose mode

---

# ============================================================================
# PHASE 5 - DISCOVERY INTELLIGENCE
# ============================================================================

## DISC-003: Additional Discovery Providers
**Status:** Planned

### Candidate Providers

- SNMP
- WMI
- SSH
- WinRM
- LLDP
- CDP
- mDNS
- NetBIOS
- ARP cache import

---

## DISC-004: Provider Fusion
**Status:** Planned

### Objectives

- Merge evidence across providers
- Attribute evidence to discovery sources
- Confidence-weight provider results
- Produce unified device profiles

---

## DISC-005: Discovery Confidence
**Status:** Future

### Objective

Measure confidence in discovered device attributes based on multiple
independent discovery providers.

---

# ============================================================================
# EXPORTS
# ============================================================================

## EXPORT-001: Rich Evidence Export
**Status:** Planned

### Objectives

Export:

- RuleResult evidence
- Confidence
- Classification reasoning

Supported formats:

- CSV
- Markdown
- JSON

---

## EXPORT-002: Diagnostic Reports
**Status:** Future

### Objectives

Generate developer-oriented reports containing:

- Unknown-device summaries
- Rule evaluation statistics
- Confidence distributions
- Evidence reports

---

# ============================================================================
# ANALYTICS
# ============================================================================

## ANALYTICS-001: Classification Metrics
**Status:** Future

Potential metrics:

- Rule hit rates
- Unknown-device trends
- Vendor distribution
- Classification confidence distribution
- Discovery-source effectiveness

---

# ============================================================================
# LONG-TERM IDEAS
# ============================================================================

## Rule Configuration

Investigate making classification rules data-driven through external
configuration files.

---

## Plugin Architecture

Investigate optional plugin-based discovery and classification providers.

---

## Classification Analytics Dashboard

Potential future features:

- Rule performance
- Classification trends
- Unknown-device heatmaps
- Discovery confidence visualization

---

# ============================================================================
# OUT OF SCOPE
# ============================================================================

The following are **not** current project goals:

- Machine-learning classification
- Cloud-hosted processing
- Closed-source components
- Vendor lock-in
- Non-deterministic classification
- AI-generated device classifications

NetworkMapper prioritizes deterministic, explainable decisions over
black-box inference.

---

# ============================================================================
# PROJECT STATUS
# ============================================================================

## Architecture Status

✅ Discovery Framework Complete

✅ Classification Framework Complete

✅ Evidence Framework Complete

## Current Focus

Improve classification quality through better evidence, stronger rules,
and richer diagnostics.

## Long-Term Vision

NetworkMapper should evolve into an explainable network discovery and
classification engine where every device classification is transparent,
reproducible, and supported by deterministic evidence.