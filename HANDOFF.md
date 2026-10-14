# HANDOFF · 交接清单（v3.0.0 之后）

> 给下一次迭代的你（或下一次会话的我）：本页登记已完成基线 + 未完成事项 + 接手要点。

## ✅ 当前基线（v3.5.0，2026-10-15）

- **后台八分区**（/admin，左侧导航）：模型池 / 人设 GPT / 首页卡片 / 对话与朗读 / 外观品牌 / MCP 工具 / 系统 / 账号；对齐 dog2027 全部后台能力并本地化（热重载 MCP 是它没有的）。UI 全部自有 ChatGPT 风，不学 dog2027 视觉。
- **settings.json = 本地「数据库」主表**：外观/对话默认/人设/首页卡片/MCP 配置/朗读音色一张键值表（%APPDATA%），与 models.json（模型池）、admin.json（凭据）构成三表；将来上 Worker/D1 按键拆表。
- **前台动态下发**（dynamic.js 零侵入）：/api/appearance（品牌/主题/强调色）、/api/personas（GPT 列表，静态项兜底）、/api/starters（hero 建议卡片）；对话默认（sysExtra/tone/温度/上限）全部服务端注入，前台零改动。
- **MCP 热重载**：tools.reload_extensions 摘 ms_ 前缀重挂，后台保存即生效；config.json 的 mcpServers/builtinMcp 一次性迁入 settings（标记位 mcpMigrated 防回填）。

