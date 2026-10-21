#!/usr/bin/env python3
"""Create a quiet, original pulse-based electronic bed for the 115s film."""
from __future__ import annotations

import argparse
import math
import wave
from pathlib import Path

import numpy as np


def make_block(start: int, count: int, rate: int, duration: float) -> np.ndarray:
    t = (start + np.arange(count, dtype=np.float64)) / rate
    beat = 60.0 / 96.0
    bar = beat * 4
    bar_index = np.floor(t / bar).astype(np.int64) % 4
    local_bar = np.mod(t, bar)
    fade_in = np.clip(t / 2.0, 0.0, 1.0)
    fade_out = np.clip((duration - t) / 3.0, 0.0, 1.0)
    envelope = np.minimum(fade_in, fade_out)

    # A restrained four-chord minor progression; every component stays well below dialogue level.
    chords = ((45, 52, 57), (41, 48, 53), (36, 43, 48), (43, 50, 55))
    pad = np.zeros(count, dtype=np.float64)
    for chord_index, notes in enumerate(chords):
        gate = (bar_index == chord_index).astype(np.float64)
        chord = np.zeros(count, dtype=np.float64)
        for note in notes:
            hz = 440.0 * (2.0 ** ((note - 69) / 12.0))
            chord += np.sin(2.0 * math.pi * hz * t + 0.08 * np.sin(2.0 * math.pi * 0.13 * t))
        pad += gate * chord / 3.0
    pad *= 0.035

    # Soft kick every other beat and a very quiet filtered tick on eighth notes.
    beat_phase = np.mod(t, beat)
    beat_index = np.floor(t / beat).astype(np.int64)
    kick_gate = (beat_index % 2 == 0).astype(np.float64)
    kick_env = np.exp(-beat_phase * 13.0) * kick_gate
    kick_hz = 42.0 + 32.0 * np.exp(-beat_phase * 24.0)
    kick = np.sin(2.0 * math.pi * kick_hz * beat_phase) * kick_env * 0.10

    eighth_phase = np.mod(t, beat / 2.0)
    noise_rng = np.random.default_rng(start + 20261021)
    tick_noise = noise_rng.standard_normal(count)
    tick = tick_noise * np.exp(-eighth_phase * 95.0) * 0.006

    # Three-note bell figure on alternating eighths, tucked behind the data.
    melody = np.asarray((76, 79, 83, 79, 74, 77, 81, 77), dtype=np.int64)
    step = np.floor(t / (beat / 2.0)).astype(np.int64)
    step_phase = np.mod(t, beat / 2.0)
    note = melody[step % len(melody)]
    note_hz = 440.0 * np.power(2.0, (note - 69) / 12.0)
    bell = np.sin(2.0 * math.pi * note_hz * step_phase) * np.exp(-step_phase * 10.0) * 0.012

    mono = (pad + kick + tick + bell) * envelope
    mono = np.tanh(mono * 1.35) * 0.62
    # Slight stereo width from slow, subtle modulation; no hard-panned elements.
    width = 0.008 * np.sin(2.0 * math.pi * 0.17 * t)
    stereo = np.stack((mono * (1.0 - width), mono * (1.0 + width)), axis=1)
    return np.clip(stereo, -0.95, 0.95)


def write_score(out_path: Path, duration: float = 115.0, rate: int = 48000) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = int(round(duration * rate))
    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        cursor = 0
        block_size = rate * 2
        while cursor < total:
            count = min(block_size, total - cursor)
            block = make_block(cursor, count, rate, duration)
            pcm = (block * 32767.0).astype("<i2", copy=False)
            wav.writeframes(pcm.tobytes())
            cursor += count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=115.0)
    args = parser.parse_args()
    write_score(args.out, args.duration)


if __name__ == "__main__":
    main()
