"""修 PDF 域代码、页码残留、星号乘号和收尾标题，只动这些字段。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"
ART = re.compile(r"(?:MM)?PAGE\s*\\?\*?\s*(?:M)?ERGE[A-Z]*\s*\d*", re.I)
PGNO = re.compile(r"(?:(?<=^)|(?<=\n)|\s)[—–]\s*\d{1,3}\s*[—–](?=\s|$|\n)")

d = json.loads(P.read_text(encoding="utf-8"))
changed = []


def fix_text(v):
    n = ART.sub("", v)
    n = PGNO.sub(" ", n)
    return n


def walk(it):
    touched = []
    for k, v in list(it.items()):
        if isinstance(v, str):
            n = fix_text(v)
            if n != v:
                it[k] = n
                touched.append(k)
    for i, s in enumerate(it.get("steps") or []):
        if isinstance(s, dict):
            for k in ("what", "where", "when"):
                if isinstance(s.get(k), str):
                    n = fix_text(s[k])
                    if n != s[k]:
                        s[k] = n
                        touched.append(f"steps.{i}.{k}")
        elif isinstance(s, str):
            n = fix_text(s)
            if n != s:
                it["steps"][i] = n
                touched.append(f"steps.{i}")
    for i, m in enumerate(it.get("materials") or []):
        if isinstance(m, dict) and isinstance(m.get("name"), str):
            n = fix_text(m["name"])
            if n != m["name"]:
                m["name"] = n
                touched.append(f"materials.{i}")
    for key in ("pitfalls", "advisory"):
        for i, p in enumerate(it.get(key) or []):
            if isinstance(p, str):
                n = fix_text(p)
                if n != p:
                    it[key][i] = n
                    touched.append(f"{key}.{i}")
    return touched


for it in d["items"]:
    t = walk(it)
    if t:
        changed.append((it["id"], t))

by_id = {it["id"]: it for it in d["items"]}

# 乘号：课程学时×课程系数
x = by_id["pt-b4cd59846b"]
for k in ("title", "answer"):
    if isinstance(x.get(k), str):
        x[k] = x[k].replace("课程学时*课程系数", "课程学时×课程系数")

# 星号只是分隔符：选课的要点，具体课程所属类别
y = by_id["pt-65a5329a25"]
for k in ("title", "answer"):
    if isinstance(y.get(k), str):
        y[k] = y[k].replace("选课的要点*具体课程", "选课的要点，具体课程")

# 标题被截断在「14:00—1」，用完整原句重写标题，保留来源后缀
z = by_id["pt-d3e9a4a4b1"]
src_tail = z["title"].split(" · ", 1)[1] if " · " in z["title"] else ""
z["title"] = z["answer"].lstrip("4.").strip() + (f" · {src_tail}" if src_tail else "")

# 就业协议首次签约步骤改回原文
j = by_id["jy-xieyishu"]
full = ("与用人单位达成就业意向的毕业生应与用人单位签订《就业协议书》。如需政审，"
        "就业创业指导中心负责统筹协调，学部（院）负责出具思想鉴定、安排谈话对象，"
        "保卫处负责核查毕业生遵纪守法情况并出具相关材料，学生档案管理部门"
        "（学生工作处、研究生院）负责配合用人单位阅档。")
j["steps"][0]["what"] = full
j["evidence"]["steps.0"]["quote"] = full.rstrip("。")

P.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
print("items", len(d["items"]))
for c in changed:
    print(c)
