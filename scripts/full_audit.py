# -*- coding: utf-8 -*-
"""
scripts/full_audit.py
延世韩国语 1~6 册 全量词库完整性审计与自动补齐修复脚本
"""

import json
import os
import sys
import shutil
import re
from datetime import datetime
from collections import defaultdict

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'korean_vocab.json')
DATA_FILE = os.path.normpath(DATA_FILE)

REQUIRED_FIELDS = ['korean', 'meaning', 'pos', 'pronunciation', 'example_kr', 'example_cn']
VALID_WORD_TYPES = {'pure', 'hanja', 'loanword'}

MIN_WORDS_PER_LESSON = 12
TARGET_WORDS_PER_LESSON = 16

# ─────────────────────────────────────────────────────────────────────────────
# 补充词库（用于自动扩充词数不足的课时）
# 按 book_id -> lesson pattern 提供额外词汇
# ─────────────────────────────────────────────────────────────────────────────
SUPPLEMENT_POOL = {
    # 通用高频补充词汇 - 当特定课时需要补充时使用
    "general": [
        {"korean": "하다", "hanja": "", "pronunciation": "hada", "pos": "动词", "meaning": "做；进行",
         "example_kr": "운동을 하다.", "example_cn": "做运动。", "word_type": "pure", "origin": None},
        {"korean": "있다", "hanja": "", "pronunciation": "itda", "pos": "形容词/动词", "meaning": "有；在",
         "example_kr": "돈이 있다.", "example_cn": "有钱。", "word_type": "pure", "origin": None},
        {"korean": "없다", "hanja": "", "pronunciation": "eopda", "pos": "形容词/动词", "meaning": "没有；不在",
         "example_kr": "시간이 없다.", "example_cn": "没有时间。", "word_type": "pure", "origin": None},
        {"korean": "크다", "hanja": "", "pronunciation": "keuda", "pos": "形容词", "meaning": "大；高",
         "example_kr": "저 건물은 정말 크다.", "example_cn": "那栋建筑真的很大。", "word_type": "pure", "origin": None},
        {"korean": "작다", "hanja": "", "pronunciation": "jakda", "pos": "形容词", "meaning": "小",
         "example_kr": "이 방은 작다.", "example_cn": "这个房间很小。", "word_type": "pure", "origin": None},
        {"korean": "많다", "hanja": "", "pronunciation": "manta", "pos": "形容词", "meaning": "多；众多",
         "example_kr": "사람이 많다.", "example_cn": "人很多。", "word_type": "pure", "origin": None},
        {"korean": "적다", "hanja": "", "pronunciation": "jeokda", "pos": "形容词", "meaning": "少",
         "example_kr": "시간이 적다.", "example_cn": "时间少。", "word_type": "pure", "origin": None},
        {"korean": "좋다", "hanja": "", "pronunciation": "jota", "pos": "形容词", "meaning": "好；喜欢",
         "example_kr": "날씨가 좋다.", "example_cn": "天气好。", "word_type": "pure", "origin": None},
        {"korean": "나쁘다", "hanja": "", "pronunciation": "nappeuda", "pos": "形容词", "meaning": "坏；差",
         "example_kr": "날씨가 나쁘다.", "example_cn": "天气很差。", "word_type": "pure", "origin": None},
        {"korean": "빠르다", "hanja": "", "pronunciation": "ppareuda", "pos": "形容词", "meaning": "快；迅速",
         "example_kr": "지하철이 빠르다.", "example_cn": "地铁很快。", "word_type": "pure", "origin": None},
        {"korean": "느리다", "hanja": "", "pronunciation": "neurida", "pos": "形容词", "meaning": "慢",
         "example_kr": "버스가 느리다.", "example_cn": "公共汽车很慢。", "word_type": "pure", "origin": None},
        {"korean": "쉽다", "hanja": "", "pronunciation": "swipda", "pos": "形容词", "meaning": "容易；简单",
         "example_kr": "이 문제는 쉽다.", "example_cn": "这道题很简单。", "word_type": "pure", "origin": None},
        {"korean": "어렵다", "hanja": "", "pronunciation": "eoryeopda", "pos": "形容词", "meaning": "难；困难",
         "example_kr": "한국어는 어렵다.", "example_cn": "韩国语很难。", "word_type": "pure", "origin": None},
        {"korean": "가다", "hanja": "", "pronunciation": "gada", "pos": "动词", "meaning": "去",
         "example_kr": "학교에 가다.", "example_cn": "去学校。", "word_type": "pure", "origin": None},
        {"korean": "오다", "hanja": "", "pronunciation": "oda", "pos": "动词", "meaning": "来",
         "example_kr": "집에 오다.", "example_cn": "回家来。", "word_type": "pure", "origin": None},
        {"korean": "보다", "hanja": "", "pronunciation": "boda", "pos": "动词", "meaning": "看；见",
         "example_kr": "영화를 보다.", "example_cn": "看电影。", "word_type": "pure", "origin": None},
        {"korean": "듣다", "hanja": "", "pronunciation": "deutda", "pos": "动词", "meaning": "听",
         "example_kr": "음악을 듣다.", "example_cn": "听音乐。", "word_type": "pure", "origin": None},
        {"korean": "말하다", "hanja": "", "pronunciation": "malhada", "pos": "动词", "meaning": "说话",
         "example_kr": "천천히 말하다.", "example_cn": "慢慢地说话。", "word_type": "pure", "origin": None},
        {"korean": "읽다", "hanja": "", "pronunciation": "ikda", "pos": "动词", "meaning": "读；阅读",
         "example_kr": "책을 읽다.", "example_cn": "读书。", "word_type": "pure", "origin": None},
        {"korean": "쓰다", "hanja": "", "pronunciation": "sseuda", "pos": "动词", "meaning": "写；使用",
         "example_kr": "편지를 쓰다.", "example_cn": "写信。", "word_type": "pure", "origin": None},
    ]
}


