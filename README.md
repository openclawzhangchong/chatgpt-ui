# ChatGPT UI —— ChatGPT 完美复刻（真实对话 · Python 桌面版）

> 100% 还原 ChatGPT 官方界面观感，接入 OpenAI 兼容大模型 API **真实对话**；v3.0 起 Python 打包为 Windows 桌面 EXE，对话中 AI 可调用**本地 MCP 工具**直接生成 Word / Excel / PPT、操作桌面文件、抓取网页。

![Version](https://img.shields.io/badge/version-v3.0.0-19c37d) ![License](https://img.shields.io/badge/license-MIT-blue) ![Tech](https://img.shields.io/badge/stack-HTML%20%2B%20JS%20%2B%20Python%20%E5%A3%B3-orange) ![Deps](https://img.shields.io/badge/frontend%20deps-0-success)

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
- 🧰 **本地 MCP 工具**：对话中 AI 自动调用——生成 Word / Excel / PPT 到桌面、查看并打开桌面文件、抓取网页；工具调用过程在气泡内可视化
- 💾 **会话持久化**：IndexedDB 存储，刷新/重启不丢聊天记录
- 🔊 **朗读**：Edge TTS（联网）+ Windows SAPI 离线兜底
- 🧩 **菜单换血**：工具箱（查看本机工具）/ 导出中心（会话导出 Word、Markdown）/ 关于本应用

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
├── config.example.js   # 网页版 API 配置模板（入库）
├── config.js           # 网页版真实配置（gitignore，本地自建）
├── desktop/            # v3.0 Python 桌面版
│   ├── main.py         #   入口：pywebview 窗口 + uvicorn 本地服务
│   ├── server.py       #   OpenAI 兼容 SSE 代理 + MCP 工具循环 + TTS + 导出
│   ├── tools.py        #   本地工具注册表（Word/Excel/PPT/桌面文件/网页抓取）
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
| v3.x | 上下文压缩（RC_compress 钩子已预留）/ 多会话隔离 | 📋 规划中 |
| v3.x | API 配置改从 Worker / 数据库动态获取 | 📋 规划中 |
| v4.0 | 安全加固（服务端代理 Key、对外部署） | 📋 规划中 |

## 🤝 贡献

欢迎提 Issue / PR，尤其欢迎官方界面细节的还原度修正。

## 📄 License

[MIT](./LICENSE) © 2026
