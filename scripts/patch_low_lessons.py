# -*- coding: utf-8 -*-
"""
scripts/patch_low_lessons.py
针对去重后词数不足的 2 课进行专项精准补充
"""
import json, os, shutil
from datetime import datetime

DATA_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data', 'korean_vocab.json'))

# ─── 专项补充词汇（针对 Book1 Lesson27: 6-2 约会时间）───────────────────────
PATCH_BOOK1_L27 = [
    {"korean": "약속 시간", "hanja": "約束 時間", "pronunciation": "yaksok sigan",
     "pos": "名词短语", "meaning": "约定的时间 / 约会时间",
     "example_kr": "약속 시간을 꼭 지켜야 해요.", "example_cn": "一定要遵守约定时间。",
     "word_type": "hanja", "origin": None},
    {"korean": "약속 장소", "hanja": "約束 場所", "pronunciation": "yaksok jangso",
     "pos": "名词短语", "meaning": "约定地点 / 见面地点",
     "example_kr": "약속 장소는 카페입니다.", "example_cn": "见面地点是咖啡馆。",
     "word_type": "hanja", "origin": None},
    {"korean": "몇 시에", "hanja": "", "pronunciation": "myeot sie",
     "pos": "疑问短语", "meaning": "几点（问时间）",
     "example_kr": "몇 시에 만날까요?", "example_cn": "几点见面呢？",
     "word_type": "pure", "origin": None},
    {"korean": "오후", "hanja": "午後", "pronunciation": "ohu",
     "pos": "名词", "meaning": "下午 / 午后",
     "example_kr": "오후 두 시에 만나요.", "example_cn": "下午两点见面。",
     "word_type": "hanja", "origin": None},
    {"korean": "오전", "hanja": "午前", "pronunciation": "ojeon",
     "pos": "名词", "meaning": "上午 / 午前",
     "example_kr": "오전에는 수업이 있어요.", "example_cn": "上午有课。",
     "word_type": "hanja", "origin": None},
    {"korean": "연락하다", "hanja": "連絡하다", "pronunciation": "yeollakada",
     "pos": "动词", "meaning": "联系 / 联络",
     "example_kr": "나중에 연락할게요.", "example_cn": "之后我来联系你。",
     "word_type": "hanja", "origin": None},
    {"korean": "확인하다", "hanja": "確認하다", "pronunciation": "hwakin hada",
     "pos": "动词", "meaning": "确认 / 核实",
     "example_kr": "시간을 다시 확인해요.", "example_cn": "再次确认一下时间。",
     "word_type": "hanja", "origin": None},
]

# ─── 专项补充词汇（针对 Book1 Lesson46: 10-1 交通工具）───────────────────────
PATCH_BOOK1_L46 = [
    {"korean": "지하철", "hanja": "地下鐵", "pronunciation": "jihacheol",
     "pos": "名词", "meaning": "地铁 / 地下铁",
     "example_kr": "지하철을 타고 회사에 가요.", "example_cn": "乘地铁去公司。",
     "word_type": "hanja", "origin": None},
    {"korean": "버스", "hanja": "", "pronunciation": "beoseu",
     "pos": "名词", "meaning": "公共汽车 / 巴士",
     "example_kr": "버스를 타면 30분 걸려요.", "example_cn": "坐公交车要30分钟。",
     "word_type": "loanword", "origin": "bus"},
    {"korean": "택시", "hanja": "", "pronunciation": "taeksi",
     "pos": "名词", "meaning": "出租车 / 的士",
     "example_kr": "비가 오면 택시를 타요.", "example_cn": "下雨时就坐出租车。",
     "word_type": "loanword", "origin": "taxi"},
    {"korean": "자전거", "hanja": "自轉車", "pronunciation": "jajeongeo",
     "pos": "名词", "meaning": "自行车",
     "example_kr": "주말에 자전거를 타요.", "example_cn": "周末骑自行车。",
     "word_type": "hanja", "origin": None},
    {"korean": "도보", "hanja": "徒步", "pronunciation": "dobo",
     "pos": "名词", "meaning": "步行 / 徒步",
     "example_kr": "집에서 도보로 10분 거리예요.", "example_cn": "从家步行10分钟的距离。",
     "word_type": "hanja", "origin": None},
]


def patch_lesson(book, lesson_id, new_words):
    """向指定 lesson 追加词汇，并规范化 ID"""
    existing_korean = set()
    target_lesson = None
    for lesson in book['lessons']:
        if lesson['lesson_id'] == lesson_id:
            target_lesson = lesson
            existing_korean = {w['korean'].strip() for w in lesson.get('words', [])}
            break
    if not target_lesson:
        print(f"  ❌ Lesson {lesson_id} 未找到！")
        return 0
    added = 0
    for w in new_words:
        if w['korean'].strip() not in existing_korean:
            target_lesson['words'].append(w)
            existing_korean.add(w['korean'].strip())
            added += 1
    # Re-assign IDs
    bid = book['book_id']
    for seq, word in enumerate(target_lesson['words'], start=1):
        word['id'] = f"{bid}_{lesson_id}_{seq:02d}"
    return added


def main():
    print("\n🔧 专项补充：针对去重后词数不足的课时进行精准扩充")
    print("─" * 60)

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    book1 = data['books'][0]

    # Patch Lesson 27
    before27 = len(next(l['words'] for l in book1['lessons'] if l['lesson_id'] == 27))
    added27 = patch_lesson(book1, 27, PATCH_BOOK1_L27)
    after27 = len(next(l['words'] for l in book1['lessons'] if l['lesson_id'] == 27))
    print(f"  第1册 Lesson 27 (6-2 约会时间): {before27} → {after27} 词（补充 {added27} 词）")

    # Patch Lesson 46
    before46 = len(next(l['words'] for l in book1['lessons'] if l['lesson_id'] == 46))
    added46 = patch_lesson(book1, 46, PATCH_BOOK1_L46)
    after46 = len(next(l['words'] for l in book1['lessons'] if l['lesson_id'] == 46))
    print(f"  第1册 Lesson 46 (10-1 交通工具): {before46} → {after46} 词（补充 {added46} 词）")

    # Save
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = DATA_FILE + '.bak.' + ts
    shutil.copy2(DATA_FILE, backup)
    tmp = DATA_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(tmp, 'r', encoding='utf-8') as f:
        json.load(f)  # validate
    os.replace(tmp, DATA_FILE)
    print(f"\n  ✓ 写入完成，备份: {os.path.basename(backup)}")
    print(f"  ✓ 共补充 {added27 + added46} 个词条")


if __name__ == '__main__':
    main()
