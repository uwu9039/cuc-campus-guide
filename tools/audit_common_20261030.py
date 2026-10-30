"""常见问题全量打分：把 presets 的 442 条问法 + 追加自然问法逐条跑一遍。

输出一行一题，便于人工逐条阅读相关度与联想性：
    OK    直接命中
    ASK   反问 / 候选菜单（打印候选，人工判断联想是否对路）
    MISS  没对上
用法：python tools/audit_common_20261030.py [--group 名称片段] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402

EXTRA = [
    # 用户这次点名的四类
    "宿舍桌子规格", "中蓝宿舍一期桌子长宽是多少", "宿舍能用冰箱吗", "宿舍能用洗衣机吗",
    "校园跑", "校园跑多少次", "校园跑怎么计分", "阳光长跑", "闪动校园",
    "班干部有哪些", "班委有哪些", "团支部委员", "班委怎么选", "班委什么时候换届",
    # 其他常见口语问法
    "洗澡有热水吗", "宿舍几点关门", "宿舍电费怎么交", "宿舍报修", "床多大",
    "柜子多大", "宿舍有被子吗", "吹风机在哪", "宿舍能养猫吗", "电动车电池能带回宿舍吗",
    "快递在哪取", "快递地址怎么写", "食堂几点开门", "哪个食堂好吃", "清真食堂在哪",
    "校园卡丢了怎么办", "校园卡怎么充值", "饭卡没钱了", "网费怎么交", "校园网密码忘了",
    "怎么连校园网", "选课什么时候", "补考怎么报名", "缓考怎么申请", "重修怎么选",
    "成绩什么时候出", "绩点怎么算", "转专业什么时候", "辅修怎么报", "微专业怎么报",
    "奖学金怎么申请", "助学金怎么申请", "助学贷款怎么申请", "勤工助学怎么申请",
    "困难认定怎么弄", "医保怎么报销", "校医院在哪", "心理中心在哪", "保卫处电话",
    "图书馆几点开门", "图书馆怎么预约座位", "自习室在哪", "打印店在哪", "游泳馆怎么收费",
    "校车怎么坐", "在读证明怎么开", "成绩单怎么打", "毕业证明怎么补", "学生证丢了",
    "四六级什么时候报名", "普通话考试怎么报名", "教师资格证怎么考", "保研条件",
    "就业协议怎么签", "三方协议", "档案在哪", "户口怎么迁", "出国留学怎么申请",
    "军训要准备什么", "新生报到", "绿色通道", "团组织关系怎么转", "入党怎么申请",
    "社团怎么加", "志愿者怎么报名", "体测什么时候", "体育课怎么选", "免修怎么申请",
    "教室怎么借", "会议室怎么借", "活动场地怎么申请", "失物招领", "报警电话",
]


def load_bank(group: str | None) -> list[tuple[str, str]]:
    data = json.loads((ROOT / "presets.json").read_text(encoding="utf-8"))
    rows: list[tuple[str, str]] = []
    for g in data["groups"]:
        if group and group not in g["name"]:
            continue
        for q in g["items"]:
            rows.append((g["name"], q))
    if not group:
        for q in EXTRA:
            rows.append(("追加", q))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="_audit_common_20261030.jsonl")
    args = ap.parse_args()

    rows = load_bank(args.group or None)
    if args.limit:
        rows = rows[: args.limit]

    out = []
    stat = {"n": 0, "ok": 0, "ask": 0, "miss": 0, "empty": 0}
    t0 = time.time()
    last_group = ""
    for group, q in rows:
        if group != last_group:
            print(f"\n## {group}")
            last_group = group
        try:
            r = app.answer_question(q, {})
        except Exception as e:  # noqa: BLE001
            r = {"matched": False, "error": f"{type(e).__name__}: {e}"}
        item = r.get("item") or {}
        iid = item.get("id") or ""
        title = (item.get("title") or "").replace("\n", " ")[:38]
        opts = [f"{o.get('title', '')[:18]}" for o in (r.get("disambiguate") or [])]
        texts = [a.get("text") for a in (r.get("answers") or []) if a.get("text")]
        steps_n = sum(len(a.get("steps") or []) for a in (r.get("answers") or []))
        empty = bool(r.get("matched")) and not texts and steps_n == 0
        if r.get("disambiguate"):
            kind = "ASK"
            stat["ask"] += 1
            tail = " | ".join(opts[:4])
        elif r.get("matched"):
            kind = "OK"
            stat["ok"] += 1
            tail = f"{iid} · {title}"
        else:
            kind = "MISS"
            stat["miss"] += 1
            tail = ""
        stat["n"] += 1
        stat["empty"] += empty
        flag = " ⚠空" if empty else ""
        print(f"{kind:<4} {q:<26} {tail}{flag}")
        out.append({"group": group, "q": q, "kind": kind, "item": iid, "title": title,
                    "opts": opts, "empty": empty,
                    "confidence": r.get("confidence"), "error": r.get("error") or ""})

    (ROOT / args.out).write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n", encoding="utf-8")
    dur = time.time() - t0
    print(f"\n共 {stat['n']} 题，直接命中 {stat['ok']}，反问/候选 {stat['ask']}，"
          f"没对上 {stat['miss']}，空内容 {stat['empty']}；用时 {dur:.1f}s（{dur / max(1, stat['n']):.2f}s/题）")
    print(f"明细已写入 {args.out}")


if __name__ == "__main__":
    main()
