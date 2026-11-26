<div align="center">
  <img src="https://registry.npmmirror.com/@lobehub/icons-static-png/1.74.0/files/dark/jimeng-color.png" width="120" />
</div>

## 2026年11月26日
- 新增 MAGI-2 视频生成节点，移植星朗3.5 Java 渠道协议与素材处理方式。

## 2026年11月25日
- 新增Seedance2.5 Flash模型，参数与官方一致
- 新增Seedream5.5 生图模型，参数与官方一致
# ComfyUI 即梦 API 节点

本项目为 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 提供了火山方舟的视觉模型（即梦/豆包） API 节点。用户可以通过这些节点在 ComfyUI 中使用多种图像生成和视频生成功能。

- 项目已支持 `Seedance 2.0`、`Seedance 2.0 Fast`、`Seedance 2.0 Mini` 与 `Seedance 2.5` 、`Seedance2.5 Flash🌟`；2.0 标准版最高支持 4K，2.5 最长支持 30 秒。
- 项目同时支持独立渠道模型 `MAGI-2`，从 Java 星朗3.5 渠道实现提取，支持公网素材直链与已加白素材 ID。
- 如在使用过程中遇到问题，请通过 [ISSUES](https://github.com/fkxianzhou/ComfyUI-Jimeng-API/issues) 反馈。
- Classic Canvas 与 Nodes 2.0（Vue）均受支持，最低支持 ComfyUI `0.25.1`。

## ✨ 项目特性

- **多 Key 管理**：支持在配置文件中设置多个 API Key，并在节点中灵活切换，方便管理不同账户或配额。
- **异步与并发**：所有核心节点均支持任务的异步提交和并发生成，无需阻塞队列，大幅提升批量生成效率。
- **友好交互**：提供清晰的控制台进度提示和完善的异常处理机制，报错信息直观，便于快速排查问题。

## 📦 安装

方式1：  **克隆仓库**:
打开终端，`cd` 到 ComfyUI 的 `custom_nodes` 目录，运行：

```bash
git clone https://github.com/fkxianzhou/ComfyUI-Jimeng-API
```

方式2： **使用ComfyUI Manager下载**。

## ⚙️ 设置：配置 API 密钥

### 方式 1：手动配置

1. 在插件根目录中找到 `api_keys.json.example` 文件。
2. 将其**重命名**为 `api_keys.json`。
3. 打开文件并填入您的密钥信息（[从此获取 Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey)）。

### 方式 2：节点内配置

1. 在 ComfyUI 中添加 **Jimeng API Client** 节点。
2. 在 `key_name` 下拉框中选择 **Custom**。
3. 在弹出的输入框中填入您的 API Key。
4. （可选）在 `new_key_name` 中填入一个名称（如 "MyKey"），运行一次后该 Key 将被自动保存。
   - *注意：保存后需刷新浏览器页面，新密钥才会显示在下拉列表中。*

## 📖 功能节点列表

(所有节点均位于 `JimengAI` 菜单下)

- **基础设置**:
  - `火山方舟 API 客户端`: **(必须)** 用于加载并创建一个可供其他节点使用的客户端实例。
  - `MAGI-2 API 客户端`: MAGI-2 独立渠道客户端，填写渠道分配的 API Key 与接口地址，不使用火山方舟密钥。
  - `Jimeng 配额设置`: 用于设置图像和视频生成的配额限制，防止意外消耗过多资源。
- **图像生成**:
  - `图像生成（Seedream 3）`: 基础图像生成节点。
  - `图像生成（Seedream 4）`: 高级图像生成节点，支持多图输入、**组图生成**以及 4.5 模型。
  - `图像生成（Seedream 5）`: 支持 Seedream 5.5、5 Pro/Lite；5.5 支持透明 RGBA 与**图层拆分**，Pro 提供提示词优化，Lite 支持组图与**联网搜索**。
- **视频生成**:
  - `视频生成（Seedance 1.0）`: 核心视频生成节点，支持文生视频、图生视频（首/尾帧）。
  - `视频生成（Seedance 1.5 Pro）`: 支持**音频生成**和**智能时长**的高级视频生成节点。
  - `视频生成（Seedance 2 / 2.5）`: 支持**图片/视频/音频多模态参考**、**视频编辑/延长**与**联网搜索增强**，覆盖 2.5 Flash。
  - `视频生成（MAGI-2）`: 移植 Java 星朗3.5 渠道，支持公网直链素材或已上传加白素材 ID。
  - `视频生成（参考图生视频）`: 根据 1-4 张**参考图像**生成视频。
  - `视频生成任务列表查询`: 用于查询和管理在 API 上运行的任务历史。
- **视觉理解**:
  - `视觉理解（Visual Understanding）`: 默认使用 Seed 2.1 Pro，并保留 Seed 2.0 Pro/Lite/Mini 兼容旧工作流。

## 📑 节点详解

### `火山方舟 API 客户端 (Jimeng API Client)`

加载 `api_keys.json` 中的密钥配置。这是所有工作流的起点。

- **输入**: `密钥名称` (在 JSON 中配置的 customName)。
- **输出**: `客户端` 实例。

### `Jimeng 配额设置 (Jimeng Quota Settings)`

允许为当前客户端设置图像（张数）和视频（Tokens）的使用上限。

- **特性**: 当达到限额时自动停止任务并抛出提示，防止额度超支。
- **示例工作流**（点击预览图打开 JSON）：

  [![Quota Settings Workflow](./example_workflows/QuotaSettings.jpg)](./example_workflows/QuotaSettings.json)

***

### `图像生成（Seedream 4）`

支持 `doubao-seedream-4.5` 与 `doubao-seedream-4.0`。

- **输入图像**: 支持单张或多张（Batch）图像作为参考。
- **启用组图生成**: 开启后可一次性生成多张内容关联的图片。
- **提示词优化**: Seedream 4.0 可通过开关启用；Seedream 4.5 不发送此参数。

**示例工作流**（点击预览图打开 JSON）：

[![Seedream 4 Workflow](./example_workflows/Seedream%204.jpg)](./example_workflows/Seedream%204.json)

***

### `图像生成（Seedream 5）`

支持 `doubao-seedream-5.5`、`doubao-seedream-5.0-pro` 与 `doubao-seedream-5.0-lite`。

- **5.5**: 最多 10 张参考图；单一输出（不支持组图/流式）；支持 `1K` / `1.5K` / `2K` 档位、透明 RGBA 背景、图层拆分（底图 + 最多 99 图层，可返回 OCR）；默认 PNG。提示词优化使用 `standard` 模式。
- **Pro**: 最多 10 张参考图；保留种子与水印；默认开启提示词优化，使用参考图时必须开启；输出通过 URL 下载。
- **Lite**: 保留流式 Base64、组图生成、联网搜索与种子功能。
- **自定义尺寸**: 5.5 总像素为 921600–4624220；Pro 要求宽高为 16 的倍数、比例在 1:16–16:1、总像素为 921600–4194304。

**示例工作流**（点击预览图打开 JSON）：

[![Seedream 5 Workflow](./example_workflows/Seedream%205.jpg)](./example_workflows/Seedream%205.json)

***

### `视频生成（Seedance 1.0/1.5 Pro）`

支持文生视频与首/尾帧图生视频；在 1.0 能力基础上，1.5 Pro 支持**音效生成**与**智能时长**控制。

**示例工作流**（点击预览图打开 JSON）：

[![Seedance 1 Workflow](./example_workflows/Seedance%201.jpg)](./example_workflows/Seedance%201.json)

### `视频生成（Seedance 2 / 2.5）`

可覆盖文生视频、多模态参考生视频、视频编辑、视频延长与联网搜索增强。

- **Seedance 2.5**: 480p / 720p、4–30 秒；最多 30 张参考图、10 段参考视频和 10 段参考音频，并允许纯音频参考。
- **Seedance 2.5 Flash**: 480p / 720p、4–30 秒；最多 10 张参考图、5 段参考视频和 5 段参考音频，允许纯音频参考。
- **Seedance 2.0 标准版**: 480p / 720p / 1080p / 4K、4–15 秒；最多 9 张参考图、3 段参考视频和 3 段参考音频。
- **Seedance 2.0 Fast、Mini**: 480p / 720p、4–15 秒；参考数量限制与 2.0 标准版相同。
- **参考视频**: 最大 200 MB、409600–8295044 像素、24–60 FPS；可识别编码元数据时要求 H.264/H.265 视频与 AAC/MP3 音频。
- **参考媒体时长**: Seedance 2.5 单个及同类素材总时长上限为 30.2 秒；Seedance 2.0 系列为 15.2 秒。
- **请求大小**: 最终紧凑 UTF-8 JSON 请求体不得超过 64 MiB。

**示例工作流**（点击预览图打开 JSON）：

[![Seedance 2 Workflow](./example_workflows/Seedance%202.jpg)](./example_workflows/Seedance%202.json)

***

### `视频生成（MAGI-2）`

该节点从 `D:\Projects\ai-video` 的业务渠道“星朗3.5” Java 实现中提取协议，并改名为 **MAGI-2** 模型。它使用独立的 MAGI-2 API Key 与渠道 endpoint，不依赖火山方舟客户端或配额节点。

- **提交方式**: `POST {endpoint}/v2/generations`，每个任务只提交一次，不使用幂等键，也不在提交失败时自动重试；与 Java 实现一致。
- **查询方式**: `GET {endpoint}/v2/generations/{id}`，按可配置间隔轮询；查询接口异常不进入终态，下一轮继续查询。
- **鉴权**: `Authorization: Bearer <API Key>`；API Key 可带或不带 `Bearer` 前缀。
- **请求参数**: `model=magi-2`、`parts`、`duration`、`aspectRatio`、`resolution`。
  - `duration`: 4–30 秒，非法值回退为 5 秒。
  - `aspectRatio`: `21:9`、`16:9`、`4:3`、`1:1`、`3:4`、`9:16`，非法值回退为 `16:9`。
  - `resolution`: 固定 `1080p`。
  - `parts`: 第一段为文本提示词，后续按图片、视频、音频顺序追加引用素材；提示词按 `@图片1`、`@视频1`、`@音频1` 对应素材序号。
  - 界面素材输入：`参考图片`、`参考视频`、`参考音频` 均为多行文本框，每行一个 URL 或 assetId，无需额外动态组件。
- **素材处理方式**:
  - `public_url`（默认）: 直接把无需鉴权的公网 HTTP(S) 素材直链写入 `url` 字段，对应 Java `SandMediaRef.url`，**无需预先上传或加白审核**。
  - `asset_id`: 写入 `assetId` 字段，对应 Java `SandMediaRef.assetId`；该模式要求素材**已在渠道侧预先上传/加白审核通过**，并提供数字素材 ID。Java 项目仅在 DTO 中预留 `assetId`，未实现 `/v1/assets` 上传接口，本插件同样不代做上传/审核，只接收已获得的 ID。
- **响应处理**: `queued/pending` 映射为排队，`processing/running` 映射为处理中，`failed/canceled` 为失败，`succeeded` 为成功；成功但尚无 `videoUrl` 时继续轮询。
- **输出**: 首个视频、最后一帧（提取失败时为白图）和包含任务 ID、视频 URL、URL 有效期的 JSON。

### `MAGI-2 API 客户端`

- **输入**: `api_key`（MAGI-2 渠道 API Key）和 `base_url`（渠道 endpoint）。`base_url` 默认值为 `https://api.sand.ai`，可按需修改。
- **输出**: 供 `视频生成（MAGI-2）` 使用的客户端实例。
- **独立性**: MAGI-2 不读取 `api_keys.json`，也不依赖火山方舟 SDK；即使火山节点不可用，MAGI-2 节点仍会注册到 ComfyUI。

**界面用法**：在 ComfyUI 中添加 `MAGI-2 API Client` → 填入 API Key（endpoint 保持默认或按需修改）→ 添加 `视频生成（MAGI-2）` → 将客户端连接到 `client` 输入 → 填写提示词和素材 → 运行。无需额外 API 客户端、配置文件或动态素材组件。

***

### `视频生成任务列表查询`

支持按状态、模型版本或任务 ID 过滤查询任务历史。

***

### `视觉理解（Seed 2.1 / 2.0）`

默认使用 `doubao-seed-2-1-pro`，并保留 `doubao-seed-2.0` 系列模型。

- **多模态输入**: 支持上传图片或视频进行理解和问答。
- **多轮对话**: 支持开启多轮对话模式，保持上下文。
- **深度思考**: 支持开启深度思考模式，提升复杂问题的推理能力。

**示例工作流**（点击预览图打开 JSON）：

[![Visual Understanding Workflow](./example_workflows/VisualUnderstanding.jpg)](./example_workflows/VisualUnderstanding.json)

## 📓 示例工作流

您可以在 `example_workflows` 目录中找到所有节点的示例工作流。

## 🧩 ComfyUI 兼容性

| ComfyUI / 前端 | Classic Canvas | Nodes 2.0 | 说明 |
|---|---:|---:|---|
| 0.25.1 / 1.45.15 | 支持 | 支持 | 最低支持版本；包含旧平铺工作流迁移 |
| 0.28.0 / 1.45.21 | 支持 | 支持 | 官方稳定分支目标 |
| 前端 1.46.3+ | 支持 | 支持 | 已覆盖 DynamicCombo 保存与恢复路径 |
