from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]


MODULES = [
    "main_az",
    "analysis.cross_site_comparison",
    "ai_assistant.color_swatch_resolver",
    "ai_assistant.weekly_report_generator",
    "utils.report_pdf",
    "utils.google_drive_sync",
    "utils.email_sender",
    "jobs.weekly_competitor_pipeline",
]


def _check_modules() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for module_name in MODULES:
        try:
            importlib.import_module(module_name)
            results.append({"module": module_name, "ok": True})
        except Exception as exc:
            results.append({"module": module_name, "ok": False, "error": str(exc)})
    return results


def _check_paths(week: str) -> dict[str, Any]:
    output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir

    report_root = Path(os.getenv("REPORT_OUTPUT_DIR", "data/report_runs"))
    report_dir = ROOT / report_root / week if not report_root.is_absolute() else report_root / week

    return {
        "output_dir": str(output_dir),
        "output_dir_exists": output_dir.exists(),
        "excel_count": len(list(output_dir.glob("*.xlsx"))) if output_dir.exists() else 0,
        "report_dir": str(report_dir),
        "report_dir_exists": report_dir.exists(),
        "manifest_exists": (report_dir / "manifest.json").exists(),
        "markdown_exists": any(report_dir.glob("*.md")) if report_dir.exists() else False,
        "pdf_exists": any(report_dir.glob("*.pdf")) if report_dir.exists() else False,
    }


def _check_config() -> dict[str, Any]:
    return {
        "az_data_source": os.getenv("AZ_DATA_SOURCE", "file"),
        "az_input_path_configured": bool(os.getenv("AZ_INPUT_PATH", "").strip()),
        "az_api_url_configured": bool(os.getenv("AZ_API_URL", "").strip()),
        "google_drive_folder_configured": bool(os.getenv("GOOGLE_DRIVE_REPORT_FOLDER_ID", "").strip()),
        "report_email_to_configured": bool(os.getenv("REPORT_EMAIL_TO", "").strip()),
        "smtp_configured": bool(os.getenv("SMTP_HOST", "").strip()),
        "color_swatch_config": os.getenv("COLOR_SWATCH_CONFIG", "config/color_swatches.json"),
    }


def validate(week: str) -> dict[str, Any]:
    load_dotenv(dotenv_path=str(ROOT / ".env"), override=True)
    module_results = _check_modules()
    return {
        "week": week,
        "ok": all(item.get("ok") for item in module_results),
        "modules": module_results,
        "paths": _check_paths(week),
        "config": _check_config(),
        "notes": [
            "This validation does not send email or call Google APIs.",
            "Run jobs/weekly_competitor_pipeline.py with --skip-crawl for a local end-to-end report using existing Excel files.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate weekly competitor pipeline setup.")
    parser.add_argument("--week", required=True, help="周次，例如 2026-W23")
    parser.add_argument("--output", default="", help="可选 JSON 输出路径")
    args = parser.parse_args()

    result = validate(args.week)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
