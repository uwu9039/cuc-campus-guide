"""把图书馆手册「特色阅览区索引图」的 9 条原文分别成条，并加一条总览。

原文：sources/wendao-text/00f4cdcc.txt（中国传媒大学图书馆手册 20241128）
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = "00f4cdcc"
URL = "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=00f4cdcc1f6e43c99b30eb8d0af91c07"
TITLE = "中国传媒大学图书馆手册（20241128）"

BOOKING = {
    "id": "lib-fangjian-yuyue",
    "title": "图书馆研讨间 / 视听间 / 静音舱预约",
    "aliases": ["研讨间预约", "视听间预约", "静音舱预约", "图书馆研讨间怎么预约",
                "研讨间怎么预约", "静音舱怎么预约", "视听间怎么预约",
                "图书馆房间预约", "图书馆空间预约", "研讨间怎么借", "研讨间申请"],
    "keywords": ["研讨间", "视听间", "静音舱", "空间预约"],
    "steps": [
        ("预约入口",
         "可通过图书馆公众号“中传大阅城”或图书馆主页进行预约，读者可以通过关注中国传媒大学企业号，接收预约信息提示。"),
        ("公众号预约",
         "公众号预约：进入中传大阅城公众号，点击下方“大阅城微服务大厅”，进入“空间预约”模块进行预约。"),
        ("网页预约",
         "网页预约：在“图书馆主页—读者服务—空间预约”模块或在直接登录网址：http://rc.cuc.edu.cn，使用校园网账号及密码登录预约。"),
        ("人数要求",
         "研讨间需三人（含）以上才能预约；静音舱分两种类型，一种可容纳1人，一种可容纳2人（需两人预约）。"),
        ("签到",
         "一旦预约生效，请主预约人组织所有预约读者于指定时间使用房间，并完成签到（所有预约读者均至少在研讨间/视听间平板处刷卡一次即为签到）。"),
    ],
    "pitfalls": [
        "必须完成入馆教育系统中的答题闯关，自助开通权限，次日数据同步后方可预约！",
        "研讨间、视听间、静音舱等空间是为学术研究而设，请勿用作个人或集体自习。",
        "国家法定假日当天研讨间不开放。",
    ],
}

AREAS = [
    ("jingyin", "静音阅览区", "二层西侧", "2001-2064",
     "静音阅览区（二层西侧，座位编号 2001-2064）：不可使用电脑及其鼠标、键盘等可能产生电子噪音设备的安静学习区",
     ["静音阅览区在哪", "静音阅览区位置", "静音阅览区规则", "图书馆静音阅览区",
      "静音阅览区能带电脑吗", "静音阅览区可以说话吗"]),
    ("shenzuo", "深度自习区", "五层东南", "Z001-Z200",
     "深度自习区（五层东南，座位编号 Z001-Z200）：单人工位桌 200 个",
     ["深度自习区在哪", "深度自习区位置", "深度自习区座位", "图书馆深度自习区",
      "深度自习区怎么用"]),
    ("waiwen", "外文阅览区", "五层西侧", "5101-5132",
     "外文阅览区（五层西侧，座位编号 5101-5132）：该阅览区为我馆外文原版图书摆放处",
     ["外文阅览区在哪", "外文阅览区位置", "图书馆外文阅览区", "外文阅览区有什么"]),
    ("jiaoshi", "教师阅览区", "六层西北", "6101-6124",
     "教师阅览区（六层西北，座位号 6101-6124）：教师无需预约，直接使用",
     ["教师阅览区在哪", "教师阅览区位置", "教师阅览区需要预约吗", "教师阅览区谁能用",
      "图书馆教师阅览区"]),
    ("shendu", "深度阅览区", "六层东南", "6901-6952",
     "深度阅览区（六层东南，座位号 6901-6952）：此区域内手机及网络信号均被屏蔽",
     ["深度阅览区在哪", "深度阅览区位置", "深度阅览区有信号吗", "图书馆深度阅览区"]),
    ("ziyou", "自由阅读区", "三、四、五层西侧", "",
     "自由阅读区（三、四、五层西侧）：可自由组合的移动桌椅，玻璃白板",
     ["自由阅读区在哪", "自由阅读区位置", "图书馆自由阅读区", "自由阅读区有什么"]),
    ("jingyincang", "静音舱", "二、三、四、五层东侧", "",
     "静音舱（二、三、四、五层东侧）：满足会议研讨、考试、远程面试等需求",
     ["静音舱在哪", "静音舱位置", "图书馆静音舱", "静音舱怎么用"]),
    ("yantaohui", "研讨间", "二、三、四层南侧", "",
     "研讨间（二、三、四层南侧）：满足上课、研讨等需求，其中特设教师专用研讨间（304-305研讨间，最多可容纳 20 人）",
     ["研讨间在哪", "研讨间位置", "图书馆研讨间", "研讨间怎么用"]),
    ("shiting", "视听间", "三、四、五层电梯南侧", "",
     "视听间（三、四、五层电梯南侧）：满足音视频观摩研讨需求",
     ["视听间在哪", "视听间位置", "图书馆视听间", "视听间怎么用"]),
]


def area_item(key: str, name: str, where: str, seats: str, text: str,
              aliases: list[str]) -> dict:
    location = where + (f"（座位编号 {seats}）" if seats else "")
    return {
        "id": f"lib-{key}",
        "title": f"{name}（{where}）",
        "aliases": [name, *aliases],
        "keywords": [name],
        "dept": "图书馆",
        "channel": ["线下"],
        "audience": ["本科生", "研究生", "教职工"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": [{"when": "位置与规则", "what": text, "where": where}],
        "fee": None,
        "location": location,
        "hours": None,
        "duration": None,
        "window": None,
        "pitfalls": [],
        "contact": None,
        "slots": [],
        "draft": None,
        "answer": None,
        "kind": "service",
        # 房间的预约办法在手册另一节，别用「这间房干什么用」占掉预约问法
        "exclude": ["预约"] if name in {"静音舱", "研讨间", "视听间"} else [],
        "source": [{"title": TITLE, "url": URL, "checked": "2026-10-29"}],
        "evidence": {
            "steps.0": {"src": SRC, "quote": text},
            "location": {"src": SRC, "quote": text},
        },
    }


def main() -> None:
    path = ROOT / "items.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["items"]
    by_id = {i["id"]: i for i in items}
    shutil.copy2(path, path.with_suffix(".json.bak-before-library"))

    # 总览：只认「特色阅览区」这类整块问法，不抢各区域自己的问法。
    overview = {
        "id": "lib-tese-yuelan",
        "title": "图书馆特色阅览区（九处空间的位置与规则）",
        "aliases": ["图书馆特色阅览区", "特色阅览区", "特色阅览区有哪些",
                    "图书馆有哪些阅览区", "图书馆特色阅览区在哪",
                    "图书馆特色阅览区介绍", "特色阅览区索引"],
        "keywords": ["特色阅览区"],
        "dept": "图书馆",
        "channel": ["线下"],
        "audience": ["本科生", "研究生", "教职工"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": [
            {"when": name, "what": text, "where": where}
            for _, name, where, _, text, _ in AREAS
        ],
        "fee": None,
        "location": None,
        "hours": None,
        "duration": None,
        "window": None,
        "pitfalls": [],
        "contact": None,
        "slots": [],
        "draft": None,
        "answer": None,
        "kind": "service",
        "source": [{"title": TITLE, "url": URL, "checked": "2026-10-29"}],
        "evidence": {
            f"steps.{n}": {"src": SRC, "quote": text}
            for n, (_, _, _, _, text, _) in enumerate(AREAS)
        },
    }

    added = []
    if "lib-tese-yuelan" not in by_id:
        items.append(overview)
        added.append(overview["id"])
    else:
        idx = items.index(by_id["lib-tese-yuelan"])
        items[idx] = overview

    for key, name, where, seats, text, extra_aliases in AREAS:
        item_id = f"lib-{key}"
        aliases = list(extra_aliases)
        if seats:
            aliases.append(f"{name}座位号")
        item = area_item(key, name, where, seats, text, aliases)
        if item_id not in by_id:
            items.append(item)
            added.append(item_id)
        else:
            items[items.index(by_id[item_id])] = item

    # 「图书馆」是场馆泛词：它让任何图书馆子问题都先落到借阅条目或楼宇速查上。
    jieyue = by_id["lib-jieyue"]
    if "图书馆" in jieyue.get("keywords", []):
        jieyue["keywords"] = [k for k in jieyue["keywords"] if k != "图书馆"]
    louming = by_id["campus-louming"]
    if "图书馆" in louming.get("aliases", []):
        louming["aliases"] = [
            ("图书馆在哪" if a == "图书馆" else a) for a in louming["aliases"]
        ]
        for extra in ("图书馆位置", "图书馆怎么走", "大阅城在哪"):
            if extra not in louming["aliases"]:
                louming["aliases"].append(extra)

    booking = {
        "id": BOOKING["id"],
        "title": BOOKING["title"],
        "aliases": BOOKING["aliases"],
        "keywords": BOOKING["keywords"],
        "dept": "图书馆",
        "channel": ["微信公众号", "线上"],
        "audience": ["本科生", "研究生", "教职工"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": [{"when": when, "what": what} for when, what in BOOKING["steps"]],
        "fee": None,
        "location": None,
        "hours": None,
        "duration": None,
        "window": None,
        "pitfalls": BOOKING["pitfalls"],
        "contact": None,
        "slots": [],
        "draft": None,
        "answer": None,
        "kind": "service",
        "source": [{"title": TITLE, "url": URL, "checked": "2026-10-29"}],
        "evidence": {
            **{f"steps.{n}": {"src": SRC, "quote": what}
               for n, (_, what) in enumerate(BOOKING["steps"])},
            **{f"pitfalls.{n}": {"src": SRC, "quote": what}
               for n, what in enumerate(BOOKING["pitfalls"])},
        },
    }
    if BOOKING["id"] not in by_id:
        items.append(booking)
        added.append(booking["id"])
    else:
        items[items.index(by_id[BOOKING["id"]])] = booking

    # 首轮曾把区域事实放成段落条目；改成人工条目后清掉旧 id，避免两份答案。
    old_ids = {f"pt-lib-{key}" for key, *_ in AREAS}
    items[:] = [i for i in items if i["id"] not in old_ids]

    data["updated"] = "2026-10-29"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("新增/更新：", ", ".join(added))
    print("条目总数：", len(items))


if __name__ == "__main__":
    main()
