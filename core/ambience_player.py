"""
ambience_player.py
------------------
「未来的韩语卡片」- 本地轻量白噪音伴学与音效播放引擎
1. 纯本地波形合成：首尔小雨 (Seoul Rain)、咖啡馆环境音 (Cafe Ambience)、纯净粉红白噪音 (Pure Pink Noise)、倒计时轻柔提示铃 (Soft Chime)
2. 多声道无冲突混音：使用 pygame.mixer 独立通道循环播放，与主 TTS 朗读发音互不干扰
3. 零外部音频文件依赖：按需自动合成 44.1kHz 16-bit 立体声 WAV 缓存
"""

import os
import wave
import struct
import math
import random
from typing import Optional, Dict

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from utils.path_helper import get_data_path

AMBIENCE_TYPES = {
    "none": {"name": "🔇 静音关闭", "file": None},
    "rain": {"name": "🌧️ 首尔小雨", "file": "seoul_rain.wav"},
    "cafe": {"name": "☕ 咖啡馆环境", "file": "cafe_ambience.wav"},
    "white": {"name": "🌊 纯净白噪音", "file": "pure_white_noise.wav"},
}


def _generate_wav_files(dir_path: str):
    """合成生成本地环境音与提示铃声 WAV 文件"""
    os.makedirs(dir_path, exist_ok=True)
    sample_rate = 44100

    # 1. 🔔 倒计时结束轻柔磬音 (timer_chime.wav) - 1.6 秒
    chime_path = os.path.join(dir_path, "timer_chime.wav")
    if not os.path.exists(chime_path):
        duration = 1.6
        total_samples = int(sample_rate * duration)
        with wave.open(chime_path, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = bytearray()
            for i in range(total_samples):
                t = i / sample_rate
                # 双音节和弦 523.25Hz (C5) + 659.25Hz (E5) + 1046.5Hz (C6)
                env1 = math.exp(-3.5 * t)
                env2 = math.exp(-2.5 * max(0.0, t - 0.15)) if t >= 0.15 else 0.0
                
                s1 = math.sin(2 * math.pi * 523.25 * t) * 0.45 * env1
                s2 = math.sin(2 * math.pi * 659.25 * t) * 0.35 * env1
                s3 = (math.sin(2 * math.pi * 1046.5 * (t - 0.15)) * 0.30 * env2) if t >= 0.15 else 0.0
                
                sample_val = int((s1 + s2 + s3) * 26000)
                sample_val = max(-32768, min(32767, sample_val))
                frames.extend(struct.pack('<hh', sample_val, sample_val))
            wf.writeframes(frames)

    # 2. 🌊 纯净粉红白噪音 (pure_white_noise.wav) - 5 秒平滑循环
    white_path = os.path.join(dir_path, "pure_white_noise.wav")
    if not os.path.exists(white_path):
        duration = 5.0
        total_samples = int(sample_rate * duration)
        with wave.open(white_path, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = bytearray()
            b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
            for i in range(total_samples):
                white = random.uniform(-1.0, 1.0)
                # Paul Kellet 的精炼粉红噪音滤波算法
                b0 = 0.99886 * b0 + white * 0.0555179
                b1 = 0.99332 * b1 + white * 0.0750759
                b2 = 0.96900 * b2 + white * 0.1538520
                b3 = 0.86650 * b3 + white * 0.3104856
                b4 = 0.55000 * b4 + white * 0.5329522
                b5 = -0.7616 * b5 - white * 0.0168980
                pink = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362
                b6 = white * 0.115926
                
                # 边缘淡入淡出保证循环无咔哒声
                fade = 1.0
                fade_len = int(sample_rate * 0.1)
                if i < fade_len:
                    fade = i / fade_len
                elif i > total_samples - fade_len:
                    fade = (total_samples - i) / fade_len

                sample_val = int(pink * 0.065 * fade * 32767)
                sample_val = max(-32768, min(32767, sample_val))
                frames.extend(struct.pack('<hh', sample_val, sample_val))
            wf.writeframes(frames)

    # 3. 🌧️ 首尔小雨 (seoul_rain.wav) - 6 秒无缝循环
    rain_path = os.path.join(dir_path, "seoul_rain.wav")
    if not os.path.exists(rain_path):
        duration = 6.0
        total_samples = int(sample_rate * duration)
        with wave.open(rain_path, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = bytearray()
            b0 = b1 = b2 = 0.0
            drop_decay_L = 0.0
            drop_decay_R = 0.0
            for i in range(total_samples):
                white = random.uniform(-1.0, 1.0)
                b0 = 0.95 * b0 + white * 0.05
                b1 = 0.85 * b1 + white * 0.15
                rain_bg = (b0 + b1) * 0.5

                # 随机生成微细雨滴落水声
                if random.random() < 0.0018:
                    drop_decay_L = 1.0
                if random.random() < 0.0018:
                    drop_decay_R = 1.0

                drop_L = drop_decay_L * random.uniform(0.5, 1.0) * math.sin(i * 0.08)
                drop_R = drop_decay_R * random.uniform(0.5, 1.0) * math.sin(i * 0.09)
                drop_decay_L *= 0.9985
                drop_decay_R *= 0.9985

                fade = 1.0
                fade_len = int(sample_rate * 0.1)
                if i < fade_len:
                    fade = i / fade_len
                elif i > total_samples - fade_len:
                    fade = (total_samples - i) / fade_len

                val_L = int((rain_bg * 0.12 + drop_L * 0.08) * fade * 32767)
                val_R = int((rain_bg * 0.12 + drop_R * 0.08) * fade * 32767)
                val_L = max(-32768, min(32767, val_L))
                val_R = max(-32768, min(32767, val_R))
                frames.extend(struct.pack('<hh', val_L, val_R))
            wf.writeframes(frames)

    # 4. ☕ 咖啡馆环境音 (cafe_ambience.wav) - 6 秒无缝循环
    cafe_path = os.path.join(dir_path, "cafe_ambience.wav")
    if not os.path.exists(cafe_path):
        duration = 6.0
        total_samples = int(sample_rate * duration)
        with wave.open(cafe_path, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = bytearray()
            low_b = 0.0
            tinkle_decay = 0.0
            for i in range(total_samples):
                white = random.uniform(-1.0, 1.0)
                low_b = 0.98 * low_b + white * 0.02
                # 温暖低频咖啡馆人群低语白噪
                hum = low_b * 1.2 + math.sin(i * 0.002) * 0.05

                # 杯盘偶尔轻触轻音
                if random.random() < 0.0003:
                    tinkle_decay = 1.0
                tinkle = tinkle_decay * math.sin(i * 0.35) * 0.15
                tinkle_decay *= 0.9992

                fade = 1.0
                fade_len = int(sample_rate * 0.1)
                if i < fade_len:
                    fade = i / fade_len
                elif i > total_samples - fade_len:
                    fade = (total_samples - i) / fade_len

                val = int((hum * 0.14 + tinkle) * fade * 32767)
                val = max(-32768, min(32767, val))
                frames.extend(struct.pack('<hh', val, val))
            wf.writeframes(frames)


class AmbiencePlayer:
    """本地轻量白噪音伴学与提示音播放引擎"""

    _instance: Optional['AmbiencePlayer'] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_dir: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._data_dir = data_dir or get_data_path("ambience")
        self._current_type: str = "none"
        self._volume: float = 0.6  # 0.0 ~ 1.0
        self._sounds: Dict[str, any] = {}
        self._ambience_channel = None
        self._chime_channel = None

        self._init_audio()

    def _init_audio(self):
        """初始化音频合成文件与通道"""
        if not PYGAME_AVAILABLE:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(8)
            # Channel 1: 白噪音背景音循环
            self._ambience_channel = pygame.mixer.Channel(1)
            # Channel 2: 提示铃声
            self._chime_channel = pygame.mixer.Channel(2)
        except Exception:
            pass

        # 确保音频文件存在
        _generate_wav_files(self._data_dir)

    def _get_sound(self, filename: str):
        """获取或缓存 pygame Sound 对象"""
        if not PYGAME_AVAILABLE or not filename:
            return None
        if filename in self._sounds:
            return self._sounds[filename]
        
        file_path = os.path.join(self._data_dir, filename)
        if os.path.exists(file_path):
            try:
                snd = pygame.mixer.Sound(file_path)
                self._sounds[filename] = snd
                return snd
            except Exception:
                pass
        return None

    def set_ambience(self, ambience_type: str):
        """切换伴学白噪音类型 ('none', 'rain', 'cafe', 'white')"""
        if ambience_type not in AMBIENCE_TYPES:
            ambience_type = "none"
        
        self._current_type = ambience_type

        if not PYGAME_AVAILABLE:
            return

        if ambience_type == "none":
            if self._ambience_channel:
                self._ambience_channel.stop()
            return

        info = AMBIENCE_TYPES[ambience_type]
        snd = self._get_sound(info["file"])
        if snd and self._ambience_channel:
            self._ambience_channel.set_volume(self._volume)
            self._ambience_channel.play(snd, loops=-1)

    def set_volume(self, volume: float):
        """设置白噪音音量 (0.0 ~ 1.0)"""
        self._volume = max(0.0, min(1.0, volume))
        if self._ambience_channel:
            self._ambience_channel.set_volume(self._volume)

    def get_volume(self) -> float:
        return self._volume

    def get_current_type(self) -> str:
        return self._current_type

    def play_chime(self):
        """播放番茄钟结束轻柔提示音"""
        if not PYGAME_AVAILABLE:
            return
        snd = self._get_sound("timer_chime.wav")
        if snd and self._chime_channel:
            self._chime_channel.set_volume(0.85)
            self._chime_channel.play(snd)

    def stop_all(self):
        """停止所有白噪音与音效"""
        if self._ambience_channel:
            self._ambience_channel.stop()
        if self._chime_channel:
            self._chime_channel.stop()
