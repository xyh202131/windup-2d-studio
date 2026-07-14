# Windup 2D Studio

面向 2D 游戏与角色展示的高清人物资产工作台。它把人物母版、动作生成、逐帧审核、局部重生、正式入库与 ZIP 导出放在同一条可追溯链路中。

## 核心规格

- 1024×1024 三视角人物母版：侧视、正面、3/4。
- 512×512 透明动作帧，支持 8 / 12 / 16 帧和固定 8 FPS 预览。
- 待机、走、跑、跳、攻击、施法预设，以及自由描述动作。
- 四个关键锚点先行，再用母版、锚点与相邻帧补齐动作序列。
- 每一帧都有独立候选版本；全部审核通过后才能正式入库。
- 自动检查画布、Alpha、空帧、重复帧、主体位置、脚底线和循环接缝。
- 低于目标分辨率的模型结果会失败，不允许向上插值冒充高清。

## 一键启动（Windows）

要求：

- Python 3.11+
- Node.js 22 LTS
- npm

双击项目根目录的 `start.bat`，或在 CMD 中执行 `start.bat`。启动器全程由 `cmd.exe` 执行，不依赖 PowerShell。首次运行会创建 `.venv`、安装依赖、启动前后端并打开浏览器。如果服务已经启动，再次执行会直接复用，不会重装正在使用的前端依赖。

```cmd
start.bat
```

如果不希望自动打开浏览器：

```cmd
start.bat --no-browser
```

- 工作台：<http://127.0.0.1:5175>
- API：<http://127.0.0.1:8002>
- OpenAPI：<http://127.0.0.1:8002/docs>

API Key 默认由页面的“生成服务”对话框手动输入，`start.bat` 不会读取、写入或要求 Key。默认图像模型为 `gemini-3.1-flash-image-preview`，并保留 `gemini-2.5-flash-image` 作为兼容备选；本地功能演示可输入 `demo`，模型选择 `windup-demo-image`。真实 Key 只存在后端进程内存，不写入 SQLite、浏览器存储、日志或 Git；后端环境变量仅作可选兼容方式。

如果确实要用环境变量，可在当前 CMD 会话中先设置 `QNAIGC_KEY`：

```cmd
set "QNAIGC_KEY=你的Key"
start.bat
```

## 手动开发

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8002
```

另开一个终端：

```powershell
cd frontend
npm ci
npm run dev
```

## 架构

```text
frontend/                 React + TypeScript 数字灯箱工作台
backend/app/api.py        FastAPI HTTP 适配
backend/app/service.py    生成、审核、发布与导出用例
backend/app/provider.py   七牛 OpenAI-compatible 传输边界
backend/app/database.py   SQLite 元数据仓库
backend/app/processing.py 高清抠图、归一化与连续性质检
contracts/                唯一产品契约
runtime/                  本机任务与资产（Git 忽略）
tools/                    契约生成与验证入口
```

任务主路径：

```text
queued → planning → generating → processing → awaiting_review → promoting → approved
                                    ↘ failed / interrupted / cancelled
```

候选资产永远不会直接覆盖正式资产。发布先写临时目录，已有资产移动到 `runtime/backups/` 后再原子切换。

## 配置

环境变量示例见 `.env.example`：

- `QNAIGC_BASE`：API 根地址。
- `QNAIGC_IMAGE_MODEL`：默认图像模型。
- `QNAIGC_KEY`：可选的进程级 Key；不要写入 `.env` 后提交。
- `WINDUP_2D_MAX_WORKERS`：跨任务最大工作线程数，默认 2。
- `WINDUP_2D_ALLOWED_ORIGINS`：允许携带会话 Cookie 的前端 Origin。

## 验证

首次安装依赖后执行：

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify.ps1
```

验证包括契约漂移、pytest、ESLint、TypeScript、Vitest、生产构建和 `git diff --check`。视觉验收为人工浏览器检查，不使用截图自动化。

## 安全与数据

- `runtime/`、`.env`、参考图、生成结果、导出包和虚拟环境均被 Git 忽略。
- 上传仅接受 PNG/JPEG/WebP，最大 15MB，边长必须在 256–8192px。
- 本地单用户版本不包含账号系统或云端对象存储，请勿直接暴露到公网。
- 自动质检不能可靠判断解剖、变脸或动作语义，正式入库前必须人工逐帧确认。
