# -*- coding: utf-8 -*-
"""
models.py · 模型池 + 管理员鉴权（v3.4.0）
----------------------------------------------------------------
两层存储（对齐 dog2027 providers 数据模型，为将来上 Worker/D1 留好迁移形态）：
  · 随包默认层  models.default.json（打进 EXE，只读不改）——内置模型 + 默认口令哈希
  · 运行时覆写层 %APPDATA%/ChatGPT-UI/models.json（首次运行从默认层复制，后台增删改全写这里）

管理员凭据同样两层：admin.default.json（只含 PBKDF2 哈希，禁止明文，dog2027 v1.19.0 教训）
→ %APPDATA%/ChatGPT-UI/admin.json。

token：HMAC-SHA256 签名的 JSON（sub/role/exp），密钥随机生成后持久化在 admin.json，
TTL 7 天。本地单机场景够用；将来上云整体换成 dog2027 那套 signToken 即可。
"""
import os
import io
import json
import time
import hmac
import base64
import hashlib
import secrets
import threading

APP_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'ChatGPT-UI')
RUNTIME_MODELS = os.path.join(APP_DIR, 'models.json')
RUNTIME_ADMIN = os.path.join(APP_DIR, 'admin.json')
RUNTIME_SETTINGS = os.path.join(APP_DIR, 'settings.json')
PBKDF2_ROUNDS = 200_000
TOKEN_TTL_MS = 7 * 86_400_000
ADMIN_NAME_DEFAULT = '张翀'
TTS_VOICE_DEFAULT = 'zh-CN-XiaoxiaoNeural'

_lock = threading.RLock()
_cache = {'models': None, 'admin': None}


# ---------- 路径（兼容 PyInstaller onefile） ----------

def _bundled_dir():
    if getattr(__import__('sys'), 'frozen', False):
        return __import__('sys')._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _read_json(path):
    try:
        with io.open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)  # 原子替换，避免写一半崩溃留下坏档


# ---------- 模型池 ----------

def _seed_models():
    """首次运行：把随包默认池复制到 %APPDATA%。之后读写都只碰覆写层。"""
    default = _read_json(os.path.join(_bundled_dir(), 'models.default.json')) or {}
    data = {'version': 1,
            'defaultProviderId': default.get('defaultProviderId'),
            'providers': default.get('providers') or []}
    _write_json(RUNTIME_MODELS, data)
    return data


def load_models():
    with _lock:
        if _cache['models'] is not None:
            return _cache['models']
        data = _read_json(RUNTIME_MODELS)
        if not isinstance(data, dict) or not isinstance(data.get('providers'), list):
            data = _seed_models()
        _cache['models'] = data
        return data


def save_models(data):
    with _lock:
        _write_json(RUNTIME_MODELS, data)
        _cache['models'] = data


def _norm_provider(p):
    """补齐字段、掐掉前后空格、base_url 去尾斜杠。缺字段按安全默认值，不让脏数据进池。"""
    p = dict(p or {})
    p['id'] = str(p.get('id') or '').strip()
    p['name'] = str(p.get('name') or '').strip()
    p['base_url'] = str(p.get('base_url') or '').strip().rstrip('/')
    p['api_key'] = str(p.get('api_key') or '').strip()
    p['model'] = str(p.get('model') or '').strip()
    for k in ('max_input_tokens', 'max_output_tokens'):
        v = p.get(k)
        p[k] = int(v) if isinstance(v, (int, float)) and v > 0 else None
    t = p.get('temperature')
    p['temperature'] = float(t) if isinstance(t, (int, float)) and 0 <= float(t) <= 2 else 0.7
    p['enabled'] = bool(p.get('enabled', True))
    p['builtin'] = bool(p.get('builtin', False))
    p['created_at'] = int(p.get('created_at') or int(time.time() * 1000))
    return p


def list_providers(include_disabled=True):
    rows = [_norm_provider(p) for p in load_models().get('providers') or []]
    rows = [p for p in rows if p['id']]
    if not include_disabled:
        rows = [p for p in rows if p['enabled']]
    return rows


def get_provider(pid):
    for p in list_providers():
        if p['id'] == pid:
            return p
    return None


def default_provider_id():
    pid = load_models().get('defaultProviderId')
    return pid if pid and get_provider(pid) else None


def resolve_provider(pid=None):
    """聊天时选型：显式 id → 默认 → 第一条启用的。都找不到返回 None（调用方给友好报错）。"""
    if pid:
        p = get_provider(pid)
        if p and p['enabled']:
            return p
    did = default_provider_id()
    if did:
        p = get_provider(did)
        if p and p['enabled']:
            return p
    for p in list_providers(include_disabled=False):
        return p
    return None


