# AI Development Guide

Version: 1.0

---

# Purpose

This document defines the engineering workflow used while developing
NetworkMapper with AI-assisted programming tools.

It exists to ensure that every implementation remains:

- Deterministic
- Reviewable
- Testable
- Maintainable

AI is used to accelerate implementation.

Humans remain responsible for architecture and engineering decisions.

---

# Core Principle

AI should implement engineering tasks.

Humans make engineering decisions.

AI writes code.

Humans approve architecture.

---

# Development Philosophy

Small changes are preferred over large changes.

Every sprint should have:

- One objective
- One implementation
- One review
- One commit

Avoid combining unrelated work.

---

# Sprint Workflow

The canonical sprint lifecycle is defined in
[docs/process/sprint-lifecycle.md](process/sprint-lifecycle.md):
Investigation → Architecture Review → Implementation → Validation → Human
Review → Commit.

Never skip review.

---

# AI Prompt Guidelines

Prompts should define:

- Objective
- Requirements
- Constraints
- Validation
- Execution Policy

Avoid vague prompts.

Bad

```
Improve the classifier.
```

Good

```
INTEL-003

Expand Cisco switch heuristics using
multiple independent observations while
preserving rule ordering and first-match-wins.

Do not modify DeviceClassifier.
```

See [docs/process/prompt-templates.md](process/prompt-templates.md) for
copy-pasteable templates covering Investigation, Architecture, and
Implementation sprints.

---

# Execution Policy

Every implementation prompt should end with:

```
Execution Policy

1. Read only the project files required.

2. Keep changes within sprint scope.

3. Update only affected tests.

4. Run the smallest appropriate regression target.

5. If validation output is unavailable,
   rerun the requested tests.

6. Validate only using:

   • unittest output
   • pytest output
   • compiler/interpreter diagnostics
   • $LASTEXITCODE

7. Never inspect:

   • VS Code workspaceStorage
   • GitHub Copilot chat-session-resources
   • content.txt
   • editor cache
   • temporary AI transcripts
   • IDE-generated files

8. Never execute commands that reference
   those locations.

9. Summarize the validation.

10. Stop.
```

See [docs/process/stop-conditions.md](process/stop-conditions.md) for the
complete, mandatory set of situations that require stopping immediately.

---

# Review Process

AI implementation is never committed immediately.

Review:

- Architecture
- Scope
- Simplicity
- Test coverage
- Documentation

Only after review:

Commit.

---

# Validation Rules

Validation commands and when to use each — `validate`, `validate --all`,
`benchmark`, `diagnostics` — are defined in
[docs/process/validation-workflow.md](process/validation-workflow.md).

Never validate using IDE artifacts. If validation is incomplete, rerun the
tests — do not inspect cached output.

---

# Safe Commands

Normally approve:

```
python -m devtools validate

python -m devtools benchmark

pytest ...

python -m networkmapper...

git status

git add

git commit

git push

$LASTEXITCODE

Get-ChildItem

Get-Content (project files)

mkdir

New-Item
```

---

# Review Commands

Review before approving:

```
git reset

git clean

Remove-Item

Move-Item

Rename-Item

Large refactors

Bulk deletes
```

---

# Never Approve

Immediately reject commands referencing:

```
workspaceStorage

chat-session-resources

content.txt

AppData\Roaming\Code

VS Code cache

editor cache

temporary AI transcript

IDE implementation files
```

These are implementation details of the IDE.

They are never authoritative.

---

# Human Responsibilities

Humans decide:

- Architecture
- Folder structure
- Naming
- Scope
- Trade-offs
- Acceptance

AI should never decide project direction.

---

# Code Review Checklist

Before every commit verify:

✓ Scope stayed focused

✓ No unrelated files changed

✓ Tests updated

✓ Tests passed

✓ Documentation updated

✓ No architecture drift

✓ No unnecessary abstraction

✓ No duplicated logic introduced

---

# Commit Checklist

Every completed sprint receives:

- One commit

- One descriptive message

Examples

```
CLASS-007:
Introduce RuleResult framework

INTEL-002:
Expand printer heuristics

DEV-001:
Add benchmark CLI

ACC-001:
Introduce benchmark framework
```

Avoid:

```
Update

Fix

Changes

Misc
```

---

# Documentation Checklist

Architecture changes update:

docs/architecture/

ROADMAP.md

ADR.md

Engineering changes update:

ENGINEERING.md

Process/workflow changes update:

docs/process/

Knowledge changes update:

docs/knowledge/

Investigation and implementation reports live in:

docs/reports/ (see docs/reports/README.md)

Developer workflow changes update:

AI-DEVELOPMENT-GUIDE.md

---

# AI Behaviors

Known GitHub Copilot behaviors:

• Attempts to inspect content.txt

Solution:

Skip.

• Attempts to inspect workspaceStorage

Solution:

Skip.

• Attempts to inspect
chat-session-resources

Solution:

Skip.

• Loses validation stdout

Solution:

Rerun python -m devtools validate.

Never recover cached output.

---

# Architecture First

Architecture changes require human review.

AI should not:

- Introduce compatibility layers

- Refactor unrelated systems

- Rename public APIs

unless explicitly requested.

---

# Continuous Improvement

Alternate development between:

Capability

↓

Engineering Quality

↓

Capability

↓

Engineering Quality

This keeps technical debt low.

---

# Engineering Metrics

Success is measured by:

- Maintainability

- Test coverage

- Benchmark accuracy

- Documentation quality

- Deterministic behavior

Not by lines of code.

---

# Product Vision

NetworkMapper should become the easiest way to:

- Discover

- Understand

- Document

- Compare

- Visualize

enterprise networks.

Every sprint should move the project closer to that goal.

---

# Final Principle

The goal is not simply to write code.

The goal is to build software that another engineer can understand,
trust, and confidently extend years later.