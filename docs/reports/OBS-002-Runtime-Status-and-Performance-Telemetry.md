# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — this sprint adds a new observability layer (a
publish/subscribe event bus, a telemetry recorder, a CLI renderer) that
sits alongside discovery/classification/reporting without changing any
of their public contracts in an incompatible way, changing scan
behavior, or introducing a new persisted data format. `NmapProvider` and
`DiscoveryEngine` each gained one new optional, defaulted constructor
parameter; every existing caller and test that doesn't pass it is
unaffected. No existing ADR (ADR-001 two-phase discovery, ADR-008
discovery/interpretation separation, ADR-009 correlated evidence) is
contradicted or superseded.

Recommended Next Sprint:
No single sprint is pre-selected. Two candidates surfaced but were
deliberately left out of scope: (1) a GUI subscriber — this sprint's own
constraint ("do not implement a GUI") — now has a concrete, tested
integration point (`RuntimeEventBus.subscribe`) to build against without
touching discovery code; (2) genuinely live per-host progress during
Service Enrichment (see Known Limitations) would require restructuring
`NmapProvider`'s single batched Nmap subprocess call per phase into
either a per-host loop or a streaming-XML/`--stats-every` read — a much
larger, riskier change to actual scan behavior that this sprint
deliberately did not make.

---

## Summary

Before this sprint, `Application.run()` printed status directly at
scattered points, with zero visibility into what was happening *during*
a long-running Nmap scan — an operator saw "NetworkMapper is starting"
and then nothing until the entire two-phase scan (which can run for
minutes) finished and a large diagnostics dump appeared all at once.
There was also no structured record of how long each phase took or how
long the run took in total; `ScanPhase.elapsed_seconds` existed but was
Nmap's own self-reported number for one phase, buried inside a larger
diagnostics printout, not a general-purpose runtime telemetry model.

This sprint introduces a new `networkmapper/runtime/` package — a
publish/subscribe event system that discovery, classification, and
report generation publish truthful, measurable status to, and that the
CLI (today) or a future GUI (without any discovery-code change)
subscribes to:

- **`RuntimeEvent`** — one phase-started, progress, or phase-completed
  event, carrying only directly observed state: a timestamp, an
  optional free-text "current activity" message, and an optional
  `ProgressMeasurement` (`completed`, `unit_label`, and `total` — `total`
  only ever set when genuinely known in advance, never guessed).
- **`RuntimeEventBus`** — a minimal subscribe/publish dispatcher.
  Producers always have a real bus (defaulting to a fresh,
  subscriber-less one), so publishing is unconditionally safe and no
  producer ever null-checks whether anyone is listening.
- **`RuntimeTelemetryRecorder`** — subscribes to the bus and builds
  `PhaseTelemetry` records (start time, completion time, duration) plus
  total run time, decoupled from any rendering so it's directly reusable
  by future benchmarking/performance analysis.
- **`CliRuntimeEventRenderer`** — the CLI's own subscriber; the only
  thing that turns events into console text.
- **`render_runtime_summary()`** — a pure function rendering the final
  per-phase-duration + total-runtime summary from a
  `RuntimeTelemetryRecorder`, independently testable without capturing
  stdout.

`NmapProvider` now publishes real Host Discovery and Service Enrichment
events (start, per-host progress where genuinely observable, and
completion). `DiscoveryEngine` now publishes real Classification events
around its own per-device classification pass. `Application.run()`
publishes Application Startup, Report Generation, and Completion events
directly (these aren't discovery's responsibility) and prints the final
runtime summary as the last thing it does.

The pre-existing detailed "Discovery Diagnostics" / "Classification
Summary" / "Sample Classifications" dumps were left completely
untouched — they remain a valuable detailed report shown once
everything finishes. The new event stream is an additional, real-time
layer that fires *during* the run, not a replacement for that dump.

No estimated percentage or ETA appears anywhere in this system —
verified directly by tests asserting the renderer's and summary's output
never contains `%`, `ETA`, or `remaining`.

---

## Files Changed

Production code:

