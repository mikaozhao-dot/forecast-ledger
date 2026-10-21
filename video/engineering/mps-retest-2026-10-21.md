# ComfyUI MPS 氛围复测（2026-10-21）

依据 `video/comfyui-fix-instruction.md`（仓库提交 `9736b22f`）执行。只改变启动设备选择：从启动参数移除 `--cpu`；ComfyUI 版本、工作流、模型、提示词与采样参数均未调整。只提交了一次工作流。

## 启动与环境

- 启动器实际命令：`/Users/mikao/Documents/ChatGPT/插件/.runtime/comfy/bin/comfy --workspace=/Users/mikao/ComfyUI launch -- --listen 127.0.0.1 --port 8188`
- ComfyUI 子进程命令：`main.py --listen 127.0.0.1 --port 8188`（无 `--cpu`）
- 地址：`http://127.0.0.1:8188`
- 版本：`v0.21.1-11-g77e2ed5e`；未升级
- 设备日志：`Device: mps`；Apple M5 Max，统一内存 128 GiB
- PyTorch：`2.13.0.dev20260515`

## 保持不变的输入

- 工作流：`video/engineering/comfy-atmosphere.json`
- 工作流 SHA-256：`18540c3317ece71f75601fb8cf030d6902a276bcc621eec85f95c1929b93967f`
- 校验：`valid: true`，0 错误、0 警告
- 模型：`flux1-dev-fp8.safetensors`
- 画布：1024×576；seed：20261021；采样：20 步，guidance 3.5，Euler / simple
- 提示词、工作流节点及参数原样保留

## 结果

- ComfyUI prompt ID：`4c7dbee6-107a-4451-aa39-ecacf46ccb22`
- 状态：正常完成，27.49 秒；输出 `video/assets/mps-retest-2026-10-21.png`
- 样本：纯黑帧，3,280 bytes，SHA-256 `246383a29ede61e79975bb7afdfbb0def8659e740fc0ef254792a3d39eed489c`
- 相关日志：
  - `[2026-10-21 18:44:47.323] Device: mps`
  - `[2026-10-21 18:46:02.949] model_type FLUX`
  - `[2026-10-21 18:46:07.962] VAE load device: mps, offload device: cpu, dtype: torch.bfloat16`
  - `[2026-10-21 18:46:29.598] 100%|██████████| 20/20 [00:18<00:00,  1.04it/s]`
  - `[2026-10-21 18:46:30.308] /Users/mikao/ComfyUI/nodes.py:1643: RuntimeWarning: invalid value encountered in cast`
  - `[2026-10-21 18:46:30.311] Prompt executed in 27.49 seconds`

MPS 下仍为黑帧，按指令到此停止 ComfyUI 排查与重试。视频使用已授权的程序化代码背景，不等待该问题。黑帧样本只作故障留档，没有进入成片。
