"""按官方原文修正条目里被改硬的限定语（2026-10-29 限定语审计）。

原则：条目文本只能复述原文；原文写「原则上 / 一般 / 需」，条目不得写成
「必须 / 一律 / 禁止」。每一处修改都把 evidence.quote 扩到能覆盖整句。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"

# id -> [(字段, 新文本, 新证据 quote 或 None 表示沿用)]
FIX = {
    "jwc-zaidu": [
        ("pitfalls.0", "非京籍需依照规定填写相应审批表，持四份表格到本科生院办理盖章手续",
         {"sources": [
             {"src": "20201222-c13068a177272",
              "quote": "非京籍：根据教育部、北京市教委和北京市公安局等有关规定，非京籍需依照规定填写相应审批表"},
             {"src": "20201222-c13068a177272",
              "quote": "持四份表格到本科生院办理盖章手续"},
         ]}),
    ],
    "jwc-buxuanke": [
        ("steps.0", "学生一般在每学期开学初进行本学期课程的补（退）选课，每学期末进行下学期课程的选课", None),
        ("pitfalls.0", "补退选课结束后，不再允许补退选课", None),
    ],
    "it-youxiang": [
        ("pitfalls.0", "使用人毕业、离校后，邮箱将统一注销，请务必于离校前完成数据备份工作", None),
    ],
    "moe-zhuanxue": [
        ("pitfalls.2", "转学须经所在学校和拟转入学校同意", None),
    ],
    "zxj-guojia": [
        ("pitfalls.0", "不用盖章但需个人承诺并签字，请诚实守信、如实填写", None),
    ],
    "jwc-zhuanhuan": [
        ("pitfalls.0",
         "未经国际交流与合作处或本科生院批准，学生自行联系并参加的境（内）外交流项目或自费赴境（内）外大学学习，所修读课程及学分不予置换或认定",
         {"src": "hbkechengzhihuan",
          "quote": "第四条　未经国际交流与合作处或本科生院批准，学生自行联系并参加的境（内）外交流项目或自费赴境（内）外大学学习，所修读课程及学分不予置换或认定。"}),
    ],
    "gzc-zhaobiao": [
        ("pitfalls.0", "凡符合本办法第十七条规定的采购项目，一般应采用公开招标方式",
         {"src": "9015703667", "quote": "第二十一条 凡符合本办法第十七条规定的采购项目，一般应采用公开招标方式。"}),
    ],
    "waijing-jiaoliu": [
        ("pitfalls.0",
         "未经学校事先审批而自主到境外大学学习的，其学分不予认定",
         {"src": "70165cc26f",
          "quote": "（一）凡我校在读本科生，经学校批准，赴与我校签署交流协议的境外大学学习者，所获得的各类学分均须认定。未经学校事先审批而自主到境外大学学习的，其学分不予认定。"}),
        ("pitfalls.1",
         "境外没有对应课程的专业核心课，需在规定的最长有效修业年限内补修并成绩合格后方能毕业",
         {"src": "70165cc26f",
          "quote": "（五）学生因在境外学习而错过的本专业培养计划中的专业核心课，而境外学习期间没有与其相同或者教学内容相近的课程，需要在规定的最长有效修业年限内补修并成绩合格后方能毕业"}),
    ],
    "biye-hukou-dangan": [
        ("pitfalls.0", "户档暂留期间只办理与迁户相关的手续，户口卡一律不外借",
         {"src": "hb49833f4409",
          "quote": "（六）需要办理户档暂留手续的，在学生工作部（处）就业科办理相应的手续，并持相关证明到保卫部（处）户籍科备案。户档暂留期间只办理与迁户相关的手续，户口卡一律不外借。"}),
    ],
    "xszz-qingong": [
        ("pitfalls.0", "学生参加勤工助学的时间原则上每周不超过 8 小时，每月不超过 40 小时", None),
    ],
    "xueji-fuxue": [
        ("window", "原则上应在新学期开学后两周之内提出复学申请", None),
    ],
}


def set_field(item: dict, key: str, text: str) -> None:
    head, _, idx = key.partition(".")
    if not idx:
        item[key] = text
        return
    if head == "pitfalls":
        item["pitfalls"][int(idx)] = text
    elif head == "steps":
        item["steps"][int(idx)]["what"] = text
    elif head == "materials":
        item["materials"][int(idx)]["name"] = text
    else:
        raise KeyError(key)


def main() -> None:
    data = json.loads(P.read_text(encoding="utf-8"))
    items = {i["id"]: i for i in data["items"]}
    changed = 0
    for iid, edits in FIX.items():
        item = items[iid]
        for key, text, ev in edits:
            set_field(item, key, text)
            if ev is not None:
                item["evidence"][key] = ev
            changed += 1
    P.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"修正 {len(FIX)} 个条目 / {changed} 个字段")


if __name__ == "__main__":
    main()
