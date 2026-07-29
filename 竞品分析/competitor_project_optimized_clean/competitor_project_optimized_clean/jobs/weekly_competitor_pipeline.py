from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from ai_assistant.weekly_report_generator import generate_weekly_report
from utils.email_sender import send_report_email
from utils.google_drive_sync import GoogleDrivePublisher
from utils.report_pdf import markdown_to_pdf


ROOT = Path(__file__).resolve().parents[1]


def _current_week_for_previous_week(today: date | None = None) -> str:
    current = today or date.today()
    previous_week_day = current - timedelta(days=7)
    iso = previous_week_day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _run_subprocess(command: list[str], cwd: Path) -> dict[str, Any]:
    started_at = _now_text()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
        )
        return {
            "command": command,
            "started_at": started_at,
            "finished_at": _now_text(),
            "returncode": completed.returncode,
            "stdout": completed.stdout[-5000:],
            "stderr": completed.stderr[-5000:],
            "ok": completed.returncode == 0,
        }
    except Exception as exc:
        return {
            "command": command,
            "started_at": started_at,
            "finished_at": _now_text(),
            "returncode": None,
            "stdout": "",
            "stderr": traceback.format_exc(),
            "ok": False,
            "error": str(exc),
        }


def _copy_latest_excels(output_dir: Path, target_dir: Path) -> list[str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in sorted(output_dir.glob("*.xlsx")):
        if path.name.startswith("~$"):
            continue
        dest = target_dir / path.name
        shutil.copy2(path, dest)
        copied.append(str(dest))
    return copied


def _publish_google_outputs(
    *,
    week: str,
    report_dir: Path,
    markdown_path: Path,
    pdf_path: Path,
    excel_paths: list[str],
    manifest: dict[str, Any],
) -> None:
    credentials = os.getenv("GOOGLE_CREDENTIALS_JSON") or os.getenv("GSHEET_CREDENTIALS_JSON", "credentials.json")
    parent_folder_id = os.getenv("GOOGLE_DRIVE_REPORT_FOLDER_ID", "").strip()
    if not parent_folder_id:
        manifest["google"] = {"skipped": True, "reason": "GOOGLE_DRIVE_REPORT_FOLDER_ID not configured"}
        return

    publisher = GoogleDrivePublisher(credentials, parent_folder_id)
    folder = publisher.ensure_folder(week)
    folder_id = folder["id"]

    uploaded_excels = [
        publisher.upload_file(Path(path), folder_id)
        for path in excel_paths
        if Path(path).exists()
    ]
    uploaded_pdf = publisher.upload_file(pdf_path, folder_id, mime_type="application/pdf") if pdf_path.exists() else {}
    google_doc = publisher.create_doc_from_markdown(
        title=f"BD_Competitor_Report_{week}",
        markdown_path=markdown_path,
        folder_id=folder_id,
    )

    manifest["google"] = {
        "skipped": False,
        "folder": folder,
        "excel_files": uploaded_excels,
        "pdf": uploaded_pdf,
        "doc": google_doc,
    }


def _send_email_if_configured(week: str, pdf_path: Path, manifest: dict[str, Any]) -> None:
    recipients = os.getenv("REPORT_EMAIL_TO", "").strip()
    if not recipients:
        manifest["email"] = {"skipped": True, "reason": "REPORT_EMAIL_TO not configured"}
        return

    google = manifest.get("google", {})
    doc_url = ((google.get("doc") or {}).get("url") if isinstance(google, dict) else "") or ""
    folder_url = ((google.get("folder") or {}).get("url") if isinstance(google, dict) else "") or ""
    body = "\n".join(
        [
            f"{week} BD 竞品分析周报已生成。",
            "",
            f"Google Doc: {doc_url or '未生成'}",
            f"Google Drive: {folder_url or '未生成'}",
            "",
            "本邮件由竞品分析自动任务发送。",
        ]
    )
    send_report_email(
        subject=f"{week} BD 竞品分析周报",
        body=body,
        attachments=[pdf_path] if pdf_path.exists() else [],
    )
    manifest["email"] = {"skipped": False, "to": recipients, "sent_at": _now_text()}


def run_weekly_pipeline(
    *,
    week: str,
    skip_crawl: bool = False,
    sites: str = "all",
) -> dict[str, Any]:
    load_dotenv(dotenv_path=str(ROOT / ".env"), override=True)

    report_root = Path(os.getenv("REPORT_OUTPUT_DIR", "data/report_runs"))
    output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    report_dir = ROOT / report_root / week if not report_root.is_absolute() else report_root / week
    excel_dir = report_dir / "excel"
    assets_dir = report_dir / "assets"
    markdown_path = report_dir / f"BD_Competitor_Report_{week}.md"
    comparison_path = report_dir / f"BD_Competitor_Comparison_{week}.json"
    pdf_path = report_dir / f"BD_Competitor_Report_{week}.pdf"
    html_path = report_dir / f"BD_Competitor_Report_{week}.html"
    manifest_path = report_dir / "manifest.json"

    report_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "week": week,
        "started_at": _now_text(),
        "root": str(ROOT),
        "steps": {},
        "outputs": {},
    }

    if skip_crawl:
        manifest["steps"]["crawl"] = {"skipped": True}
    else:
        site_args = ["--site", sites]
        manifest["steps"]["crawl"] = _run_subprocess([sys.executable, "run.py", *site_args], ROOT)

    excel_paths = _copy_latest_excels(output_dir, excel_dir)
    manifest["outputs"]["excel_files"] = excel_paths

    try:
        generate_weekly_report(
            week=week,
            input_path=excel_dir,
            output_path=markdown_path,
            write_pinecone=os.getenv("REPORT_WRITE_PINECONE", "false").strip().lower() in {"1", "true", "yes", "y"},
            comparison_path=comparison_path,
            color_assets_root=assets_dir,
        )
        manifest["steps"]["weekly_report"] = {"ok": True}
    except Exception as exc:
        manifest["steps"]["weekly_report"] = {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}

    try:
        if markdown_path.exists():
            markdown_to_pdf(markdown_path, pdf_path, html_path)
            manifest["steps"]["pdf"] = {"ok": True}
        else:
            manifest["steps"]["pdf"] = {"ok": False, "error": "Markdown report not found"}
    except Exception as exc:
        manifest["steps"]["pdf"] = {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}

    try:
        if markdown_path.exists():
            _publish_google_outputs(
                week=week,
                report_dir=report_dir,
                markdown_path=markdown_path,
                pdf_path=pdf_path,
                excel_paths=excel_paths,
                manifest=manifest,
            )
    except Exception as exc:
        manifest["google"] = {"skipped": False, "ok": False, "error": str(exc), "traceback": traceback.format_exc()}

    try:
        _send_email_if_configured(week, pdf_path, manifest)
    except Exception as exc:
        manifest["email"] = {"skipped": False, "ok": False, "error": str(exc), "traceback": traceback.format_exc()}

    manifest["outputs"].update(
        {
            "report_dir": str(report_dir),
            "markdown": str(markdown_path),
            "comparison_json": str(comparison_path),
            "pdf": str(pdf_path),
            "html": str(html_path),
            "manifest": str(manifest_path),
        }
    )
    manifest["finished_at"] = _now_text()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run weekly competitor analysis delivery pipeline.")
    parser.add_argument("--week", default=None, help="周次，例如 2026-W23；默认取上周")
    parser.add_argument("--skip-crawl", action="store_true", help="跳过爬虫，直接使用 output 里的 Excel")
    parser.add_argument("--site", default=os.getenv("REPORT_SITES", "all"), help="传给 run.py 的 --site 参数")
    args = parser.parse_args()

    week = args.week or _current_week_for_previous_week()
    manifest = run_weekly_pipeline(week=week, skip_crawl=args.skip_crawl, sites=args.site)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
