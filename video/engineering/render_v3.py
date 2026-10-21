#!/usr/bin/env python3
"""Render the seven-scene v3 picture track without replacing the v2 film."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import render as r2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ENGINEERING = Path(__file__).resolve().parent
DATA_PATH = ENGINEERING / "timeline-v3.json"
FFMPEG = r2.FFMPEG
FPS = r2.FPS
W, H = r2.W, r2.H
PURPLE, GOLD = r2.PURPLE, r2.GOLD
WHITE, MUTED, FAINT = r2.WHITE, r2.MUTED, r2.FAINT
PANEL, PANEL_ALT = r2.PANEL, r2.PANEL_ALT
GREEN = r2.GREEN
CURRENT_SCENE = 0


def header_v3(draw: ImageDraw.ImageDraw, scene_no: int, section: str, title: str, subtitle: str) -> None:
    page_no = 6 if section == "THE FORECAST LEDGER" else scene_no
    r2.text(draw, (112, 42), "SIGNAL  /  NOISE     ·     FORECAST LEDGER", 19, MUTED)
    r2.text(draw, (W - 112, 42), f"{page_no:02d} / 07", 18, MUTED, anchor="ra")
    draw.line((112, 82, W - 112, 82), fill=(59, 55, 85), width=2)
    r2.text(draw, (112, 111), section.upper(), 19, PURPLE)
    r2.text(draw, (112, 147), title, 44, WHITE)
    r2.text(draw, (112, 205), subtitle, 20, MUTED)


def footer_v3(draw: ImageDraw.ImageDraw, scene_no: int) -> None:
    page_no = CURRENT_SCENE
    draw.line((112, 1012, W - 112, 1012), fill=(42, 41, 59), width=1)
    r2.text(draw, (112, 1027), "MUSE × CODEX     /     2026.10.21", 15, FAINT)
    r2.text(draw, (W - 112, 1027), f"{page_no:02d}   ·   07", 15, FAINT, anchor="ra")


r2.header = header_v3
r2.footer = footer_v3


def draw_intro(image: Image.Image, t: float, data: dict) -> None:
    d = ImageDraw.Draw(image)
    r2.text(d, (142, 174), "A FORECAST LEDGER  /  2026—2027", 20, GOLD)
    r2.text(d, (138, 240), "信号与噪声", 82, WHITE)
    r2.text(d, (143, 345), "预测台账", 66, WHITE)
    r2.text(d, (147, 448), "概率，不是预言   ·   2026-10-21 立账 v3", 26, MUTED)
    d.line((146, 515, 653, 515), fill=PURPLE, width=4)
    r2.text(d, (145, 548), "让每个判断，都留下可以复盘的刻度。", 27, WHITE)
    cx, cy = 1410, 425
    for radius in (132, 184, 238):
        d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(41, 38, 65), width=2)
    d.arc((cx - 184, cy - 184, cx + 184, cy + 184), 210, 322, fill=PURPLE, width=4)
    d.arc((cx - 238, cy - 238, cx + 238, cy + 238), 21, 118, fill=GOLD, width=3)
    d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=GOLD)
    r2.text(d, (cx, cy - 36), "P", 62, WHITE, anchor="mm")
    r2.text(d, (cx, cy + 30), "0.00—1.00", 19, MUTED, anchor="mm")
    reveal = min(1.0, max(0.0, (t - 0.7) / 6.2))
    for i, method in enumerate(data["method_six"]):
        active = reveal >= i / 6.0
        color = WHITE if active else (74, 75, 91)
        y = 760 + i * 39
        r2.text(d, (145, y), f"{i + 1:02d}", 17, GOLD if active else (73, 67, 50))
        r2.text(d, (194, y - 2), method, 21, color)
        bar_w = 160 * r2.ease_out((reveal - i / 6.0) * 5 + 0.05)
        d.line((455, y + 15, 455 + bar_w, y + 15), fill=PURPLE if active else (48, 46, 64), width=2)
    footer_v3(d, 0)


def draw_stocks(image: Image.Image, t: float, data: dict) -> None:
    r2.draw_stock_cards(image, t, data)
    d = ImageDraw.Draw(image)
    for i, stock in enumerate(data["stocks"]):
        x = 112 + i * (406 + 24)
        r2.text(d, (x + 29, 264 + 239),
                f"{stock['rmb_reference']} · 人民币参考（汇率 6.69）", 12, MUTED)


def panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    r2.rounded(draw, box, PANEL, (44, 43, 63), 18, 2)


def draw_seedance_prices(image: Image.Image, t: float, data: dict) -> None:
    d = ImageDraw.Draw(image)
    header_v3(d, 4, "SEEDANCE · OFFICIAL & CHANNEL", "Seedance 官方价与渠道分化",
              "官方梯队、同模型渠道价差、国内补贴价分屏呈现   /   ¥/秒")
    official = data["seedance_prices"]["official"]
    left_box = (112, 262, 758, 646)
    right_box = (780, 262, 1808, 646)
    panel(d, left_box)
    panel(d, right_box)
    r2.text(d, (136, 282), official["title"], 23, WHITE)
    r2.text(d, (136, 320), "国内官方人民币价 · 720p 新一代溢价约 52%", 14, MUTED)
    columns = ((432, "480p"), (540, "720p"), (652, "1080p"))
    for x, name in columns:
        r2.text(d, (x, 355), name, 15, MUTED, anchor="ra")
    for i, row in enumerate(official["rows"]):
        y = 377 + i * 55
        r2.text(d, (136, y), row["model"], 17, WHITE)
        for (x, _), value in zip(columns, row["values"]):
            r2.text(d, (x, y), "—" if value is None else f"¥{value:.3f}", 16,
                    GOLD if row["model"] == "2.5" else WHITE, anchor="ra")
        if i < len(official["rows"]) - 1:
            d.line((136, y + 31, 734, y + 31), fill=(36, 37, 53), width=1)
    r2.text(d, (136, 607), "官方价 10/15 建基线；10/17–21 五次检查，未见调价", 12, MUTED)

    r2.text(d, (804, 282), "2.5 · 720p 同模型渠道价差", 23, WHITE)
    r2.text(d, (1778, 288), "标价 / 渠道价", 13, MUTED, anchor="ra")
    channel_rows = data["seedance_prices"]["channels"]
    bar_x, max_w, max_price = 1010, 490, 3.16
    for i, row in enumerate(channel_rows):
        y = 325 + i * 32
        r2.text(d, (804, y), row["name"], 14, GOLD if i == 0 else WHITE)
        width = max_w * row["price"] / max_price * r2.ease_out((t - 0.7 - i * 0.3) / 1.0)
        r2.rounded(d, (bar_x, y + 4, bar_x + max(2, width), y + 19),
                   GOLD if i == 0 else PURPLE, radius=7)
        r2.text(d, (bar_x + max_w + 12, y), f"¥{row['price']:.3f}".rstrip("0").rstrip("."),
                14, WHITE)
    r2.text(d, (804, 615), "渠道标价仅作同模型横向比较；价格快照：2026-10-15 至 10-21", 12, MUTED)

    subsidy_box = (112, 668, 1808, 974)
    panel(d, subsidy_box)
    r2.text(d, (136, 688), "国内补贴渠道", 23, WHITE)
    r2.text(d, (1778, 694), "补贴价 · 非标价   /   ¥/秒", 15, GOLD, anchor="ra")
    subsidies = data["seedance_prices"]["subsidies"]
    x_positions = [152, 560, 968, 1376]
    for i, (row, x) in enumerate(zip(subsidies, x_positions)):
        r2.rounded(d, (x, 742, x + 360, 846), PANEL_ALT, (39, 40, 57), 13, 1)
        r2.text(d, (x + 18, 754), row["name"], 19, WHITE)
        r2.text(d, (x + 340, 754), f"约 ¥{row['price']:.2f}", 17, GOLD, anchor="ra")
        w = 276 * row["price"] / 0.5 * r2.ease_out((t - 3.0 - i * 0.35) / 1.2)
        r2.rounded(d, (x + 18, 794, x + 18 + max(3, w), 806), PURPLE, radius=6)
        d.line((x + 18, 811, x + 294, 811), fill=(48, 49, 65), width=1)
        r2.text(d, (x + 18, 820), "补贴价，非标价", 12, MUTED)
    r2.text(d, (136, 871), data["seedance_prices"]["subsidy_footnote"], 14, GOLD)
    r2.text(d, (136, 902), "来源：BigGo 2026-08-13 + 我方价格监控基线；火山官方锚 ¥1.512/秒", 14, MUTED)
    r2.text(d, (136, 926), data["seedance_prices"]["footnote"], 14, MUTED)
    footer_v3(d, 4)


def draw_competitor_prices(image: Image.Image, t: float, data: dict) -> None:
    d = ImageDraw.Draw(image)
    header_v3(d, 5, "COMPETITIVE PRICE BANDS", "竞争品牌：价格带已经铺满",
              "官方 API 价与渠道实测分开标注；Wan 只列区间，不进口播   /   ¥/秒")
    rows = data["competitor_prices"]["rows"]
    box = (112, 262, 1808, 966)
    panel(d, box)
    r2.text(d, (140, 278), "品牌 / 模型与口径", 15, MUTED)
    r2.text(d, (655, 278), "相对每秒价格（线性比例）", 15, MUTED)
    r2.text(d, (1450, 278), "价格", 15, MUTED)
    r2.text(d, (1778, 278), "来源 / 口径", 15, MUTED, anchor="ra")
    bar_x, bar_w, max_price = 655, 710, 2.68
    row_h = 42
    for i, row in enumerate(rows):
        y = 308 + i * row_h
        if i % 2 == 0:
            r2.rounded(d, (130, y - 3, 1790, y + 35), PANEL_ALT, radius=7)
        r2.text(d, (140, y + 3), row["name"], 14, WHITE)
        if "range" in row:
            lo, hi = row["range"]
            left = bar_x + bar_w * lo / max_price
            right = bar_x + bar_w * hi / max_price
            d.line((bar_x, y + 15, bar_x + bar_w, y + 15), fill=(35, 36, 52), width=5)
            d.line((left, y + 15, right, y + 15), fill=GREEN, width=10)
            d.line((left, y + 7, left, y + 23), fill=GREEN, width=2)
            d.line((right, y + 7, right, y + 23), fill=GREEN, width=2)
            price_label = f"¥{lo:.2f}–{hi:.2f}"
        else:
            d.line((bar_x, y + 15, bar_x + bar_w, y + 15), fill=(35, 36, 52), width=5)
            width = bar_w * row["price"] / max_price * r2.ease_out((t - 0.7 - i * 0.12) / 0.75)
            color = GREEN if "渠道实测" in row["name"] else PURPLE
            r2.rounded(d, (bar_x, y + 10, bar_x + max(3, width), y + 20), color, radius=5)
            price_label = f"约 ¥{row['price']:.2f}"
        r2.text(d, (1450, y + 2), price_label, 14, GOLD if "渠道实测" in row["name"] else WHITE)
        source = row["source"]
        if len(source) > 26:
            source = source[:25] + "…"
        r2.text(d, (1778, y + 4), source, 12, MUTED, anchor="ra")
    r2.text(d, (140, 941), data["competitor_prices"]["footnote"], 14, MUTED)
    footer_v3(d, 5)


def draw_ledger(image: Image.Image, t: float, data: dict) -> None:
    r2.draw_ledger(image, t, data)
    d = ImageDraw.Draw(image)
    r2.text(d, (112, 984), data["stock_rmb_footnote"], 12, MUTED)


SCENE_RENDERERS = (
    draw_intro, draw_stocks, r2.draw_memory, r2.draw_duel,
    draw_seedance_prices, draw_competitor_prices, draw_ledger,
)


def make_frame(global_t: float, data: dict) -> Image.Image:
    global CURRENT_SCENE
    durations = data["scene_seconds"]
    cursor, scene, scene_t = 0.0, len(durations) - 1, 0.0
    for i, duration in enumerate(durations):
        if global_t < cursor + duration or i == len(durations) - 1:
            scene, scene_t = i, global_t - cursor
            break
        cursor += duration
    CURRENT_SCENE = scene
    image = r2.background(scene, scene_t)
    SCENE_RENDERERS[scene](image, scene_t, data)
    fade = min(scene_t / 0.24, (durations[scene] - scene_t) / 0.24, 1.0)
    if fade < 1.0:
        image = Image.blend(Image.new("RGB", image.size, (0, 0, 0)), image, max(0.0, fade))
    return image


def save_storyboard(data: dict) -> list[str]:
    out_dir = ROOT / "video" / "frames-v3"
    out_dir.mkdir(parents=True, exist_ok=True)
    starts = [sum(data["scene_seconds"][:i]) for i in range(len(data["scene_seconds"]))]
    paths = []
    for i, start in enumerate(starts):
        mark = min(start + data["scene_seconds"][i] * 0.88, data["runtime_seconds"] - 0.1)
        image = make_frame(mark, data).resize((960, 540), Image.Resampling.LANCZOS)
        path = out_dir / f"scene-{i:02d}.jpg"
        image.save(path, format="JPEG", quality=92, optimize=True)
        paths.append(str(path.relative_to(ROOT)))
    return paths


def render(out_path: Path, preview_only: bool = False) -> dict:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if preview_only:
        return {"storyboard_frames": save_storyboard(data), "preview_only": True}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    duration = float(data["runtime_seconds"])
    frame_count = int(sum(data["scene_frames"]))
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{W}x{H}",
           "-framerate", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert process.stdin is not None
    for frame_index in range(frame_count):
        frame = make_frame(frame_index / FPS, data)
        process.stdin.write(frame.tobytes())
        if frame_index % (FPS * 5) == 0:
            print(f"frame {frame_index + 1}/{frame_count}  t={frame_index / FPS:.1f}s", flush=True)
    process.stdin.close()
    code = process.wait()
    if code != 0:
        raise RuntimeError(f"FFmpeg video encode failed with status {code}")
    scenes = save_storyboard(data)
    report = {
        "output": str(out_path.resolve().relative_to(ROOT)),
        "duration_seconds": duration,
        "width": W,
        "height": H,
        "fps": FPS,
        "frames": frame_count,
        "audio": "separate narration and Udio mix applied by mix_v3.py",
        "background": "procedural code-generated gradient, grid, orbit and particles",
        "storyboard_frames": scenes,
        "source_data": str(DATA_PATH.relative_to(ROOT)),
        "renderer": str(Path(__file__).relative_to(ROOT)),
    }
    (ENGINEERING / "render-report-v3.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "video" / "output" / "forecast-ledger-v3.silent.mp4")
    parser.add_argument("--storyboard-only", action="store_true")
    args = parser.parse_args()
    report = render(args.out, args.storyboard_only)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
