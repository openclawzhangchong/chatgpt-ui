# -*- coding: utf-8 -*-
"""
build_desktop.py · ChatGPT UI 桌面版打包流水线
1. 同步前端文件到 desktop/ui/（index.html + 增强脚本 + 桌面版 config.js 指向本地服务）
2. PyInstaller 单文件打包（--windowed 无黑窗）
3. 产物拷贝到桌面：ChatGPT-UI.exe + config.json（可改 key 不用重打包）
用法：python build_desktop.py
"""
import os
import sys
import shutil
import subprocess
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # chatgpt-ui 项目根
UI = os.path.join(HERE, 'ui')
NAME = 'ChatGPT-UI'
DESKTOP_CANDIDATES = [
    os.path.join(os.path.expanduser('~'), 'Desktop'),
    os.path.join(os.path.expanduser('~'), 'OneDrive', 'Desktop'),
]

FRONTEND_FILES = ['index.html', 'realchat.js', 'storage.js', 'tts.js', 'toolbox.js', 'compress.js', 'config.example.js']


def step_sync_ui():
    os.makedirs(UI, exist_ok=True)
    for f in FRONTEND_FILES:
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(UI, f))
            print('  ui/', f)
    # 桌面版 config.js：指向本地服务（key 由 Python 侧持有，前端占位）
    with open(os.path.join(UI, 'config.js'), 'w', encoding='utf-8') as f:
        f.write('''/**
 * 桌面版前端配置（由 build_desktop.py 自动生成）。
 * baseUrl 指向 Python 本地服务，真实 API Key 在 EXE 旁的 config.json（或内置默认）。
 * TODO(Worker): 将来配置改为从 Worker/数据库下发。
 */
window.RC_CONFIG = {
  baseUrl: '/api',
  apiKey: 'local-desktop',
  model: 'local-desktop',
  maxTokens: 16384,
  temperature: 0.7
};
''')
    print('  ui/config.js (desktop variant)')
    print('[1/3] UI 同步完成')


def step_pyinstaller():
    args = [
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--onefile', '--windowed', '--name', NAME,
        '--add-data', os.path.join(UI) + ';ui',
        '--add-data', os.path.join(HERE, 'config.json') + ';.',
        '--collect-all', 'webview',
        '--collect-all', 'uvicorn',
        '--collect-all', 'edge_tts',
        '--collect-all', 'docx',
        '--hidden-import', 'server', '--hidden-import', 'tools', '--hidden-import', 'appconfig',
        '--distpath', os.path.join(HERE, 'dist'),
        '--workpath', os.path.join(HERE, 'build'),
        '--specpath', HERE,
        os.path.join(HERE, 'main.py'),
    ]
    print('  ', ' '.join(args[1:]))
    r = subprocess.run(args, cwd=HERE)
    if r.returncode != 0:
        sys.exit('PyInstaller 打包失败')
    print('[2/3] PyInstaller 打包完成')


def step_deploy():
    exe = os.path.join(HERE, 'dist', NAME + '.exe')
    if not os.path.isfile(exe):
        sys.exit('未找到打包产物：' + exe)
    target_dir = next((d for d in DESKTOP_CANDIDATES if os.path.isdir(d)), os.path.expanduser('~'))
    dest = os.path.join(target_dir, NAME + '.exe')
    shutil.copy2(exe, dest)
    cfg_dest = os.path.join(target_dir, 'config.json')
    if not os.path.exists(cfg_dest):  # 不覆盖用户已改过的配置
        shutil.copy2(os.path.join(HERE, 'config.json'), cfg_dest)
    print('[3/3] 已部署到桌面：%s' % dest)
    print('      配置文件：%s' % cfg_dest)


if __name__ == '__main__':
    print('[0/3] ChatGPT UI 桌面版打包开始')
    step_sync_ui()
    step_pyinstaller()
    step_deploy()
