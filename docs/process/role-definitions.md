# Role Definitions

NetworkMapper's engineering process distinguishes four roles. A single AI assistant may play multiple AI roles across one sprint, but the responsibilities below remain distinct — naming them explicitly makes it possible to deliberately split them across separate sprint turns when that's useful (for example, a dedicated review-only pass).

## Human Architect

Owns product-architecture and process decisions. Approves ADRs, approves sprints, and decides when to override or refine an investigation's recommendation. Holds final authority over scope and direction.

## AI Investigator

Performs investigation-only sprints. Reads required documents, gathers evidence directly from the repository (git history, code, tests, benchmarks), and reports findings without modifying anything. Responsible for surfacing discrepancies rather than resolving them unilaterally.

## AI Implementer

Performs implementation sprints within an approved, scoped sprint. Writes code, tests, and benchmark fixtures; runs validation; reports results and a git diff. Does not commit and does not expand scope beyond what was approved.

## AI Reviewer

Validates a completed implementation before it's reported as ready for human approval. Confirms scope stayed within bounds, confirms validation actually covered the right areas (for example, choosing `validate --all` over `validate` when a change touches more than classification), and confirms no unrelated files changed.

See [docs/reports/ARCH-001A-Engineering-Workflow-Investigation.md](../reports/ARCH-001A-Engineering-Workflow-Investigation.md) for how these roles were observed operating in practice.
