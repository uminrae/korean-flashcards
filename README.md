# 未来的韩语卡片

一个 Windows 桌面端的韩语悬浮背单词卡片。内置延世韩国语词库，边背边听真人发音，支持剪贴板划词翻译、韩语变位、助词高亮、番茄钟与学习统计热力图。

基于 PyQt6 + edge-tts 构建。

## 功能

| 模块 | 说明 |
| --- | --- |
| 悬浮卡片 | 桌面置顶单词卡，支持键盘快捷键与迷你条 |
| 词库 | 内置延世韩国语分册分课词表（`data/korean_vocab.json`） |
| 发音 | edge-tts 在线合成（ko-KR-SunHiNeural / InJoonNeural），本地缓存秒播；离线回退 pyttsx3 / SAPI5 |
| 划词翻译 | 监听剪贴板，划词即弹翻译抽屉 |
| 韩语变位 | 动词/形容词变位规则解析（`core/korean_conjugator.py`） |
| 助词高亮 | 句子中助词自动识别与高亮（`core/particle_highlighter.py`） |
| 汉字音转换 | 韩语汉字词 ↔ 汉字对照（`core/hanja_converter.py`） |
| 字帖生成 | 生成韩语临摹字帖（`core/copybook_generator.py`） |
| 番茄钟 | 计时 + 白噪音（咖啡厅 / 首尔雨声 / 白噪音） |
| 统计 | 学习记录持久化与复习热力图 |
| 老板键 | 一键隐藏窗口 |
| 备份 / 恢复 | 词库与学习进度导出导入 |

## 运行

```bash
pip install -r requirements.txt
python -X utf8 main.py
```

## 打包

```bash
python build_exe.py          # PyInstaller 打包为 exe
python build_installer.py    # 生成安装包（需 Inno Setup）
```

## 目录结构

```
core/       核心逻辑（词库、TTS、变位、统计、翻译等 21 个模块）
ui/         界面层（主窗口、卡片、对话框、托盘）
utils/      路径与资源工具
data/       词库、自定义生词本、字体
assets/     应用图标
scripts/    验证脚本
tests/      回归测试
```

## 注意

**翻译接口**：`core/translator_manager.py` 中的 Papago `n2mt`、有道 `aidemo`、Google `translate_a/single` 均为第三方**非官方**端点，可能随时失效或被限制。默认可用 MyMemory 公开接口替代。请勿用于商业或高频调用。

**字体**：`data/fonts/` 下的手写字体未随仓库分发。字帖功能需要你自备一个韩语 TTF 放入该目录，并在 `core/copybook_generator.py` 中修改文件名。

**歌词数据**：`data/idle_lyrics.json` 包含韩语歌词原文与译文，版权归原作者所有，仅供个人学习，未随仓库分发。

## 许可

MIT，见 `LICENSE`。
