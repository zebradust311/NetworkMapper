from __future__ import annotations

from networkmapper.runtime.events import ProgressMeasurement, RuntimeEvent, RuntimeEventKind
from networkmapper.runtime.telemetry import RuntimeTelemetryRecorder


class CliRuntimeEventRenderer:
    """Renders runtime events as real-time console output.

    OBS-002: discovery/classification/reporting publish events; this is
    the CLI's own subscriber that turns them into console text — the
    only place that does so. A future GUI subscribes its own renderer to
    the same `RuntimeEventBus` instead of this class being extended or
    discovery logic changing.

    Deliberately renders only PHASE_STARTED and PHASE_COMPLETED, not
    every intermediate PROGRESS tick: OBS-002's own CLI Output examples
    show exactly one progress line per phase, and a CLI printing every
    tick to a new line (e.g. once per classified device) would flood the
    console rather than provide useful real-time feedback. The full
    PROGRESS stream is still published on the bus for any other
    subscriber (telemetry, or a future GUI progress bar) that wants
    finer granularity.
    """

    def handle_event(self, event: RuntimeEvent) -> None:
        """Print one line of real-time status for a published event.
        Bind this as a RuntimeEventBus subscriber."""
        if event.kind == RuntimeEventKind.PHASE_STARTED:
            print(f"\n{event.phase.value}")
            if event.activity:
                print(event.activity)
        elif event.kind == RuntimeEventKind.PHASE_COMPLETED:
            if event.progress is not None:
                print(_format_progress(event.progress))
            elif event.activity:
                print(event.activity)


def _format_progress(progress: ProgressMeasurement) -> str:
    """Render a progress measurement as "N / Total Label" when the total
    is known, or a bare "N Label" when it isn't — never a percentage."""
    if progress.total is not None:
        return f"{progress.completed} / {progress.total} {progress.unit_label}"

    return f"{progress.completed} {progress.unit_label}"


def render_runtime_summary(telemetry: RuntimeTelemetryRecorder) -> str:
    """Render the final CLI summary: each phase's duration, then total runtime.

    A pure function over already-recorded `RuntimeTelemetryRecorder`
    state, kept separate from `CliRuntimeEventRenderer` so it's directly
    testable without capturing stdout, and reusable wherever a run's
    telemetry needs to be presented (a report, a benchmark comparison)
    without depending on live event rendering.
    """
    lines = ["", "Runtime Summary", "-" * 40]

    if not telemetry.phases:
        lines.append("No phases recorded.")
        return "\n".join(lines)

    for phase_telemetry in telemetry.phases:
        lines.append(
            f"{phase_telemetry.phase.value:<24} {phase_telemetry.duration_seconds:>8.2f}s"
        )

    lines.append("")
    total_runtime_seconds = telemetry.total_runtime_seconds
    if total_runtime_seconds is not None:
        lines.append(f"Total Runtime: {total_runtime_seconds:.2f}s")

    return "\n".join(lines)
