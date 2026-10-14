/**
 * storage.js · v3.0.0 会话持久化（IndexedDB）
 * ------------------------------------------------------------------
 * 选型结论：IndexedDB（非 localStorage）。
 * - 图片消息含 base64（单条可达数 MB），localStorage 5MB 上限存不住，且同步写入阻塞 UI
 * - IndexedDB 支持按会话记录级读写，为后续「上下文压缩」「多会话/多人」扩展预留
 * - schema：sessions 仓（每会话一条记录，含 compression 预留字段）+ meta 仓（状态 KV）
 *   TODO(Worker): 会话云端同步将来可在此挂 Worker 上报钩子。
 */
(function () {
  'use strict';
  if (!window.indexedDB) return;
  const DB_NAME = 'chatgpt-ui', DB_VER = 1;
  let db = null;
  let lastHash = '';

  function open() {
    return new Promise(function (resolve, reject) {
      const r = indexedDB.open(DB_NAME, DB_VER);
      r.onupgradeneeded = function (e) {
        const d = e.target.result;
        if (!d.objectStoreNames.contains('sessions')) d.createObjectStore('sessions', { keyPath: 'id' });
        if (!d.objectStoreNames.contains('meta')) d.createObjectStore('meta');
      };
      r.onsuccess = function (e) { resolve(e.target.result); };
      r.onerror = function () { reject(r.error); };
    });
  }
  function tx(store, mode) { return db.transaction(store, mode).objectStore(store); }
  function req(r) { return new Promise(function (res, rej) { r.onsuccess = function () { res(r.result); }; r.onerror = function () { rej(r.error); }; }); }

  function snapshot() {
    const chats = {};
    for (const k of Object.keys(CHATS)) chats[k] = CHATS[k];
    return { currentChat: currentChat, chats: chats };
  }

  async function save(force) {
    if (!db) return;
    try {
      const s = snapshot();
      const str = JSON.stringify(s);
      if (!force && str === lastHash) return;
      lastHash = str;
      const names = Object.keys(s.chats);
      // 删除已不存在的会话
      const existing = await req(tx('sessions', 'readonly').getAllKeys());
      for (const k of existing) {
        if (names.indexOf(k) < 0) tx('sessions', 'readwrite').delete(k);
      }
      for (const k of names) {
        const c = s.chats[k];
        tx('sessions', 'readwrite').put({
          id: k, title: c.title || '', sys: c.sys || null,
          owner: c.owner || 'default',   // v3.3：多用户隔离字段（将来按 owner 过滤）
          msgs: c.msgs || [], updated_at: Date.now(),
          // 预留：compressed / summary / summarized_until_seq（上下文压缩）字段
          compressed: c.compressed || false
        });
      }
      tx('meta', 'readwrite').put({ currentChat: s.currentChat, saved_at: Date.now() }, 'state');
    } catch (e) { /* 存储失败静默（隐私模式下 quota 受限） */ }
  }

  async function restore() {
    try {
      db = await open();
      const state = await req(tx('meta', 'readonly').get('state'));
      const all = await req(tx('sessions', 'readonly').getAll());
      if (all && all.length) {
        // 有历史数据：整体替换默认演示会话
        for (const k of Object.keys(CHATS)) delete CHATS[k];
        for (const rec of all) {
          CHATS[rec.id] = { title: rec.title, msgs: rec.msgs || [] };
          if (rec.sys) CHATS[rec.id].sys = rec.sys;
          if (rec.compressed) CHATS[rec.id].compressed = true;
        }
        currentChat = (state && state.currentChat && CHATS[state.currentChat]) ? state.currentChat
          : Object.keys(CHATS)[0];
        renderChatList();
        openChat(currentChat);
      }
      // 定时快照（hash 变了才写）+ 离开前兜底
      setInterval(function () { save(false); }, 2000);
      window.addEventListener('beforeunload', function () { save(true); });
    } catch (e) { /* 首次运行或 IDB 异常：直接用默认数据 */ }
  }

  // 暴露给「清空本地数据」与将来的会话管理
  window.RCStorage = {
    save: function () { return save(true); },
    clear: async function () {
      if (!db) db = await open();
      tx('sessions', 'readwrite').clear();
      tx('meta', 'readwrite').clear();
      lastHash = '';
    }
  };
  restore();
})();
