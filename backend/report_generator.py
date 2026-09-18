"""Report generation, disk persistence in reports/, and sanitized retrieval."""
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.config import settings
from backend.schemas import OptimizationReport


def sanitize_report_id(report_id: str) -> str:
    """Ensure report_id is alphanumeric with hyphens/underscores to prevent path traversal."""
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "", report_id)
    if not cleaned:
        raise ValueError(f"Invalid report ID format: '{report_id}'")
    return cleaned


def save_report(report: OptimizationReport) -> Path:
    """Save OptimizationReport as formatted UTF-8 JSON file with 2-space indentation."""
    reports_dir = settings.reports_path
    safe_id = sanitize_report_id(report.report_id)
    filename = f"cloud_optimization_report_{safe_id}.json"
    file_path = reports_dir / filename

    # Assign download URL relative path
    report.download_url = f"/api/reports/{safe_id}/download"

    report_data = report.model_dump(mode="json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    return file_path


def get_report_file_path(report_id: str) -> Optional[Path]:
    """Find path to report file by ID with path traversal protection."""
    try:
        safe_id = sanitize_report_id(report_id)
    except ValueError:
        return None

    reports_dir = settings.reports_path
    file_path = reports_dir / f"cloud_optimization_report_{safe_id}.json"
    if file_path.exists() and file_path.is_file():
        return file_path
    return None


def load_report(report_id: str) -> Optional[Dict[str, Any]]:
    """Read and parse report JSON from disk."""
    file_path = get_report_file_path(report_id)
    if not file_path:
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_saved_reports() -> List[str]:
    """List all saved report IDs."""
    reports_dir = settings.reports_path
    if not reports_dir.exists():
        return []
    ids = []
    for p in reports_dir.glob("cloud_optimization_report_*.json"):
        match = re.match(r"cloud_optimization_report_(.+)\.json", p.name)
        if match:
            ids.append(match.group(1))
    return sorted(ids, reverse=True)
