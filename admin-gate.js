/**
 * admin-gate.js · v3.4.0 前台管理员入口（零侵入追加）
 * ------------------------------------------------------------------
 * 1. userMenu 里「管理员登录 / 管理后台」两项按登录态显隐——未登录时入口零暴露
 *    （不泄露内部状态，符合本产品 UX 纪律）。
 * 2. 登录浮层：用户名 + 口令 → POST /api/admin/login → token 存 sessionStorage。
 *    与 /admin 后台页同源共享这把 token；后台页改口令/登出即时同步到前台。
 * 3. 「管理后台」点击 → location.href = '/admin'（server 静态路由，同窗口打开）。
 */
(function () {
  'use strict';
  var TK = 'RC_ADMIN_TOKEN';
  var state = { logged: false, name: '' };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function toast(msg) {
    if (window.toast) { window.toast(msg); return; }
    var t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = 'position:fixed;left:50%;bottom:36px;transform:translateX(-50%);background:#0d0d0e;color:#fff;padding:9px 18px;border-radius:9px;font-size:13px;z-index:9999';
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2600);
  }

  /* —— 登录态显隐 —— */
  function paintMenu() {
    var a = document.getElementById('menuAdminLogin');
    var b = document.getElementById('menuAdminPanel');
    if (a) a.style.display = state.logged ? 'none' : '';
    if (b) b.style.display = state.logged ? '' : 'none';
  }
  function refresh() {
    var token = sessionStorage.getItem(TK) || '';
    if (!token) { state.logged = false; paintMenu(); return; }
    fetch('/api/admin/session', { headers: { 'authorization': 'Bearer ' + token } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        state.logged = !!(d && d.ok);
        state.name = (d && d.name) || '';
        paintMenu();
      })
      .catch(function () { state.logged = false; paintMenu(); });
  }

  /* —— 登录浮层 —— */
  function openLogin() {
    var old = document.getElementById('rcAdminLogin');
    if (old) { old.classList.add('open'); return; }
    var mask = document.createElement('div');
    mask.className = 'modal-mask open';
    mask.id = 'rcAdminLogin';
    mask.innerHTML =
      '<div class="settings-modal" style="max-width:360px;height:auto;padding:28px">' +
      '<button class="close-x" id="rcAlClose">✕</button>' +
      '<div style="font-size:18px;font-weight:700;margin-bottom:4px">管理员登录</div>' +
      '<div style="font-size:13px;color:var(--text-secondary);margin-bottom:18px">登录后可在账号菜单进入管理后台</div>' +
      '<div style="color:var(--danger,#e5484d);font-size:13px;min-height:20px;margin-bottom:8px" id="rcAlErr"></div>' +
      '<div class="field" style="margin-bottom:14px"><label style="display:block;font-size:13px;color:var(--text-secondary);margin-bottom:5px">管理员用户名</label>' +
      '<input id="rcAlName" style="width:100%;padding:9px 12px;border:1px solid var(--border,#e5e5e7);border-radius:8px;background:var(--bg,#fff);color:var(--text,#0d0d0e);font-size:14px;outline:none"></div>' +
      '<div class="field" style="margin-bottom:18px"><label style="display:block;font-size:13px;color:var(--text-secondary);margin-bottom:5px">口令</label>' +
      '<input id="rcAlPass" type="password" style="width:100%;padding:9px 12px;border:1px solid var(--border,#e5e5e7);border-radius:8px;background:var(--bg,#fff);color:var(--text,#0d0d0e);font-size:14px;outline:none"></div>' +
      '<button class="btn" id="rcAlGo" style="width:100%;padding:10px;border:none;border-radius:8px;background:var(--accent,#19c37d);color:#fff;font-size:14px">登 录</button></div>';
    document.body.appendChild(mask);
    var close = function () { mask.classList.remove('open'); setTimeout(function () { mask.remove(); }, 200); };
    mask.addEventListener('click', function (e) { if (e.target === mask) close(); });
    document.getElementById('rcAlClose').onclick = close;
    var go = function () {
      var name = document.getElementById('rcAlName').value.trim();
      var pw = document.getElementById('rcAlPass').value;
      document.getElementById('rcAlErr').textContent = '';
      fetch('/api/admin/login', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: name, password: pw })
      }).then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.token) {
            sessionStorage.setItem(TK, d.token);
            state.logged = true; state.name = d.name || '';
            paintMenu();
            close();
            toast('管理员已登录');
          } else {
            document.getElementById('rcAlErr').textContent = d.error || '登录失败';
          }
        })
        .catch(function () { document.getElementById('rcAlErr').textContent = '网络错误，请重试'; });
    };
    document.getElementById('rcAlGo').onclick = go;
    document.getElementById('rcAlPass').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') go();
    });
    setTimeout(function () { document.getElementById('rcAlName').focus(); }, 50);
  }

  /* —— 绑定菜单项（DOM 就绪后） —— */
  function bind() {
    var a = document.getElementById('menuAdminLogin');
    var b = document.getElementById('menuAdminPanel');
    if (a) a.onclick = function (e) { e.stopPropagation(); openLogin(); };
    if (b) b.onclick = function (e) {
      e.stopPropagation();
      if (!sessionStorage.getItem(TK)) { openLogin(); return; }
      location.href = '/admin';
    };
    refresh();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }

  // 后台页登出后回到前台时同步显隐
  window.addEventListener('focus', refresh);

  window.RC_ADMIN = state;
})();
