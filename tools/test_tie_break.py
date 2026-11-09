"""同分定序的回归：模型给分并列时，按候选池名次取靠前那条，不许靠采样运气。

盯三件事：
  1. 分数严格相等才动，更高分一律不顶（否则就是拿名次否决模型的判断）。
  2. 模型没给 best 打分时原样返回，不猜。
  3. best 为 None（模型判死）时返回 None，不许定序把它「救」成某条。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

failed = 0


def check(name, ok, detail=""):
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:120])


def it(i, auto):
    return {"id": i, "title": i, "auto": auto}


app.TIE_BREAK = True
pool = [(it("a", True), 91), (it("b", False), 88), (it("c", False), 70)]
check("同分取池子靠前", app._tie_break(pool, {"a": 85, "b": 85, "c": 85}, it("c", False))["id"] == "a", "")
check("更高分不被动", app._tie_break(pool, {"a": 80, "b": 90}, it("b", False))["id"] == "b", "")
check("模型没给分原样返回", app._tie_break(pool, {}, it("b", False))["id"] == "b", "")
check("判死时不许被定序救回", app._tie_break(pool, {"a": 85}, None) is None, "")
check("并列里含整理条目时按池子顺序，不按类型改写",
      app._tie_break([(it("x", True), 90), (it("y", False), 85)], {"x": 86, "y": 86}, it("y", False))["id"] == "x", "")
app.TIE_BREAK = False
check("开关关着时一个字都不动（归因档要能复现现行）",
      app._tie_break(pool, {"a": 85, "b": 85, "c": 85}, it("c", False))["id"] == "c", "")
print("failed", failed)
sys.exit(1 if failed else 0)
