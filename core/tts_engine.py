# core/tts_engine.py
# -*- coding: utf-8 -*-
"""多引擎韩语音频合成与零延迟秒播系统
1. 本地持久化缓存：data/audio_cache/<md5>.mp3
2. 零延迟秒播策略：命中本地缓存时毫秒级瞬时秒播（基于 pygame 内存流零文件锁）
3. 后台异步预抓取（Prefetch Worker）：切词时静默并发预下载周边单词音频，100% 消除网络等待延迟
4. 高保真首选引擎：edge-tts (自然韩语女声 ko-KR-SunHiNeural / 男声 ko-KR-InJoonNeural)
5. 离线兜底引擎：pyttsx3 / Windows SAPI5 (无网状态随时发音)
6. 架构解耦：QThread 异步工作流，主界面 0 阻塞 0 卡顿
"""

import os
import io
import re
import queue
import hashlib
import asyncio
from typing import Optional, List

from PyQt6.QtCore import QObject, QThread, pyqtSignal

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

import threading

from config.settings import (
    TTS_VOICE_PRIMARY, TTS_RATE, TTS_VOLUME
)
from utils.path_helper import get_data_path

_mixer_lock = threading.Lock()


def ensure_mixer_init():
    """安全初始化 pygame.mixer 音频驱动"""
    if not PYGAME_AVAILABLE:
        return False
    with _mixer_lock:
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except Exception:
                try:
                    pygame.mixer.init()
                except Exception as e:
                    print(f"[TTSEngine] pygame.mixer 初始化失败: {e}")
                    return False
    return True