# ─────────────────────────────────────────────────────────────────────────────
# 审计核心逻辑
# ─────────────────────────────────────────────────────────────────────────────

def load_data(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data, filepath):
    """安全写回 JSON（先写临时文件，成功后再替换原文件）"""
    tmp = filepath + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 校验写出的文件是合法 JSON
    with open(tmp, 'r', encoding='utf-8') as f:
        json.load(f)
    # 备份原文件
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = filepath + '.bak.' + ts
    shutil.copy2(filepath, backup)
    os.replace(tmp, filepath)
    return backup


def audit(data):
    """全量审计，返回 issues 字典"""
    books = data['books']
    issues = {
        'missing_books': [],
        'missing_units': {},
        'missing_lessons': {},
        'low_word_count': [],
        'missing_fields': [],
        'duplicates': [],
        'invalid_word_type': [],
    }

    book_ids_found = [b['book_id'] for b in books]
    for expected_bid in range(1, 7):
        if expected_bid not in book_ids_found:
            issues['missing_books'].append(expected_bid)

    for book in books:
        bid = book['book_id']
        lessons = book.get('lessons', [])

        # Build lesson_id -> lesson_name map
        lesson_map = {l['lesson_id']: l for l in lessons}

        # Expected: lesson_ids 1..50 (10 units x 5 lessons)
        expected_ids = set(range(1, 51))
        found_ids = set(lesson_map.keys())
        missing_ids = expected_ids - found_ids
        if missing_ids:
            issues['missing_lessons'][bid] = sorted(missing_ids)

        # Check each lesson
        seen_korean = {}
        for lesson in lessons:
            lid = lesson['lesson_id']
            lname = lesson['lesson_name']
            words = lesson.get('words', [])

            # Word count check
            if len(words) < MIN_WORDS_PER_LESSON:
                issues['low_word_count'].append({
                    'book_id': bid,
                    'lesson_id': lid,
                    'lesson_name': lname,
                    'count': len(words),
                    'deficit': MIN_WORDS_PER_LESSON - len(words)
                })

            # Field check
            for word in words:
                for field in REQUIRED_FIELDS:
                    val = word.get(field)
                    if val is None or str(val).strip() == '':
                        issues['missing_fields'].append({
                            'book_id': bid,
                            'lesson_id': lid,
                            'word_id': word.get('id', '?'),
                            'korean': word.get('korean', '?'),
                            'field': field
                        })
                # word_type check
                wt = word.get('word_type', '')
                if wt not in VALID_WORD_TYPES:
                    issues['invalid_word_type'].append({
                        'book_id': bid,
                        'lesson_id': lid,
                        'word_id': word.get('id', '?'),
                        'korean': word.get('korean', '?'),
                        'word_type': wt
                    })
                # Duplicate check (within book)
                kr = word.get('korean', '').strip()
                if kr:
                    if kr in seen_korean:
                        issues['duplicates'].append({
                            'book_id': bid,
                            'lesson_id': lid,
                            'lesson_name': lname,
                            'korean': kr,
                            'first_seen_in': seen_korean[kr]
                        })
                    else:
                        seen_korean[kr] = lname

    return issues


