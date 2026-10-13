# HANDOFF · 交接清单（v3.0.0 之后）

> 给下一次迭代的你（或下一次会话的我）：本页登记已完成基线 + 未完成事项 + 接手要点。

## ✅ 当前基线（v3.1.0，2026-10-14）

- **网页版**：index.html（UI 框架，红线不动）+ realchat.js（真实对话）+ storage.js（IndexedDB）+ tts.js（朗读）+ toolbox.js（菜单换血）+ compress.js（上下文压缩）+ config.js（gitignore）。
- **桌面版**：`desktop/` Python 壳——main.py（pywebview 窗口 + **系统托盘** + uvicorn）+ server.py（OpenAI 兼容 SSE 代理 + 工具循环 + TTS + 导出）+ tools.py（注册表 + 扩展装载）+ tools_extra.py（11 新内建工具）+ mcp_client.py（通用 MCP 客户端）。**已交付桌面 EXE，双击即用。**
- **工具总数 23**（17 内建 + 6 远程 MCP）。远程 MCP 实测接通：DeepWiki 3 工具 + Microsoft Learn 3 工具；ModelScope 魔搭 MCP 适配位已就绪（config.json mcpServers 填 URL 即生效）。
- **上下文压缩**：compress.js 的 RC_compress（8 万字符预算 → 先折叠旧图片 → 再丢最旧，保留 system + 最近 6 条）。
- **实测基线**：流式对话 / 思考折叠 / 多工具一轮齐发（时间+天气+系统信息）/ 多步工具链（list_directory 试错→DeepWiki 远程 MCP）/ 造真实 Word+Excel / 刷新持久化 / 托盘线程启动。
- 本地运行：网页 `python -m http.server 8080`；桌面 `cd desktop && python -m uvicorn server:app --port 18765`。

## 🧭 关键架构事实（接手必读）

1. **前端 → 本地服务**：桌面版前端 config.js 的 baseUrl 是 `/api`，realchat.js 请求 `/api/chat/completions`；server.py 做 OpenAI 兼容 SSE 透传（reasoning_content/content 原样转发）+ 工具循环（最多 6 轮），工具事件塞在 `delta.rc_tool`。
2. **工具注册表 = MCP 兼容**：tools.py 的 `{name, description, inputSchema(JSON Schema), handler}` 与 MCP tool 描述符同构；将来接标准 MCP server 用官方 SDK ClientSession.list_tools() 包一层 handler 混入 REGISTRY 即可，工具循环零改动。
3. **API 实测特征**：Qwen3.6-35B-A3B-Vision 是推理模型（先 reasoning 后 content）；原生支持 function calling；max_tokens 给太小（<800）会全耗在思考上正文为空；上游 Cloudflare 拦 Python 默认 UA（必须带浏览器 UA）；线路有 TCP 抖动（超时 100s + 3 次重试）。
4. **pywebview 红线**：必须 `webview.start(private_mode=False)`——否则 WebView2 用户目录不持久化，IndexedDB 重启即丢（本次踩坑已修）。
5. **edge-tts 已知问题**：微软 WSS 握手 403（GEC 令牌/线路策略），已实现 SAPI 离线兜底；edge-tts 7.2.8 若将来修复可自动恢复高音质。
6. **重新生成/朗读拦截**都挂在 document 捕获层（事件在目标元素时 capture 监听器按注册顺序执行，挂 #messages 上拦不住原演示监听器）。
7. **打包**：`desktop/build_desktop.py` 三步（同步前端到 ui/ → PyInstaller --onefile --windowed → 拷 EXE+config.json 到桌面）。EXE 旁 config.json 优先于内置配置，改 key 不用重打包。

## 📋 未完成 / 后续方向（按优先级）

| 优先级 | 事项 | 说明 |
|--------|------|------|
| P1 | **上下文压缩** | realchat.js buildApiMessages 已留 `window.RC_compress` 钩子；方案：按 token 预算裁剪最旧消息 + 对被裁历史生成摘要（summary 存会话记录 compressed 字段，schema 已预留） |
| P1 | **多会话/多人隔离** | IndexedDB sessions 仓按会话记录级存储已就绪；补 owner 字段过滤 + 会话切换 UI 即可支持多用户 |
| P1 | **API 配置改从 Worker/数据库下发** | 所有配置文件已埋 `TODO(Worker)`；server.py load_config() 与 tools.REGISTRY 都是单点替换位 |
| P2 | Excel/PPT 的流式产物预览 | 目前导出后只回路径文本；可加产物卡片（文件名+打开按钮） |
| P2 | 更多 MCP 工具 | 在 tools_extra.py / config.json mcpServers 加条目即自动进入 AI 工具清单（含魔搭广场个人 URL） |
| P2 | 设置弹窗语音 Tab 真实化 | /api/tts/voices 已就绪，补前端下拉绑定 |
| P3 | 语音输入（STT） | voiceOverlay 仍是展示态；可接 whisper.cpp 或在线 ASR |
| P3 | EXE 图标/签名/更新器 | 当前无自定义图标；杀软误报可加签名 |
| P3 | LLM 摘要式上下文压缩 | compress.js 当前为确定性折叠；可升级为调 LLM 生成摘要存会话 compression 字段 |

## ⚠️ 已知限制与红线

1. **UI 框架红线**：index.html 的界面 CSS/结构/原型 JS 不重构；所有增强走零侵入（覆盖全局函数 + document 捕获拦截 + 追加 script）。
2. **API Key 安全（用户拍板最后处理）**：桌面版 key 在 EXE 旁 config.json（本机可读）；网页版 key 在前端可见。公开部署前必须做服务端代理。
3. **config.js / desktop/config.json 永不入库**（已 gitignore）。
4. **realchat.js 覆盖点依赖**：sendMessage/renderModelMenu/newChat/CHATS/MODELS/currentModel 等全局名——重构 index.html JS 必须同步检查。
5. **桌面 open_file 白名单**：仅限桌面与导出目录，勿放开到全盘。
6. **⚠️ config.json 升级坑（v3.1 踩到）**：build_desktop 不覆盖已存在于桌面的 config.json——配置模板升级（如新增 mcpServers 字段）时必须手动把新模板覆盖到桌面，否则 EXE 读旧配置、新功能静默不生效。后续应改成「外部 config 缺字段时自动合并模板」。
7. **远程 MCP 特性**：mcp_client.py 支持 http/sse/stdio 三传输，工具以 `ms_<服务器>_<工具>` 前缀合并；启动时后台装载，失败不影响其他工具。ModelScope 托管 URL 个人专属 24h 有效，过期需重新复制。托盘 UI 需用户双击 EXE 在交互会话验证（沙箱后台会话看不到托盘）。
8. 版本节奏：每版更新版本号 + CHANGELOG + git tag（当前 v3.1.0）。
