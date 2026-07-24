# devtools

`devtools` provides deterministic developer automation for NetworkMapper.

## Purpose

The package centralizes project-level development commands so contributors use a single canonical entrypoint instead of running ad hoc validation commands.

## Available Commands

- `validate`: Runs the canonical regression suite and prints a concise PASS/FAIL summary.
- `benchmark`: Runs the canonical benchmark workflow and writes JSON/Markdown reports.

## Usage

Run the standard validation suite:

```bash
python -m devtools validate
```

Run the standard benchmark workflow:

```bash
python -m devtools benchmark
```

## Future Tools

Planned developer tools may include commands for:

- documentation generation
- release checks
- focused test selection
