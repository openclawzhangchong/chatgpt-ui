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
- POST /api/export           : 当前会话导出 Word / Markdown
TODO(Worker): API 配置与工具清单将来可改为从 Worker/数据库下发。
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, Response, FileResponse

import tools

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
PORT = int(CFG.get('port') or 18765)
MAX_TOKENS = int(CFG.get('maxTokens') or 16384)
TEMP = float(CFG.get('temperature') if CFG.get('temperature') is not None else 0.7)
TTS_VOICE = CFG.get('ttsVoice') or 'zh-CN-XiaoxiaoNeural'
UPSTREAM = (CFG.get('baseUrl') or '').rstrip('/')
API_KEY = CFG.get('apiKey') or ''
MODEL = CFG.get('model') or 'Qwen3.6-35B-A3B-Vision'

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

def upstream_events(payload):
    """请求上游 OpenAI 兼容接口（SSE），实时产出事件元组：
      ('reasoning', text) / ('content', text) / ('tool_calls', [..])
    流开始前网络错误自动重试 1 次；开始后异常直接抛出（由调用方转 rc_error）。"""
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                UPSTREAM + '/chat/completions', data=body, method='POST',
                headers={'Content-Type': 'application/json',
                         'Authorization': 'Bearer ' + API_KEY,
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
    body = await request.json()
    msgs_in = body.get('messages') or []
    # 服务端不信任前端 model/key：一律使用本地配置
    msgs = list(msgs_in)

    def gen():
        yield sse({'choices': [{'delta': {'role': 'assistant'}, 'index': 0}]})
        try:
            for round_no in range(6):  # 最多 6 轮工具循环
                payload = {'model': MODEL, 'messages': msgs, 'stream': True,
                           'max_tokens': MAX_TOKENS, 'temperature': TEMP,
                           'tools': tools.schemas(), 'tool_choice': 'auto'}
                content_parts = []
                calls = None
                for kind, data in upstream_events(payload):
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
                        yield sse({'choices': [{'delta': {'rc_tool': {'phase': 'result', 'name': name,
                                                                      'ok': result.get('ok'),
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
    return {'tools': tools.describe(), 'export_dir': str(tools.export_dir())}

@app.post('/api/tool')
async def api_tool_call(request: Request):
    b = await request.json()
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

@app.get('/api/tts/voices')
def tts_voices():
    return {'voices': [
        {'id': 'zh-CN-XiaoxiaoNeural', 'name': '晓晓（女声）'},
        {'id': 'zh-CN-YunxiNeural', 'name': '云希（男声）'},
        {'id': 'zh-CN-YunyangNeural', 'name': '云扬（男声·新闻）'},
        {'id': 'zh-CN-XiaoyiNeural', 'name': '晓伊（女声）'},
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
