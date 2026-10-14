/**
 * toolbox.js · v3.0.0 菜单换血（UI 框架零改动，只重绑定功能与文案）
 * ------------------------------------------------------------------
 * - Sora           → 工具箱（真实：MCP 工具清单 + 导出目录）
 * - 资料库          → 导出中心（真实：当前会话导出 Word / Markdown）
 * - 升级方案 ×2     → 关于本应用
 * - 创建公开链接    → 复制对话全文
 * - 退出登录        → 清空本地数据
 * - 免责声明文案更新
 * TODO(Worker): 工具清单将来可由 Worker/数据库下发合并到 /api/tools。
 */
(function () {
  'use strict';
  const IS_DESKTOP = !!window.RC_CONFIG && location.origin.indexOf('127.0.0.1') === 0 && !location.origin.match(/:8080$/);

  function relabel(id, text) {
    const el = document.getElementById(id);
    if (!el) return;
    const tn = Array.prototype.find.call(el.childNodes, function (n) {
      return n.nodeType === 3 && n.textContent.trim();
    });
    if (tn) tn.textContent = text;
  }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* ---------- 导航文字换血 ---------- */
  relabel('soraNav', '工具箱');
  relabel('libNav', '导出中心');
  relabel('menuUpgrade', '关于本应用');
  const upLabel = document.querySelector('#upgradeBtn > div > div');
  if (upLabel) upLabel.textContent = '关于本应用';
  document.querySelectorAll('.disclaimer').forEach(function (d) {
    d.textContent = '由 AI 生成，仅供参考 · 桌面版 v3.0 · 本地 MCP 工具已就绪';
  });
  const smPublic = document.getElementById('smPublic');
  if (smPublic) {
    relabel('smPublic', '复制对话全文');
    smPublic.onclick = function () {
      closeMenus();
      const chat = CHATS[currentChat];
      if (!chat) { toast('没有可复制的内容'); return; }
      const lines = (chat.msgs || []).map(function (m) {
        return (m.role === 'user' ? '【用户】' : '【AI】') + (m.text || '');
      });
      copyText((chat.title ? '《' + chat.title + '》\n\n' : '') + lines.join('\n\n'));
    };
  }
  const logoutEl = Array.prototype.find.call(document.querySelectorAll('.um-item'),
    function (el) { return el.textContent.indexOf('退出登录') >= 0; });
  if (logoutEl) {
    const tn = Array.prototype.find.call(logoutEl.childNodes, function (n) { return n.nodeType === 3 && n.textContent.trim(); });
    if (tn) tn.textContent = '清空本地数据';
    logoutEl.onclick = function () {
      closeMenus();
      if (!window.RCStorage) { toast('当前环境不支持本地存储清理'); return; }
      window.RCStorage.clear().then(function () {
        toast('已清空本地会话数据，即将刷新');
        setTimeout(function () { location.reload(); }, 800);
      });
    };
  }

  /* ---------- 工具箱（原 Sora 弹窗） ---------- */
  const soraModal = document.getElementById('soraModal');
  if (soraModal) {
    soraModal.querySelector('.sub-modal').innerHTML =
      '<h3>🧰 工具箱 · 本地 MCP 工具</h3>' +
      '<div class="sub-desc">对话中 AI 可自动调用以下本机工具（由 Python 桌面端提供）</div>' +
      '<div id="tbToolList" style="display:flex;flex-direction:column;gap:8px;margin:10px 0;">' +
      '<div class="sub-desc">加载中…</div></div>' +
      '<div class="sub-desc" id="tbExportDir"></div>' +
      '<div style="text-align:right;margin-top:10px"><button id="tbClose" style="background:var(--btn-bg);color:var(--btn-text);border:none;border-radius:8px;padding:8px 18px;cursor:pointer;font-size:14px">关闭</button></div>';
    soraModal.querySelector('#tbClose').onclick = function () { soraModal.classList.remove('open'); };
    $('soraNav').onclick = function (e) {
      e.stopPropagation(); closeMenus();
      soraModal.classList.add('open');
      fetch('/api/tools').then(function (r) { return r.json(); }).then(function (data) {
        const box = document.getElementById('tbToolList');
        const mcpRows = (data.mcp || []).map(function (m) {
          return '<div class="rc-tool" style="margin:0"><span>' + (m.status === '已连接' ? '🟢' : '🔴') + '</span>' +
            '<span class="t-name">' + esc(m.name) + '</span>' +
            '<span class="t-args" style="white-space:normal">' + esc(m.status) + ' · ' + m.tool_count + ' 个工具' +
            (m.status !== '已连接' ? '（如为魔搭 MCP：URL 为个人专属 24 小时有效，需在广场重新复制）' : '') + '</span></div>';
        }).join('');
        box.innerHTML = (mcpRows || '') + (data.tools || []).map(function (t) {
          return '<div class="rc-tool" style="margin:0"><span>🔧</span><span class="t-name">' + esc(t.name) +
            '</span><span class="t-args" style="white-space:normal">' + esc(t.description) + '</span></div>';
        }).join('') || '<div class="sub-desc">无工具</div>';
        document.getElementById('tbExportDir').textContent = '📁 导出目录：' + (data.export_dir || '-');
      }).catch(function () {
        document.getElementById('tbToolList').innerHTML =
          '<div class="sub-desc">工具服务不可用（需要桌面版运行）</div>';
      });
    };
  }

  /* ---------- 导出中心（原资料库弹窗） ---------- */
  const libModal = document.getElementById('libModal');
  if (libModal) {
    libModal.querySelector('.sub-modal').innerHTML =
      '<h3>📤 导出中心</h3>' +
      '<div class="sub-desc">把当前会话导出为文件，保存到桌面 chatgpt-ui-exports 目录</div>' +
      '<div style="display:flex;gap:10px;margin:14px 0;flex-wrap:wrap">' +
      '<button id="expWord" style="flex:1;min-width:140px;background:var(--btn-bg);color:var(--btn-text);border:none;border-radius:10px;padding:12px;cursor:pointer;font-size:14px;font-weight:600">📄 导出为 Word</button>' +
      '<button id="expMd" style="flex:1;min-width:140px;background:var(--bg-hover);color:var(--text-primary);border:1px solid var(--border);border-radius:10px;padding:12px;cursor:pointer;font-size:14px">📝 导出为 Markdown</button>' +
      '</div>' +
      '<div class="sub-desc" id="expResult"></div>' +
      '<div style="text-align:right;margin-top:10px"><button id="expClose" style="background:var(--btn-bg);color:var(--btn-text);border:none;border-radius:8px;padding:8px 18px;cursor:pointer;font-size:14px">关闭</button></div>';
    libModal.querySelector('#expClose').onclick = function () { libModal.classList.remove('open'); };

    function currentMsgs() {
      const chat = CHATS[currentChat];
      if (!chat || !chat.msgs || !chat.msgs.length) return null;
      const out = [];
      for (const m of chat.msgs) {
        if (!m.text) continue;
        out.push({ role: m.role === 'user' ? 'user' : 'assistant', text: m.text });
      }
      return out.length ? { title: chat.title || '对话导出', messages: out } : null;
    }
    function doExport(fmt) {
      const payload = currentMsgs();
      const box = document.getElementById('expResult');
      if (!payload) { box.textContent = '当前会话没有可导出的内容'; return; }
      box.textContent = '导出中…';
      fetch('/api/export', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: payload.title, messages: payload.messages, fmt: fmt }) })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            box.innerHTML = '✅ 已导出：<span class="t-name">' + esc(data.path) + '</span>';
            toast('导出成功');
          } else { box.textContent = '导出失败：' + JSON.stringify(data); }
        })
        .catch(function () { box.textContent = '导出需要桌面版（本地服务不可用）'; });
    }
    libModal.querySelector('#expWord').onclick = function () { doExport('word'); };
    libModal.querySelector('#expMd').onclick = function () { doExport('markdown'); };
    $('libNav').onclick = function (e) { e.stopPropagation(); closeMenus(); libModal.classList.add('open'); };
  }

  /* ---------- 关于本应用（原升级弹窗） ---------- */
  const upModal = document.getElementById('upModal');
  if (upModal) {
    const model = (window.RC_CONFIG && window.RC_CONFIG.model) || '-';
    upModal.querySelector('.sub-modal').innerHTML =
      '<h3>ℹ️ 关于本应用</h3>' +
      '<div class="sub-desc" style="line-height:2">' +
      '<b>ChatGPT UI 桌面版</b> <span id="abVer">v…</span><br>' +
      '架构：Python 壳（pywebview）+ 本地 MCP 工具 + Edge TTS + IndexedDB 持久化<br>' +
      '模型：' + esc(model) + '<br>' +
      '接口：OpenAI 兼容（本地直连）<br>' +
      '开源：github.com/openclawzhangchong/chatgpt-ui<br>' +
      '<span style="color:var(--text-tertiary)">由 AI 生成，仅供参考</span></div>' +
      '<div style="text-align:right;margin-top:10px"><button id="abClose" style="background:var(--btn-bg);color:var(--btn-text);border:none;border-radius:8px;padding:8px 18px;cursor:pointer;font-size:14px">关闭</button></div>';
    // 版本号动态拉取（单一数据源 = server.py APP_VERSION，避免显示版本漂移）
    fetch('/api/version').then(function (r) { return r.json(); }).then(function (d) {
      var el = upModal.querySelector('#abVer');
      if (el && d.version) el.textContent = 'v' + d.version;
    }).catch(function () { /* 拉不到就保持占位，纯网页模式不显示版本 */ });
    upModal.querySelector('#abClose').onclick = function () { upModal.classList.remove('open'); };
    $('upgradeBtn').onclick = function (e) { e.stopPropagation(); closeMenus(); upModal.classList.add('open'); };
    $('menuUpgrade').onclick = function () { closeMenus(); upModal.classList.add('open'); };
  }

  document.querySelectorAll('.lib-card').forEach(function (c) { c.onclick = null; });
})();
