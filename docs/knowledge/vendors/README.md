# Vendor Knowledge

This document explains what Vendor Knowledge is, why it is a separate subsystem from Field Observations, how it relates to the broader Knowledge Framework, when a vendor document should be created, and how contributors should use this subsystem.

It complements [docs/knowledge/README.md](../README.md), [docs/knowledge/FIELD-OBSERVATIONS.md](../FIELD-OBSERVATIONS.md), and [docs/knowledge/KNOWLEDGE-LIFECYCLE.md](../KNOWLEDGE-LIFECYCLE.md).

## What Vendor Knowledge Is

Vendor Knowledge is corroborated operational experience organized by vendor rather than by individual observation event.

It captures:

- Deployment characteristics — how a vendor's devices are actually configured and used in the field.
- Naming conventions — hostname and identification patterns observed across that vendor's products.
- Operational context — the operational role(s) a vendor's devices tend to play once deployed.

Vendor Knowledge is intended to become future benchmark input and future classifier input, once it has matured through the stages in [KNOWLEDGE-LIFECYCLE.md](../KNOWLEDGE-LIFECYCLE.md).

Vendor Knowledge is **not**:

- A product catalog.
- Vendor marketing.
- A device inventory.

A vendor document does not describe everything a vendor sells. It describes only what NetworkMapper has actually observed, corroborated, and found operationally relevant.

## Why It Is Separate From Field Observations

A [Field Observation](../FIELD-OBSERVATIONS.md) is a single, individual account of what one technician saw in one deployment. It is raw, timestamped in effect by its sequence number, and deliberately not generalized at the moment it is recorded (see [OBSERVATION-TEMPLATE.md](../OBSERVATION-TEMPLATE.md)).

Vendor Knowledge is different in kind, not just in detail. It is the durable, per-vendor view that emerges only after multiple independent Field Observations about the same vendor have been corroborated — the same distinction [KNOWLEDGE-LIFECYCLE.md](../KNOWLEDGE-LIFECYCLE.md) draws between an **Observation** and **Knowledge**.

Keeping the two separate preserves an important property: a single technician's account is never silently generalized into vendor-wide guidance. Vendor Knowledge only exists where that generalization has actually been earned.

## How It Relates to the Knowledge Framework

Vendor Knowledge sits inside the Knowledge Framework described in [docs/knowledge/README.md](../README.md), downstream of Field Observations and upstream of Benchmark and Classification work in [KNOWLEDGE-LIFECYCLE.md](../KNOWLEDGE-LIFECYCLE.md).

A vendor document is where corroborated Knowledge about a specific vendor accumulates and stays organized, so that it can later inform a benchmark case or a classification rule without having to be reconstructed from scattered individual observations each time.

Vendor Knowledge does not introduce a new lifecycle stage. It is an organizing view over the same **Observation → Knowledge → Benchmark → Classification → Validation → Architecture Review** progression.

## When Vendor Documents Should Be Created

A vendor document should be created only when:

- Multiple independent Field Observations about the same vendor exist in [FIELD-OBSERVATIONS.md](../FIELD-OBSERVATIONS.md), and
- Those observations have been corroborated consistently across separate environments, reaching the **Knowledge** stage described in [KNOWLEDGE-LIFECYCLE.md](../KNOWLEDGE-LIFECYCLE.md).

A vendor document should not be created from a single observation, and should not be created speculatively in anticipation of future observations.

## How Contributors Should Use This Subsystem

- Start from [VENDOR-TEMPLATE.md](./VENDOR-TEMPLATE.md) rather than writing a vendor document from scratch.
- Reference the specific Field Observation numbers that corroborate each claim in the vendor document.
- Describe only operational experience — deployment characteristics, naming conventions, and operational context. Do not include specifications, feature lists, or language drawn from vendor marketing material.
- Update an existing vendor document as new corroborating observations arrive, rather than creating a duplicate document for the same vendor.
- Treat vendor documents as engineering documentation: reviewable, specific, and traceable back to the observations that support them.

Creating individual vendor documents is out of scope for this subsystem's foundation. This document and [VENDOR-TEMPLATE.md](./VENDOR-TEMPLATE.md) establish the structure; vendor-specific documents are created later, as corroborated Knowledge actually accumulates.