def validate_provider(body, existing=None):
    """新增/编辑校验。返回 (ok, err)。编辑时 apiKey 留空 = 不改。"""
    def s(k):
        v = body.get(k)
        return v.strip() if isinstance(v, str) else None
    name = s('name') or (existing or {}).get('name')
    base_url = s('baseUrl') or (existing or {}).get('base_url')
    model = s('model') or (existing or {}).get('model')
    if not name or not base_url or not model:
        return False, '名称、Base URL、模型名都要填'
    if not (base_url.startswith('http://') or base_url.startswith('https://')):
        return False, 'Base URL 必须以 http:// 或 https:// 开头'
    key = s('apiKey') or (existing or {}).get('api_key')
    if not key:
        return False, 'API Key 不能为空（编辑时留空表示不变）'
    return True, None


def add_provider(body):
    data = load_models()
    pid = 'pv_' + secrets.token_hex(4)
    while get_provider(pid):  # 理论上不会撞，撞了就重摇
        pid = 'pv_' + secrets.token_hex(4)
    row = _norm_provider({
        'id': pid, 'name': body.get('name'), 'base_url': body.get('baseUrl'),
        'api_key': body.get('apiKey'), 'model': body.get('model'),
        'max_input_tokens': body.get('maxInputTokens'), 'max_output_tokens': body.get('maxOutputTokens'),
        'temperature': body.get('temperature'), 'enabled': True, 'builtin': False,
    })
    data['providers'].append(row)
    # 池里原本一条都没有：新加的直接当默认，用户端立刻可用（dog2027 v1.6.2 同款思路）
    if not data.get('defaultProviderId') or not get_provider(data['defaultProviderId']):
        data['defaultProviderId'] = pid
    save_models(data)
    return row


def update_provider(pid, body):
    data = load_models()
    for i, p in enumerate(data['providers']):
        if p.get('id') == pid:
            merged = dict(p)
            merged.update({'name': body.get('name') or p.get('name'),
                           'base_url': body.get('baseUrl') or p.get('base_url'),
                           'model': body.get('model') or p.get('model'),
                           'api_key': body.get('apiKey') or p.get('api_key'),
                           'max_input_tokens': body.get('maxInputTokens') if body.get('maxInputTokens') else p.get('max_input_tokens'),
                           'max_output_tokens': body.get('maxOutputTokens') if body.get('maxOutputTokens') else p.get('max_output_tokens'),
                           'temperature': body.get('temperature') if body.get('temperature') is not None else p.get('temperature')})
            data['providers'][i] = _norm_provider(merged)
            save_models(data)
            return data['providers'][i]
    return None


def delete_provider(pid):
    data = load_models()
    target = next((p for p in data['providers'] if p.get('id') == pid), None)
    if not target:
        return False, '条目不存在'
    if target.get('builtin'):
        return False, '内置模型不可删除，可停用'
    data['providers'] = [p for p in data['providers'] if p.get('id') != pid]
    if data.get('defaultProviderId') == pid:
        data['defaultProviderId'] = next((p['id'] for p in data['providers'] if p.get('enabled')), None)
    save_models(data)
    return True, None


def set_enabled(pid, on):
    data = load_models()
    for p in data['providers']:
        if p.get('id') == pid:
            p['enabled'] = bool(on)
            # 停用默认模型：静默滑到下一个启用的，别让聊天直接发不出去
            if not on and data.get('defaultProviderId') == pid:
                data['defaultProviderId'] = next((q['id'] for q in data['providers'] if q.get('enabled') and q['id'] != pid), None)
            save_models(data)
            return True
    return False


def set_default(pid):
    p = get_provider(pid)
    if not p:
        return False, '条目不存在'
    if not p['enabled']:
        return False, '先启用再设为默认'
    data = load_models()
    data['defaultProviderId'] = pid
    save_models(data)
    return True, None


def mask_provider(p):
    """Key 只写不读：对外一律打码（dog2027 §7.3 同款纪律）。"""
    q = dict(p)
    key = q.pop('api_key', '')
    q['apiKeyMasked'] = ('sk-…' + key[-4:]) if key else ''
    q['hasKey'] = bool(key)
    return q


# ---------- 管理员凭据与 token ----------

def _seed_admin():
    default = _read_json(os.path.join(_bundled_dir(), 'admin.default.json')) or {}
    data = {'name': default.get('name') or ADMIN_NAME_DEFAULT,
            'password_hash': default.get('password_hash') or '',
            'token_secret': secrets.token_hex(32),
            'created_at': int(time.time() * 1000)}
    _write_json(RUNTIME_ADMIN, data)
    return data


def load_admin():
    with _lock:
        if _cache['admin'] is not None:
            return _cache['admin']
        data = _read_json(RUNTIME_ADMIN)
        if not isinstance(data, dict) or not data.get('password_hash'):
            data = _seed_admin()
        data.setdefault('token_secret', secrets.token_hex(32))
        _cache['admin'] = data
        return data


def save_admin(data):
    with _lock:
        _write_json(RUNTIME_ADMIN, data)
        _cache['admin'] = data


