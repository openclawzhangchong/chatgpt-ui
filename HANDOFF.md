# HANDOFF · 交接清单（v2.0.0 之后）

> 给下一次迭代的你（或下一次会话的我）：本页登记已完成基线 + 未完成事项 + 接手要点。

## ✅ 当前基线（v2.0.0，2026-10-13）

- 单文件静态复刻页 `index.html` + 零侵入接入模块 `realchat.js` + 配置 `config.js`（不入库）。
- 真实对话已跑通：OpenAI 兼容接口直连 `https://jiuyeke.cn/v1`，模型 `Qwen3.6-35B-A3B-Vision`，SSE 流式、思考过程折叠、图片上传（Vision）、多轮上下文、停止、重新生成、错误中文映射均已实测通过。
- 本地运行：`python -m http.server 8080`，浏览器开 `http://localhost:8080`。
- 服务端 CORS 已放行（回显任意 Origin），浏览器直连无跨域问题。
- API 实测特征：该模型是推理模型，先推 `delta.reasoning_content` 再推 `delta.content`；`max_tokens` 上限 16384，给太小会全部耗在思考上导致正文为空。
- 网络注意：该 API 线路有抖动（偶发 TCP 连接超时），客户端已用浏览器 fetch 天然可重试；如需更稳可加前端超时重连。

## 📋 未完成 / 后续方向（按优先级）

| 优先级 | 事项 | 说明 |
|--------|------|------|
| P1 | **API 配置改从 Worker/数据库获取** | 代码里已埋 `TODO(Worker)` 标记（realchat.js 头部、config 两文件）。只需替换 `window.RC_CONFIG` 的来源，realchat.js 不用动。用户明确表示将来配置（Key、模型清单）可能从 Worker / 第一数据库下发 |
| P1 | 历史会话持久化 | 目前 `CHATS` 在内存里，刷新即失。方案：localStorage / IndexedDB 序列化 CHATS + 启动时恢复 |
| P2 | 思考过程的持久化 | AI 消息已存 `reasoning` 字段，但切回旧会话时 `appendMsg` 只渲染 `html`，思考过程不回显。可在渲染时重建折叠块 |
| P2 | 语音模式真实现 | `voiceOverlay` 目前是纯展示。可接 Web Speech API（STT/TTS）或后端语音服务 |
| P2 | Python 打包 Windows 客户端 | PyWebview / pywebview + 本地静态文件即可，Roadmap v3.0 |
| P3 | 设置弹窗真实化 | 主题切换已真实；其余 Tab（语音/数据控制等）仍为演示 |
| P3 | 朗读 / 分享 / 资料库 / Sora 弹窗 | 均为演示占位 |
| P3 | Markdown 渲染增强 | 自写轻量 mdRender，暂无表格/链接/嵌套列表；如需增强可换 marked.js（注意保持零依赖原则则需内联进 realchat.js） |

## ⚠️ 已知限制与红线

1. **API Key 在前端可见**：浏览器抓包即可拿到。仅自用；若要公开部署，先在服务端撤换 Key 或改走代理（用户当前明确选择不接 Cloudflare，尊重此决定，但公开部署前必须提醒）。
2. `config.js` 永不入库（已 gitignore），换机器部署时从 `config.example.js` 复制。
3. 接入方式为**零侵入覆盖**：`realchat.js` 依赖 index.html 里的全局函数名（`sendMessage/renderModelMenu/newChat/CHATS/MODELS/currentModel/...`），若重构 index.html 的 JS，必须同步检查 realchat.js 的覆盖点。
4. 重新生成拦截挂在 **document 捕获层**（事件在目标元素上时 capture 监听器按注册顺序执行，挂 #messages 上会晚于原演示监听器）——不要挪回 #messages。
5. 版本节奏：每版更新版本号 + CHANGELOG + git tag（当前 v2.0.0）。
