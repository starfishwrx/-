from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict

from PIL import Image, ImageDraw, ImageFont


COLOR_BORDER = (0, 0, 0)
COLOR_TITLE_BG = (151, 203, 108)
COLOR_HEADER_BG = (230, 230, 230)
COLOR_BODY_BG = (242, 242, 242)
COLOR_POS_BG = (247, 225, 225)
COLOR_NEG_BG = (223, 236, 210)
COLOR_TOTAL_BG = (245, 182, 79)
COLOR_COMPARE_LABEL_BG = (153, 217, 234)
COLOR_TEXT = (20, 20, 20)
COLOR_RED = (220, 40, 40)
COLOR_GREEN = (0, 146, 76)


def render_payment_table_images(payment_tables: Dict[str, Any], charts_dir: Path) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    charts_dir.mkdir(parents=True, exist_ok=True)

    page_data = payment_tables.get("page")
    if isinstance(page_data, dict):
        page_path = charts_dir / _build_page_filename(page_data)
        _render_page_table(page_data, page_path)
        out["page"] = page_path

    mobile_data = payment_tables.get("mobile")
    if isinstance(mobile_data, dict):
        mobile_path = charts_dir / _build_mobile_filename(mobile_data)
        _render_mobile_table(mobile_data, mobile_path)
        out["mobile"] = mobile_path

    return out


def _build_page_filename(data: Dict[str, Any]) -> str:
    day = str(data.get("today_date") or "").replace("-", "")
    suffix = day if day else "unknown"
    return f"505_page_payment_table_{suffix}.png"


def _build_mobile_filename(data: Dict[str, Any]) -> str:
    day = str(data.get("today_date") or "").replace("-", "")
    suffix = day if day else "unknown"
    return f"505_mobile_payment_table_{suffix}.png"


