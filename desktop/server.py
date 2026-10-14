# -*- coding: utf-8 -*-
"""
server.py · ChatGPT UI 桌面版本地服务
----------------------------------------------------------------
- 静态托管 ui/（前端打包产物）
- POST /api/chat/completions : OpenAI 兼容 SSE 代理 + MCP 工具循环（tool-calling loop）
  前端 realchat.js 无需知道工具存在；工具过程通过 delta.rc_tool 事件透传渲染
- GET  /api/tools            : 工具清单（工具箱面板）
- GET  /api/tts              : Edge TTS 朗读（返回 audio/mpeg）
- GET  /api/tts/voices       : 可用音色
- GET  /api/models           : 模型池清单（前台模型菜单用）
- GET  /admin                : 管理后台页（ui/admin.html，需管理员登录）
- POST /api/admin/login      : 管理员登录（口令 → token）
- GET  /api/admin/models     : 模型池管理（增删改/启停/默认/测试，require_admin 守卫）
- POST /api/export           : 当前会话导出 Word / Markdown
模型池两层存储：随包 models.default.json + %APPDATA% 覆写层，详见 models.py。
"""
import os
import re
import sys
import json
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, Response, FileResponse

import tools
import models

APP_TITLE = 'ChatGPT · 复刻版'
HOST = '127.0.0.1'


# ---------- 配置 ----------

def _bundled_dir():
    if getattr(sys, 'frozen', False):  # PyInstaller onefile
        return Path(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))
    return Path(__file__).parent

def _exe_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

def load_config():
    for p in [_exe_dir() / 'config.json', _bundled_dir() / 'config.json', _bundled_dir() / 'config.example.json']:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if p.name == 'config.example.json' or not cfg.get('apiKey') or 'xxx' in str(cfg.get('apiKey', '')):
                    if p.name == 'config.example.json':
                        continue
                return cfg, str(p)
        except Exception:
            continue
    return {}, None

CFG, CFG_PATH = load_config()
try:  # 诊断：把实际生效的配置来源写进崩溃日志（windowed 下无 stdout，这是唯一排查入口）
    with open(os.path.join(os.environ.get('TEMP', '.'), 'ChatGPT-UI.log'), 'a', encoding='utf-8') as _f:
        _f.write('[%s] config loaded from: %s | builtinMcp=%s | mcpServers=%d\n' % (
            time.strftime('%Y-%m-%d %H:%M:%S'), CFG_PATH,
            (CFG.get('builtinMcp') if isinstance(CFG, dict) else None),
            len((CFG.get('mcpServers') or []) if isinstance(CFG, dict) else [])))
except Exception:
    pass
PORT = int(CFG.get('port') or 18765)
MAX_TOKENS = int(CFG.get('maxTokens') or 16384)
TEMP = float(CFG.get('temperature') if CFG.get('temperature') is not None else 0.7)
TTS_VOICE = CFG.get('ttsVoice') or 'zh-CN-XiaoxiaoNeural'
# 上游模型配置改由 models.py 模型池裁决（config.json 的 baseUrl/apiKey/model 仅作随包默认种子）。
# 兼容读取：旧 config.json 若无池可用时，退回这里的单Provider包装，保证老配置不瞎。
UPSTREAM = (CFG.get('baseUrl') or '').rstrip('/')
API_KEY = CFG.get('apiKey') or ''
MODEL = CFG.get('model') or 'Qwen3.6-35B-A3B-Vision'


def _load_extensions_async():
    """后台挂载扩展工具：11 个新内建（tools_extra）+ 本地 MCP server 池（builtinMcp）
    + config.json mcpServers 远程 MCP。远程连接需要数秒，不阻塞服务就绪。"""
    try:
        import tools as _tools
        _tools.load_extensions(CFG.get('mcpServers') or [], CFG.get('builtinMcp') or [],
                               log=lambda m: print('[mcp]', m))
    except Exception as e:
        print('[mcp] 扩展装载异常：', e)


threading.Thread(target=_load_extensions_async, daemon=True).start()


