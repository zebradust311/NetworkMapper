# Engineering Handbook

This is the authoritative entry point for NetworkMapper's engineering workflow — how humans and AI assistants collaborate on this project.

`ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` cover engineering standards, product philosophy, and AI-specific behavioral guidance. This handbook covers the workflow itself: the sprint lifecycle, the principles behind it, who is responsible for what, when to stop, how to validate, and what a sprint prompt should look like.

## Documents in This Handbook

- [sprint-lifecycle.md](sprint-lifecycle.md) — the canonical sprint lifecycle: Investigation → Architecture Review → Implementation → Validation → Human Review → Commit.
- [engineering-principles.md](engineering-principles.md) — the core principles behind every sprint.
- [role-definitions.md](role-definitions.md) — Human Architect, AI Investigator, AI Implementer, AI Reviewer.
- [stop-conditions.md](stop-conditions.md) — situations that require work to stop immediately.
- [validation-workflow.md](validation-workflow.md) — when to use `validate`, `validate --all`, `benchmark`, and `diagnostics`.
- [prompt-templates.md](prompt-templates.md) — canonical prompt shapes for Investigation, Architecture, and Implementation sprints.

## Where Process Documentation Lives

- `docs/process/` (this directory) — the engineering workflow itself: lifecycle, principles, roles, stop conditions, validation, prompt templates.
- `docs/architecture/` — canonical, implemented product architecture, plus `docs/ADR.md` for architecture decisions.
- `docs/knowledge/` — operational knowledge and field observations.
- `docs/reports/` — investigation and implementation reports (see [docs/reports/README.md](../reports/README.md)).

`ENGINEERING.md` covers engineering standards, coding conventions, and product philosophy, and references this handbook for workflow. `docs/AI-DEVELOPMENT-GUIDE.md` covers AI-specific behavioral guidance (prompt writing, commit safety, human review) and also references this handbook for workflow, rather than each independently defining it.

## Sprint Prefix Taxonomy

| Prefix | Meaning | Example |
|---|---|---|
| `DISC-` | Discovery subsystem work | Two-phase STANDARD discovery |
| `CLASS-` | Classification rule framework | RuleResult migration |
| `EVID-` | Classification evidence/explainability | Evidence API |
| `INTEL-` | Classifier heuristic improvements | Expanded heuristics |
| `ACC-` | Benchmark accuracy tooling | Confusion matrix |
| `DEV-` | Developer tooling | Benchmark CLI |
| `DOC-` / `DOCS-` | Documentation-only changes | Refresh project documentation |
| `KNOW-` | Knowledge Framework | Field observations, vendor knowledge |
| `ARCH-` | Product or process architecture | ADRs, this handbook |
| `FEAT-` | Feature investigation/implementation | Evidence-driven classification review |
| `TEST-` | Validation/test infrastructure | Validation coverage assessment |

When a new sprint doesn't fit an existing prefix, prefer the closest match over inventing a new one. Introduce a new prefix only when the work is a genuinely new category, and add it to this table when it is.

## Provenance

This handbook was created by ARCH-001B, implementing the recommendations approved in [docs/reports/ARCH-001A-Engineering-Workflow-Investigation.md](../reports/ARCH-001A-Engineering-Workflow-Investigation.md).