def _render_page_table(data: Dict[str, Any], output_path: Path) -> None:
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    today_label = _to_date_label(str(data.get("today_date") or ""))
    week_label = _to_date_label(str(data.get("week_date") or ""))
    total_today = int(data.get("total_today") or 0)
    total_week = int(data.get("total_week") or 0)
    total_delta = int(data.get("total_delta") or 0)
    title = str(data.get("title") or "页游付费数据")

    col_widths = [380, 380, 380, 380]
    title_h = 42
    head_h = 34
    row_h = 30
    total_h = 34
    width = sum(col_widths) + 1
    height = title_h + head_h + len(rows) * row_h + total_h + 1

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = _load_font(24, bold=True)
    head_font = _load_font(22, bold=True)
    body_font = _load_font(20, bold=False)
    num_font = _load_font(20, bold=False)

    y = 0
    _draw_cell(draw, 0, y, width - 1, title_h, COLOR_TITLE_BG, title, title_font, COLOR_TEXT, align="center")
    y += title_h

    headers = ["游戏名称", today_label, week_label, "对比"]
    x = 0
    for idx, head in enumerate(headers):
        w = col_widths[idx]
        _draw_cell(draw, x, y, w, head_h, COLOR_HEADER_BG, head, head_font, COLOR_TEXT, align="center")
        x += w
    y += head_h

    for row in rows:
        game = str(row.get("game") or "")
        today_val = int(row.get("today") or 0)
        week_val = int(row.get("week") or 0)
        delta = int(row.get("delta") or 0)

        x = 0
        _draw_cell(draw, x, y, col_widths[0], row_h, COLOR_BODY_BG, game, body_font, COLOR_TEXT, align="center")
        x += col_widths[0]
        _draw_cell(draw, x, y, col_widths[1], row_h, COLOR_BODY_BG, _fmt_int(today_val), num_font, COLOR_TEXT, align="center")
        x += col_widths[1]
        _draw_cell(draw, x, y, col_widths[2], row_h, COLOR_BODY_BG, _fmt_int(week_val), num_font, COLOR_TEXT, align="center")
        x += col_widths[2]

        compare_bg = COLOR_BODY_BG
        compare_color = COLOR_RED
        if delta > 0:
            compare_bg = COLOR_POS_BG
            compare_color = COLOR_RED
        elif delta < 0:
            compare_bg = COLOR_NEG_BG
            compare_color = COLOR_GREEN
        _draw_cell(draw, x, y, col_widths[3], row_h, compare_bg, _fmt_int(delta), num_font, compare_color, align="center")
        y += row_h

    x = 0
    _draw_cell(draw, x, y, col_widths[0], total_h, COLOR_TOTAL_BG, "总计", head_font, COLOR_TEXT, align="center")
    x += col_widths[0]
    _draw_cell(draw, x, y, col_widths[1], total_h, COLOR_TOTAL_BG, _fmt_int(total_today), head_font, COLOR_TEXT, align="center")
    x += col_widths[1]
    _draw_cell(draw, x, y, col_widths[2], total_h, COLOR_TOTAL_BG, _fmt_int(total_week), head_font, COLOR_TEXT, align="center")
    x += col_widths[2]
    _draw_cell(draw, x, y, col_widths[3], total_h, COLOR_TOTAL_BG, _fmt_int(total_delta), head_font, COLOR_TEXT, align="center")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def _render_mobile_table(data: Dict[str, Any], output_path: Path) -> None:
    today_rows = data.get("today_rows") if isinstance(data.get("today_rows"), list) else []
    week_rows = data.get("week_rows") if isinstance(data.get("week_rows"), list) else []
    today_label = _to_date_label(str(data.get("today_date") or ""))
    week_label = _to_date_label(str(data.get("week_date") or ""))
    total_today = int(data.get("total_today") or 0)
    total_week = int(data.get("total_week") or 0)
    total_delta = int(data.get("total_delta") or 0)
    title = str(data.get("title") or "手游付费数据")

    col_widths = [350, 350, 350, 350]
    title_h = 42
    head_h = 34
    row_h = 30
    total_h = 34
    compare_h = 32
    body_rows = max(len(today_rows), len(week_rows))
    width = sum(col_widths) + 1
    height = title_h + head_h + body_rows * row_h + total_h + compare_h + 1

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = _load_font(24, bold=True)
    head_font = _load_font(22, bold=True)
    body_font = _load_font(20, bold=False)
    num_font = _load_font(20, bold=False)

    y = 0
    _draw_cell(draw, 0, y, width - 1, title_h, COLOR_TITLE_BG, title, title_font, COLOR_TEXT, align="center")
    y += title_h

    headers = ["游戏名称", today_label, "游戏名称", week_label]
    x = 0
    for idx, head in enumerate(headers):
        w = col_widths[idx]
        _draw_cell(draw, x, y, w, head_h, COLOR_HEADER_BG, head, head_font, COLOR_TEXT, align="center")
        x += w
    y += head_h

    for idx in range(body_rows):
        left_game = ""
        left_amt = ""
        right_game = ""
        right_amt = ""
        if idx < len(today_rows):
            left_game = str(today_rows[idx].get("game") or "")
            left_amt = _fmt_int(int(today_rows[idx].get("amount") or 0))
        if idx < len(week_rows):
            right_game = str(week_rows[idx].get("game") or "")
            right_amt = _fmt_int(int(week_rows[idx].get("amount") or 0))

        x = 0
        _draw_cell(draw, x, y, col_widths[0], row_h, COLOR_BODY_BG, left_game, body_font, COLOR_TEXT, align="center")
        x += col_widths[0]
        _draw_cell(draw, x, y, col_widths[1], row_h, COLOR_BODY_BG, left_amt, num_font, COLOR_TEXT, align="center")
        x += col_widths[1]
        _draw_cell(draw, x, y, col_widths[2], row_h, COLOR_BODY_BG, right_game, body_font, COLOR_TEXT, align="center")
        x += col_widths[2]
        _draw_cell(draw, x, y, col_widths[3], row_h, COLOR_BODY_BG, right_amt, num_font, COLOR_TEXT, align="center")
        y += row_h

    x = 0
    _draw_cell(draw, x, y, col_widths[0], total_h, COLOR_TOTAL_BG, "合计（元）", head_font, COLOR_TEXT, align="center")
    x += col_widths[0]
    _draw_cell(draw, x, y, col_widths[1], total_h, COLOR_TOTAL_BG, _fmt_int(total_today), head_font, COLOR_TEXT, align="center")
    x += col_widths[1]
    _draw_cell(draw, x, y, col_widths[2], total_h, COLOR_TOTAL_BG, "合计（元）", head_font, COLOR_TEXT, align="center")
    x += col_widths[2]
    _draw_cell(draw, x, y, col_widths[3], total_h, COLOR_TOTAL_BG, _fmt_int(total_week), head_font, COLOR_TEXT, align="center")
    y += total_h

    compare_color = COLOR_RED if total_delta >= 0 else COLOR_GREEN
    x = 0
    _draw_cell(draw, x, y, col_widths[0], compare_h, COLOR_COMPARE_LABEL_BG, "对比", head_font, COLOR_TEXT, align="center")
    x += col_widths[0]
    _draw_cell(draw, x, y, col_widths[1], compare_h, (255, 255, 255), _fmt_int(total_delta), head_font, compare_color, align="center")
    x += col_widths[1]
    _draw_cell(draw, x, y, col_widths[2], compare_h, (255, 255, 255), "", head_font, COLOR_TEXT, align="center")
    x += col_widths[2]
    _draw_cell(draw, x, y, col_widths[3], compare_h, (255, 255, 255), "", head_font, COLOR_TEXT, align="center")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def _draw_cell(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    fill: tuple[int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    text_color: tuple[int, int, int],
    align: str = "center",
) -> None:
    draw.rectangle([x, y, x + w, y + h], fill=fill, outline=COLOR_BORDER, width=1)
    if not text:
        return
    text = str(text)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x + (w - tw) // 2
    if align == "left":
        tx = x + 8
    elif align == "right":
        tx = x + w - tw - 8
    ty = y + (h - th) // 2
    draw.text((tx, ty), text, font=font, fill=text_color)


def _fmt_int(value: int) -> str:
    return str(int(value))


def _to_date_label(value: str) -> str:
    try:
        d = date.fromisoformat(value)
        return f"{d.month}月{d.day}日"
    except ValueError:
        return value or "-"


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    if bold:
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()
