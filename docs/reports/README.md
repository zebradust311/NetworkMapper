# Engineering Reports

This directory contains investigation reports generated during engineering
sprints.

These reports capture the research, analysis, and rationale that lead to
engineering decisions.

Reports are historical engineering artifacts. They are not normative
architecture documentation and do not supersede ADRs or other architecture
documents.

## Guiding Principle

Reports capture **why** an engineering decision was made.

Architecture documents describe the resulting design.

Knowledge documents capture operational experience and field observations.

These three document types complement one another and should not duplicate
content.

## Naming Convention

```
<Sprint ID>-<Short-Description>.md
```

Examples:

- FEAT-002A-Discovery-Evidence-Assessment.md
- TEST-001-Validation-Coverage-Assessment.md
- ARCH-005-Discovery-Architecture-Review.md

## Investigation Status

Every report begins with the following status block:

```text
# Status

Investigation Complete

Implementation: Not Started / In Progress / Completed

Production Code Modified: Yes / No

ADR Required: Yes / No

Recommended Next Sprint:
<Sprint ID – Sprint Name>
```

This provides a concise executive summary of the investigation outcome before
the detailed analysis begins.

## Report Format

Unless a sprint requires otherwise, reports should follow this structure:

```text
# Status

Executive Summary

Investigation

Findings

Recommendations

Risks

Assumptions

ADR Considerations (if applicable)
```

Additional sections may be included when appropriate for the investigation.

## Lifecycle

Engineering reports are historical artifacts.

They document the investigation that led to an engineering decision and are
not updated after completion except to:

- Correct factual errors.
- Fix broken references.
- Correct formatting issues.

If a later investigation revisits the same topic, create a new report rather
than modifying an existing one. This preserves the engineering history and
decision-making process.

## Relationship to Other Documentation

| Documentation | Purpose | Living Document |
|--------------|---------|-----------------|
| `docs/architecture/` | Canonical architecture and ADRs | Yes |
| `docs/knowledge/` | Operational knowledge and field observations | Yes |
| `docs/reports/` | Investigation reports and engineering analyses | No |

Engineering reports provide historical context for engineering decisions.
Architecture documents define the approved design.
Knowledge documents capture lessons learned from real-world deployments.