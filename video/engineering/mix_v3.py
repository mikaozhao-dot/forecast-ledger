#!/usr/bin/env python3
"""Mix the v3 narration with the delivered Udio bed and target -16 LUFS."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINEERING = Path(__file__).resolve().parent
VIDEO = ROOT / "video"
FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"
TIMELINE = ENGINEERING / "timeline-v3.json"


def run(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, check=True, text=True, capture_output=capture)
    except subprocess.CalledProcessError as error:
        if error.stderr:
            print(error.stderr, file=__import__("sys").stderr)
        raise


def probe_duration(path: Path) -> float:
    result = run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture=True)
    return float(result.stdout.strip())


def build_filter(data: dict) -> tuple[list[str], str, float]:
    scene_starts = [sum(data["scene_seconds"][:i]) for i in range(len(data["scene_seconds"]))]
    offsets = [start + lead for start, lead in zip(scene_starts, data["voice_lead_seconds"])]
    duration = float(data["runtime_seconds"])
    parts = [
        f"[1:a]atrim=duration={duration:.6f},asetpts=PTS-STARTPTS,volume=-9dB,"
        f"afade=t=out:st={max(0.0, duration - 2.0):.6f}:d=2[bed]"
    ]
    voice_labels = []
    for i, offset in enumerate(offsets):
        delay_ms = round(offset * 1000)
        parts.append(
            f"[{i + 2}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"loudnorm=I=-17:TP=-2:LRA=8,adelay={delay_ms}:all=1[v{i}]"
        )
        voice_labels.append(f"[v{i}]")
    parts.append(
        f"{''.join(voice_labels)}amix=inputs={len(voice_labels)}:duration=longest:"
        "dropout_transition=0:normalize=0,alimiter=limit=0.891[voice_pre]"
    )
    parts.append("[voice_pre]asplit=2[voice_mix][sidechain]")
    parts.append(
        "[bed][sidechain]sidechaincompress=threshold=0.03:ratio=10:attack=35:release=650:"
        "makeup=1[ducked]"
    )
    parts.append(
        "[voice_mix][ducked]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.891,aresample=48000[mixed]"
    )
    return parts, "[mixed]", duration


def main() -> None:
    data = json.loads(TIMELINE.read_text(encoding="utf-8"))
    silent = VIDEO / "output" / "forecast-ledger-v3.silent.mp4"
    music = VIDEO / "assets" / "udio-underscore-v3.mp3"
    voices = [VIDEO / "assets" / "narration" / f"scene-{i:02d}.mp3" for i in range(7)]
    output = VIDEO / "output" / "forecast-ledger-v3.mp4"
    if not all(path.is_file() for path in [silent, music, *voices]):
        raise FileNotFoundError("Missing v3 picture, Udio source, or one of the seven narration clips")
    if probe_duration(music) <= 0:
        raise ValueError("Udio source has no readable duration")
    parts, output_label, duration = build_filter(data)
    inputs = ["-i", str(silent), "-stream_loop", "-1", "-i", str(music)]
    for path in voices:
        inputs.extend(["-i", str(path)])
    common = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *inputs,
              "-filter_complex", ";".join(parts)]
    measure_parts = parts[:-1] + [
        parts[-1].replace("[mixed]", "[premeasure]"),
        "[premeasure]loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json[measured]",
    ]
    measure_prefix = common[:common.index("-filter_complex")]
    measure_prefix[measure_prefix.index("-loglevel") + 1] = "info"
    measure = run([*measure_prefix, "-filter_complex", ";".join(measure_parts),
                   "-map", "[measured]", "-f", "null", "-"], capture=True)
    blocks = re.findall(r"\{[^{}]*\}", measure.stderr, flags=re.DOTALL)
    stats = None
    for block in reversed(blocks):
        try:
            candidate = json.loads(block)
        except json.JSONDecodeError:
            continue
        if "input_i" in candidate:
            stats = candidate
            break
    if stats is None:
        print(measure.stderr[-3000:], file=__import__("sys").stderr)
        raise RuntimeError("Could not read loudness measurements from FFmpeg")
    final_filter = (
        "[preloudnorm]loudnorm=I=-16:TP=-1.5:LRA=11:"
        f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
        f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}:linear=true:print_format=summary[aout]"
    )
    # Replace the terminal label from the common graph with the measured final loudness stage.
    final_parts = parts[:-1] + [parts[-1].replace("[mixed]", "[preloudnorm]"), final_filter]
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *inputs,
         "-filter_complex", ";".join(final_parts), "-map", "0:v:0", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{duration:.6f}",
         "-movflags", "+faststart", str(output)])
    report = {
        "output": str(output.relative_to(ROOT)),
        "runtime_seconds": probe_duration(output),
        "voice_files": [str(path.relative_to(ROOT)) for path in voices],
        "music_source": str(music.relative_to(ROOT)),
        "music_duration_seconds": probe_duration(music),
        "mix": {
            "narration": "each clip normalized to -17 LUFS, then mixed at its scene offset",
            "music": "Udio source looped to runtime, -9 dB bed gain, sidechain ducked by narration",
            "sidechain": "threshold 0.03, ratio 10:1, attack 35 ms, release 650 ms",
            "master_target": "-16 LUFS, -1.5 dBTP",
            "measurement": stats,
        },
    }
    (ENGINEERING / "mix-report-v3.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
