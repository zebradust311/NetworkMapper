# Prompt Templates

Three sprint types are used in this repository. Each has a canonical prompt shape, reflecting what has worked in practice.

## Investigation

```text
<ID> – <Name>

Objective

<what to investigate and why>

This is an investigation sprint.

Do not modify any files.

Required Reading

<documents to read first>

Tasks

<what the investigation must cover>

Deliverables

<report location and required sections>

Do not implement.

Do not commit.
```

## Architecture

```text
<ID> – <Name>

Objective

Create/update an ADR documenting <the decision>.

This sprint is architecture only.

No production code changes.

Tasks

1. Review existing ADRs for conflicts.
2. Draft the ADR (Context, Decision, Rationale, Consequences, Future Work).
3. Identify any minimal, targeted documentation cross-references.

Constraints

<explicit boundaries — for example, no schema changes, no implementation>

Deliverables

New ADR, minimal documentation integration, summary of modified files.
```

## Implementation

```text
<ID> – <Name>

Objective

<what to implement, referencing the approved investigation/architecture decision>

Required Reading

<documents to read first>

Tasks

<specific, scoped tasks>

Constraints

<explicit boundaries — what must not change>

Validation

<which validation command(s) to run — see validation-workflow.md>

Deliverables

Updated code, updated tests, validation results, git diff, concise summary,
and a mandatory Implementation Report (see docs/reports/README.md).

Do not commit.
```

See [docs/reports/ARCH-001A-Engineering-Workflow-Investigation.md](../reports/ARCH-001A-Engineering-Workflow-Investigation.md) for the evidence behind this shape.
