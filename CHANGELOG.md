# 更新日志（Changelog）

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，
版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- 上下文压缩算法实现（RC_compress 钩子已预留）
- 多会话/多人隔离（IndexedDB schema 已预留 owner 字段）
- 设置弹窗语音 Tab 真实化（音色选择）

## [3.0.0] - 2026-10-13

**Python 桌面版**：pywebview 壳 + 本地 MCP 风格工具 + 离线语音 + 会话持久化，交付单文件 EXE。

### Added
- **桌面版**：Python 壳（pywebview + uvicorn/FastAPI），`build_desktop.py` 一键 PyInstaller 单文件打包，双击 EXE 即用
- **本地 MCP 工具体系**：`tools.py` 工具注册表（OpenAI JSON Schema 兼容 MCP 描述符），对话中 AI 自动调用：
  - `create_word` / `create_excel` / `create_ppt`：对话直接产出 Office 文档，落盘桌面 `chatgpt-ui-exports/`
  - `list_desktop_files` / `open_file`：本机文件查看与打开（白名单限制桌面与导出目录）
  - `fetch_webpage`：网页抓取
  - 工具过程以 `rc_tool` SSE 事件透传，AI 气泡内渲染「🔧 工具调用 ✓」芯片
- **会话持久化**：IndexedDB（sessions 按会话记录级存储 + meta 状态仓），刷新/重启不丢历史；预留压缩/多人字段
- **朗读**：Edge TTS（联网）+ Windows SAPI 离线兜底双通道
- **菜单换血**（UI 框架零改动）：Sora→工具箱（工具清单）、资料库→导出中心（会话导出 Word/Markdown）、升级方案→关于本应用、创建公开链接→复制对话全文、退出登录→清空本地数据
- **导出中心**：当前会话一键导出 Word / Markdown
- **架构预留**：`RC_compress` 上下文压缩钩子（realchat.js）、标准 MCP 端点扩展位（tools.py 注册表同构）

### Fixed
- 上游请求补浏览器 UA（默认 Python UA 被 Cloudflare 403 拦截）
- 静态 catch-all 路由后置，修复 /api/* 被劫持
- 上游连接超时收紧（600s→100s）+ 3 次重试，快速暴露线路抖动

### Security
- 桌面版 API Key 由 Python 侧持有（EXE 旁 `config.json`），前端不再持有真实 key

## [2.0.0] - 2026-10-13

静态复刻壳 → **真实可对话**。接入 OpenAI 兼容接口，直连（不经过代理）。

### Added
- 真实对话：`POST /v1/chat/completions`，SSE 流式逐字渲染（`realchat.js` 零侵入接入）
- 思考过程展示：推理模型 `reasoning_content` 实时流式显示，正文开始后自动折叠、可点击展开
- 图片上传（Vision）：输入框附件按钮 → canvas 压缩（≤1024px / JPEG 85%）→ base64 → OpenAI content 数组格式，最多 4 张，气泡内缩略图预览、可移除
- 多轮上下文：完整会话历史随请求发送；GPT 列表项接入角色 system prompt
- 重新生成：真实重新请求（移除末尾 AI 回复后重发）
- 停止生成：流式期间发送按钮变红色停止键，或按 Esc
- 错误中文映射：401/403/404/429/5xx/网络失败分别给出可读提示
- 配置模块：`config.js`（本地真实 Key，已 gitignore）+ `config.example.js`（入库模板），含 `TODO(Worker)` 标记——将来配置改为从 Worker/数据库动态获取

### Fixed
- 中文输入法（IME）输入中按回车误发送消息
- 附件按钮原为演示 toast，现接入真实图片选择与上传
- 模型选择器真实化：主项为实际接入的 Qwen3.6-35B-A3B-Vision，原 ChatGPT 系列项标注「演示」

### Security
- 真实 API Key 不入库（`config.js` 加入 `.gitignore`），公开仓库仅含模板文件

## [1.0.0] - 2026-10-13

首个公开版本。ChatGPT 官方界面的完美复刻静态版。

### Added
- 像素级复刻 ChatGPT 官方界面：侧边栏、对话区、输入框、消息气泡
- 深色 / 浅色双主题一键切换（CSS 变量驱动，全站联动）
- 模型选择器：下拉菜单 + NEW 徽标 + 模型简介面板
- 侧边栏 GPT 子菜单（数据分析 / 写作助手 / 课件排版）
- 全屏语音模式覆盖层与动效
- 设置中心二级弹窗（通用 / 语音 / 数据控制 Tab），移动端自适应整页化
- 移动端竖屏 / PC 横屏双布局，侧边栏抽屉式滑出
- 单文件架构：HTML + CSS + JS 全内联，零依赖、零构建、零外部请求

[Unreleased]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/releases/tag/v1.0.0
