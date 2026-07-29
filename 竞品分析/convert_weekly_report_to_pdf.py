from __future__ import annotations

import html
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT_MD = ROOT / "weekly_report_2026-W23.md"
OUTPUT_PDF = ROOT / "weekly_report_2026-W23.pdf"
TEMP_HTML = ROOT / "weekly_report_2026-W23.__pdf.html"


def render_markdown(markdown_text: str) -> str:
    try:
        import markdown  # type: ignore

        return markdown.markdown(
            markdown_text,
            extensions=[
                "extra",
                "tables",
                "fenced_code",
                "sane_lists",
                "nl2br",
            ],
            output_format="html5",
        )
    except Exception:
        # Fallback: preserve the original text exactly if markdown is unavailable.
        return f"<pre>{html.escape(markdown_text)}</pre>"


def build_html(body_html: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>weekly_report_2026-W23</title>
  <style>
    @page {{
      size: A4;
      margin: 18mm 16mm;
    }}
    body {{
      font-family: "Microsoft YaHei", "SimSun", Arial, sans-serif;
      color: #1f2937;
      font-size: 12px;
      line-height: 1.68;
    }}
    h1 {{
      font-size: 24px;
      margin: 0 0 18px;
      padding-bottom: 8px;
      border-bottom: 1px solid #d1d5db;
    }}
    h2 {{
      font-size: 18px;
      margin: 24px 0 10px;
      padding-bottom: 4px;
      border-bottom: 1px solid #e5e7eb;
    }}
    h3 {{
      font-size: 15px;
      margin: 18px 0 8px;
    }}
    p {{
      margin: 6px 0;
    }}
    ul, ol {{
      margin: 6px 0 10px 22px;
      padding: 0;
    }}
    li {{
      margin: 3px 0;
    }}
    strong {{
      font-weight: 700;
    }}
    hr {{
      border: 0;
      border-top: 1px solid #e5e7eb;
      margin: 20px 0;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 12px 0;
      font-size: 11px;
    }}
    th, td {{
      border: 1px solid #d1d5db;
      padding: 6px 8px;
      vertical-align: top;
    }}
    th {{
      background: #f3f4f6;
      font-weight: 700;
    }}
    code, pre {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 11px;
      background: #f9fafb;
    }}
    pre {{
      padding: 10px;
      border: 1px solid #e5e7eb;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    a {{
      color: #2563eb;
      text-decoration: none;
    }}
  </style>
</head>
<body>
{body_html}
</body>
</html>
"""


def main() -> None:
    if not INPUT_MD.exists():
        raise FileNotFoundError(f"Markdown file not found: {INPUT_MD}")

    markdown_text = INPUT_MD.read_text(encoding="utf-8")
    html_text = build_html(render_markdown(markdown_text))
    TEMP_HTML.write_text(html_text, encoding="utf-8")

    from playwright.sync_api import sync_playwright  # type: ignore

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(TEMP_HTML.as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(OUTPUT_PDF),
            format="A4",
            print_background=True,
            margin={
                "top": "18mm",
                "right": "16mm",
                "bottom": "18mm",
                "left": "16mm",
            },
        )
        browser.close()

    try:
        os.remove(TEMP_HTML)
    except OSError:
        pass

    print(f"PDF generated: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
