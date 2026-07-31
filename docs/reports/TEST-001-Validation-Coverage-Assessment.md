# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: Yes — adopting a fast/full validation split (this report's recommendation) is a Developer Platform architecture decision that extends ADR-007, and the finding that `validate` is intentionally classification-scoped rather than comprehensive is worth recording so it isn't later mistaken for an oversight.

Recommended Next Sprint:
TEST-002 – Introduce Full Validation Mode

---

# Executive Summary

`python -m devtools validate` runs exactly 75 of the repository's 125 unit tests (60%), and every one of those 75 belongs to the classification subsystem — the core classifier, the RuleResult/evidence framework, and all 8 individual classification rules. The other 50 tests, covering discovery (`NmapProvider`), the CLI entry point (`Application`), the entire benchmark infrastructure (`BenchmarkRunner`, 27 tests), both exporters, the classification workbench, project comparison, and project summary/reporting, are never run by `validate`, `diagnostics`, or any other devtools command.

Git history shows this was a deliberate design choice made once, in a single commit, and never revisited — not an oversight that accumulated over time. All 8 excluded test files already existed before `devtools/validate.py` was written; none were added afterward and simply forgotten. However, this sprint's own prior work (FEAT-002B) demonstrates the real cost of that scope: a genuine, currently-failing bug in `csv_exporter.py` is invisible to `validate` and was only found by manually running the full test suite outside the canonical command.

Runtime is not a constraint on fixing this. The full 125-test suite runs in well under half a second of actual test execution; expanding coverage to everything would add a negligible, sub-second cost. The recommendation is to introduce an explicit full-validation mode alongside the existing fast one, rather than silently redefining what `validate` has always meant.

---

# Current Validation Pipeline

`python -m devtools validate` ([devtools/validate.py](../../devtools/validate.py)) loads and runs a hardcoded tuple, `STANDARD_REGRESSION_TESTS`, containing exactly 11 test module names via `unittest.defaultTestLoader`, and prints a pass/fail summary with counts. Its own CLI help text ([devtools/__main__.py](../../devtools/__main__.py)) describes it precisely: "Run canonical **classifier** regression validation."

`python -m devtools diagnostics` ([devtools/diagnostics.py](../../devtools/diagnostics.py)) wraps six checks: Python runtime, key imports, project structure, developer-platform file presence, `run_validation()` (the same 11 modules above), and one benchmark run — hardcoded to the `homelab` dataset only (`DEFAULT_BENCHMARK_DATASET = "homelab"`). It adds no test coverage beyond `validate`; it adds environment/file-presence checks and a single benchmark pass.

`python -m devtools benchmark [dataset]` runs one named dataset (default `homelab`) through `BenchmarkRunner` and writes JSON/Markdown reports. It never runs more than one dataset unless invoked repeatedly with different arguments.

`python -m devtools compare` diffs two previously-generated benchmark JSON reports. It has no independent validation role.

No linter, formatter, or static-analysis tool is configured anywhere in the repository (no `ruff.toml`, `.flake8`, `pyproject.toml`, `mypy.ini`, or `.pre-commit-config.yaml`). `.github/` contains only `copilot-instructions.md` — there is no CI workflow. All validation today is local and manually invoked.

---

# Validation Coverage Matrix

