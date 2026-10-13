# -*- coding: utf-8 -*-
"""appconfig.py · 桌面端共享配置读取（端口等），避免 main/server 循环导入"""
import json
import sys
from pathlib import Path

def _exe_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

def _bundled_dir():
    if getattr(sys, 'frozen', False):
        return Path(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))
    return Path(__file__).parent

import os

def load():
    for p in [_exe_dir() / 'config.json', _bundled_dir() / 'config.json']:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if 'xxx' not in str(cfg.get('apiKey', '')):
                    return cfg
        except Exception:
            continue
    return {}

PORT = int(load().get('port') or 18765)