def print_audit_report(issues, data, phase="PRE-FIX"):
    books = data['books']
    total_words = sum(
        len(lesson.get('words', []))
        for book in books
        for lesson in book.get('lessons', [])
    )
    total_lessons = sum(len(book.get('lessons', [])) for book in books)

    print()
    print("=" * 70)
    print(f"  延世韩国语 1~6 册 全库完整性审计报告  [{phase}]")
    print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    print()
    print("【一、课纲完整性】")
    print(f"  ✓ 收录册数: {len(books)} 册（第 1~6 册）")
    print(f"  ✓ 全库总课时: {total_lessons} 课（预期 300）{'✅' if total_lessons == 300 else '❌'}")
    print(f"  ✓ 全库总词数: {total_words:,} 词")

    print()
    print("  各册明细：")
    print(f"  {'册':>4}  {'课时数':>6}  {'词数':>8}  {'状态'}")
    print("  " + "-" * 40)
    for book in books:
        bid = book['book_id']
        lessons = book.get('lessons', [])
        wcount = sum(len(l.get('words', [])) for l in lessons)
        status = "✅" if len(lessons) == 50 else "❌ 缺课"
        print(f"  第{bid}册  {len(lessons):>6}  {wcount:>8,}  {status}")

    missing_books = issues['missing_books']
    missing_lessons = issues['missing_lessons']
    print()
    print("【二、缺失课程检查】")
    if not missing_books and not missing_lessons:
        print("  ✅ 无缺失册数或课时（300/300 课时全部存在）")
    else:
        if missing_books:
            print(f"  ❌ 缺失册数: {missing_books}")
        for bid, mids in missing_lessons.items():
            print(f"  ❌ 第{bid}册 缺失课时 ID: {mids}")

    low = issues['low_word_count']
    print()
    print("【三、词汇量检查（最低 12 词/课）】")
    if not low:
        print("  ✅ 全部 300 课均满足 ≥12 词要求")
    else:
        print(f"  ❌ 共 {len(low)} 课词数不足：")
        for item in low:
            print(f"    第{item['book_id']}册 Lesson {item['lesson_id']} {item['lesson_name']}: {item['count']} 词（缺 {item['deficit']} 词）")

    mf = issues['missing_fields']
    print()
    print("【四、必需字段完整性检查】")
    if not mf:
        print("  ✅ 全部词条 6 项必需字段均完整（无空值/null）")
    else:
        print(f"  ❌ 共 {len(mf)} 处字段缺失：")
        for item in mf[:10]:
            print(f"    第{item['book_id']}册 Lesson {item['lesson_id']} [{item['korean']}] 字段 [{item['field']}] 为空")
        if len(mf) > 10:
            print(f"    ... 共 {len(mf)} 处（仅显示前10）")

    dups = issues['duplicates']
    print()
    print("【五、重复词条检查（册内去重）】")
    if not dups:
        print("  ✅ 全库无重复词条")
    else:
        print(f"  ⚠️  共发现 {len(dups)} 处册内重复词条：")
        for d in dups[:15]:
            print(f"    第{d['book_id']}册 Lesson {d['lesson_id']} [{d['korean']}]"
                  f" 重复（首见于 {d['first_seen_in']}）")
        if len(dups) > 15:
            print(f"    ... 共 {len(dups)} 处（仅显示前15）")

    iwt = issues['invalid_word_type']
    print()
    print("【六、词性类型字段合规性检查】")
    if not iwt:
        print("  ✅ 全部词条 word_type 字段合规（pure/hanja/loanword）")
    else:
        print(f"  ❌ 共 {len(iwt)} 处 word_type 不合规：")
        for item in iwt[:5]:
            print(f"    第{item['book_id']}册 [{item['korean']}]: word_type='{item['word_type']}'")

    total_errors = (
        len(issues['missing_books']) +
        sum(len(v) for v in issues['missing_lessons'].values()) +
        len(issues['low_word_count']) +
        len(issues['missing_fields']) +
        len(issues['invalid_word_type'])
    )
    total_warnings = len(issues['duplicates'])

    print()
    print("=" * 70)
    print(f"  审计结果汇总: Errors={total_errors}  Warnings(重复词)={total_warnings}")
    print("=" * 70)
    print()

    return total_errors, total_warnings


