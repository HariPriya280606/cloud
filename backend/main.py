"""FastAPI Application for Autonomous Cloud Cost-Optimization Agent."""
import logging
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError

from backend.config import settings
from backend.schemas import (
    OptimizationRequest,
    OptimizationReport,
)
from backend.agent import agent
from backend.report_generator import (
    save_report,
    load_report,
    get_report_file_path,
    list_saved_reports,
)
from backend.simulator import simulator
from backend.sample_data import SCENARIOS, get_scenario_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cloud_agent.api")

app = FastAPI(
    title="Cloud Bill That Wouldn't Stop Growing",
    description="Autonomous Cloud Cost-Optimization Agent with Deterministic Safety Verification",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom readable validation error handler."""
    errors = []
    raw_errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        errors.append(f"{loc}: {msg}")
        raw_errors.append({
            "loc": [str(l) for l in err.get("loc", [])],
            "msg": str(err.get("msg")),
            "type": str(err.get("type")),
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": errors,
            "raw": raw_errors,
        },
    )


@app.get("/", summary="Root status")
async def root() -> Dict[str, Any]:
    """Root endpoint returning health and project name."""
    return {
        "project": "Cloud Bill That Wouldn't Stop Growing",
        "description": "Autonomous cloud cost-optimization agent with safety verification",
        "status": "healthy",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", summary="Health check")
async def health_check() -> Dict[str, Any]:
    """Return backend health status."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "llm_configured": bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip()),
        "reports_dir": str(settings.reports_path),
    }


@app.post("/api/optimize", response_model=OptimizationReport, summary="Run Optimization Agent")
async def optimize_services(request: OptimizationRequest) -> OptimizationReport:
    """Run full autonomous optimization workflow and return persisted report."""
    try:
        report = await agent.run(request)
        save_report(report)
        return report
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Optimization run failed: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal agent error: {str(exc)}")


@app.post("/api/optimize/download", summary="Run Optimization and Download JSON Report")
async def optimize_and_download(request: OptimizationRequest):
    """Run optimization workflow, persist report, and stream downloadable JSON file."""
    try:
        report = await agent.run(request)
        file_path = save_report(report)
        filename = f"cloud_optimization_report_{report.report_id}.json"
        return FileResponse(
            path=file_path,
            media_type="application/json",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Optimization download failed: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.get("/api/reports", summary="List All Generated Reports")
async def list_reports() -> Dict[str, Any]:
    """Return list of all stored report IDs."""
    ids = list_saved_reports()
    return {"count": len(ids), "reports": ids}


@app.get("/api/reports/{report_id}", summary="Get Stored Report JSON")
async def get_report(report_id: str) -> Dict[str, Any]:
    """Retrieve a previously generated optimization report by ID."""
    report_data = load_report(report_id)
    if not report_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' was not found.",
        )
    return report_data


@app.get("/api/reports/{report_id}/download", summary="Download Stored Report File")
async def download_report(report_id: str):
    """Download existing report JSON file with path traversal protection."""
    file_path = get_report_file_path(report_id)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report file for '{report_id}' was not found.",
        )
    filename = file_path.name
    return FileResponse(
        path=file_path,
        media_type="application/json",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/scenarios/{scenario_name}", response_model=OptimizationReport, summary="Execute Preset Test Scenario")
async def run_scenario(scenario_name: str) -> OptimizationReport:
    """Execute one of the predefined test scenarios (scenario_a, scenario_b, scenario_c, scenario_d)."""
    try:
        req = get_scenario_request(scenario_name)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_name}' not found. Available: {list(SCENARIOS.keys())}",
        )
    report = await agent.run(req)
    save_report(report)
    return report


@app.get("/api/services", summary="Get Current Simulated Cloud Services")
async def get_simulated_services() -> Dict[str, Any]:
    """Return live services inside the cloud simulator."""
    services = simulator.list_services()
    return {"services": services, "count": len(services)}


@app.post("/api/reset", summary="Reset Simulator State")
async def reset_simulator() -> Dict[str, Any]:
    """Reset simulator state, action history, and failure flags."""
    simulator.reset()
    return {"status": "reset_successful", "message": "Simulator state cleared."}
