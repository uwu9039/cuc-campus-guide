"""扩大扫描面积：排除项目自身文件，列出机器上其他位置的候选官方材料。"""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("scan", "tools/scan_local.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

ROOTS = [
    r"（本地路径已隐藏）",
    r"（本地路径已隐藏）",
    r"（本地路径已隐藏）",
    r"（本地路径已隐藏）",
    "D:\\",
]
PROJECT = "智能体节"

rows = []
for p in m.walk(ROOTS, max_files=6000):
    sp = str(p)
    if PROJECT in sp:
        continue
    if not m.NAME_HINTS.search(p.name):
        continue
    try:
        text = m.sniff(p)
    except Exception:
        text = ""
    official = any(k in text for k in m.BODY_HINTS)
    rows.append((p.stat().st_size // 1024, official, sp))

rows.sort(reverse=True)
print(f"命中 {len(rows)} 个（已排除项目自身文件）\n")
for kb, off, path in rows[:30]:
    print(f"{kb:>6}KB {'官方' if off else '  ?'}  {path[:104]}")