app = FastAPI(title=APP_TITLE, docs_url=None, redoc_url=None)


# ---------- 静态资源 ----------

def ui_dir():
    d = _bundled_dir() / 'ui'
    return d if d.is_dir() else _bundled_dir()

@app.get('/')
def index():
    f = ui_dir() / 'index.html'
    return FileResponse(f, media_type='text/html') if f.is_file() else Response('ui/index.html 缺失', status_code=500)


# ---------- 上游 LLM 流式 ----------

def upstream_events(payload, base_url, api_key):
    """请求上游 OpenAI 兼容接口（SSE），实时产出事件元组：
      ('reasoning', text) / ('content', text) / ('tool_calls', [..])
    流开始前网络错误自动重试 1 次；开始后异常直接抛出（由调用方转 rc_error）。"""
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                base_url + '/chat/completions', data=body, method='POST',
                headers={'Content-Type': 'application/json',
                         'Authorization': 'Bearer ' + api_key,
                         'Accept': 'text/event-stream',
                         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'})
            resp = urllib.request.urlopen(req, timeout=100)
            break
        except urllib.error.HTTPError as e:
            detail = ''
            try:
                detail = e.read().decode('utf-8', 'ignore')[:300]
            except Exception:
                pass
            raise RuntimeError('上游 HTTP %s：%s' % (e.code, detail))
        except Exception as e:
            last_err = e
            time.sleep(1.5)
    else:
        raise RuntimeError('网络连接失败（已重试）：%s' % last_err)

    tool_calls = {}
    buf = ''
    started = False
    while True:
        chunk = resp.read(4096)
        if not chunk:
            break
        buf += chunk.decode('utf-8', 'ignore')
        while '\n' in buf:
            line, buf = buf.split('\n', 1)
            line = line.strip()
            if not line.startswith('data:'):
                continue
            data = line[5:].strip()
            if data == '[DONE]':
                continue
            try:
                j = json.loads(data)
            except Exception:
                continue
            ch = (j.get('choices') or [{}])[0]
            d = ch.get('delta') or {}
            if d.get('reasoning_content'):
                started = True
                yield ('reasoning', d['reasoning_content'])
            if d.get('content'):
                started = True
                yield ('content', d['content'])
            for tc in (d.get('tool_calls') or []):
                started = True
                idx = tc.get('index', 0)
                slot = tool_calls.setdefault(idx, {'id': '', 'name': '', 'arguments': ''})
                if tc.get('id'):
                    slot['id'] = tc['id']
                fn = tc.get('function') or {}
                if fn.get('name'):
                    slot['name'] += fn['name']
                if fn.get('arguments'):
                    slot['arguments'] += fn['arguments']
    resp.close()
    calls = [tool_calls[i] for i in sorted(tool_calls)] if tool_calls else None
    if calls:
        yield ('tool_calls', calls)


def sse(obj):
    return 'data: ' + json.dumps(obj, ensure_ascii=False) + '\n\n'


@app.post('/api/chat/completions')
async def chat_completions(request: Request):
    body = await _json_body(request)
    msgs_in = body.get('messages') or []
    # 前端可传 model = 模型池条目 id；不传/不认识/已停用 → 静默回落到默认（dog2027 同款静默回落，
    # 用户看到的是「悄悄换回默认」，比「发不出去」好）。服务端不信任前端传来的 key/baseUrl。
    provider = models.resolve_provider(body.get('model'))
    if not provider:
        # 池子空的极端情况：退回 config.json 单Provider 包装，老配置不至于直接瘫
        if UPSTREAM and API_KEY:
            provider = {'id': '_cfg', 'name': MODEL, 'base_url': UPSTREAM, 'api_key': API_KEY,
                        'model': MODEL, 'max_output_tokens': MAX_TOKENS, 'temperature': TEMP}
        else:
            async def _no_model():
                yield sse({'choices': [{'delta': {'rc_error': '没有可用的模型：请打开管理后台添加并启用一个'}, 'index': 0}]})
                yield 'data: [DONE]\n\n'
            return StreamingResponse(_no_model(), media_type='text/event-stream')
    p_base, p_key, p_model = provider['base_url'], provider['api_key'], provider['model']
    p_max = provider.get('max_output_tokens') or MAX_TOKENS
    p_temp = provider.get('temperature')
    if p_temp is None:
        p_temp = TEMP
    msgs = list(msgs_in)

    def gen():
        yield sse({'choices': [{'delta': {'role': 'assistant'}, 'index': 0}]})
        try:
            for round_no in range(10):  # 最多 10 轮工具循环（复杂多步任务需要）
                payload = {'model': p_model, 'messages': msgs, 'stream': True,
                           'max_tokens': p_max, 'temperature': p_temp,
                           'tools': tools.schemas(), 'tool_choice': 'auto'}
                content_parts = []
                calls = None
                for kind, data in upstream_events(payload, p_base, p_key):
                    if kind == 'reasoning':
                        yield sse({'choices': [{'delta': {'reasoning_content': data}, 'index': 0}]})
                    elif kind == 'content':
                        content_parts.append(data)
                        yield sse({'choices': [{'delta': {'content': data}, 'index': 0}]})
                    elif kind == 'tool_calls':
                        calls = data
                collected_content = ''.join(content_parts)

                if calls:
                    # 工具轮：思考/正文已实时转发，这里组装 assistant 消息进入下一轮
                    assistant_msg = {'role': 'assistant', 'content': collected_content or '',
                                     'tool_calls': [{'id': c['id'] or ('call_%d_%d' % (round_no, i)),
                                                     'type': 'function',
                                                     'function': {'name': c['name'], 'arguments': c['arguments'] or '{}'}}
                                                    for i, c in enumerate(calls)]}
                    msgs.append(assistant_msg)
                    for i, c in enumerate(calls):
                        name = c['name']
                        try:
                            args = json.loads(c['arguments'] or '{}')
                        except Exception:
                            args = {}
                        yield sse({'choices': [{'delta': {'rc_tool': {'phase': 'call', 'name': name, 'args': args}}, 'index': 0}]})
                        result = tools.execute(name, args)
                        tool_path = (result.get('data') or {}).get('path') if isinstance(result.get('data'), dict) else None
                        if not tool_path:
                            # office/pdf/media 类工具直接返回路径字符串，兼容提取
                            t = (result.get('text') or '').strip()
                            if re.match(r'^[A-Za-z]:\\', t) and os.path.isfile(t):
                                tool_path = t
                        yield sse({'choices': [{'delta': {'rc_tool': {'phase': 'result', 'name': name,
                                                                      'ok': result.get('ok'),
                                                                      'path': tool_path,
                                                                      'text': (result.get('text') or '')[:600]}}, 'index': 0}]})
                        msgs.append({'role': 'tool', 'tool_call_id': assistant_msg['tool_calls'][i]['id'],
                                     'content': result.get('text') or ('' if result.get('ok') else '失败')})
                    continue  # 下一轮：让模型基于工具结果继续
                # 正常结束
                yield sse({'choices': [{'delta': {}, 'finish_reason': 'stop', 'index': 0}]})
                yield 'data: [DONE]\n\n'
                return
            yield sse({'choices': [{'delta': {'content': '\n\n（工具循环轮次已达上限，已停止）'}, 'index': 0}]})
            yield sse({'choices': [{'delta': {}, 'finish_reason': 'stop', 'index': 0}]})
            yield 'data: [DONE]\n\n'
        except Exception as e:
            yield sse({'choices': [{'delta': {'rc_error': str(e)}, 'index': 0}]})
            yield 'data: [DONE]\n\n'

    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ---------- 工具箱 ----------

@app.get('/api/tools')
def api_tools():
    import tools as _tools
    return {'tools': _tools.describe(), 'export_dir': str(_tools.export_dir()),
            'mcp': _tools.REMOTE_STATUS,
            'remote': any(t.get('remote') for t in _tools.REGISTRY)}

async def _json_body(request):
    """解析请求体 JSON；兼容非 UTF-8 客户端（如 Windows 命令行按 GBK 发送的场景）。"""
    raw = await request.body()
    try:
        return json.loads(raw.decode('utf-8'))
    except UnicodeDecodeError:
        return json.loads(raw.decode('gbk', 'ignore'))


@app.post('/api/tool')
async def api_tool_call(request: Request):
    b = await _json_body(request)
    return JSONResponse(tools.execute(b.get('name'), b.get('args') or {}))


# ---------- 会话导出 ----------

@app.post('/api/export')
async def api_export(request: Request):
    b = await request.json()
    title = (b.get('title') or '对话导出')[:60]
    messages = b.get('messages') or []
    fmt = b.get('fmt') or 'word'
    if fmt == 'markdown':
        lines = ['# %s' % title, '']
        for m in messages:
            who = '🧑 用户' if m.get('role') == 'user' else '🤖 AI'
            lines += ['**%s**' % who, '', m.get('text', ''), '']
        path = os.path.join(tools.export_dir(), tools._safe_name(title, '.md'))
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return {'ok': True, 'path': path}
    content_parts = []
    for m in messages:
        who = '【用户】' if m.get('role') == 'user' else '【AI】'
        content_parts.append('## %s' % who)
        content_parts.append(m.get('text', ''))
    path = tools.create_word(title, title + '（%s）' % time.strftime('%Y-%m-%d'), '\n'.join(content_parts))
    return {'ok': True, 'path': path}


# ---------- Edge TTS ----------

_TTS_VOICE_CACHE = {'ts': 0, 'voices': None}

# 微软标准中文音色的小名人名映射（下拉框里「晓晓」比「XiaoxiaoNeural」好认）；
# 不在表里的显示 ShortName 核心段，不硬翻。
_CN_VOICE_NAMES = {
    'Xiaoxiao': '晓晓', 'Xiaoyi': '晓伊', 'Xiaomo': '晓墨', 'Xiaoxuan': '晓萱',
    'Xiaorui': '晓睿', 'Xiaoshuang': '晓双', 'Xiaohan': '晓涵', 'Xiaomeng': '晓梦',
    'Xiaqiu': '晓秋', 'Yunxi': '云希', 'Yunyang': '云扬', 'Yunjie': '云杰',
    'Yunfeng': '云枫', 'Yunhao': '云浩', 'Xiaochen': '晓辰', 'Xiaoman': '晓曼',
}


def _voice_label(v):
    sn = v.get('ShortName') or ''
    parts = sn.split('-')
    core = parts[-1].replace('Neural', '').replace('Online', '') if parts else sn
    cn = _CN_VOICE_NAMES.get(core)
    label = cn or core or sn
    dialect = (parts[2] if len(parts) >= 4 and parts[0].lower() == 'zh' and parts[1].upper() == 'CN'
               and not parts[2].endswith(('Neural', 'Online')) else '')
    if dialect and not cn:
        label = core + '（' + dialect.capitalize() + '）'
    return label


def _classify_voice(v):
    """分组规则（参考 dog2027 思路，按微软 ShortName 规律裁到本地版）：
    中文女声 / 中文男声 / 方言 / 多语言 / 其他。
    ShortName 形如 zh-CN-XiaoxiaoNeural；方言音色第三段是方言名（zh-CN-liaoning-XiaobeiNeural）。"""
    sn = v.get('ShortName') or ''
    parts = sn.split('-')
    locale = parts[0].lower() if parts else ''
    gender = (v.get('Gender') or '').lower()
    if locale == 'zh' and len(parts) >= 2 and parts[1].upper() == 'CN':
        if len(parts) >= 4 and not parts[2].endswith(('Neural', 'Online')):
            return '方言'  # liaoning / shaanxi / sichuan…
        if gender == 'male':
            return '中文男声'
        return '中文女声'
    if locale == 'zh':  # zh-HK / zh-TW 等变体
        return '多语言'
    if 'multilingual' in sn.lower() or 'multilingual' in (v.get('FriendlyName') or '').lower():
        return '多语言'
    return '其他'


@app.get('/api/tts/voices')
def tts_voices():
    """微软全量音色（约 500 个），分组下发；edge-tts 拉不到（断网）时回落内置 4 个，
    设置面板照常能用，不给用户开天窗（dog2027 同款兜底纪律）。"""
    import time as _t
    if _TTS_VOICE_CACHE['voices'] and _t.time() - _TTS_VOICE_CACHE['ts'] < 600:
        return _TTS_VOICE_CACHE['voices']
    groups = {}
    try:
        import asyncio
        import edge_tts
        # 同步端点跑在线程池里，没有 running loop，asyncio.run 最稳；
        # 万一将来在异步上下文里调到，RuntimeError 会被下面 except 接住回落内置 4 个。
        raw = asyncio.run(edge_tts.list_voices())
        for v in raw or []:
            sn = v.get('ShortName')
            if not sn:
                continue
            g = _classify_voice(v)
            groups.setdefault(g, []).append({'id': sn, 'name': _voice_label(v), 'group': g})
        # 组内按名字排，中文组排最前
        order = ['中文女声', '中文男声', '方言', '多语言', '其他']
        voices = []
        for g in order:
            if g in groups:
                voices.extend(sorted(groups.pop(g), key=lambda x: x['name']))
        for g, items in groups.items():  # 未预料的组兜底追加
            voices.extend(sorted(items, key=lambda x: x['name']))
        out = {'voices': voices}
        _TTS_VOICE_CACHE.update({'ts': _t.time(), 'voices': out})
        return out
    except Exception:
        return {'voices': [
            {'id': 'zh-CN-XiaoxiaoNeural', 'name': '晓晓（女声）', 'group': '中文女声'},
            {'id': 'zh-CN-YunxiNeural', 'name': '云希（男声）', 'group': '中文男声'},
            {'id': 'zh-CN-YunyangNeural', 'name': '云扬（男声·新闻）', 'group': '中文男声'},
            {'id': 'zh-CN-XiaoyiNeural', 'name': '晓伊（女声）', 'group': '中文女声'},
        ]}

@app.get('/api/tts')
async def api_tts(text: str, voice: str = None):
    text = (text or '').strip()[:5000]
    if not text:
        return Response('text required', status_code=400)
    # 优先 Edge TTS（联网、音质好）；被微软服务端拒绝/断网时降级 Windows SAPI（离线）
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice or TTS_VOICE)
        buf = bytearray()
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                buf += chunk['data']
        if buf:
            return Response(bytes(buf), media_type='audio/mpeg', headers={'Cache-Control': 'no-cache'})
    except Exception:
        pass
    # SAPI 离线兜底
    import tempfile, asyncio
    p = os.path.abspath(os.path.join(tempfile.gettempdir(), 'rc_tts_%d.wav' % int(time.time() * 1000)))

    def sapi_render():
        import win32com.client
        v = win32com.client.Dispatch('SAPI.SpVoice')
        stream = win32com.client.Dispatch('SAPI.SpFileStream')
        stream.Open(p, 3)  # SSFMCreateForWrite
        v.AudioOutputStream = stream
        v.Speak(text)
        stream.Close()
        v.AudioOutputStream = None

    await asyncio.to_thread(sapi_render)
    return Response(open(p, 'rb').read(), media_type='audio/wav', headers={'Cache-Control': 'no-cache'})