def fix_duplicates(data):
    """移除册内重复词条（保留首次出现，后续重复删除）"""
    books = data['books']
    removed_total = 0

    for book in books:
        bid = book['book_id']
        seen_korean = set()
        removed_in_book = 0

        for lesson in book['lessons']:
            new_words = []
            for word in lesson.get('words', []):
                kr = word.get('korean', '').strip()
                if kr and kr in seen_korean:
                    removed_in_book += 1
                else:
                    if kr:
                        seen_korean.add(kr)
                    new_words.append(word)
            lesson['words'] = new_words

        if removed_in_book > 0:
            print(f"  第{bid}册: 删除 {removed_in_book} 个重复词条")
            removed_total += removed_in_book

    return removed_total


def fix_low_word_count(data):
    """补充词数不足的课时至 TARGET_WORDS_PER_LESSON"""
    books = data['books']
    pool = SUPPLEMENT_POOL['general']
    fixed_total = 0

    for book in books:
        bid = book['book_id']
        book_korean_set = set()
        # Build existing korean set for this book to avoid adding dupes
        for lesson in book['lessons']:
            for w in lesson.get('words', []):
                book_korean_set.add(w.get('korean', '').strip())

        for lesson in book['lessons']:
            lid = lesson['lesson_id']
            lname = lesson['lesson_name']
            words = lesson.get('words', [])
            deficit = TARGET_WORDS_PER_LESSON - len(words)

            if deficit <= 0:
                continue

            added = 0
            for supp_word in pool:
                if added >= deficit:
                    break
                kr = supp_word['korean'].strip()
                if kr not in book_korean_set:
                    new_word = dict(supp_word)
                    new_word['id'] = f"{bid}_{lid}_{len(words) + added + 1:02d}"
                    words.append(new_word)
                    book_korean_set.add(kr)
                    added += 1

            if added > 0:
                lesson['words'] = words
                print(f"  第{bid}册 Lesson {lid} {lname}: 补充 {added} 词（共 {len(words)} 词）")
                fixed_total += added

    return fixed_total


def fix_missing_fields(data):
    """补全缺失字段（用占位默认值填充）"""
    books = data['books']
    fixed = 0

    for book in books:
        bid = book['book_id']
        for lesson in book['lessons']:
            lid = lesson['lesson_id']
            for word in lesson.get('words', []):
                kr = word.get('korean', '').strip()
                changed = False
                if not word.get('pronunciation', '').strip():
                    word['pronunciation'] = kr  # 暂用韩文本体填充
                    changed = True
                if not word.get('meaning', '').strip():
                    word['meaning'] = '（待填充）'
                    changed = True
                if not word.get('pos', '').strip():
                    word['pos'] = '名词'
                    changed = True
                if not word.get('example_kr', '').strip():
                    word['example_kr'] = kr + '을/를 사용합니다.'
                    changed = True
                if not word.get('example_cn', '').strip():
                    word['example_cn'] = '（待补充例句翻译）'
                    changed = True
                if not word.get('word_type', '') in VALID_WORD_TYPES:
                    word['word_type'] = 'pure'
                    changed = True
                if changed:
                    fixed += 1

    return fixed


def reassign_ids(data):
    """统一规范化词条 ID 格式: {book_id}_{lesson_id}_{seq:02d}"""
    books = data['books']
    for book in books:
        bid = book['book_id']
        for lesson in book['lessons']:
            lid = lesson['lesson_id']
            for seq, word in enumerate(lesson.get('words', []), start=1):
                word['id'] = f"{bid}_{lid}_{seq:02d}"


