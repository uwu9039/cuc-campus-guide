"""按 humanizer-zh 的检查点扫描界面文案：只报告，不自动改。

用法：python tools/humanize_lint.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")
TARGETS = [ROOT / "index.html", ROOT / "app.py"]

PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("假对比", re.compile(r"不是.{1,12}而是"), "只抬语气就删，真纠错才留"),
    ("起跑式铺垫", re.compile(r"让我们|接下来我们|以下是你需要知道|本文将深入"), "删掉预告句"),
    ("拔高尾巴", re.compile(r"彰显了|标志着|充分体现|开创.{0,4}新"), "删掉只赞美的尾巴"),
    ("客服腔", re.compile(r"好问题|希望.{0,6}有帮助|亲爱的用户|感谢您的"), "独立文章里删"),
    ("AI 高频词", re.compile(r"赋能|闭环|至关重要|深入探讨|无缝衔接|全方位"), "空泛才改，术语保留"),
    ("套话收尾", re.compile(r"拭目以待|至此结束|综上所述|让我们一起"), "没有信息就删"),
    ("限定堆叠", re.compile(r"也许可能|可能或许|大概也许"), "压成一层不确定"),
    ("进行+动词", re.compile(r"进行(测试|检查|确认|评估|核实)"), "换直接动词"),
    ("被动堆叠", re.compile(r"被.{1,8}被"), "改成主动或拆句"),
    ("假想敌", re.compile(r"不要误会|我不是在|并不是说"), "直接说事"),
]

# 只扫"用户能看到的字符串"，跳过代码与注释
def extract_strings(path: Path) -> list[tuple[int, str]]:
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if s.startswith(("#", "//", "/*", "*")):
            continue
        for m in re.finditer(r'"([^"\\]{6,120})"|\'([^\'\\]{6,120})\'|>([^<>{}]{6,120})<', line):
            text = next(g for g in m.groups() if g)
            if re.search(r"[\u4e00-\u9fff]", text):
                out.append((i, text.strip()))
    return out


def main() -> None:
    hits = []
    for f in TARGETS:
        if not f.exists():
            continue
        for line, text in extract_strings(f):
            for name, rx, advice in PATTERNS:
                if rx.search(text):
                    hits.append((f.name, line, name, text[:56], advice))
    if not hits:
        print("✓ 没有命中检查点")
        return
    print(f"命中 {len(hits)} 处（仅供参考，改不改看上下文）\n")
    for f, line, name, text, advice in hits:
        print(f"  [{name}] {f}:{line}")
        print(f"    文案：{text}")
        print(f"    建议：{advice}")


if __name__ == "__main__":
    main()
