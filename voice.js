/**
 * voice.js · v3.3 语音能力（零侵入追加）
 * ------------------------------------------------------------------
 * 1. 设置面板「语音」Tab 音色 chips 真实化：GET /api/tts/voices 渲染 Edge TTS 音色，
 *    选择持久化 localStorage（RC_TTS_VOICE），tts.js 播放时读取。
 * 2. 语音输入闭环：mic 按钮 → 全屏聆听覆盖层（Web Speech API，中文识别，实时中间文本）
 *    → 识别完成自动填入输入框并发送 → AI 回复完成后自动朗读（若本次来自语音）。
 *    纯网页模式（无本地服务）下降级：识别仍可用（浏览器内置），播放提示需桌面版。
 */
(function () {
  'use strict';

  var VOICE_KEY = 'RC_TTS_VOICE';

  /* ============ 1. 音色 chips 真实化 ============ */
  function initVoiceChips() {
    var box = document.getElementById('voiceChips');
    if (!box) return;
    fetch('/api/tts/voices').then(function (r) { return r.json(); }).then(function (d) {
      var cur = localStorage.getItem(VOICE_KEY) || (d.voices[0] && d.voices[0].id);
      box.innerHTML = '';
      (d.voices || []).forEach(function (v) {
        var b = document.createElement('button');
        b.className = 'chip' + (v.id === cur ? ' on' : '');
        b.textContent = v.name;
        b.dataset.voice = v.id;
        b.onclick = function () {
          box.querySelectorAll('.chip').forEach(function (c) { c.classList.remove('on'); });
          b.classList.add('on');
          localStorage.setItem(VOICE_KEY, v.id);
          toast('已选择音色：' + v.name);
        };
        box.appendChild(b);
      });
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
