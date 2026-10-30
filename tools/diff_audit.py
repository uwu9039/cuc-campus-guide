"""对比两轮审计文本，只列出结果有变化的题。"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse(p: Path) -> dict[str, tuple[str, str]]:
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(OK|ASK|MISS)\s+(.+?)\s{2,}(.*)$", line)
        if m:
            out[m.group(2).strip()] = (m.group(1), m.group(3).strip())
    return out


old, new = parse(ROOT / sys.argv[1]), parse(ROOT / sys.argv[2])
print(f"{len(old)} -> {len(new)} 题")
for q in sorted(set(old) | set(new)):
    a = old.get(q)
    b = new.get(q)
    if a != b:
        print(f"{q:<26} {a[0] if a else '—':<5} {a[1][:44] if a else '':<46} => {b[0] if b else '—':<5} {b[1][:44] if b else ''}")
