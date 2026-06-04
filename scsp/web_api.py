from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import run_simulation, run_sweep
from .experiment import JsonlExperimentStore, reproduce_experiment, run_experiment

DEFAULT_OUTPUT_ROOT = Path("experiments/runs")
DEFAULT_STORE_PATH = Path("experiments/records.jsonl")


class SingleSimulationRequest(BaseModel):
    config: Dict[str, Any]
    bandwidth_gbps: Optional[int] = None


class SweepSimulationRequest(BaseModel):
    config: Dict[str, Any]
    bandwidths_gbps: Optional[List[int]] = None


class RunExperimentRequest(BaseModel):
    config: Dict[str, Any]
    experiment_name: Optional[str] = None
    template_name: Optional[Literal["single_point", "bandwidth_sensitivity"]] = None
    output_root: Optional[str] = None
    store_path: Optional[str] = None


def create_app() -> FastAPI:
    app = FastAPI(title="SCSP API", version="v1")
    web_root = Path(__file__).resolve().parents[1] / "web"
    assets_root = Path(__file__).resolve().parents[1] / "assets"
    configs_root = Path(__file__).resolve().parents[1] / "configs"
    if web_root.exists():
        app.mount("/web", StaticFiles(directory=str(web_root)), name="web")
    if assets_root.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_root)), name="assets")
    if configs_root.exists():
        app.mount("/configs", StaticFiles(directory=str(configs_root)), name="configs")

    @app.get("/api/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/simulations/single")
    def api_run_single(req: SingleSimulationRequest) -> Dict[str, Any]:
        try:
            return run_simulation(req.config, bandwidth_gbps=req.bandwidth_gbps)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/simulations/sweep")
    def api_run_sweep(req: SweepSimulationRequest) -> Dict[str, Any]:
        try:
            return run_sweep(req.config, bandwidths_gbps=req.bandwidths_gbps)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/experiments/run")
    def api_run_experiment(req: RunExperimentRequest) -> Dict[str, Any]:
        output_root = req.output_root or str(DEFAULT_OUTPUT_ROOT)
        store_path = req.store_path or str(DEFAULT_STORE_PATH)
        try:
            return run_experiment(
                raw_config=req.config,
                output_root=output_root,
                store_path=store_path,
                experiment_name=req.experiment_name,
                template_name=req.template_name,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/experiments")
    def api_list_experiments(store_path: Optional[str] = None) -> Dict[str, Any]:
        path = store_path or str(DEFAULT_STORE_PATH)
        store = JsonlExperimentStore(path)
        records = store.list_records()
        return {"count": len(records), "records": records}

    @app.get("/api/experiments/{experiment_id}")
    def api_get_experiment(experiment_id: str, store_path: Optional[str] = None) -> Dict[str, Any]:
        path = store_path or str(DEFAULT_STORE_PATH)
        store = JsonlExperimentStore(path)
        try:
            return store.get(experiment_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/experiments/reproduce/{experiment_id}")
    def api_reproduce_experiment(
        experiment_id: str,
        output_root: Optional[str] = None,
        store_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            return reproduce_experiment(
                experiment_id=experiment_id,
                output_root=output_root or str(DEFAULT_OUTPUT_ROOT),
                store_path=store_path or str(DEFAULT_STORE_PATH),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/experiments/{experiment_id}/export")
    def api_export_experiment(experiment_id: str, store_path: Optional[str] = None) -> Dict[str, Any]:
        path = store_path or str(DEFAULT_STORE_PATH)
        store = JsonlExperimentStore(path)
        try:
            record = store.get(experiment_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return {"experiment": record, "export_format": "json"}

    @app.get("/")
    def index() -> FileResponse:
        index_path = web_root / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="Frontend page not found")
        return FileResponse(index_path)

    return app


app = create_app()
