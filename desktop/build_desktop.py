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

FRONTEND_FILES = ['index.html', 'realchat.js', 'storage.js', 'tts.js', 'toolbox.js', 'compress.js',
                  'voice.js', 'admin-gate.js', 'admin.html', 'admin.js', 'config.example.js']


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
        '--icon', os.path.join(HERE, 'app.ico'),
        '--add-data', os.path.join(UI) + ';ui',
        '--add-data', os.path.join(HERE, 'config.json') + ';.',
        '--add-data', os.path.join(HERE, 'models.default.json') + ';.',
        '--add-data', os.path.join(HERE, 'admin.default.json') + ';.',
        '--collect-all', 'webview',
        '--collect-all', 'uvicorn',
        '--collect-all', 'edge_tts',
        '--collect-all', 'docx',
        '--hidden-import', 'server', '--hidden-import', 'tools', '--hidden-import', 'appconfig',
        '--hidden-import', 'tools_extra', '--hidden-import', 'mcp_client', '--hidden-import', 'models',
        # 本地 MCP server 池是 importlib 动态导入，必须显式列出父包+子模块（collect-submodules 不带父包）
        '--hidden-import', 'mcp_servers', '--hidden-import', 'mcp_servers.web',
        '--hidden-import', 'mcp_servers.files', '--hidden-import', 'mcp_servers.office',
        '--hidden-import', 'mcp_servers.dev', '--hidden-import', 'mcp_servers.pdf',
        '--hidden-import', 'mcp_servers.media',
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


def step_make_icon():
    """生成 EXE/托盘同款图标（绿色圆角块 + 白色 A），多尺寸 ico。"""
    try:
        from PIL import Image, ImageDraw
        path = os.path.join(HERE, 'app.ico')
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([12, 12, 244, 244], radius=52, fill=(16, 185, 129, 255))
        d.rectangle([88, 76, 116, 178], fill=(255, 255, 255, 255))
        d.line([116, 178, 172, 76], fill=(255, 255, 255, 255), width=26)
        d.line([138, 138, 206, 138], fill=(255, 255, 255, 255), width=20)
        img.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print('  app.ico 已生成')
    except Exception as e:
        print('  app.ico 生成失败（不影响打包）：', e)


if __name__ == '__main__':
    print('[0/3] ChatGPT UI 桌面版打包开始')
    step_make_icon()
    step_sync_ui()
    step_pyinstaller()
    step_deploy()
