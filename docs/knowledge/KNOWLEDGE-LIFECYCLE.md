# Knowledge Lifecycle

This document describes how a recorded observation is expected to mature within NetworkMapper.

It complements [README.md](./README.md), which explains why Knowledge exists, and [FIELD-OBSERVATIONS.md](./FIELD-OBSERVATIONS.md), which contains the observations this lifecycle applies to.

## The Progression

```
Observation
    │
    ▼
Knowledge
    │
    ▼
Benchmark
    │
    ▼
Classification
    │
    ▼
Validation
    │
    ▼
Architecture Review
```

Most observations do not reach the end of this progression, and that is expected. An observation only advances when it earns the next stage.

## Observation

A technician records what was actually seen in the field, using [OBSERVATION-TEMPLATE.md](./OBSERVATION-TEMPLATE.md), and it is appended to [FIELD-OBSERVATIONS.md](./FIELD-OBSERVATIONS.md).

At this stage, the observation is a single data point. It is recorded honestly, but it is not yet treated as reliable or general.

## Knowledge

An observation becomes Knowledge once the same pattern has been observed consistently across multiple, independent environments — not a single customer, and not a single technician's recollection.

This bar already exists informally in the project (see [docs/field-notes.md](../field-notes.md): "A note should only become a classification rule after it has been observed consistently across multiple customer environments"). The Knowledge Framework makes that bar explicit and applies it uniformly.

Knowledge is still descriptive at this stage. It has not yet influenced any measured or production behavior.

## Benchmark

Knowledge that could plausibly affect classification is turned into one or more benchmark cases before it changes anything in production.

This preserves the separation described in [docs/ADR.md](../ADR.md) (ADR-006 — Benchmark Framework): benchmarking measures classifier behavior against curated, realistic data, and never modifies production classification itself. Encoding Knowledge into a benchmark case makes it possible to see how a candidate classification change would perform before that change exists.

## Classification

Only after a benchmark case exists does Knowledge justify a classification change.

Any resulting rule must still meet the standards in [ENGINEERING.md](../../ENGINEERING.md) and [docs/architecture/classification.md](../architecture/classification.md): deterministic, explainable, ordered intentionally, and returning a `RuleResult` with clear evidence. The rule's `reason` text is where the original observation's operational rationale should be visible to a future reader.

## Validation

A classification change earns validation the same way any other change does: focused unit tests for the new or modified rule, and a full regression run confirming existing behavior is preserved (see the Sprint Workflow and Validation Workflow in [ENGINEERING.md](../../ENGINEERING.md)).

Validation confirms the change behaves as the benchmark predicted and did not regress unrelated classifications.

## Architecture Review

Accumulated Knowledge-driven changes are periodically assessed as part of an Architecture Review (see [ENGINEERING.md](../../ENGINEERING.md)).

This is where the project steps back from individual observations and asks a broader question: is the accumulated Knowledge shaping the classifier and benchmarks in a coherent, intentional direction? Architecture Reviews are the mechanism that keeps the Knowledge Framework's long-term influence deliberate rather than incidental.

## Summary

| Stage | What changes | What does not change |
|---|---|---|
| Observation | A new entry exists in FIELD-OBSERVATIONS.md | Nothing else |
| Knowledge | The observation is corroborated across environments | Production behavior |
| Benchmark | A benchmark case exists | Production classification |
| Classification | A rule is added or changed | Deterministic, first-match-wins behavior |
| Validation | Tests and regression confirm the change | Existing, unrelated classifications |
| Architecture Review | The project's long-term direction is reassessed | — |
