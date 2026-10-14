# -*- coding: utf-8 -*-
"""
mcp_servers/__init__.py · 本地自建 MCP Server 池
----------------------------------------------------------------
每个子模块是一个标准 MCP server（同构描述符：name/description/inputSchema/handler）。
本地 server 走「builtin 进程内加载」：不打子进程、不增打包风险，连接即用。
config.json 的 builtinMcp 数组控制启用哪些：["web", "files", "office", "dev"]
TODO(Worker): 将来 server 清单可改为 Worker/数据库下发。
"""


def load_builtin(names, log=print):
    """按名加载本地 MCP server，返回 (新增工具描述符列表, 状态列表)。"""
    import importlib
    out = []
    status = []
    for name in (names or []):
        try:
            mod = importlib.import_module('mcp_servers.' + name)
            tools = getattr(mod, 'TOOLS', [])
            out.extend(tools)
            status.append({'name': 'builtin-' + name, 'status': '已加载', 'tool_count': len(tools), 'server': name})
            log('本地 MCP[%s] 已加载 %d 个工具' % (name, len(tools)))
        except Exception as e:
            status.append({'name': 'builtin-' + name, 'status': '加载失败', 'tool_count': 0, 'server': name})
            log('本地 MCP[%s] 加载失败：%s' % (name, str(e)[:200]))
    return out, status