| Component | Covered by `validate`? | Validation Mechanism | Notes |
|---|---|---|---|
| Classification rules (8 rules) | **Yes** | 8 dedicated test files in `STANDARD_REGRESSION_TESTS` | Complete — every rule has its own whitelisted test file |
| `DeviceClassifier` / `RuleResult` framework | **Yes** | `test_classifier`, `test_rule_result_framework`, `test_device_classifier_evidence_api` | Core engine and evidence API fully covered |
| Evidence helpers (`evidence_helpers.py`) | **Yes** | `EvidenceHelpersTest` class inside `test_classifier.py` | Covered only because it lives inside an already-whitelisted file |
| Discovery (`NmapProvider`, scan profiles) | **No** | `test_nmap_provider_scan_profile.py` exists (8 tests) | Confirmed gap: FEAT-002B's port-list change passed `validate` without these tests ever running |
| `DiscoveryEngine` | **No** | No dedicated test file; touched only incidentally inside `test_application_cli.py` | Zero direct unit coverage of graph-insertion/classification-orchestration logic |
| CLI / `Application` entry point | **No** | `test_application_cli.py` exists (6 tests) | Covers scan-profile args and the workbench flag; excluded |
| Benchmark infrastructure (`BenchmarkRunner`) | **No** | `test_benchmark_runner.py` exists (**27 tests** — the largest file in the suite) | Covers accuracy calculation, mismatch detection, JSON/Markdown/console report generation, CLI parsing |
| Classification Workbench | **No** | `test_classification_workbench.py` exists (5 tests) | |
| CSV exporter | **No** | `test_csv_exporter.py` exists (1 test) | This test is **currently failing** (`AttributeError` in `csv_exporter.py`) — confirmed pre-existing and unrelated to any sprint in this series, and invisible to `validate` |
| Markdown exporter | **No** | `test_markdown_exporter.py` exists (1 test) | |
| Project comparison | **No** | `test_project_comparator.py` exists (1 test) | |
| Project summary/reporting | **No** | `test_project_summary.py` exists (1 test) | |
| `Project` model / `ProjectSerializer` (persistence) | **No dedicated test at all** | Only touched incidentally inside `test_application_cli.py` | Persistence is a "completed" Phase 1 milestone per ROADMAP.md with no dedicated regression test |
| `NetworkGraph` | **No dedicated test at all** | Only touched incidentally inside `test_csv_exporter.py` | |
| Benchmark JSON fixtures (`inventory.json`/`expected_results.json` syntax) | **Partial** | Only implicitly checked when `devtools benchmark <dataset>` is run against that specific dataset | `homelab` is the only dataset any devtools command runs by default; `enterprise`/`small_office` are only checked when manually specified |
| Linters / static analysis | **No** | None configured | No linter/formatter config exists in the repository |
| CI pipeline | **No** | None | No GitHub Actions workflow; all validation is local and manual |

---

# Missing Coverage

**Pattern:** every excluded test file maps cleanly onto "not the classification subsystem" — discovery, CLI, benchmark infrastructure, exporters, developer workbench, comparison, and reporting. Every included test file maps cleanly onto "the classification subsystem." There is no partial or inconsistent boundary; it is exact in both directions across all 19 test files.

**Chronology (evidence):** `devtools/validate.py` was authored in a single commit (`9ec5734`, DEV-003) and has never been modified since. Checking creation history for all 8 excluded test files shows every one of them already existed **before** that commit:

| Excluded file | Created in |
|---|---|
| `test_application_cli.py` | `21c906c` |
| `test_benchmark_runner.py` | `35a1021` |
| `test_classification_workbench.py` | `21c906c` |
| `test_csv_exporter.py` | `83abf9b` |
| `test_markdown_exporter.py` | `bc58c5b` |
| `test_nmap_provider_scan_profile.py` | `0e06601` |
| `test_project_comparator.py` | `dd123d4` |
| `test_project_summary.py` | `bc58c5b` |

**Conclusion: intentional, not oversight, not organic technical debt.** If these files had been created after `validate.py` and simply never added, that would point to process drift (a new test file lands, nobody updates the whitelist). Instead, every excluded file was already sitting in the repository when the whitelist was written, and was left out by choice — consistent with the CLI's own description of the command as "classifier regression validation," not general regression validation.

**But the scope decision has a real, now-demonstrated cost.** During this sprint series' FEAT-002B work, `python -m devtools validate` reported a clean pass after a discovery-layer change, without ever executing the discovery-layer tests that change touched. Separately, running the full suite for this investigation surfaced a genuine, currently-broken test (`test_csv_exporter.py`) that has evidently been failing silently with respect to the canonical command. A scope that was reasonable when `validate` was scoped to "the classifier" is easy to mistake for "the regression suite" as the project and its Sprint Workflow (ENGINEERING.md) have grown to lean on `devtools validate` as the default verification step for any sprint, regardless of which subsystem it touches.

---

# Runtime Analysis

Measured on this development environment:

| Run | Tests | Wall-clock time |
|---|---|---|
| `python -m devtools validate` (current, 11 modules) | 75 | ~0.55s (dominated by interpreter startup) |
| Full suite (`unittest discover`, all 19 files) | 125 | ~0.3s pure execution / ~1.3s wall-clock with startup |
| `python -m devtools benchmark <dataset>` (any one dataset) | — | ~0.5s each |
| `python -m devtools diagnostics` (validate + homelab benchmark + env checks) | — | ~0.57s |

All 125 tests are fast, in-memory `unittest` cases using mocks (e.g., `unittest.mock.patch` over `nmap.PortScanner`) — none perform real network I/O, real subprocess scanning, or sleeps. Adding the 50 currently-excluded tests to `validate` would add a fraction of a second. Adding the two currently-unused benchmark datasets (`enterprise`, `small_office`) to a "run everything" path would add roughly another second (two more ~0.5s dataset runs).

