# process_icon.py
# -*- coding: utf-8 -*-
"""
高清应用图标圆角与透明遮罩处理脚本
功能：
1. 采用 4x 超采样（Supersampling）+ LANCZOS 抗锯齿技术，实现极致丝滑的圆角/纯圆透明裁剪
2. 支持两种现代图标样式：
   - squircle (默认推荐): iOS / macOS 风格现代大圆角（圆角率约 22.5%）
   - circle: 纯正圆形裁剪
3. 自动生成高清 assets/app_icon.png 与包含多分辨率层级的 Windows 标准 assets/app_icon.ico
   尺寸层级: 256x256, 128x128, 64x64, 48x48, 32x32, 16x16
"""

import os
import sys
import argparse
from PIL import Image, ImageDraw

ICON_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
TARGET_SIZE = 512  # 基准高清处理尺寸 (512x512)
SUPERSAMPLE_SCALE = 4  # 4倍超采样以达到极致平滑无毛边


def crop_to_square(img: Image.Image) -> Image.Image:
    """将图片从中心正方形居中裁剪 (1:1 比例)"""
    width, height = img.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    right = left + min_dim
    bottom = top + min_dim
    return img.crop((left, top, right, bottom))


def generate_antialiased_mask(size: int, shape: str = "squircle", radius_ratio: float = 0.225) -> Image.Image:
    """
    使用 4x 超采样绘制高分辨率 Alpha 遮罩，并通过 LANCZOS 缩小，生成零锯齿的丝滑羽化边缘
    """
    hires_size = size * SUPERSAMPLE_SCALE
    mask_hires = Image.new("L", (hires_size, hires_size), 0)
    draw = ImageDraw.Draw(mask_hires)

    if shape == "circle":
        # 纯圆裁剪
        draw.ellipse([0, 0, hires_size - 1, hires_size - 1], fill=255)
    else:
        # 现代大圆角 (Squircle) 风格
        radius = int(hires_size * radius_ratio)
        draw.rounded_rectangle(
            [0, 0, hires_size - 1, hires_size - 1],
            radius=radius,
            fill=255
        )

    # LANCZOS 平滑缩小至目标尺寸，边缘自动形成亚像素级平滑抗锯齿渐变
    smooth_mask = mask_hires.resize((size, size), Image.Resampling.LANCZOS)
    return smooth_mask


def process_icon(shape: str = "squircle", radius_ratio: float = 0.225):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # 优先使用原始的 jpg 高清图，若无则使用现有 png
    source_candidates = [
        os.path.join(assets_dir, "app_icon.jpg"),
        os.path.join(assets_dir, "app_icon.png"),
        os.path.join(assets_dir, "app_icon.jpeg"),
    ]

    source_path = None
    for cand in source_candidates:
        if os.path.exists(cand):
            source_path = cand
            break

    if not source_path:
        print(f"❌ 未找到源图片文件！请检查 {assets_dir} 目录。")
        return False

    print(f"📂 读取源图片: {source_path}")
    print(f"🎨 裁剪样式: {'现代大圆角 (Squircle)' if shape == 'squircle' else '纯正圆形 (Circle)'}")

    try:
        with Image.open(source_path) as raw_img:
            # 1. 转换为 RGBA
            img_rgba = raw_img.convert("RGBA")

            # 2. 居中 1:1 正方形裁剪
            square_img = crop_to_square(img_rgba)

            # 3. 缩放到标准基准分辨率
            resized_img = square_img.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)

            # 4. 生成 4x 超采样抗锯齿 Alpha 遮罩
            smooth_mask = generate_antialiased_mask(TARGET_SIZE, shape=shape, radius_ratio=radius_ratio)

            # 5. 应用遮罩，四周多余区域完全透明化
            final_img = Image.new("RGBA", (TARGET_SIZE, TARGET_SIZE), (0, 0, 0, 0))
            final_img.paste(resized_img, (0, 0), mask=smooth_mask)

            # 6. 保存高质量 PNG
            out_png = os.path.join(assets_dir, "app_icon.png")
            final_img.save(out_png, format="PNG", optimize=True)
            print(f"  ✓ 高清透明 PNG 已更新: {out_png} ({TARGET_SIZE}x{TARGET_SIZE})")

            # 7. 生成多分辨率层级 Windows ICO 文件
            out_ico = os.path.join(assets_dir, "app_icon.ico")
            final_img.save(
                out_ico,
                format="ICO",
                sizes=ICON_SIZES
            )
            print(f"  ✓ Windows 标准多尺寸 ICO 已生成: {out_ico}")
            print(f"    包含尺寸层级: {ICON_SIZES}")

            return True

    except Exception as e:
        print(f"❌ 图标处理失败: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="高清应用图标圆角与透明遮罩生成工具")
    parser.add_argument(
        "--shape",
        choices=["squircle", "circle"],
        default="squircle",
        help="裁剪形状：squircle (现代大圆角，默认) 或 circle (纯圆形)"
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=0.225,
        help="圆角率 (0.0~0.5，默认为 0.225 即宽度的 22.5%%)"
    )
    args = parser.parse_args()

    success = process_icon(shape=args.shape, radius_ratio=args.radius)
    if not success:
        sys.exit(1)
