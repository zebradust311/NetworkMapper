import unittest
from datetime import datetime

from networkmapper.runtime.events import (
    ProgressMeasurement,
    RuntimeEvent,
    RuntimeEventKind,
    RuntimePhase,
)
from networkmapper.runtime.telemetry import RuntimeTelemetryRecorder


class RuntimeTelemetryRecorderTest(unittest.TestCase):
    def test_no_phases_recorded_before_any_completion(self):
        recorder = RuntimeTelemetryRecorder()

        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.HOST_DISCOVERY,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime(2026, 8, 11, 9, 0, 0),
            )
        )

        self.assertEqual(recorder.phases, ())
        self.assertIsNone(recorder.total_runtime_seconds)

    def test_phase_duration_is_computed_from_start_to_completion(self):
        recorder = RuntimeTelemetryRecorder()
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.HOST_DISCOVERY,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime(2026, 8, 11, 9, 0, 0),
            )
        )
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.HOST_DISCOVERY,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime(2026, 8, 11, 9, 0, 4, 500000),
                progress=ProgressMeasurement(completed=89, unit_label="Hosts Found"),
            )
        )

        self.assertEqual(len(recorder.phases), 1)
        phase_telemetry = recorder.phases[0]
        self.assertEqual(phase_telemetry.phase, RuntimePhase.HOST_DISCOVERY)
        self.assertEqual(phase_telemetry.duration_seconds, 4.5)
        self.assertEqual(phase_telemetry.final_progress.completed, 89)

    def test_intermediate_progress_events_do_not_create_phase_records(self):
        recorder = RuntimeTelemetryRecorder()
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.SERVICE_ENRICHMENT,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime(2026, 8, 11, 9, 0, 0),
            )
        )
        for completed in range(1, 4):
            recorder.handle_event(
                RuntimeEvent(
                    phase=RuntimePhase.SERVICE_ENRICHMENT,
                    kind=RuntimeEventKind.PROGRESS,
                    timestamp=datetime(2026, 8, 11, 9, 0, completed),
                    progress=ProgressMeasurement(
                        completed=completed, total=3, unit_label="Hosts Completed"
                    ),
                )
            )

        self.assertEqual(recorder.phases, ())

    def test_multiple_phases_are_recorded_independently_in_completion_order(self):
        recorder = RuntimeTelemetryRecorder()
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.HOST_DISCOVERY,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime(2026, 8, 11, 9, 0, 0),
            )
        )
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.HOST_DISCOVERY,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime(2026, 8, 11, 9, 0, 5),
            )
        )
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.CLASSIFICATION,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime(2026, 8, 11, 9, 0, 5),
            )
        )
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.CLASSIFICATION,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime(2026, 8, 11, 9, 0, 6),
            )
        )

        self.assertEqual(
            [phase_telemetry.phase for phase_telemetry in recorder.phases],
            [RuntimePhase.HOST_DISCOVERY, RuntimePhase.CLASSIFICATION],
        )
        self.assertEqual(recorder.phases[0].duration_seconds, 5.0)
        self.assertEqual(recorder.phases[1].duration_seconds, 1.0)

    def test_total_runtime_spans_first_start_to_last_completion(self):
        recorder = RuntimeTelemetryRecorder()
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.APPLICATION_STARTUP,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime(2026, 8, 11, 9, 0, 0),
            )
        )
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.APPLICATION_STARTUP,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime(2026, 8, 11, 9, 0, 1),
            )
        )
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.COMPLETION,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime(2026, 8, 11, 9, 0, 20),
            )
        )
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.COMPLETION,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime(2026, 8, 11, 9, 0, 21),
            )
        )

        self.assertEqual(recorder.total_runtime_seconds, 21.0)

    def test_completion_with_no_matching_start_uses_completion_timestamp_as_start(self):
        recorder = RuntimeTelemetryRecorder()

        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.REPORT_GENERATION,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime(2026, 8, 11, 9, 0, 0),
            )
        )

        self.assertEqual(recorder.phases[0].duration_seconds, 0.0)


if __name__ == "__main__":
    unittest.main()
