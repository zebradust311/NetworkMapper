# devtools

`devtools` provides deterministic developer automation for NetworkMapper.

## Purpose

The package centralizes project-level development commands so contributors use a single canonical entrypoint instead of running ad hoc validation commands.

## Available Commands

- `validate`: Runs the fast classifier regression suite and prints a concise PASS/FAIL summary.
- `validate --all`: Runs every test module under `tests/` plus every benchmark dataset under `benchmarks/`, discovered automatically.
- `benchmark`: Runs the canonical benchmark workflow and writes JSON/Markdown reports.
- `compare`: Compares two benchmark JSON reports and summarizes improvements/regressions.
- `diagnostics`: Runs the canonical developer environment pre-flight checks.

## Which Command Should I Use?

- **`validate`** — use during focused iteration on classification rules, the classifier, or RuleResult evidence. Fast (well under a second) because it runs only the classification-layer test modules.
- **`validate --all`** — use before considering any sprint complete, and always when a change touches discovery, exporters, the CLI, benchmark infrastructure, the classification workbench, project comparison, or project summary/reporting. `validate` alone does not exercise any of these areas.
- **`diagnostics`** — use for a quick environment sanity check (imports, project structure, one benchmark dataset). Not a substitute for `validate --all` — it runs the same fast classifier suite plus a single benchmark dataset, not the full picture.
- **`benchmark [dataset]`** — use to inspect one dataset's classification accuracy in detail, or after a classifier change to see per-device-type impact. `validate --all` runs every dataset but only reports pass/fail per dataset; use `benchmark` directly for the full accuracy report.

See [docs/reports/TEST-001-Validation-Coverage-Assessment.md](../docs/reports/TEST-001-Validation-Coverage-Assessment.md) for the investigation behind this distinction.

## Usage

Run the fast validation suite:

```bash
python -m devtools validate
```

Run comprehensive validation (every test module, every benchmark dataset):

```bash
python -m devtools validate --all
```

Run the standard benchmark workflow:

```bash
python -m devtools benchmark
```

Compare benchmark reports:

```bash
python -m devtools compare
```

Compare explicit report files:

```bash
python -m devtools compare output/benchmarks/homelab.json output/benchmarks/enterprise.json
```

Run developer environment diagnostics:

```bash
python -m devtools diagnostics
```

## Future Tools

Planned developer tools may include commands for:

- documentation generation
- release checks
- focused test selection
