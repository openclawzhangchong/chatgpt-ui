/**
 * tts.js · v3.0.0 朗读（Edge TTS，Python 桌面端 /api/tts 提供 mp3）
 * 零侵入：document 捕获层拦截消息「朗读」按钮（原为演示 toast）。
 * 纯静态模式（无本地服务）时 fetch 404 → 友好提示。
 */
(function () {
  'use strict';
  let audio = null;
  let playingBtn = null;

  function stop() {
    if (audio) { try { audio.pause(); } catch (_) {} audio = null; }
    if (playingBtn) { playingBtn.textContent = '🔊'; playingBtn = null; }
  }

  document.addEventListener('click', function (e) {
    const btn = e.target.closest && e.target.closest('.act-btn');
    if (!btn || btn.dataset.act !== 'speak') return;
    const msgBox = document.getElementById('messages');
    if (!msgBox || !msgBox.contains(btn)) return;
    e.stopImmediatePropagation(); e.preventDefault();

    if (playingBtn === btn) { stop(); return; }  // 再点一次 = 停止
    stop();

    const msgEl = btn.closest('.msg');
    const body = msgEl.querySelector('.ai-body');
    const content = body ? (body.querySelector('.rc-content') || body) : null;
    const text = (content ? content.textContent : '').trim();
    if (!text) { toast('没有可朗读的内容'); return; }

    fetch('/api/tts?text=' + encodeURIComponent(text.slice(0, 4500)))
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.blob();
      })
      .then(function (blob) {
        audio = new Audio(URL.createObjectURL(blob));
        playingBtn = btn;
        btn.textContent = '⏹';
        audio.onended = stop;
        audio.onerror = stop;
        return audio.play();
      })
      .catch(function (err) {
        stop();
        toast(String(err).indexOf('404') >= 0 || String(err).indexOf('Failed') >= 0
          ? '朗读需要桌面版（本地 Edge TTS 服务）'
          : '朗读失败：' + err);
      });
  }, true);
})();
