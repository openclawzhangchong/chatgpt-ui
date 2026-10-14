# -*- coding: utf-8 -*-
"""
mcp_servers/office.py · 办公文档读取 MCP Server（本地自建）
----------------------------------------------------------------
工具（与内建 create_* 形成读写闭环）：
- read_docx：读取 Word 段落/表格文本
- read_xlsx：读取 Excel 工作表（行数/内容，上限可控）
- read_pptx：读取 PPT 每页标题与文本
"""
import os

_SYS_DIRS = ('c:\\windows', 'c:\\program files', 'c:\\program files (x86)', 'c:\\programdata')


def _guard(path):
    p = os.path.abspath(os.path.expanduser(str(path)))
    low = p.lower()
    for bad in _SYS_DIRS:
        if low.startswith(bad):
            raise PermissionError('系统目录禁止访问：' + p)
    if not os.path.isfile(p):
        raise FileNotFoundError('文件不存在：' + p)
    return p


def read_docx(path, max_chars=8000):
    p = _guard(path)
    from docx import Document
    doc = Document(p)
    parts = []
    for para in doc.paragraphs:
        t = para.text.strip()
        if t:
            style = (para.style.name or '').lower()
            if 'heading' in style:
                lvl = style.replace('heading', '').strip() or '1'
                parts.append('#' * int(lvl) + ' ' + t)
            elif 'list' in style:
                parts.append('- ' + t)
            else:
                parts.append(t)
    for tb in doc.tables:
        for row in tb.rows[:50]:
            parts.append(' | '.join(c.text.strip() for c in row.cells))
    text = '\n'.join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + '\n……（已截断，共 %d 字符）' % len(text)
    return {'path': p, 'paragraphs': len(doc.paragraphs), 'tables': len(doc.tables),
            'text': text}


def read_xlsx(path, sheet=None, max_rows=100, max_chars=8000):
    import openpyxl
    p = _guard(path)
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb.active
    rows = []
    total = 0
    for r in ws.iter_rows(values_only=True):
        total += 1
        if len(rows) < max_rows:
            rows.append(['' if c is None else str(c) for c in r])
    wb.close()
    text = '\n'.join(' | '.join(r) for r in rows)
    if len(text) > max_chars:
        text = text[:max_chars] + '\n……（已截断）'
    return {'path': p, 'sheet': ws.title, 'sheets': wb.sheetnames if not wb else [],
            'total_rows': total, 'shown_rows': len(rows), 'text': text}


def read_pptx(path, max_chars=8000):
    from pptx import Presentation
    p = _guard(path)
    prs = Presentation(p)
    slides = []
    for i, s in enumerate(prs.slides, 1):
        texts = []
        for sh in s.shapes:
            if sh.has_text_frame:
                t = sh.text_frame.text.strip()
                if t:
                    texts.append(t)
        slides.append({'slide': i, 'text': '\n'.join(texts)})
    all_text = '\n\n'.join('【第%d页】\n%s' % (s['slide'], s['text']) for s in slides if s['text'])
    if len(all_text) > max_chars:
        all_text = all_text[:max_chars] + '\n……（已截断）'
    return {'path': p, 'slide_count': len(prs.slides._sldIdLst), 'text': all_text}


def _h(fn):
    return lambda args: fn(**args)


TOOLS = [
    {
        'name': 'read_docx',
        'description': '读取 Word 文档（.docx）的段落与表格文本，标题转为 markdown 层级。',
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string', 'description': 'docx 文件完整路径'},
            'max_chars': {'type': 'integer', 'description': '最大返回字符数，默认 8000'}},
            'required': ['path']},
        'handler': _h(lambda path, max_chars=8000: read_docx(path, max_chars)),
    },
    {
        'name': 'read_xlsx',
        'description': '读取 Excel 表格（.xlsx）指定工作表的内容（默认首个，上限 max_rows 行）。',
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string'},
            'sheet': {'type': 'string', 'description': '工作表名，默认活动表'},
            'max_rows': {'type': 'integer', 'description': '最多读取行数，默认 100'},
            'max_chars': {'type': 'integer', 'description': '最大返回字符数，默认 8000'}},
            'required': ['path']},
        'handler': _h(lambda path, sheet=None, max_rows=100, max_chars=8000:
                      read_xlsx(path, sheet, max_rows, max_chars)),
    },
    {
        'name': 'read_pptx',
        'description': '读取 PPT 演示文稿（.pptx）每页的标题与正文文本。',
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string'},
            'max_chars': {'type': 'integer', 'description': '最大返回字符数，默认 8000'}},
            'required': ['path']},
        'handler': _h(lambda path, max_chars=8000: read_pptx(path, max_chars)),
    },
]
