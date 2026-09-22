# build_installer.py
# -*- coding: utf-8 -*-
"""
「未来的韩语卡片」- 全流程一键打包与 Inno Setup 安装包制作脚本
工作流：
1. 清理历史构建缓存 (build/, dist/, Output/, *.spec)
2. 确保 assets/app_icon.ico 高清图标就绪
3. 阶段一：调用 PyInstaller 编译生成 dist/未来的韩语卡片/ (onedir 模式)
4. 阶段二：自动智能探测系统中的 Inno Setup 7/6 编译器 (ISCC.exe)
5. 阶段三：调用 ISCC 编译 installer.iss，在 Output/ 目录中生成 单文件安装包 (未来的韩语卡片_Setup_v1.0.exe)
"""

import os
import sys
import shutil
import hashlib
import subprocess
from typing import Optional

APP_NAME = "未来的韩语卡片"
APP_VERSION = "1.1"
MAIN_ENTRY = "main.py"
ICON_FILE = os.path.join("assets", "app_icon.ico")
ISS_FILE = "installer.iss"
OUTPUT_DIR = "Output"
INSTALLER_NAME = f"{APP_NAME}_Setup_v{APP_VERSION}.exe"


def clean_artifacts():
    """清理历史构建缓存与旧产物"""
    print("🧹 [1/4] 正在清理历史构建产物与缓存...")
    dirs_to_clean = ["build", "dist", OUTPUT_DIR, f"{APP_NAME}.spec", "韩语卡片.spec"]
    for d in dirs_to_clean:
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
        elif os.path.isfile(d):
            try:
                os.remove(d)
            except Exception:
                pass
    print("  ✓ 缓存清理完毕")


def check_and_prepare_icon():
    """确保应用专属高清图标存在"""
    if not os.path.exists(ICON_FILE):
        print("🎨 [2/4] 正在生成高清多尺寸应用图标...")
        try:
            from process_icon import process_icon
            process_icon(shape="squircle")
        except Exception as e:
            print(f"⚠️ 图标生成脚本异常: {e}")
    else:
        print(f"  ✓ 应用图标已就绪: {ICON_FILE}")


