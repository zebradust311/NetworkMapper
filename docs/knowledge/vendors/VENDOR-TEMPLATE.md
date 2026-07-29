# Vendor Template

Copy the template below to create a new vendor document once corroborated Vendor Knowledge actually exists for that vendor.

See [README.md](./README.md) for what belongs in a vendor document, why vendor documents are separate from Field Observations, and when a new vendor document should be created.

## Instructions

- Only create this document once multiple independent Field Observations about this vendor have been corroborated into Knowledge, per [KNOWLEDGE-LIFECYCLE.md](../KNOWLEDGE-LIFECYCLE.md).
- Reference the specific Field Observation numbers from [FIELD-OBSERVATIONS.md](../FIELD-OBSERVATIONS.md) that corroborate each section.
- Describe operational experience only — deployment characteristics, naming conventions, and operational context. Do not include product specifications or marketing language.
- Do not propose a specific benchmark case or classification rule here. Record what could inform them, not the change itself.
- Update this document as new corroborating observations arrive, rather than creating a duplicate document.

## Template

```markdown
# <Vendor Name>

## Overview

<A brief, neutral description of the product category this document covers for this
vendor. Not marketing copy — only what is operationally relevant to NetworkMapper.>

## Corroborating Observations

- Field Observation #<NNN> — <one-line description>
- Field Observation #<NNN> — <one-line description>

## Product Lines Observed

- <product or product line>
- <product or product line>

## Naming Conventions

<Hostname or identification patterns observed across this vendor's products,
including known factory-default patterns and common deviations from them.>

## Deployment Characteristics

<How this vendor's products are typically configured and used in the field —
typical environments, common companion devices, common deployment patterns.>

## Operational Context

<The operational role(s) this vendor's devices tend to play once deployed, and
how primary versus secondary roles are typically distinguished.>

## Benchmark Considerations

<Notes on how this Vendor Knowledge could inform a future benchmark case. Does
not add or modify benchmark data.>

## Classification Considerations

<Notes on how this Vendor Knowledge could inform a future classification rule.
Does not add or modify a classification rule.>

## Knowledge Maturity

<Observation | Knowledge | Benchmark | Classification | Validation | Architecture Review>

## Confidence

<Low | Medium | High>

## Last Updated

<Date this document was last revised, and what prompted the revision.>
```
