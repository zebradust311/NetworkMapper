# Validation Workflow

## Which Command to Use

- **`python -m devtools validate`** — fast, classifier-only regression. Use while iterating on classification rules, the classifier, or RuleResult evidence. Does not exercise discovery, exporters, the CLI, benchmark infrastructure, the classification workbench, project comparison, or project summary/reporting.
- **`python -m devtools validate --all`** — comprehensive: every discovered test module plus every discovered benchmark dataset. Use whenever a sprint touches anything outside the classification layer, and always before considering a sprint complete, regardless of what it touched.
- **`python -m devtools benchmark [dataset]`** — use to inspect one dataset's classification accuracy in detail (per-device-type breakdown), or after a classifier change to see specific impact. `validate --all` runs every dataset but only reports pass/fail per dataset, not the full accuracy report.
- **`python -m devtools diagnostics`** — quick environment sanity check (imports, project structure, one benchmark dataset). Not a substitute for `validate --all`.

## After Implementing a Sprint

1. Execute the appropriate validation target from the list above.
2. Use only the stdout/stderr produced by that execution.
3. Summarize the results.
4. Stop.

If additional validation is required, rerun the requested tests. Do not inspect cached output.

Never inspect VS Code workspaceStorage, GitHub Copilot chat-session-resources, `content.txt`, editor cache, temporary AI transcripts, or other IDE-generated files. Never execute commands that reference those locations. Project source files and current test execution are the authoritative sources.

See [docs/reports/TEST-001-Validation-Coverage-Assessment.md](../reports/TEST-001-Validation-Coverage-Assessment.md) for the investigation behind the fast/comprehensive split.
