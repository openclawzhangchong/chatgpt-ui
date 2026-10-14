# -*- coding: utf-8 -*-
"""
mcp_servers/pdf.py · PDF 读取 MCP Server（本地自建）
----------------------------------------------------------------
工具：pdf_read（提取全部页文本）、pdf_info（页数/元信息/目录大纲）
"""
import os
import datetime

_SYS_DIRS = ('c:\\windows', 'c:\\program files', 'c:\\program files (x86)', 'c:\\programdata')


def _guard(path):
    p = os.path.abspath(os.path.expanduser(str(path)))
    low = p.lower()
    for bad in _SYS_DIRS:
        if low.startswith(bad):
            raise PermissionError('系统目录禁止访问：' + p)
    if not os.path.isfile(p):
        raise FileNotFoundError('文件不存在：' + p)
    if not p.lower().endswith('.pdf'):
        raise ValueError('仅支持 .pdf 文件')
    return p


def pdf_read(path, max_pages=50, max_chars=10000):
    import pymupdf
    p = _guard(path)
    doc = pymupdf.open(p)
    pages = []
    total = len(doc)
    for i in range(min(total, max_pages)):
        pages.append('【第%d页】\n%s' % (i + 1, doc[i].get_text().strip()))
    doc.close()
    text = '\n\n'.join(pages)
    if len(text) > max_chars:
        text = text[:max_chars] + '\n……（已截断，共 %d 页）' % total
    return {'path': p, 'total_pages': total, 'shown_pages': min(total, max_pages), 'text': text}


def pdf_info(path):
    import pymupdf
    p = _guard(path)
    doc = pymupdf.open(p)
    meta = doc.metadata or {}
    toc = doc.get_toc()[:50]
    doc.close()
    return {'path': p, 'pages': meta.get('pages') or len(toc),
            'title': meta.get('title') or '',
            'author': meta.get('author') or '',
            'creator': meta.get('creator') or '',
            'toc': [{'level': lv, 'title': t, 'page': pg} for lv, t, pg in toc]}


def _h(fn):
    return lambda args: fn(**args)


TOOLS = [
    {
        'name': 'pdf_read',
        'description': '读取 PDF 文件文本内容（按页分段，可限页数与字符数）。适合合同、论文、报告等 PDF 的资料提取。',
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string', 'description': 'PDF 文件完整路径'},
            'max_pages': {'type': 'integer', 'description': '最多读取页数，默认 50'},
            'max_chars': {'type': 'integer', 'description': '最大返回字符数，默认 10000'}},
            'required': ['path']},
        'handler': _h(lambda path, max_pages=50, max_chars=10000: pdf_read(path, max_pages, max_chars)),
    },
    {
        'name': 'pdf_info',
        'description': '查看 PDF 元信息：页数、标题、作者、制作工具、书签目录。',
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string'}},
            'required': ['path']},
        'handler': _h(lambda path: pdf_info(path)),
    },
]
