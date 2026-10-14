# -*- coding: utf-8 -*-
"""
mcp_servers/web.py · 网页抓取增强 MCP Server（本地自建）
----------------------------------------------------------------
工具：
- fetch_page_markdown：抓网页 → 智能正文提取 → 转 Markdown
  · 已知站点专用规则：微信公众号 / 知乎 / CSDN / 简书 / 掘金 / 豆瓣 / 头条 / B站
  · 通用网页：启发式正文提取（文本密度 + 段落密度评分）
  · HTML→Markdown：标题层级/列表/链接/图片/代码块/引用/表格
- web_search：DuckDuckGo HTML 端点搜索（免 key），返回标题/链接/摘要
- extract_links：提取页面全部链接（可按域名/关键词过滤）
注意：日志一律走 stderr，严禁 print 到 stdout（会污染 stdio JSON-RPC 流）。
"""
import re
import json
import urllib.request
import urllib.parse
from html.parser import HTMLParser

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

# ---------------- 抓取与解码 ----------------

def _fetch(url, timeout=30, max_bytes=6 * 1024 * 1024):
    if not re.match(r'^https?://', url or ''):
        raise ValueError('URL 必须以 http(s):// 开头')
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(max_bytes)
        charset = None
        try:
            charset = r.headers.get_content_charset()
        except Exception:
            pass
    if not charset:
        head = raw[:4096].decode('ascii', 'ignore')
        m = re.search(r'charset=["\']?([\w-]+)', head, re.I)
        charset = m.group(1) if m else 'utf-8'
    try:
        return raw.decode(charset, 'ignore')
    except (LookupError, UnicodeDecodeError):
        return raw.decode('utf-8', 'ignore')


# ---------------- HTML 结构解析 ----------------

class _Node(object):
    __slots__ = ('tag', 'attrs', 'children', 'parent', 'text')

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []
        self.parent = parent
        self.text = ''


