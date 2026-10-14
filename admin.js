/**
 * admin.js · v3.4.0 管理后台逻辑（配 admin.html，路由 /admin）
 * ------------------------------------------------------------------
 * 登录闸门 → 模型池管理（增删改/启停/默认/测试）→ 改口令。
 * token 存 sessionStorage（与前台同源，前台登录态实时同步；关页即清，符合本地工具习惯）。
 * Key 只写不读：列表接口一律打码，编辑时留空 = 不改（dog2027 §7.3 同款纪律）。
 */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var TK = 'RC_ADMIN_TOKEN';
  var token = sessionStorage.getItem(TK) || '';
  var cache = { providers: [], defaultId: '' };

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

  /* —— 登录 / 登出 —— */
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
    loadAll();
  }
  function signOut() {
    token = '';
    sessionStorage.removeItem(TK);
    $('#app').classList.remove('show');
    $('#gate').style.display = '';
  }
  $('#btnOut').addEventListener('click', signOut);

  // 带旧 token 打开本页：先验一次会话，过了直接进
  if (token) {
    api('session').then(function () { return api('models'); }).then(function (d) {
      enter(d.adminName);
    }).catch(function () { signOut(); });
  }

  function loadAll() { loadModels(); }

  /* —— 模型池 —— */
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

  /* —— 新增 / 编辑弹层 —— */
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

  /* —— 改口令 —— */
  $('#btnPw').addEventListener('click', function () {
    $('#pwOld').value = ''; $('#pwNew').value = '';
    $('#pwMask').classList.add('open');
  });
  $('#pwCancel').addEventListener('click', function () { $('#pwMask').classList.remove('open'); });
  $('#pwMask').addEventListener('click', function (e) { if (e.target === this) this.classList.remove('open'); });
  $('#pwSave').addEventListener('click', function () {
    api('password', { method: 'POST', body: { oldPassword: $('#pwOld').value, newPassword: $('#pwNew').value } })
      .then(function () {
        $('#pwMask').classList.remove('open');
        toast('口令已修改');
      }).catch(function (e) { toast(e.message); });
  });
})();
