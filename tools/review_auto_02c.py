"""auto_02c 补丁：把 1a5c2d43 正文里的半角逗号改为全角，仅动标点。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "items.json"
OUT = ROOT / "_review_items" / "auto_02c_after.txt"

SUBST: dict[str, list[tuple[str, str]]] = {
    "pt-aff3d77f24": [("考生,按照", "考生，按照")],
    "pt-8fb64419ae": [("指导地位,全面", "指导地位，全面"), ("为核心,培育", "为核心，培育")],
    "pt-bfec2f0976": [("具体办法,健全", "具体办法，健全")],
    "pt-d213738298": [("退学学生,学校", "退学学生，学校")],
    "pt-d2800de753": [("接班人,依据", "接班人，依据")],
}


def suffix_of(title: str) -> str:
    i = title.rfind(" · ")
    return title[i:] if i >= 0 else ""


def main() -> None:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    idx = {it["id"]: it for it in d["items"]}
    changes: list[tuple[str, str, str]] = []
    notes: list[str] = []

    for iid, pairs in SUBST.items():
        it = idx.get(iid)
        if not it:
            notes.append(f"MISSING {iid}")
            continue
        old = it.get("answer") or ""
        new = old
        for a, b in pairs:
            if a in new:
                new = new.replace(a, b)
            else:
                notes.append(f"SUBST-NOT-FOUND {iid} {a!r}")
        if old == new:
            notes.append(f"NO-OP {iid}")
            continue
        changes.append((iid, old, new))
        it["answer"] = new
        suf = suffix_of(it.get("title") or "")
        head = new[:40] + ("…" if len(new) > 40 else "")
        it["title"] = head + suf
        al = it.get("aliases") or []
        if al and (al[0].endswith("…") or old.startswith(al[0])):
            al[0] = head

    d["updated"] = "2026-10-30"
    DATA.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    with OUT.open("w", encoding="utf-8") as o:
        for iid, old, new in changes:
            o.write(f"### {iid}\nOLD: {old}\nNEW: {new}\n\n")

    print(f"修改 {len(changes)} 条，剩余 {len(d['items'])} 条")
    for n in notes:
        print("  ", n)


if __name__ == "__main__":
    main()
