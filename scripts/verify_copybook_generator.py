"""
verify_copybook_generator.py
----------------------------
自动化测试高清手写字帖生成引擎：
1. 测试单页生词导出 PDF & PNG
2. 测试多页生词自动分页导出 PDF & PNG
3. 校验图片分辨率 (2480x3508 @ 300DPI) 与文件有效性
"""

import sys
import os
import traceback
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.copybook_generator import CopybookGenerator

def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)

    test_dir = os.path.join(os.path.dirname(__file__), "test_output")
    os.makedirs(test_dir, exist_ok=True)

    try:
        sample_words = [
            {
                "id": "1_1_01",
                "korean": "안녕하세요",
                "meaning": "你好 / 您好",
                "pronunciation": "annyeonghaseyo",
                "pos": "感叹词",
                "example_kr": "안녕하세요, 저는 김민수입니다.",
                "example_cn": "你好，我是金民秀。"
            },
            {
                "id": "1_1_02",
                "korean": "안녕",
                "meaning": "你好 / 再见",
                "pronunciation": "annyeong",
                "pos": "感叹词",
                "example_kr": "안녕, 오랜만이야!",
                "example_cn": "嗨，好久不见！"
            },
            {
                "id": "1_1_03",
                "korean": "처음 뵙겠습니다",
                "meaning": "初次见面",
                "pronunciation": "cheoeum boepgetseumnida",
                "pos": "表达",
                "example_kr": "처음 뵙겠습니다. 잘 부탁드립니다.",
                "example_cn": "初次见面，请多关照。"
            },
            {
                "id": "1_1_04",
                "korean": "만나서 반갑습니다",
                "meaning": "见到您很高兴",
                "pronunciation": "mannaseo bangapseumnida",
                "pos": "表达",
                "example_kr": "새로운 친구들을 만나서 반갑습니다.",
                "example_cn": "很高兴结识新朋友们。"
            },
            {
                "id": "1_1_05",
                "korean": "도서관",
                "meaning": "图书馆",
                "pronunciation": "doseogwan",
                "pos": "名词",
                "example_kr": "도서관에서 한국어를 공부합니다.",
                "example_cn": "在图书馆学习韩语。"
            }
        ]

        generator = CopybookGenerator()

        # [Test 1] 单页 PDF 导出
        log("[Test 1] Testing single-page PDF generation...")
        pdf_path = os.path.join(test_dir, "test_copybook_single.pdf")
        pdf_files = generator.generate(sample_words, pdf_path, title="韩语基础打卡字帖")
        assert len(pdf_files) == 1, "PDF 返回文件列表异常"
        assert os.path.exists(pdf_path), "PDF 文件未生成"
        pdf_size = os.path.getsize(pdf_path)
        assert pdf_size > 10000, f"PDF 文件大小过小: {pdf_size} bytes"
        log(f"[OK] Single-page PDF created: {pdf_path} ({pdf_size / 1024:.1f} KB)")

        # [Test 2] 单页 PNG 导出与分辨率校验
        log("[Test 2] Testing single-page PNG generation and resolution...")
        png_path = os.path.join(test_dir, "test_copybook_single.png")
        png_files = generator.generate(sample_words, png_path, title="韩语基础打卡字帖")
        assert len(png_files) == 1, "PNG 返回文件列表异常"
        assert os.path.exists(png_path), "PNG 文件未生成"
        with Image.open(png_path) as img:
            assert img.size == (2480, 3508), f"PNG 分辨率非标准 A4 300DPI: {img.size}"
            log(f"[OK] Single-page PNG verified (Size: {img.size}, Mode: {img.mode})")

        # [Test 3] 多页生词 (16 词 = 3 页) PDF 与 PNG 导出
        log("[Test 3] Testing multi-page (16 words -> 3 pages) PDF & PNG...")
        multi_words = sample_words * 3 + [sample_words[0]] # 16 个词
        multi_pdf_path = os.path.join(test_dir, "test_copybook_multi.pdf")
        multi_pdf_files = generator.generate(multi_words, multi_pdf_path, title="延世韩国语 第一册 生词临摹练习本")
        assert os.path.exists(multi_pdf_path), "多页 PDF 文件未生成"
        multi_pdf_size = os.path.getsize(multi_pdf_path)
        log(f"[OK] Multi-page PDF created: {multi_pdf_path} ({multi_pdf_size / 1024:.1f} KB)")

        multi_png_path = os.path.join(test_dir, "test_copybook_multi.png")
        multi_png_files = generator.generate(multi_words, multi_png_path, title="延世韩国语 第一册 生词临摹练习本")
        assert len(multi_png_files) == 3, f"多页 PNG 导出页数不符 (应为 3 页, 实际 {len(multi_png_files)} 页)"
        for pf in multi_png_files:
            assert os.path.exists(pf), f"分页 PNG 文件不存在: {pf}"
        log(f"[OK] Multi-page PNG verified: {len(multi_png_files)} pages generated.")

        log("[SUCCESS] ALL COPYBOOK GENERATOR TESTS PASSED 100%.")

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
    finally:
        with open("test_copybook_result.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

if __name__ == "__main__":
    test()
