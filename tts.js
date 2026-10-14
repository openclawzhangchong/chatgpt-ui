/**
 * tts.js · v3.0 朗读（Edge TTS，Python 桌面端 /api/tts 提供音频）
 * v3.3：暴露 window.RC_TTS.play/stop 供 voice.js 语音闭环复用；音色读 localStorage。
 * 零侵入：document 捕获层拦截消息「朗读」按钮（原为演示 toast）。
 * 纯静态模式（无本地服务）时 fetch 404 → 友好提示。
 */
(function () {
  'use strict';
  var VOICE_KEY = 'RC_TTS_VOICE';
  var audio = null;
  var playingBtn = null;

  function stop() {
    if (audio) { try { audio.pause(); } catch (_) {} audio = null; }
    if (playingBtn) { playingBtn.textContent = '🔊'; playingBtn = null; }
  }

  function play(text) {
    stop();
    return fetch('/api/tts?text=' + encodeURIComponent(String(text).slice(0, 4500))
      + '&voice=' + encodeURIComponent(localStorage.getItem(VOICE_KEY) || ''))
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.blob();
      })
      .then(function (blob) {
        audio = new Audio(URL.createObjectURL(blob));
        audio.onended = stop;
        audio.onerror = stop;
        return audio.play();
      })
      .catch(function (err) {
        stop();
        var msg = String(err).indexOf('404') >= 0 || String(err).indexOf('Failed') >= 0
          ? '朗读需要桌面版（本地 Edge TTS 服务）' : '朗读失败：' + err;
        toast(msg);
        throw err;
      });
  }

  // 消息操作栏 🔊 拦截（捕获层，先于原演示 toast）
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('.act-btn');
    if (!btn || btn.dataset.act !== 'speak') return;
    var msgBox = document.getElementById('messages');
    if (!msgBox || !msgBox.contains(btn)) return;
    e.stopImmediatePropagation(); e.preventDefault();

    if (playingBtn === btn) { stop(); return; }  // 再点一次 = 停止
    var msgEl = btn.closest('.msg');
    var body = msgEl.querySelector('.ai-body');
    var content = body ? (body.querySelector('.rc-content') || body) : null;
    var text = (content ? content.textContent : '').trim();
    if (!text) { toast('没有可朗读的内容'); return; }
    play(text).then(function () {
      playingBtn = btn; btn.textContent = '⏹';
    }).catch(function () { /* 错误已 toast */ });
  }, true);

  window.RC_TTS = { play: play, stop: stop };
})();
