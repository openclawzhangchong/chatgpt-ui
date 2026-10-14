# -*- coding: utf-8 -*-
"""
mcp_servers/media.py · 媒体生成与图片信息 MCP Server（本地自建）
----------------------------------------------------------------
工具：qr_generate（生成二维码 PNG）、image_info（图片尺寸/格式/EXIF）
"""
import os
import datetime
import urllib.request

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')


def _export_dir():
    import tools as _t
    return _t.export_dir()


def qr_generate(text, filename=None, size=10):
    if not (text or '').strip():
        raise ValueError('二维码内容不能为空')
    import qrcode
    qr = qrcode.QRCode(border=2, box_size=max(4, min(int(size), 30)))
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    name = filename or ('qr_' + datetime.datetime.now().strftime('%H%M%S'))
    p = os.path.join(_export_dir(), name if name.lower().endswith('.png') else name + '.png')
    img.save(p)
    return {'path': p, 'content': text[:100], 'size_kb': round(os.path.getsize(p) / 1024, 1)}


def _guard(path):
    p = os.path.abspath(os.path.expanduser(str(path)))
    low = p.lower()
    for bad in ('c:\\windows', 'c:\\program files', 'c:\\program files (x86)', 'c:\\programdata'):
        if low.startswith(bad):
            raise PermissionError('系统目录禁止访问：' + p)
    if not os.path.isfile(p):
        raise FileNotFoundError('文件不存在：' + p)
    return p


def image_info(path):
    from PIL import Image, ExifTags
    p = _guard(path)
    with Image.open(p) as im:
        info = {'path': p, 'format': im.format, 'mode': im.mode,
                'width': im.width, 'height': im.height,
                'size_kb': round(os.path.getsize(p) / 1024, 1)}
        exif = {}
        try:
            raw = im.getexif()
            for k, v in list(raw.items())[:30]:
                tag = ExifTags.TAGS.get(k, str(k))
                if isinstance(v, (str, int, float)):
                    exif[tag] = str(v)[:100]
        except Exception:
            pass
        if exif:
            info['exif'] = exif
    return info


def _h(fn):
    return lambda args: fn(**args)


TOOLS = [
    {
        'name': 'qr_generate',
        'description': '生成二维码 PNG 并保存到桌面导出目录（内容可以是网址/文本/名片信息）。',
        'inputSchema': {'type': 'object', 'properties': {
            'text': {'type': 'string', 'description': '二维码内容'},
            'filename': {'type': 'string', 'description': '可选文件名（默认自动命名）'},
            'size': {'type': 'integer', 'description': '模块尺寸 4-30，默认 10'}},
            'required': ['text']},
        'handler': _h(lambda text, filename=None, size=10: qr_generate(text, filename, size)),
    },
    {
        'name': 'image_info',
        'description': '查看图片信息：格式/尺寸/色彩模式/文件大小/EXIF 拍摄信息。',
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string', 'description': '图片完整路径'}},
            'required': ['path']},
        'handler': _h(lambda path: image_info(path)),
    },
]