def clean_korean_text(text: str) -> str:
    """清理韩语文本中的汉字括号、中文注释及特殊符号，提取纯净发音文本"""
    if not text:
        return ""
    cleaned = re.sub(r"\(.*?\)", "", text)
    cleaned = re.sub(r"（.*?）", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned if cleaned else text


def get_audio_cache_path(text: str, voice: str = TTS_VOICE_PRIMARY, cache_dir: Optional[str] = None) -> str:
    """生成或获取本地音频缓存文件绝对路径"""
    if not cache_dir:
        cache_dir = get_data_path(os.path.join("data", "audio_cache"))
    os.makedirs(cache_dir, exist_ok=True)
    clean_txt = clean_korean_text(text)
    cache_key = hashlib.md5(f"{voice}:{clean_txt}".encode("utf-8")).hexdigest()
    # 清理非字母数字文件名字符，便于在本地查看识别
    safe_prefix = re.sub(r'[\\/*?:"<>|]', "", clean_txt)[:12]
    filename = f"{safe_prefix}_{cache_key[:8]}.mp3" if safe_prefix else f"{cache_key}.mp3"
    return os.path.join(cache_dir, filename)


class PrefetchWorker(QThread):
    """后台静默音频预抓取线程：在用户浏览卡片时提前下载周边词汇音频至本地缓存"""

    def __init__(self, cache_dir: str, parent=None):
        super().__init__(parent)
        self._cache_dir = cache_dir
        self._queue: queue.Queue = queue.Queue()
        self._running = True
        self._pending_set = set()

    def enqueue(self, texts: List[str], voice: str = TTS_VOICE_PRIMARY):
        """将待预抓取的词条加入队列"""
        if not EDGE_TTS_AVAILABLE:
            return
        for t in texts:
            clean_t = clean_korean_text(t)
            if not clean_t:
                continue
            key = f"{voice}:{clean_t}"
            if key not in self._pending_set:
                target_file = get_audio_cache_path(clean_t, voice, self._cache_dir)
                if not (os.path.exists(target_file) and os.path.getsize(target_file) > 0):
                    self._pending_set.add(key)
                    self._queue.put((clean_t, voice, target_file, key))

    def run(self):
        while self._running:
            try:
                item = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            clean_t, voice, target_file, key = item
            if not self._running:
                break

            # 再次确认未被下载
            if not (os.path.exists(target_file) and os.path.getsize(target_file) > 0):
                try:
                    asyncio.run(self._download_edge_tts(clean_t, voice, target_file))
                except Exception:
                    pass

            self._pending_set.discard(key)
            self._queue.task_done()

    async def _download_edge_tts(self, text: str, voice: str, target_file: str):
        comm = edge_tts.Communicate(text, voice, rate=TTS_RATE, volume=TTS_VOLUME)
        # 先保存为临时文件再重命名，避免生成破损文件
        tmp_file = target_file + ".tmp"
        await comm.save(tmp_file)
        if os.path.exists(tmp_file) and os.path.getsize(tmp_file) > 0:
            if os.path.exists(target_file):
                os.remove(target_file)
            os.rename(tmp_file, target_file)

    def stop(self):
        self._running = False
        try:
            self._queue.put_nowait(("", "", "", ""))
        except Exception:
            pass
        self.wait(50)
        if self.isRunning():
            self.terminate()


class AudioWorker(QThread):
    """单次音频合成与零延迟播放工作线程"""

    playback_started = pyqtSignal(str)     # 开始播放 (text)
    playback_finished = pyqtSignal(str)    # 播放结束 (text)
    playback_error = pyqtSignal(str, str)  # (text, error_msg)

    def __init__(
        self,
        text: str,
        voice: str = TTS_VOICE_PRIMARY,
        cache_dir: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.text = text
        self.clean_text = clean_korean_text(text)
        self.voice = voice
        self.cache_dir = cache_dir or get_data_path(os.path.join("data", "audio_cache"))
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        self.wait(30)
        if self.isRunning():
            self.terminate()

    def run(self):
        if not self.clean_text or self._cancelled:
            self.playback_finished.emit(self.text)
            return

        cache_path = get_audio_cache_path(self.clean_text, self.voice, self.cache_dir)
        self.playback_started.emit(self.text)

        # ── 1. 命中本地持久化缓存 -> 毫秒级零延迟秒播 ──
        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
            if not self._cancelled:
                self._play_mp3(cache_path)
            self.playback_finished.emit(self.text)
            return

        # ── 2. 在线合成 (edge-tts) 并写入本地缓存 ──
        if EDGE_TTS_AVAILABLE and not self._cancelled:
            try:
                asyncio.run(self._synthesize_edge_tts(self.clean_text, self.voice, cache_path))
                if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0 and not self._cancelled:
                    self._play_mp3(cache_path)
                    self.playback_finished.emit(self.text)
                    return
            except Exception as e:
                print(f"[AudioWorker] edge-tts 合成异常: {e}")

        # ── 3. 离线本地兜底引擎 (pyttsx3 / Windows SAPI5) ──
        if PYTTSX3_AVAILABLE and not self._cancelled:
            try:
                self._speak_pyttsx3(self.clean_text)
                self.playback_finished.emit(self.text)
                return
            except Exception as e:
                print(f"[AudioWorker] pyttsx3 本地离线发音失败: {e}")

        if not self._cancelled:
            self.playback_error.emit(self.text, "发音失败，请检查系统音频驱动")
        self.playback_finished.emit(self.text)

    async def _synthesize_edge_tts(self, text: str, voice: str, target_file: str):
        comm = edge_tts.Communicate(text, voice, rate=TTS_RATE, volume=TTS_VOLUME)
        tmp_file = target_file + ".tmp"
        await comm.save(tmp_file)
        if os.path.exists(tmp_file) and os.path.getsize(tmp_file) > 0:
            if os.path.exists(target_file):
                os.remove(target_file)
            os.rename(tmp_file, target_file)

    def _play_mp3(self, file_path: str) -> bool:
        """通过 pygame 内存流播放音频，彻底解耦 Windows 文件锁"""
        if not ensure_mixer_init() or self._cancelled:
            return False
        try:
            import time
            with open(file_path, "rb") as f:
                audio_data = f.read()
            if self._cancelled:
                return True
            with _mixer_lock:
                sound = pygame.mixer.Sound(io.BytesIO(audio_data))
                sound.set_volume(1.0)
                channel = sound.play()
            if channel:
                while channel.get_busy() and not self._cancelled:
                    time.sleep(0.02)
                if self._cancelled:
                    with _mixer_lock:
                        channel.stop()
            return True
        except Exception as e:
            print(f"[AudioWorker] pygame.mixer 播放错误: {e}")
            return False

    def _speak_pyttsx3(self, text: str):
        """调用 Windows 本地 TTS 引擎发音"""
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        for v in voices:
            if "ko" in v.id.lower() or "heami" in v.name.lower() or "korean" in v.name.lower():
                engine.setProperty("voice", v.id)
                break
        engine.setProperty("rate", 140)
        engine.say(text)
        engine.runAndWait()


class TTSEngine(QObject):
    """统一音频管理器（管理并发播放、静默预抓取与状态回调）"""

    started = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_worker: Optional[AudioWorker] = None
        self._cache_dir = get_data_path(os.path.join("data", "audio_cache"))
        os.makedirs(self._cache_dir, exist_ok=True)
        ensure_mixer_init()

        # 启动后台静默预抓取工作线程
        self._prefetch_worker = PrefetchWorker(self._cache_dir, parent=self)
        self._prefetch_worker.start()

    def speak(self, text: str, voice: str = TTS_VOICE_PRIMARY):
        """触发即时/零延迟秒播发音"""
        if not text:
            return

        self.stop()
        self._current_worker = AudioWorker(
            text=text,
            voice=voice,
            cache_dir=self._cache_dir
        )
        self._current_worker.playback_started.connect(self.started.emit)
        self._current_worker.playback_finished.connect(self._on_worker_finished)
        self._current_worker.playback_error.connect(self.error.emit)
        self._current_worker.start()

    def prefetch(self, texts: List[str], voice: str = TTS_VOICE_PRIMARY):
        """后台静默预加载多个单词的音频到本地缓存"""
        if self._prefetch_worker and self._prefetch_worker.isRunning():
            self._prefetch_worker.enqueue(texts, voice)

    def _on_worker_finished(self, text: str):
        self.finished.emit(text)

    def stop(self):
        """立即中断正在播放的音频"""
        if PYGAME_AVAILABLE:
            try:
                with _mixer_lock:
                    if pygame.mixer.get_init():
                        pygame.mixer.stop()
            except Exception:
                pass
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.cancel()
            self._current_worker.wait(100)
            self._current_worker = None

    def is_playing(self) -> bool:
        if PYGAME_AVAILABLE and pygame.mixer.get_init():
            return pygame.mixer.get_busy()
        return bool(self._current_worker and self._current_worker.isRunning())

    def cleanup(self):
        self.stop()
        if self._prefetch_worker:
            self._prefetch_worker.stop()
        if PYGAME_AVAILABLE and pygame.mixer.get_init():
            try:
                pygame.mixer.quit()
            except Exception:
                pass
