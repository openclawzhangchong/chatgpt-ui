# ChatGPT UI —— ChatGPT 完美复刻（真实对话 · Python 桌面版）

> 100% 还原 ChatGPT 官方界面观感，接入 OpenAI 兼容大模型 API **真实对话**；v3.5 起拥有 **41 个工具**（17 内建 + 18 本地自建 MCP + 6 远程 MCP）+ **八分区管理后台**（模型池/人设 GPT/首页卡片/对话与朗读/外观品牌/MCP 工具/系统/账号，MCP 保存热重载即时生效），对话中 AI 可抓网页（含公众号）、生成/读取 Word/Excel/PPT/PDF、二维码、操作桌面文件、查天气、搜资料，支持语音听说闭环与微软全量音色选择。

![Version](https://img.shields.io/badge/version-v3.5.0-19c37d) ![License](https://img.shields.io/badge/license-MIT-blue) ![Tech](https://img.shields.io/badge/stack-HTML%20%2B%20JS%20%2B%20Python%20%E5%A3%B3-orange) ![MCP](https://img.shields.io/badge/MCP%20tools-41-blueviolet) ![Frontend%20deps](https://img.shields.io/badge/frontend%20deps-0-success)

## ✨ 项目简介

这是一个对 ChatGPT 官方网页界面进行**像素级复刻**的前端项目，并已接入 OpenAI 兼容大模型 API 让它**真正能对话**。整个项目不依赖任何框架、任何 CDN、任何外部资源，本地起个静态服务即可使用。

适合用作：前端练手参考、产品原型演示、自建轻量 AI 对话入口、二次开发的界面底座。

## 🎯 特性

**真实对话（v2.0 新增）**

- 🗨️ **真实大模型对话**：OpenAI 兼容接口，SSE 流式逐字渲染
- 💭 **思考过程可视化**：推理模型的思维链实时展示，正文开始后自动折叠、可展开回看
- 🖼️ **图片理解（Vision）**：输入框添加图片，自动压缩后随消息发送，支持最多 4 张
- 🔄 **多轮上下文 / 重新生成 / 停止生成**（发送键变停止键，或按 Esc）
- 🧠 **GPT 角色系统提示词**：侧边栏 GPT 列表项自动注入角色 prompt
- 🈶 **中文错误提示** + ⌨️ **输入法友好**（中文组合中按回车不误发送）

**桌面版（v3.0 新增）**

- 🖥️ **单文件 EXE**：PyInstaller 打包，双击即用，Python 壳（pywebview + 本地服务）
- 🖥️ **系统托盘**：关闭窗口不退出、退到托盘常驻；托盘菜单「显示主窗口 / 退出程序」
- 🧰 **41 个工具**（17 内建 + 18 本地 MCP + 6 远程 MCP），对话中 AI 自动调用：
  - 办公读写闭环：`create_word`/`create_excel`/`create_ppt` 生成 + `read_docx`/`read_xlsx`/`read_pptx` 读取（落盘桌面 `chatgpt-ui-exports/`，气泡内**一键打开**）
  - PDF 与媒体：`pdf_read`/`pdf_info`、`qr_generate`（二维码）、`image_info`
  - 网页抓取：`fetch_page_markdown`（**微信公众号/知乎/CSDN/掘金/简书/豆瓣/头条/B站**专用规则 → Markdown，实测公众号文章提取）、`web_search`（Bing）、`extract_links`
  - 文件系统：`search_files`（递归搜名/内容）、`file_hash`、`tree_directory`、`list_desktop_files`、`open_file`
  - 系统与生活：`system_info`/`current_time`/`get_weather`/`calculate`/`clipboard_read`/`clipboard_write`/`take_screenshot`/`open_url`
  - 开发辅助：`json_format`/`base64_codec`/`url_codec`/`regex_test`/`timestamp_convert`
  - **远程 MCP**（可选）：DeepWiki + Microsoft Learn；工具调用过程在气泡内可视化
- 💾 **会话持久化**：IndexedDB 存储，刷新/重启不丢聊天记录
- 🗜️ **上下文压缩**：超 8 万字符自动折叠较早图片与历史（LLM 生成摘要保留关键信息），始终保留系统提示与最近对话
- 🔊 **语音听说闭环**：消息 🔊 朗读（Edge TTS + SAPI 离线兜底，四音色可选）；mic 语音输入（Web Speech API 中文识别 → 自动发送 → 回复自动播报）
- 🧩 **菜单换血**：工具箱（工具清单+MCP连接状态）/ 导出中心（会话导出 Word、Markdown）/ 关于本应用

**接入你自己的 MCP 服务器**（含魔搭 ModelScope）：编辑 EXE 旁的 `config.json`，在 `mcpServers` 数组填 URL 即可（支持 streamable HTTP / SSE / stdio 三种传输，与 Cherry Studio / Claude Desktop 配置同构）：

```json
"mcpServers": [
  {"name": "modelscope-fetch", "transport": "sse", "url": "https://mcp.api-inference.modelscope.cn/sse/你的专属ID"}
]
```

> 魔搭 MCP 广场的托管 URL 是**个人专属且 24 小时有效**：登录 modelscope.cn → MCP 广场 → 服务详情页复制 SSE URL，粘贴到 config.json，重启 EXE 生效；过期后重新复制。工具箱面板可查看连接状态。

**界面复刻（v1.0）**

- **像素级复刻**：侧边栏、对话区、输入框、气泡样式均按官方视觉规格还原
- **深色 / 浅色双主题**、**移动端适配**、**零前端依赖架构**

## 🚀 快速开始

### 桌面版（推荐）

```
1. 双击桌面上的 ChatGPT-UI.exe
2. 开始对话。想生成文件？直接说：「用工具在桌面生成一个 Word，内容是……」
```

> EXE 旁的 `config.json` 可随时改 API 地址 / Key / 模型，无需重新打包。

### 网页版（开发模式）

```bash
# 1. 配置 API（OpenAI 兼容接口）
cp config.example.js config.js
#    编辑 config.js，填入你的 baseUrl / apiKey / model

# 2. 启动本地服务
python -m http.server 8080
#    浏览器访问 http://localhost:8080 即可开始对话
```

### 桌面版打包（从源码）

```bash
cd desktop
python build_desktop.py
# 自动：同步前端 → PyInstaller 单文件 → 拷贝 EXE 到桌面
```

> ⚠️ **安全提示**：网页版 `config.js` 含真实 API Key（已 gitignore，勿提交/公开分发）；桌面版 Key 在 EXE 旁 `config.json`。安全加固（服务端代理等）规划在最终版统一处理。

## 📂 项目结构

```
chatgpt-ui/
├── index.html          # 界面主体（HTML + CSS + 原型 JS 单文件，UI 框架不改动）
├── realchat.js         # v2.0 大模型接入模块（零侵入覆盖假链路）
├── storage.js          # v3.0 IndexedDB 会话持久化
├── tts.js              # v3.0 朗读（Edge TTS / SAPI，走桌面端本地服务）
├── toolbox.js          # v3.0 菜单换血（工具箱 / 导出中心 / 关于）
├── compress.js         # v3.1 上下文压缩（确定性折叠 + v3.3 LLM 摘要）
├── voice.js            # v3.3 语音闭环（音色分组下拉试听 + Web Speech API 输入）
├── admin-gate.js       # v3.4 前台管理员入口（登录浮层 + 后台链接）
├── dynamic.js          # v3.5 后台配置的前台应用（品牌/人设/首页卡片下发）
├── admin.html          # v3.4 管理后台页（/admin，模型池管理）
├── admin.js            # v3.4 管理后台逻辑
├── config.example.js   # 网页版 API 配置模板（入库）
├── config.js           # 网页版真实配置（gitignore，本地自建）
├── desktop/            # v3.0 Python 桌面版
│   ├── main.py         #   入口：pywebview 窗口 + 托盘 + uvicorn 本地服务
│   ├── server.py       #   OpenAI 兼容 SSE 代理 + 工具循环 + TTS + 导出 + 管理后台 API
│   ├── models.py       #   v3.4 模型池 + 管理员鉴权（两层存储 + PBKDF2 + token）
│   ├── models.default.json  # v3.4 随包默认模型池（内置 Qwen，只读种子）
│   ├── admin.default.json   # v3.4 随包默认管理员凭据（只存 PBKDF2 哈希）
│   ├── tools.py        #   本地工具注册表 + 扩展装载入口
│   ├── tools_extra.py  #   v3.1 新增 11 个内建工具
│   ├── mcp_client.py   #   通用 MCP 客户端（HTTP / SSE / stdio 三传输）
│   ├── mcp_servers/    #   v3.2 本地自建 MCP server 池（web/files/office/dev/pdf/media）
│   ├── build_desktop.py#   一键打包流水线（同步前端 → PyInstaller → 拷桌面）
│   └── config.example.json
├── HANDOFF.md          # 交接清单：已完成基线 / 待办 / 红线
├── README.md
├── CHANGELOG.md        # 版本记录
├── LICENSE
└── .gitignore
```

## 🗺️ 升级路线图（Roadmap）

| 阶段 | 内容 | 状态 |
|------|------|------|
| v1.0 | 完美复刻静态版 | ✅ 已完成 |
| v2.0 | 接入大模型 API，真实对话 + 流式 + 图片理解 | ✅ 已完成 |
| v3.0 | Python 桌面版 EXE + 本地 MCP 工具 + IndexedDB + Edge TTS | ✅ 已完成 |
| v3.1 | 远程 MCP 客户端（DeepWiki/MS Learn 实测接通）+ 11 个新工具 + 系统托盘 + 上下文压缩 | ✅ 已完成 |
| v3.2 | 本地自建 MCP server 池（web/files/office/dev 四服务器 14 工具）+ 公众号抓取实测 | ✅ 已完成 |
| v3.3 | 产物预览卡片 + PDF/媒体工具 + 语音听说闭环 + LLM 摘要压缩 + EXE 图标（41 工具） | ✅ 已完成 |
| v3.x | 上下文压缩（RC_compress 钩子已预留）/ 多会话隔离 | 📋 规划中 |
| v3.x | API 配置改从 Worker / 数据库动态获取 | 📋 规划中 |
| v4.0 | 安全加固（服务端代理 Key、对外部署） | 📋 规划中 |

## 🤝 贡献

欢迎提 Issue / PR，尤其欢迎官方界面细节的还原度修正。

## 📄 License

[MIT](./LICENSE) © 2026
