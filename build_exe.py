# build_exe.py
# -*- coding: utf-8 -*-
"""
韩语悬浮卡片 - PyInstaller 自动化一键打包构建脚本
功能：
1. 自动检查并编译多尺寸高清 app_icon.ico
2. 调用 PyInstaller 自动化构建独立分发目录 (onedir) 或单文件 (onefile)
3. 包含完整静态资源 (data/, assets/) 与隐式依赖项 (pygame, edge_tts, PyQt6)
4. 输出目录: dist/韩语卡片/ (内含 韩语卡片.exe)
"""

import os
import sys
import shutil
import subprocess

APP_NAME = "未来的韩语卡片"
MAIN_ENTRY = "main.py"
ICON_FILE = os.path.join("assets", "app_icon.ico")


def check_and_create_icon():
    """确保 app_icon.ico 图标文件存在"""
    if not os.path.exists(ICON_FILE):
        print("🔧 正在自动生成高清应用图标 app_icon.ico...")
        from scripts.convert_icon import convert_image_to_ico
        if not convert_image_to_ico():
            print("⚠️ 未能生成 app_icon.ico，将使用默认无图标模式构建")
            return None
    return ICON_FILE


def clean_build_artifacts():
    """清理旧的构建缓存与产物"""
    print("🧹 正在清理旧的 build / dist 缓存...")
    for d in ["build", "dist", f"{APP_NAME}.spec"]:
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
        elif os.path.isfile(d):
            try:
                os.remove(d)
            except Exception:
                pass


def build_app(mode: str = "onedir"):
    """
    执行 PyInstaller 打包构建
    :param mode: 'onedir' (推荐目录分发) 或 'onefile' (单文件便携版)
    """
    clean_build_artifacts()
    icon_path = check_and_create_icon()

    print(f"\n🚀 开始使用 PyInstaller 构建 [{mode}] 模式应用...")

    # 构建基础指令
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        f"--name={APP_NAME}",
        f"--{mode}",
        "--noconsole",
        "--clean",
        "--noconfirm",
    ]

    # 图标设置
    if icon_path and os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")

    # 数据与资源文件包含 (Windows 使用分号 ;)
    data_sep = ";" if os.name == "nt" else ":"
    
    # 静态资源目录
    for resource_dir in ["data", "assets"]:
        if os.path.exists(resource_dir):
            cmd.append(f"--add-data={resource_dir}{data_sep}{resource_dir}")

    # 隐式依赖库
    hidden_imports = [
        "pygame",
        "pygame.mixer",
        "edge_tts",
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtMultimedia",
        "sqlite3",
        "asyncio",
        "PIL",
        "ctypes",
    ]
    for h in hidden_imports:
        cmd.append(f"--hidden-import={h}")

    # 入口脚本
    cmd.append(MAIN_ENTRY)

    print(f"📦 执行打包命令:\n{' '.join(cmd)}\n")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n❌ 打包构建失败，返回码: {result.returncode}")
        return False

    # 检查输出文件
    if mode == "onedir":
        dist_dir = os.path.join("dist", APP_NAME)
        exe_file = os.path.join(dist_dir, f"{APP_NAME}.exe")
    else:
        exe_file = os.path.join("dist", f"{APP_NAME}.exe")

    if os.path.exists(exe_file):
        size_mb = os.path.getsize(exe_file) / (1024 * 1024)
        print("\n" + "=" * 60)
        print(f"🎉 打包构建大功告成！")
        print(f"  ✓ 可执行文件: {os.path.abspath(exe_file)}")
        if mode == "onedir":
            print(f"  ✓ 应用分发目录: {os.path.abspath(dist_dir)}")
        print(f"  ✓ 主程序大小: {size_mb:.2f} MB")
        print("=" * 60)
        return True
    else:
        print(f"\n❌ 未在预期路径找到构建产物: {exe_file}")
        return False


if __name__ == "__main__":
    mode = "onedir"
    if len(sys.argv) > 1 and sys.argv[1] in ["onefile", "onedir"]:
        mode = sys.argv[1]
    success = build_app(mode)
    if not success:
        sys.exit(1)
