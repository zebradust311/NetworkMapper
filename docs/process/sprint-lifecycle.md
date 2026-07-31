# Sprint Lifecycle

This is the canonical sprint lifecycle for NetworkMapper. `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` reference this document rather than each independently defining the workflow.

## The Lifecycle

```
Investigation
    │  (docs/reports/<ID>-<Description>.md — only when genuinely warranted;
    │   trivial sprints may skip straight to Implementation)
    ▼
Architecture Review
    │  (only when the investigation surfaces a product-architecture question;
    │   produces an ADR if a decision is made, or a note that none was needed)
    ▼
Implementation
    │  (scoped strictly to the approved sprint; no unrelated cleanup)
    ▼
Validation
    │  (python -m devtools validate, or validate --all when the change
    │   touches anything outside classification — see validation-workflow.md)
    ▼
Human Review
    │  (git diff + concise summary; approval requested explicitly)
    ▼
Commit
```

## Notes

Not every sprint needs every stage. A one-line documentation fix does not need a full Investigation report. When a stage is skipped, say so explicitly (for example, "no Architecture Review needed — no product-architecture question here") rather than leaving its absence unexplained.

Commit is a distinct, human-triggered step. AI assistants do not commit on their own initiative — every sprint stops after Human Review and waits for explicit direction.

See also: [engineering-principles.md](engineering-principles.md), [role-definitions.md](role-definitions.md), [stop-conditions.md](stop-conditions.md).

For the evidence behind this lifecycle, see [docs/reports/ARCH-001A-Engineering-Workflow-Investigation.md](../reports/ARCH-001A-Engineering-Workflow-Investigation.md).
