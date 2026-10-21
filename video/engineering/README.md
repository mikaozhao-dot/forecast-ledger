# 视频工程

- `timeline.json` 是本片逐帧绘制使用的数据与时间线。数值直接按仓库 `main@9eba71134566e7dd95a4c52e9f4730184571e10d` 的任务书、台账 v2.1 与四份 research 底稿录入。
- `render.py` 用 Pillow 绘制 1920×1080 图形与中文文字，并通过 FFmpeg 编为 H.264/AAC MP4。数据动画、概率条和所有文字都由代码生成。
- `synth_score.py` 合成 96 BPM 的低音量节奏型电子配乐；不含语音或采样素材。
- `render-report.json` 记录本次成片规格和预览帧路径。
- `mps-retest-2026-10-21.md` 记录按仓库冻结指令进行的单次 MPS 复测；样本仍为黑帧，故成片采用程序化氛围背景。

## 复现

```bash
python3 video/engineering/render.py --out video/output/forecast-ledger-v2.mp4
```

需要 Pillow、NumPy，以及带 `libx264` 与 AAC 编码器的 FFmpeg。片长由 2760 帧 / 24 fps 精确构成 115 秒。ComfyUI 的 `flux1-dev-fp8.safetensors` 在本机 MPS 路径仍输出黑帧并触发 `invalid value encountered in cast`；按冻结指令停止复测，成片使用程序化氛围背景。此前的失败样本 `video/assets/32e5f3f2_000.png` 与本次证据 `video/assets/mps-retest-2026-10-21.png` 均保留，均未进入成片。
