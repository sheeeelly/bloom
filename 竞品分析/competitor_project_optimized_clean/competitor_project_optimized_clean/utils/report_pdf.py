from __future__ import annotations

import html
import re
from pathlib import Path


def _fallback_markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    html_lines: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            close_list()
            html_lines.append("")
            continue
        if stripped.startswith("![") and "](" in stripped and stripped.endswith(")"):
            close_list()
            alt = stripped[2:].split("]", 1)[0]
            src = stripped.split("](", 1)[1][:-1]
            html_lines.append(f'<img src="{html.escape(src)}" alt="{html.escape(alt)}" />')
            continue
        if stripped.startswith("#"):
            close_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            text = stripped[level:].strip()
            html_lines.append(f"<h{level}>{html.escape(text)}</h{level}>")
            continue
        if stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{html.escape(stripped[2:].strip())}</li>")
            continue
        close_list()
        text = html.escape(stripped)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        html_lines.append(f"<p>{text}</p>")

    close_list()
    return "\n".join(html_lines)


def _markdown_to_html(markdown_text: str) -> str:
    try:
        import markdown  # type: ignore

        return markdown.markdown(
            markdown_text,
            extensions=["extra", "tables", "fenced_code", "sane_lists"],
            output_format="html5",
        )
    except Exception:
        return _fallback_markdown_to_html(markdown_text)


def build_report_html(markdown_text: str) -> str:
    body = _markdown_to_html(markdown_text)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    @page {{ size: A4; margin: 18mm 16mm; }}
    body {{
      font-family: "Microsoft YaHei", "SimSun", Arial, sans-serif;
      color: #1f2937;
      font-size: 12px;
      line-height: 1.65;
    }}
    h1 {{ font-size: 24px; border-bottom: 1px solid #d1d5db; padding-bottom: 8px; }}
    h2 {{ font-size: 18px; margin-top: 24px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }}
    h3 {{ font-size: 15px; margin-top: 18px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 11px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 6px 8px; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
    img {{ max-width: 100%; max-height: 220px; display: block; margin: 10px 0; }}
    code, pre {{ font-family: Consolas, "Courier New", monospace; background: #f9fafb; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def markdown_to_pdf(markdown_path: Path, pdf_path: Path, html_path: Path | None = None) -> Path:
    markdown_text = markdown_path.read_text(encoding="utf-8")
    html_text = build_report_html(markdown_text)
    html_path = html_path or pdf_path.with_suffix(".html")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html_text, encoding="utf-8")

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        raise RuntimeError("缺少 playwright，无法生成 PDF。请安装 playwright 并执行 playwright install chromium。") from exc

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "18mm", "right": "16mm", "bottom": "18mm", "left": "16mm"},
        )
        browser.close()

    return pdf_path
