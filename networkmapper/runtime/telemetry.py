from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from networkmapper.runtime.events import (
    ProgressMeasurement,
    RuntimeEvent,
    RuntimeEventKind,
    RuntimePhase,
)


@dataclass(frozen=True)
class PhaseTelemetry:
    """Recorded timing and final measurable progress for one completed phase.

    Attributes:
        phase: The phase this record describes.
        started_at: When the phase's PHASE_STARTED event was published.
        completed_at: When the phase's PHASE_COMPLETED event was published.
        duration_seconds: `completed_at - started_at`, in seconds.
        final_progress: The progress measurement attached to the
            PHASE_COMPLETED event, if any.
    """

    phase: RuntimePhase
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    final_progress: ProgressMeasurement | None


@dataclass
class RuntimeTelemetryRecorder:
    """Subscribes to a RuntimeEventBus and builds a reusable record of
    phase timing and final progress.

    OBS-002: this is the shared source of truth for the CLI's runtime
    summary, and is intentionally decoupled from any rendering so it can
    be reused by future benchmarking/performance analysis without
    depending on CLI output at all.
    """

    _phase_started_at: dict[RuntimePhase, datetime] = field(default_factory=dict)
    _completed_phases: list[PhaseTelemetry] = field(default_factory=list)
    _run_started_at: datetime | None = field(default=None)
    _run_completed_at: datetime | None = field(default=None)

    def handle_event(self, event: RuntimeEvent) -> None:
        """Record a published event. Bind this as a RuntimeEventBus subscriber."""
        if event.kind == RuntimeEventKind.PHASE_STARTED:
            self._phase_started_at[event.phase] = event.timestamp
            if self._run_started_at is None:
                self._run_started_at = event.timestamp
        elif event.kind == RuntimeEventKind.PHASE_COMPLETED:
            started_at = self._phase_started_at.get(event.phase, event.timestamp)
            duration_seconds = (event.timestamp - started_at).total_seconds()
            self._completed_phases.append(
                PhaseTelemetry(
                    phase=event.phase,
                    started_at=started_at,
                    completed_at=event.timestamp,
                    duration_seconds=duration_seconds,
                    final_progress=event.progress,
                )
            )
            self._run_completed_at = event.timestamp

    @property
    def phases(self) -> tuple[PhaseTelemetry, ...]:
        """Return the completed phases, in the order they finished."""
        return tuple(self._completed_phases)

    @property
    def total_runtime_seconds(self) -> float | None:
        """Return elapsed time from the first PHASE_STARTED to the most
        recent PHASE_COMPLETED, or `None` if the run hasn't produced both yet."""
        if self._run_started_at is None or self._run_completed_at is None:
            return None

        return (self._run_completed_at - self._run_started_at).total_seconds()
