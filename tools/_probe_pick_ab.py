"""A/B 探针：资格条款到底是「召回不到」还是「挑证据时被截断/漏挑」。

对四个已知失败案例，打印：
  1) _synth_candidates 里是否含目标条目（以及它的引文前 200 字）
  2) 现行 _synth_pick 挑中的编号
  3) 用「全引文 + 明示要挑资格条款」的菜单重挑一次，看目标条款是否进来
不写任何文件，不改 app。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

CASES = [
    ("四六级没过能毕业吗？能保研吗？", "tuimian-tiaojian"),
    ("挂科了还能保研吗？补考通过算吗？", "tuimian-tiaojian"),
    ("校园卡冻结了，奖学金还能打进卡里吗？", None),
    ("辅修和微专业能同时修吗？成绩怎么算？", None),
]

PICK2 = (
    "下面有几条要核实的前提，和一组候选引文。给每条前提挑出**真正能支撑它**的引文编号，"
    "每条 1～3 个；一条都没有就留空数组。\n"
    "特别注意：问到「X 是否要求/是否影响 Y」时，X 的**资格条件条款**本身就是关键证据——"
    "即使这条条款里一个字都没提 Y，也要挑它：条款未列 Y，正是问题的答案。\n"
    '只输出 JSON：{{"picks": {{"0": [1, 5], "1": [3]}}}}。'
)


def run(q: str, target: str | None) -> None:
    print("=" * 74)
    print("Q:", q)
    premises, queries = app._synth_plan(q, {})
    cands = app._synth_candidates(queries or premises, premises, question=q)
    print(" premises:", premises)
    print(" queries:", queries)
    print(" cands:", len(cands))
    if target:
        pos = [i + 1 for i, c in enumerate(cands) if c.get("doc") and target in json.dumps(c, ensure_ascii=False)]
        hit = [c for c in cands if "推免" in (c.get("quote") or "") and "基本条件" in (c.get("quote") or "")]
        print(f" 目标条目在候选里的位置: {pos or '不在'}")
        for c in hit:
            print("   候选引文:", c["quote"][:120].replace("\n", " "))
    # A：现行菜单（160 字截断）
    ev_a = app._synth_pick(premises, cands, queries)
    print(" A 现行挑证据:", len(ev_a), [e["quote"][:22] for e in ev_a])
    # B：全引文 + 资格条款提示
    menu = "\n".join(f"[{i}] {c['doc']}：{c['quote'].replace(chr(10), ' ')}"
                     for i, c in enumerate(cands, 1))
    ask = "\n".join(f"{i}. {p}" for i, p in enumerate(premises))
    raw = app.ds_chat([{"role": "system", "content": PICK2},
                       {"role": "user", "content": f"前提：\n{ask}\n\n候选：\n{menu}"}],
                      max_tokens=400, json_mode=True)
    data = json.loads(raw) or {}
    idx = [int(x) - 1 for xs in (data.get("picks") or {}).values()
           for x in (xs or []) if str(x).isdigit()]
    ev_b = [cands[i] for i in sorted(set(idx)) if 0 <= i < len(cands)]
    print(" B 全引文挑证据:", len(ev_b), [e["quote"][:22] for e in ev_b])
    if target:
        print(" B 是否含 推免基本条件:",
              any("推免" in e["quote"] and "基本条件" in e["quote"] for e in ev_b))


if __name__ == "__main__":
    for q, t in CASES:
        run(q, t)
