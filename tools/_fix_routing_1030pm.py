"""修正 10-30 晚回归发现的 3 处劫持：交流学分认定泛词、新生户口抢身份证、转专业课程条款缺步骤。

只做 upsert / 追加，不删除任何条目。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "items.json"

data = json.loads(PATH.read_text(encoding="utf-8"))
items = {it["id"]: it for it in data["items"]}


def add_unique(lst: list, vals: list) -> None:
    for v in vals:
        if v not in lst:
            lst.append(v)


# 1. 课程置换与学分认定：学分认定是全校成绩管理环节的统称，留作关键词会把
#    「实习学分怎么认定」这类问句劫持进来；只保留交流/交换/外校的具体说法。
it = items["jwc-zhuanhuan"]
it["aliases"] = [a for a in it["aliases"] if a != "学分认定"]
it["keywords"] = [k for k in it["keywords"] if k != "学分认定"]
add_unique(it["aliases"], ["交流学分认定", "外校学分认定", "交换学分认定"])
add_unique(it["keywords"], ["学籍异动"])
it["steps"].append({
    "when": "转专业/休学等",
    "what": "学籍异动（含转专业、休学、保留学籍、留降级等）前所修读的课程，也在可申请课程置换或学分认定的范围内",
    "where": "本科生院",
})
it["evidence"]["steps.3"] = {
    "src": "hbkechengzhihuan",
    "quote": "（三）学生学籍异动（含转专业、休学、保留学籍、留降级等）前所修读的课程",
}

# 2. 新生户口迁移：问身份证丢了/过期，答的是身份证办理，不是迁户口。
it = items["xinsheng-hukou"]
add_unique(it.setdefault("exclude", []), ["身份证丢", "身份证过期", "身份证补办", "换身份证", "补领身份证"])

# 3. 转专业：补上转入后的课程置换、补修与培养方案，问「转专业后课程怎么补」才有答案。
it = items["zhuanzhuanye"]
add_unique(it["aliases"], ["转专业学分", "转专业补修", "转专业课程"])
add_unique(it["keywords"], ["转专业学分", "补修", "课程置换"])
new_steps = [
    ("转入后·课程置换",
     "原专业已修读并通过、与转入专业培养方案课程名称内容相同或相近且难度相当的课程，可申请课程置换，获得该课程成绩及学分",
     "学生在原专业已修读并通过的课程，与转入专业培养方案中的课程名称、内容相同或相近，难度相当，可申请课程置换，获得该课程成绩及学分"),
    ("转入后·无对应课程",
     "无对应课程的，可申请学分兑换认定为通识选修课中的自由选修课程学分或通识拓展课学分，并应在规定时间内完成课程置换及学分认定",
     "无对应课程的，可申请学分兑换认定为通识选修课中的自由选修课程学分或通识拓展课学分。转专业学生应在规定时间内完成课程置换及学分认定，接收学院应及时确认培养方案变更情况。"),
    ("转入后·培养方案",
     "转专业后须执行转入专业对应年级的培养方案，完成规定的全部课程并取得学分，经审核达到毕业要求才能毕业",
     "学生转专业后，须执行转入专业对应年级的培养方案。在学校规定的最长有效修业年限内，完成转入专业培养方案规定的全部课程，取得规定的学分，经审核达到毕业要求者方能毕业。"),
    ("转入后·补修冲突",
     "补修必修课程与现有课程时间冲突时，经本人申请、任课老师同意、学校批准，可采用自修方式完成学习",
     "转专业学生补修必修课程时，若遇必修课程间时间冲突，经本人申请、任课老师同意、学校批准后，允许采用自修方式完成学习。"),
]
for i, (when, what, quote) in enumerate(new_steps, start=len(it["steps"])):
    it["steps"].append({"when": when, "what": what, "where": "接收学院"})
    it["evidence"][f"steps.{i}"] = {"src": "zhuanzhuanye-2025", "quote": quote}

PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("已更新", PATH.name, "条目数", len(data["items"]))