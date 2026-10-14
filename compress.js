/**
 * compress.js · v3.1 上下文压缩（window.RC_compress）
 * ------------------------------------------------------------------
 * 由 realchat.js 的 buildApiMessages 钩子调用（默认不挂，本文件挂上即生效）。
 * 策略（确定性、不调 LLM，零成本）：
 *   1. 按字符预算（默认 80000 字符）控制发送给模型的上下文
 *   2. 超预算时：先把较早消息里的图片替换为「[历史图片已折叠]」占位（图片 token 是大头）
 *   3. 仍超预算：从最旧开始丢弃整条消息，并在开头插入折叠说明
 *   4. 始终保留 system 提示与最近 6 条消息不动
 * TODO(Worker): 将来可升级为 LLM 摘要式压缩（把被裁历史调 LLM 生成 summary 存入会话 compression.summary）
 */
(function () {
  'use strict';
  const BUDGET = 80000;   // 字符预算（约 2-3 万 token 安全线）
  const KEEP_TAIL = 6;    // 最近消息保留条数

  function sizeOf(m) {
    const c = m.content;
    return typeof c === 'string' ? c.length : JSON.stringify(c || '').length;
  }

  window.RC_compress = function (msgs) {
    if (!Array.isArray(msgs) || msgs.length <= KEEP_TAIL) return msgs;
    let total = 0;
    for (const m of msgs) total += sizeOf(m);
    if (total <= BUDGET) return msgs;

    const out = msgs.map(function (m) { return { role: m.role, content: m.content }; });
    let dropped = 0;

    // 第一轮：折叠较早消息中的图片
    for (let i = 0; i < out.length - KEEP_TAIL; i++) {
      const m = out[i];
      if (Array.isArray(m.content)) {
        const texts = m.content.filter(function (c) { return c.type === 'text'; })
          .map(function (c) { return c.text || ''; });
        m.content = '[历史图片已折叠] ' + texts.join(' ');
      }
    }
    total = 0;
    for (const m of out) total += sizeOf(m);
    if (total <= BUDGET) return out;

    // 第二轮：丢弃最旧消息（保留 system 与尾部 KEEP_TAIL 条）
    let i = 0;
    while (out.length - dropped > KEEP_TAIL + 1 && total > BUDGET && i < out.length) {
      const m = out[i];
      if (m.role === 'system') { i++; continue; }
      if (i >= out.length - KEEP_TAIL - dropped) break;
      total -= sizeOf(m);
      out.splice(i, 1);
      dropped++;
    }
  if (dropped > 0) {
    out.splice(1, 0, {
      role: 'user',
      content: '（系统提示：更早的 ' + dropped + ' 条历史已按上下文预算折叠，仅保留最近对话。被折叠消息包含重要信息时请提醒用户。'
    });
  }
  return out;
};

/* ---------- v3.3 LLM 摘要式压缩（异步，发送前由 realchat.js 调用） ----------
   流程：先走同步 RC_compress 裁剪；若真的丢弃了历史，则把被裁部分发给模型
   生成 200 字摘要，替换掉占位提示——被裁信息以摘要形式保留在上下文里。 */
window.RC_compressAsync = async function (msgs) {
  const trimmed = window.RC_compress(msgs);
  const noteIdx = trimmed.findIndex(function (m) {
    return typeof m.content === 'string' && m.content.indexOf('系统提示：更早的') === 0;
  });
  if (noteIdx < 0) return trimmed;  // 未触发裁剪
  const droppedCount = msgs.length - (trimmed.length - 2);
  const dropped = msgs.slice(0, Math.max(0, droppedCount)).filter(function (m) { return m.role !== 'system'; });
  if (!dropped.length) return trimmed;
  try {
    const text = dropped.map(function (m) {
      const c = typeof m.content === 'string' ? m.content : JSON.stringify(m.content || '');
      return (m.role === 'user' ? '用户' : 'AI') + '：' + c.slice(0, 1500);
    }).join('\n').slice(0, 6000);
    const resp = await fetch('/api/chat/completions', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: [{ role: 'user', content: '请用 200 字以内概括以下对话历史的关键信息（保留结论、数字、文件路径、待办）：\n' + text }], stream: true })
    });
    const summary = await _readSSEAll(resp);
    if (summary && summary.trim().length > 10) {
      trimmed[noteIdx] = { role: 'user', content: '（更早对话的自动摘要）\n' + summary.trim() };
    }
  } catch (_) { /* 摘要失败则保留原占位提示 */ }
  return trimmed;
};

function _readSSEAll(resp) {
  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = '', out = '';
  function pump() {
    return reader.read().then(function (r) {
      if (r.done) return out;
      buf += dec.decode(r.value, { stream: true });
      let i;
      while ((i = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        if (line.indexOf('data:') !== 0) continue;
        const d = line.slice(5).trim();
        if (d === '[DONE]') continue;
        try {
          const j = JSON.parse(d);
          const c = (j.choices && j.choices[0] && j.choices[0].delta || {}).content;
          if (c) out += c;
        } catch (_) {}
      }
      return pump();
    });
  }
  return pump();
}
})();
