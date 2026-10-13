# -*- coding: utf-8 -*-
"""
main.py · ChatGPT UI 桌面版入口
Python 做壳：uvicorn 起本地服务(127.0.0.1) → pywebview 开窗口加载 UI。
WebView2 缺失时自动降级为系统浏览器打开。
崩溃日志：%TEMP%/ChatGPT-UI.log（窗口模式下排查问题的唯一入口）
"""
import socket
import threading
import time
import traceback
import webbrowser
import os

LOG = os.path.join(os.environ.get('TEMP', '.'), 'ChatGPT-UI.log')


def log(msg):
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write('[%s] %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg))
    except Exception:
        pass


def _free_port(start):
    for p in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', p))
                return p
            except OSError:
                continue
    return start


def run_uvicorn(app, port):
    try:
        import uvicorn
        log('uvicorn starting on 127.0.0.1:%d' % port)
        # log_config=None：--windowed 打包后没有 stdout，uvicorn 默认 formatter
        # 调 sys.stdout.isatty() 会崩（AttributeError），必须禁用其内置日志配置
        uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning', log_config=None)
        log('uvicorn exited')
    except Exception:
        log('uvicorn thread crashed:\n' + traceback.format_exc())


def main():
    from server import app
    from appconfig import PORT
    port = _free_port(PORT)
    url = 'http://127.0.0.1:%d/' % port
    log('launch: port=%d (requested %d), frozen=%s' % (port, PORT, bool(getattr(__import__('sys'), 'frozen', False))))

    t = threading.Thread(target=run_uvicorn, args=(app, port), daemon=True)
    t.start()

    ok = False
    for _ in range(100):  # 最多等 25 秒
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                ok = True
                break
        except OSError:
            time.sleep(0.25)
    log('server ready: %s' % ok)

    try:
        import webview
        webview.create_window('ChatGPT · 复刻版', url, width=1280, height=860, min_size=(420, 600))
        webview.start(private_mode=False)
        log('webview closed normally')
    except Exception:
        log('pywebview failed, fallback browser:\n' + traceback.format_exc())
        webbrowser.open(url)
        while True:
            time.sleep(3600)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log('main crashed:\n' + traceback.format_exc())
