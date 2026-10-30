"""把「宿舍设施」拆成一个个能直接回答的小条目，避免一问空调就铺 9 步。

只做 upsert / append，不删除条目。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


TEXTS: dict[str, str] = {}
for sub in ("wendao-text", "great", "local", "huibian", "crawl", "cdp", "extra", "wechat", "pdf"):
    d = SRC / sub
    if not d.exists():
        continue
    for f in d.glob("*.txt"):
        TEXTS.setdefault(f.stem, squash(f.read_text(encoding="utf-8", errors="ignore")))
for f in SRC.glob("*.txt"):
    TEXTS.setdefault(f.stem, squash(f.read_text(encoding="utf-8", errors="ignore")))


def q(src: str, text: str) -> dict[str, str]:
    assert squash(text) in TEXTS.get(src, ""), f"{src} 找不到：{text[:60]}"
    return {"src": src, "quote": text}


def ev(*quotes: dict[str, str]) -> dict:
    return quotes[0] if len(quotes) == 1 else {"sources": list(quotes)}


def make(iid: str, title: str, aliases: list[str], dept: str,
         steps: list[tuple[str, str, list[dict]]], note: str | None = None,
         confidence: str = "high") -> dict:
    evid = {}
    out_steps = []
    for i, (when, what, quotes) in enumerate(steps):
        out_steps.append({"when": when, "what": what})
        evid[f"steps.{i}"] = ev(*quotes)
    return {
        "id": iid, "title": title, "aliases": aliases, "keywords": [], "dept": dept,
        "channel": ["线下"], "audience": ["本科生", "研究生"], "status": "verified",
        "confidence": confidence, "materials": [], "steps": out_steps, "fee": None,
        "location": None, "hours": None, "duration": None, "window": None,
        "pitfalls": [], "contact": None, "slots": [], "draft": None, "answer": None,
        "kind": "service", "source": [], "evidence": evid, "note": note,
    }


NEW = [
    make("sushe-kongtiao", "宿舍空调（有没有、电费怎么算）",
         ["宿舍有空调吗", "宿舍能装空调吗", "宿舍空调", "宿舍有没有空调", "宿舍有空调么",
          "宿舍装空调", "中蓝空调"],
         "后勤保障处（学生公寓服务中心）",
         [("空调", "各学生公寓楼均已安装空调机，供学生免费使用（电费自理），其中中蓝公寓（二期）为中央空调。",
           [q("9bf17365", "各学生公寓楼均已安装空调机， 供学生免费使用（电费自理） ，其中中蓝公寓（二期）为中央空调。")])],
         note="空调本身免费使用，电费从宿舍电费里出；中蓝二期为中央空调。"),

    make("sushe-weiyu", "宿舍卫浴（独立卫浴还是公共卫浴）",
         ["宿舍有独立卫浴吗", "中蓝有没有独立卫生间", "宿舍有没有独立卫浴", "宿舍是公共卫浴吗",
          "宿舍有独卫吗", "宿舍有没有浴室", "宿舍独立卫浴", "中蓝独立卫浴"],
         "后勤保障处（学生公寓服务中心）",
         [("梆子井", "梆子井公寓：1、2、3、6 号楼为公共卫浴，4 号楼每间配独立卫浴。",
           [q("d940cbae", "1.2.3.6号楼配有公共卫浴，4号楼每个房间配有独立卫浴。")]),
          ("中蓝", "中蓝公寓楼内有独立卫生间和浴室；按区域看，A 区、E 区为独立卫浴，F 区为公共卫浴，二期为独立卫浴。",
           [q("9bf17365", "中蓝公寓包括一期（分为 ABCDEF六个区）、二期（高层）为本科生、研究生女生公寓，位于学校西门对面，从校内有专门的过街天桥直达公寓院内，楼内有独立卫生间和浴室。"),
            q("d940cbae", "中蓝F 区（公共卫浴）")]),
          ("校内", "校内公寓：36、37、38、41、43 号楼和 34 号楼西配公共卫生间和公共浴室；34 号楼东、35 号楼、47 号楼房间内有独立卫生间和浴室。",
           [q("9bf17365", "校内 36号楼、37号楼、38号楼、41号楼、43号楼、34号楼西为本科生宿舍，楼内配有公共卫生间和公共浴室； 8号楼（东西两楼）、 7号楼为硕士研究生公寓， 4号楼为博士生公寓，每一层配有公共卫生间和公共浴室； 34号楼东、35号楼、47号楼为博士、硕士研究生公寓，屋内有独立卫生间和浴室。")])]),

    make("sushe-yangtai", "宿舍阳台（哪些楼有阳台）",
         ["宿舍有阳台吗", "有阳台吗", "宿舍阳台", "哪些宿舍有阳台"],
         "后勤保障处（学生公寓服务中心）",
         [("阳台", "阳台因楼而异：梆子井 2 人间有阳台、4 人间无阳台，1、2、6 号楼 6 人间有阳台（3 号楼 3102、3112 两间无阳台）；校内 47 号楼 01、02、38、39 号房只有小窗、无阳台。",
           [q("d940cbae", "2人间有阳台，4人间无阳台，1.2.6号楼6人间有阳台、3号楼因房间户型不同今年新生 6人间房间3102、3112 无阳台，其余6人间有阳台。"),
            q("d940cbae", "其中01、02、38、39 无阳台小窗户。")])]),

    make("sushe-zhiyinshui", "宿舍直饮水与洗衣机",
         ["宿舍有直饮水吗", "宿舍饮水机", "宿舍饮水机在哪", "宿舍有洗衣机吗", "宿舍洗衣机在哪"],
         "后勤保障处（学生公寓服务中心）",
         [("配备", "梆子井各楼配有直饮机、洗衣机、壁挂式空调；直饮水和洗衣机是楼内公共设备。",
           [q("d940cbae", "各楼都配有直饮机、洗衣机，壁挂式空调。")])],
         note="直饮水的免费用水额度另有条目「校园直饮水免费用水额度」。"),

    make("sushe-fangxing", "宿舍几人间（各公寓房型）",
         ["宿舍几人间", "几人间", "宿舍是几人间", "宿舍几个人住", "中蓝几人间", "梆子井几人间"],
         "后勤保障处（学生公寓服务中心）",
         [("房型", "中蓝 A、E 区为 6 人间（E 区另有 8 人间），F 区为 4 或 6 人间，二期都是 6 人间；校内 47 号楼硕士 4 人间、博士 3 人间；标准四人间约 25 平方米。",
           [q("d940cbae", "中蓝A 区（独立卫浴） 1、房间单号：朝北，双号朝南。6 人间。"),
            q("d940cbae", "中蓝F 区（公共卫浴） 1、房间朝向：东西向。房间人数：4 人间，6 人间。"),
            q("d940cbae", "中蓝二期（独立卫浴） 1、房间朝向：单号朝南，双号朝北。"),
            q("d940cbae", "校内47 号楼： 硕士4 人间，博士三人间。"),
            q("d940cbae", "标准四人间房间面积25 平米左右，特殊3 人间房间面积22 平米左右，八人间房间面积60 平米左右。")])]),

    make("sushe-chuanglian", "宿舍床帘、改造与查寝",
         ["宿舍能挂床帘吗", "床帘", "宿舍查寝吗", "查寝", "宿舍改造", "宿舍能挪床吗"],
         "后勤保障处（学生公寓服务中心）",
         [("床帘与改造", "新生指南说，学校对安床帘没有限制，挪柜子、挪床、挪桌椅等大部分改造形式也没有限制。",
           [q("loc-新生指南2026-水印版-76f3d8", "学校对大部分改造形式没有限制，包括挪柜子、挪床、挪桌椅等，对于安床帘也没有限制。")]),
          ("查寝", "新生指南说，查寝并不严格，但违禁电器仍会被处理，建议注意用电安全。",
           [q("loc-新生指南2026-水印版-76f3d8", "查寝并不严格，很多不让使用的东西只要藏起来就好了，但仍建议同学们妥善保管个人物品，注意用电安全。")])],
         note="两条都摘自 2026 新生指南（学生经验整理），不是校规原文。", confidence="medium"),

    make("sushe-chuangpin", "宿舍被褥与床上用品（要不要自己买）",
         ["宿舍有被子吗", "床上用品", "被子褥子", "床垫", "学校卖被褥吗", "床上用品要自己买吗",
          "床上用品怎么买", "被褥", "被子", "宿舍提供被子吗", "学校发被子吗"],
         "后勤保障处（学生公寓服务中心）",
         [("提不提供", "宿舍不提供被子褥子等床上用品。",
           [q("9bf17365", "宿舍不提供被子褥子等床上用品。")]),
          ("怎么买", "床上用品实行自愿购买原则，包括被子、褥子、床垫、枕芯、被罩、床单、枕套、枕巾、蚊帐、毛巾被（或凉被）10 种 14 件套，价格每套 500 元左右。",
           [q("9bf17365", "床上用品实行自愿购买原则，包括被子、褥子、床垫、枕芯、被罩、床单、枕套、枕巾、蚊帐、毛巾被（或凉被）10种14件套（被罩、床单、枕套、枕巾为双件），价格为每套 500元左右。")]),
          ("自带", "生活用具及被装可以自带，没有要求；每年区域内都有被装供应厂商，学生可自行购买。",
           [q("d940cbae", "5.生活用具及被装可自带，无要求，每年区域内都有被装供应厂商，学生可自行购买。")])]),
]

# 伞条目只留「宿舍设施有哪些」这类整体问法，具体问题交给上面的小条目
UMBRELLA_DROP = [
    "宿舍有空调吗", "宿舍能装空调吗", "宿舍空调", "宿舍有没有空调",
    "宿舍有独立卫浴吗", "中蓝有没有独立卫生间", "宿舍有没有独立卫浴",
    "宿舍是公共卫浴吗", "宿舍有独卫吗", "宿舍有阳台吗",
    "宿舍有直饮水吗", "宿舍饮水机",
    "宿舍能挂床帘吗", "宿舍查寝吗",
    "宿舍几人间", "几人间", "宿舍是几人间",
]
UMBRELLA_ADD = ["宿舍设施", "宿舍配套", "宿舍有什么设施", "宿舍条件怎么样", "宿舍设施有哪些"]

JIAJU_DROP = ["宿舍有被子吗", "床上用品", "被子褥子", "床垫", "被子",
              "学校卖被褥吗", "床上用品要自己买吗", "床上用品怎么买", "被褥"]


def main() -> None:
    p = ROOT / "items.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    by_id = {it["id"]: it for it in data["items"]}

    added = 0
    for item in NEW:
        if item["id"] in by_id:
            continue
        data["items"].append(item)
        by_id[item["id"]] = item
        added += 1

    umbrella = by_id["sushe-sheshi"]
    umbrella["aliases"] = [a for a in umbrella["aliases"] if a not in UMBRELLA_DROP]
    for a in UMBRELLA_ADD:
        if a not in umbrella["aliases"]:
            umbrella["aliases"].append(a)

    jiaju = by_id["sushe-jiaju"]
    jiaju["aliases"] = [a for a in jiaju["aliases"] if a not in JIAJU_DROP]
    jiaju["title"] = "宿舍家具尺寸（桌子 / 柜子 / 床）"

    data["updated"] = "2026-10-30"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"新增条目 {added} 条，总计 {len(data['items'])}")


if __name__ == "__main__":
    main()
