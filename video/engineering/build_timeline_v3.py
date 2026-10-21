#!/usr/bin/env python3
"""Build the v3 timeline from the frozen v2 ledger plus approved price data."""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINEERING = Path(__file__).resolve().parent
FFPROBE = "/opt/homebrew/bin/ffprobe"
FPS = 24


def duration(path: Path) -> float:
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def scene_frames(index: int, original_frames: int, voice_seconds: float) -> int:
    lead = 1.0 if index == 0 else 0.5
    safety_tail = 0.6
    return max(original_frames, math.ceil((voice_seconds + lead + safety_tail) * FPS))


def build() -> dict:
    data = json.loads((ENGINEERING / "timeline.json").read_text(encoding="utf-8"))
    data["edition"] = "v3"
    data["scene_order"] = [
        "intro", "stocks", "memory", "duel", "seedance-prices", "competitor-prices", "ledger"
    ]
    voice_paths = [ROOT / "video" / "assets" / "narration" / f"scene-{i:02d}.mp3" for i in range(7)]
    voice_seconds = [duration(path) for path in voice_paths]
    original_frames = [8 * FPS, 32 * FPS, 30 * FPS, 25 * FPS, 0, 0, 20 * FPS]
    frames = [
        scene_frames(i, original_frames[i], voice_seconds[i]) if i < 4 or i == 6
        else math.ceil((voice_seconds[i] + 0.5 + 0.6) * FPS)
        for i in range(7)
    ]
    # The repository amendment allocates roughly 65–70 seconds to the two new scenes.
    frames[4], frames[5] = 33 * FPS, 32 * FPS
    data["voice_seconds"] = voice_seconds
    data["voice_lead_seconds"] = [1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    data["scene_frames"] = frames
    data["scene_seconds"] = [n / FPS for n in frames]
    data["runtime_seconds"] = sum(frames) / FPS
    data["rmb_exchange_rate"] = 6.69
    rmb = {"SPCX": "约 ¥977", "AMD": "约 ¥3,577", "NVDA": "约 ¥1,448", "META": "约 ¥4,645"}
    for stock in data["stocks"]:
        stock["rmb_reference"] = rmb[stock["ticker"]]
        stock["rmb_reference_note"] = "人民币参考（汇率 6.69）"
    for row in data["ledger"]:
        if row["id"] in {"S1", "S2", "S3", "S4"}:
            ticker = {"S1": "SPCX", "S2": "AMD", "S3": "NVDA", "S4": "META"}[row["id"]]
            row["short"] += f"（{rmb[ticker]}）"

    data["stock_rmb_footnote"] = "人民币为按 6.69 折算的参考值，到期判定以美元收盘价为准"
    data["seedance_prices"] = {
        "official": {
            "title": "Seedance 官方价梯队",
            "unit": "¥/秒",
            "columns": ["480p", "720p", "1080p"],
            "rows": [
                {"model": "2.5", "values": [0.672, 1.512, 3.742]},
                {"model": "2.0 标准", "values": [0.462, 0.994, 2.478]},
                {"model": "2.0 Fast", "values": [0.372, 0.800, None]},
                {"model": "2.0 Mini", "values": [0.232, 0.496, None]},
            ],
            "source": "火山引擎国内官方价目表；10/15 建基线，10/17–21 连续五次检查均未调价",
            "trend": "2.5 720p ¥1.512，较 2.0 标准 720p ¥0.994 溢价约 52%",
        },
        "channels": [
            {"name": "国内官方（锚）", "price": 1.512, "source": "火山引擎国内官方价目表"},
            {"name": "Replicate", "price": 1.55, "source": "Replicate 公开报价，按 6.69 折算"},
            {"name": "Segmind", "price": 1.60, "source": "Segmind 公开报价，按 6.69 折算"},
            {"name": "Pika API", "price": 1.63, "source": "Pika API token 口径，按 6.69 折算"},
            {"name": "apimodels.app", "price": 1.81, "source": "apimodels.app 公开报价，按 6.69 折算"},
            {"name": "Atlas Cloud", "price": 2.01, "source": "Atlas Cloud 公开报价，按 6.69 折算"},
            {"name": "Kie.ai", "price": 2.11, "source": "Kie.ai credit 口径，按 6.69 折算"},
            {"name": "Wavespeed 标准", "price": 2.41, "source": "Wavespeed 标准端点报价，按 6.69 折算"},
            {"name": "fal.ai", "price": 3.16, "source": "fal.ai 公开报价，按 6.69 折算"},
        ],
        "subsidies": [
            {"name": "Flova", "price": 0.23, "source": "BigGo 2026-08-13 + 我方价格监控基线"},
            {"name": "TapNow", "price": 0.24, "source": "BigGo 2026-08-13 + 我方价格监控基线"},
            {"name": "OiiOii", "price": 0.27, "source": "BigGo 2026-08-13 + 我方价格监控基线"},
            {"name": "LibTV", "price": 0.40, "source": "BigGo 2026-08-13 + 我方价格监控基线"},
        ],
        "footnote": "价格为 2026 年 10 月核查口径，渠道价随时变动；美元报价按 6.69 折算，展示人民币",
        "subsidy_footnote": "补贴价 · 非标价；BigGo 2026-08-13 + 我方基线；官方价 ¥1.512/秒，补贴价约为官方 15%–26%",
    }
    data["competitor_prices"] = {
        "unit": "¥/秒，720p 附近口径",
        "rows": [
            {"name": "可灵 Kling 3.0 · 无音频", "price": 0.56, "source": "官方 API 价目折算；framesurfer 2026-10-13 复核"},
            {"name": "可灵 Kling 3.0 · 原生音频", "price": 0.84, "source": "官方 API 价目折算；framesurfer 2026-10-13 复核"},
            {"name": "可灵 Kling 2.5 Turbo · 无音频", "price": 0.28, "source": "官方 API 价目折算；framesurfer 2026-10-13 复核"},
            {"name": "MiniMax H3 · 768p", "price": 0.54, "source": "MiniMax 官方 pay-as-you-go，按 6.69 折算"},
            {"name": "MiniMax Hailuo 2.3 · 768p", "price": 0.31, "source": "MiniMax 官方按条价折算每秒"},
            {"name": "Google Veo 3.1 Fast", "price": 0.67, "source": "Gemini API 官方价目，720p 带音频"},
            {"name": "Google Veo 3.1 标准版", "price": 2.68, "source": "Gemini API 官方价目"},
            {"name": "Runway Gen-4 Turbo", "price": 0.33, "source": "Runway 官方挂牌，第三方复核"},
            {"name": "Runway Gen-4.5", "price": 0.80, "source": "Runway 12 credits/秒折算"},
            {"name": "Luma Ray 3.2", "price": 0.60, "source": "Higgsfield 每 10 秒 clip 对照表"},
            {"name": "PixVerse V6 · 渠道实测", "price": 0.27, "source": "第三方渠道实测，768p，token 计量"},
            {"name": "PixVerse C1 · 渠道实测", "price": 0.21, "source": "第三方渠道实测，768p，token 计量"},
            {"name": "Vidu Q3 · 渠道实测", "price": 0.52, "source": "第三方渠道实测，768p，token 计量"},
            {"name": "Vidu Q3 Pro · 渠道实测", "price": 0.62, "source": "第三方渠道实测，768p，token 计量"},
            {"name": "阿里 Wan 系列 · 仅列区间", "range": [0.13, 0.67], "source": "第三方 API 渠道报价区间；只入表、不进口播"},
        ],
        "footnote": "价格为 2026 年 10 月核查口径，渠道价随时变动；美元报价按 6.69 折算，展示人民币；来源：官方 API 价目及表内注明渠道",
    }
    output = ENGINEERING / "timeline-v3.json"
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    result = build()
    print(json.dumps({"runtime_seconds": result["runtime_seconds"], "scene_seconds": result["scene_seconds"],
                      "voice_seconds": result["voice_seconds"]}, ensure_ascii=False, indent=2))
