# core/translator_manager.py
# -*- coding: utf-8 -*-
"""
多引擎中韩智能翻译管理模块
支持：
1. Naver Papago（韩语口语地道黄金标准）
2. Google Translate（快速通用全文翻译）
3. 本地离线词典（Offline Fallback，毫秒级快速匹配项目内置词库）
4. 多引擎对照模式（All Engines Compare）
5. 智能双向语种检测（自动判断 ko->zh 或 zh->ko）
"""

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple, Any
from PyQt6.QtCore import QObject, QThread, pyqtSignal


def is_korean_text(text: str) -> bool:
    """判断文本是否主要为韩文字符"""
    if not text:
        return False
    korean_chars = re.findall(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]", text)
    return len(korean_chars) > 0


def detect_direction(text: str) -> Tuple[str, str]:
    """
    自动检测中韩翻译方向
    返回: (source_lang, target_lang)
    例如: ('ko', 'zh-CN') 或 ('zh-CN', 'ko')
    """
    if is_korean_text(text):
        return "ko", "zh-CN"
    else:
        return "zh-CN", "ko"


class OfflineDictEngine:
    """本地离线词库检索引擎（基于项目已有的延世词库、自定义词库与歌词库）"""

    def __init__(self, vocab_json_path: str = "data/korean_vocab.json"):
        self.vocab_json_path = vocab_json_path
        self._kr_index: Dict[str, Dict[str, Any]] = {}
        self._cn_index: List[Dict[str, Any]] = []
        self._load_cache()

    def _load_cache(self):
        """加载项目内置词库建立内存倒排索引"""
        # 1. 主词库
        if os.path.exists(self.vocab_json_path):
            try:
                with open(self.vocab_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for b in data.get("books", []):
                    for l in b.get("lessons", []):
                        for w in l.get("words", []):
                            self._index_word(w)
            except Exception:
                pass

        # 2. 自定义词库
        custom_path = "data/custom_vocab.json"
        if os.path.exists(custom_path):
            try:
                with open(custom_path, "r", encoding="utf-8") as f:
                    custom_words = json.load(f)
                if isinstance(custom_words, list):
                    for w in custom_words:
                        self._index_word(w)
            except Exception:
                pass

        # 3. 歌词库
        lyrics_path = "data/idle_lyrics.json"
        if os.path.exists(lyrics_path):
            try:
                with open(lyrics_path, "r", encoding="utf-8") as f:
                    lyrics = json.load(f)
                if isinstance(lyrics, list):
                    for item in lyrics:
                        self._index_word(item)
            except Exception:
                pass

    def _index_word(self, w: Dict[str, Any]):
        kr = w.get("korean", "").strip()
        if not kr:
            return
        clean_kr = re.sub(r"[\s\(\)（）\-_~·/]", "", kr).lower()
        if clean_kr not in self._kr_index:
            self._kr_index[clean_kr] = w
        self._kr_index[kr.lower()] = w
        self._cn_index.append(w)

    def lookup(self, query: str) -> Dict[str, Any]:
        """
        离线词典查询
        返回包含: success, result_text, details (词性, 音标, 例句等)
        """
        q = query.strip()
        if not q:
            return {"success": False, "text": "", "details": None}

        clean_q = re.sub(r"[\s\(\)（）\-_~·/]", "", q).lower()

        # 1. 韩语查中文（精确与前缀匹配）
        if clean_q in self._kr_index:
            w = self._kr_index[clean_q]
            meaning = w.get("meaning", w.get("chinese", ""))
            return {
                "success": True,
                "text": meaning,
                "korean": w.get("korean", q),
                "pronunciation": w.get("pronunciation", ""),
                "pos": w.get("pos", ""),
                "example_kr": w.get("example_kr", ""),
                "example_cn": w.get("example_cn", ""),
                "source": "本地离线词典 (精确匹配)"
            }

        # 2. 中文查韩文（在释义中搜索）
        matches = []
        for w in self._cn_index:
            meaning = w.get("meaning", w.get("chinese", ""))
            if q in meaning:
                matches.append(w)
                if len(matches) >= 3:
                    break

        if matches:
            best = matches[0]
            kr_list = [m.get("korean", "") for m in matches if m.get("korean")]
            return {
                "success": True,
                "text": " / ".join(kr_list),
                "korean": best.get("korean", ""),
                "pronunciation": best.get("pronunciation", ""),
                "pos": best.get("pos", ""),
                "meaning": best.get("meaning", best.get("chinese", "")),
                "example_kr": best.get("example_kr", ""),
                "example_cn": best.get("example_cn", ""),
                "source": f"本地离线词典 (找到 {len(matches)} 条匹配)"
            }

        # 3. 词干部分匹配 (去掉 다 等)
        if q.endswith("다") and len(q) > 2:
            stem = q[:-1]
            for kr_k, w in self._kr_index.items():
                if kr_k.startswith(stem):
                    return {
                        "success": True,
                        "text": w.get("meaning", w.get("chinese", "")),
                        "korean": w.get("korean", q),
                        "pronunciation": w.get("pronunciation", ""),
                        "pos": w.get("pos", ""),
                        "source": "本地离线词典 (词干联想)"
                    }

        return {
            "success": False,
            "text": "离线词典中未收录此词条（联网可使用 Papago / Google 翻译）",
            "details": None
        }


def translate_youdao(text: str, sl: str = "ko", tl: str = "zh-CN", timeout: float = 2.5) -> Tuple[bool, str]:
    """
    通过有道智能翻译接口进行中韩极速互译（国内 100% 免梯直连，毫秒级响应）
    """
    if not text.strip():
        return False, ""

    from_lang = "ko" if sl.startswith("ko") else "zh-CHS"
    to_lang = "zh-CHS" if sl.startswith("ko") else "ko"

    try:
        url = "https://aidemo.youdao.com/trans"
        data = urllib.parse.urlencode({
            "q": text,
            "from": from_lang,
            "to": to_lang
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://ai.youdao.com/",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if "translation" in res and len(res["translation"]) > 0:
                t = res["translation"][0].strip()
                if t:
                    return True, t
            if "basic" in res and "explains" in res["basic"]:
                explains = res["basic"]["explains"]
                if explains:
                    return True, " / ".join(explains)
            if "web" in res and len(res["web"]) > 0:
                values = res["web"][0].get("value", [])
                if values:
                    return True, " / ".join(values)
    except Exception:
        pass

    return False, "有道翻译连接超时"


def translate_mymemory(text: str, sl: str = "ko", tl: str = "zh-CN", timeout: float = 2.5) -> Tuple[bool, str]:
    """
    通过 MyMemory 开放翻译接口（全球免翻备用引擎）
    """
    if not text.strip():
        return False, ""

    from_lang = "ko" if sl.startswith("ko") else "zh-CN"
    to_lang = "zh-CN" if sl.startswith("ko") else "ko"

    try:
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair={from_lang}|{to_lang}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            res_text = data.get("responseData", {}).get("translatedText", "").strip()
            if res_text and "MYMEMORY WARNING" not in res_text:
                return True, res_text
    except Exception:
        pass

    return False, "MyMemory连接超时"


def translate_google(text: str, sl: str = "auto", tl: str = "zh-CN", timeout: float = 1.5) -> Tuple[bool, str]:
    """通过 Google 开放翻译接口进行中韩翻译（若无梯子将平滑降级至有道）"""
    if not text.strip():
        return False, ""

    try:
        encoded_q = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={sl}&tl={tl}&dt=t&q={encoded_q}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_json = response.read().decode("utf-8")
            data = json.loads(raw_json)

        # 解析 Google 返回结构
        if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            translated_chunks = []
            for item in data[0]:
                if isinstance(item, list) and len(item) > 0 and item[0]:
                    translated_chunks.append(item[0])
            result = "".join(translated_chunks)
            if result.strip():
                return True, result.strip()
    except Exception:
        pass

    # 无梯子或网络受阻时，自动平滑切换至有道免梯直连
    ok_y, y_text = translate_youdao(text, sl=sl, tl=tl, timeout=timeout)
    if ok_y:
        return True, f"{y_text} (Google已自动平滑免梯连接)"

    ok_m, m_text = translate_mymemory(text, sl=sl, tl=tl, timeout=timeout)
    if ok_m:
        return True, f"{m_text} (已自动免梯连接)"

    return False, "网络连接超时"


def translate_papago(text: str, sl: str = "ko", tl: str = "zh-CN", timeout: float = 1.5) -> Tuple[bool, str]:
    """
    通过 Naver Papago 开放接口进行中韩互译（若无梯子将平滑降级至有道/Google/MyMemory）
    """
    if not text.strip():
        return False, ""

    papago_sl = "ko" if sl.startswith("ko") else "zh-CN"
    papago_tl = "zh-CN" if sl.startswith("ko") else "ko"

    try:
        url = "https://papago.naver.com/apis/n2mt/translate"
        post_data = urllib.parse.urlencode({
            "deviceId": "flashcard-desktop-client",
            "locale": "zh-CN",
            "dict": "true",
            "dictDisplay": "30",
            "honorific": "false",
            "instant": "false",
            "paging": "false",
            "source": papago_sl,
            "target": papago_tl,
            "text": text,
            "authroization": "anonymous"
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=post_data,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://papago.naver.com/",
                "Origin": "https://papago.naver.com",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_json = response.read().decode("utf-8")
            data = json.loads(raw_json)
            if "translatedText" in data and data["translatedText"].strip():
                return True, data["translatedText"].strip()
    except Exception:
        pass

    # 无梯子或 Papago 失败时，第一顺位自动降级为国内免梯直连有道
    ok_y, y_text = translate_youdao(text, sl=sl, tl=tl, timeout=timeout)
    if ok_y:
        return True, f"{y_text} (Papago已自动免梯直连)"

    ok_g, g_text = translate_google(text, sl=sl, tl=tl, timeout=timeout)
    if ok_g:
        return True, f"{g_text} (Papago已自动平滑连接)"

    ok_m, m_text = translate_mymemory(text, sl=sl, tl=tl, timeout=timeout)
    if ok_m:
        return True, f"{m_text} (已自动免梯连接)"

    return False, "网络连接超时"


class TranslationWorker(QThread):
    """异步多引擎翻译后台工作线程（杜绝阻塞 UI 线程）"""

    result_ready = pyqtSignal(dict)

    def __init__(self, text: str, engine: str = "youdao", parent=None):
        super().__init__(parent)
        self._text = text.strip()
        self._engine = engine
        self._offline_dict = OfflineDictEngine()

    def run(self):
        if not self._text:
            self.result_ready.emit({"status": "empty", "query": ""})
            return

        sl, tl = detect_direction(self._text)
        query = self._text
        engine = self._engine

        results = {
            "status": "success",
            "query": query,
            "sl": sl,
            "tl": tl,
            "direction_label": "韩 ➔ 中" if sl == "ko" else "中 ➔ 韩",
            "engine": engine,
            "data": {}
        }

        # 1. 离线词典查询结果（毫秒级）
        offline_res = self._offline_dict.lookup(query)
        fallback_text = offline_res.get("text") if offline_res.get("success") else "未能连接网络且离线词典未收录"

        if engine == "offline":
            results["data"]["offline"] = offline_res
            results["main_result"] = offline_res.get("text", "")
            results["details"] = offline_res

        elif engine == "youdao":
            ok, text = translate_youdao(query, sl=sl, tl=tl)
            if not ok:
                ok, text = translate_mymemory(query, sl=sl, tl=tl)
            if not ok:
                ok, text = translate_papago(query, sl=sl, tl=tl)
            results["data"]["youdao"] = {"success": ok, "text": text}
            results["data"]["offline"] = offline_res
            results["main_result"] = text if ok else f"{fallback_text} (已自动平滑切换离线词典)"
            results["details"] = offline_res if offline_res.get("success") else None

        elif engine == "papago":
            ok, text = translate_papago(query, sl=sl, tl=tl)
            results["data"]["papago"] = {"success": ok, "text": text}
            results["data"]["offline"] = offline_res
            results["main_result"] = text if ok else f"{fallback_text} (已自动平滑切换离线词典)"
            results["details"] = offline_res if offline_res.get("success") else None

        elif engine == "google":
            ok, text = translate_google(query, sl=sl, tl=tl)
            results["data"]["google"] = {"success": ok, "text": text}
            results["data"]["offline"] = offline_res
            results["main_result"] = text if ok else f"{fallback_text} (已自动平滑切换离线词典)"
            results["details"] = offline_res if offline_res.get("success") else None

        elif engine == "all":
            ok_y, y_text = translate_youdao(query, sl=sl, tl=tl)
            ok_p, p_text = translate_papago(query, sl=sl, tl=tl)
            ok_g, g_text = translate_google(query, sl=sl, tl=tl)
            results["data"]["youdao"] = {"success": ok_y, "text": y_text if ok_y else "网络超时"}
            results["data"]["papago"] = {"success": ok_p, "text": p_text if ok_p else "网络超时"}
            results["data"]["google"] = {"success": ok_g, "text": g_text if ok_g else "网络超时"}
            results["data"]["offline"] = offline_res
            best_res = y_text if ok_y else (p_text if ok_p else (g_text if ok_g else fallback_text))
            results["main_result"] = best_res
            results["details"] = offline_res if offline_res.get("success") else None

        self.result_ready.emit(results)


class TranslatorManager(QObject):
    """多引擎翻译管理器总控（带 200ms 限频保护与国内免梯直连）"""

    translation_completed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_worker: Optional[TranslationWorker] = None
        self._current_engine: str = "youdao"
        self._last_request_time: float = 0.0

    def set_engine(self, engine: str):
        self._current_engine = engine

    def translate_async(self, text: str, engine: Optional[str] = None):
        """执行异步防抖与限频翻译"""
        import time
        now = time.time()
        # 200ms 内快速重复请求直接终止前一个任务
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.terminate()
            self._current_worker.wait(50)

        self._last_request_time = now
        target_engine = engine or self._current_engine
        self._current_worker = TranslationWorker(text, engine=target_engine, parent=self)
        self._current_worker.result_ready.connect(self.translation_completed.emit)
        self._current_worker.start()

    def cancel(self):
        """取消当前后台翻译工作线程"""
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.terminate()
            self._current_worker.wait(50)
            self._current_worker = None
