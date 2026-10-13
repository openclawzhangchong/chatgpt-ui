# -*- coding: utf-8 -*-
"""
mcp_client.py · 通用 MCP 客户端（远程 streamable HTTP / SSE + 本地 stdio）
----------------------------------------------------------------
- 按标准 mcpServers 配置接入（与 ModelScope MCP 广场 / Cherry Studio / Claude Desktop 同构）：
    {"name": "deepwiki", "transport": "http", "url": "https://mcp.deepwiki.com/mcp"}
    {"name": "modelscope-fetch", "transport": "sse", "url": "https://mcp.api-inference.modelscope.cn/sse/xxxx"}
    {"name": "local-weather", "transport": "stdio", "command": "python", "args": ["server.py"], "env": {}}
- ModelScope 托管 MCP 的 URL 是个人专属且 24 小时有效：在魔搭广场服务详情页复制，
  粘贴到 config.json 的 mcpServers[].url 即可，过期后刷新重填（客户端启动时自动探测，失败不影响其他服务）。
- 协议：JSON-RPC 2.0（initialize → notifications/initialized → tools/list → tools/call）
TODO(Worker): 远程 MCP 清单将来可由 Worker/数据库下发。
"""
import json
import os
import subprocess
import threading
import urllib.request
import urllib.error

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
PROTO_VER = '2025-03-26'


def _post(url, payload, headers=None, timeout=60):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    h = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
         'User-Agent': UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method='POST', headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode('utf-8', 'ignore')
        sid = r.headers.get('Mcp-Session-Id') or r.headers.get('mcp-session-id')
        ctype = r.headers.get('Content-Type', '')
    body = _extract_jsonrpc(raw, ctype)
    return body, sid


def _extract_jsonrpc(raw, ctype):
    """响应可能是纯 JSON，也可能是 SSE（data: 行）。"""
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith('{'):
        try:
            return json.loads(raw)
        except Exception:
            return None
    if 'event-stream' in ctype or '\ndata:' in raw or raw.startswith('data:') or 'data:' in raw[:200]:
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith('data:'):
                try:
                    return json.loads(line[5:].strip())
                except Exception:
                    continue
    try:
        return json.loads(raw)
    except Exception:
        return None


class RemoteMcp:
    """单个远程/本地 MCP 服务器的客户端会话（轻量：按需重建）。"""

    def __init__(self, conf):
        self.name = conf.get('name') or 'mcp'
        self.conf = conf
        self.transport = (conf.get('transport') or ('stdio' if conf.get('command') else 'http')).lower()
        self.url = conf.get('url') or ''
        self.headers = dict(conf.get('headers') or {})
        self.session_id = None
        self.proc = None
        self._id = 0
        self.status = '未连接'
        self.server_info = None

    # ---------- JSON-RPC ----------
    def _rpc(self, method, params=None, notify=False):
        self._id += 1
        payload = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            payload['params'] = params
        if not notify:
            payload['id'] = self._id
        if self.transport == 'stdio':
            return self._rpc_stdio(payload, notify)
        body, sid = _post(self.url, payload, headers=self.headers)
        if sid and not self.session_id:
            self.session_id = sid
            self.headers['Mcp-Session-Id'] = sid
            # 状态型服务器需要补发 initialized 通知
            if method == 'initialize':
                try:
                    _post(self.url, {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                          headers=self.headers)
                except Exception:
                    pass
        if body and isinstance(body, dict) and 'error' in body:
            raise RuntimeError('MCP %s: %s' % (self.name, json.dumps(body['error'], ensure_ascii=False)[:300]))
        return body.get('result') if isinstance(body, dict) else None

    def _rpc_stdio(self, payload, notify=False):
        if self.proc is None or self.proc.poll() is not None:
            env = dict(os.environ)
            env.update(self.conf.get('env') or {})
            self.proc = subprocess.Popen(
                [self.conf['command']] + list(self.conf.get('args') or []),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env=env, text=True, encoding='utf-8', bufsize=1)
        line = json.dumps(payload, ensure_ascii=False) + '\n'
        self.proc.stdin.write(line)
        self.proc.stdin.flush()
        if notify:
            return None
        # 读取直到拿到对应 id 的响应（跳过通知行）
        while True:
            out = self.proc.stdout.readline()
            if not out:
                raise RuntimeError('MCP %s: stdio 无响应' % self.name)
            out = out.strip()
            if not out:
                continue
            try:
                msg = json.loads(out)
            except Exception:
                continue
            if msg.get('id') == payload.get('id'):
                if 'error' in msg:
                    raise RuntimeError('MCP %s: %s' % (self.name, json.dumps(msg['error'], ensure_ascii=False)[:300]))
                return msg.get('result')

    # ---------- MCP 生命周期 ----------
    def connect(self):
        result = self._rpc('initialize', {
            'protocolVersion': PROTO_VER,
            'capabilities': {},
            'clientInfo': {'name': 'chatgpt-ui-desktop', 'version': '3.1.0'},
        })
        self.server_info = (result or {}).get('serverInfo')
        if self.transport == 'http' and not self.session_id:
            # 无状态服务器：无需 initialized 通知
            pass
        elif self.transport != 'http':
            try:
                self._rpc('notifications/initialized', notify=True)
            except Exception:
                pass
        self.status = '已连接'
        return self.server_info

    def list_tools(self):
        result = self._rpc('tools/list', {})
        return (result or {}).get('tools') or []

    def call_tool(self, tool_name, arguments):
        result = self._rpc('tools/call', {'name': tool_name, 'arguments': arguments or {}})
        if result is None:
            return {'ok': False, 'text': 'MCP %s 无响应' % self.name}
        # 结果可能含 isError 与 content[{type:'text',text}]
        err = bool(result.get('isError'))
        parts = []
        for c in result.get('content') or []:
            t = c.get('type')
            if t == 'text':
                parts.append(c.get('text', ''))
            elif t == 'image':
                parts.append('[图片：%s]' % c.get('mimeType', 'image'))
            elif t == 'resource':
                parts.append('[资源] %s' % json.dumps(c.get('resource', {}), ensure_ascii=False)[:500])
        text = '\n'.join(p for p in parts if p) or json.dumps(result, ensure_ascii=False)[:1000]
        return {'ok': not err, 'text': text[:4000]}


def load_remote_tools(conf_list, log=print):
    """连接所有配置的远程 MCP 服务器，返回 MCP 兼容描述符列表：
       [{name(带前缀), description, inputSchema, handler, server}]"""
    out = []
    for conf in (conf_list or []):
        name = conf.get('name') or 'mcp'
        if not (conf.get('url') or conf.get('command')):
            continue
        cli = RemoteMcp(conf)
        try:
            cli.connect()
            tools = cli.list_tools()
        except Exception as e:
            log('MCP[%s] 连接失败：%s' % (name, str(e)[:200]))
            continue
        log('MCP[%s] 已连接 %s，%d 个工具' % (name, (cli.server_info or {}).get('name', ''), len(tools)))
        for t in tools:
            tname = t.get('name') or ''
            if not tname:
                continue
            out.append({
                'name': 'ms_%s_%s' % (name, tname),
                'display': '%s · %s' % (name, tname),
                'description': ('[%s/MCP] %s' % (name, t.get('description') or tname)).strip()[:300],
                'inputSchema': t.get('inputSchema') or {'type': 'object', 'properties': {}},
                'handler': (lambda c, tn: lambda args: c.call_tool(tn, args))(cli, tname),
                'remote': True,
            })
    return out