# ---------- 管理后台（模型池 + 管理员登录） ----------

def _admin_gate(request: Request):
    """统一守卫：Bearer token 且 role=admin，否则返回 (None, 响应)。"""
    claims = models.verify_token(models.token_from_request(request))
    if not claims:
        return None, JSONResponse({'error': '未登录或登录已过期'}, status_code=401)
    return claims, None


@app.get('/api/models')
def api_models():
    """前台模型菜单：只给启用的（Key 打码），顺带告诉前端当前默认是哪条。"""
    return {'models': [models.mask_provider(p) for p in models.list_providers(include_disabled=False)],
            'activeId': models.default_provider_id()}


@app.post('/api/admin/login')
async def admin_login(request: Request):
    b = await _json_body(request)
    token, err = models.admin_login(b.get('name') or '', b.get('password') or '')
    if err:
        return JSONResponse({'error': err}, status_code=401)
    return {'token': token, 'name': models.load_admin().get('name'), 'role': 'admin'}


@app.get('/api/admin/session')
def admin_session(request: Request):
    claims, err = _admin_gate(request)
    if err:
        return err
    return {'ok': True, 'name': claims.get('name')}


@app.get('/api/admin/models')
async def admin_list_models(request: Request):
    claims, err = _admin_gate(request)
    if err:
        return err
    return {'models': [models.mask_provider(p) for p in models.list_providers()],
            'defaultProviderId': models.default_provider_id(),
            'adminName': models.load_admin().get('name')}


