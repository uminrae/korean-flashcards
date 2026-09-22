# core/vocab_importer.py
"""外部词库文件解析与导入模块 (支持 CSV / TXT / JSON)"""

import csv
import json
import os
import re
from typing import List, Dict, Tuple, Optional


def parse_csv_or_txt(file_path: str) -> List[Dict]:
    """解析 CSV 或 TXT 格式的词库文件"""
    words = []
    
    # 尝试不同编码打开
    encodings = ["utf-8-sig", "utf-8", "gb18030", "cp949", "euc-kr"]
    content = None
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, Exception):
            continue

    if content is None:
        raise ValueError("无法识别文件编码，请保存为 UTF-8 编码格式")

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return []

    # 自动探测分隔符（逗号、制表符、分号、斜杠、减号）
    sample = lines[0]
    delimiter = ","
    if "\t" in sample:
        delimiter = "\t"
    elif ";" in sample:
        delimiter = ";"
    elif " - " in sample or " — " in sample:
        delimiter = None  # 自定义正则拆分

    header_map = {}
    for idx, line in enumerate(lines, start=1):
        if delimiter:
            # 使用 csv reader 解析
            reader = csv.reader([line], delimiter=delimiter)
            row = next(reader, [])
        else:
            # 正则拆分 " - " 或 " — "
            row = [x.strip() for x in re.split(r"\s+[\-—]\s+", line) if x.strip()]

        if not row:
            continue

        # 智能识别表头并建立列映射
        if idx == 1 and any(h in row[0].lower() for h in ["korean", "word", "韩文", "单词", "hangul"]):
            for col_idx, col_name in enumerate(row):
                c_clean = col_name.strip().lower()
                if any(k in c_clean for k in ["korean", "word", "韩文", "单词", "hangul"]):
                    header_map["korean"] = col_idx
                elif any(k in c_clean for k in ["pron", "音标", "读音", "发音"]):
                    header_map["pronunciation"] = col_idx
                elif any(k in c_clean for k in ["pos", "词性", "性"]):
                    header_map["pos"] = col_idx
                elif any(k in c_clean for k in ["meaning", "释义", "中文", "含义", "解释", "translation"]):
                    header_map["meaning"] = col_idx
                elif any(k in c_clean for k in ["hanja", "汉字", "词源"]):
                    header_map["hanja"] = col_idx
                elif any(k in c_clean for k in ["ex_kr", "例句", "韩文例句", "example"]):
                    header_map["example_kr"] = col_idx
                elif any(k in c_clean for k in ["ex_cn", "翻译", "例句翻译", "中文例句"]):
                    header_map["example_cn"] = col_idx
            continue

        meaning = ""
        hanja = ""
        pos = "名词"
        pron = ""
        ex_kr = ""
        ex_cn = ""

        if header_map:
            # 根据表头映射提取
            kr = row[header_map["korean"]].strip() if "korean" in header_map and len(row) > header_map["korean"] else ""
            if "meaning" in header_map and len(row) > header_map["meaning"]:
                meaning = row[header_map["meaning"]].strip()
            if "pronunciation" in header_map and len(row) > header_map["pronunciation"]:
                pron = row[header_map["pronunciation"]].strip()
            if "pos" in header_map and len(row) > header_map["pos"]:
                pos = row[header_map["pos"]].strip()
            if "hanja" in header_map and len(row) > header_map["hanja"]:
                hanja = row[header_map["hanja"]].strip()
            if "example_kr" in header_map and len(row) > header_map["example_kr"]:
                ex_kr = row[header_map["example_kr"]].strip()
            if "example_cn" in header_map and len(row) > header_map["example_cn"]:
                ex_cn = row[header_map["example_cn"]].strip()
        else:
            # 无表头启发式提取
            kr = row[0].strip() if len(row) > 0 else ""
            if not kr:
                continue

            if len(row) == 2:
                meaning = row[1].strip()
            elif len(row) == 3:
                # 可能是 韩文, 释义, 例句
                meaning = row[1].strip()
                ex_kr = row[2].strip()
            elif len(row) == 4:
                # 可能是 韩文, 汉字词, 释义, 例句
                hanja = row[1].strip()
                meaning = row[2].strip()
                ex_kr = row[3].strip()
            elif len(row) >= 5:
                # 可能是 韩文, 汉字, 读音, 词性, 释义, 例句
                hanja = row[1].strip()
                pron = row[2].strip()
                pos = row[3].strip() if row[3].strip() else "名词"
                meaning = row[4].strip()
                if len(row) >= 6:
                    ex_kr = row[5].strip()
                if len(row) >= 7:
                    ex_cn = row[6].strip()

        if not kr:
            continue

        # 尝试从韩文文本提取括号内的汉字 (如 "학교(學校)")
        if not hanja:
            m = re.search(r"[\(（]([^\)）]+)[\)）]", kr)
            if m:
                extracted = m.group(1).strip()
                # 如果包含汉字字符
                if any('\u4e00' <= ch <= '\u9fff' for ch in extracted):
                    hanja = extracted

        # 推导词性
        if not pos or pos == "名词":
            if kr.endswith("다") or " " in kr:
                if any(kr.endswith(x) for x in ["하다", "가다", "오다", "보다", "먹다", "마시다", "사다", "잡다", "들다", "나다"]):
                    pos = "动词"
                elif any(kr.endswith(x) for x in ["좋다", "크다", "작다", "예쁘다", "멋있다", "어렵다", "쉽다", "있다", "없다"]):
                    pos = "形容词"

        word_obj = {
            "korean": kr,
            "hanja": hanja,
            "pronunciation": pron,
            "pos": pos,
            "meaning": meaning,
            "example_kr": ex_kr,
            "example_cn": ex_cn
        }
        words.append(word_obj)

    return words