def run_pyinstaller() -> bool:
    """阶段一：调用 PyInstaller 生成 onedir 目录"""
    print(f"\n📦 [3/4] 阶段一：正在执行 PyInstaller 打包构建 [{APP_NAME}] (onedir 模式)...")

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        f"--name={APP_NAME}",
        "--onedir",
        "--noconsole",
        "--clean",
        "--noconfirm",
    ]

    if os.path.exists(ICON_FILE):
        cmd.append(f"--icon={ICON_FILE}")

    data_sep = ";" if os.name == "nt" else ":"
    for resource_dir in ["data", "assets"]:
        if os.path.exists(resource_dir):
            cmd.append(f"--add-data={resource_dir}{data_sep}{resource_dir}")

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

    cmd.append(MAIN_ENTRY)

    print(f"  > 执行指令: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"❌ PyInstaller 构建失败，退出码: {result.returncode}")
        return False

    dist_exe = os.path.join("dist", APP_NAME, f"{APP_NAME}.exe")
    if os.path.exists(dist_exe):
        size_mb = os.path.getsize(dist_exe) / (1024 * 1024)
        print(f"  ✓ PyInstaller 构建成功！主程序: {os.path.abspath(dist_exe)} ({size_mb:.2f} MB)")
        return True
    else:
        print(f"❌ 未找到生成的 exe 文件: {dist_exe}")
        return False


def find_iscc_compiler() -> Optional[str]:
    """多策略智能探测系统中的 Inno Setup 编译器 (ISCC.exe)"""
    # 1. 优先检查 PATH 环境变量
    which_iscc = shutil.which("ISCC.exe") or shutil.which("iscc")
    if which_iscc and os.path.isfile(which_iscc):
        return which_iscc

    # 2. 检查常见安装绝对路径 (包含 Inno Setup 7, 6, 5 及各盘根目录)
    candidate_paths = [
        r"D:\Inno Setup 7\ISCC.exe",
        r"C:\Program Files\Inno Setup 7\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
        r"D:\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"E:\Inno Setup 7\ISCC.exe",
        r"E:\Inno Setup 6\ISCC.exe",
    ]
    for path in candidate_paths:
        if os.path.isfile(path):
            return path

    # 3. 检查 Windows 注册表
    try:
        import winreg
        reg_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for root, subkey in reg_keys:
            try:
                with winreg.OpenKey(root, subkey) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as app_key:
                                try:
                                    display_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                                    if "Inno Setup" in str(display_name):
                                        install_loc, _ = winreg.QueryValueEx(app_key, "InstallLocation")
                                        iscc_exe = os.path.join(str(install_loc), "ISCC.exe")
                                        if os.path.isfile(iscc_exe):
                                            return iscc_exe
                                except Exception:
                                    pass
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass

    return None


def run_inno_setup(iscc_path: str) -> bool:
    """阶段二：调用 Inno Setup 编译器编译 installer.iss"""
    print(f"\n💿 [4/4] 阶段二：正在调用 Inno Setup 编译器制作安装向导安装包...")
    print(f"  > 编译器路径: {iscc_path}")

    if not os.path.exists(ISS_FILE):
        print(f"❌ 未找到 Inno Setup 配置文件: {ISS_FILE}")
        return False

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cmd = [iscc_path, ISS_FILE]
    print(f"  > 执行编译: {' '.join(cmd)}")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"❌ Inno Setup 编译失败，返回码: {result.returncode}")
        return False

    out_installer = os.path.join(OUTPUT_DIR, INSTALLER_NAME)
    if os.path.exists(out_installer):
        size_mb = os.path.getsize(out_installer) / (1024 * 1024)
        
        # 计算 MD5
        hasher = hashlib.md5()
        with open(out_installer, "rb") as f:
            while chunk := f.read(8192 * 16):
                hasher.update(chunk)
        file_md5 = hasher.hexdigest()

        print("\n" + "=" * 70)
        print("🎉🎉🎉 安装包全自动制作大功告成！")
        print(f"  ✓ 安装包文件: {os.path.abspath(out_installer)}")
        print(f"  ✓ 安装包大小: {size_mb:.2f} MB")
        print(f"  ✓ 校验 MD5  : {file_md5}")
        print(f"  ✓ 默认安装路径: C:\\Program Files\\KoreanFlashcards")
        print(f"  ✓ 桌面快捷方式: 自动创建 (带专属高清 app_icon.ico)")
        print(f"  ✓ 开始菜单与卸载: 完整集成")
        print("=" * 70)
        return True
    else:
        print(f"❌ 未找到生成的安装包文件: {out_installer}")
        return False


def main():
    print("=" * 70)
    print(f"   「{APP_NAME}」- 全流程一键打包与安装包制作向导")
    print("=" * 70)

    # 1. 清理
    clean_artifacts()

    # 2. 图标检查
    check_and_prepare_icon()

    # 3. 阶段一：PyInstaller
    if not run_pyinstaller():
        sys.exit(1)

    # 4. 阶段二：探测 Inno Setup
    iscc_path = find_iscc_compiler()
    if not iscc_path:
        print("\n" + "!" * 70)
        print("⚠️ 未在系统中检测到 Inno Setup 编译器 (ISCC.exe)！")
        print("  - 第一阶段 PyInstaller 分发包已成功生成于: dist/未来的韩语卡片/")
        print("  - 如需生成独立安装向导 (.exe)，请前往官网下载安装 Inno Setup 7:")
        print("    https://jrsoftware.org/isdl.php")
        print("!" * 70)
        sys.exit(1)

    # 5. 阶段三：Inno Setup 编译
    if not run_inno_setup(iscc_path):
        sys.exit(1)


if __name__ == "__main__":
    main()