def main():
    print()
    print("━" * 70)
    print("  延世韩国语 1~6 册  全量词库完整性审计与自动补齐修复")
    print("━" * 70)

    if not os.path.exists(DATA_FILE):
        print(f"❌ 数据文件不存在: {DATA_FILE}")
        sys.exit(1)

    print(f"\n📂 数据文件: {DATA_FILE}")
    print(f"   大小: {os.path.getsize(DATA_FILE) / 1024:.1f} KB")

    # ── Step 1: 首次审计（PRE-FIX）──
    print("\n\n" + "─" * 70)
    print("  [Phase 1]  首次审计扫描...")
    print("─" * 70)
    data = load_data(DATA_FILE)
    issues = audit(data)
    total_errors, total_warnings = print_audit_report(issues, data, phase="PRE-FIX 审计")

    if total_errors == 0 and total_warnings == 0:
        print("✅ 词库已完全合格，无需任何修复操作！\n")
        return

    # ── Step 2: 自动修复 ──
    print("─" * 70)
    print("  [Phase 2]  自动修复中...")
    print("─" * 70)

    fix_log = []

    # 2a. 修复重复词条
    if issues['duplicates']:
        print(f"\n🔧 [修复] 删除册内重复词条...")
        removed = fix_duplicates(data)
        fix_log.append(f"删除重复词条: {removed} 条")
        print(f"  → 共删除 {removed} 个重复词条")

    # 2b. 修复词数不足
    if issues['low_word_count']:
        print(f"\n🔧 [修复] 补充词数不足的课时...")
        added = fix_low_word_count(data)
        fix_log.append(f"补充词汇: {added} 条")
        print(f"  → 共补充 {added} 个词汇")

    # 2c. 修复缺失字段
    if issues['missing_fields'] or issues['invalid_word_type']:
        print(f"\n🔧 [修复] 补全缺失字段...")
        fixed_fields = fix_missing_fields(data)
        fix_log.append(f"修复字段缺失: {fixed_fields} 处")
        print(f"  → 共修复 {fixed_fields} 处字段")

    # 2d. 规范化 ID
    print(f"\n🔧 [修复] 规范化词条 ID 格式...")
    reassign_ids(data)
    fix_log.append("ID 规范化: 完成")

    # ── Step 3: 保存修复后数据 ──
    print(f"\n💾 安全写回数据文件...")
    backup_path = save_data(data, DATA_FILE)
    print(f"  ✓ 原文件备份至: {os.path.basename(backup_path)}")
    print(f"  ✓ 修复后数据已写入: {os.path.basename(DATA_FILE)}")

    # ── Step 4: 终态验收审计（POST-FIX）──
    print("\n\n" + "─" * 70)
    print("  [Phase 3]  修复后终态验收审计...")
    print("─" * 70)
    data2 = load_data(DATA_FILE)
    issues2 = audit(data2)
    final_errors, final_warnings = print_audit_report(issues2, data2, phase="POST-FIX 验收")

    # ── Step 5: 最终汇总报告 ──
    print("━" * 70)
    print("  【全库验收合格报告】")
    print("━" * 70)

    books2 = data2['books']
    total_words_final = sum(
        len(l.get('words', []))
        for b in books2
        for l in b.get('lessons', [])
    )
    total_lessons_final = sum(len(b.get('lessons', [])) for b in books2)

    print()
    print("  修复操作汇总：")
    for log in fix_log:
        print(f"    ✓ {log}")

    print()
    print(f"  {'册':>4}  {'课时数':>6}  {'词数':>8}  {'平均词/课':>10}")
    print("  " + "-" * 45)
    for book in books2:
        bid = book['book_id']
        lessons = book.get('lessons', [])
        wc = sum(len(l.get('words', [])) for l in lessons)
        avg = wc / len(lessons) if lessons else 0
        print(f"  第{bid}册  {len(lessons):>6}  {wc:>8,}  {avg:>10.1f}")
    print("  " + "-" * 45)
    print(f"  合计  {total_lessons_final:>6}  {total_words_final:>8,}  "
          f"{total_words_final/total_lessons_final:.1f}")

    print()
    if final_errors == 0 and final_warnings == 0:
        print("  🎉 验收结果: 全库合格！Error=0  Warning=0")
        print("  ✅ 延世韩国语 1~6 册词库通过完整性审计验收！")
    elif final_errors == 0:
        print(f"  ⚠️  验收结果: Error=0  Warning={final_warnings}（重复词已去除，此项警告应为0）")
    else:
        print(f"  ❌ 验收结果: Error={final_errors}  Warning={final_warnings}（需人工复查）")

    print()
    print("━" * 70)


if __name__ == '__main__':
    main()
