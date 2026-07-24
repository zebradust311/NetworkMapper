# devtools

`devtools` provides deterministic developer automation for NetworkMapper.

## Purpose

The package centralizes project-level development commands so contributors use a single canonical entrypoint instead of running ad hoc validation commands.

## Available Commands

- `validate`: Runs the canonical regression suite and prints a concise PASS/FAIL summary.

## Usage

Run the standard validation suite:

```bash
python -m devtools validate
```

## Future Tools

Planned developer tools may include commands for:

- benchmark execution
- documentation generation
- release checks
- focused test selection
