# devtools

`devtools` provides deterministic developer automation for NetworkMapper.

## Purpose

The package centralizes project-level development commands so contributors use a single canonical entrypoint instead of running ad hoc validation commands.

## Available Commands

- `validate`: Runs the canonical regression suite and prints a concise PASS/FAIL summary.
- `benchmark`: Runs the canonical benchmark workflow and writes JSON/Markdown reports.
- `compare`: Compares two benchmark JSON reports and summarizes improvements/regressions.
- `diagnostics`: Runs the canonical developer environment pre-flight checks.

## Usage

Run the standard validation suite:

```bash
python -m devtools validate
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
