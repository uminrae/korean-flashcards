# utils/path_helper.py
# -*- coding: utf-8 -*-
"""静态资源与持久化数据动态路径兼容助手
解决 PyInstaller 打包为 onedir / onefile 后的资源定位与路径丢失 Bug
"""

import sys
import os


def get_base_dir() -> str:
    """获取程序根目录（未打包时为源码根目录，打包后为 exe 所在目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        # 当前 utils 文件的上一级目录
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_path(relative_path: str) -> str:
    """
    获取静态只读资源绝对路径（兼容开发环境与 PyInstaller 打包后的 sys._MEIPASS）
    用于：内置默认词库、应用图标、预置模板等打包进 exe 或内部资源目录的文件
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = get_base_dir()
    return os.path.normpath(os.path.join(base_path, relative_path))


def get_data_path(relative_path: str) -> str:
    """
    获取持久化读写数据路径（保证用户数据与缓存可读写）
    用于：SQLite 数据库、用户外部导入字体、TTS 语音缓存文件等
    如果指定路径的父目录不存在，将自动安全创建
    """
    base_path = get_base_dir()
    full_path = os.path.normpath(os.path.join(base_path, relative_path))
    parent_dir = os.path.dirname(full_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    return full_path
