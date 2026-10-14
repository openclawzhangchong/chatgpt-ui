# 更新日志（Changelog）

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，
版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- 语音输入真机验证（需麦克风环境）
- 设置弹窗其余 Tab 真实化
- 设置快照上云（Worker/D1，对齐 dog2027 数据模型已预留）

## [3.4.2] - 2026-10-14

**版本号单一数据源**：修复显示版本漂移（后台系统页停在 v3.4.0、前台「关于」页停在 v3.0.0）。

### Fixed
- 前台「关于」页与后台「系统」页的版本号改为动态拉取 `/api/version`（`/api/tools` 同步附带 `version` 字段），**唯一维护点 = desktop/server.py 的 `APP_VERSION` 常量**——以后发版只改这一处，杜绝显示版本与实际发布版本脱节

## [3.4.1] - 2026-10-14

**P1 补全**：后台默认音色（音色分组/试听/内置徽章/Key 打码已于 3.4.0 交付）。

### Added
- **后台默认音色**（v3.4.1）：`/admin` 新增「朗读设置」区——分组音色下拉（322 个）+ 试听 + 保存，写 `%APPDATA%/ChatGPT-UI/settings.json`；`/api/tts` 音色优先级改为 **请求显式指定 > 后台默认 > config.json 兜底**（用户在设置面板手动选过的始终最优先）
- **settings 存储层**（models.py）：第三个本地「数据库文件」settings.json，种子自随包 config.json 的 ttsVoice（老配置平滑迁移）；与 models.json/admin.json 同款原子写入，将来上 Worker/D1 时同批迁移

## [3.4.0] - 2026-10-14

**管理后台 + 模型池**：从「单模型写死」进化为「后台可管理的模型池」，新增 /admin 管理页与管理员登录体系，模型菜单真实化；音色从 4 个硬编码升级为微软全量 322 个分组下拉。

### Added
- **管理后台**（`/admin`，ui/admin.html + admin.js）：登录闸门（管理员用户名 + 口令）→ 模型池管理（新增/编辑/删除/启用停用/设为默认/连通测试/Key 打码）+ 修改口令 + 系统信息。视觉对齐前台，支持深浅色
- **管理员鉴权体系**（models.py）：口令 PBKDF2-SHA256 20 万次迭代哈希存储（**只存哈希不存明文**，dog2027 v1.19.0 教训）；token HMAC-SHA256 签名、TTL 7 天；`/api/admin/*` 统一守卫，401/403 行为一致
- **模型池两层存储**：随包 `models.default.json`（内置 Qwen 条目，可停用不可删）+ `%APPDATA%/ChatGPT-UI/models.json` 运行时覆写层（后台增删改全写这里，加模型不用重打包）；数据模型对齐 dog2027 providers 表，将来上 Worker/D1 无缝迁移
- **前台管理员入口**（admin-gate.js）：右上角头像菜单按登录态显隐「管理员登录 / 管理后台」——未登录时入口零暴露；登录浮层 + token 与 /admin 页同源共享
- **模型菜单真实化**：顶栏模型下拉改拉 `/api/models` 渲染真实池，选择持久化（localStorage RC_MODEL_ID），请求带条目 id；服务端不识别/停用 → 静默回落默认（用户看到的是悄悄换回默认，不是发不出去）
- **音色全量化**：`/api/tts/voices` 改拉 `edge_tts.list_voices()` 微软全量 322 个，按「中文女声/中文男声/方言/多语言/其他」分组（小名人名映射：Xiaoxiao→晓晓），设置面板升级为分组下拉 +「▶ 试听」按钮（1.5s 节流 + 自动播放解锁，dog2027 同款纪律）；断网回落内置 4 个

### Changed
- server.py 聊天循环：上游配置从全局单 Provider 改为按请求 model 字段走模型池裁决；config.json 的 baseUrl/apiKey/model 降级为随包默认种子，老配置不瞎
- build_desktop.py：FRONTEND_FILES 增 admin.html/admin.js/admin-gate.js；打包数据增 models.default.json + admin.default.json；hidden-import 增 models

### Security
- 管理员口令哈希 20 万次 PBKDF2；默认口令（18596950000）只以哈希形式存在于随包 admin.default.json，首次后台改口令后换随机盐
- 模型 Key 只写不读：所有列表接口一律打码（sk-…末四位），编辑时留空 = 不改

## [3.3.0] - 2026-10-14

**HANDOFF 候选清零轮**：产物预览卡片 + PDF/媒体工具 + 语音闭环 + LLM 摘要压缩 + EXE 图标，工具总数 37 → **41**。

### Added
- **产物预览卡片**：AI 生成 Word/Excel/PPT/PDF/二维码后，工具芯片内直接显示文件名 +「📂 打开」按钮（点击经 /api/tool open_file 用系统默认程序打开，实测 WPS 唤起成功）
- **本地 MCP server 池扩充**：`pdf`（pdf_read 按页提取 / pdf_info 元信息目录）+ `media`（qr_generate 二维码 / image_info 图片信息 EXIF），本地 MCP 工具 14 → 18
- **语音闭环**（voice.js）：① 设置面板「语音」Tab 音色 chips 真实化（Edge TTS 四音色，选择持久化）② mic 按钮接 Web Speech API 中文语音识别——聆听覆盖层实时显示识别文本，说完自动填入并发送，AI 回复完成后自动朗读
- **LLM 摘要式上下文压缩**（compress.js RC_compressAsync）：触发折叠时把被裁历史发给模型生成 200 字摘要替换占位提示，被裁信息以摘要形式保留
- **EXE 自定义图标**（绿色 A 标，与托盘同款，多尺寸 ico）
- 会话记录 `owner` 字段落地（多用户隔离预留）

### Fixed
- 工具循环轮次上限 6 → 10（复杂多步任务不再被掐断）
- server 配置诊断日志（config 来源 + builtinMcp/mcpServers 数量写入 %TEMP%/ChatGPT-UI.log，windowed 下排查配置问题的唯一入口）
- 排查并清除僵尸进程占用端口导致新 EXE 工具加载异常的问题（实测 41 工具全装载）

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

[Unreleased]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v3.3.0...HEAD
[3.3.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v3.2.0...v3.3.0
[3.2.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v3.1.0...v3.2.0
[3.1.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/releases/tag/v1.0.0
