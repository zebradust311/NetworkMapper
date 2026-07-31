# Engineering Principles

These are NetworkMapper's core engineering principles for AI-assisted development. They apply to every sprint, regardless of type.

- **Investigate before implementing.** Understand the current state before changing it.
- **Evidence over assumptions.** Ground conclusions in what the repository, git history, tests, and benchmarks actually show — not in what seems likely.
- **Keep changes narrowly scoped.** A sprint has one objective. Unrelated cleanup, refactoring, or scope expansion belongs in a separate sprint.
- **Preserve backwards compatibility whenever practical.** Existing behavior should keep working unless a sprint explicitly changes it.
- **Validate before review.** Run the appropriate validation (see [validation-workflow.md](validation-workflow.md)) and report real results before requesting approval.
- **Human approval before commit.** Implementation is never committed without explicit human review and direction.
- **Benchmark classifier changes.** Any change to what evidence is available or how it's matched should be measured, not just unit-tested.
- **Stop and ask rather than guess.** When a sprint's instructions contradict each other, or the repository contradicts the prompt, stop and surface it — do not silently pick an interpretation. See [stop-conditions.md](stop-conditions.md).

Each of these principles is grounded in something this project has already observed happening, not stated as aspiration — see [docs/reports/ARCH-001A-Engineering-Workflow-Investigation.md](../reports/ARCH-001A-Engineering-Workflow-Investigation.md) for the evidence.
