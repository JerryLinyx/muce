"""Dataclass schema for backtest report manifests."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


@dataclass(frozen=True)
class DateRange:
    start: str
    end: str


@dataclass(frozen=True)
class ArtifactRef:
    name: str
    path: str
    rows: int


@dataclass(frozen=True)
class ReportManifest:
    run_id: str
    kind: Literal["sweep", "validate"]
    created_at: str
    elapsed_seconds: float
    git_commit: str | None
    git_dirty: bool
    data_range: DateRange
    symbols: list[str]
    config_hash: str
    config_path: str
    artifacts: list[ArtifactRef]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SweepManifest(ReportManifest):
    strategy: str = ""
    grid_size: int = 0
    rank_by: str = ""
    top_combos: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class ValidateManifest(ReportManifest):
    strategy: str = ""
    signal_adjust: str = "qfq"
    execution_adjust: str = "raw"
    summary_metrics: dict = field(default_factory=dict)
