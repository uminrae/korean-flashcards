# core/vocab_manager.py
"""词库加载与三级筛选逻辑（支持 册 -> 单元 -> 课程 三级联动 / 随机乱序 / 掌握度标记）"""

import json
import os
import re
import random
from typing import List, Dict, Optional, Tuple, Set
from core.pronunciation_rules import analyze_pronunciation

GLOBAL_NUANCE_DIFFS = {
    '생각하다': '생각하다(普通思考/想起/主观认为) vs 고민하다(内心苦恼纠结/慎重权衡)',
    '고민하다': '고민하다(陷入苦恼焦虑/权衡抉择) vs 생각하다(日常脑海中想/考虑)',
    '예쁘다': '예쁘다(五官外貌可爱甜美、小巧精致) vs 아름답다(壮丽风景、艺术或心灵宏大之美)',
    '아름답다': '아름답다(偏书面语的深邃壮丽之美) vs 예쁘다(日常口语视觉上的漂亮)',
    '보다': '보다(视线注视/看书/看电视) vs 구경하다(走动游览、逛街看热闹)',
    '구경하다': '구경하다(观光/游览看热闹) vs 보다(简单用眼睛看)',
    '배우다': '배우다(从他人处获得技能手艺/跟随老师) vs 공부하다(自主坐下钻研书本文理功课)',
    '공부하다': '공부하다(学校学业/自主复习自习) vs 배우다(跟师傅老师学习技能)',
    '모이다': '모이다(自动词：人群/事物自发聚集) vs 모으다(他动词：主动收集积攒财富物品)',
    '모으다': '모으다(他动词：主动收集/积攒) vs 모이다(自动词：自然汇聚集合)',
    '맞다': '맞다(正确/符合标准/对的) vs 틀리다(错误/不同/不符)',
    '틀리다': '틀리다(是非对错上的错误) vs 다르다(事物性质特征上的不同)',
    '다르다': '다르다(事物性质/特征存在差异) vs 틀리다(对错是非上的错误)',
    '가르치다': '가르치다(传授知识教学) vs 가리키다(用手指指向某人或方向)',
    '가리키다': '가리키다(指示方向或目标) vs 가르치다(传授知识)',
    '빌리다': '빌리다(借入他人之物) vs 빌려주다(借出给他人使用)',
    '빌려주다': '빌려주达(借给别人) vs 빌리다(向别人借)',
    '잃다': '잃다(遗失具体实物/迷失方向) vs 잊다(大脑遗忘记忆/忘掉事情)',
    '잊다': '잊다(大脑遗忘事物/忘记记忆) vs 잃다(丢失具体实物)',
    '기다리다': '기다리다(等待时间/人物到来) vs 기대하다(心中满怀期盼与愿望)',
    '기대하다': '기대하다(心怀期待向往) vs 기다리다(耐着性子等待)',
    '알다': '알다(知晓事实信息/认识某人) vs 이해하다(深入理解掌握原理原因)',
    '이해하다': '이해하다(理解掌握逻辑原理) vs 알다(单纯知晓信息)',
    '크다': '크다(体积/尺度/年龄宏大) vs 넓다(面积/胸襟宽阔开阔)',
    '넓다': '넓다(平面面积宽阔) vs 크다(立体体积高大)',
    '작다': '작다(体积/尺度/身高小) vs 좁다(面积/空间狭窄)',
    '좁다': '좁다(空间狭窄) vs 작다(体积极小)',
    '빠르다': '빠르다(速度迅捷/时间过早) vs 이르다(时刻偏早/尚未到时候)',
    '이르다': '이르다(时刻偏早/为时尚早) vs 빠르다(移动速度飞快)',
    '늦다': '늦다(时间迟了/上学迟到) vs 느리다(动作/速度迟缓缓慢)',
    '느리다': '느리다(行动速度慢腾腾) vs 늦다(超过规定时间而迟到)',
    '바쁘다': '바쁘다(事务繁多抽不开身) vs 급하다(性子急躁/事情危急刻不容缓)',
    '급하다': '급하다(事态危急/脾气急躁) vs 바쁘다(日程繁忙琐事多)',
    '좋다': '좋다(形容词：品质优秀/令人喜爱) vs 좋아하다(他动词：主观主动喜欢某物)',
    '좋아하다': '좋아하다(他动词：主动喜欢) vs 좋다(形容词：客观性质好)',
    '싫다': '싫다(形容词：令人厌烦抗拒) vs 싫어하다(他动词：主观主动讨厌)',
    '싫어하다': '싫어하다(他动词：主动厌恶) vs 싫다(形容词：客观上讨厌)',
    '만나다': '만나다(约定见面/偶然相遇) vs 뵙다(谦语：拜见长辈/谒见老师)',
    '먹다': '먹다(日常食用口语) vs 드시다(尊称敬语：长辈请用餐)',
    '자다': '자다(日常睡觉口语) vs 주무시다(尊称敬语：长辈就寝安睡)',
    '말하다': '말하다(日常说话表达) vs 말씀하시다(尊称敬语：长辈讲话垂询)',
    '있다': '있다(存在/拥有/在某处) vs 계시다(尊称敬语：长辈在某处)',
    '죽다': '죽다(生物死亡口语) vs 돌아가시다(婉转尊称：仙逝长眠/逝世)',
    '묻다': '묻다(向他人询问打听) vs 질문하다(正式提出疑问/提问)',
    '끝나다': '끝나다(自动词：事情自然结束告终) vs 끝내다(他动词：主动完成做完)',
    '끝내다': '끝내다(他动词：主动完成任务) vs 끝나다(自动词：活动自然收尾)',
    '열리다': '열리다(自动词：门自然敞开/活动举行) vs 열다(他动词：主动推开门)',
    '열다': '열다(他动词：主动推开门) vs 열리다(自动词：门被推开/自然开启)',
    '닫히다': '닫히다(自动词：门被风关上) vs 닫다(他动词：主动关上门)',
    '닫다': '닫다(他动词：主动关上门) vs 닫히다(自动词：门自然关上)',
    '시작되다': '시작되다(自动词：学期/活动自发开启) vs 시작하다(他动词：主动着手开展)',
    '시작하다': '시작하다(他动词：主动着手开展) vs 시작되다(自动词：活动自发展开)',
    '바꾸다': '바꾸다(更换物件/兑换货币) vs 변하다(性质/外貌自身发生转变)',
    '변하다': '변하다(自动词：事物状态自身变异) vs 바꾸다(他动词：主动置换物品)'
}