@app.post('/api/admin/models')
async def admin_add_model(request: Request):
    claims, err = _admin_gate(request)
    if err:
        return err
    b = await _json_body(request)
    ok, why = models.validate_provider(b)
    if not ok:
        return JSONResponse({'error': why}, status_code=400)
    return {'ok': True, 'provider': models.mask_provider(models.add_provider(b))}


@app.put('/api/admin/models/{pid}')
async def admin_update_model(pid: str, request: Request):
    claims, err = _admin_gate(request)
    if err:
        return err
    b = await _json_body(request)
    existing = models.get_provider(pid)
    if not existing:
        return JSONResponse({'error': '条目不存在'}, status_code=404)
    ok, why = models.validate_provider(b, existing)
    if not ok:
        return JSONResponse({'error': why}, status_code=400)
    return {'ok': True, 'provider': models.mask_provider(models.update_provider(pid, b))}


@app.delete('/api/admin/models/{pid}')
async def admin_delete_model(pid: str, request: Request):
    claims, err = _admin_gate(request)
    if err:
        return err
    ok, why = models.delete_provider(pid)
    if not ok:
        return JSONResponse({'error': why}, status_code=403)
    return {'ok': True}


@app.post('/api/admin/models/{pid}/enable')
async def admin_enable_model(pid: str, request: Request):
    claims, err = _admin_gate(request)
    if err:
        return err
    return {'ok': models.set_enabled(pid, True)}


