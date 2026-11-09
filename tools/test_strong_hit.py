"""强命中免检线的语义：literal 只放过「字面点名」，不放过关键词叠加到 99 的那一档。

2026-11-09 靶向复测的依据：把 99 分放回判定层后，「考试不及格」8/8 对（旧线 0/8），
「宿舍电器」「超市」「补考重修」两臂不变。所以 99 必须有测试钉住，不许被顺手加回来。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

failed = 0


def check(name, ok, detail=""):
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:120])


real = app.STRONG_HIT_MODE
try:
    check("默认是 literal", real == "literal", f"实际 {real}")

    app.STRONG_HIT_MODE = "literal"
    check("100 免检", app._strong_hit(100) is True)
    check("97 免检（去掉问法词后原样命中）", app._strong_hit(97) is True)
    check("99 不免检（关键词叠加）", app._strong_hit(99) is False)
    check("95 不免检", app._strong_hit(95) is False)
    check("0 不免检", app._strong_hit(0) is False)

    app.STRONG_HIT_MODE = "96"
    check("旧线 96 下 99 免检（可回退）", app._strong_hit(99) is True)
    check("旧线 96 下 95 不免检", app._strong_hit(95) is False)

    app.STRONG_HIT_MODE = "100"
    check("阈值 100 下 99 不免检", app._strong_hit(99) is False)
    check("阈值 100 下 100 免检", app._strong_hit(100) is True)

    app.STRONG_HIT_MODE = "garbage"
    check("写错时退回旧线 96，不炸", app._strong_hit(99) is True)
finally:
    app.STRONG_HIT_MODE = real

print("failed", failed)
sys.exit(1 if failed else 0)
