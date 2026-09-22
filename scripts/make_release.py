import os, shutil, sys

SRC = r"C:\Users\min.qeoleu\Desktop\korean"
DST = r"C:\Users\min.qeoleu\Desktop\korean_release"

EXCLUDE_DIRS = {"__pycache__", "build", "dist", "Output", "cache", "fonts", "ambience",
                "audio_cache", "test_output", ".workbuddy-ai", ".git"}
EXCLUDE_EXT = {".pyc", ".pyo", ".db", ".log", ".tmp", ".ttf", ".wav", ".mp3"}
EXCLUDE_FILES = {"idle_lyrics.json", "custom_vocab.json", "verify_result.txt",
                 "debug_run.log", "执行.txt"}

copied_files = 0
copied_bytes = 0

def should_skip_dir(name):
    return name in EXCLUDE_DIRS

def should_skip_file(name):
    if name in EXCLUDE_FILES:
        return True
    if os.path.splitext(name)[1].lower() in EXCLUDE_EXT:
        return True
    if name.endswith(".spec"):
        return True
    return False

TOP_FILES = ["main.py", "requirements.txt", "README.md", "LICENSE", ".gitignore",
             "build_exe.py", "build_installer.py", "build_exe.bat", "build_installer.bat",
             "installer.iss", "process_icon.py", "ChineseSimplified.isl"]
TOP_DIRS = ["core", "ui", "utils", "tests", "scripts", "config", "assets"]

if os.path.exists(DST):
    shutil.rmtree(DST)
os.makedirs(DST)

def copy_dir(rel):
    global copied_files, copied_bytes
    src = os.path.join(SRC, rel)
    dst = os.path.join(DST, rel)
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        for f in files:
            if should_skip_file(f):
                continue
            s = os.path.join(root, f)
            rel_path = os.path.relpath(s, SRC)
            d = os.path.join(DST, rel_path)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            copied_files += 1
            copied_bytes += os.path.getsize(s)

for f in TOP_FILES:
    s = os.path.join(SRC, f)
    if os.path.exists(s):
        shutil.copy2(s, os.path.join(DST, f))
        copied_files += 1
        copied_bytes += os.path.getsize(s)

for d in TOP_DIRS:
    p = os.path.join(SRC, d)
    if os.path.isdir(p):
        copy_dir(d)

# 复制词库（仅 json 词表）
data_src = os.path.join(SRC, "data")
data_dst = os.path.join(DST, "data")
os.makedirs(data_dst, exist_ok=True)
for f in os.listdir(data_src):
    if f.endswith(".json") and f not in EXCLUDE_FILES:
        s = os.path.join(data_src, f)
        shutil.copy2(s, os.path.join(data_dst, f))
        copied_files += 1
        copied_bytes += os.path.getsize(s)

# 空模板：自定义生词本
with open(os.path.join(data_dst, "custom_vocab.example.json"), "w", encoding="utf-8") as fp:
    fp.write('{\n  "title": "自定义生词本与剪贴板划词库",\n  "updated_at": "",\n  "words": []\n}\n')

# 空模板：字体目录说明
os.makedirs(os.path.join(data_dst, "fonts"), exist_ok=True)
with open(os.path.join(data_dst, "fonts", "README.txt"), "w", encoding="utf-8") as fp:
    fp.write("把你的韩语 TTF 字体放进本目录，并在 core/copybook_generator.py 中改成对应文件名。\n")

print(f"OK  files={copied_files}  size={copied_bytes/1024/1024:.2f} MB  -> {DST}")