class _DomBuilder(HTMLParser):
    """构建简易 DOM 树，自动跳过 script/style 等噪声标签。"""

    SKIP = {'script', 'style', 'noscript', 'svg', 'iframe', 'template', 'head', 'meta', 'link'}
    VOID = {'br', 'img', 'hr', 'input', 'source', 'area', 'base', 'col', 'embed', 'param', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node('#root', [], None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            return
        node = _Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in self.VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        if tag in self.SKIP:
            return
        self.cur.children.append(_Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        if tag in self.VOID or tag in self.SKIP:
            return
        node = self.cur
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.cur = node.parent

    def handle_data(self, data):
        self.cur.text += data


def _find_all(node, pred, out=None):
    if out is None:
        out = []
    if pred(node):
        out.append(node)
    for c in node.children:
        _find_all(c, pred, out)
    return out


def _find_first(node, pred):
    for n in _find_all(node, pred):
        return n
    return None


def _class_or_id(node, *keys):
    cid = (node.attrs.get('class', '') + ' ' + node.attrs.get('id', '')).lower()
    return any(k.lower() in cid for k in keys)


# ---------------- 已知站点正文规则 ----------------

def _wx_extract(dom):
    """微信公众号：标题 og:title/h1，正文 #js_content（可能被 visibility 隐藏但内容在 DOM）。"""
    title = ''
    h1 = _find_first(dom, lambda n: _class_or_id(n, 'rich_media_title'))
    if h1:
        title = _node_text(h1).strip()
    if not title:
        og = _find_first(dom, lambda n: n.tag == 'meta' and n.attrs.get('property') == 'og:title')
        if og:
            title = og.attrs.get('content', '')
    author = ''
    nm = _find_first(dom, lambda n: _class_or_id(n, 'js_name') or _class_or_id(n, 'profile_nickname'))
    if nm:
        author = _node_text(nm).strip()
    if not author:
        ma = _find_first(dom, lambda n: n.tag == 'meta' and n.attrs.get('name') == 'author')
        if ma:
            author = ma.attrs.get('content', '')
    content = _find_first(dom, lambda n: n.attrs.get('id') == 'js_content')
    return title, author, content


_KNOWN_SITES = [
    # (匹配函数, 标题选择, 作者选择, 正文选择)
    (lambda u: 'mp.weixin.qq.com' in u, 'rich_media_title', 'js_name|profile_nickname', 'js_content'),
    (lambda u: 'zhuanlan.zhihu.com' in u, 'Post-Title', 'AuthorInfo-name', 'RichText'),
    (lambda u: 'blog.csdn.net' in u, 'title-article', 'follow-nickName', 'article_content'),
    (lambda u: 'jianshu.com' in u, '_1RuRku', 'name', 'article'),
    (lambda u: 'juejin.cn' in u, 'article-title', 'username', 'article-content'),
    (lambda u: 'douban.com' in u, 'note-header', 'author', 'note'),
    (lambda u: 'toutiao.com' in u, 'article-title', 'name', 'articleContent'),
    (lambda u: 'bilibili.com' in u, 'basicInfo-title', 'up-name', 'basic-desc'),
]


def _known_extract(url, dom):
    for match, t_key, a_key, c_key in _KNOWN_SITES:
        if match(url):
            content = _find_first(dom, lambda n: _class_or_id(n, c_key))
            title = ''
            h = _find_first(dom, lambda n: _class_or_id(n, t_key))
            if h:
                title = _node_text(h).strip()
            if not title:
                og = _find_first(dom, lambda n: n.tag == 'meta' and n.attrs.get('property') == 'og:title')
                if og:
                    title = og.attrs.get('content', '')
            author = ''
            a = _find_first(dom, lambda n: _class_or_id(n, a_key))
            if a:
                author = _node_text(a).strip()
            return title, author, content
    return None


# ---------------- 通用启发式正文提取 ----------------

def _node_text(node):
    parts = []
    _collect_text(node, parts)
    return ''.join(parts)


def _collect_text(node, parts):
    if node.tag == 'br':
        parts.append('\n')
    if node.text:
        parts.append(node.text)
    for c in node.children:
        _collect_text(c, parts)


def _heuristic_extract(dom):
    """通用正文提取：对容器按 文本长度 + <p> 密度 - 链接密度 打分，取最高分。"""
    candidates = _find_all(dom, lambda n: n.tag in ('div', 'article', 'section', 'main', 'td'))
    best, best_score = None, -1.0
    for n in candidates:
        if _find_first(n, lambda x: x is not n and x.tag in ('div', 'article', 'section', 'main')) is not None \
                and len(_find_all(n, lambda x: x.tag == 'p')) < 3:
            continue
        text = _node_text(n)
        tl = len(text.strip())
        if tl < 100:
            continue
        ps = len(_find_all(n, lambda x: x.tag == 'p'))
        links = len(_find_all(n, lambda x: x.tag == 'a'))
        link_text = sum(len(_node_text(a).strip()) for a in _find_all(n, lambda x: x.tag == 'a'))
        link_density = link_text / max(tl, 1)
        score = tl * (1 + ps * 0.1) * (1 - min(link_density, 0.8))
        if score > best_score:
            best, best_score = n, score
    title = ''
    og = _find_first(dom, lambda n: n.tag == 'meta' and n.attrs.get('property') == 'og:title')
    if og:
        title = og.attrs.get('content', '')
    if not title:
        t = _find_first(dom, lambda n: n.tag == 'title')
        if t:
            title = _node_text(t).strip()
    return title, '', best


# ---------------- HTML → Markdown ----------------

class _MdConverter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.list_stack = []   # 'ul' | 'ol'
        self.pre = 0
        self.link_href = ''
        self.skip = 0
        self.table_row = []
        self.in_table = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
            return
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.out.append('\n\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'p':
            self.out.append('\n\n')
        elif tag == 'br':
            self.out.append('  \n')
        elif tag == 'hr':
            self.out.append('\n\n---\n\n')
        elif tag in ('strong', 'b'):
            self.out.append('**')
        elif tag in ('em', 'i'):
            self.out.append('*')
        elif tag == 'code' and not self.pre:
            self.out.append('`')
        elif tag == 'pre':
            self.pre += 1
            self.out.append('\n\n```\n')
        elif tag == 'blockquote':
            self.out.append('\n\n> ')
        elif tag == 'ul':
            self.list_stack.append('ul')
            self.out.append('\n')
        elif tag == 'ol':
            self.list_stack.append('ol')
            self.out.append('\n')
        elif tag == 'li':
            self.out.append('\n' + ('- ' if self.list_stack[-1:] == ['ul'] else '1. '))
        elif tag == 'a':
            self.link_href = a.get('href', '')
            self.out.append('[')
        elif tag == 'img':
            src = a.get('src') or a.get('data-src') or ''
            alt = a.get('alt', '')
            if src:
                self.out.append('\n![%s](%s)\n' % (alt, src))
        elif tag == 'table':
            self.in_table += 1
        elif tag == 'tr':
            self.table_row = []
        elif tag == 'td':
            self.table_row.append('| ')
        elif tag == 'th':
            self.table_row.append('| ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            if self.skip:
                self.skip -= 1
            return
        if self.skip:
            return
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.out.append('\n')
        elif tag in ('strong', 'b'):
            self.out.append('**')
        elif tag in ('em', 'i'):
            self.out.append('*')
        elif tag == 'code' and not self.pre:
            self.out.append('`')
        elif tag == 'pre':
            if self.pre:
                self.pre -= 1
            self.out.append('\n```\n')
        elif tag in ('ul', 'ol'):
            if self.list_stack:
                self.list_stack.pop()
            self.out.append('\n')
        elif tag == 'a':
            href = self.link_href
            self.link_href = ''
            if href and href.startswith('/'):
                href = 'https://mp.weixin.qq.com' + href if False else href
            self.out.append('](%s)' % href if href else ']')
        elif tag == 'td' or tag == 'th':
            self.table_row.append(' ')
        elif tag == 'tr':
            if self.table_row:
                self.out.append('\n' + ''.join(self.table_row).rstrip() + ' |\n')
            self.table_row = []
        elif tag == 'table':
            if self.in_table:
                self.in_table -= 1

    def handle_data(self, data):
        if self.skip:
            return
        if self.pre:
            self.out.append(data)
        else:
            t = re.sub(r'\s+', ' ', data)
            if t.strip():
                self.out.append(t)

    def result(self):
        md = ''.join(self.out)
        md = re.sub(r'\n{3,}', '\n\n', md)
        md = re.sub(r'[ \t]+\n', '\n', md)
        return md.strip()


def _html_to_md(html):
    c = _MdConverter()
    try:
        c.feed(html)
    except Exception:
        pass
    return c.result()


def _node_to_html(node):
    """把 DOM 子树序列化回 HTML（供 markdown 转换器复用）。"""
    parts = []
    _serialize(node, parts)
    return ''.join(parts)


def _serialize(node, parts):
    if node.tag == '#root':
        for c in node.children:
            _serialize(c, parts)
        return
    attrs = ''.join(' %s="%s"' % (k, v) for k, v in node.attrs.items() if v)
    if node.tag in ('br', 'img', 'hr'):
        parts.append('<%s%s>' % (node.tag, attrs))
        return
    parts.append('<%s%s>' % (node.tag, attrs))
    if node.text:
        parts.append(node.text)
    for c in node.children:
        _serialize(c, parts)
    parts.append('</%s>' % node.tag)


# ---------------- 工具实现 ----------------

def fetch_page_markdown(url, max_chars=12000):
    html = _fetch(url)
    dom = _DomBuilder()
    try:
        dom.feed(html)
    except Exception:
        pass
    known = _known_extract(url, dom.root)
    if known and known[2] is not None:
        title, author, content_node = known
    elif 'mp.weixin.qq.com' in url:
        title, author, content_node = _wx_extract(dom.root)
    else:
        title, author, content_node = _heuristic_extract(dom.root)

    if content_node is None:
        # 兜底：整页文本
        text = re.sub(r'<(script|style)[\s\S]*?</\1>', ' ', html, flags=re.I)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return {'title': title or url, 'url': url, 'author': author or '',
                'site': 'generic', 'markdown': text[:max_chars], 'note': '未能定位正文容器，返回全文文本'}

    body_html = _node_to_html(content_node)
    md = _html_to_md(body_html)
    if len(md) > max_chars:
        md = md[:max_chars] + '\n\n……（正文过长已截断，完整内容 %d 字符）' % len(md)
    return {'title': title or url, 'url': url, 'author': author or '',
            'site': _site_of(url), 'markdown': md}


def _site_of(url):
    if 'mp.weixin.qq.com' in url:
        return 'weixin'
    if 'zhuanlan.zhihu.com' in url:
        return 'zhihu'
    if 'blog.csdn.net' in url:
        return 'csdn'
    if 'juejin.cn' in url:
        return 'juejin'
    return 'web'


def _bing_search(query, num):
    q = urllib.parse.quote(query or '')
    html = _fetch('https://www.bing.com/search?q=%s&setlang=zh-CN&count=20' % q, timeout=25)
    dom = _DomBuilder()
    try:
        dom.feed(html)
    except Exception:
        pass
    results = []
    for blk in _find_all(dom.root, lambda n: 'b_algo' in n.attrs.get('class', '')):
        h = _find_first(blk, lambda n: n.tag == 'h2')
        a = _find_first(blk, lambda n: n.tag == 'a')
        if not h or not a:
            continue
        title = _node_text(h).strip()
        href = a.attrs.get('href', '')
        cap = _find_first(blk, lambda n: 'b_caption' in n.attrs.get('class', '')
                          or _class_or_id(n, 'b_lineclamp'))
        snippet = _node_text(cap).strip()[:300] if cap else ''
        if title and href.startswith('http'):
            results.append({'title': title, 'url': href, 'snippet': snippet})
        if len(results) >= num:
            break
    return results


def _ddg_search(query, num):
    q = urllib.parse.quote(query or '')
    html = _fetch('https://html.duckduckgo.com/html/?q=%s' % q, timeout=25)
    dom = _DomBuilder()
    try:
        dom.feed(html)
    except Exception:
        pass
    results = []
    for a in _find_all(dom.root, lambda n: n.tag == 'a' and 'result__a' in n.attrs.get('class', '')):
        title = _node_text(a).strip()
        href = a.attrs.get('href', '')
        m = re.search(r'uddg=([^&]+)', href)
        if m:
            href = urllib.parse.unquote(m.group(1))
        if title and href.startswith('http'):
            results.append({'title': title, 'url': href})
        if len(results) >= num:
            break
    snippets = []
    for s in _find_all(dom.root, lambda n: 'result__snippet' in n.attrs.get('class', '')):
        snippets.append(_node_text(s).strip())
    for i, r in enumerate(results):
        if i < len(snippets):
            r['snippet'] = snippets[i][:300]
    return results


def web_search(query, num=8):
    results, source, note = [], '', ''
    try:
        results = _bing_search(query, num)
        source = 'bing'
    except Exception as e:
        note = 'Bing 失败：%s' % str(e)[:80]
    if not results:
        try:
            results = _ddg_search(query, num)
            source = 'duckduckgo'
        except Exception as e:
            note += '；DuckDuckGo 失败：%s' % str(e)[:80]
    if not results:
        return {'query': query, 'results': [], 'note': note or '未解析到结果'}
    return {'query': query, 'source': source, 'results': results}


def extract_links(url, contains=None):
    html = _fetch(url, timeout=25)
    dom = _DomBuilder()
    try:
        dom.feed(html)
    except Exception:
        pass
    base = urllib.parse.urlparse(url)
    base_host = base.netloc.lower()
    seen, links = set(), []
    for a in _find_all(dom.root, lambda n: n.tag == 'a'):
        href = (a.attrs.get('href') or '').strip()
        text = _node_text(a).strip()
        if not href or href.startswith('#') or href.startswith('javascript'):
            continue
        if href.startswith('/'):
            href = '%s://%s%s' % (base.scheme, base.netloc, href)
        if not href.startswith('http'):
            continue
        host = urllib.parse.urlparse(href).netloc.lower()
        if host == base_host:
            kind = 'internal'
        else:
            kind = 'external'
        if contains and contains.lower() not in (href + text).lower():
            continue
        if href in seen:
            continue
        seen.add(href)
        links.append({'text': text[:80], 'url': href, 'type': kind})
        if len(links) >= 200:
            break
    return {'url': url, 'count': len(links), 'links': links}


def _h(fn):
    return lambda args: fn(**args)


TOOLS = [
    {
        'name': 'fetch_page_markdown',
        'description': '抓取网页并转为 Markdown（智能正文提取）。支持微信公众号/知乎/CSDN/掘金/简书/豆瓣/头条/B站专用规则，其他网页用启发式提取；保留标题层级、列表、链接、图片、代码块。',
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string', 'description': '网页完整 URL'},
            'max_chars': {'type': 'integer', 'description': '返回 markdown 最大字符数，默认 12000'}},
            'required': ['url']},
        'handler': _h(lambda url, max_chars=12000: fetch_page_markdown(url, max_chars)),
    },
    {
        'name': 'web_search',
        'description': '搜索引擎查询（DuckDuckGo，免 key），返回标题/链接/摘要列表。用于查资料、找官网。',
        'inputSchema': {'type': 'object', 'properties': {
            'query': {'type': 'string', 'description': '搜索关键词'},
            'num': {'type': 'integer', 'description': '结果条数，默认 8'}},
            'required': ['query']},
        'handler': _h(lambda query, num=8: web_search(query, num)),
    },
    {
        'name': 'extract_links',
        'description': '提取网页全部链接（标注站内/站外，可按关键词过滤）。',
        'inputSchema': {'type': 'object', 'properties': {
            'url': {'type': 'string'},
            'contains': {'type': 'string', 'description': '可选，只保留 URL 或文本包含该关键词的链接'}},
            'required': ['url']},
        'handler': _h(lambda url, contains=None: extract_links(url, contains)),
    },
]
