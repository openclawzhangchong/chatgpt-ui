# 更新日志（Changelog）

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，
版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- LLM 摘要式上下文压缩（当前为确定性折叠版）
- 设置弹窗语音 Tab 真实化（音色选择）

## [3.2.0] - 2026-10-14

**本地自建 MCP Server 池**：从「接别人的 MCP」升级为「自己起自己的」，新增 4 个本地 server 14 个工具，工具总数 23 → **37**。

### Added
- **本地 MCP server 池**（`desktop/mcp_servers/`，进程内加载，零子进程零打包风险），config.json `builtinMcp` 一行开关：
  - **web**：`fetch_page_markdown`（网页→Markdown 智能正文提取，微信公众号/知乎/CSDN/掘金/简书/豆瓣/头条/B站专用规则+通用启发式，保留标题层级/列表/链接/图片/代码块）、`web_search`（Bing 主 + DuckDuckGo 备）、`extract_links`
  - **files**：`search_files`（文件名/内容递归搜索）、`file_hash`（MD5/SHA1/SHA256）、`tree_directory`
  - **office**：`read_docx` / `read_xlsx` / `read_pptx`（与 create_* 形成读写闭环）
  - **dev**：`json_format` / `base64_codec` / `url_codec` / `regex_test` / `timestamp_convert`
- 公众号文章抓取实测通过（用户指定测试用例）：AI 自主调用 fetch_page_markdown 提取正文并准确概括

### Fixed
- web_search 数据源：DuckDuckGo 境内不通 → Bing 主源（实测解析 10 条结果）
- PyInstaller 打包：`collect-submodules` 不带父包导致动态 import 的 mcp_servers 整个丢失 → 显式 hidden-import 父包+子模块（已登记踩坑）
- 本地 MCP 池装载增加防御：单个 server 失败不影响其他工具

## [3.1.0] - 2026-10-14

**MCP 工具扩充 + 系统托盘 + 上下文压缩**：工具总数 6 → 23，新增托盘常驻与上下文自动折叠。

### Added
- **远程 MCP 客户端**（mcp_client.py）：通用 JSON-RPC 2.0 客户端，支持 streamable HTTP / SSE / stdio 三种传输；按标准 `mcpServers` 配置接入，工具自动合并进注册表（工具名前缀 `ms_<服务器>_<工具>`）
- **实测接通 2 个公开 MCP 服务器**：DeepWiki（GitHub 仓库文档问答，3 工具）+ Microsoft Learn（官方文档搜索/代码示例，3 工具）
- **ModelScope 魔搭 MCP 适配位**：config.json `mcpServers` 已留位——在魔搭广场复制个人 SSE URL（24h 有效）填入即生效，工具箱面板显示连接状态
- **11 个新内建工具**：read_text_file / write_text_file / list_directory / clipboard_read / clipboard_write / take_screenshot / open_url / system_info / get_weather / current_time / calculate（工具总数达 23）
- **Windows 系统托盘**：关闭窗口不退出、退到托盘；托盘菜单「显示主窗口 / 退出程序」；启动气泡提示
- **上下文压缩**（compress.js）：`window.RC_compress` 钩子落地——超 8 万字符预算时先折叠较早消息中的图片、再从最旧丢弃，始终保留 system 与最近 6 条

### Fixed
- get_weather：wttr.in 在境内网络返回落地页 HTML → Open-Meteo 兜底 + 常见中国城市拼音映射
- 请求体 JSON 解析兼容非 UTF-8 客户端（GBK 兜底）

### Security
- 新增工具路径守卫：禁止访问 Windows/Program Files 系统目录；open_file 白名单不变

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

[Unreleased]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v3.2.0...HEAD
[3.2.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v3.1.0...v3.2.0
[3.1.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/releases/tag/v1.0.0
