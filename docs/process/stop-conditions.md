# Mandatory Stop Conditions

Work must stop immediately — not be reasoned around — when any of the following occur. Stopping means: report the condition and await explicit human direction before continuing.

- **Requirements contradict themselves.** A sprint's own sections describe incompatible outcomes.
- **Repository contradicts the prompt.** The sprint assumes something exists (a file, an example, a prior decision) that isn't actually in the repository or its history.
- **Existing implementation already satisfies the sprint.** The requested work has already been done.
- **Scope expands beyond the approved sprint.** Completing the objective would require touching something outside what was approved.
- **An ADR becomes unexpectedly necessary.** The work surfaces a genuine product-architecture decision that wasn't anticipated by the sprint.
- **Validation contradicts implementation.** Validation results don't make sense given what was implemented (for example, an unexpected test count, or a test that shouldn't pass passing).
- **An engineering principle would be violated.** Completing the sprint as specified would require breaking backwards compatibility, skipping benchmarking, or breaking another principle in [engineering-principles.md](engineering-principles.md), without that being an explicit, approved part of the sprint.

See [docs/reports/ARCH-001A-Engineering-Workflow-Investigation.md](../reports/ARCH-001A-Engineering-Workflow-Investigation.md) for real examples of each of these occurring in this project's history.