- `networkmapper/runtime/__init__.py` — new, empty (matches
  `networkmapper/discovery/__init__.py`'s convention).
- `networkmapper/runtime/events.py` — new. `RuntimePhase`,
  `RuntimeEventKind`, `ProgressMeasurement`, `RuntimeEvent`,
  `RuntimeEventBus`.
- `networkmapper/runtime/telemetry.py` — new. `PhaseTelemetry`,
  `RuntimeTelemetryRecorder`.
- `networkmapper/runtime/cli_renderer.py` — new.
  `CliRuntimeEventRenderer`, `render_runtime_summary()`.
- `networkmapper/discovery/discovery_engine.py` — `DiscoveryEngine`
  gained an optional `event_bus` constructor parameter. `discover()` was
  restructured from one interleaved per-provider loop
  (discover-then-classify-per-device, per provider) into two passes:
  gather every provider's devices first, then classify all of them in a
  single, event-published pass. This is a **behavior-preserving**
  restructuring (see Testing Performed) needed so Classification's
  PHASE_STARTED event never fires before a provider's own Host
  Discovery/Service Enrichment events do.
- `networkmapper/discovery/nmap_provider.py` — `NmapProvider` gained an
  optional `event_bus` constructor parameter and a small `_publish()`
  helper. `_discover_single_pass()` and `_discover_with_enrichment()`
  now publish Host Discovery start/completion and (when enrichment
  actually runs) Service Enrichment start/per-host-progress/completion
  events around their existing Nmap calls. No Nmap argument, call
  count, or call shape changed.
- `networkmapper/application.py` — `run()` now constructs one
  `RuntimeEventBus`/`RuntimeTelemetryRecorder` per run, subscribes the
  CLI renderer and the telemetry recorder, publishes Application
  Startup/Report Generation/Completion events itself, passes the bus
  into `NmapProvider`/`DiscoveryEngine`, and prints
  `render_runtime_summary(telemetry)` as the final output. Added a small
  private `_publish()` helper for the three phases it owns directly.

Tests:

- `tests/test_runtime_events.py` — new. `RuntimeEventBus`
  subscribe/publish behavior (no-subscriber no-op, single/multiple
  subscribers, publish order) and `ProgressMeasurement`'s `total`
  default.
- `tests/test_runtime_telemetry.py` — new. Phase duration computation,
  intermediate PROGRESS events not creating phase records, multiple
  phases recorded independently and in completion order, total-runtime
  spanning first start to last completion, and the edge case of a
  completion event with no matching start.
- `tests/test_runtime_cli_renderer.py` — new. Phase-started/completed
  rendering (with and without activity/progress, with and without a
  known total), PROGRESS events deliberately not rendered, and direct
  assertions that neither the renderer nor the summary ever emit `%`,
  `ETA`, or "remaining".
- `tests/test_discovery_engine.py` — new (no test file existed for
  `DiscoveryEngine` before this sprint). Covers classification/graph
  behavior directly (previously only exercised indirectly, through a
  fully-mocked `DiscoveryEngine` in `test_application_cli.py`), plus
  Classification event ordering/counts, the zero-devices case, and that
  `discover()` still works with no event bus supplied.
- `tests/test_nmap_provider_runtime_events.py` — new. FAST publishes
  only Host Discovery events; STANDARD/DEEP with zero hosts publishes
  only Host Discovery events (Service Enrichment genuinely doesn't run,
  so it correctly publishes nothing); STANDARD with hosts publishes the
  full Host Discovery → Service Enrichment (with per-host PROGRESS
  ticks) sequence in order; DEEP also publishes Service Enrichment
  events; no event bus supplied doesn't raise.
- `tests/test_application_cli.py` — five existing `provider_mock.
  assert_called_once_with(...)` assertions updated to include
  `event_bus=ANY`, since `NmapProvider` is now always constructed with
  one. No other assertion changed — every existing printed-substring
  assertion still passes unmodified.
- `tests/test_nmap_provider_scan_profile.py`,
  `tests/test_nmap_provider_deep_profile.py`,
  `tests/test_nmap_provider_run_diagnostics.py` — **not changed**; all
  pass unmodified, confirming Nmap call arguments/counts/shapes are
  untouched.

---

## Runtime Event Architecture

```
Producers                          Bus                    Subscribers
----------                         ---                    -----------
NmapProvider          --publish--> RuntimeEventBus --+--> CliRuntimeEventRenderer
  (Host Discovery,                                    |      (prints real-time
   Service Enrichment)                                |       console status)
                                                       |
DiscoveryEngine        --publish-->                   +--> RuntimeTelemetryRecorder
  (Classification)                                    |      (records phase timing,
                                                        |       reusable for
Application             --publish-->                   |       benchmarking)
  (Application Startup,                                |
   Report Generation,                                  +--> (future) GUI subscriber
   Completion)                                                (same interface, zero
                                                                discovery/classification
                                                                changes required)
```

- **Producers never know who's listening.** `NmapProvider` and
  `DiscoveryEngine` each hold a `RuntimeEventBus` (defaulting to a
  fresh, empty one) and call `publish()` unconditionally — no
  `if event_bus is not None` branching at any call site, and a bus with
  zero subscribers is a genuine no-op, not a special case.
- **`Application.run()` is the sole composition point.** It builds the
  bus, subscribes the CLI renderer and telemetry recorder to it, and is
  the only thing that hands the *same* bus instance to `NmapProvider`
  and `DiscoveryEngine` — those two classes have no knowledge of each
  other or of the CLI.
- **Six phases, in execution order**, as `RuntimePhase`: Application
  Startup → Host Discovery → Service Enrichment → Classification →
  Report Generation → Completion. Ownership is split by who actually
  knows when each phase starts/stops:
  - `NmapProvider` owns Host Discovery and Service Enrichment (it's the
    only thing that knows when an Nmap phase's subprocess call starts
    and returns).
  - `DiscoveryEngine` owns Classification (it's the only thing that
    runs `DeviceClassifier` and knows when that pass starts/ends).
  - `Application` owns Application Startup, Report Generation, and
    Completion directly, since none of those are discovery's
    responsibility.
- **Every event kind is one of three**: `PHASE_STARTED`, `PROGRESS`, or
  `PHASE_COMPLETED`. There's no fourth "activity update" kind —
  free-text "current activity" is just an optional field on any event,
  supplied by whichever phase knows what's happening (e.g. "Scanning
  172.16.100.0/24 for live hosts...").
- **`ProgressMeasurement.unit_label` is supplied by the producer, not
  guessed by the renderer.** `CliRuntimeEventRenderer` never branches on
  `event.phase` to decide what word to print ("Hosts Found" vs. "Hosts
  Completed" vs. "Devices Classified") — the phase that emits the event
  already knows what it's counting, and a future GUI gets the same
  label for free without its own phase-name-to-label mapping.
- **The CLI renders only `PHASE_STARTED` and `PHASE_COMPLETED`, not
  every `PROGRESS` tick** — see Known Limitations for why, and for why
  the full `PROGRESS` stream still exists on the bus regardless.

---

## Telemetry Collected

`RuntimeTelemetryRecorder` subscribes to the same bus and, independent
of any console output, builds:

- **Per-phase `PhaseTelemetry`**: `phase`, `started_at`, `completed_at`,
  `duration_seconds` (computed directly from the two timestamps — never
  estimated), and the phase's final `ProgressMeasurement` if it had one.
- **`total_runtime_seconds`**: the span from the very first
  `PHASE_STARTED` event of the run to the most recent
  `PHASE_COMPLETED` event.

This is exposed as `telemetry.phases` (a tuple, in completion order) and
`telemetry.total_runtime_seconds`, with no dependency on `print()` or any
other presentation concern — the same object could be serialized to
JSON, compared across two runs, or fed into a future benchmark report
without any change to `NmapProvider`, `DiscoveryEngine`, or
`Application`.

---

## CLI Output Example

Captured from a real (mocked-Nmap) end-to-end run of
`Application().run()` with `--scan-profile standard` against 3 hosts —
unedited except for truncating the pre-existing Discovery
Diagnostics/Classification Summary dump in the middle, which is
unchanged from before this sprint:

```
NetworkMapper is starting...


Application Startup
Parsing CLI arguments...
Scan profile: STANDARD

Host Discovery
Scanning 172.16.100.0/24 for live hosts...
3 Hosts Found

Service Enrichment
Enriching 3 discovered host(s)...
3 / 3 Hosts Completed

Classification
Classifying 3 discovered device(s)...
3 Devices Classified

Discovery Diagnostics
----------------------------------------
[... existing, unchanged detailed diagnostics dump ...]

Classification Summary
----------------------------------------
[... existing, unchanged classification counts + sample table ...]

Report Generation
Generating Markdown and CSV reports...
✓ CSV exported to output\2026-08-11_120747_standard\devices.csv
✓ Markdown exported to output\2026-08-11_120747_standard\report.md

Completion
Finalizing project persistence...
Customer Name          : Test Network
Device Count (Before)  : 3
Device Count (After)   : 3

✓ Persistence validation successful.

Runtime Summary
----------------------------------------
Application Startup          0.02s
Host Discovery                0.00s
Service Enrichment            0.00s
Classification                 0.00s
Report Generation              0.00s
Completion                     0.01s

Total Runtime: 0.03s
```

(Phase durations are near-zero here because Nmap itself was mocked;
against a real network they reflect real elapsed wall-clock time per
phase, since every timestamp is `datetime.now()` at the moment each
event is actually published.)

---

## Testing Performed

`python -m unittest discover -s tests -p "test_*.py"`: **293 passed, 0
failed** (261 before this sprint + 32 new, across five new test files
covering the event bus, telemetry recorder, CLI renderer, the
previously-untested `DiscoveryEngine`, and `NmapProvider`'s new event
emission).

`devtools.validate.run_full_validation()`: **PASS** — 293/293 unit
tests, and all three benchmark datasets (enterprise, homelab,
small_office) unchanged at 100.0% accuracy (expected — no
classification or evidence-collection logic changed).

Manual end-to-end verification: ran `Application().run()` with a mocked
`nmap.PortScanner` (3 hosts, STANDARD profile) with no other mocking —
real `DiscoveryEngine`, real `NmapProvider`, real classifier, real
exporters, real `RuntimeEventBus`/`RuntimeTelemetryRecorder`/
`CliRuntimeEventRenderer`. Confirmed the exact output shown above,
including correctly-classified devices, real report artifacts written
to a real versioned directory (REPORT-002, unaffected), and a runtime
summary with all six phases and a total.

Against this sprint's explicit Testing checklist:

- **Every phase emits start and completion events** — confirmed for all
  six phases: `test_fast_profile_publishes_host_discovery_start_and_
  completion_only`, `test_standard_profile_publishes_host_progress_
  during_enrichment`, `test_classification_phase_events_are_published_
  in_order` (`tests/test_discovery_engine.py`), and the manual run above
  showing Application Startup/Report Generation/Completion events.
- **Phase timing is recorded correctly** —
  `test_phase_duration_is_computed_from_start_to_completion` and
  `test_total_runtime_spans_first_start_to_last_completion`
  (`tests/test_runtime_telemetry.py`), using exact `datetime` fixtures
  so the arithmetic is checked precisely (e.g. `4.5` seconds from a
  500ms-resolution timestamp pair), not just "some positive number".
- **Host progress updates during enrichment** — confirmed directly:
  `test_standard_profile_publishes_host_progress_during_enrichment`
  asserts three `PROGRESS` events fire in order with `completed`
  incrementing `1, 2, 3` against a known `total=3`, between Service
  Enrichment's `PHASE_STARTED` and `PHASE_COMPLETED`. See Known
  Limitations for the honest caveat on *when*, wall-clock-wise, these
  fire relative to the actual scan.
- **Existing scan behavior is unchanged** — confirmed by every existing
  Nmap-argument/call-count assertion in `test_nmap_provider_scan_
  profile.py`, `test_nmap_provider_deep_profile.py`, and
  `test_nmap_provider_run_diagnostics.py` passing completely unmodified;
  none of those three files needed a single edit.
- **Existing tests continue to pass** — 261/261 pre-existing tests still
  pass; the only test-file edits were five `assert_called_once_with`
  calls in `test_application_cli.py` gaining `event_bus=ANY` (the new
  constructor argument itself, not a behavior change), and none of that
  file's stdout-substring assertions needed to change.

---

## Known Limitations

- **Service Enrichment's per-host `PROGRESS` events are real, but not
  smoothly "live" against wall-clock time — this is a deliberate,
  disclosed constraint, not a hidden gap.** `NmapProvider` invokes Nmap
  once per phase, covering *every* discovered host in a single blocking
  subprocess call (confirmed directly in `nmap_provider.py`: one
  `self._scanner.scan(hosts=enrichment_hosts, ...)` call for the whole
  batch, not one call per host). The per-host `PROGRESS` events this
  sprint adds are published in the loop that processes that single
  call's *already-complete* results (parsing evidence, merging SMB/RDP
  identity, running `diagnose_host()`) — real, measurable, sequential
  per-host work, but all of it happens in a fast burst immediately
  *after* the (potentially multi-minute) network scan itself finishes,
  not spread across the scan's real duration. This sprint's own
  constraint — "only expose truthful runtime state and measurable
  progress" — is why no attempt was made to fabricate smoother-looking
  ticks: doing so would mean reporting progress the code doesn't
  actually have visibility into. Making these ticks genuinely live would
  require either restructuring the single batched Nmap call into a
  per-host loop (a real change to scan performance/semantics, and one
  that would break the batched-call assertions in
  `test_nmap_provider_scan_profile.py`/`test_nmap_provider_deep_
  profile.py`) or parsing Nmap's own real-time `--stats-every`/streaming
  XML output instead of `python-nmap`'s blocking `.scan()` call —
  either is a substantially larger, riskier change than this sprint's
  scope, and neither was requested.
- **Host Discovery has no `total` by design, not by omission.** The
  number of hosts a scan will find isn't knowable before the scan
  finishes, so `ProgressMeasurement.total` is left `None` for Host
  Discovery's `PHASE_COMPLETED` event — it renders as a bare "N Hosts
  Found" rather than a fabricated "N / ???".
- **The CLI intentionally renders only `PHASE_STARTED`/
  `PHASE_COMPLETED`, never intermediate `PROGRESS`.** Printing every
  tick as its own console line (e.g. once per classified device on a
  large network) would flood the console rather than provide useful
  real-time feedback, and this sprint's own CLI Output examples show
  exactly one progress line per phase. The full `PROGRESS` stream is
  still published for any other subscriber — a future GUI progress bar,
  or a future telemetry consumer wanting finer granularity — without
  any change to the producers.
