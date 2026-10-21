#!/usr/bin/env python3
"""Render the forecast-ledger film as exact, code-drawn 1920x1080 frames + FFmpeg."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ENGINEERING = Path(__file__).resolve().parent
DATA_PATH = ENGINEERING / "timeline.json"
PYTHON = sys.executable
FFMPEG = "/opt/homebrew/bin/ffmpeg"
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"

PURPLE = (124, 108, 255)
PURPLE_DARK = (55, 47, 117)
GOLD = (232, 179, 75)
GOLD_DARK = (101, 76, 35)
WHITE = (237, 236, 242)
MUTED = (151, 153, 170)
FAINT = (78, 81, 102)
PANEL = (16, 17, 27)
PANEL_ALT = (20, 21, 33)
GRID = (27, 28, 42)
GREEN = (111, 200, 167)
W, H, FPS = 1920, 1080, 24

FONT_CACHE: dict[int, ImageFont.FreeTypeFont] = {}
BASE_CACHE: dict[int, Image.Image] = {}


def font(size: int) -> ImageFont.FreeTypeFont:
    if size not in FONT_CACHE:
        FONT_CACHE[size] = ImageFont.truetype(FONT_PATH, size=size, index=0)
    return FONT_CACHE[size]


def text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], value: str, size: int,
         fill: tuple[int, int, int] = WHITE, spacing: int = 8, anchor: str | None = None) -> None:
    draw.multiline_text(xy, value, font=font(size), fill=fill, spacing=spacing, anchor=anchor)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float],
            fill: tuple[int, int, int] | None = None,
            outline: tuple[int, int, int] | None = None, radius: int = 20, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def ease_out(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return 1.0 - (1.0 - value) ** 3


def background(scene: int, elapsed: float) -> Image.Image:
    if scene not in BASE_CACHE:
        BASE_CACHE[scene] = make_base(scene)
    image = BASE_CACHE[scene].copy()
    d = ImageDraw.Draw(image)

    # Code-generated ambient orbit and moving data particles (no generated image assets).
    drift = elapsed * 11.0 + scene * 37.0
    cx, cy = 1490, 490
    for radius, color in ((182, (23, 25, 43)), (286, (25, 24, 42)), (394, (23, 21, 34))):
        d.arc((cx - radius, cy - radius, cx + radius, cy + radius), 196, 346,
              fill=color, width=2)
    d.polygon(((1370, 485), (1478, 340), (1605, 365), (1694, 526), (1594, 690), (1436, 650)),
              outline=(27, 27, 45))
    for i in range(26):
        phase = (drift * (0.013 + (i % 5) * 0.002) + i * 0.37) % (2 * math.pi)
        radius = 115 + (i * 67) % 315
        px = cx + math.cos(phase) * radius
        py = cy + math.sin(phase * 0.88) * radius * 0.58
        color = (49, 44, 91) if i % 4 else (93, 71, 46)
        d.ellipse((px - 2, py - 2, px + 2, py + 2), fill=color)
        if i > 0 and i % 3 == 0:
            prev_phase = (drift * (0.013 + (i % 5) * 0.002) + (i - 1) * 0.37) % (2 * math.pi)
            qx = cx + math.cos(prev_phase) * (115 + ((i - 1) * 67) % 315)
            qy = cy + math.sin(prev_phase * 0.88) * (115 + ((i - 1) * 67) % 315) * 0.58
            d.line((qx, qy, px, py), fill=(33, 31, 53), width=1)
    return image


def make_base(scene: int) -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    gx, gy = xx / W, yy / H
    purple_glow = np.exp(-(((gx - 0.77) / 0.46) ** 2 + ((gy - 0.32) / 0.58) ** 2) * 2.0)
    gold_glow = np.exp(-(((gx - 0.13) / 0.55) ** 2 + ((gy - 0.84) / 0.55) ** 2) * 2.6)
    base = np.empty((H, W, 3), dtype=np.uint8)
    base[:, :, 0] = np.clip(9 + gx * 5 + purple_glow * 6 + gold_glow * 2, 0, 255)
    base[:, :, 1] = np.clip(9 + gy * 4 + purple_glow * 4 + gold_glow * 2, 0, 255)
    base[:, :, 2] = np.clip(15 + gx * 9 + purple_glow * 13 + gold_glow * 3, 0, 255)
    image = Image.fromarray(base, mode="RGB")
    d = ImageDraw.Draw(image)

    # Quiet technical grid, kept behind the typography.
    for x in range(84, W, 96):
        d.line((x, 84, x, H - 62), fill=GRID, width=1)
    for y in range(112, H - 54, 84):
        d.line((86, y, W - 86, y), fill=GRID, width=1)
    return image


def header(draw: ImageDraw.ImageDraw, scene_no: int, section: str, title: str, subtitle: str) -> None:
    text(draw, (112, 42), "SIGNAL  /  NOISE     ·     FORECAST LEDGER", 19, MUTED)
    text(draw, (W - 112, 42), f"{scene_no:02d} / 05", 18, MUTED, anchor="ra")
    draw.line((112, 82, W - 112, 82), fill=(59, 55, 85), width=2)
    text(draw, (112, 111), section.upper(), 19, PURPLE)
    text(draw, (112, 147), title, 44, WHITE)
    text(draw, (112, 205), subtitle, 20, MUTED)


def footer(draw: ImageDraw.ImageDraw, scene_no: int) -> None:
    draw.line((112, 1012, W - 112, 1012), fill=(42, 41, 59), width=1)
    text(draw, (112, 1027), "MUSE × CODEX     /     2026.10.21", 15, FAINT)
    text(draw, (W - 112, 1027), f"{scene_no:02d}   ·   05", 15, FAINT, anchor="ra")


def draw_intro(image: Image.Image, t: float, data: dict) -> None:
    d = ImageDraw.Draw(image)
    text(d, (142, 174), "A FORECAST LEDGER  /  2026—2027", 20, GOLD)
    text(d, (138, 240), "信号与噪声", 82, WHITE)
    text(d, (143, 345), "预测台账", 66, WHITE)
    text(d, (147, 448), "概率，不是预言   ·   2026-10-21 立账 v2", 26, MUTED)
    d.line((146, 515, 653, 515), fill=PURPLE, width=4)
    text(d, (145, 548), "让每个判断，都留下可以复盘的刻度。", 27, WHITE)

    # Circular index element is also drawn from code, with no labels in the background layer.
    cx, cy = 1410, 425
    for radius in (132, 184, 238):
        d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(41, 38, 65), width=2)
    d.arc((cx - 184, cy - 184, cx + 184, cy + 184), 210, 322, fill=PURPLE, width=4)
    d.arc((cx - 238, cy - 238, cx + 238, cy + 238), 21, 118, fill=GOLD, width=3)
    d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=GOLD)
    text(d, (cx, cy - 36), "P", 62, WHITE, anchor="mm")
    text(d, (cx, cy + 30), "0.00—1.00", 19, MUTED, anchor="mm")

    list_y = 760
    reveal = min(1.0, max(0.0, (t - 0.7) / 6.2))
    for i, method in enumerate(data["method_six"]):
        threshold = i / 6.0
        active = reveal >= threshold
        color = WHITE if active else (74, 75, 91)
        y = list_y + i * 39
        text(d, (145, y), f"{i + 1:02d}", 17, GOLD if active else (73, 67, 50))
        text(d, (194, y - 2), method, 21, color)
        bar_w = 160 * ease_out((reveal - threshold) * 5 + 0.05)
        d.line((455, y + 15, 455 + bar_w, y + 15), fill=PURPLE if active else (48, 46, 64), width=2)
    footer(d, 0)


def draw_probability(draw: ImageDraw.ImageDraw, x: float, y: float, width: float, p: float,
                     progress: float, label: str = "命题成立概率") -> None:
    text(draw, (x, y - 35), label, 16, MUTED)
    text(draw, (x + width, y - 42), f"{p:.2f}", 24, GOLD, anchor="ra")
    rounded(draw, (x, y, x + width, y + 13), (31, 31, 47), radius=7)
    shown = max(0.0, min(p, p * ease_out(progress)))
    end = x + width * shown
    if end > x + 1:
        rounded(draw, (x, y, end, y + 13), PURPLE, radius=7)
    for tick in (0.25, 0.50, 0.75, 1.0):
        tx = x + width * tick
        draw.line((tx, y + 17, tx, y + 22), fill=(75, 75, 91), width=1)


def draw_stock_cards(image: Image.Image, t: float, data: dict) -> None:
    d = ImageDraw.Draw(image)
    header(d, 1, "MARKET SNAPSHOT", "四只股票，四种赔率", "股价锚点 → 52 周区间位置 → 命题成立概率   /   判定取 2027-01-29 收盘")
    stocks = data["stocks"]
    card_w, gap, left, top, card_h = 406, 24, 112, 264, 646
    for i, stock in enumerate(stocks):
        x = left + i * (card_w + gap)
        appear = ease_out((t - i * 1.35) / 1.1)
        rounded(d, (x, top, x + card_w, top + card_h), PANEL, (44, 43, 63), 22, 2)
        d.rounded_rectangle((x + 1, top + 1, x + card_w - 1, top + 10), radius=6,
                            fill=PURPLE if i % 2 == 0 else GOLD)
        text(d, (x + 29, top + 34), stock["ticker"], 32, WHITE)
        text(d, (x + 29, top + 78), stock["name"], 16, MUTED)
        text(d, (x + 29, top + 137), "锚价", 17, MUTED)
        text(d, (x + 27, top + 165), stock["anchor"], 39, GOLD)
        text(d, (x + 29, top + 216), stock["anchor_date"], 16, MUTED)

        if stock["ticker"] == "SPCX":
            axis_top, axis_bottom = top + 290, top + 450
            ax = x + 58
            d.line((ax, axis_top, ax, axis_bottom), fill=(80, 77, 103), width=3)
            lo, hi = 100.0, 230.0
            for level in sorted(stock["key_levels"], key=lambda row: row["value"]):
                yy = axis_bottom - (level["value"] - lo) / (hi - lo) * (axis_bottom - axis_top)
                tick_color = GOLD if level["label"].startswith("锚价") else PURPLE
                d.line((ax - 8, yy, ax + 10, yy), fill=tick_color, width=3)
                label_y = yy - 19 if level["label"].startswith("锚价") else yy - 3 if level["label"] == "发行价" else yy - 12
                text(d, (x + 88, label_y), f"{level['display']}   {level['label']}", 16,
                     GOLD if level["label"].startswith("锚价") else WHITE)
            text(d, (x + 29, top + 477), "关键价位标尺 · 口径各异，不绘区间位置", 14, MUTED)
        else:
            track_x, track_y, track_w = x + 31, top + 359, 344
            d.line((track_x, track_y, track_x + track_w, track_y), fill=(83, 80, 104), width=9)
            low = stock["range_low"]
            high = stock["range_high"]
            anchor = float(stock["anchor"].replace("$", ""))
            pos = (anchor - low) / (high - low)
            marker_x = track_x + pos * track_w
            d.ellipse((track_x - 8, track_y - 8, track_x + 8, track_y + 8), fill=FAINT)
            d.ellipse((track_x + track_w - 8, track_y - 8, track_x + track_w + 8, track_y + 8), fill=FAINT)
            d.line((marker_x, track_y - 21, marker_x, track_y + 22), fill=GOLD, width=4)
            text(d, (track_x, track_y + 26), stock["range_low_display"], 14, MUTED)
            text(d, (track_x + track_w, track_y + 26), stock["range_high_display"], 14, MUTED, anchor="ra")
            text(d, (x + 30, track_y + 61), "52 周区间位置", 16, MUTED)
            text(d, (x + card_w - 30, track_y + 61), "锚价", 15, GOLD, anchor="ra")

        progress = min(1.0, max(0.0, (t - i * 1.35 - 2.5) / 4.3))
        draw_probability(d, x + 30, top + 548, 300, stock["probability"], progress)
        text(d, (x + 30, top + 591), stock["signal"], 16, WHITE, spacing=7)
    footer(d, 1)


def draw_dram_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], t: float,
                    rows: list[dict]) -> None:
    x0, y0, x1, y1 = box
    rounded(draw, box, PANEL, (44, 43, 63), 22, 2)
    text(draw, (x0 + 28, y0 + 27), "01   DRAM 环比涨幅", 23, WHITE)
    text(draw, (x0 + 28, y0 + 67), "一般型 DRAM 合约价 · 台账 v2", 15, MUTED)
    chart_l, chart_r = x0 + 78, x1 - 40
    chart_t, chart_b = y0 + 139, y0 + 473
    for val in (0, 25, 50, 75, 100):
        yy = chart_b - (val / 100.0) * (chart_b - chart_t)
        draw.line((chart_l, yy, chart_r, yy), fill=(37, 38, 55), width=1)
        text(draw, (chart_l - 18, yy - 9), str(val), 13, FAINT, anchor="ra")
    visible = ease_out((t - 0.5) / 8.5)
    point_xs = [chart_l + 28 + i * ((chart_r - chart_l - 56) / 3) for i in range(4)]
    for i, row in enumerate(rows):
        if visible <= i / 4:
            continue
        draw_amt = min(1.0, max(0.0, (visible - i / 4) * 4.0))
        low_y = chart_b - (row["low"] / 100.0) * (chart_b - chart_t)
        high_y = chart_b - (row["high"] / 100.0) * (chart_b - chart_t)
        mid_y = (low_y + high_y) / 2.0
        px = point_xs[i]
        reach_y = chart_b - draw_amt * (chart_b - mid_y)
        if row["low"] == row["high"]:
            draw.line((px, reach_y - 9, px, reach_y + 9), fill=GOLD, width=4)
        else:
            # Range bars preserve the published interval, with no invented midpoint label.
            draw.line((px, reach_y, px, chart_b - draw_amt * (chart_b - high_y)), fill=PURPLE, width=10)
            if draw_amt >= 0.98:
                draw.line((px - 10, high_y, px + 10, high_y), fill=PURPLE, width=3)
                draw.line((px - 10, low_y, px + 10, low_y), fill=PURPLE, width=3)
        if i > 0 and visible > i / 4:
            # A directional guide only: it does not encode a separate point estimate.
            prev = rows[i - 1]
            py = chart_b - ((prev["low"] + prev["high"]) / 2.0 / 100.0) * (chart_b - chart_t)
            draw.line((point_xs[i - 1], py, px, mid_y), fill=(74, 57, 120), width=2)
        text(draw, (px, chart_b - 43), row["quarter"].replace(" 2026", ""), 14, MUTED, anchor="mm")
        if draw_amt >= 0.75:
            text(draw, (px, min(low_y, high_y) - 31), row["display"], 15,
                 GOLD if i == 3 else WHITE, anchor="mm")
    text(draw, (x0 + 28, y1 - 82), "涨幅峰已过、价格未见顶", 21, GOLD)
    text(draw, (x0 + 28, y1 - 43), "连线仅示方向；范围与限定词按原文保留", 13, MUTED)


def draw_hbm_scenarios(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], t: float,
                       scenarios: list[dict]) -> None:
    x0, y0, x1, y1 = box
    rounded(draw, box, PANEL, (44, 43, 63), 22, 2)
    text(draw, (x0 + 28, y0 + 27), "02   2027 HBM 均价情景", 23, WHITE)
    text(draw, (x0 + 28, y0 + 67), "同比涨幅预测 · 三家机构情景，不是概率分布", 15, MUTED)
    left, right = x0 + 172, x1 - 48
    top = y0 + 178
    span = right - left
    max_value = 130.0
    threshold_x = left + span * 80.0 / max_value
    for tick in (0, 40, 80, 120):
        xx = left + span * tick / max_value
        draw.line((xx, top - 27, xx, y1 - 178), fill=(39, 40, 56), width=1)
        text(draw, (xx, top - 50), f"+{tick}%", 13, FAINT, anchor="mm")
    draw.line((threshold_x, top - 8, threshold_x, y1 - 166), fill=GOLD, width=2)
    text(draw, (threshold_x + 8, y1 - 157), "台账线 +80%", 15, GOLD)
    for i, row in enumerate(scenarios):
        yy = top + i * 112
        label = row["label"]
        text(draw, (x0 + 28, yy + 11), label, 16, MUTED)
        progress = ease_out((t - 9.0 - i * 1.4) / 4.0)
        shown = min(row["value"], 50) if row.get("open_ended") else row["value"]
        length = span * shown / max_value * progress
        color = (119, 103, 235) if i == 0 else (PURPLE if i == 1 else GOLD)
        rounded(draw, (left, yy + 5, left + max(4, length), yy + 36), color, radius=15)
        if row.get("open_ended") and progress > 0.96:
            tip = left + span * 50 / max_value
            draw.line((tip + 4, yy + 20, tip + 22, yy + 20), fill=color, width=5)
            draw.polygon(((tip + 22, yy + 12), (tip + 35, yy + 20), (tip + 22, yy + 28)), fill=color)
        text(draw, (right, yy + 43), row["display"], 18, WHITE, anchor="ra")
    text(draw, (x0 + 28, y1 - 101), "海力士命题：2027 混合均价同比 ≥ +80%", 18, WHITE)
    text(draw, (x0 + 28, y1 - 65), "P = 0.55", 20, GOLD)


def draw_hbm_shares(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], t: float,
                    shares: list[dict]) -> None:
    x0, y0, x1, y1 = box
    rounded(draw, box, PANEL, (44, 43, 63), 22, 2)
    text(draw, (x0 + 28, y0 + 27), "03   HBM 营收份额", 23, WHITE)
    text(draw, (x0 + 28, y0 + 67), "Counterpoint · 约数，不归一化", 15, MUTED)
    colors = (PURPLE, GOLD, (114, 119, 141))
    keys = (("sk_hynix", "海力士"), ("samsung", "三星"), ("micron", "美光"))
    bar_x, bar_w = x0 + 42, x1 - x0 - 84
    capacity = 105.0
    for row_i, row in enumerate(shares):
        yy = y0 + 180 + row_i * 173
        text(draw, (bar_x, yy - 32), row["quarter"], 18, WHITE)
        rounded(draw, (bar_x, yy, bar_x + bar_w, yy + 43), (31, 31, 47), radius=15)
        cursor = bar_x
        progress = ease_out((t - 19.0 - row_i * 3.3) / 4.0)
        for j, (key, name) in enumerate(keys):
            amount = row[key]
            segment = bar_w * amount / capacity * progress
            if segment > 1:
                draw.rectangle((cursor, yy, cursor + segment, yy + 43), fill=colors[j])
            cursor += segment
        if progress > 0.98:
            # 100% reference is visible; the approximate 2026 values extend to 101% as stated.
            ref_x = bar_x + bar_w * 100.0 / capacity
            draw.line((ref_x, yy - 6, ref_x, yy + 50), fill=(189, 190, 202), width=1)
        legend_y = yy + 65
        cursor = bar_x
        for j, (key, name) in enumerate(keys):
            label = f"{name} {row[key]}%"
            dxy = (cursor, legend_y)
            draw.ellipse((cursor, legend_y + 4, cursor + 10, legend_y + 14), fill=colors[j])
            text(draw, (cursor + 17, legend_y - 2), label, 16, MUTED)
            cursor += (bar_w - 4) / 3
    text(draw, (x0 + 28, y1 - 93), "三星一年追 18 个百分点", 20, GOLD)
    text(draw, (x0 + 28, y1 - 56), "份额营收口径 · 2026 Q2 三家约数合计 101%", 15, MUTED)


def draw_memory(image: Image.Image, t: float, data: dict) -> None:
    d = ImageDraw.Draw(image)
    header(d, 2, "MEMORY CYCLE", "涨幅在降速，价格仍在高位", "趋势、机构情景与份额变化分开呈现   /   不把情景伪装成概率")
    gap, left, top = 22, 112, 265
    width = (W - 2 * left - 2 * gap) // 3
    height = 646
    boxes = [(left + i * (width + gap), top, left + i * (width + gap) + width, top + height)
             for i in range(3)]
    draw_dram_panel(d, boxes[0], t, data["dram_qoq"])
    draw_hbm_scenarios(d, boxes[1], t, data["hbm_2027_scenarios"])
    draw_hbm_shares(d, boxes[2], t, data["hbm_revenue_shares"])
    footer(d, 2)


def draw_company_table(draw: ImageDraw.ImageDraw, data: dict, t: float) -> None:
    x0, y0, x1, y1 = 112, 276, 1808, 772
    rounded(draw, (x0, y0, x1, y1), PANEL, (44, 43, 63), 22, 2)
    col1, col2, col3 = x0 + 420, x0 + 1020, x1 - 42
    text(draw, (x0 + 35, y0 + 27), "指标", 18, MUTED)
    text(draw, (col1, y0 + 27), "SAMSUNG", 19, GOLD)
    text(draw, (col2, y0 + 27), "SK hynix", 19, PURPLE)
    rows = [
        ("DRAM 营收份额", data["samsung"]["dram_share"], data["sk_hynix"]["dram_share"], "TrendForce · 2026 Q2"),
        ("HBM 营收份额", data["samsung"]["hbm_share"], data["sk_hynix"]["hbm_share"], "Counterpoint · 2026 Q2"),
        ("16 层 HBM", data["samsung"]["sixteen_layer"], data["sk_hynix"]["sixteen_layer"], "量产 / 商品化口径"),
    ]
    for i, row in enumerate(rows):
        yy = y0 + 82 + i * 112
        alpha = ease_out((t - 2.2 - i * 2.1) / 1.4)
        if alpha > 0.01:
            rounded(draw, (x0 + 20, yy, x1 - 20, yy + 86), PANEL_ALT,
                    (40, 40, 58), 14, 1)
            text(draw, (x0 + 35, yy + 16), row[0], 21, WHITE)
            text(draw, (col1, yy + 15), row[1], 24, GOLD if i != 2 else MUTED)
            text(draw, (col2, yy + 15), row[2], 24, PURPLE if i != 2 else GREEN)
            text(draw, (col3, yy + 21), row[3], 14, MUTED, anchor="ra")
    text(draw, (118, 806), "三星的两张牌", 19, GOLD)
    text(draw, (118, 844), "2031 年前约 70% 产能锁入 LTA 长约", 19, WHITE)
    text(draw, (948, 806), "HBM4E 进展", 19, PURPLE)
    text(draw, (948, 844), "据韩媒称已过 NVIDIA 与大客户测试 · 未官宣", 18, WHITE)
    text(draw, (118, 893), "M 组命题成立概率", 16, MUTED)
    ms = (("M1 DRAM", 0.58), ("M2 16 层", 0.40), ("M3 HBM 价", 0.55),
          ("M4 HBM 份额", 0.52), ("M5 NAND", 0.55))
    start_x, gap = 118, 326
    for i, (label, p) in enumerate(ms):
        x = start_x + i * gap
        text(draw, (x, 922), label, 14, MUTED)
        text(draw, (x + 280, 918), f"{p:.2f}", 17, GOLD, anchor="ra")
        rounded(draw, (x, 948, x + 280, 957), (32, 32, 48), radius=5)
        width = 280 * p * ease_out((t - 9.0 - i * 1.3) / 5.0)
        if width > 1:
            rounded(draw, (x, 948, x + width, 957), PURPLE, radius=5)


def draw_duel(image: Image.Image, t: float, data: dict) -> None:
    d = ImageDraw.Draw(image)
    header(d, 3, "TWO LEADERS · ONE CYCLE", "三星 vs 海力士：份额与路线", "市场份额看当前，技术节点看下一代   /   口径均随行标注")
    draw_company_table(d, data["company_comparison"], t)
    footer(d, 3)


def draw_ledger(image: Image.Image, t: float, data: dict) -> None:
    d = ImageDraw.Draw(image)
    header(d, 4, "THE FORECAST LEDGER", "十条命题，逐条留下刻度", "S / 股票   ·   M / 内存   ·   C / 行业   /   概率是命题成立概率")
    x0, x1, top = 112, 1808, 270
    id_x, statement_x, prob_x, due_x = 148, 258, 1260, 1772
    text(d, (id_x, top), "编号", 16, MUTED)
    text(d, (statement_x, top), "命题简称", 16, MUTED)
    text(d, (prob_x, top), "P", 16, MUTED, anchor="ra")
    text(d, (due_x, top), "到期 / 判定", 16, MUTED, anchor="ra")
    d.line((x0, top + 36, x1, top + 36), fill=(65, 61, 88), width=2)
    rows = data["ledger"]
    row_top = top + 48
    row_h = 58
    visible = ease_out((t - 1.0) / 9.0)
    count = int(math.ceil(visible * len(rows)))
    for i, row in enumerate(rows[:count]):
        yy = row_top + i * row_h
        if i % 2 == 0:
            rounded(d, (x0, yy - 2, x1, yy + row_h - 4), (15, 16, 25), radius=8)
        alpha = ease_out((visible * len(rows) - i))
        accent = GOLD if row["id"].startswith("S") else PURPLE if row["id"].startswith("M") else GREEN
        text(d, (id_x, yy + 12), row["id"], 17, accent)
        text(d, (statement_x, yy + 11), row["short"], 18, WHITE)
        rounded(d, (1032, yy + 21, 1224, yy + 30), (34, 34, 52), radius=5)
        bar_w = 192 * row["probability"] * alpha
        if bar_w > 1:
            rounded(d, (1032, yy + 21, 1032 + bar_w, yy + 30), accent, radius=5)
        text(d, (prob_x, yy + 6), f"{row['probability']:.2f}", 18, GOLD, anchor="ra")
        text(d, (due_x, yy + 9), row["due"], 16, MUTED, anchor="ra")
    note_y = row_top + 10 * row_h + 17
    text(d, (112, note_y), "到期逐条打分（Brier）——说错了，这张表会自己揭穿。", 24, WHITE)
    text(d, (112, note_y + 42), "S 组到期 2027-01-31，判定取 2027-01-29 收盘   ·   台账 v2.1", 17, GOLD)
    footer(d, 4)


SCENE_RENDERERS = (draw_intro, draw_stock_cards, draw_memory, draw_duel, draw_ledger)


def make_frame(global_t: float, data: dict) -> Image.Image:
    durations = data["scene_seconds"]
    cursor, scene, scene_t = 0.0, len(durations) - 1, 0.0
    for i, duration in enumerate(durations):
        if global_t < cursor + duration or i == len(durations) - 1:
            scene, scene_t = i, global_t - cursor
            break
        cursor += duration
    image = background(scene, scene_t)
    SCENE_RENDERERS[scene](image, scene_t, data)
    d = ImageDraw.Draw(image)
    # A 0.24s low-luminance reveal at scene cuts; the film runtime stays exactly 115s.
    fade = min(scene_t / 0.24, (durations[scene] - scene_t) / 0.24, 1.0)
    if fade < 1.0:
        black = Image.new("RGB", image.size, (0, 0, 0))
        image = Image.blend(black, image, max(0.0, fade))
    return image


def save_storyboard(data: dict) -> list[str]:
    out_dir = ROOT / "video" / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    starts = np.cumsum([0] + data["scene_seconds"][:-1]).tolist()
    marks = [min(starts[i] + data["scene_seconds"][i] * 0.88, sum(data["scene_seconds"]) - 0.1)
             for i in range(len(data["scene_seconds"]))]
    paths = []
    for i, mark in enumerate(marks):
        image = make_frame(mark, data)
        image = image.resize((960, 540), Image.Resampling.LANCZOS)
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
    frame_count = int(round(duration * FPS))
    ffmpeg_cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{W}x{H}",
        "-framerate", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", str(duration),
        str(out_path.with_suffix(".silent.mp4"))
    ]
    silent_path = out_path.with_suffix(".silent.mp4")
    ffmpeg_cmd[-1] = str(silent_path)
    process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    assert process.stdin is not None
    for frame_index in range(frame_count):
        timestamp = frame_index / FPS
        frame = make_frame(timestamp, data)
        process.stdin.write(frame.tobytes())
        if frame_index % (FPS * 5) == 0:
            print(f"frame {frame_index + 1}/{frame_count}  t={timestamp:.1f}s", flush=True)
    process.stdin.close()
    code = process.wait()
    if code != 0:
        raise RuntimeError(f"FFmpeg video encode failed with status {code}")

    with tempfile.TemporaryDirectory(prefix="forecast-ledger-") as temp_dir:
        wav_path = Path(temp_dir) / "score.wav"
        subprocess.run([PYTHON, str(ENGINEERING / "synth_score.py"), "--out", str(wav_path),
                        "--duration", str(duration)], check=True)
        mux_cmd = [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent_path),
            "-i", str(wav_path), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k", "-af", "afade=t=in:st=0:d=1.6,afade=t=out:st=111:d=4",
            "-t", str(duration), "-movflags", "+faststart", str(out_path)
        ]
        subprocess.run(mux_cmd, check=True)
    silent_path.unlink(missing_ok=True)
    scenes = save_storyboard(data)
    report = {
        "output": str(out_path.resolve().relative_to(ROOT)),
        "duration_seconds": duration,
        "width": W,
        "height": H,
        "fps": FPS,
        "frames": frame_count,
        "audio": "original synthesized electronic music; no narration",
        "background": "procedural code-generated gradient, grid, orbit and particles",
        "storyboard_frames": scenes,
        "source_data": str(DATA_PATH.relative_to(ROOT)),
        "renderer": str(Path(__file__).relative_to(ROOT))
    }
    (ROOT / "video" / "engineering" / "render-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "video" / "output" / "forecast-ledger-v2.mp4")
    parser.add_argument("--storyboard-only", action="store_true")
    args = parser.parse_args()
    report = render(args.out, args.storyboard_only)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