def _hash_password(password, salt_hex, rounds=PBKDF2_ROUNDS):
    return 'pbkdf2_sha256$%d$%s$%s' % (
        rounds, salt_hex,
        hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt_hex), rounds).hex())


def verify_password(password):
    stored = load_admin().get('password_hash') or ''
    try:
        algo, rounds, salt_hex, hash_hex = stored.split('$')
        if algo != 'pbkdf2_sha256':
            return False
        cand = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                   bytes.fromhex(salt_hex), int(rounds)).hex()
        return hmac.compare_digest(cand, hash_hex)
    except Exception:
        return False


def admin_login(name, password):
    cfg = load_admin()
    if not cfg.get('password_hash'):
        return None, '服务端未配置管理员口令'
    if name.strip() != cfg.get('name'):
        return None, '用户名或口令不正确'
    if not password or not verify_password(password):
        return None, '用户名或口令不正确'
    return issue_token(), None


def change_password(old_password, new_password):
    if not new_password or len(new_password) < 6:
        return False, '新口令至少 6 位'
    if not verify_password(old_password):
        return False, '原口令不正确'
    cfg = load_admin()
    salt_hex = secrets.token_bytes(16).hex()  # 换随机盐，和默认那把彻底脱钩
    cfg['password_hash'] = _hash_password(new_password, salt_hex)
    save_admin(cfg)
    return True, None


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def issue_token():
    cfg = load_admin()
    header = _b64url(json.dumps({'alg': 'HS256', 'typ': 'JWT'}, separators=(',', ':')).encode())
    body = _b64url(json.dumps({'sub': 'admin', 'role': 'admin', 'name': cfg.get('name'),
                               'iat': int(time.time() * 1000),
                               'exp': int(time.time() * 1000) + TOKEN_TTL_MS},
                              separators=(',', ':')).encode())
    sig = hmac.new(cfg['token_secret'].encode(), ('%s.%s' % (header, body)).encode(), hashlib.sha256).digest()
    return '%s.%s.%s' % (header, body, _b64url(sig))


def verify_token(token):
    if not token or token.count('.') != 2:
        return None
    header, body, sig = token.split('.')
    cfg = load_admin()
    expect = hmac.new(cfg['token_secret'].encode(), ('%s.%s' % (header, body)).encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url(expect), sig):
        return None
    try:
        pad = '=' * (-len(body) % 4)
        claims = json.loads(base64.urlsafe_b64decode(body + pad))
    except Exception:
        return None
    if claims.get('role') != 'admin' or claims.get('exp', 0) < int(time.time() * 1000):
        return None
    return claims


def token_from_request(request):
    h = request.headers.get('authorization') or ''
    return h[7:] if h.startswith('Bearer ') else ''


# ---------- 全局设置（v3.4.1：后台默认音色等，轻量键值本地库） ----------
# 现阶段的「本地数据库」就是这组 JSON 文件：models.json / admin.json / settings.json，
# 增删改查全在 Python 侧完成，原子写入防坏档。将来要多设备同步时，把这三个文件的
# 读写函数换成 Worker/D1 调用即可，上层 API 零改动。

def load_settings():
    with _lock:
        data = _read_json(RUNTIME_SETTINGS)
        if not isinstance(data, dict):
            # 种子：随包 config.json 的 ttsVoice（老配置平滑迁移，用户已有选择不丢）
            cfg = _read_json(os.path.join(_bundled_dir(), 'config.json')) or {}
            data = {'ttsVoice': cfg.get('ttsVoice') or TTS_VOICE_DEFAULT}
            _write_json(RUNTIME_SETTINGS, data)
        data.setdefault('ttsVoice', TTS_VOICE_DEFAULT)
        return data


def save_settings(data):
    with _lock:
        _write_json(RUNTIME_SETTINGS, data)


# ---------- 连通性测试（真发一条 1-token 请求） ----------

def test_provider(pid):
    p = get_provider(pid)
    if not p:
        return {'ok': False, 'error': '条目不存在'}
    import urllib.request
    import urllib.error
    started = time.time()
    try:
        req = urllib.request.Request(
            p['base_url'] + '/chat/completions', method='POST',
            data=json.dumps({'model': p['model'],
                             'messages': [{'role': 'user', 'content': 'ping'}],
                             'max_tokens': 1, 'stream': False}).encode('utf-8'),
            headers={'Content-Type': 'application/json',
                     'Authorization': 'Bearer ' + p['api_key'],
                     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'})
        resp = urllib.request.urlopen(req, timeout=30)
        resp.read(256)
        return {'ok': True, 'status': resp.status, 'ms': int((time.time() - started) * 1000)}
    except urllib.error.HTTPError as e:
        detail = ''
        try:
            detail = e.read().decode('utf-8', 'ignore')[:300]
        except Exception:
            pass
        return {'ok': False, 'status': e.code, 'ms': int((time.time() - started) * 1000), 'error': detail}
    except Exception as e:
        return {'ok': False, 'ms': int((time.time() - started) * 1000), 'error': str(e)}
