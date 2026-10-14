/**
 * dynamic.js · v3.5.0 后台配置的前台应用（零侵入追加）
 * ------------------------------------------------------------------
 * 1. 外观品牌：/api/appearance → 应用名（document.title + 侧栏菜单）、默认主题、默认强调色
 * 2. 人设 GPT：/api/personas → 侧栏 GPT 列表动态渲染（拉不到保留静态兜底项）
 * 3. 首页卡片：/api/starters → hero 输入框下方建议卡片，点击填入输入框
 * UI 全部走前台现有 ChatGPT 风格（不引入 dog2027 视觉）。
 */
(function () {
  'use strict';

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

  /* ============ 1. 外观品牌 ============ */
  function applyAppearance(d) {
    try {
      var name = (d && d.appName) || '';
      if (name) {
        document.title = name;
        var lm = document.getElementById('lmGpt');
        if (lm) lm.innerHTML = '<span style="color:var(--accent)">✓</span> ' + esc(name);
      }
      // 默认主题：后台设了非 system 才动；用户随后仍可点右上角切换
      if (d && d.theme && d.theme !== 'system') {
        document.documentElement.setAttribute('data-theme', d.theme);
        var tt = document.getElementById('themeToggle');
        if (tt) tt.textContent = d.theme === 'light' ? '🌙' : '☀️';
        document.querySelectorAll('#themeSeg .seg-item').forEach(function (b) {
          b.classList.toggle('on', b.dataset.themeVal === d.theme);
        });
      }
      // 默认强调色
      if (d && d.accent && /^#[0-9a-fA-F]{6}$/.test(d.accent)) {
        document.documentElement.style.setProperty('--accent', d.accent);
        document.querySelectorAll('#accentDots .dot').forEach(function (dot) {
          dot.classList.toggle('sel', dot.dataset.color.toLowerCase() === d.accent.toLowerCase());
        });
      }
    } catch (_) { /* 品牌应用失败不影响对话 */ }
  }

  /* ============ 2. 人设 GPT 动态渲染 ============ */
  var PERSONA_SYS_FALLBACK = '你是「{name}」。请始终以该角色的专业口吻回答用户的问题，回答使用简体中文。';
  function renderPersonas(list) {
    var sub = document.getElementById('gptSub');
    if (!sub || !list || !list.length) return;
    sub.innerHTML = '';
    list.forEach(function (p) {
      var item = document.createElement('div');
      item.className = 'gpt-item';
      item.textContent = (p.avatar || '🤖') + ' ' + p.name;
      item.onclick = function (e) {
        e.stopPropagation();
        // 与 realchat.js 静态 GPT 项同款行为（全局词法作用域直接取 CHATS 等）
        window.newChat();
        currentChat = '_gpt_' + Date.now();
        CHATS[currentChat] = {
          title: p.name,
          sys: p.prompt || PERSONA_SYS_FALLBACK.replace('{name}', p.name),
          msgs: [{ role: 'ai', text: '你好，我是 **' + p.name + '**。' + (p.desc || '有什么可以帮你？'),
                   html: '<p>你好，我是 <b>' + esc(p.name) + '</b>。' + esc(p.desc || '有什么可以帮你？') + '</p>' }]
        };
        renderChatList();
        openChat(currentChat);
      };
      sub.appendChild(item);
    });
  }

  /* ============ 3. 首页卡片 ============ */
  function renderStarters(list) {
    var hero = document.getElementById('hero');
    var wrap = hero ? hero.querySelector('.composer-wrap') : null;
    if (!wrap || !list || !list.length) return;
    var row = document.createElement('div');
    row.id = 'rcStarters';
    row.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:18px';
    list.forEach(function (s0) {
      var b = document.createElement('button');
      b.className = 'tool-pill';
      b.style.cssText = 'max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
      b.textContent = '💡 ' + s0.title;
      b.title = s0.prompt;
      b.onclick = function () {
        var input = document.getElementById('heroInput');
        if (input) { input.value = s0.prompt; input.focus(); }
      };
      row.appendChild(b);
    });
    wrap.parentNode.insertBefore(row, wrap.nextSibling);
  }

  /* ============ 启动 ============ */
  function boot() {
    fetch('/api/appearance').then(function (r) { return r.json(); })
      .then(applyAppearance).catch(function () {});
    fetch('/api/personas').then(function (r) { return r.json(); })
      .then(function (d) { renderPersonas(d.personas); }).catch(function () {});
    fetch('/api/starters').then(function (r) { return r.json(); })
      .then(function (d) { renderStarters(d.starters); }).catch(function () {});
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
