# -*- coding: utf-8 -*-
"""
tools_extra.py · v3.1 内建工具扩充（11 个）
----------------------------------------------------------------
由 tools.load_extensions() 在启动时挂载进 REGISTRY，不改动 v3.0 的 tools.py 本体。
新增：read_text_file / write_text_file / list_directory / clipboard_read / clipboard_write /
      take_screenshot / open_url / system_info / get_weather / current_time / calculate
"""
import os
import re
import json
import datetime
import urllib.request
import urllib.parse

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

_TEXT_EXTS = ('.txt', '.md', '.json', '.csv', '.log', '.py', '.js', '.html', '.css', '.xml',
              '.yaml', '.yml', '.ini', '.cfg', '.bat', '.ps1', '.mdx', '.htm', '.tsv')
_SYS_DIRS = ('c:\\windows', 'c:\\program files', 'c:\\program files (x86)', 'c:\\programdata')


def _guard(path):
    p = os.path.abspath(os.path.expanduser(str(path)))
    low = p.lower()
    for bad in _SYS_DIRS:
        if low.startswith(bad):
            raise PermissionError('系统目录禁止访问：' + p)
    return p


def read_text_file(path, max_chars=6000):
    import tools as _t
    p = _guard(path)
    if not os.path.isfile(p):
        raise FileNotFoundError('文件不存在：' + p)
    if not p.lower().endswith(_TEXT_EXTS):
        raise ValueError('仅支持读取文本类文件：' + ' '.join(_TEXT_EXTS))
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read(max_chars)


def write_text_file(filename, content):
    import tools as _t
    p = os.path.join(_t.export_dir(), _t._safe_name(filename, '.txt'))
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content or '')
    return p


def list_directory(path=None):
    import tools as _t
    p = _guard(path or _t.desktop_dir())
    items = []
    for n in sorted(os.listdir(p))[:100]:
        fp = os.path.join(p, n)
        items.append({'name': n, 'dir': os.path.isdir(fp),
                      'size_kb': round(os.path.getsize(fp) / 1024, 1) if os.path.isfile(fp) else None})
    return {'dir': p, 'entries': items}


def clipboard_read():
    import win32clipboard
    win32clipboard.OpenClipboard()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        return '[剪贴板中无文本内容]'
    finally:
        win32clipboard.CloseClipboard()


def clipboard_write(text):
    import win32clipboard
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, str(text))
    finally:
        win32clipboard.CloseClipboard()
    return '已写入剪贴板（%d 字符）' % len(str(text))


def take_screenshot(monitor=1):
    from PIL import ImageGrab
    img = ImageGrab.grab()
    p = os.path.join(_export_dir(), 'screenshot_%s.png' % datetime.datetime.now().strftime('%H%M%S'))
    img.save(p)
    return p


def _export_dir():
    import tools as _t
    return _t.export_dir()


def open_url(url):
    if not re.match(r'^https?://', url or ''):
        raise ValueError('URL 必须以 http(s):// 开头')
    import webbrowser
    webbrowser.open(url)
    return '已在默认浏览器打开：' + url


def system_info():
    info = {'os': os.environ.get('OS', ''), 'computer': os.environ.get('COMPUTERNAME', ''),
            'user': os.environ.get('USERNAME', '')}
    try:
        import psutil
        vm = psutil.virtual_memory()
        du = psutil.disk_usage('C:/')
        info['cpu_percent'] = psutil.cpu_percent(interval=0.3)
        info['mem'] = '%d%%（可用 %.1f/%.1f GB）' % (vm.percent, vm.available / 2**30, vm.total / 2**30)
        info['disk_c'] = '%d%%（剩余 %.1f GB）' % (du.percent, du.free / 2**30)
    except Exception as e:
        info['psutil'] = '不可用：' + str(e)
    return info


