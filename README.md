# ChatGPT UI —— ChatGPT 完美复刻（静态版）

> 100% 还原 ChatGPT 官方界面观感的纯静态复刻版。零依赖、零构建、单文件即开即用。

![Version](https://img.shields.io/badge/version-v1.0.0-19c37d) ![License](https://img.shields.io/badge/license-MIT-blue) ![Tech](https://img.shields.io/badge/stack-HTML%20%2B%20CSS%20%2B%20JS-orange) ![Deps](https://img.shields.io/badge/dependencies-0-success)

## ✨ 项目简介

这是一个对 ChatGPT 官方网页界面进行**像素级复刻**的静态前端项目。整个项目只有一个 `index.html`，不依赖任何框架、任何 CDN、任何外部资源，双击即可在浏览器中打开，界面观感与官方版高度一致。

适合用作：前端练手参考、产品原型演示、二次开发的界面底座。

## 🎯 特性

- **像素级复刻**：侧边栏、对话区、输入框、气泡样式均按官方视觉规格还原（CSS 变量驱动，色值对齐官方 Dark/Light 主题）
- **深色 / 浅色双主题**：一键切换，全站 CSS 变量联动
- **模型选择器**：ChatGPT 模型下拉菜单，含 NEW 徽标、模型简介面板
- **GPT 列表**：侧边栏 GPT 子菜单（数据分析 / 写作助手 / 课件排版等）
- **语音模式**：全屏语音对话覆盖层，动效还原
- **设置中心**：二级弹窗设置页（通用 / 语音 / 数据控制等 Tab），移动端自适应整页化
- **移动端适配**：手机竖屏 / PC 横屏双布局，侧边栏抽屉式滑出
- **单文件架构**：HTML + CSS + JS 全部内联，0 依赖、0 构建、0 外部请求

## 🚀 快速开始

无需安装任何东西：

```bash
# 方式一：直接双击 index.html 用浏览器打开

# 方式二：本地起个静态服务
python -m http.server 8080
# 然后访问 http://localhost:8080
```

> 💡 也可以直接部署到 GitHub Pages / Vercel / Cloudflare Pages，开箱即上线。

## 📂 项目结构

```
chatgpt-ui/
├── index.html      # 全部代码（HTML + CSS + JS 单文件）
├── README.md
├── CHANGELOG.md    # 版本记录
├── LICENSE
└── .gitignore
```

## 🗺️ 升级路线图（Roadmap）

本项目会持续迭代，后续方向：

| 阶段 | 内容 | 状态 |
|------|------|------|
| v1.0 | 完美复刻静态版（当前版本） | ✅ 已完成 |
| v2.0 | 接入大模型 API Key（OpenAI / 兼容接口），静态壳变真实对话 | 📋 规划中 |
| v3.0 | 使用 Python（如 PyWebview / Tkinter + WebView）打包为 Windows 桌面客户端 | 📋 规划中 |

## 🤝 贡献

欢迎提 Issue / PR，尤其欢迎官方界面细节的还原度修正。

## 📄 License

[MIT](./LICENSE) © 2026
