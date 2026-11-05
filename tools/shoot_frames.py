"""重抓视频要用的界面截图（对齐「广院通」新版界面）。

用法：python tools/shoot_frames.py
输出：video-remotion/public/raw-*.png
"""
from __future__ import annotations

import subprocess
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "video-remotion" / "public"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# 文件 → (问题, 窗口宽, 窗口高)
SHOTS = {
    "raw-2.png": ("成绩单密封章几点能办", 760, 620),
    "raw-3.png": ("选课什么时候截止", 760, 620),
    "raw-zwzy.png": ("转去新闻学院要什么条件", 760, 620),
    "raw-tic.png": ("体测免测怎么办", 760, 620),
    "raw-xyk.png": ("校园卡丢了怎么补", 760, 620),
    "raw-bx.png": ("宿舍报修找谁", 760, 620),
}


def main() -> None:
    for name, (q, w, h) in SHOTS.items():
        url = "http://127.0.0.1:8000/?q=" + urllib.parse.quote(q)
        cmd = [
            EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=2", f"--window-size={w},{h}",
            "--virtual-time-budget=12000",
            f"--user-data-dir={Path.home()}/AppData/Local/Temp/edge-shot-{name}",
            f"--screenshot={OUT / name}", url,
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)
        size = (OUT / name).stat().st_size if (OUT / name).exists() else 0
        print(f"  {name:<14}{size:>8} B  {q}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
