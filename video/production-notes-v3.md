# v3 录制与混音说明

## 录制

- 通道：豆包语音体验中心网页，Doubao - TTS 2.0。
- 音色：温柔妈妈 2.0（成年女性）。
- 语音指令：成年女性新闻讲解风格，语气沉稳、清晰、自然克制，语速利落，接近每秒 5 个汉字，不拖沓，不要广告腔；只朗读原文，不增删内容。
- 语速滑块：14。为响应“旁白语音要快一些，不能说得太慢”，采用比默认更利落的速度；数字和英文型号按仓库定稿原文逐字照录。
- 七段音频均为独立 MP3，旁白总时长 154.632 秒。

| 幕 | 音频 | 实际时长 | 画面时长 | 说明 |
|---|---|---:|---:|---|
| 00 片头 | `assets/narration/scene-00.mp3` | 5.160 秒 | 8.000 秒 | 旁白从第 1 秒开始 |
| 01 股票 | `assets/narration/scene-01.mp3` | 34.296 秒 | 35.417 秒 | 原 32 秒幕延长 3.417 秒 |
| 02 内存趋势 | `assets/narration/scene-02.mp3` | 30.408 秒 | 31.542 秒 | 原 30 秒幕延长 1.542 秒 |
| 03 三星 vs 海力士 | `assets/narration/scene-03.mp3` | 22.368 秒 | 25.000 秒 | 保留原幕时长 |
| 04 Seedance 价格与渠道 | `assets/narration/scene-04.mp3` | 26.544 秒 | 33.000 秒 | 新增幕 |
| 05 竞争品牌价格带 | `assets/narration/scene-05.mp3` | 25.656 秒 | 32.000 秒 | 新增幕 |
| 06 台账收尾 | `assets/narration/scene-06.mp3` | 10.200 秒 | 20.000 秒 | 保留原幕时长 |

新增两幕画面合计 65 秒；幕间保留约 0.6 秒呼吸。全片 4,439 帧、24 fps，最终时长 184.958 秒，低于 185 秒上限。

## 音乐与混音

- 音乐正本：`assets/udio-underscore-v3.mp3`，时长 143.184 秒，SHA-256：`73c72fa2dcb00205a6e6911403f1829663139f5666bd11992ca2207ddf2aa87f`。音乐循环至片尾并作 2 秒淡出；未使用 `synth_score.py`。
- 每段旁白先归一至 −17 LUFS；Udio 音乐底电平降低 9 dB，并由旁白侧链闪避：threshold 0.03、ratio 10:1、attack 35 ms、release 650 ms。无旁白时音乐恢复。
- 母带目标 −16 LUFS、−1.5 dBTP。最终响度测量：−16.20 LUFS、−1.50 dBTP。

## 画面与复现

- 成片：`output/forecast-ledger-v3.mp4`（H.264，1920×1080，24 fps；AAC 双声道 48 kHz）。
- 画面由代码生成，新增价格均来自 `seedance-competition-supplement.md`；两幕只显示人民币，并按官方价、渠道价和补贴价分组。股票人民币值只作参考，判定仍以美元收盘价为准。
- v2 原工程、成片及其报告未改写。ComfyUI 按冻结指令停止复测，v3 沿用程序化背景。
- 复现画面：`python3 video/engineering/build_timeline_v3.py`，再运行 `python3 video/engineering/render_v3.py --out video/output/forecast-ledger-v3.silent.mp4`；最后运行 `python3 video/engineering/mix_v3.py`。
- 报告：`engineering/render-report-v3.json`、`engineering/mix-report-v3.json`；分幕预览：`frames-v3/`。
