"""给会分叉的条目补反问条件：slots + 步骤 if 条件，只问真的会改变答案的。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"


def slot(key, ask, options, decides, why, hints=None):
    s = {
        "key": key,
        "ask": ask,
        "options": options,
        "required": True,
        "decides": decides,
        "why": why,
        "blocking": True,
    }
    if hints:
        s["hints"] = hints
    return s


PLAN = {
    # 保留学籍：入伍多一道武装部审批
    "xueji-baoliu": {
        "slots": [
            slot(
                "reason",
                "你是因为什么要保留学籍？",
                ["应征入伍", "参加境内外交流或跨校联合培养超过一学期（含）", "自费出国（境）留学", "其他"],
                ["steps", "overview"],
                "应征入伍还要多一道武装部审核",
                {"应征入伍": ["入伍", "参军", "当兵"], "自费出国（境）留学": ["自费留学", "出国留学"]},
            )
        ],
        "ifs": {3: {"reason": "应征入伍"}},
    },
    # 退学：主动和被退学的流程不同
    "xueji-tuixue": {
        "slots": [
            slot(
                "mode",
                "你是自己想退学，还是学校拟作退学处理？",
                ["主动退学", "被退学"],
                ["steps", "overview"],
                "两条流程完全不一样",
                {"主动退学": ["我想退学", "主动退学"], "被退学": ["被退学", "劝退", "学校让我退"]},
            )
        ],
        "ifs": {0: {"mode": "主动退学"}, 1: {"mode": "被退学"}},
    },
    # 复学：因病休学要交医院证明并复查
    "xueji-fuxue": {
        "slots": [
            slot(
                "reason",
                "当初是因为什么休学的？",
                ["因病休学", "其他原因"],
                ["steps", "materials", "overview"],
                "因病休学要额外交二级甲等以上医院证明，并经校医院复查",
                {"因病休学": ["生病", "因病", "看病", "住院"]},
            )
        ],
        "ifs": {2: {"reason": "因病休学"}},
    },
    # 跨校转学：研究生多一道导师同意
    "moe-zhuanxue": {
        "slots": [
            slot(
                "level",
                "你是本科生还是研究生？",
                ["本科生", "研究生"],
                ["steps", "overview"],
                "研究生转学还要经拟转入专业导师同意",
            )
        ],
        "ifs": {3: {"level": "研究生"}},
    },
    # 毕业生户口档案：去向决定拿户口卡还是迁移证
    "biye-hukou-dangan": {
        "slots": [
            slot(
                "dest",
                "毕业后你的户口打算怎么走？",
                ["北京就业且落户", "外埠就业且落户", "暂不就业 / 考研 / 出国", "需要缓迁"],
                ["steps", "overview"],
                "北京落户领户口卡，外埠落户领迁移证，暂不就业迁回原籍，缓迁要先办暂留",
            )
        ],
        "ifs": {
            0: {"dest": "北京就业且落户"},
            1: {"dest": "外埠就业且落户"},
            2: {"dest": "暂不就业 / 考研 / 出国"},
            3: {"dest": "需要缓迁"},
        },
    },
    # 快递：校内和梆子井是两个驿站
    "kuaidi-yizhan": {
        "slots": [
            slot(
                "campus",
                "你住校内还是梆子井公寓？",
                ["校内", "梆子井"],
                ["steps", "location", "overview"],
                "两个园区各有一个菜鸟驿站，位置不同",
                {"校内": ["学校里面", "校内"], "梆子井": ["梆子井", "公寓"]},
            )
        ],
        "ifs": {0: {"campus": "校内"}, 1: {"campus": "校内"}, 2: {"campus": "梆子井"}},
    },
    # 充电桩：校内和梆子井位置不同
    "zxc-chongdian": {
        "slots": [
            slot(
                "campus",
                "你的车停在校内还是梆子井？",
                ["校内", "梆子井"],
                ["steps", "location", "overview"],
                "两边充电桩位置不一样",
                {"校内": ["学校里面", "校内"], "梆子井": ["梆子井"]},
            )
        ],
        "ifs": {0: {"campus": "校内"}, 1: {"campus": "校内"}, 2: {"campus": "梆子井"}},
    },
    # 校门：校外人员要预约
    "xiaomen-jinchu": {
        "slots": [
            slot(
                "who",
                "你是校内师生，还是校外人员 / 车辆？",
                ["校内师生", "校外人员或车辆"],
                ["steps", "overview"],
                "校外人员和车辆需要访客预约才能进校",
                {"校内师生": ["我是学生", "我是老师", "校内"], "校外人员或车辆": ["校外", "访客", "家长", "开车"]},
            )
        ],
        "ifs": {2: {"who": "校外人员或车辆"}},
    },
    # 境外交流：超过一学期要办保留学籍
    "waijing-jiaoliu": {
        "slots": [
            slot(
                "length",
                "你计划在外学习多久？",
                ["不超过一学期", "超过一学期（含一学期）"],
                ["steps", "overview"],
                "超过一学期（含）要额外办理保留学籍",
            )
        ],
        "ifs": {2: {"length": "超过一学期（含一学期）"}},
    },
    # 新生报到：不能按期报到要事先书面请假
    "xinsheng-baodao": {
        "slots": [
            slot(
                "ontime",
                "你能在 9 月 5 日—6 日按期报到吗？",
                ["能按期报到", "不能按期报到"],
                ["steps", "overview"],
                "不能按期报到要事先向学院和本科生院书面请假",
            )
        ],
        "ifs": {2: {"ontime": "不能按期报到"}},
    },
    # 助学贷款：生源地 / 校园地办理地点不同
    "dk-zhuxue": {
        "slots": [
            slot(
                "kind",
                "你想办生源地贷款还是校园地贷款？",
                ["生源地贷款", "校园地贷款"],
                ["steps", "location", "overview"],
                "一个找户籍所在地资助部门，一个找学校资助部门",
                {"生源地贷款": ["生源地"], "校园地贷款": ["校园地", "学校办"]},
            )
        ],
        "ifs": {0: {"kind": "生源地贷款"}, 1: {"kind": "校园地贷款"}},
    },
}


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    by_id = {it["id"]: it for it in data["items"]}

    for iid, plan in PLAN.items():
        it = by_id[iid]
        it["slots"] = plan["slots"]
        for idx, cond in plan["ifs"].items():
            assert 0 <= idx < len(it["steps"]), f"{iid} 没有第 {idx} 步"
            it["steps"][idx]["if"] = cond

    # 已有的非阻断槽位：确实会分叉的改成会追问
    by_id["jwc-chengjidan"]["slots"][1]["blocking"] = True
    by_id["jwc-chengjidan"]["steps"][1]["if"] = {"sealed": "需要"}

    liuxue = by_id["liuxue-jiaoliu"]
    for s in liuxue["slots"]:
        if s["key"] == "kind":
            s["blocking"] = True
    liuxue["steps"][1]["if"] = {"kind": "因公（校际交流 / 联合培养）"}
    liuxue["steps"][2]["if"] = {"kind": "因私（自费留学）"}

    data["updated"] = "2026-10-29"
    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(1 for it in data["items"] if it.get("slots"))
    print(f"更新 {len(PLAN)} 个条目的追问条件，当前 {n} 个条目带 slots")


if __name__ == "__main__":
    main()