def parse_json_file(file_path: str) -> Tuple[str, List[Dict]]:
    """解析 JSON 格式的词库文件，返回 (book_name, words_list)"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    book_name = "我的自定义词库"
    words = []

    if isinstance(data, list):
        # 直接是单词列表
        words = data
    elif isinstance(data, dict):
        book_name = data.get("book_name", data.get("name", "我的自定义词库"))
        if "words" in data and isinstance(data["words"], list):
            words = data["words"]
        elif "lessons" in data and isinstance(data["lessons"], list):
            for l in data["lessons"]:
                for w in l.get("words", []):
                    words.append(w)
        elif "books" in data and isinstance(data["books"], list):
            for b in data["books"]:
                for l in b.get("lessons", []):
                    for w in l.get("words", []):
                        words.append(w)

    return book_name, words


def import_custom_vocab(
    file_path: str,
    vocab_json_path: str = "data/korean_vocab.json",
    custom_book_name: Optional[str] = None
) -> Tuple[bool, int, str, str]:
    """
    统一导入入口：将外部 CSV/TXT/JSON 文件合并导入到 korean_vocab.json 中
    返回: (success: bool, imported_count: int, book_title: str, message: str)
    """
    if not os.path.exists(file_path):
        return False, 0, "", "指定的文件不存在"

    ext = os.path.splitext(file_path)[1].lower()
    raw_words: List[Dict] = []
    book_title = custom_book_name or "我的自定义词库"

    try:
        if ext in [".csv", ".txt"]:
            raw_words = parse_csv_or_txt(file_path)
            # 如果未指定书名，默认使用文件名（不含扩展名）
            if not custom_book_name:
                base_title = os.path.splitext(os.path.basename(file_path))[0]
                book_title = f"自定义: {base_title}"
        elif ext == ".json":
            detected_title, raw_words = parse_json_file(file_path)
            if not custom_book_name and detected_title:
                book_title = detected_title
        else:
            return False, 0, "", f"不支持的文件格式: {ext} (仅支持 .csv, .txt, .json)"
    except Exception as e:
        return False, 0, "", f"文件解析失败: {e}"

    if not raw_words:
        return False, 0, "", "文件中未提取到有效单词条目"

    # 读取现有的 korean_vocab.json
    if not os.path.isabs(vocab_json_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vocab_json_path = os.path.join(base_dir, vocab_json_path)

    try:
        with open(vocab_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        data = {"books": []}

    # 计算新 Book ID
    existing_book_ids = [b.get("book_id", 0) for b in data.get("books", [])]
    new_book_id = (max(existing_book_ids) + 1) if existing_book_ids else 1

    # 将单词按每 15 词分为一课
    LESSON_SIZE = 15
    lessons = []
    for l_idx in range(0, len(raw_words), LESSON_SIZE):
        chunk = raw_words[l_idx : l_idx + LESSON_SIZE]
        lesson_num = (l_idx // LESSON_SIZE) + 1
        unit_num = (lesson_num - 1) // 5 + 1
        sub_lesson_num = (lesson_num - 1) % 5 + 1
        
        lesson_name = f"{unit_num}-{sub_lesson_num} 自定义课时{lesson_num}"
        formatted_words = []

        for w_idx, w in enumerate(chunk, start=1):
            kr = w.get("korean", "").strip()
            meaning = w.get("meaning", w.get("chinese", "")).strip()
            hanja = w.get("hanja", "").strip()
            pron = w.get("pronunciation", "").strip()
            pos = w.get("pos", "名词").strip()
            ex_kr = w.get("example_kr", "").strip()
            ex_cn = w.get("example_cn", "").strip()

            formatted_words.append({
                "id": f"{new_book_id}_{lesson_num}_{w_idx:02d}",
                "korean": kr,
                "hanja": hanja,
                "pronunciation": pron,
                "pos": pos if pos else "名词",
                "meaning": meaning,
                "example_kr": ex_kr,
                "example_cn": ex_cn
            })

        lessons.append({
            "lesson_id": lesson_num,
            "lesson_name": lesson_name,
            "words": formatted_words
        })

    new_book_entry = {
        "book_id": new_book_id,
        "book_name": book_title,
        "lessons": lessons
    }

    # 检查是否已存在同名自定义书，存在则更新，否则追加
    replaced = False
    for i, b in enumerate(data.get("books", [])):
        if b.get("book_name") == book_title:
            new_book_entry["book_id"] = b["book_id"]
            # 重新更新 ID 前缀
            for l in lessons:
                for w in l["words"]:
                    w["id"] = f"{b['book_id']}_{l['lesson_id']}_{w['id'].split('_')[-1]}"
            data["books"][i] = new_book_entry
            replaced = True
            break

    if not replaced:
        data.setdefault("books", []).append(new_book_entry)

    # 写回文件
    with open(vocab_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_words = len(raw_words)
    return True, total_words, book_title, f"成功导入 {total_words} 个词条（包含 {len(lessons)} 课时）到「{book_title}」！"
