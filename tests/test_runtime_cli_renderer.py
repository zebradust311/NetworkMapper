import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime

from networkmapper.runtime.cli_renderer import CliRuntimeEventRenderer, render_runtime_summary
from networkmapper.runtime.events import (
    ProgressMeasurement,
    RuntimeEvent,
    RuntimeEventKind,
    RuntimePhase,
)
from networkmapper.runtime.telemetry import RuntimeTelemetryRecorder


class CliRuntimeEventRendererTest(unittest.TestCase):
    def _render(self, event: RuntimeEvent) -> str:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            CliRuntimeEventRenderer().handle_event(event)
        return stdout.getvalue()

    def test_phase_started_prints_phase_name_and_activity(self):
        output = self._render(
            RuntimeEvent(
                phase=RuntimePhase.HOST_DISCOVERY,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime.now(),
                activity="Scanning 172.16.100.0/24 for live hosts...",
            )
        )

        self.assertIn("Host Discovery", output)
        self.assertIn("Scanning 172.16.100.0/24 for live hosts...", output)

    def test_phase_started_without_activity_prints_only_phase_name(self):
        output = self._render(
            RuntimeEvent(
                phase=RuntimePhase.COMPLETION,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime.now(),
            )
        )

        self.assertIn("Completion", output)

    def test_phase_completed_with_bare_count_prints_count_and_label(self):
        output = self._render(
            RuntimeEvent(
                phase=RuntimePhase.HOST_DISCOVERY,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime.now(),
                progress=ProgressMeasurement(completed=89, unit_label="Hosts Found"),
            )
        )

        self.assertIn("89 Hosts Found", output)
        self.assertNotIn("/", output)

    def test_phase_completed_with_total_prints_fraction(self):
        output = self._render(
            RuntimeEvent(
                phase=RuntimePhase.SERVICE_ENRICHMENT,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime.now(),
                progress=ProgressMeasurement(
                    completed=89, total=89, unit_label="Hosts Completed"
                ),
            )
        )

        self.assertIn("89 / 89 Hosts Completed", output)

    def test_progress_events_are_not_rendered(self):
        output = self._render(
            RuntimeEvent(
                phase=RuntimePhase.SERVICE_ENRICHMENT,
                kind=RuntimeEventKind.PROGRESS,
                timestamp=datetime.now(),
                progress=ProgressMeasurement(
                    completed=37, total=89, unit_label="Hosts Completed"
                ),
            )
        )

        self.assertEqual(output, "")

    def test_never_renders_a_percentage_or_eta(self):
        """OBS-002 explicitly forbids estimated percentages/ETAs — verify
        the renderer's own output never manufactures one."""
        output = self._render(
            RuntimeEvent(
                phase=RuntimePhase.SERVICE_ENRICHMENT,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime.now(),
                progress=ProgressMeasurement(
                    completed=37, total=89, unit_label="Hosts Completed"
                ),
            )
        )

        self.assertNotIn("%", output)
        self.assertNotIn("ETA", output)
        self.assertNotIn("remaining", output.lower())


class RenderRuntimeSummaryTest(unittest.TestCase):
    def test_no_phases_recorded_renders_placeholder(self):
        summary = render_runtime_summary(RuntimeTelemetryRecorder())

        self.assertIn("No phases recorded.", summary)

    def test_summary_lists_each_phase_duration_and_total_runtime(self):
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
                timestamp=datetime(2026, 8, 11, 9, 0, 4),
            )
        )
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.CLASSIFICATION,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime(2026, 8, 11, 9, 0, 4),
            )
        )
        recorder.handle_event(
            RuntimeEvent(
                phase=RuntimePhase.CLASSIFICATION,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime(2026, 8, 11, 9, 0, 5),
            )
        )

        summary = render_runtime_summary(recorder)

        self.assertIn("Runtime Summary", summary)
        self.assertIn("Host Discovery", summary)
        self.assertIn("4.00s", summary)
        self.assertIn("Classification", summary)
        self.assertIn("1.00s", summary)
        self.assertIn("Total Runtime: 5.00s", summary)

    def test_summary_never_renders_a_percentage_or_eta(self):
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
                timestamp=datetime(2026, 8, 11, 9, 0, 4),
            )
        )

        summary = render_runtime_summary(recorder)

        self.assertNotIn("%", summary)
        self.assertNotIn("ETA", summary)


if __name__ == "__main__":
    unittest.main()
