from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from networkmapper import __version__
from networkmapper.discovery.scan_profile import ScanProfile


@dataclass(frozen=True)
class RunMetadata:
    """Describes one report-generating run.

    REPORT-002: embedded into exported reports so a single Markdown file
    can stand alone (who/what/when it was generated from) without access
    to its source Project file.
    """

    generated_at: datetime
    scan_profile: ScanProfile
    customer_name: str
    device_count: int
    version: str | None = __version__


@dataclass(frozen=True)
class ReportRunPaths:
    """The unique output directory and artifact paths for one report run."""

    run_directory: Path
    markdown_path: Path
    csv_path: Path


def build_report_run_paths(
    output_root: Path | str,
    run_metadata: RunMetadata,
) -> ReportRunPaths:
    """Compute and create the unique per-run output directory and the
    Markdown/CSV artifact paths inside it.

    Keying the directory name on the run's generation timestamp and scan
    profile (`<YYYY-MM-DD_HHMMSS>_<profile>`) means consecutive runs never
    collide or overwrite a previous run's artifacts, and related artifacts
    from the same run (Markdown report, CSV export) stay together in one
    directory. Second-level precision is used rather than the
    minute-level precision shown in REPORT-002's own example structure,
    specifically so back-to-back runs (as happen in automated tests, or
    when a technician re-runs a scan moments later) still land in
    distinct directories.

    Args:
        output_root: The base output directory reports are written under.
        run_metadata: The metadata for the run being reported, used to
            derive the run directory name.

    Returns:
        The created run directory and the Markdown/CSV paths within it.
    """
    run_directory_name = (
        f"{run_metadata.generated_at:%Y-%m-%d_%H%M%S}_{run_metadata.scan_profile.value}"
    )
    run_directory = Path(output_root) / run_directory_name
    run_directory.mkdir(parents=True, exist_ok=True)

    return ReportRunPaths(
        run_directory=run_directory,
        markdown_path=run_directory / "report.md",
        csv_path=run_directory / "devices.csv",
    )