class VocabManager:
    """管理延世韩国语词库的加载、三级筛选、乱序与掌握度"""

    UNIT_TITLES = {
        1: {
            1: "Unit 1 自我介绍",
            2: "Unit 2 学校生活",
            3: "Unit 3 买东西",
            4: "Unit 4 日常生活",
            5: "Unit 5 位置与场所",
            6: "Unit 6 约定与时间",
            7: "Unit 7 过去与周末",
            8: "Unit 8 天气与季节",
            9: "Unit 9 饮食与餐厅",
            10: "Unit 10 交通与出行",
        },
        2: {
            1: "Unit 1 约会与见面",
            2: "Unit 2 购物与市场",
            3: "Unit 3 饮食与料理",
            4: "Unit 4 日常与爱好",
            5: "Unit 5 电话与通信",
            6: "Unit 6 旅行与休假",
            7: "Unit 7 公共设施与问路",
            8: "Unit 8 心情与状态",
            9: "Unit 9 房屋与居住",
            10: "Unit 10 回忆与未来",
        },
        3: {
            1: "Unit 1 性格与外貌",
            2: "Unit 2 饮食生活与料理",
            3: "Unit 3 居住生活与环境",
            4: "Unit 4 休闲生活与文化",
            5: "Unit 5 职场生活与求职",
            6: "Unit 6 突发事故与问题解决",
            7: "Unit 7 韩国传统与风俗",
            8: "Unit 8 健康与疾病管理",
            9: "Unit 9 大众传媒与社会",
            10: "Unit 10 人生规划与社会变迁",
        },
        4: {
            1: "Unit 1 人际关系与沟通",
            2: "Unit 2 语言习惯与文化",
            3: "Unit 3 科学技术与生活",
            4: "Unit 4 职场与职业生涯",
            5: "Unit 5 艺术鉴赏与文化遗产",
            6: "Unit 6 自然生态与环境保护",
            7: "Unit 7 现代社会结构与变迁",
            8: "Unit 8 历史人物与传统智慧",
            9: "Unit 9 哲学思考与价值观",
            10: "Unit 10 全球化与未来社会",
        },
        5: {
            1: "Unit 1 语言与生活",
            2: "Unit 2 科学与现代文明",
            3: "Unit 3 经济与消费趋势",
            4: "Unit 4 现代社会与问题",
            5: "Unit 5 艺术与文化深度",
            6: "Unit 6 大众传媒与网络生态",
            7: "Unit 7 历史传承与时代精神",
            8: "Unit 8 生态环境与可持续发展",
            9: "Unit 9 法律与公民意识",
            10: "Unit 10 心理省思与哲学追求",
        },
        6: {
            1: "Unit 1 人与自然生态",
            2: "Unit 2 科学与未来探索",
            3: "Unit 3 全球经济与金融",
            4: "Unit 4 文学鉴赏与世界文化",
            5: "Unit 5 历史变迁与国家发展",
            6: "Unit 6 政治制度与国际关系",
            7: "Unit 7 思想流派与哲学伦理",
            8: "Unit 8 现代生活与心理省思",
            9: "Unit 9 语言发展与媒体变迁",
            10: "Unit 10 未来展望与人类共同体",
        }
    }

    def __init__(self, data_path: str = "data/korean_vocab.json"):
        self.data_path = data_path
        self.data: Dict = {}
        self.all_words: List[Dict] = []
        self.filtered_words: List[Dict] = []
        self._ordered_filtered_words: List[Dict] = []
        self.current_index: int = 0
        self._current_book: int = 0    # 0 = 全部
        self._current_unit: int = 0    # 0 = 全部
        self._current_lesson: int = 0  # 0 = 全部
        self._shuffle_mode: bool = False
        self._mastered_ids: Set[str] = set()
        self.load()

    def load(self):
        """加载 JSON 词库"""
        from utils.path_helper import get_resource_path, get_data_path
        path = self.data_path
        if not os.path.isabs(path):
            # 优先从运行目录寻找，若无则从打包资源目录寻找
            local_path = get_data_path(self.data_path)
            res_path = get_resource_path(self.data_path)
            if os.path.exists(local_path):
                path = local_path
            elif os.path.exists(res_path):
                path = res_path
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                path = os.path.join(base, self.data_path)
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._flatten_all_words()
        self.apply_filter()

    def _flatten_all_words(self):
        """将所有词平铺，并附带 book/unit/lesson 信息，兼容各种结构字段"""
        self.all_words = []
        for book in self.data.get("books", []):
            book_id = book.get("book_id", book.get("book", 1))
            book_name = book.get("book_name", book.get("name", f"第{book_id}册"))
            
            # 标准化 lessons 格式
            lessons = book.get("lessons", [])
            # 兼容旧版包含 units 的格式
            if not lessons and "units" in book:
                for unit in book.get("units", []):
                    for l in unit.get("lessons", []):
                        lessons.append(l)

            for lesson in lessons:
                lesson_id = lesson.get("lesson_id", lesson.get("lesson", 1))
                lesson_name = lesson.get("lesson_name", lesson.get("title", f"第{lesson_id}课"))
                
                # 计算属于哪个单元
                unit_id = (lesson_id - 1) // 5 + 1
                if "-" in lesson_name:
                    prefix = lesson_name.split()[0]
                    if "-" in prefix:
                        try:
                            unit_id = int(prefix.split("-")[0])
                        except ValueError:
                            pass
                
                unit_name = self.UNIT_TITLES.get(book_id, {}).get(unit_id, f"Unit {unit_id}")

                for word in lesson.get("words", []):
                    word_copy = dict(word)
                    word_copy["_book"] = book_id
                    word_copy["_book_name"] = book_name
                    word_copy["_unit"] = unit_id
                    word_copy["_unit_name"] = unit_name
                    word_copy["_lesson"] = lesson_id
                    word_copy["_lesson_name"] = lesson_name
                    
                    # 字段标准化兼容
                    if "meaning" in word_copy and "chinese" not in word_copy:
                        word_copy["chinese"] = word_copy["meaning"]
                    elif "chinese" in word_copy and "meaning" not in word_copy:
                        word_copy["meaning"] = word_copy["chinese"]

                    # 易混近义词语境辨析 (Nuance Diff) 自动解析与注入
                    if "nuance_diff" not in word_copy or not word_copy["nuance_diff"]:
                        kr_text = word_copy.get("korean", "").strip()
                        clean_kr = re.sub(r"[\s\(\)（）\-_~·/]", "", kr_text)
                        if kr_text in GLOBAL_NUANCE_DIFFS:
                            word_copy["nuance_diff"] = GLOBAL_NUANCE_DIFFS[kr_text]
                        elif clean_kr in GLOBAL_NUANCE_DIFFS:
                            word_copy["nuance_diff"] = GLOBAL_NUANCE_DIFFS[clean_kr]
                        
                    # 例句标准化兼容
                    if "example_kr" in word_copy and "examples" not in word_copy:
                        word_copy["examples"] = [
                            {
                                "korean": word_copy.get("example_kr", ""),
                                "chinese": word_copy.get("example_cn", "")
                            }
                        ]
                    elif "examples" in word_copy and word_copy["examples"] and "example_kr" not in word_copy:
                        ex = word_copy["examples"][0]
                        word_copy["example_kr"] = ex.get("korean", "")
                    # 歌词 / 影视台词微语境标准化兼容
                    q = word_copy.get("quote_lyric") or word_copy.get("quote")
                    if q and isinstance(q, dict):
                        word_copy["quote_kr"] = q.get("kr") or q.get("korean") or q.get("lyric_kr", "")
                        word_copy["quote_cn"] = q.get("cn") or q.get("chinese") or q.get("lyric_cn", "")
                        word_copy["quote_source"] = q.get("source") or q.get("title") or ""
                        word_copy["quote_type"] = q.get("type", "song")
                    elif "quote_kr" in word_copy:
                        word_copy["quote_lyric"] = {
                            "kr": word_copy.get("quote_kr", ""),
                            "cn": word_copy.get("quote_cn", ""),
                            "source": word_copy.get("quote_source", ""),
                            "type": word_copy.get("quote_type", "song")
                        }

                    # 地道搭配语块 (Collocations) 标准化
                    collocs = word_copy.get("collocations") or word_copy.get("collocation")
                    if isinstance(collocs, list):
                        norm_collocs = []
                        for item in collocs:
                            if isinstance(item, dict):
                                norm_collocs.append({
                                    "kr": item.get("kr", item.get("korean", "")),
                                    "cn": item.get("cn", item.get("chinese", ""))
                                })
                            elif isinstance(item, str) and item.strip():
                                norm_collocs.append({"kr": item.strip(), "cn": ""})
                        word_copy["collocations"] = norm_collocs
                    elif isinstance(collocs, str) and collocs.strip():
                        word_copy["collocations"] = [{"kr": collocs.strip(), "cn": ""}]
                    else:
                        word_copy["collocations"] = []

                    # 反义词 (Antonyms) 标准化
                    ants = word_copy.get("antonyms") or word_copy.get("antonym")
                    if isinstance(ants, list):
                        norm_ants = []
                        for item in ants:
                            if isinstance(item, dict):
                                norm_ants.append({
                                    "kr": item.get("kr", item.get("korean", "")),
                                    "cn": item.get("cn", item.get("chinese", ""))
                                })
                            elif isinstance(item, str) and item.strip():
                                norm_ants.append({"kr": item.strip(), "cn": ""})
                        word_copy["antonyms"] = norm_ants
                    elif isinstance(ants, str) and ants.strip():
                        word_copy["antonyms"] = [{"kr": ants.strip(), "cn": ""}]
                    else:
                        word_copy["antonyms"] = []

                    # 自动注入韩语音变规则智能解析结果
                    custom_p = word_copy.get("pron_kr", word_copy.get("actual_pron", ""))
                    word_copy["_mutation"] = analyze_pronunciation(word_copy.get("korean", ""), custom_p)

                    self.all_words.append(word_copy)

        # 统一平铺加载自定义词库与 i-dle 专属全曲库
        for w in self.load_custom_vocab():
            self.all_words.append(w)

        for w in self.load_idle_lyrics():
            self.all_words.append(w)

    def load_custom_vocab(self) -> List[Dict]:
        """动态加载自定义/剪贴板生词本 (Book ID: -2)"""
        custom_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "custom_vocab.json"
        )
        if not os.path.exists(custom_path):
            return []
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            words = []
            for idx, w in enumerate(data.get("words", []), 1):
                w_copy = dict(w)
                w_copy["_book"] = -2
                w_copy["_book_name"] = "📥 剪贴板划词 / 自定义生词"
                w_copy["_unit"] = 1
                w_copy["_unit_name"] = "划词收录"
                w_copy["_lesson"] = 1
                w_copy["_lesson_name"] = f"词条 #{idx}"
                w_copy["_mutation"] = analyze_pronunciation(w_copy.get("korean", ""))
                words.append(w_copy)
            return words
        except Exception:
            return []

    def load_idle_lyrics(self) -> List[Dict]:
        """动态加载 i-dle 专属全曲库 (Book ID: -3)"""
        idle_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "idle_lyrics.json"
        )
        if not os.path.exists(idle_path):
            return []
        try:
            with open(idle_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_items = data if isinstance(data, list) else data.get("sentences", [])
            words = []
            album_to_unit = {}
            for item in raw_items:
                w_copy = dict(item)
                album = item.get("album", "全专收录")
                if album not in album_to_unit:
                    album_to_unit[album] = len(album_to_unit) + 1

                u_id = album_to_unit[album]
                w_copy["_book"] = -3
                w_copy["_book_name"] = "🎵 i-dle 专属全曲库"
                w_copy["_unit"] = u_id
                w_copy["_unit_name"] = f"《{album}》"
                w_copy["_lesson"] = 1
                w_copy["_lesson_name"] = f"{item.get('song_title', '歌曲')} · {item.get('artist', 'i-dle')}"
                w_copy["_mutation"] = analyze_pronunciation(w_copy.get("korean", ""))
                w_copy["is_idle_lyric"] = True
                words.append(w_copy)
            return words
        except Exception:
            return []

    def get_books(self) -> List[Tuple[int, str]]:
        """返回 [(book_id, book_name), ...]，包含全部册数、生词本、自定义与歌词库选项"""
        result = [
            (0, "全部册数"),
            (-1, "我的生词本 (待复习)"),
            (-2, "剪贴板划词 / 自定义生词"),
            (-3, "i-dle 专属全曲库"),
        ]
        for book in self.data.get("books", []):
            b_id = book.get("book_id", book.get("book", 1))
            b_name = book.get("book_name", book.get("name", f"第{b_id}册"))
            result.append((b_id, b_name))
        return result

    def get_units(self, book_id: int) -> List[Tuple[int, str]]:
        """返回指定册包含的单元列表 [(unit_id, unit_name), ...]"""
        if book_id == -1:
            return [(0, "全部生词")]
        if book_id == -2:
            return [(0, "全部收词")]
        if book_id == 0:
            return [(0, "全部单元")]

        unit_title = "全部专辑" if book_id == -3 else "全部单元"
        result = [(0, unit_title)]
        seen_units = {}
        for w in self.all_words:
            if w["_book"] == book_id:
                u_id = w.get("_unit", 0)
                u_name = w.get("_unit_name", f"Unit {u_id}")
                if u_id not in seen_units:
                    seen_units[u_id] = u_name

        for u_id in sorted(seen_units.keys()):
            if u_id > 0:
                result.append((u_id, seen_units[u_id]))
        return result

    def get_lessons(self, book_id: int, unit_id: int = 0) -> List[Tuple[int, str]]:
        """返回指定册（及指定单元）的课列表 [(lesson_id, lesson_name), ...]"""
        if book_id == -1:
            return [(0, "全部生词")]
        if book_id == -2:
            return [(0, "全部条目")]
        if book_id == 0:
            return [(0, "全部课程")]

        result = [(0, "全部课程")]
        seen_lessons = {}
        for w in self.all_words:
            if w["_book"] == book_id:
                if unit_id == 0 or w.get("_unit") == unit_id:
                    l_id = w["_lesson"]
                    l_name = w["_lesson_name"]
                    if l_id not in seen_lessons:
                        seen_lessons[l_id] = l_name

        for l_id in sorted(seen_lessons.keys()):
            result.append((l_id, seen_lessons[l_id]))
        return result

    def apply_filter(
        self,
        book: int = 0,
        unit: int = 0,
        lesson: int = 0,
        word_ids: Optional[List[str]] = None
    ):
        """应用三级筛选条件（册 -> 单元 -> 课程），更新 filtered_words"""
        self._current_book = book
        self._current_unit = unit
        self._current_lesson = lesson

        if word_ids is not None:
            # 生词本模式：只显示指定 ID 的词
            id_set = set(word_ids)
            self.filtered_words = [w for w in self.all_words if w["id"] in id_set]
        elif book == -2:
            # 剪贴板划词 / 自定义生词本
            self.filtered_words = self.load_custom_vocab()
        elif book == -3:
            # i-dle 专属歌词金句
            self.filtered_words = self.load_idle_lyrics()
        else:
            words = self.all_words
            if book != 0:
                words = [w for w in words if w["_book"] == book]
            if unit != 0:
                words = [w for w in words if w.get("_unit") == unit]
            if lesson != 0:
                words = [w for w in words if w["_lesson"] == lesson]
            self.filtered_words = words

        self._ordered_filtered_words = list(self.filtered_words)
        if self._shuffle_mode:
            random.shuffle(self.filtered_words)

        self.current_index = 0

    def toggle_shuffle(self) -> bool:
        """切换随机乱序模式，返回切换后的状态"""
        self._shuffle_mode = not self._shuffle_mode
        if self._shuffle_mode:
            self._ordered_filtered_words = list(self.filtered_words)
            random.shuffle(self.filtered_words)
        else:
            if self._ordered_filtered_words:
                self.filtered_words = list(self._ordered_filtered_words)
        self.current_index = 0
        return self._shuffle_mode

    def set_shuffle(self, enabled: bool):
        """设定随机乱序模式"""
        if self._shuffle_mode == enabled:
            return
        self._shuffle_mode = enabled
        if self._shuffle_mode:
            self._ordered_filtered_words = list(self.filtered_words)
            random.shuffle(self.filtered_words)
        else:
            if self._ordered_filtered_words:
                self.filtered_words = list(self._ordered_filtered_words)
        self.current_index = 0

    @property
    def is_shuffle(self) -> bool:
        return self._shuffle_mode

    # ─────────────────────────────────────────────────────────
    # 掌握度管理
    # ─────────────────────────────────────────────────────────

    def mark_mastered(self, word_id: str):
        """标记单词为已掌握"""
        if word_id:
            self._mastered_ids.add(word_id)

    def unmark_mastered(self, word_id: str):
        """取消单词的已掌握标记"""
        self._mastered_ids.discard(word_id)

    def is_mastered(self, word_id: str) -> bool:
        """检查单词是否已掌握"""
        return word_id in self._mastered_ids

    def mastered_count(self) -> int:
        """当前筛选列表中已掌握的词数"""
        return sum(1 for w in self.filtered_words if w["id"] in self._mastered_ids)

    # ─────────────────────────────────────────────────────────
    # 词汇导航
    # ─────────────────────────────────────────────────────────

    def current_word(self) -> Optional[Dict]:
        if not self.filtered_words:
            return None
        return self.filtered_words[self.current_index]

    def next_word(self) -> Optional[Dict]:
        if not self.filtered_words:
            return None
        self.current_index = (self.current_index + 1) % len(self.filtered_words)
        return self.current_word()

    def prev_word(self) -> Optional[Dict]:
        if not self.filtered_words:
            return None
        self.current_index = (self.current_index - 1) % len(self.filtered_words)
        return self.current_word()

    def jump_to(self, index: int):
        if self.filtered_words:
            self.current_index = max(0, min(index, len(self.filtered_words) - 1))

    def jump_to_word(self, word_id: Any = None, korean: str = None) -> bool:
        """根据 word_id 或 korean 精准定位卡片"""
        if not self.filtered_words:
            return False
        if word_id:
            for idx, w in enumerate(self.filtered_words):
                if str(w.get("id")) == str(word_id):
                    self.current_index = idx
                    return True
        if korean:
            for idx, w in enumerate(self.filtered_words):
                if w.get("korean") == korean:
                    self.current_index = idx
                    return True
        return False

    def total(self) -> int:
        return len(self.filtered_words)

    def progress_text(self) -> str:
        if not self.filtered_words:
            return "0 / 0"
        curr_word = self.current_word()
        mastered_mark = " ✓" if (curr_word and curr_word["id"] in self._mastered_ids) else ""
        return f"{self.current_index + 1} / {self.total()}{mastered_mark}"

    def get_nearby_words(self, window: int = 2) -> List[Dict]:
        """获取当前词附近的词汇列表（如 N-1, N+1, N+2），用于后台静默异步预抓取音频"""
        if not self.filtered_words:
            return []
        total = len(self.filtered_words)
        result = []
        # 优先预加载后续单词 N+1, N+2，以及前一个 N-1
        offsets = [1, 2, -1]
        for off in offsets:
            idx = (self.current_index + off) % total
            w = self.filtered_words[idx]
            if w not in result:
                result.append(w)
        return result

    # ─────────────────────────────────────────────────────────
    # 🎯 加权智能复习模式 (Weighted Review Engine)
    # ─────────────────────────────────────────────────────────

    def generate_weighted_review_batch(self, batch_size: int = 20, state_manager=None) -> List[Dict]:
        """
        根据用户的历史学习轨迹执行科学加权抽样：
        - 不熟生词 (unfamiliar): 权重 5.0 (高频突击)
        - 常规已学 (seen): 权重 2.0 (适度复习)
        - 已掌握词 (mastered): 权重 0.5 (低频巩固)
        - 若已学词库不足，自动从其余单词中补充 (权重 1.0)
        返回打乱且不重复的复习单词列表
        """
        if not self.all_words:
            return []

        records = state_manager.get_all_study_records() if state_manager else {}

        # 1. 划分各状态词池
        unfamiliar_pool = []
        seen_pool = []
        mastered_pool = []
        new_pool = []

        for w in self.all_words:
            wid = str(w.get("id"))
            status = records.get(wid, {}).get("status", "new")
            if status == "unfamiliar":
                unfamiliar_pool.append(w)
            elif status == "mastered":
                mastered_pool.append(w)
            elif status == "seen":
                seen_pool.append(w)
            else:
                new_pool.append(w)

        studied_total = len(unfamiliar_pool) + len(seen_pool) + len(mastered_pool)

        # 2. 构建抽样候选池与权重
        candidates = []
        weights = []

        for w in unfamiliar_pool:
            candidates.append(w)
            weights.append(5.0)

        for w in seen_pool:
            candidates.append(w)
            weights.append(2.0)

        for w in mastered_pool:
            candidates.append(w)
            weights.append(0.5)

        # 如果已学过的词少于设定的单次复习量，从未学池补充
        if studied_total < batch_size and new_pool:
            needed = batch_size - studied_total
            supplement = random.sample(new_pool, min(needed, len(new_pool)))
            for w in supplement:
                candidates.append(w)
                weights.append(1.0)

        if not candidates:
            # 若无任何记录，直接从全词库随机抽样
            sample_count = min(batch_size, len(self.all_words))
            return random.sample(self.all_words, sample_count)

        # 3. 依权重进行无放回抽样
        chosen_words = []
        cand_pool = list(candidates)
        weight_pool = list(weights)
        target_count = min(batch_size, len(cand_pool))

        for _ in range(target_count):
            if not cand_pool:
                break
            # 依权重随机选出一个
            selected = random.choices(cand_pool, weights=weight_pool, k=1)[0]
            idx = cand_pool.index(selected)
            chosen_words.append(selected)
            cand_pool.pop(idx)
            weight_pool.pop(idx)

        # 4. 洗牌打乱顺序，保证题目随机分布
        random.shuffle(chosen_words)
        return chosen_words

    def apply_review_batch(self, words: List[Dict]):
        """将生成的复习序列直接应用到当前播放列表"""
        self.filtered_words = list(words)
        self._ordered_filtered_words = list(words)
        self.current_index = 0

    def find_word_by_korean(self, korean_str: str) -> Optional[dict]:
        """根据韩文单词原型查找词条对象（支持全量词库、自定义词库与歌词库）"""
        if not korean_str:
            return None
        target = korean_str.strip()
        # 1. 优先在当前 filtered_words 中查找
        for w in self.filtered_words:
            if w.get("korean", "").strip() == target:
                return w
        # 2. 在全量词库中查找
        for w in self.all_words:
            if w.get("korean", "").strip() == target:
                return w
        # 3. 在自定义词库中查找
        for w in self.load_custom_vocab():
            if w.get("korean", "").strip() == target:
                return w
        # 4. 在歌词库中查找
        for w in self.load_idle_lyrics():
            if w.get("korean", "").strip() == target:
                return w
        return None

    def jump_to_korean(self, korean_str: str) -> bool:
        """根据韩文单词原型跳转当前索引（若在当前列表中）"""
        if not korean_str:
            return False
        target = korean_str.strip()
        for idx, w in enumerate(self.filtered_words):
            if w.get("korean", "").strip() == target:
                self.current_index = idx
                return True
        return False
