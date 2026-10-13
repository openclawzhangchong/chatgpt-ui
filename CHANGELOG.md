# 更新日志（Changelog）

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，
版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- 使用 Python（PyWebview 等）打包为 Windows 桌面客户端
- API 配置改为从 Worker / 数据库动态获取（见 HANDOFF.md）

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

[Unreleased]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/releases/tag/v1.0.0
