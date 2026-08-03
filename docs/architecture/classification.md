# Classification Architecture

This document describes the implemented classification subsystem in NetworkMapper.

It complements the broader project context in [README.md](../../README.md), the engineering constraints in [ENGINEERING.md](../../ENGINEERING.md), the accepted architectural decisions in [docs/ADR.md](../ADR.md), and the system-level relationships described in [overview.md](./overview.md).

## Purpose

The classification subsystem is responsible for interpreting discovered device evidence and assigning a `DeviceType` to each device.

Its current architectural goals are:

- deterministic behavior
- explainable decisions
- stable rule ordering
- clear boundaries for developer tooling

Classification is part of the runtime processing pipeline, but it is also a shared service consumed by developer tooling such as benchmarking and the classification workbench.

## Architectural Role

In the implemented system, classification sits between discovery evidence collection and downstream consumers of project state.

The current workflow is:

Discovery

↓

Evidence Collection

↓

Ordered Rule Evaluation

↓

RuleResult

↓

DeviceType Assignment

Discovery providers collect evidence such as hostname, vendor, and correlated per-service evidence (port, protocol, service name, and, where available, product and version — see ADR-009). `DiscoveryEngine` passes each discovered `Device` into `DeviceClassifier`, which evaluates the device against the current ordered rule list. The resulting device type is then stored in the `NetworkGraph` and carried forward into the `Project`.

## Responsibilities

### DeviceClassifier

`DeviceClassifier` is the coordinating service for classification.

Its architectural responsibilities are:

- hold the current ordered rule list
- evaluate rules in deterministic sequence
- stop at the first matching result that suggests a device type
- assign the final `DeviceType` to the device
- retain evidence from the most recent classification through a read-only API

`DeviceClassifier` is therefore both the evaluation engine and the boundary between individual rules and the rest of the system.

### ClassificationRule Interface

`ClassificationRule` defines the contract for an individual classification rule.

Its role is architectural rather than procedural: each rule encapsulates one small, deterministic decision about whether the available device evidence supports a specific classification.

This keeps the classifier composed of small units rather than a single monolithic decision tree. It also supports targeted rule tests and localized heuristic changes without changing the classifier orchestration model.

### RuleResult

`RuleResult` is the structured output of evaluating one rule.

Its architectural purpose is to separate classification evidence from the final device mutation. Instead of rules returning only a yes/no decision, they return a structured explanation that the classifier and developer tooling can both consume.

The current implemented `RuleResult` contract exposes:

- `matched`
- `confidence_contribution`
- `reason`
- `suggested_device_type`

This supports explainable classification because each evaluated rule can describe what it observed and whether that observation contributed to a classification decision.

The current implementation does not expose `matched_fields`. Because this document describes implemented behavior only, `matched_fields` is not documented as part of the active public contract.

## Rule Registration and Ordering

Rule registration is currently centralized in `DeviceClassifier`, which constructs the ordered list of rule instances during initialization.

This ordering is part of the architecture, not an incidental implementation detail, because the classifier follows first-match-wins evaluation. Once a rule returns a matching `RuleResult` with a suggested device type, later rules are not evaluated for that device.

This behavior is documented by [docs/ADR.md](../ADR.md) in:

- ADR-002 — RuleResult
- ADR-003 — First Match Wins Classification
- ADR-004 — Read-Only Evidence API

Ordering matters because multiple rules can legitimately match overlapping evidence. The classifier resolves that overlap by giving priority to earlier rules in the ordered list.

## Rule Evaluation Lifecycle

The current rule evaluation lifecycle is:

1. A device enters classification with discovery evidence already attached.
2. `DeviceClassifier` clears evidence from the previous classification run.
3. Each registered rule evaluates the device in order.
4. Each evaluation returns a `RuleResult`.
5. The classifier records that `RuleResult` in its most-recent evidence collection.
6. If the result is a match with a suggested device type, classification stops.
7. The device is assigned that device type.
8. If no rule matches, the device is assigned `UNKNOWN`.

This lifecycle preserves determinism because rule order is stable, evaluation stops consistently at the same point, and the fallback path is explicit.

## Deterministic First-Match-Wins Behavior

First-match-wins is a deliberate architectural property of the current classifier.

Its design intent is to preserve stable behavior while keeping rule interactions understandable. Rather than accumulating competing classifications and resolving them later, the classifier uses a simple ordered model:

- earlier rules have higher precedence
- evaluation is deterministic
- the final result can be explained in terms of the rule that matched

This makes classifier behavior easier to test, reason about, and benchmark.

## Explainability and RuleResult

Explainability is a defining characteristic of the implemented classification subsystem.

`RuleResult` exists so classification produces structured evidence, not just a final label. Architecturally, this enables:

- developer tooling to inspect why a device matched or did not match a rule
- stable evidence reporting without exposing classifier internals directly
- benchmarking and diagnostics to consume classifier behavior through documented outputs rather than private control flow

The `reason` field is especially important because it provides the human-readable explanation that developer tooling surfaces.

The `matched` field distinguishes supporting evidence from non-matches.

The `confidence_contribution` field is part of the current structure even though the current classifier remains deterministic and rule-order-driven rather than score-driven.

## Evidence API

The classification subsystem exposes a read-only evidence API through `get_last_rule_results()`.

Architecturally, this API provides a stable public boundary for consumers that need rule-by-rule evidence from the most recent classification pass.

Its current role is to support:

- developer tooling
- workbench output
- evidence-oriented validation and diagnostics

The interface is read-only because it returns an immutable collection rather than exposing internal mutable classifier state. This matches ADR-004 and preserves encapsulation while still making evidence available to consumers.

### Workbench Integration

The classification workbench uses the classifier as an evidence source rather than re-implementing rule logic.

That relationship is important architecturally because it means developer diagnostics are consumers of classifier behavior, not alternative classification paths. The workbench asks the classifier to evaluate a device, reads rule evidence through the public API, and renders that evidence for human inspection.

## Shared Evidence Helpers

The shared evidence helpers support the classification subsystem by centralizing common evidence-processing behavior used across multiple rules.

Their architectural purpose is to:

- normalize evidence consistently
- eliminate duplicated rule logic
- preserve deterministic matching behavior across rules

In the current implementation, these helpers are used for tasks such as hostname normalization, vendor normalization, first-match lookups for ports and services, and consistent evidence formatting.

They are not a separate decision-making subsystem. They exist to support rules while preserving the current classifier model: ordered rules, deterministic evaluation, and explainable outputs.

## Multi-Evidence Classification

The implemented classifier supports rules that combine multiple observations.

Depending on the rule, these observations may include:

- vendor
- hostname
- services
- ports

Architecturally, this means a rule can make a decision based on more than one type of evidence without changing the classifier orchestration model. Multi-evidence rules still participate in the same ordered evaluation lifecycle and still return a `RuleResult` with an explicit explanation.

This preserves two important properties:

- classification remains deterministic
- classification remains explainable

## Relationship to Discovery

Classification depends on discovery, but it is not part of the discovery provider contract.

Discovery providers are responsible for collecting device evidence. `DiscoveryEngine` is responsible for passing that evidence into the classifier. Classification then interprets the evidence and assigns the device type before the device is stored in `NetworkGraph`.

This separation keeps evidence collection and evidence interpretation as distinct architectural concerns.

This is formalized as a project-wide architectural principle in [docs/ADR.md](../ADR.md), ADR-008 — Discovery is Immutable, Interpretation is Adjustable. That decision does not change the classification behavior described in this document; it establishes the broader principle that discovery data and interpretation data are distinct and evolve independently.

## Relationship to Benchmarking

Benchmarking is a consumer of classifier behavior rather than part of the classification subsystem itself.

The implemented relationship is:

BenchmarkRunner

↓

DeviceClassifier

↓

RuleResult

↓

Reports

↓

Developer Platform

`BenchmarkRunner` constructs benchmark devices from curated datasets and runs them through the same `DeviceClassifier` used by discovery. It then turns the resulting classifications into benchmark reports and report summaries.

This architectural separation matters because benchmarking evaluates classifier behavior without changing the classifier itself. It is an observation and reporting layer built on top of the implemented classification subsystem.

## Design Intent

The current classification architecture is intentionally simple:

- one coordinating classifier
- one rule contract
- one structured evidence model
- one ordered evaluation path
- one public evidence API for developer consumers

That simplicity is consistent with [ENGINEERING.md](../../ENGINEERING.md), which emphasizes maintainability, explicit responsibilities, and deterministic behavior.

The classification subsystem is therefore not just a collection of heuristics. It is a bounded architectural component that turns discovery evidence into explainable, testable, benchmarkable device classification.