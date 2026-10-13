# ChatGPT UI —— ChatGPT 完美复刻（已接入真实大模型）

> 100% 还原 ChatGPT 官方界面观感的复刻版。v2.0 起已接入 OpenAI 兼容大模型 API，**真实对话、流式输出、图片理解**，零构建、开箱即用。

![Version](https://img.shields.io/badge/version-v2.0.0-19c37d) ![License](https://img.shields.io/badge/license-MIT-blue) ![Tech](https://img.shields.io/badge/stack-HTML%20%2B%20CSS%20%2B%20JS-orange) ![Deps](https://img.shields.io/badge/dependencies-0-success)

## ✨ 项目简介

这是一个对 ChatGPT 官方网页界面进行**像素级复刻**的前端项目，并已接入 OpenAI 兼容大模型 API 让它**真正能对话**。整个项目不依赖任何框架、任何 CDN、任何外部资源，本地起个静态服务即可使用。

适合用作：前端练手参考、产品原型演示、自建轻量 AI 对话入口、二次开发的界面底座。

## 🎯 特性

**真实对话（v2.0 新增）**

- 🗨️ **真实大模型对话**：OpenAI 兼容接口直连，SSE 流式逐字渲染
- 💭 **思考过程可视化**：推理模型的思维链实时展示，正文开始后自动折叠、可展开回看
- 🖼️ **图片理解（Vision）**：输入框添加图片，自动压缩后随消息发送，支持最多 4 张
- 🔄 **多轮上下文 / 重新生成 / 停止生成**（发送键变停止键，或按 Esc）
- 🧠 **GPT 角色系统提示词**：侧边栏 GPT 列表项自动注入角色 prompt
- 🈶 **中文错误提示**：鉴权失败 / 限流 / 网络异常等场景均有可读反馈
- ⌨️ **输入法友好**：中文输入法组合中按回车不再误发送

**界面复刻（v1.0）**

- **像素级复刻**：侧边栏、对话区、输入框、气泡样式均按官方视觉规格还原（CSS 变量驱动，色值对齐官方 Dark/Light 主题）
- **深色 / 浅色双主题**：一键切换，全站 CSS 变量联动
- **模型选择器**：真实接入模型为主项，官方系列保留为「演示」项
- **语音模式 / 设置中心**：覆盖层与弹窗完整还原（语音暂为展示，见 HANDOFF）
- **移动端适配**：手机竖屏 / PC 横屏双布局，侧边栏抽屉式滑出
- **零依赖架构**：HTML + CSS + JS 全部本地，0 构建、0 外部请求

## 🚀 快速开始

```bash
# 1. 配置 API（OpenAI 兼容接口）
cp config.example.js config.js
#    编辑 config.js，填入你的 baseUrl / apiKey / model

# 2. 启动本地服务
python -m http.server 8080
#    浏览器访问 http://localhost:8080 即可开始对话
```

> ⚠️ **安全提示**：`config.js` 含真实 API Key，已加入 `.gitignore`，**请勿提交到仓库或公开分发**。浏览器端直连意味着 Key 对使用者可见，适合个人自用；公开部署前请在服务端撤换 Key 或改走代理。
>
> 💡 不配置 `config.js` 也能打开页面：界面完整可用，发送时会提示配置缺失。

## 📂 项目结构

```
chatgpt-ui/
├── index.html          # 界面主体（HTML + CSS + 原型 JS 单文件）
├── realchat.js         # v2.0 大模型接入模块（零侵入覆盖假链路）
├── config.example.js   # API 配置模板（入库）
├── config.js           # 真实配置（gitignore，本地自建）
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
| v2.x | API 配置改从 Worker / 数据库动态获取 | 📋 规划中 |
| v2.x | 历史会话持久化（localStorage / IndexedDB） | 📋 规划中 |
| v3.0 | Python 打包为 Windows 桌面客户端（PyWebview） | 📋 规划中 |

## 🤝 贡献

欢迎提 Issue / PR，尤其欢迎官方界面细节的还原度修正。

## 📄 License

[MIT](./LICENSE) © 2026