@app.post('/api/admin/models/{pid}/disable')
async def admin_disable_model(pid: str, request: Request):
    claims, err = _admin_gate(request)
    if err:
        return err
    return {'ok': models.set_enabled(pid, False)}


@app.post('/api/admin/models/{pid}/default')
async def admin_default_model(pid: str, request: Request):
    claims, err = _admin_gate(request)
    if err:
        return err
    ok, why = models.set_default(pid)
    if not ok:
        return JSONResponse({'error': why}, status_code=400)
    return {'ok': True}


@app.post('/api/admin/models/{pid}/test')
async def admin_test_model(pid: str, request: Request):
    claims, err = _admin_gate(request)
    if err:
        return err
    return models.test_provider(pid)


@app.post('/api/admin/password')
async def admin_change_password(request: Request):
    claims, err = _admin_gate(request)
    if err:
        return err
    b = await _json_body(request)
    ok, why = models.change_password(b.get('oldPassword') or '', b.get('newPassword') or '')
    if not ok:
        return JSONResponse({'error': why}, status_code=400)
    return {'ok': True}


@app.get('/admin')
def admin_page():
    f = ui_dir() / 'admin.html'
    return FileResponse(f, media_type='text/html') if f.is_file() else Response('admin.html 缺失', status_code=500)


# ---------- 静态资源 catch-all（必须最后注册，避免劫持 /api/* 路由） ----------

@app.get('/{fname:path}')
def static_files(fname: str):
    base = ui_dir().resolve()
    f = (base / fname).resolve()
    if not str(f).startswith(str(base)) or not f.is_file():
        return Response('Not Found', status_code=404)
    mime = {'html': 'text/html', 'js': 'application/javascript', 'css': 'text/css',
            'json': 'application/json', 'png': 'image/png', 'svg': 'image/svg+xml'}.get(
        f.suffix.lstrip('.'), 'application/octet-stream')
    return FileResponse(f, media_type=mime)
