"""检查 _display_text 只改标点、不改字词。

对 items.json 里所有会走 _display_text 的字段，去掉标点空白后逐字比对；
字词有增删就列出来，人工确认是不是把原意改了。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

PUNCT = re.compile(r"[\s，。；：、！？!?,.;:\"'“”‘’「」『』（）()《》〈〉…\-—–~～*＊#·|/\\\[\]{}<>+=_`^&%$@]")
AI_FILLER = re.compile(
    r"首先|其次|再次|最后|此外|另外|综上(?:所述)?|总而言之|总的来说|"
    r"值得注意的是|需要注意的是|需要说明的是|值得一提的是|"
    r"简单来说|简而言之|换句话说|说到底|说白了|表面看是|归根结底|"
    r"往深了说|说到这|你发现没|说来有趣|这条我认|这流程我熟|"
    r"我理解你的(?:痛苦|焦虑|难处|处境)|你不是一个人|"
    r"按照这个方案|马上去行动|话不多说|不多废话")


def skeleton(s: str) -> str:
    s = str(s)
    # 区间的连字符和波浪线换成「至」，其余破折号只当标点
    s = re.sub(r"(?<=[0-9年月日元岁级])\s*[-—–~～]+\s*(?=[0-9])", "至", s)
    s = re.sub(r"(?<=[0-9年月日])\s*[-—–~～]+\s*(?=次年|翌年)", "至", s)
    s = re.sub(r"(?<=周[一二三四五六日天])\s*[~～]\s*(?=周)", "至", s)
    s = re.sub(r"[~～]", "至", s)
    s = re.sub(r"[-—–―]+", "", s)
    # 星号写成「星号」或直接删掉都算标点处理；星号换成乘号也不算改词
    s = s.replace("星号", "").replace("*", "").replace("＊", "")
    s = s.replace("×", "*").replace("*", "")
    s = s.replace("而是", "是")
    # 比例冒号写成「比」只算标点，不算增词
    s = re.sub(r"(?<=\d)\s*比\s*(?=\d)", "", s)
    # 用户点名要删的口头禅不算事实内容
    s = AI_FILLER.sub("", s)
    return PUNCT.sub("", s)


def fields(item: dict):
    for k in ("title", "answer", "fee", "location", "hours", "duration", "window",
              "note", "scope_note"):
        if isinstance(item.get(k), str) and item[k].strip():
            yield k, item[k]
    for i, s in enumerate(item.get("steps") or []):
        if isinstance(s, dict):
            for k in ("what", "where", "when"):
                if isinstance(s.get(k), str) and s[k].strip():
                    yield f"steps.{i}.{k}", s[k]
        elif isinstance(s, str) and s.strip():
            yield f"steps.{i}", s
    for i, m in enumerate(item.get("materials") or []):
        if isinstance(m, dict) and isinstance(m.get("name"), str) and m["name"].strip():
            yield f"materials.{i}", m["name"]
    for i, p in enumerate(item.get("pitfalls") or []):
        if isinstance(p, str) and p.strip():
            yield f"pitfalls.{i}", p
    for i, p in enumerate(item.get("advisory") or []):
        if isinstance(p, str) and p.strip():
            yield f"advisory.{i}", p
    for i, s in enumerate(item.get("slots") or []):
        if isinstance(s, dict):
            for k in ("ask", "why"):
                if isinstance(s.get(k), str) and s[k].strip():
                    yield f"slots.{i}.{k}", s[k]


def main() -> None:
    data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    total = 0
    bad = []
    for item in data["items"]:
        for field, raw in fields(item):
            total += 1
            out = app._display_text(raw)
            if skeleton(raw) != skeleton(out):
                bad.append((item["id"], field, raw, out))
    print(f"检查字段 {total} 个，字词有变化 {len(bad)} 个")
    for iid, field, raw, out in bad[:200]:
        print(f"\n--- {iid} {field}\n原：{raw}\n新：{out}")
    if len(bad) > 200:
        print(f"\n……其余 {len(bad) - 200} 个未显示")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
