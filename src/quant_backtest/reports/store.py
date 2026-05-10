"""Read/write helpers for the on-disk backtest report layout."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date as _date
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from quant_backtest.reports.schema import (
    ArtifactRef,
    DateRange,
    ReportManifest,
    SweepManifest,
    ValidateManifest,
)

_KIND_TO_DIR = {"sweep": "sweeps", "validate": "validations"}


def write_report(
    *,
    kind: str,
    config: dict,
    manifest_extra: dict,
    artifacts: dict[str, pd.DataFrame],
    base_dir: Path | str = Path("reports"),
) -> str:
    if kind not in _KIND_TO_DIR:
        raise ValueError(f"unknown report kind: {kind}")

    base = Path(base_dir)
    extra = dict(manifest_extra)  # mutate-safe copy
    config_hash = _hash_config(config)
    timestamp = datetime.now(tz=timezone.utc)
    run_id = f"{kind}-{timestamp.strftime('%Y%m%d-%H%M%S')}-{config_hash}"
    run_dir = base / _KIND_TO_DIR[kind] / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    artifact_refs: list[ArtifactRef] = []
    for name, df in artifacts.items():
        path = f"{name}.parquet"
        df.to_parquet(run_dir / path, index=False)
        artifact_refs.append(ArtifactRef(name=name, path=path, rows=int(len(df))))

    (run_dir / "config.json").write_text(json.dumps(config, indent=2, default=str, ensure_ascii=False))

    git_commit, git_dirty = _git_state()
    common = dict(
        run_id=run_id,
        kind=kind,
        created_at=timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        elapsed_seconds=float(extra.pop("elapsed_seconds", 0.0)),
        git_commit=git_commit,
        git_dirty=git_dirty,
        data_range=DateRange(**extra.pop("data_range")),
        symbols=list(extra.pop("symbols", [])),
        config_hash=config_hash,
        config_path="config.json",
        artifacts=artifact_refs,
    )

    if kind == "sweep":
        manifest: ReportManifest = SweepManifest(**common, **extra)
    else:
        manifest = ValidateManifest(**common, **extra)

    (run_dir / "manifest.json").write_text(
        json.dumps(manifest.to_dict(), indent=2, default=str, ensure_ascii=False)
    )
    return run_id


def list_reports(
    base_dir: Path | str,
    *,
    kind: str | None = None,
    since: _date | None = None,
    limit: int | None = None,
) -> list[ReportManifest]:
    base = Path(base_dir)
    kinds = [kind] if kind else list(_KIND_TO_DIR.keys())
    manifests: list[ReportManifest] = []
    for k in kinds:
        if k not in _KIND_TO_DIR:
            continue
        sub = base / _KIND_TO_DIR[k]
        if not sub.exists():
            continue
        for run_dir in sub.iterdir():
            manifest_path = run_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            manifests.append(_load_manifest_from_dict(json.loads(manifest_path.read_text())))
    manifests.sort(key=lambda m: m.created_at, reverse=True)
    if since is not None:
        manifests = [m for m in manifests if m.created_at[:10] >= since.isoformat()]
    if limit is not None:
        manifests = manifests[:limit]
    return manifests


def load_report(base_dir: Path | str, run_id: str) -> ReportManifest:
    base = Path(base_dir)
    kind = run_id.split("-", 1)[0]
    if kind not in _KIND_TO_DIR:
        raise FileNotFoundError(run_id)
    manifest_path = base / _KIND_TO_DIR[kind] / run_id / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(run_id)
    return _load_manifest_from_dict(json.loads(manifest_path.read_text()))


def load_artifact(base_dir: Path | str, run_id: str, name: str) -> pd.DataFrame:
    base = Path(base_dir)
    kind = run_id.split("-", 1)[0]
    if kind not in _KIND_TO_DIR:
        raise FileNotFoundError(f"{run_id}/{name}")
    path = base / _KIND_TO_DIR[kind] / run_id / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{run_id}/{name}")
    return pd.read_parquet(path)


def _hash_config(config: dict) -> str:
    blob = json.dumps(config, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:6]


def _git_state() -> tuple[str | None, bool]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, False
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return commit, False
    return commit, bool(status.strip())


def _load_manifest_from_dict(payload: dict) -> ReportManifest:
    payload = dict(payload)
    payload["data_range"] = DateRange(**payload["data_range"])
    payload["artifacts"] = [ArtifactRef(**a) for a in payload.get("artifacts", [])]
    if payload["kind"] == "sweep":
        return SweepManifest(**payload)
    if payload["kind"] == "validate":
        return ValidateManifest(**payload)
    return ReportManifest(**payload)