**Conclusion: runtime is not, and has never been, a valid reason to keep the excluded tests out of a comprehensive validation path.** The current scope is a design choice about what "the classifier regression suite" means, not a performance-driven tradeoff.

---

# Architectural Options

**A. Keep `validate` lightweight (status quo)**
- Benefit: preserves its current, accurate identity as a fast classifier-only regression check; no behavior change for anyone currently relying on it.
- Risk: leaves the demonstrated gap in place — non-classification changes (discovery, exporters, benchmark infrastructure, CLI) can pass `validate` while carrying real regressions, exactly as observed in FEAT-002B and with the currently-failing CSV exporter test.

**B. Expand `validate` in place to run all 19 test files**
- Benefit: closes the gap with the smallest possible interface change — no new command to learn.
- Risk: silently redefines what `validate` has always meant and what its own help text promises ("classifier regression validation"). Anyone (human or AI assistant) who has learned "validate is the fast, classification-focused check" would have that assumption invalidated without warning. Given ENGINEERING.md's emphasis on deliberate, minimal-surprise changes, silently repurposing an existing, working, accurately-named command is the riskiest of the three options despite being the least code.

**C. Introduce separate fast/full validation modes**
- Benefit: preserves `validate`'s existing, accurately-described scope and speed for classification-focused iteration, while adding an explicit, comprehensively-named option (e.g., a `--all` flag or a new `full-validate` subcommand) that runs all 19 test files plus all 3 benchmark datasets. Matches ADR-007's existing pattern of exposing developer workflows as distinct, explicitly-named subcommands rather than overloading one command's meaning.
- Risk: a second command only helps if people actually reach for it — the same "assumed sufficient" problem could simply move from `validate` to whichever narrower mode becomes the reflexive default. This is a process/documentation risk, not a technical one.

---

# Recommendation

**Option C — introduce an explicit full-validation mode alongside the existing `validate`.**

The runtime analysis rules out "keep it lightweight because it's faster" as the reason for the current scope — there is no meaningful performance cost to running everything. But Option B's in-place expansion changes the meaning of an existing, well-named, currently-accurate command without any signal to whoever depends on its current fast/narrow behavior. Option C gets the coverage benefit of B without that silent redefinition: `validate` keeps meaning exactly what its help text already says, and a new, explicitly comprehensive command (suggested: `python -m devtools validate --all`, matching the existing single-entry-point philosophy from ADR-007) becomes the thing a sprint touching discovery, exporters, benchmark infrastructure, or the CLI should reach for.

This recommendation should also prompt fixing the `Sprint Workflow`/`Validation Workflow` guidance in ENGINEERING.md to specify which validation mode a sprint should use based on what it touches, rather than defaulting every sprint to `devtools validate` regardless of scope — that guidance is what caused this investigation's own prior sprint to nearly rely on an incomplete signal.

---

# Risks

- Introducing a second command doesn't fix the underlying habit of defaulting to whichever one is faster to type; the recommendation only works if ENGINEERING.md's guidance is updated to route sprints to the right mode by what they touch (see TEST-002 scope).
- The complete absence of any CI workflow means neither validation mode runs automatically today regardless of scope — this report's recommendation improves what's available to run manually, but doesn't address the larger fact that nothing currently enforces running it. That is a separate, larger gap beyond this investigation's scope.
- The currently-failing `test_csv_exporter.py` test will surface as soon as any full-validation mode exists; fixing it is out of scope for this investigation and for TEST-002 as currently conceived, but should be triaged before or alongside that sprint so the new full mode doesn't launch already red.

---

# Assumptions

- Runtime measurements were taken on a single local development machine; absolute numbers will differ on other hardware or in CI, but the relative proportions (all tests are fast, mocked unit tests with no real I/O) should hold generally.
- "Comprehensive" in this report means "runs every existing test file and every existing benchmark dataset." It does not evaluate whether the tests themselves are well-designed or whether additional tests should be written — that is a separate question from whether existing tests are wired into the canonical command.
- The exact mechanism for a "full" mode (new flag vs. new subcommand) is left to TEST-002 to decide; this report only concludes that some explicit, separately-named comprehensive option is the right shape.

---

# ADR Considerations

An ADR is recommended if TEST-002 proceeds with the fast/full split, for two reasons: first, it extends ADR-007's existing decision that developer workflows are exposed as distinct, explicitly-named subcommands rather than by silently changing an existing one's behavior; second, it would formally record that `validate`'s classification-only scope is an intentional, historical design decision (evidenced above) rather than a defect — preventing a future contributor from "fixing" it by quietly expanding `validate` in place and reintroducing the exact ambiguity this report identifies.
