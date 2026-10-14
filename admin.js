/**
 * admin.js · v3.5.0 管理后台逻辑（配 admin.html，路由 /admin）
 * ------------------------------------------------------------------
 * 八分区：模型池 / 人设 GPT / 首页卡片 / 对话与朗读 / 外观品牌 / MCP 工具 / 系统 / 账号。
 * token 存 sessionStorage（与前台同源共享）；Key 只写不读、编辑留空 = 不改。
 */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var TK = 'RC_ADMIN_TOKEN';
  var token = sessionStorage.getItem(TK) || '';
  var cache = { providers: [], defaultId: '', voices: [] };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function toast(msg) {
    var t = $('#toast'); t.textContent = msg; t.classList.add('show');
    clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove('show'); }, 2600);
  }
  function confirmDlg(opt) {
    return new Promise(function (resolve) {
      var d = document.createElement('dialog');
      d.style.cssText = 'border:none;border-radius:12px;padding:20px;max-width:380px;background:var(--card);color:var(--text)';
      d.innerHTML = '<h3 style="font-size:15px;margin-bottom:8px">' + esc(opt.title) + '</h3>'
        + (opt.desc ? '<p style="font-size:13px;color:var(--text-2);margin-bottom:16px">' + esc(opt.desc) + '</p>' : '')
        + '<div style="display:flex;justify-content:flex-end;gap:8px">'
        + '<button class="btn ghost sm" data-a="no">取消</button>'
        + '<button class="btn sm ' + (opt.danger ? 'danger' : '') + '" data-a="yes">' + esc(opt.okText || '确定') + '</button></div>';
      document.body.appendChild(d);
      d.onclick = function (e) {
        var a = e.target && e.target.dataset && e.target.dataset.a;
        if (!a) return;
        d.onclose = null; d.close(); resolve(a === 'yes');
      };
      d.onclose = function () { resolve(false); };
      d.addEventListener('close', function () { d.remove(); }, { once: true });
      d.showModal();
    });
  }

  function api(path, opts) {
    opts = opts || {};
    return fetch('/api/admin/' + path, {
      method: opts.method || 'GET',
      headers: { 'content-type': 'application/json', 'authorization': 'Bearer ' + token },
      body: opts.body ? JSON.stringify(opts.body) : undefined
    }).then(function (r) {
      if (r.status === 401) { signOut(); throw new Error('登录已过期，请重新登录'); }
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new Error(d.error || ('请求失败 ' + r.status));
        return d;
      });
    });
  }

  /* ================= 登录 / 登出 / 导航 ================= */
  $('#gateCard').addEventListener('submit', function (e) {
    e.preventDefault();
    var name = $('#admName').value.trim(), pw = $('#admPass').value;
    $('#gateErr').textContent = '';
    $('#admSubmit').disabled = true;
    fetch('/api/admin/login', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ name: name, password: pw })
    }).then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (d) {
        if (d.token) {
          token = d.token;
          sessionStorage.setItem(TK, token);
          $('#admPass').value = '';
          enter(d.name);
        } else {
          $('#gateErr').textContent = d.error || '登录失败';
        }
      })
      .catch(function () { $('#gateErr').textContent = '网络错误，请重试'; })
      .finally(function () { $('#admSubmit').disabled = false; });
  });

  function enter(name) {
    $('#gate').style.display = 'none';
    $('#app').classList.add('show');
    $('#admLabel').textContent = name ? ('· ' + name) : '';
    loadPage('models');
  }
  function signOut() {
    token = '';
    sessionStorage.removeItem(TK);
    $('#app').classList.remove('show');
    $('#gate').style.display = '';
  }
  $('#btnOut').addEventListener('click', signOut);

  if (token) {
    api('session').then(function () { enter(null); }).catch(function () { signOut(); });
  }

  var loadedPages = {};
  document.querySelectorAll('#sideNav button').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('#sideNav button').forEach(function (x) { x.classList.toggle('on', x === b); });
      var page = b.dataset.page;
      document.querySelectorAll('.page').forEach(function (p) { p.classList.toggle('on', p.id === 'page-' + page); });
      loadPage(page);
    });
  });
  function loadPage(page) {
    if (page === 'models') loadModels();
    else if (page === 'personas') loadPersonas();
    else if (page === 'starters') loadStarters();
    else if (page === 'dialog') loadDialog();
    else if (page === 'appearance') loadAppearance();
    else if (page === 'mcp') loadMcp();
    else if (page === 'system') loadSystem();
    else if (page === 'account') loadAccount();
    loadedPages[page] = true;
  }

  /* ================= ① 模型池 ================= */
  function loadModels() {
    api('models').then(function (d) {
      cache.providers = d.models || [];
      cache.defaultId = d.defaultProviderId || '';
      renderModels();
    }).catch(function (e) { $('#pvList').innerHTML = '<div class="empty">' + esc(e.message) + '</div>'; });
  }
  function renderModels() {
    var box = $('#pvList');
    if (!cache.providers.length) {
      box.innerHTML = '<div class="empty">模型池是空的，点右上角「新增模型」添加一个</div>';
      return;
    }
    box.innerHTML = '';
    cache.providers.forEach(function (p) { box.appendChild(modelCard(p)); });
  }
  function modelCard(p) {
    var el = document.createElement('div');
    el.className = 'card' + (p.enabled ? '' : ' off');
    var badges = '';
    if (p.builtin) badges += '<span class="badge builtin">内置</span>';
    badges += '<span class="badge ' + (p.enabled ? 'on">启用中' : 'off">已停用') + '</span>';
    if (p.id === cache.defaultId) badges += '<span class="badge def">默认</span>';
    el.innerHTML = '<div style="min-width:0"><div class="nm">' + esc(p.name) + badges + '</div>'
      + '<div class="meta"><code>' + esc(p.model) + '</code> · ' + esc(p.base_url) + '</div>'
      + '<div class="meta">Key ' + esc(p.apiKeyMasked || '未设置') + ' · 上下文 '
      + (p.max_input_tokens || '未设') + ' · 输出 ' + (p.max_output_tokens || '未设') + '</div></div>'
      + '<div class="ops"></div>';
    var ops = el.querySelector('.ops');
    function btn(text, cls, fn) {
      var b = document.createElement('button');
      b.className = 'btn ghost sm' + (cls ? ' ' + cls : '');
      b.textContent = text;
      b.onclick = fn;
      ops.appendChild(b);
    }
    if (p.id !== cache.defaultId) btn('设为默认', '', function () {
      api('models/' + p.id + '/default', { method: 'POST' }).then(function () {
        toast('已设为默认模型'); loadModels();
      }).catch(function (e) { toast(e.message); });
    });
    btn(p.enabled ? '停用' : '启用', '', function () {
      api('models/' + p.id + '/' + (p.enabled ? 'disable' : 'enable'), { method: 'POST' })
        .then(function () { toast(p.enabled ? '已停用' : '已启用，前台立即可选'); loadModels(); })
        .catch(function (e) { toast(e.message); });
    });
    btn('测试', '', function () {
      toast('测试中…');
      api('models/' + p.id + '/test', { method: 'POST' }).then(function (r) {
        toast(r.ok ? ('连通正常（' + r.ms + 'ms）') : ('不通：' + (r.error || r.status || '未知')));
      }).catch(function (e) { toast(e.message); });
    });
    btn('编辑', '', function () { openDlg(p); });
    if (!p.builtin) btn('删除', 'danger', function () {
      confirmDlg({ title: '删除模型「' + p.name + '」？', desc: '删除后前台不可再选。', okText: '删除', danger: true })
        .then(function (ok) {
          if (!ok) return;
          api('models/' + p.id, { method: 'DELETE' }).then(function () {
            toast('已删除'); loadModels();
          }).catch(function (e) { toast(e.message); });
        });
    });
    return el;
  }
  var editingId = null;
  function openDlg(p) {
    editingId = p ? p.id : null;
    $('#pvDlgTitle').textContent = p ? '编辑模型' : '新增模型';
    $('#fName').value = p ? p.name : '';
    $('#fBase').value = p ? p.base_url : '';
    $('#fKey').value = '';
    $('#fKeyHint').textContent = p ? '留空表示不修改（当前 ' + (p.apiKeyMasked || '未设置') + '）' : '';
    $('#fModel').value = p ? p.model : '';
    $('#fMaxIn').value = p && p.max_input_tokens ? p.max_input_tokens : '';
    $('#fMaxOut').value = p && p.max_output_tokens ? p.max_output_tokens : '';
    $('#fTemp').value = p && p.temperature != null ? p.temperature : '';
    $('#pvMask').classList.add('open');
  }
  $('#btnAdd').addEventListener('click', function () { openDlg(null); });
  $('#pvCancel').addEventListener('click', function () { $('#pvMask').classList.remove('open'); });
  $('#pvMask').addEventListener('click', function (e) { if (e.target === this) this.classList.remove('open'); });
  $('#pvSave').addEventListener('click', function () {
    var body = {
      name: $('#fName').value.trim(), baseUrl: $('#fBase').value.trim(),
      apiKey: $('#fKey').value.trim(), model: $('#fModel').value.trim(),
      maxInputTokens: $('#fMaxIn').value ? Number($('#fMaxIn').value) : null,
      maxOutputTokens: $('#fMaxOut').value ? Number($('#fMaxOut').value) : null,
      temperature: $('#fTemp').value !== '' ? Number($('#fTemp').value) : null
    };
    var req = editingId
      ? api('models/' + editingId, { method: 'PUT', body: body })
      : api('models', { method: 'POST', body: body });
    req.then(function () {
      $('#pvMask').classList.remove('open');
      toast(editingId ? '已保存' : '已添加，前台立即可选');
      loadModels();
    }).catch(function (e) { toast(e.message); });
  });

  /* ============ 行编辑通用（人设/卡片/MCP 列表：编辑中副本，保存才落库） ============ */
  function bindRowInputs(el, rows, i, repaint) {
    el.querySelectorAll('[data-f]').forEach(function (inp) {
      var f = inp.dataset.f;
      var ev = (inp.type === 'checkbox') ? 'change' : 'input';
      inp.addEventListener(ev, function () {
        rows[i][f] = (inp.type === 'checkbox') ? inp.checked : inp.value;
      });
    });
    el.querySelectorAll('button[data-a]').forEach(function (b) {
      b.addEventListener('click', function () {
        var a = b.dataset.a;
        if (a === 'del') rows.splice(i, 1);
        else {
          var j = a === 'up' ? i - 1 : i + 1;
          if (rows[j] !== undefined) { var t = rows[i]; rows[i] = rows[j]; rows[j] = t; }
        }
        repaint();
      });
    });
  }

  /* ================= ② 人设 GPT ================= */
  var psRows = [];
  function loadPersonas() {
    api('settings').then(function (s) {
      psRows = (s.personas || []).map(function (p) { return Object.assign({}, p); });
      psPaint();
    }).catch(function (e) { $('#psList').innerHTML = '<div class="empty">' + esc(e.message) + '</div>'; });
  }
  function psPaint() {
    var box = $('#psList');
    box.innerHTML = psRows.length ? '' : '<div class="empty">还没有人设，点「新增人设」创建</div>';
    psRows.forEach(function (p, i) {
      var el = document.createElement('div');
      el.className = 'row-edit' + (p.enabled ? '' : ' off');
      el.innerHTML = '<div class="row-grid">'
        + '<input class="av" type="text" data-f="avatar" maxlength="4" title="图标（emoji）" value="' + esc(p.avatar || '') + '" placeholder="🤖">'
        + '<input type="text" data-f="name" maxlength="24" placeholder="显示名" value="' + esc(p.name || '') + '">'
        + '<input type="text" data-f="desc" maxlength="60" placeholder="一句话说明（显示在选择卡片上）" value="' + esc(p.desc || '') + '"></div>'
        + '<textarea data-f="prompt" placeholder="人设系统提示词（最多 3000 字）">' + esc(p.prompt || '') + '</textarea>'
        + '<div class="row-foot">'
        + '<label class="sw"><input type="checkbox" data-f="enabled" ' + (p.enabled ? 'checked' : '') + '>'
        + '<span class="sw-trk"><span class="sw-thb"></span></span>启用</label>'
        + '<span class="num-wrap">顺序<input data-f="sort" type="number" min="0" max="999" value="' + (p.sort || 0) + '"></span>'
        + (p.builtin ? '<span class="badge preset">预置</span>' : '')
        + '<span class="grow"></span>'
        + '<button class="ib" data-a="up" title="上移" ' + (i === 0 ? 'disabled' : '') + '>↑</button>'
        + '<button class="ib" data-a="down" title="下移" ' + (i === psRows.length - 1 ? 'disabled' : '') + '>↓</button>'
        + '<button class="ib del" data-a="del" title="删除">✕</button></div>';
      bindRowInputs(el, psRows, i, psPaint);
      box.appendChild(el);
    });
  }
  $('#psAdd').addEventListener('click', function () {
    psRows.push({ id: '', name: '', desc: '', avatar: '🤖', prompt: '', enabled: true, sort: psRows.length, builtin: false });
    psPaint();
  });
  $('#psSave').addEventListener('click', function () {
    var bad = psRows.filter(function (p) { return !(p.name || '').trim(); }).length;
    if (bad) { toast(bad + ' 个人设没填名字，补上再保存'); return; }
    api('personas', { method: 'POST', body: { personas: psRows } }).then(function (r) {
      toast('人设已保存（' + r.count + ' 个），前台立即生效');
      loadPersonas();
    }).catch(function (e) { toast(e.message); });
  });

  /* ================= ③ 首页卡片 ================= */
  var stRows = [];
  function loadStarters() {
    api('settings').then(function (s) {
      stRows = (s.starters || []).map(function (x) { return Object.assign({}, x); });
      stPaint();
    }).catch(function (e) { $('#stList').innerHTML = '<div class="empty">' + esc(e.message) + '</div>'; });
  }
  function stPaint() {
    var box = $('#stList');
    box.innerHTML = stRows.length ? '' : '<div class="empty">还没有卡片，点「新增卡片」创建</div>';
    stRows.forEach(function (s0, i) {
      var el = document.createElement('div');
      el.className = 'row-edit' + (s0.enabled ? '' : ' off');
      el.innerHTML = '<div class="row-grid2">'
        + '<input type="text" data-f="title" maxlength="24" placeholder="卡片标题" value="' + esc(s0.title || '') + '">'
        + '<label class="sw"><input type="checkbox" data-f="enabled" ' + (s0.enabled ? 'checked' : '') + '>'
        + '<span class="sw-trk"><span class="sw-thb"></span></span>启用</label></div>'
        + '<textarea data-f="prompt" placeholder="点击后填入输入框的提示词" style="min-height:48px">' + esc(s0.prompt || '') + '</textarea>'
        + '<div class="row-foot">'
        + '<span class="num-wrap">顺序<input data-f="sort" type="number" min="0" max="999" value="' + (s0.sort || 0) + '"></span>'
        + '<span class="grow"></span>'
        + '<button class="ib" data-a="up" title="上移" ' + (i === 0 ? 'disabled' : '') + '>↑</button>'
        + '<button class="ib" data-a="down" title="下移" ' + (i === stRows.length - 1 ? 'disabled' : '') + '>↓</button>'
        + '<button class="ib del" data-a="del" title="删除">✕</button></div>';
      bindRowInputs(el, stRows, i, stPaint);
      box.appendChild(el);
    });
  }
  $('#stAdd').addEventListener('click', function () {
    if (stRows.length >= 12) { toast('最多 12 张，先删掉几张'); return; }
    stRows.push({ id: '', title: '', prompt: '', enabled: true, sort: stRows.length });
    stPaint();
  });
  $('#stSave').addEventListener('click', function () {
    api('starters', { method: 'POST', body: { starters: stRows } }).then(function (r) {
      toast('首页卡片已保存（' + r.count + ' 张），前台立即生效');
      loadStarters();
    }).catch(function (e) { toast(e.message); });
  });

  /* ================= ④ 对话与朗读 ================= */
  function loadDialog() {
    Promise.all([api('settings'), fetch('/api/tts/voices').then(function (r) { return r.json(); })])
      .then(function (rs) {
        var s = rs[0] || {};
        $('#dSys').value = s.sysExtra || '';
        $('#dTone').value = s.tone || 'professional';
        $('#dTemp').value = s.temperature != null ? s.temperature : '';
        $('#dMax').value = s.maxTokens != null ? s.maxTokens : '';
        cache.voices = rs[1].voices || [];
        var sel = $('#vSel');
        var groups = {};
        cache.voices.forEach(function (v) { (groups[v.group || '其他'] = groups[v.group || '其他'] || []).push(v); });
        sel.innerHTML = '';
        Object.keys(groups).forEach(function (g) {
          var og = document.createElement('optgroup'); og.label = g;
          groups[g].forEach(function (v) {
            var o = document.createElement('option');
            o.value = v.id; o.textContent = v.name;
            og.appendChild(o);
          });
          sel.appendChild(og);
        });
        var cur = s.ttsVoice;
        if (!cache.voices.some(function (v) { return v.id === cur; })) cur = cache.voices.length ? cache.voices[0].id : cur;
        sel.value = cur;
        paintVoiceMeta(cur);
      }).catch(function (e) { $('#voiceMeta').textContent = '加载失败：' + e.message; });
  }
  function paintVoiceMeta(id) {
    var v = cache.voices.filter(function (x) { return x.id === id; })[0];
    $('#voiceMeta').textContent = v ? (v.group + ' · ' + v.id) : (id || '未设置');
  }
  $('#vSel').addEventListener('change', function () {
    api('settings', { method: 'POST', body: { ttsVoice: $('#vSel').value } }).then(function () {
      paintVoiceMeta($('#vSel').value);
      toast('默认音色已保存');
    }).catch(function (e) { toast(e.message); });
  });
  var tryAudio = null, tryCtrl = null;
  $('#vTry').addEventListener('click', function () {
    if (tryCtrl) { tryCtrl.abort(); tryCtrl = null; return; }
    tryCtrl = new AbortController();
    $('#voiceMeta').textContent = '试听中…';
    fetch('/api/tts?text=' + encodeURIComponent('你好，这是后台默认音色的试听效果。')
      + '&voice=' + encodeURIComponent($('#vSel').value), { signal: tryCtrl.signal })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.blob(); })
      .then(function (blob) {
        if (!tryAudio) tryAudio = new Audio();
        tryAudio.src = URL.createObjectURL(blob);
        tryAudio.onended = function () { tryCtrl = null; URL.revokeObjectURL(tryAudio.src); paintVoiceMeta($('#vSel').value); };
        tryAudio.onerror = function () { tryCtrl = null; paintVoiceMeta($('#vSel').value); };
        return tryAudio.play();
      })
      .catch(function (err) {
        tryCtrl = null; paintVoiceMeta($('#vSel').value);
        if (err && err.name === 'AbortError') return;
        toast('试听失败：' + (err.message || err));
      });
  });
  $('#dlgSave').addEventListener('click', function () {
    api('settings', { method: 'POST', body: {
      sysExtra: $('#dSys').value, tone: $('#dTone').value,
      temperature: $('#dTemp').value !== '' ? Number($('#dTemp').value) : null,
      maxTokens: $('#dMax').value !== '' ? Number($('#dMax').value) : null
    } }).then(function () { toast('对话默认已保存，下一条消息起生效'); })
      .catch(function (e) { toast(e.message); });
  });

  /* ================= ⑤ 外观品牌 ================= */
  function loadAppearance() {
    api('settings').then(function (s) {
      $('#aName').value = s.appName || '';
      $('#aTheme').value = s.theme || 'system';
      $('#aAccent').value = s.accent || '#19c37d';
    }).catch(function (e) { toast(e.message); });
  }
  $('#apSave').addEventListener('click', function () {
    api('settings', { method: 'POST', body: {
      appName: $('#aName').value.trim(), theme: $('#aTheme').value, accent: $('#aAccent').value
    } }).then(function () { toast('外观已保存，刷新前台生效'); })
      .catch(function (e) { toast(e.message); });
  });

  /* ================= ⑥ MCP 工具 ================= */
  var bmState = {}, rmRows = [];
  var BM_LABELS = { web: '🌐 网页抓取/搜索', files: '📁 文件搜索/哈希', office: '📝 Word/Excel/PPT 读写',
                    dev: '🔧 JSON/编解码/正则', pdf: '📄 PDF 读取', media: '🎨 二维码/图片信息' };
  function loadMcp() {
    api('settings').then(function (s) {
      bmState = Object.assign({}, s.builtinMcp || {});
      rmRows = (s.mcpRemote || []).map(function (m) { return Object.assign({}, m); });
      bmPaint(); rmPaint(); paintMcpMeta();
    }).catch(function (e) { toast(e.message); });
  }
  function paintMcpMeta() {
    api('system').then(function (d) {
      $('#mcpMeta').textContent = '当前已装载 ' + d.tools + ' 个工具 · 本地池开启 '
        + (d.builtinMcp || []).length + '/6 组 · 远程 ' + (d.mcpRemote || []).length + ' 个服务器';
    }).catch(function () {});
  }
  function bmPaint() {
    var box = $('#bmList');
    box.innerHTML = '';
    Object.keys(BM_LABELS).forEach(function (k) {
      var l = document.createElement('label');
      l.className = 'bm-card' + (bmState[k] ? ' on' : '');
      l.innerHTML = '<input type="checkbox" ' + (bmState[k] ? 'checked' : '') + '>'
        + '<span class="bm-dot"></span>' + BM_LABELS[k];
      l.querySelector('input').addEventListener('change', function (e) {
        bmState[k] = e.target.checked;
        l.classList.toggle('on', e.target.checked);
      });
      box.appendChild(l);
    });
  }
  function rmPaint() {
    var box = $('#rmList');
    box.innerHTML = rmRows.length ? '' : '<div class="empty">没有远程 MCP，点「新增」添加</div>';
    rmRows.forEach(function (m, i) {
      var el = document.createElement('div');
      el.className = 'row-edit';
      el.innerHTML = '<div class="row-grid" style="grid-template-columns:110px 1fr 30px">'
        + '<input type="text" data-f="name" maxlength="30" placeholder="名称" value="' + esc(m.name || '') + '">'
        + '<input type="text" data-f="url" placeholder="https://…（MCP 端点地址）" value="' + esc(m.url || '') + '">'
        + '<button class="ib del" data-a="del" title="删除">✕</button></div>'
        + '<input type="text" data-f="comment" maxlength="80" placeholder="备注（选填）" value="' + esc(m.comment || '') + '">';
      el.querySelectorAll('[data-f]').forEach(function (inp) {
        inp.addEventListener('input', function () { rmRows[i][inp.dataset.f] = inp.value; });
      });
      el.querySelector('button[data-a=del]').addEventListener('click', function () {
        rmRows.splice(i, 1); rmPaint();
      });
      box.appendChild(el);
    });
  }
  $('#rmAdd').addEventListener('click', function () {
    rmRows.push({ name: '', transport: 'http', url: '', comment: '' });
    rmPaint();
  });
  $('#mcpSave').addEventListener('click', function () {
    var badUrl = rmRows.filter(function (m) {
      return (m.url || '').trim() && !/^https?:\/\//.test(m.url.trim());
    }).length;
    if (badUrl) { toast(badUrl + ' 个远程地址不是 http(s) 开头，改一下再保存'); return; }
    toast('保存并热重载中…');
    api('mcp', { method: 'POST', body: { remote: rmRows, builtin: bmState } }).then(function (r) {
      toast('已生效：共 ' + r.total + ' 个工具（远程 ' + r.remote + ' 个服务器）');
      paintMcpMeta();
    }).catch(function (e) { toast(e.message); });
  });

  /* ================= ⑦ 系统 ================= */
  function loadSystem() {
    api('system').then(function (d) {
      var box = $('#sysList');
      box.innerHTML = '';
      function kv(k, v, action) {
        var el = document.createElement('div');
        el.className = 'kv';
        el.innerHTML = '<span class="k">' + esc(k) + '</span><span class="v">' + esc(v) + '</span>';
        if (action) el.appendChild(action);
        box.appendChild(el);
      }
      function openBtn(target, label) {
        var b = document.createElement('button');
        b.className = 'btn ghost sm';
        b.style.marginLeft = '10px';
        b.textContent = label;
        b.onclick = function () {
          api('open', { method: 'POST', body: { target: target } })
            .then(function () { toast('已打开'); })
            .catch(function (e) { toast(e.message || '打开失败'); });
        };
        return b;
      }
      kv('版本', 'v' + d.version);
      kv('已装载工具', d.tools + ' 个');
      kv('本地工具池', (d.builtinMcp || []).join('、') || '全关');
      kv('远程 MCP', (d.mcpRemote || []).map(function (m) { return m.name; }).join('、') || '无');
      kv('导出目录', d.exportDir, openBtn('export', '打开目录'));
      kv('运行日志', d.logPath, openBtn('log', '打开日志'));
    }).catch(function (e) { $('#sysList').innerHTML = '<div class="empty">' + esc(e.message) + '</div>'; });
  }

  /* ================= ⑧ 账号 ================= */
  function loadAccount() {
    api('session').then(function (d) {
      $('#acNameNow').value = d.name || '';
    }).catch(function () {});
    $('#acName').value = ''; $('#acOld').value = ''; $('#acNew').value = '';
  }
  $('#acSave').addEventListener('click', function () {
    var body = { oldPassword: $('#acOld').value };
    if ($('#acName').value.trim()) body.name = $('#acName').value.trim();
    if ($('#acNew').value) body.newPassword = $('#acNew').value;
    if (!body.name && !body.newPassword) { toast('没有要修改的内容'); return; }
    if (!body.oldPassword) { toast('请先输入原口令'); return; }
    api('account', { method: 'POST', body: body }).then(function (r) {
      toast(r.changed + '已修改');
      loadAccount();
      $('#admLabel').textContent = r.name ? ('· ' + r.name) : '';
    }).catch(function (e) { toast(e.message); });
  });
})();