- **网页版**：index.html（UI 框架，红线不动）+ realchat.js（真实对话 + 模型菜单真实化）+ storage.js（IndexedDB）+ tts.js（朗读）+ toolbox.js（菜单换血）+ compress.js（上下文压缩）+ voice.js（语音闭环 + 音色分组下拉试听）+ admin-gate.js（管理员入口）+ admin.html/admin.js（/admin 后台页）+ config.js（gitignore）。
- **桌面版**：`desktop/` Python 壳——main.py（pywebview + **系统托盘** + uvicorn）+ server.py（OpenAI 兼容 SSE 代理 + 工具循环 + TTS + 导出 + 配置诊断日志 + **/api/models + /api/admin/* + /admin 路由**）+ tools.py（注册表 + 扩展装载）+ tools_extra.py（11 内建）+ mcp_client.py（远程 MCP 客户端）+ mcp_servers/（本地自建 MCP server 池：web/files/office/dev/pdf/media）+ **models.py（模型池 + 管理员鉴权，v3.4.0 新增）**。**已交付桌面 EXE（含自定义图标），双击即用。**
- **工具总数 41** = 17 内建 + 18 本地 MCP（web 3/files 3/office 3/dev 5/pdf 2/media 2）+ 6 远程 MCP（DeepWiki 3 + MS Learn 3）。
- **管理后台（v3.4.0）**：`/admin` 页，管理员口令登录（PBKDF2 20 万轮哈希，默认口令 18596950000，只存哈希）；模型池增删改/启停/默认/测试；内置 Qwen 条目带「内置」徽章可停用不可删；Key 全程打码；token TTL 7 天。
- **模型池两层存储**：随包 `desktop/models.default.json` + `%APPDATA%/ChatGPT-UI/models.json` 覆写层；管理员凭据同理（`admin.default.json` → `%APPDATA%/ChatGPT-UI/admin.json`）。换机器/重装 = 回到随包默认，覆写层不丢（除非删 %APPDATA%）。
- **音色（v3.4.1）**：微软全量 322 个分组下拉（中文女声/男声/方言/多语言/其他，小名映射）+ 前台设置面板试听 + **后台「朗读设置」默认音色**（settings.json）；优先级 = 前台手动选 > 后台默认 > config 兜底；断网回落 SAPI。
- **实测基线**：流式对话 / 思考折叠 / 多工具齐发 / 多步工具链 / Word+Excel+PPT 读写闭环 / PDF 读取 / 二维码生成 / 产物打开按钮 / 刷新持久化 / 托盘 / EXE 41 工具全装载 / **管理员登录(错密拒+对密过+无 token 401) / 模型 CRUD / 停用后设默认被拒 / 删内置 403 / 假 model id 静默回落 / 聊天带 model id 路由 / 音色 322 个分组 / 后台默认音色读写+TTS 链路**。

## 🧭 关键架构事实（接手必读）

1. **前端 → 本地服务**：桌面版前端 config.js 的 baseUrl 是 `/api`，realchat.js 请求 `/api/chat/completions`；server.py 做 OpenAI 兼容 SSE 透传（reasoning_content/content 原样转发）+ 工具循环（最多 6 轮），工具事件塞在 `delta.rc_tool`。
2. **工具注册表 = MCP 兼容**：tools.py 的 `{name, description, inputSchema(JSON Schema), handler}` 与 MCP tool 描述符同构；将来接标准 MCP server 用官方 SDK ClientSession.list_tools() 包一层 handler 混入 REGISTRY 即可，工具循环零改动。
3. **API 实测特征**：Qwen3.6-35B-A3B-Vision 是推理模型（先 reasoning 后 content）；原生支持 function calling；max_tokens 给太小（<800）会全耗在思考上正文为空；上游 Cloudflare 拦 Python 默认 UA（必须带浏览器 UA）；线路有 TCP 抖动（超时 100s + 3 次重试）。
4. **pywebview 红线**：必须 `webview.start(private_mode=False)`——否则 WebView2 用户目录不持久化，IndexedDB 重启即丢（本次踩坑已修）。
5. **edge-tts 已知问题**：微软 WSS 握手 403（GEC 令牌/线路策略），已实现 SAPI 离线兜底；edge-tts 7.2.8 若将来修复可自动恢复高音质。
6. **重新生成/朗读拦截**都挂在 document 捕获层（事件在目标元素时 capture 监听器按注册顺序执行，挂 #messages 上拦不住原演示监听器）。
7. **打包**：`desktop/build_desktop.py` 三步（同步前端到 ui/ → PyInstaller --onefile --windowed → 拷 EXE+config.json 到桌面）。EXE 旁 config.json 优先于内置配置，改 key 不用重打包。
8. **v3.4.0 安全默认值**：管理员默认口令 18596950000（仅以 PBKDF2 20 万轮哈希形式存在于随包 `admin.default.json`，仓库 public 也可接受）。**首次登录后请立即在后台「修改口令」**——换随机盐、与默认值彻底脱钩。模型 Key 同理：只写不读、接口一律打码。
9. **v3.4.0 路由注册顺序**：`/admin` 与 `/api/*` 必须注册在静态 catch-all `/{fname:path}` **之前**，否则会被劫持成 404（v3.2 踩过的坑同款位置）。
10. **版本号铁律（v3.4.2 起）**：单一数据源 = `desktop/server.py` 的 `APP_VERSION` 常量；发版时改它 + CHANGELOG + README 徽章，前端「关于」页/后台「系统」页自动动态拉取 `/api/version`，**禁止在 HTML/JS 里再写死版本串**（v3.4.1 曾漏更后台页版本，v3.4.2 修掉）。测试前先 `netstat` 查 18765 有无残留 EXE/僵尸进程——旧进程会冒充新代码响应，得出假测试结果。

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
6. **⚠️ config.json 升级坑（v3.1 踩到）**：build_desktop 不覆盖已存在于桌面的 config.json——配置模板升级（如新增 mcpServers/builtinMcp 字段）时必须手动把新模板覆盖到桌面，否则 EXE 读旧配置、新功能静默不生效。后续应改成「外部 config 缺字段时自动合并模板」。
7. **⚠️ PyInstaller 动态导入坑（v3.2 踩到）**：`--collect-submodules` 只收子模块**不带父包**，importlib 动态 import 的包（mcp_servers）整个丢失且静默失败——必须显式 `--hidden-import mcp_servers`（父包）+ 各子模块。凡运行时 importlib.import_module 的包都要显式列出。
8. **远程 MCP 特性**：mcp_client.py 支持 http/sse/stdio 三传输，工具以 `ms_<服务器>_<工具>` 前缀合并；启动时后台装载，失败不影响其他工具。ModelScope 托管 URL 个人专属 24h 有效，过期需重新复制。托盘 UI 需用户双击 EXE 在交互会话验证（沙箱后台会话看不到托盘）。
9. **本地 MCP server 池**：mcp_servers/ 每文件一个标准 MCP server（同构描述符），builtin 进程内加载；加新 server = 新建模块 + config.json builtinMcp 加名 + build_desktop.py 加 hidden-import。web_search 用 Bing 主源（DuckDuckGo 境内不通）；Bing 中文查询会把高亮词堆在标题尾部，属服务端行为非 bug。
10. 版本节奏：每版更新版本号 + CHANGELOG + git tag（当前 v3.2.0）。
