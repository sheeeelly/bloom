from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


DEFAULT_COLOR_HEX = {
    "black": "#111111",
    "white": "#F8F8F8",
    "ivory": "#F6F0E6",
    "champagne": "#E8D7B9",
    "blush": "#EFC7C7",
    "blush pink": "#EFC7C7",
    "pink": "#E8A8B8",
    "powder blue": "#B8D8F0",
    "light blue": "#B7D7F2",
    "sky blue": "#9DC8EC",
    "navy": "#0B1F3A",
    "emerald": "#0F4F3A",
    "sage": "#A7B59A",
    "olive": "#6B6F3E",
    "burgundy": "#6E1025",
    "red": "#B00020",
    "lemon": "#F6E27A",
    "yellow": "#F4D35E",
    "butter": "#F5E7A1",
    "brown": "#6F4E37",
    "espresso": "#4A2C2A",
    "mulberry": "#70193D",
    "plum": "#5B2C4D",
}


def _safe_name(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return text or "color"


def _load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_hex(color_name: str, config_entry: dict[str, Any] | None = None) -> str:
    if config_entry:
        raw = str(config_entry.get("hex") or "").strip()
        if re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
            return raw
    return DEFAULT_COLOR_HEX.get(color_name.strip().lower(), "#D9D9D9")


def _write_svg(color_name: str, hex_value: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_safe_name(color_name)}.svg"
    escaped_name = (
        color_name.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    text_color = "#FFFFFF" if hex_value.lower() not in {"#f8f8f8", "#ffffff", "#f6f0e6", "#f5e7a1", "#f6e27a"} else "#111111"
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="220" viewBox="0 0 640 220">
  <rect width="640" height="220" rx="24" fill="{hex_value}"/>
  <text x="320" y="118" text-anchor="middle" font-size="34" font-family="Arial, sans-serif" fill="{text_color}">{escaped_name}</text>
</svg>
""",
        encoding="utf-8",
    )
    return path


def resolve_color_swatch_assets(
    colors: list[str],
    *,
    week: str,
    output_root: Path | None = None,
    config_path: Path | None = None,
) -> list[dict[str, str]]:
    """Resolve color swatch images for weekly report markdown/PDF.

    If config contains image_url for a color, that URL is used directly. Otherwise
    a local SVG swatch is generated so the report always has a visual asset.
    """
    output_root = output_root or Path("data/report_assets")
    config_path = config_path or Path(os.getenv("COLOR_SWATCH_CONFIG", "config/color_swatches.json"))
    config = _load_config(config_path)
    assets: list[dict[str, str]] = []

    for color in colors:
        color_name = str(color or "").strip()
        if not color_name:
            continue
        entry = config.get(color_name) or config.get(color_name.lower()) or {}
        entry = entry if isinstance(entry, dict) else {}
        image_url = str(entry.get("image_url") or entry.get("image") or "").strip()
        hex_value = _resolve_hex(color_name, entry)

        if image_url:
            asset_path = image_url
        else:
            asset_path = str(_write_svg(color_name, hex_value, output_root / week))

        assets.append(
            {
                "color": color_name,
                "hex": hex_value,
                "image": asset_path,
            }
        )

    return assets


def build_color_markdown(assets: list[dict[str, str]], max_items: int = 5) -> str:
    if not assets:
        return ""
    lines = ["## 颜色图总结", ""]
    for asset in assets[:max_items]:
        color = asset["color"]
        image = asset["image"]
        lines.append(f"![{color}]({image})")
        lines.append("")
        lines.append(f"- {color}")
        lines.append("")
    return "\n".join(lines).strip()