def _wttr(city):
    params = urllib.parse.urlencode({
        'format': '%l:+%c+%t+体感%f+湿度%h+风%w',
        'lang': 'zh',
    })
    url = 'https://wttr.in/%s?%s' % (urllib.parse.quote(city or 'Quanzhou'), params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        text = r.read().decode('utf-8', 'ignore').strip()
    if '<!DOCTYPE' in text or '<html' in text.lower() or not text:
        raise ValueError('wttr.in 返回异常')
    return text


def _open_meteo(city):
    """兜底天气源：Open-Meteo 地理编码 + 实时天气（免费无 key）。"""
    results = []
    for lang in ('zh', None):  # 中文名带 language=zh 优先；查不到再试不带语言（英文/拼音）
        q = {'name': city, 'count': 1}
        if lang:
            q['language'] = lang
        geo_url = 'https://geocoding-api.open-meteo.com/v1/search?%s' % urllib.parse.urlencode(q)
        try:
            with urllib.request.urlopen(urllib.request.Request(geo_url, headers={'User-Agent': UA}), timeout=20) as r:
                geo = json.loads(r.read().decode('utf-8', 'ignore'))
            results = geo.get('results') or []
        except Exception:
            results = []
        if results:
            break
    if not results:
        raise ValueError('未找到城市：%s（可尝试用拼音，如 Quanzhou）' % city)
    g = results[0]
    wx_url = 'https://api.open-meteo.com/v1/forecast?%s' % urllib.parse.urlencode({
        'latitude': g['latitude'], 'longitude': g['longitude'],
        'current': 'temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code'})
    with urllib.request.urlopen(urllib.request.Request(wx_url, headers={'User-Agent': UA}), timeout=20) as r:
        wx = json.loads(r.read().decode('utf-8', 'ignore'))
    cur = wx.get('current') or {}
    return '%s：%.1f°C（体感 %.1f°C），湿度 %d%%，风 %.1f km/h' % (
        g.get('name', city), cur.get('temperature_2m', 0), cur.get('apparent_temperature', 0),
        cur.get('relative_humidity_2m', 0), cur.get('wind_speed_10m', 0))


# 常见中国城市中文→拼音映射（Open-Meteo 地理编码只收拼音/英文名）
CITY_PINYIN = {
    '泉州': 'Quanzhou', '厦门': 'Xiamen', '福州': 'Fuzhou', '莆田': 'Putian', '漳州': 'Zhangzhou',
    '龙岩': 'Longyan', '三明': 'Sanming', '南平': 'Nanping', '宁德': 'Ningde',
    '北京': 'Beijing', '上海': 'Shanghai', '广州': 'Guangzhou', '深圳': 'Shenzhen',
    '杭州': 'Hangzhou', '南京': 'Nanjing', '苏州': 'Suzhou', '天津': 'Tianjin',
    '重庆': 'Chongqing', '成都': 'Chengdu', '武汉': 'Wuhan', '西安': 'Xian',
    '长沙': 'Changsha', '郑州': 'Zhengzhou', '济南': 'Jinan', '青岛': 'Qingdao',
    '大连': 'Dalian', '宁波': 'Ningbo', '无锡': 'Wuxi', '合肥': 'Hefei',
    '南昌': 'Nanchang', '昆明': 'Kunming', '贵阳': 'Guiyang', '南宁': 'Nanning',
    '海口': 'Haikou', '三亚': 'Sanya', '石家庄': 'Shijiazhuang', '太原': 'Taiyuan',
    '哈尔滨': 'Harbin', '长春': 'Changchun', '沈阳': 'Shenyang', '呼和浩特': 'Hohhot',
    '兰州': 'Lanzhou', '西宁': 'Xining', '银川': 'Yinchuan', '乌鲁木齐': 'Urumqi',
    '拉萨': 'Lhasa', '香港': 'Hong Kong', '澳门': 'Macau', '台北': 'Taipei',
}


def get_weather(city):
    city = (city or 'Quanzhou').strip()
    query = CITY_PINYIN.get(city, city)
    try:
        return _wttr(city if city == query else query)
    except Exception:
        return _open_meteo(query)


def current_time():
    now = datetime.datetime.now()
    wd = '一二三四五六日'[now.weekday()]
    return now.strftime('%Y-%m-%d %H:%M:%S') + ' 星期' + wd


def calculate(expression):
    expr = str(expression).strip()
    if not re.match(r'^[\d\s\+\-\*/\.\,\(\)%a-zA-Z_]+$', expr):
        raise ValueError('仅支持数学表达式（数字/运算符/括号/函数名）')
    if 'import' in expr.lower() or '_' in expr:
        raise ValueError('表达式含非法内容')
    import math
    safe = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
    safe.update({'abs': abs, 'round': round, 'min': min, 'max': max, 'sum': sum})
    return '%s = %s' % (expr, eval(expr, {'__builtins__': {}}, safe))


def _h(fn):
    return lambda args: fn(**args)


def builtin_tools():
    """返回 MCP 兼容描述符列表（name/description/inputSchema/handler）。"""
    return [
        {'name': 'read_text_file',
         'description': '读取本机文本类文件内容（txt/md/json/csv/代码等，上限 6000 字符；禁止系统目录）。',
         'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string', 'description': '文件完整路径'}}, 'required': ['path']},
         'handler': _h(lambda path, max_chars=6000: read_text_file(path, max_chars))},
        {'name': 'write_text_file',
         'description': '写一个文本文件到桌面 chatgpt-ui-exports 目录。',
         'inputSchema': {'type': 'object', 'properties': {'filename': {'type': 'string'}, 'content': {'type': 'string'}}, 'required': ['filename', 'content']},
         'handler': _h(lambda filename, content: write_text_file(filename, content))},
        {'name': 'list_directory',
         'description': '列出本机某个目录的内容（默认桌面；禁止系统目录）。',
         'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string', 'description': '目录路径，缺省为桌面'}}},
         'handler': _h(lambda path=None: list_directory(path))},
        {'name': 'clipboard_read',
         'description': '读取当前剪贴板的文本内容。',
         'inputSchema': {'type': 'object', 'properties': {}},
         'handler': _h(lambda: clipboard_read())},
        {'name': 'clipboard_write',
         'description': '把文本写入剪贴板。',
         'inputSchema': {'type': 'object', 'properties': {'text': {'type': 'string'}}, 'required': ['text']},
         'handler': _h(lambda text: clipboard_write(text))},
        {'name': 'take_screenshot',
         'description': '截取整个屏幕并保存 PNG 到导出目录，返回文件路径。',
         'inputSchema': {'type': 'object', 'properties': {}},
         'handler': _h(lambda monitor=1: take_screenshot(monitor))},
        {'name': 'open_url',
         'description': '在默认浏览器中打开一个网址。',
         'inputSchema': {'type': 'object', 'properties': {'url': {'type': 'string'}}, 'required': ['url']},
         'handler': _h(lambda url: open_url(url))},
        {'name': 'system_info',
         'description': '获取本机系统信息：操作系统/CPU/内存/磁盘占用。',
         'inputSchema': {'type': 'object', 'properties': {}},
         'handler': _h(lambda: system_info())},
        {'name': 'get_weather',
         'description': '查询城市实时天气（wttr.in，中文结果）。',
         'inputSchema': {'type': 'object', 'properties': {'city': {'type': 'string', 'description': '城市中文名或拼音'}}, 'required': ['city']},
         'handler': _h(lambda city: get_weather(city))},
        {'name': 'current_time',
         'description': '获取当前本机日期时间与星期。',
         'inputSchema': {'type': 'object', 'properties': {}},
         'handler': _h(lambda: current_time())},
        {'name': 'calculate',
         'description': '计算数学表达式（四则运算、sqrt/log/sin/cos/pi/e 等）。',
         'inputSchema': {'type': 'object', 'properties': {'expression': {'type': 'string', 'description': '如 (3+4)*sqrt(16)'}}, 'required': ['expression']},
         'handler': _h(lambda expression: calculate(expression))},
    ]
