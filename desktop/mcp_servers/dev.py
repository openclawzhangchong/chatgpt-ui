# -*- coding: utf-8 -*-
"""
mcp_servers/dev.py · 开发辅助 MCP Server（本地自建）
----------------------------------------------------------------
工具：json_format / base64_codec / url_codec / regex_test / timestamp_convert
"""
import json
import base64
import re
import urllib.parse
import datetime


def json_format(text, indent=2):
    obj = json.loads(text) if isinstance(text, str) else text
    return {'ok': True, 'formatted': json.dumps(obj, ensure_ascii=False, indent=indent)}


def base64_codec(text, mode='encode'):
    if mode == 'encode':
        return {'mode': 'encode', 'result': base64.b64encode(text.encode('utf-8')).decode('ascii')}
    if mode == 'decode':
        pad = '=' * (-len(text) % 4)
        return {'mode': 'decode', 'result': base64.b64decode(text + pad).decode('utf-8', 'ignore')}
    raise ValueError('mode 仅支持 encode/decode')


def url_codec(text, mode='encode'):
    if mode == 'encode':
        return {'mode': 'encode', 'result': urllib.parse.quote(text, safe='')}
    if mode == 'decode':
        return {'mode': 'decode', 'result': urllib.parse.unquote(text)}
    raise ValueError('mode 仅支持 encode/decode')


def regex_test(pattern, text, mode='findall'):
    flags = re.MULTILINE
    try:
        if mode == 'findall':
            hits = re.findall(pattern, text, flags)
            return {'pattern': pattern, 'mode': 'findall', 'count': len(hits), 'hits': hits[:50]}
        if mode == 'match':
            m = re.match(pattern, text, flags)
            return {'pattern': pattern, 'mode': 'match', 'matched': bool(m), 'result': m.group(0) if m else ''}
        if mode == 'replace':
            raise ValueError('replace 模式请直接在对话中说明替换内容')
        raise ValueError('mode 仅支持 findall/match')
    except re.error as e:
        raise ValueError('正则语法错误：%s' % e)


def timestamp_convert(value, mode='to_date'):
    """mode=to_date: 时间戳→日期时间（自动识别秒/毫秒）；mode=to_ts: 日期字符串→时间戳。"""
    if mode == 'to_date':
        v = int(value)
        if v > 10 ** 12:  # 毫秒
            v = v / 1000
        dt = datetime.datetime.fromtimestamp(v)
        return {'input': value, 'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'weekday': '一二三四五六日'[dt.weekday()]}
    if mode == 'to_ts':
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d'):
            try:
                dt = datetime.datetime.strptime(value, fmt)
                return {'input': value, 'timestamp': int(dt.timestamp())}
            except ValueError:
                continue
        raise ValueError('无法解析日期：%s（支持 2026-10-14 08:00:00 等格式）' % value)
    raise ValueError('mode 仅支持 to_date/to_ts')


def _h(fn):
    return lambda args: fn(**args)


TOOLS = [
    {
        'name': 'json_format',
        'description': '格式化/校验 JSON 字符串，返回标准缩进排版。',
        'inputSchema': {'type': 'object', 'properties': {
            'text': {'type': 'string', 'description': 'JSON 字符串'},
            'indent': {'type': 'integer', 'description': '缩进空格数，默认 2'}},
            'required': ['text']},
        'handler': _h(lambda text, indent=2: json_format(text, indent)),
    },
    {
        'name': 'base64_codec',
        'description': 'Base64 编码/解码。',
        'inputSchema': {'type': 'object', 'properties': {
            'text': {'type': 'string'},
            'mode': {'type': 'string', 'description': 'encode 或 decode'}},
            'required': ['text', 'mode']},
        'handler': _h(lambda text, mode='encode': base64_codec(text, mode)),
    },
    {
        'name': 'url_codec',
        'description': 'URL 编码/解码（百分号编码）。',
        'inputSchema': {'type': 'object', 'properties': {
            'text': {'type': 'string'},
            'mode': {'type': 'string', 'description': 'encode 或 decode'}},
            'required': ['text', 'mode']},
        'handler': _h(lambda text, mode='encode': url_codec(text, mode)),
    },
    {
        'name': 'regex_test',
        'description': '正则表达式测试：findall 提取全部匹配 / match 测试开头匹配。',
        'inputSchema': {'type': 'object', 'properties': {
            'pattern': {'type': 'string', 'description': '正则表达式'},
            'text': {'type': 'string', 'description': '待测文本'},
            'mode': {'type': 'string', 'description': 'findall 或 match，默认 findall'}},
            'required': ['pattern', 'text']},
        'handler': _h(lambda pattern, text, mode='findall': regex_test(pattern, text, mode)),
    },
    {
        'name': 'timestamp_convert',
        'description': '时间戳与日期时间互转（自动识别秒/毫秒时间戳）。',
        'inputSchema': {'type': 'object', 'properties': {
            'value': {'type': 'string', 'description': '时间戳数字或日期字符串'},
            'mode': {'type': 'string', 'description': 'to_date（戳→日期）或 to_ts（日期→戳）'}},
            'required': ['value']},
        'handler': _h(lambda value, mode='to_date': timestamp_convert(value, mode)),
    },
]
