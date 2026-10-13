/**
 * realchat.js · ChatGPT UI v2.0.0 大模型接入模块
 * ---------------------------------------------------------------
 * 零侵入设计：不修改 index.html 原有函数体，通过「覆盖全局函数 + 事件捕获」接入真实 API。
 * 接入点：window.sendMessage（假回复→真流式）、renderModelMenu、.gpt-item、
 *         fileInput（演示→真图片上传）、重新生成按钮、IME 回车守卫。
 *
 * TODO(Worker): API 配置当前取自 config.js（本地直连），
 *               将来改为从 Worker / 数据库动态获取后仅需替换 window.RC_CONFIG 来源。
 * ---------------------------------------------------------------
 */
(function () {
  'use strict';

  /* ================= 配置 ================= */
  const CFG = window.RC_CONFIG;
  const CFG_OK = !!(CFG && CFG.baseUrl && CFG.apiKey && CFG.model);
  const API_BASE = CFG_OK ? CFG.baseUrl.replace(/\/+$/, '') : '';
  const MAX_TOKENS = (CFG_OK && CFG.maxTokens) || 16384;
  const TEMP = (CFG_OK && CFG.temperature != null) ? CFG.temperature : 0.7;

  /* ================= 注入样式 ================= */
  const style = document.createElement('style');
  style.textContent = `
  .rc-strip { display:none; flex-wrap:wrap; gap:6px; padding:2px 2px 8px; }
  .rc-strip.has { display:flex; }
  .rc-chip { position:relative; }
  .rc-chip img { width:56px; height:56px; object-fit:cover; border-radius:8px; border:1px solid var(--border); display:block; }
  .rc-chip .x { position:absolute; top:-6px; right:-6px; width:18px; height:18px; border-radius:50%;
    background:#000a; color:#fff; font-size:11px; line-height:18px; text-align:center; cursor:pointer; }
  .rc-think { font-size:13px; color:var(--text-tertiary); cursor:pointer; user-select:none; margin-bottom:6px; }
  .rc-reason { font-size:13px; color:var(--text-tertiary); white-space:pre-wrap; max-height:140px; overflow:auto;
    border-left:2px solid var(--border); padding:2px 0 2px 10px; margin-bottom:8px; }
  .rc-reason.fold { display:none; }
  .rc-cursor { display:inline-block; width:7px; height:15px; background:var(--text-primary); vertical-align:-2px;
    margin-left:2px; animation:rc-blink .8s step-end infinite; }
  @keyframes rc-blink { 50% { opacity:0; } }
  .rc-err { color:var(--danger); font-size:14px; margin:6px 0; }
  .rc-tool { font-size:12.5px; color:var(--text-secondary); background:var(--bg-hover); border:1px solid var(--border);
    border-radius:8px; padding:5px 10px; margin:6px 0; display:flex; align-items:center; gap:6px; }
  .rc-tool .t-name { color:var(--text-primary); font-weight:600; }
  .rc-tool .t-args { color:var(--text-tertiary); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:420px; }
  .rc-tool .t-ok { color:var(--accent); }
  .rc-tool .t-fail { color:var(--danger); }
  .rc-user-img { max-width:180px; max-height:180px; border-radius:8px; display:block; margin-top:8px; border:1px solid var(--border); }
  .mm-demo { font-size:11px; color:var(--text-tertiary); border:1px solid var(--border); border-radius:4px;
    padding:0 4px; margin-left:6px; vertical-align:1px; }
  .send-btn.stop { background:var(--danger) !important; }
  .send-btn.stop svg { color:#fff !important; }
  `;
  document.head.appendChild(style);

  /* ================= 状态 ================= */
  let streaming = false;      // 是否正在流式生成
  let aborter = null;         // 停止控制器
  let pendingImages = [];     // 待发送图片（dataURL）

  /* ================= 轻量 Markdown 渲染 ================= */
  function mdRender(src) {
    const blocks = [];
    let s = String(src).replace(/```(\w*)\n?([\s\S]*?)(```|$)/g, function (m, lang, code) {
      blocks.push(code);
      return '\u0000B' + (blocks.length - 1) + '\u0000';
    });
    s = esc(s);
    s = s.replace(/`([^`\n]+)`/g, '<code>$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
    s = s.replace(/^#{1,4} (.*)$/gm, '<h4>$1</h4>');
    s = s.replace(/^(?:- .*(?:\n|$))+/gm, function (m) {
      return '<ul>' + m.trim().split('\n').map(function (l) { return '<li>' + l.slice(2) + '</li>'; }).join('') + '</ul>';
    });
    s = s.replace(/^(?:\d+\. .*(?:\n|$))+/gm, function (m) {
      return '<ol>' + m.trim().split('\n').map(function (l) { return '<li>' + l.replace(/^\d+\. /, '') + '</li>'; }).join('') + '</ol>';
    });
    s = s.split(/\n{2,}/).map(function (p) {
      p = p.trim();
      if (!p) return '';
      return /^<(h\d|ul|ol|pre|blockquote)/.test(p) ? p : '<p>' + p.replace(/\n/g, '<br>') + '</p>';
    }).join('');
    s = s.replace(/\u0000B(\d+)\u0000/g, function (m, i) {
      return '<pre><code>' + esc(blocks[+i].replace(/\n$/, '')) + '</code></pre>';
    });
    return s;
  }

  /* ================= 错误映射（中文） ================= */
  function errText(e) {
    if (e && e.name === 'AbortError') return null; // 主动停止，不算错误
    if (e && e.status === 401) return '鉴权失败（401）：API Key 无效';
    if (e && e.status === 403) return '无权限（403）：Key 可能被限制访问该模型';
    if (e && e.status === 404) return '接口不存在（404）：请检查 baseUrl 配置';
    if (e && e.status === 429) return '请求太频繁（429）：请稍后再试';
    if (e && e.status === 400) return '请求被拒绝（400）：' + String(e.body || '参数不合法').slice(0, 200);
    if (e && e.status >= 500) return '服务端错误（' + e.status + '）：请稍后再试';
    return '网络连接失败：请检查网络或 API 地址（CORS 跨域也可能导致）';
  }

  /* ================= 附件条 ================= */
  const strips = new Map(); // inputEl -> stripEl
  function buildStrips() {
    document.querySelectorAll('.composer').forEach(function (c) {
      const input = c.querySelector('input[type="text"]');
      if (!input || strips.has(input)) return;
      const strip = document.createElement('div');
      strip.className = 'rc-strip';
      c.insertBefore(strip, input);
      strips.set(input, strip);
    });
  }
  function renderStrips() {
    strips.forEach(function (strip) {
      strip.innerHTML = '';
      strip.classList.toggle('has', pendingImages.length > 0);
      pendingImages.forEach(function (url, i) {
        const chip = document.createElement('div');
        chip.className = 'rc-chip';
        chip.innerHTML = '<img src="' + url + '"><span class="x" title="移除">✕</span>';
        chip.querySelector('.x').onclick = function () {
          pendingImages.splice(i, 1); renderStrips();
        };
        strip.appendChild(chip);
      });
    });
  }
  function clearAttach() { pendingImages = []; renderStrips(); }

  /* 图片压缩：最长边 ≤1024，JPEG 85% */
  function compressImage(file) {
    return new Promise(function (resolve, reject) {
      const reader = new FileReader();
      reader.onload = function () {
        const img = new Image();
        img.onload = function () {
          const max = 1024;
          let w = img.width, h = img.height;
          if (w > max || h > max) { const k = max / Math.max(w, h); w = Math.round(w * k); h = Math.round(h * k); }
          const cv = document.createElement('canvas');
          cv.width = w; cv.height = h;
          cv.getContext('2d').drawImage(img, 0, 0, w, h);
          resolve(cv.toDataURL('image/jpeg', 0.85));
        };
        img.onerror = function () { reject(new Error('图片读取失败')); };
        img.src = reader.result;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  /* 覆盖 fileInput：去掉演示 toast，接真实图片上传 */
  const oldFileInput = document.getElementById('fileInput');
  const fileInput = oldFileInput.cloneNode(false);
  fileInput.setAttribute('accept', 'image/*');
  oldFileInput.replaceWith(fileInput);
  fileInput.addEventListener('change', function (e) {
    const files = Array.prototype.slice.call(e.target.files || []);
    e.target.value = '';
    if (!files.length) return;
    const room = 4 - pendingImages.length;
    if (room <= 0) { toast('最多附带 4 张图片'); return; }
    files.slice(0, room).forEach(function (f) {
      if (!/^image\//.test(f.type)) { toast('仅支持图片文件'); return; }
      if (f.size > 15 * 1024 * 1024) { toast('图片过大（>15MB）'); return; }
      compressImage(f).then(function (url) {
        if (pendingImages.length >= 4) return;
        pendingImages.push(url); renderStrips();
        toast('已添加图片附件');
      }).catch(function () { toast('图片处理失败'); });
    });
  });
  buildStrips();

  /* ================= 历史消息 → API messages ================= */
  function buildApiMessages(chat) {
    const msgs = [];
    if (chat.sys) msgs.push({ role: 'system', content: chat.sys });
    for (const m of chat.msgs) {
      if (m.role === 'user') {
        if (m.images && m.images.length) {
          const content = [{ type: 'text', text: m.text || '请分析这张图片' }];
          m.images.forEach(function (u) { content.push({ type: 'image_url', image_url: { url: u } }); });
          msgs.push({ role: 'user', content: content });
        } else {
          msgs.push({ role: 'user', content: m.text });
        }
      } else if (m.role === 'ai' && m.text) {
        msgs.push({ role: 'assistant', content: m.text });
      }
    }
    // RC_compress 钩子（v3.0 预留）：上下文压缩策略将来在此注入，桌面版/扩展可覆盖 window.RC_compress
    if (typeof window.RC_compress === 'function') {
      try { return window.RC_compress(msgs); } catch (_) { }
    }
    return msgs;
  }

  /* ================= SSE 流式请求 ================= */
  var opts = {}; // 事件扩展点：onEvent(kind, payload)
  function streamChat(apiMsgs, onReasoning, onContent) {
    aborter = new AbortController();
    return fetch(API_BASE + '/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + CFG.apiKey
      },
      body: JSON.stringify({
        model: CFG.model,
        messages: apiMsgs,
        stream: true,
        max_tokens: MAX_TOKENS,
        temperature: TEMP
      }),
      signal: aborter.signal
    }).then(function (res) {
      if (!res.ok) {
        return res.text().catch(function () { return ''; }).then(function (t) {
          const err = new Error('HTTP ' + res.status);
          err.status = res.status; err.body = t;
          throw err;
        });
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      function pump() {
        return reader.read().then(function (r) {
          if (r.done) return;
          buf += dec.decode(r.value, { stream: true });
          let idx;
          while ((idx = buf.indexOf('\n')) >= 0) {
            const line = buf.slice(0, idx).trim();
            buf = buf.slice(idx + 1);
            if (line.indexOf('data:') !== 0) continue;
            const data = line.slice(5).trim();
            if (data === '[DONE]') return;
            try {
              const j = JSON.parse(data);
              const d = (j.choices && j.choices[0] && j.choices[0].delta) || {};
              if (d.reasoning_content) onReasoning(d.reasoning_content);
              if (d.content) onContent(d.content);
              if (d.rc_tool && opts.onEvent) opts.onEvent('tool', d.rc_tool);
              if (d.rc_error && opts.onEvent) opts.onEvent('error', { name: d.rc_error });
            } catch (_) { /* 忽略非 JSON 行 */ }
          }
          return pump();
        });
      }
      return pump();
    });
  }

  function stopStream() {
    if (aborter) { try { aborter.abort(); } catch (_) {} }
  }
  function setStopUI(on) {
    streaming = on;
    ['heroSend', 'chatSend'].forEach(function (id) {
      const b = document.getElementById(id);
      if (b) b.classList.toggle('stop', on);
      if (b) b.title = on ? '停止生成' : '发送';
    });
  }

  /* ================= 构造流式 AI 气泡 ================= */
  function createStreamMsg() {
    const box = $('messages');
    const div = document.createElement('div');
    div.className = 'msg ai';
    div.innerHTML =
      '<div class="ai-avatar">' + LOGO_SVG + '</div>' +
      '<div style="min-width:0"><div class="ai-body">' +
      '<div class="rc-think">💭 思考中…</div>' +
      '<div class="rc-reason"></div>' +
      '<div class="rc-tools"></div>' +
      '<div class="rc-content"></div>' +
      '</div></div>';
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    return {
      div: div,
      think: div.querySelector('.rc-think'),
      reason: div.querySelector('.rc-reason'),
      toolsEl: div.querySelector('.rc-tools'),
      content: div.querySelector('.rc-content'),
      reasoning: '',
      answer: '',
      started: false,
      addTool: function (phase, name, tail) {
        let chip = this.toolsEl.querySelector('.rc-tool[data-name="' + name + '"]:last-of-type');
        if (phase === 'call' || !chip) {
          chip = document.createElement('div');
          chip.className = 'rc-tool';
          chip.dataset.name = name;
          chip.innerHTML = '<span>🔧</span><span class="t-name">' + esc(name) + '</span><span class="t-args"></span><span class="t-state"></span>';
          this.toolsEl.appendChild(chip);
        }
        if (phase === 'call') chip.querySelector('.t-args').textContent = tail || '';
        else chip.querySelector('.t-state').innerHTML = tail === '完成' ? '<span class="t-ok">✓ 完成</span>' : '<span class="t-fail">' + esc(tail || '失败') + '</span>';
        box.scrollTop = box.scrollHeight;
      },
      setReasoning: function (t) {
        this.reasoning += t;
        this.reason.textContent = this.reasoning;
        this.reason.scrollTop = this.reason.scrollHeight;
        box.scrollTop = box.scrollHeight;
      },
      setContent: function (t) {
        if (!this.started) {
          this.started = true;
          this.think.textContent = '💭 已完成思考（点击展开 / 折叠）';
          this.reason.classList.add('fold');
          this.think.onclick = function () { this.reason.classList.toggle('fold'); }.bind(this);
        }
        this.answer += t;
        this.content.innerHTML = mdRender(this.answer) + '<span class="rc-cursor"></span>';
        box.scrollTop = box.scrollHeight;
      },
      finish: function () {
        if (this.started) this.content.innerHTML = mdRender(this.answer);
        else if (!this.reasoning) this.think.style.display = 'none';
        else { // 只有思考没有内容（被截断等）
          this.think.textContent = '💭 思考完成，但未输出正文（可能达到输出上限）';
        }
      },
      error: function (msg) {
        this.content.insertAdjacentHTML('beforeend', '<div class="rc-err">⚠️ ' + esc(msg) + '</div>');
      }
    };
  }

  /* ================= 核心流式执行（send / regen 共用） ================= */
  function runStream(chat) {
    const ui = createStreamMsg();
    opts = {
      onEvent: function (kind, payload) {
        if (kind === 'tool') {
          ui.addTool(payload.phase, payload.name, payload.phase === 'call'
            ? JSON.stringify(payload.args || {})
            : (payload.ok ? '完成' : payload.text || '失败'));
        } else if (kind === 'error') {
          ui.error('服务端错误：' + payload.name);
        }
      }
    };
    setStopUI(true);
    streamChat(
      buildApiMessages(chat),
      function (t) { ui.setReasoning(t); },
      function (t) { ui.setContent(t); }
    ).then(function () {
      ui.finish();
      chat.msgs.push({ role: 'ai', text: ui.answer, html: mdRender(ui.answer), reasoning: ui.reasoning });
      setStopUI(false);
      $('messages').scrollTop = $('messages').scrollHeight;
    }).catch(function (e) {
      const msg = errText(e);
      if (msg === null) { // 主动停止：保留已生成部分
        ui.finish();
        if (ui.answer || ui.reasoning) {
          chat.msgs.push({ role: 'ai', text: ui.answer + (ui.answer ? '\n\n*(已手动停止)*' : ''), html: mdRender(ui.answer) + (ui.answer ? '<p><i>（已手动停止）</i></p>' : ''), reasoning: ui.reasoning });
        }
        toast('已停止生成');
      } else {
        ui.error(msg);
        toast(msg);
      }
      setStopUI(false);
    });
  }

  /* ================= 覆盖假发送链路 → 真实对话 ================= */
  window.sendMessage = function (inputEl) {
    if (!CFG_OK) { toast('未找到 config.js：请复制 config.example.js 为 config.js 并填入 API 配置'); return; }
    if (streaming) { toast('正在生成中，请先停止'); return; }
    const text = inputEl.value.trim();
    const imgs = pendingImages.slice();
    if (!text && !imgs.length) return;
    if (!currentChat) {
      $('hero').style.display = 'none';
      $('chatView').classList.add('active');
      currentChat = '_tmp_' + Date.now();
      CHATS[currentChat] = { title: (text || '图片对话').slice(0, 18), msgs: [] };
      renderChatList();
    }
    const chat = CHATS[currentChat];
    chat.msgs.push({ role: 'user', text: text, images: imgs.length ? imgs : undefined });
    // 渲染用户气泡（含图片预览）
    appendMsg({ role: 'user', text: text || '（图片）' });
    if (imgs.length) {
      const last = $('messages').querySelector('.msg.user:last-child .bubble');
      if (last) imgs.forEach(function (u) {
        const im = document.createElement('img');
        im.className = 'rc-user-img'; im.src = u;
        last.appendChild(im);
      });
    }
    inputEl.value = '';
    clearAttach();
    $('messages').scrollTop = $('messages').scrollHeight;
    runStream(chat);
  };
  if (!CFG_OK) {
    // 缺配置时页面仍可用（演示数据），但发送时给出引导
    document.addEventListener('DOMContentLoaded', function () { toast('未检测到 config.js，对话功能未启用'); });
  }

  /* 发送按钮：流式期间变停止按钮 */
  $('heroSend').onclick = function () { streaming ? stopStream() : window.sendMessage($('heroInput')); };
  $('chatSend').onclick = function () { streaming ? stopStream() : window.sendMessage($('chatInput')); };

  /* Esc 停止；IME 输入中回车不发送（修复中文输入法误发送）；textarea Shift+Enter 换行 */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && streaming) { stopStream(); return; }
    if (e.isComposing || e.keyCode === 229) { if (e.key === 'Enter') e.stopPropagation(); return; }
    if (e.key === 'Enter' && e.shiftKey && e.target && e.target.tagName === 'TEXTAREA') e.stopPropagation();
  }, true);

  /* ================= 模型菜单真实化 ================= */
  // TODO(Worker): 模型清单将来可从 Worker/数据库下发，当前以真实接入的 Qwen 模型为主项
  (function realignModels() {
    const real = { id: CFG_OK ? CFG.model : 'qwen3.6', name: 'Qwen 3.6 35B-A3B', desc: '视觉多模态 · 262K 上下文 · 已接入真实 API', real: true };
    const demo = []; // v3.0: 假 ChatGPT 模型项已移除，菜单只保留真实接入的模型
    MODELS.length = 0;
    MODELS.push(real);
    demo.forEach(function (d) { MODELS.push(d); });
    currentModel = MODELS[0].id;
    const badge = $('modelBadge');
    if (badge) badge.textContent = 'Qwen 3.6';
  })();

  window.renderModelMenu = function () {
    const menu = $('modelMenu');
    menu.innerHTML = MODELS.map(function (m) {
      return '<div class="mm-item" data-id="' + esc(m.id) + '">' +
        (m.id === currentModel ? '<span class="check">✓</span>' : '') +
        '<div>' + esc(m.name) + (m.real ? '' : '<span class="mm-demo">演示</span>') + '</div>' +
        '<div class="d">' + esc(m.desc) + '</div></div>';
    }).join('');
    menu.querySelectorAll('.mm-item').forEach(function (item) {
      item.onclick = function () {
        currentModel = item.dataset.id;
        const m = MODELS.find(function (x) { return x.id === currentModel; });
        $('modelBadge').textContent = m.real ? 'Qwen 3.6' : m.name.replace('ChatGPT ', '');
        if (!m.real) toast('演示项：请求实际仍由 Qwen 模型处理');
        closeMenus();
      };
    });
  };
  renderModelMenu();

  /* ================= GPT 列表 → 角色系统提示词 ================= */
  document.querySelectorAll('.gpt-item').forEach(function (item) {
    const name = item.dataset.gpt;
    item.onclick = function (e) {
      e.stopPropagation();
      newChat();
      currentChat = '_gpt_' + Date.now();
      CHATS[currentChat] = {
        title: name,
        sys: '你是「' + name + '」。请始终以该角色的专业口吻回答用户的问题，回答使用简体中文。',
        msgs: [{ role: 'ai', text: '你好，我是 **' + name + '**。有什么可以帮你？', html: '<p>你好，我是 <b>' + esc(name) + '</b>。有什么可以帮你？</p>' }]
      };
      renderChatList();
      openChat(currentChat);
    };
  });

  /* ================= 重新生成 → 真实重新请求 ================= */
  // 注意：必须挂在 document 捕获层。事件到达目标元素时 capture/bubble 监听器按注册顺序执行，
  // 挂在 #messages 上会晚于原「演示」toast 监听器，无法拦截。
  document.addEventListener('click', function (e) {
    const btn = e.target.closest && e.target.closest('.act-btn');
    if (!btn || btn.dataset.act !== 'regen') return;
    const msgBox = document.getElementById('messages');
    if (!msgBox || !msgBox.contains(btn)) return;
    e.stopImmediatePropagation(); e.preventDefault();
    if (!CFG_OK) { toast('未找到 config.js，对话功能未启用'); return; }
    if (streaming) { toast('正在生成中，请先停止'); return; }
    const chat = CHATS[currentChat];
    if (!chat) { toast('没有可重新生成的内容'); return; }
    while (chat.msgs.length && chat.msgs[chat.msgs.length - 1].role === 'ai') chat.msgs.pop();
    if (!chat.msgs.length || chat.msgs[chat.msgs.length - 1].role !== 'user') { toast('没有可重新生成的内容'); return; }
    renderMessages();
    runStream(chat);
  }, true); // document 捕获层，先于原监听器执行

  /* ================= newChat 清理附件 ================= */
  const _origNewChat = window.newChat;
  window.newChat = function () { clearAttach(); return _origNewChat.apply(this, arguments); };

})();
