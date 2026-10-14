# -*- coding: utf-8 -*-
"""
mcp_servers/files.py · 文件系统增强 MCP Server（本地自建）
----------------------------------------------------------------
工具：
- search_files：递归搜索文件名/内容（限定用户目录，禁系统目录）
- file_hash：计算文件 MD5/SHA1/SHA256
- tree_directory：目录树（可限深度/文件数）
"""
import os
import hashlib
import fnmatch

_HOME = os.path.expanduser('~')
_SYS_DIRS = ('c:\\windows', 'c:\\program files', 'c:\\program files (x86)', 'c:\\programdata')
_TEXT_EXTS = ('.txt', '.md', '.json', '.csv', '.log', '.py', '.js', '.html', '.css', '.xml',
              '.yaml', '.yml', '.ini', '.cfg', '.bat', '.ps1', '.mdx', '.htm', '.tsv', '.rst')


def _guard(path):
    p = os.path.abspath(os.path.expanduser(str(path)))
    low = p.lower()
    for bad in _SYS_DIRS:
        if low.startswith(bad):
            raise PermissionError('系统目录禁止访问：' + p)
    return p


def search_files(keyword, path=None, search_content=False, max_results=30):
    root = _guard(path or _HOME)
    kw = (keyword or '').lower()
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        # 剪枝：跳过隐藏/缓存/大型库目录
        dirnames[:] = [d for d in dirnames if not d.startswith('.')
                       and d not in ('node_modules', '__pycache__', 'AppData', 'venv', '.venv')]
        for name in filenames:
            if kw in name.lower():
                fp = os.path.join(dirpath, name)
                hits.append({'name': name, 'path': fp,
                             'size_kb': round(os.path.getsize(fp) / 1024, 1)})
                if len(hits) >= max_results:
                    return {'root': root, 'keyword': keyword, 'mode': 'name', 'count': len(hits), 'hits': hits}
    if not search_content:
        return {'root': root, 'keyword': keyword, 'mode': 'name', 'count': 0, 'hits': []}
    # 内容搜索：仅文本类文件
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')
                       and d not in ('node_modules', '__pycache__', 'AppData', 'venv', '.venv')]
        for name in filenames:
            if not name.lower().endswith(_TEXT_EXTS):
                continue
            fp = os.path.join(dirpath, name)
            try:
                if os.path.getsize(fp) > 2 * 1024 * 1024:
                    continue
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    for ln, line in enumerate(f, 1):
                        if kw in line.lower():
                            hits.append({'name': name, 'path': fp, 'line': ln,
                                         'text': line.strip()[:150]})
                            break
            except Exception:
                continue
            if len(hits) >= max_results:
                break
        if len(hits) >= max_results:
            break
    return {'root': root, 'keyword': keyword, 'mode': 'content', 'count': len(hits), 'hits': hits}


def file_hash(path, algo='sha256'):
    p = _guard(path)
    if not os.path.isfile(p):
        raise FileNotFoundError('文件不存在：' + p)
    h = hashlib.new(algo)
    with open(p, 'rb') as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return {'path': p, 'algo': algo, 'hash': h.hexdigest(),
            'size_kb': round(os.path.getsize(p) / 1024, 1)}


def tree_directory(path=None, max_depth=3, max_entries=300):
    root = _guard(path or _HOME)
    entries = []
    truncated = [False]

    def walk(d, depth, prefix):
        if depth > max_depth or len(entries) >= max_entries:
            truncated[0] = True
            return
        try:
            names = sorted(os.listdir(d))
        except Exception:
            return
        for n in names:
            if len(entries) >= max_entries:
                truncated[0] = True
                return
            fp = os.path.join(d, n)
            isdir = os.path.isdir(fp)
            entries.append({'depth': depth, 'dir': isdir,
                            'name': prefix + n + ('/' if isdir else ''),
                            'size_kb': None if isdir else round(os.path.getsize(fp) / 1024, 1)})
            if isdir and not n.startswith('.') and n not in ('node_modules', '__pycache__', 'AppData'):
                walk(fp, depth + 1, prefix + n + '/')

    walk(root, 1, '')
    return {'root': root, 'count': len(entries), 'truncated': truncated[0], 'entries': entries}


def _h(fn):
    return lambda args: fn(**args)


TOOLS = [
    {
        'name': 'search_files',
        'description': '递归搜索文件：默认按文件名匹配；search_content=true 时同时搜索文本类文件内容（返回行号与内容片段）。',
        'inputSchema': {'type': 'object', 'properties': {
            'keyword': {'type': 'string', 'description': '文件名或内容关键词'},
            'path': {'type': 'string', 'description': '搜索根目录，默认用户主目录'},
            'search_content': {'type': 'boolean', 'description': '是否搜文件内容，默认 false'},
            'max_results': {'type': 'integer', 'description': '最多返回条数，默认 30'}},
            'required': ['keyword']},
        'handler': _h(lambda keyword, path=None, search_content=False, max_results=30:
                      search_files(keyword, path, search_content, max_results)),
    },
    {
        'name': 'file_hash',
        'description': '计算文件的 MD5/SHA1/SHA256 哈希值（校验文件完整性、比对版本）。',
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string'},
            'algo': {'type': 'string', 'description': 'md5/sha1/sha256，默认 sha256'}},
            'required': ['path']},
        'handler': _h(lambda path, algo='sha256': file_hash(path, algo)),
    },
    {
        'name': 'tree_directory',
        'description': '输出目录树结构（可限深度），快速了解一个文件夹里有什么。',
        'inputSchema': {'type': 'object', 'properties': {
            'path': {'type': 'string', 'description': '目录路径，默认用户主目录'},
            'max_depth': {'type': 'integer', 'description': '最大深度，默认 3'},
            'max_entries': {'type': 'integer', 'description': '最大条目数，默认 300'}},
            'required': []},
        'handler': _h(lambda path=None, max_depth=3, max_entries=300:
                      tree_directory(path, max_depth, max_entries)),
    },
]
