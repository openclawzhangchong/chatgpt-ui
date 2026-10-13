/**
 * ChatGPT UI · API 配置模板
 * 使用方法：把本文件复制一份改名为 config.js，填入真实配置。
 * config.js 已加入 .gitignore，不会被提交到仓库（防止 Key 泄漏）。
 *
 * TODO(Worker): 将来 API 配置（baseUrl/apiKey/model）可能改为从 Worker / 数据库动态获取，
 *               届时只需保留 window.RC_CONFIG 的赋值来源变化，realchat.js 无需改动。
 */
window.RC_CONFIG = {
  baseUrl: 'https://jiuyeke.cn/v1',          // OpenAI 兼容接口入口
  apiKey: 'sk-xxxxxxxxxxxxxxxxxxxxxxxx',     // 你的 API Key（本地自用，请勿提交）
  model: 'Qwen3.6-35B-A3B-Vision',           // 大模型名称（多模态视觉）
  maxTokens: 16384,                          // 最大单次输出（该模型上限 16384）
  temperature: 0.7
};
