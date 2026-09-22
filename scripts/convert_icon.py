# scripts/convert_icon.py
# -*- coding: utf-8 -*-
"""
应用图标转换脚本：
将 assets/ 下的图片文件 (png/jpg) 自动转换为包含多分辨率层级的高清 Windows 标准 .ico 图标文件
分辨率层级包含: [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
"""

import os
import sys
from PIL import Image

ICON_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]


def convert_image_to_ico():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # 优先查找的源图片文件
    candidate_sources = [
        os.path.join(assets_dir, "app_icon.png"),
        os.path.join(assets_dir, "app_icon.jpg"),
        os.path.join(assets_dir, "app_icon.jpeg"),
        os.path.join(assets_dir, "icon.png"),
        os.path.join(assets_dir, "icon.jpg"),
    ]

    source_path = None
    for cand in candidate_sources:
        if os.path.exists(cand):
            source_path = cand
            break

    if not source_path:
        # 扫描 assets 目录下第一个图片
        for f in os.listdir(assets_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
                source_path = os.path.join(assets_dir, f)
                break

    if not source_path:
        print(f"❌ 未在 {assets_dir} 找到任何可用的源图片文件！")
        return False

    print(f"📂 找到源图片文件: {source_path}")
    output_ico = os.path.join(assets_dir, "app_icon.ico")
    output_png = os.path.join(assets_dir, "app_icon.png")

    try:
        with Image.open(source_path) as img:
            # 转换为 RGBA 模式（支持透明度通道）
            img_rgba = img.convert("RGBA")

            # 保存标准高清 PNG (256x256)
            if not os.path.exists(output_png) or os.path.abspath(source_path) != os.path.abspath(output_png):
                img_png = img_rgba.resize((256, 256), Image.Resampling.LANCZOS)
                img_png.save(output_png, format="PNG")
                print(f"  ✓ 高清 PNG 已生成: {output_png}")

            # 保存包含多分辨率层级的 Windows ICO 文件
            img_rgba.save(
                output_ico,
                format="ICO",
                sizes=ICON_SIZES
            )
            print(f"  ✓ Windows 标准多尺寸 ICO 图标生成成功: {output_ico}")
            print(f"    包含尺寸层级: {ICON_SIZES}")
            return True
    except Exception as e:
        print(f"❌ 图标转换失败: {e}")
        return False


if __name__ == "__main__":
    success = convert_image_to_ico()
    if not success:
        sys.exit(1)
