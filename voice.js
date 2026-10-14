/**
 * voice.js · v3.4.0 语音能力（零侵入追加）
 * ------------------------------------------------------------------
 * 1. 设置面板「语音」Tab 音色真实化：GET /api/tts/voices 拉微软全量音色（分组下拉），
 *    选择持久化 localStorage（RC_TTS_VOICE），tts.js 播放时读取；附「试听」按钮
 *    （dog2027 同款节流与自动播放解锁纪律）。
 * 2. 语音输入闭环：mic 按钮 → 全屏聆听覆盖层（Web Speech API，中文识别，实时中间文本）
 *    → 识别完成自动填入输入框并发送 → AI 回复完成后自动朗读（若本次来自语音）。
 *    纯网页模式（无本地服务）下降级：识别仍可用（浏览器内置），播放提示需桌面版。
 */
(function () {
  'use strict';

  var VOICE_KEY = 'RC_TTS_VOICE';

  /* ============ 1. 音色选择（v3.4.0：分组下拉 + 试听） ============ */
  // 音色表由本地服务拉微软全量（约 500 个，按 中文女声/中文男声/多语言/其他 分组，
  // 参考 dog2027 的动态分组思路）；拉不到时回落原演示 chips 并提示需要桌面版。
  var TRY_TEXT = '你好，我是你的 AI 助手，正在为你朗读这句试听文本。';
  var tryBusy = 0, tryAudio = null, tryUnlocked = false, tryCtrl = null;

  function unlockTryAudio() {
    if (!tryAudio) tryAudio = new Audio();
    if (tryUnlocked) return;
    try {
      tryAudio.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';
      tryAudio.play().then(function () {
        tryUnlocked = true;
        if (tryAudio.src.indexOf('data:') === 0) { try { tryAudio.pause(); } catch (_) {} }
      }).catch(function () {});
    } catch (_) {}
  }

  function tryVoice() {
    if (tryCtrl) { tryCtrl.abort(); tryCtrl = null; return; }  // 再点一次 = 停止
    if (Date.now() - tryBusy < 1500) return;                   // 前端节流，别把服务打爆
    tryBusy = Date.now();
    unlockTryAudio();  // 点击的同步栈里解锁，等音频回来再 play 才过自动播放策略
    var voice = localStorage.getItem(VOICE_KEY) || '';
    tryCtrl = new AbortController();
    fetch('/api/tts?text=' + encodeURIComponent(TRY_TEXT) + '&voice=' + encodeURIComponent(voice),
      { signal: tryCtrl.signal })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.blob(); })
      .then(function (blob) {
        var a = tryAudio || new Audio();
        a.src = URL.createObjectURL(blob);
        a.onended = function () { tryCtrl = null; URL.revokeObjectURL(a.src); };
        a.onerror = function () { tryCtrl = null; };
        return a.play();
      })
      .catch(function (err) {
        tryCtrl = null;
        if (err && err.name === 'AbortError') return;
        toast('试听失败：' + (err.message || err));
      });
  }

  function initVoiceChips() {
    var box = document.getElementById('voiceChips');
    if (!box) return;
    fetch('/api/tts/voices').then(function (r) { return r.json(); }).then(function (d) {
      var voices = d.voices || [];
      if (!voices.length) throw new Error('音色表为空');
      var cur = localStorage.getItem(VOICE_KEY) || (voices[0] && voices[0].id);
      if (!voices.some(function (v) { return v.id === cur; })) cur = voices[0].id;
      box.innerHTML = '';
      var sel = document.createElement('select');
      sel.style.cssText = 'padding:7px 10px;border:1px solid var(--border,#e5e5e7);border-radius:8px;'
        + 'background:var(--bg,#fff);color:var(--text,#0d0d0e);font-size:13px;max-width:220px';
      var groups = {};
      voices.forEach(function (v) { (groups[v.group || '其他'] = groups[v.group || '其他'] || []).push(v); });
      Object.keys(groups).forEach(function (g) {
        var og = document.createElement('optgroup');
        og.label = g;
        groups[g].forEach(function (v) {
          var o = document.createElement('option');
          o.value = v.id; o.textContent = v.name;
          og.appendChild(o);
        });
        sel.appendChild(og);
      });
      sel.value = cur;
      sel.onchange = function () {
        localStorage.setItem(VOICE_KEY, sel.value);
        toast('已选择音色：' + sel.options[sel.selectedIndex].textContent);
      };
      var btn = document.createElement('button');
      btn.className = 'chip';
      btn.textContent = '▶ 试听';
      btn.onclick = tryVoice;
      box.appendChild(sel);
      box.appendChild(btn);
      if (!localStorage.getItem(VOICE_KEY)) localStorage.setItem(VOICE_KEY, cur);
    }).catch(function () {
      // 无本地服务：保留原演示 chips，加提示
      box.querySelectorAll('.chip').forEach(function (c) {
        c.onclick = function () { toast('音色选择需要桌面版（本地 TTS 服务）'); };
      });
    });
  }

  /* ============ 2. 语音输入闭环 ============ */
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recog = null, listening = false, fromVoice = false;

  function currentInput() {
    return document.getElementById('chatView').classList.contains('active')
      ? document.getElementById('chatInput') : document.getElementById('heroInput');
  }

  function startListen() {
    var overlay = document.getElementById('voiceOverlay');
    var title = overlay.querySelector('.voice-title');
    var hint = overlay.querySelector('.voice-hint');
    if (!SR) {
      title.textContent = '当前浏览器不支持语音识别';
      hint.textContent = '请使用 Edge / Chrome（点击退出）';
      return;
    }
    recog = new SR();
    recog.lang = 'zh-CN';
    recog.continuous = false;
    recog.interimResults = true;
    listening = true;
    recog.onstart = function () { title.textContent = '正在聆听…'; hint.textContent = '请说话（点击任意位置取消）'; };
    recog.onresult = function (e) {
      var interim = '', final = '';
      for (var i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript;
        else interim += e.results[i][0].transcript;
      }
      if (interim) title.textContent = interim;
      if (final) {
        listening = false;
        overlay.classList.remove('open');
        var input = currentInput();
        input.value = final.trim();
        fromVoice = true;
        if (window.sendMessage) window.sendMessage(input);
        toast('已识别：' + final.trim().slice(0, 30));
      }
    };
    recog.onerror = function (e) {
      listening = false;
      title.textContent = '识别出错：' + (e.error || '未知');
      hint.textContent = '点击退出';
    };
    recog.onend = function () { listening = false; };
    try { recog.start(); } catch (_) {}
  }

  function stopListen() {
    listening = false;
    try { if (recog) recog.stop(); } catch (_) {}
  }

  // 覆盖 mic 行为：真实识别 + 保留点击退出
  document.getElementById('micBtn').onclick = function () {
    document.getElementById('voiceOverlay').classList.add('open');
    startListen();
  };
  document.getElementById('micBtn2').onclick = function () {
    document.getElementById('voiceOverlay').classList.add('open');
    startListen();
  };
  document.getElementById('voiceOverlay').onclick = function () {
    stopListen();
    document.getElementById('voiceOverlay').classList.remove('open');
  };

  /* ============ 3. 语音来源自动播报 ============ */
  // 监听最后一个 AI 气泡：语音来源且流式结束时自动朗读
  function hookAutoSpeak() {
    var messages = document.getElementById('messages');
    if (!messages || !window.MutationObserver) return;
    var lastAiCount = 0;
    setInterval(function () {
      var bubbles = messages.querySelectorAll('.msg.ai');
      if (bubbles.length === lastAiCount) return;
      var grew = bubbles.length > lastAiCount;
      lastAiCount = bubbles.length;
      if (!grew || !fromVoice) return;
      var last = bubbles[bubbles.length - 1];
      var content = last.querySelector('.rc-content') || last.querySelector('.ai-body');
      var streaming = !!last.querySelector('.rc-cursor');
      if (streaming || !content) return; // 还在流式，等下一次 tick
      var text = content.textContent.trim();
      if (text && window.RC_TTS) window.RC_TTS.play(text);
      fromVoice = false;
    }, 1200);
  }

  initVoiceChips();
  hookAutoSpeak();
})();
