"""Selection router — factor metadata, async job submission, SSE progress."""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from quant_backtest.api.deps import CacheDep
from quant_backtest.api.jobs import JobRegistry, JobState
from quant_backtest.selection import FactorSelectorConfig
from quant_backtest.selection.factors import FACTOR_COLUMNS
from quant_backtest.services import selection_service

router = APIRouter()


_FACTOR_DESCRIPTIONS = {
    "ma_breakout": "均线突破：收盘价站上长期均线",
    "kdj_golden_cross": "KDJ 金叉",
    "macd_golden_cross": "MACD 金叉",
    "rsi_momentum": "RSI 动量：高于阈值",
    "volume_breakout": "成交量放量",
    "boll_breakout": "布林带突破上轨",
}


class SelectionRequest(BaseModel):
    as_of_date: str | None = None
    config: dict = Field(default_factory=dict)
    symbol_universe: list[str] | None = None


def get_registry(request: Request) -> JobRegistry:
    return request.app.state.job_registry


RegistryDep = Annotated[JobRegistry, Depends(get_registry)]


@router.get("/factors")
def list_factors() -> dict:
    payload = [
        {
            "key": key,
            "name_cn": _FACTOR_DESCRIPTIONS.get(key, key),
            "description": _FACTOR_DESCRIPTIONS.get(key, ""),
        }
        for key in FACTOR_COLUMNS
    ]
    return {"data": payload, "meta": {"count": len(payload)}}


@router.get("/defaults")
def defaults() -> dict:
    cfg = FactorSelectorConfig()
    payload = asdict(cfg)
    payload["require_factors"] = list(cfg.require_factors)
    payload["exclude_factors"] = list(cfg.exclude_factors)
    return {"data": payload, "meta": {}}


@router.post("/jobs")
def submit_job(req: SelectionRequest, cache: CacheDep, registry: RegistryDep) -> dict:
    config = _build_config(req.config)
    job_id = registry.create_job()

    def _run() -> None:
        def progress_cb(stage: str, value: float, message: str) -> None:
            registry.update(
                job_id,
                status="running",
                stage=stage,
                progress=value,
                message=message,
            )

        try:
            result = selection_service.run_selection(
                cache=cache,
                config=config,
                as_of_date=req.as_of_date,
                symbols=req.symbol_universe,
                on_progress=progress_cb,
            )
            registry.complete(
                job_id,
                result={
                    "as_of_date": result.as_of_date,
                    "config": result.config,
                    "candidates": result.candidates,
                    "summary": result.summary,
                },
            )
        except Exception as exc:  # noqa: BLE001
            registry.fail(job_id, error=f"{type(exc).__name__}: {exc}")

    threading.Thread(target=_run, daemon=True).start()
    return {"data": {"job_id": job_id}, "meta": {}}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, registry: RegistryDep) -> dict:
    try:
        state = registry.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")
    return {"data": _state_to_dict(state), "meta": {}}


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str, registry: RegistryDep):
    try:
        registry.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")

    async def event_generator():
        last_seen: tuple[str | None, float] = (None, -1.0)
        while True:
            try:
                state = registry.get(job_id)
            except KeyError:
                yield {"event": "error", "data": json.dumps({"message": "job purged"})}
                return
            current = (state.stage, state.progress)
            if current != last_seen:
                last_seen = current
                event_name = "progress"
                payload: dict = {
                    "stage": state.stage,
                    "progress": state.progress,
                    "message": state.message,
                }
                if state.status == "done":
                    event_name = "done"
                    payload["result"] = state.result
                if state.status == "failed":
                    event_name = "failed"
                    payload["error"] = state.error
                yield {"event": event_name, "data": json.dumps(payload, default=str, ensure_ascii=False)}
                if state.status in {"done", "failed"}:
                    return
            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())


def _build_config(payload: dict) -> FactorSelectorConfig:
    default = FactorSelectorConfig()
    fields = asdict(default)
    fields["require_factors"] = list(default.require_factors)
    fields["exclude_factors"] = list(default.exclude_factors)
    for key, value in payload.items():
        if key not in fields:
            continue
        if key in {"require_factors", "exclude_factors"}:
            value = tuple(value or ())
        fields[key] = value
    fields["require_factors"] = tuple(fields["require_factors"])
    fields["exclude_factors"] = tuple(fields["exclude_factors"])
    return FactorSelectorConfig(**fields)


def _state_to_dict(state: JobState) -> dict:
    return {
        "job_id": state.job_id,
        "status": state.status,
        "stage": state.stage,
        "progress": state.progress,
        "message": state.message,
        "result": state.result,
        "error": state.error,
    }
