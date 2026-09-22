# core/font_manager.py
"""自定义外部字体管理器
功能：
1. 自动扫描并加载 data/fonts 目录下的所有本地字体文件 (.ttf / .otf / .ttc)
2. 动态注册字体到 QFontDatabase
3. 支持用户从本地导入并复制字体文件到应用目录
4. 获取包含系统韩文字体与自定义字体的完整列表
"""

import os
import shutil
from typing import List, Tuple
from PyQt6.QtGui import QFontDatabase


def get_fonts_dir() -> str:
    """获取自定义字体存储目录路径（data/fonts），不存在则自动创建"""
    from utils.path_helper import get_data_path
    return get_data_path(os.path.join("data", "fonts"))


def load_custom_fonts() -> List[str]:
    """扫描并向 QFontDatabase 动态注册 data/fonts 和 assets/fonts 目录下的所有字体文件，返回成功注册的字体家族名称列表"""
    from utils.path_helper import get_resource_path
    loaded_families = []
    valid_exts = {".ttf", ".otf", ".ttc"}

    scan_dirs = [get_fonts_dir(), get_resource_path(os.path.join("assets", "fonts")), get_resource_path(os.path.join("data", "fonts"))]
    seen_dirs = set()

    for fonts_dir in scan_dirs:
        if not os.path.exists(fonts_dir) or fonts_dir in seen_dirs:
            continue
        seen_dirs.add(fonts_dir)

        for filename in os.listdir(fonts_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in valid_exts:
                file_path = os.path.join(fonts_dir, filename)
                font_id = QFontDatabase.addApplicationFont(file_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    for fam in families:
                        if fam not in loaded_families:
                            loaded_families.append(fam)
    return loaded_families


def import_font_file(source_path: str) -> Tuple[bool, str, str]:
    """
    将外部字体文件复制到 data/fonts 并动态载入 QFontDatabase
    返回: (是否成功, 字体家族名称, 提示信息)
    """
    if not os.path.exists(source_path):
        return False, "", "所选字体文件不存在！"

    ext = os.path.splitext(source_path)[1].lower()
    if ext not in {".ttf", ".otf", ".ttc"}:
        return False, "", "仅支持 .ttf、.otf 或 .ttc 格式的字体文件！"

    try:
        fonts_dir = get_fonts_dir()
        filename = os.path.basename(source_path)
        dest_path = os.path.join(fonts_dir, filename)

        # 若源路径不是目标路径，则执行复制
        if os.path.abspath(source_path) != os.path.abspath(dest_path):
            shutil.copy2(source_path, dest_path)

        font_id = QFontDatabase.addApplicationFont(dest_path)
        if font_id == -1:
            return False, "", "字体文件解析失败，可能文件已损坏或格式不兼容！"

        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            return False, "", "未能从字体文件中提取到有效的字体名称！"

        family_name = families[0]
        return True, family_name, f"成功导入并激活字体：{family_name}"
    except Exception as e:
        return False, "", f"导入字体时发生错误：{str(e)}"


def get_available_korean_fonts() -> List[Tuple[str, str]]:
    """获取系统中可用的韩文字体列表（含自定义导入字体） [(display_name, font_family), ...]"""
    # 1. 首先加载已导入的自定义字体
    custom_families = load_custom_fonts()
    result = []
    
    for fam in custom_families:
        result.append((f"⭐ [自定义] {fam}", fam))

    # 2. 预设系统韩文字体推荐
    known_korean_fonts = [
        ("맑은 고딕 (Malgun Gothic) - 推荐现代无衬线", "Malgun Gothic"),
        ("나눔고딕 (NanumGothic) - 精致黑体", "NanumGothic"),
        ("바탕 (Batang) - 传统明朝衬线体", "Batang"),
        ("궁서 (Gungsuh) - 古典书法手写体", "Gungsuh"),
        ("돋움 (Dotum) - 紧凑黑体", "Dotum"),
        ("굴림 (Gulim) - 经典圆体", "Gulim"),
        ("微软雅黑 (Microsoft YaHei)", "Microsoft YaHei"),
        ("Segoe UI (系统默认)", "Segoe UI"),
    ]

    all_system_families = set(QFontDatabase.families())
    
    for display_name, family in known_korean_fonts:
        if family in all_system_families:
            if not any(family == r[1] for r in result):
                result.append((display_name, family))

    # 3. 扫描系统其他韩文/CJK 字体
    for family in sorted(all_system_families):
        if not any(family == r[1] for r in result):
            f_lower = family.lower()
            if any(k in f_lower for k in ["nanum", "korean", "gothic", "cjk", "hangul"]):
                result.append((family, family))

    if not result:
        result.append(("Malgun Gothic", "Malgun Gothic"))
        
    return result
