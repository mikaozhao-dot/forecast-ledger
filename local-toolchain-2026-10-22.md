# 本地工具链就绪与调用方式（2026-10-22）

Muse 同步，全线通用基建文档。机器：用户 MacBook（M5 Max / 128GB），用户 mikao，Homebrew 在 `/opt/homebrew`，`~/.local/bin` 已在 PATH。以下工具均已由创始人本机安装、Muse 逐项核验输出/截图通过（2026-10-22），可直接调用。

## 工具清单

| 工具 | 版本 | 调用方式 | 要点 |
|---|---|---|---|
| FFmpeg | 9.0.2_1 | `ffmpeg` / `ffprobe`（PATH） | 拼片、混音、字幕、转码的主力，口径不变 |
| Python | 3.12.15 | `$(brew --prefix python@3.12)/bin/python3.12` | 脚本运行时。机器上另有 python@3.15：凡涉及 torch/mlx 的包一律用 3.12 环境装，**不要用 3.15**（依赖尚不支持，mlx-whisper 已实证踩坑） |
| pipx | 1.18.2 | `pipx install --python <3.12路径> <包>` | CLI 工具隔离安装；指定解释器用 `--python "$(brew --prefix python@3.12)/bin/python3.12"` |
| mlx-whisper | 0.4.3 | `mlx_whisper <音频> --model mlx-community/whisper-large-v3-turbo --language zh --output_dir <目录>` | 本地 ASR。模型已缓存于 `~/.cache/huggingface`（约 1.6GB），可离线运行。**输出默认写当前目录，务必显式给 `--output_dir`**；需要字幕用 `--output_format srt`。注意：静音/无声段可能出现字幕腔幻听，转写产出按既有纪律在关键处复核 |
| Blender | 5.2.2 | `blender`（已链 `/opt/homebrew/bin/blender`），应用在 `/Applications/Blender.app` | 无头渲染示例：`blender -b <file.blend> -a`；脚本用 `-P <script.py>` |
| REAPER | 7.82 | 应用 `/Applications/REAPER.app`；可执行 `/Applications/REAPER.app/Contents/MacOS/REAPER` | 音频工程与混音精修位。脚本化渲染前先小样验证，再批量跑 |
| DaVinci Resolve | 21.1.1（免费版） | 应用 `/Applications/DaVinci Resolve.app` | 定位＝人工终审精修（调色/剪辑）。**免费版无外部脚本权限，禁止尝试用脚本/API 驱动它**；自动化需求一律回 FFmpeg 管线 |
| Pinokio | 8.2.0 | 应用 `/Applications/Pinokio.app` | 一键安装 AI 应用的启动器；装好的应用位于 `~/pinokio/api/<应用名>`。第二批 CosyVoice 与 GPT-SoVITS 将经 Pinokio 安装，各自的本地端口与调用法在装好后另行补发 |
| Ollama 三模型 | — | 见 `docs/codex-local-model-strategy-2026-10-21.md`（forecast-ledger 仓为根目录同名文件） | 分工不变：gpt-oss:20b 短平快、gpt-oss:120b 动脑、gemma4:31b 中文/多模态杂活；任务输入要裁剪 |

## 纪律（与本地模型策略一致，重申）

1. 本地工具与本地模型**不接触任何密钥**；密钥只走既有安全通道。
2. 产出**落盘不贴回对话**，关键产出须经云端或 Muse 复核后才可采用。
3. ComfyUI 现有环境（0.21.1）**冻结纪律不变**：不得因本工具链就绪而自行升级版本、更换模型或重试黑帧工作流；黑帧问题另行立项。
4. facepack-s1 与 studio-promo 两线**仍处暂停状态**。本文件是通用基建同步，**不构成解冻**；解冻仍以 Muse 标题含「恢复执行」的新文件入仓为准。
5. 新装工具若需再装依赖：Python 包优先 pipx/3.12 环境；brew cask 先查令牌是否存在（davinci-resolve、pinokio 在官方 cask 库不存在，已实证；近似名软件不要装）。
