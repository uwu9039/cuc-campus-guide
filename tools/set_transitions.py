"""给每一拍指定转场类型（写进 beats.json，Video.tsx 读取）。

可用类型：
  whip    鞭甩——横向位移 + 运动模糊
  zoom    推镜爆点——从放大 + 模糊收进
  flash   白闪——一闪而过，用于强节奏点
  skew    斜切擦除——从右下角斜着推入
  shake   震屏——落地瞬间抖一下（配 punch 卡）
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEATS = ROOT / "video-remotion" / "src" / "beats.json"

# 与 tts_beats.py 里的 a1..a8 一一对应
TRANS = {
    "a1": "zoom",    # 开场从放大收进
    "a2": "whip",    # 鞭甩切到界面
    "a3": "zoom",    # 推近
    "a4": "flash",   # 答案落点，白闪一下
    "a5": "skew",    # 斜切换到另一件事
    "a6": "zoom",    # 再推近
    "a7": "flash",   # 数字拍，白闪
    "a8": "shake",   # 收尾震屏
}


def main() -> None:
    beats = json.loads(BEATS.read_text(encoding="utf-8"))
    for b in beats:
        b["trans"] = TRANS.get(b["id"], "whip")
    BEATS.write_text(json.dumps(beats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {len(beats)} 拍的转场：", ", ".join(f"{b['id']}={b['trans']}" for b in beats))


if __name__ == "__main__":
    main()
