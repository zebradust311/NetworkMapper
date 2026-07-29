# Knowledge Framework

This document explains what Knowledge means in NetworkMapper, why it exists, and how it is intended to influence benchmarking, classification, and future engineering decisions.

It complements [ENGINEERING.md](../../ENGINEERING.md), [ROADMAP.md](../../ROADMAP.md), [docs/ADR.md](../ADR.md), and [docs/architecture/](../architecture/).

## What Knowledge Means

In NetworkMapper, Knowledge is structured, reviewable operational experience.

It is not a raw scan result, and it is not a classification rule. It sits between the two.

Knowledge captures what a technician has learned about how real devices behave in real environments — naming conventions, common deployment patterns, and the operational role a device actually plays on a network — in a form that can be reviewed, discussed, and eventually acted on.

Knowledge is:

- Structured — recorded in a consistent, comparable format.
- Reviewable — written so another engineer can evaluate it without the original technician present.
- Provisional — an observation is not automatically true everywhere; it matures through use, as described in [KNOWLEDGE-LIFECYCLE.md](./KNOWLEDGE-LIFECYCLE.md).

## Why It Exists

NetworkMapper's classification subsystem is deliberately deterministic, explainable, and rule-ordered (see [docs/architecture/classification.md](../architecture/classification.md) and [docs/ADR.md](../ADR.md)). That discipline only produces good outcomes if the rules it encodes reflect what actually happens in the field.

Without a Knowledge Framework, field experience stays informal — remembered by individual technicians, or scattered across ad hoc notes — and never reliably reaches the classifier or the benchmark datasets that measure it.

The Knowledge Framework exists to give that experience a home: a defined place to record it, a defined format to record it in, and a defined path for it to influence the product.

## How It Relates to Technicians

Technicians are the primary source of Knowledge.

They are the ones in customer environments observing how devices are actually named, configured, and used — information that cannot be derived from a lab environment or from vendor documentation alone.

The Knowledge Framework asks technicians to record what they observe using the canonical format in [FIELD-OBSERVATIONS.md](./FIELD-OBSERVATIONS.md) and [OBSERVATION-TEMPLATE.md](./OBSERVATION-TEMPLATE.md), rather than keeping it as personal or team-local knowledge. Recording an observation does not require the technician to write a classification rule or judge its long-term significance — only to describe what was observed, clearly and honestly.

## How It Feeds Benchmark Development

Benchmarking measures classifier quality against curated, realistic datasets (see [docs/ADR.md](../ADR.md), ADR-006). Those datasets are only as realistic as the operational knowledge behind them.

Recorded observations are a source of candidate benchmark scenarios: a device type, deployment pattern, or naming convention observed consistently in the field is a strong candidate for a new or expanded benchmark case. This lets classifier changes be evaluated against real operational patterns before they reach production behavior.

## How It Feeds Classifier Improvements

Classification rules must be deterministic, explainable, testable, and intentionally ordered (see [ENGINEERING.md](../../ENGINEERING.md)). Observations support this by supplying the operational rationale a rule's evidence and `reason` text should reflect.

An observation does not become a rule automatically. Per the lifecycle in [KNOWLEDGE-LIFECYCLE.md](./KNOWLEDGE-LIFECYCLE.md), an observation must first be corroborated into Knowledge and benchmarked before it can justify a classification change, preserving the deterministic, first-match-wins behavior described in [docs/architecture/classification.md](../architecture/classification.md).

## How It Supports Long-Term Intelligence

NetworkMapper's long-term goal is to understand device relationships, not just enumerate devices (see [ENGINEERING.md](../../ENGINEERING.md)). That understanding depends on accumulated, corroborated operational knowledge about how devices are actually deployed and used — not just their factory defaults.

The Knowledge Framework is the mechanism by which that accumulation happens deliberately rather than incidentally. Over time, it is intended to give Architecture Reviews (see [ENGINEERING.md](../../ENGINEERING.md)) a durable record of what the project has learned, and why specific classification and benchmarking decisions were made.

## Vendor Knowledge

Individual Field Observations are raw, single-encounter accounts. Once multiple independent observations about the same vendor have been corroborated into Knowledge, that understanding is organized by vendor in [docs/knowledge/vendors/](./vendors/), rather than staying scattered across individual observation entries.

Vendor Knowledge is corroborated operational experience — deployment characteristics, naming conventions, and operational context — not a product catalog, vendor marketing, or a device inventory. See [docs/knowledge/vendors/README.md](./vendors/README.md) for the full explanation of what Vendor Knowledge is, why it is kept separate from Field Observations, and when a vendor document should be created.

## Related Documents

- [FIELD-OBSERVATIONS.md](./FIELD-OBSERVATIONS.md) — the canonical observation format, with worked examples.
- [OBSERVATION-TEMPLATE.md](./OBSERVATION-TEMPLATE.md) — a reusable template for recording new observations.
- [KNOWLEDGE-LIFECYCLE.md](./KNOWLEDGE-LIFECYCLE.md) — how an observation matures into knowledge, benchmarks, classification, validation, and architecture review.
- [vendors/README.md](./vendors/README.md) — what Vendor Knowledge is and how it relates to Field Observations.
- [vendors/VENDOR-TEMPLATE.md](./vendors/VENDOR-TEMPLATE.md) — a reusable template for future vendor documents.
