# 更新日志（Changelog）

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，
版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- 接入大模型 API（OpenAI / 兼容接口），支持真实对话
- Python 打包为 Windows 桌面客户端（PyWebview 方案调研）

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

[Unreleased]: https://github.com/openclawzhangchong/chatgpt-ui/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/openclawzhangchong/chatgpt-ui/releases/tag/v1.0.0
