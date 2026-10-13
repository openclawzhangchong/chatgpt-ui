# -*- coding: utf-8 -*-
"""
main.py · ChatGPT UI 桌面版入口（v3.1）
- uvicorn 本地服务（127.0.0.1，随机端口防冲突）
- pywebview 主窗口
- **Windows 系统托盘**（右下角）：关闭窗口不退出，退到托盘；托盘菜单 显示/退出
- 崩溃日志：%TEMP%/ChatGPT-UI.log
"""
import os
import socket
import threading
import time
import traceback
import webbrowser

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
        # log_config=None：--windowed 打包后无 stdout，uvicorn 默认 formatter 调 isatty() 会崩
        uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning', log_config=None)
        log('uvicorn exited')
    except Exception:
        log('uvicorn thread crashed:\n' + traceback.format_exc())


def _make_tray_icon():
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, 60, 60], radius=14, fill=(16, 185, 129, 255))
    d.rectangle([20, 22, 26, 42], fill=(255, 255, 255, 255))   # 字母 A
    d.line([26, 42, 36, 22], fill=(255, 255, 255, 255), width=4)
    d.line([33, 34, 43, 34], fill=(255, 255, 255, 255), width=3)
    return img


def run_tray(window_holder):
    """托盘线程：常驻右下角；关闭窗口→隐藏；菜单：显示主窗口 / 退出。"""
    try:
        import pystray
    except Exception as e:
        log('pystray 不可用，托盘未启用：%s' % e)
        return
    state = {'icon': None}

    def do_show():
        w = window_holder.get('window')
        if w:
            try:
                w.show()
            except Exception as e:
                log('托盘 show 失败：%s' % e)

    def do_quit():
        log('托盘退出')
        try:
            state['icon'].stop()
        except Exception:
            pass
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem('显示主窗口', do_show, default=True),
        pystray.MenuItem('退出程序', do_quit),
    )
    icon = pystray.Icon('ChatGPT-UI', _make_tray_icon(), 'ChatGPT UI 桌面版', menu)
    state['icon'] = icon
    log('托盘线程启动')

    def _welcome():
        time.sleep(1.5)
        try:
            icon.notify('ChatGPT-UI 已启动 · 关闭窗口会退到托盘，右键图标可退出', 'ChatGPT UI')
        except Exception:
            pass

    threading.Thread(target=_welcome, daemon=True).start()
    icon.run()


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

    window_holder = {'window': None}

    try:
        import webview
        window = webview.create_window('ChatGPT · 复刻版', url, width=1280, height=860, min_size=(420, 600))
        window_holder['window'] = window

        def on_closing():
            log('窗口关闭 → 隐藏到托盘')
            try:
                window.hide()
            except Exception:
                pass
            return False  # 取消关闭，保留托盘常驻

        window.events.closing += on_closing

        threading.Thread(target=run_tray, args=(window_holder,), daemon=True).start()
        webview.start(private_mode=False)  # 持久化 WebView2 用户目录（IndexedDB 不丢）
        log('webview exited')
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
