# 指令（Muse → Codex，2026-10-21）：ComfyUI 黑帧单变量复测

## 背景（创始人截图实证）
本机 ComfyUI 核心版本 **0.21.1**，启动参数为 `main.py --cpu --listen 127.0.0.1 --port 8188`。
判读：`--cpu` 使 M5 Max 的 Metal/MPS 加速完全未启用。此前 Partner 云节点任务不受影响（云端算力）；本次氛围测试是首个本地模型工作流，CPU+fp16 产生 NaN 是黑帧经典成因，与日志 `invalid value encountered in cast` 及黑帧样本吻合。

## 执行（只许动一个变量）
1. 以**去掉 `--cpu`** 的方式重启 ComfyUI（Apple Silicon 默认走 MPS），其余启动参数不变；
2. 版本（0.21.1）、工作流（engineering/comfy-atmosphere.json）、模型与全部参数**一律不动**，原样重跑氛围测试**一次**；
3. 结果推回本仓：复测记录 `video/engineering/mps-retest-2026-10-21.md`（写明实际启动命令、设备口径、日志关键行）+ 产出样本图（放 video/assets/，文件名标注 mps-retest）。

## 边界
- **不要升级 ComfyUI 版本**：0.21→0.40 跨度大，且 facepack 线 Derek 认证诊断正冻结待 Sol 接手，版本变更会污染其变量隔离；升级另行排期；
- 不要为"跑出图"顺手改工作流/换模型/加参数——本步是诊断，不是修复工程；
- 若 MPS 下仍黑帧：停手，把完整日志与样本留档推仓，在复测记录里写明" MPS 复测仍黑帧"，氛围层即按 answers-2026-10-21.md 已授权的**代码生成背景**路径继续视频制作，黑帧问题另行立项排查。
