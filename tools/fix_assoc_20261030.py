"""第二轮联想体检修复：宿舍设施 / 床品 / 快递地址 / 失物招领 / 普通话 / 教资，
并补齐口语问法的别名，去掉楼宇速查里过宽的「食堂」「快递驿站」别名。

只做 upsert / append，不删除任何条目。
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


def build2(iid: str, title: str, aliases: list[str], dept: str,
           steps: list[tuple[str, str, list[dict]]], pitfalls: list[tuple[str, dict]] = (),
           note: str | None = None, kind: str = "service", confidence: str = "high",
           status: str = "verified", audience: list[str] | None = None) -> dict:
    """steps 为 (when, what, 引文列表)，what 是要展示的整理句。"""
    out_steps, evid = [], {}
    for i, (when, what, quotes) in enumerate(steps):
        out_steps.append({"when": when, "what": what})
        evid[f"steps.{i}"] = ev(*quotes)
    out_pf = []
    for i, (text, quote) in enumerate(pitfalls):
        out_pf.append(text)
        evid[f"pitfalls.{i}"] = quote
    return {
        "id": iid, "title": title, "aliases": aliases, "keywords": [], "dept": dept,
        "channel": ["线下"], "audience": audience or ["本科生", "研究生"],
        "status": status, "confidence": confidence, "materials": [],
        "steps": out_steps, "fee": None, "location": None, "hours": None,
        "duration": None, "window": None, "pitfalls": out_pf, "contact": None,
        "slots": [], "draft": None, "answer": None, "kind": kind, "source": [],
        "evidence": evid, "note": note,
    }


# ---------------------------------------------------------------- 新条目

NEW = []

NEW.append(build2(
    "sushe-sheshi", "宿舍设施（空调 / 卫浴 / 阳台 / 直饮水 / 洗衣机 / 床帘 / 查寝）",
    ["宿舍有空调吗", "宿舍能装空调吗", "宿舍空调", "宿舍有没有空调", "宿舍有独立卫浴吗",
     "中蓝有没有独立卫生间", "宿舍有没有独立卫浴", "宿舍是公共卫浴吗", "宿舍有阳台吗",
     "宿舍有直饮水吗", "宿舍饮水机", "宿舍能挂床帘吗", "宿舍查寝吗", "宿舍几人间",
     "几人间", "宿舍是几人间", "宿舍有独卫吗"],
    "后勤保障处（学生公寓服务中心）",
    [
        ("空调", "各学生公寓楼均已安装空调机，供学生免费使用（电费自理），其中中蓝公寓（二期）为中央空调。",
         [q("9bf17365", "各学生公寓楼均已安装空调机， 供学生免费使用（电费自理） ，其中中蓝公寓（二期）为中央空调。")]),
        ("卫浴（梆子井）", "梆子井公寓：1、2、3、6 号楼为公共卫浴，4 号楼每间配独立卫浴。",
         [q("d940cbae", "1.2.3.6号楼配有公共卫浴，4号楼每个房间配有独立卫浴。")]),
        ("卫浴（中蓝）", "中蓝公寓楼内有独立卫生间和浴室；按区域看，A 区、E 区为独立卫浴，F 区为公共卫浴，二期为独立卫浴。",
         [q("9bf17365", "中蓝公寓包括一期（分为 ABCDEF六个区）、二期（高层）为本科生、研究生女生公寓，位于学校西门对面，从校内有专门的过街天桥直达公寓院内，楼内有独立卫生间和浴室。"),
          q("d940cbae", "中蓝F 区（公共卫浴）")]),
        ("卫浴（校内）", "校内公寓：36、37、38、41、43 号楼和 34 号楼西配公共卫生间和公共浴室；34 号楼东、35 号楼、47 号楼房间内有独立卫生间和浴室。",
         [q("9bf17365", "校内 36号楼、37号楼、38号楼、41号楼、43号楼、34号楼西为本科生宿舍，楼内配有公共卫生间和公共浴室； 8号楼（东西两楼）、 7号楼为硕士研究生公寓， 4号楼为博士生公寓，每一层配有公共卫生间和公共浴室； 34号楼东、35号楼、47号楼为博士、硕士研究生公寓，屋内有独立卫生间和浴室。")]),
        ("阳台", "阳台因楼而异：梆子井 2 人间有阳台、4 人间无阳台，1、2、6 号楼 6 人间有阳台（3 号楼 3102、3112 两间无阳台）；校内 47 号楼 01、02、38、39 号房只有小窗、无阳台。",
         [q("d940cbae", "2人间有阳台，4人间无阳台，1.2.6号楼6人间有阳台、3号楼因房间户型不同今年新生 6人间房间3102、3112 无阳台，其余6人间有阳台。"),
          q("d940cbae", "其中01、02、38、39 无阳台小窗户。")]),
        ("直饮水与洗衣机", "梆子井各楼配有直饮机、洗衣机、壁挂式空调。",
         [q("d940cbae", "各楼都配有直饮机、洗衣机，壁挂式空调。")]),
        ("房型", "中蓝 A、E 区为 6 人间（E 区另有 8 人间），F 区为 4 或 6 人间，二期都是 6 人间；校内 47 号楼硕士 4 人间、博士 3 人间，标准四人间约 25 平方米。",
         [q("d940cbae", "中蓝A 区（独立卫浴） 1、房间单号：朝北，双号朝南。6 人间。"),
          q("d940cbae", "中蓝F 区（公共卫浴） 1、房间朝向：东西向。房间人数：4 人间，6 人间。"),
          q("d940cbae", "中蓝二期（独立卫浴） 1、房间朝向：单号朝南，双号朝北。"),
          q("d940cbae", "校内47 号楼： 硕士4 人间，博士三人间。"),
          q("d940cbae", "标准四人间房间面积25 平米左右，特殊3 人间房间面积22 平米左右，八人间房间面积60 平米左右。")]),
        ("床帘与改造", "新生指南说，学校对安床帘没有限制，挪柜子、挪床、挪桌椅等大部分改造形式也没有限制。",
         [q("loc-新生指南2026-水印版-76f3d8", "学校对大部分改造形式没有限制，包括挪柜子、挪床、挪桌椅等，对于安床帘也没有限制。")]),
        ("查寝", "新生指南说，查寝并不严格，但违禁电器仍会被处理，建议注意用电安全。",
         [q("loc-新生指南2026-水印版-76f3d8", "查寝并不严格，很多不让使用的东西只要藏起来就好了，但仍建议同学们妥善保管个人物品，注意用电安全。")]),
    ],
    pitfalls=[("空调免费使用但电费自理；中蓝公寓（二期）为中央空调。",
               q("9bf17365", "各学生公寓楼均已安装空调机， 供学生免费使用（电费自理） ，其中中蓝公寓（二期）为中央空调。"))],
    note="「床帘」「查寝」两条摘自 2026 新生指南（学生经验整理），不是校规原文。",
    confidence="medium",
))

NEW.append(build2(
    "shiwu-zhaoling", "失物招领（丢了东西 / 捡到东西）",
    ["失物招领", "丢东西了", "东西丢了", "丢了东西", "捡到东西", "失物", "招领", "遗失物品"],
    "后勤保障处 / 信息化处",
    [
        ("校园卡", "校园卡丢了：企业微信或中传 APP 点「校园卡」→「遗失卡查询」→「查询」；捡到卡可点「捡到卡登记」，填失主学工号、姓名和你的联系地址、手机号后提交。",
         [q("20240407-c10717a218312", "校园卡丢失时，想要查询自己卡是否已被他人捡到。可以通过中国传媒大学企业微信或中传app，点击“校园卡”，进入“遗失卡查询”界面，寻找失卡界面，点击“查询”，获取相关信息。"),
          q("20240407-c10717a218312", "捡到他人校园卡时，可以通过中国传媒大学企业微信或中传app，点击“校园卡”，进入“遗失卡查询”界面，点击“捡到卡登记”，填写失主学工号、姓名，自己联系地址和手机号等信息，点击“提交”。")]),
        ("其他物品", "后勤微信公众号的「微互动」栏目设有「报失招领」入口，可在那里报失或查看招领信息。",
         [q("2020-12-11-f27445d5", "3.微互动：建言献策、报失招领、电话查询等")]),
    ],
    note="知识库只收录到上面两个入口，没有找到全校统一的失物招领平台说明。",
    confidence="medium", status="partial",
))

NEW.append(build2(
    "putonghua-peixun", "普通话水平测试培训班（2026 立项公示）",
    ["普通话考试", "普通话考试怎么报名", "普通话水平测试", "普通话测试", "普通话培训班", "普通话报名"],
    "教育发展中心 / 培训教育管理处",
    [
        ("项目", "2026 年中国传媒大学普通话水平测试培训班，经培训教育管理处审批通过立项，审批编号 SP20250120。",
         [q("3ada4747f1", "教育发展中心申报的“2026年中国传媒大学普通话水平测试培训班”项目，经培训教育管理处审批通过，现予以立项。"),
          q("3ada4747f1", "审批编号：SP20250120")]),
        ("类型与时间", "项目类型为面向社会招生项目，执行时间 2026 年 1 月 5 日至 2026 年 12 月 31 日。",
         [q("3ada4747f1", "项目类型：面向社会招生项目"),
          q("3ada4747f1", "执行时间：2026.1.5--2026.12.31")]),
        ("公示信息", "该立项公示发布于 2025 年 11 月 24 日；监督及意见建议电话 010-65783573。",
         [q("3ada4747f1", "发布时间：2025-11-24"),
          q("3ada4747f1", "监督及意见建议电话：010-65783573")]),
    ],
    note="这是培训项目的立项公示，不是普通话水平测试的报名入口；测试报名以官方测试机构的通知为准。",
    kind="notice", confidence="high", status="partial",
))

NEW.append(build2(
    "jiaoshi-zige", "教师资格认定（本校在职教师）",
    ["教师资格证", "教师资格证怎么考", "教师资格", "教师资格认定", "高校教师资格"],
    "人事处",
    [
        ("认定对象", "学校根据北京市教育委员会通知，对本校专门从事教学工作、受聘于教师岗位的在职在岗教师进行教师资格认定，认定合格后颁发教师资格证书。",
         [q("17b5a33f", "学校根据北京市教育委员会通知，对本校专门从事教学工作、受聘于教师岗 位的在职在岗教师进行教师资格认定，经认定合格后颁发教师资格证书。")]),
        ("时间与前置条件", "教师资格认定工作每年分春秋两次；教师需参加学校组织的岗前培训并取得北京市高师培训中心颁发的《高等学校教师岗前培训合格证书》方可申请。",
         [q("17b5a33f", "教师资格认定工作每年分春秋两次，教师需参加学校组织的岗前培训并取得北京市高 师培训中心颁发的《高等学校教师岗前培训合格证书》方可申请教师资格认定。")]),
        ("通知渠道", "有关认定工作及具体条件要求，人事处在认定开始前于 OA 平台发布通知。",
         [q("17b5a33f", "有关认定工作及具体条件要求，人事处在认定开始前于 OA平台发布通知。")]),
    ],
    note="认定对象是本校在职在岗教师；在校学生不在本条范围，学生考教师资格证以国家考试通知为准。",
    confidence="medium", status="partial",
))

# ---------------------------------------------------------------- 追加步骤

EXTRA_STEPS = {
    "shitang-canting": [
        ("校外人员", "非基本伙消费权限人员（如校外人员、未用校园卡）在基本伙食堂（北苑食堂、中蓝餐厅、清真餐厅）就餐，会收取 45% 的成本补偿费。",
         [q("48e1da04", "非基本伙消费权限人员在基本伙食堂（北苑食堂、中蓝餐厅、清真餐厅）就餐会收取45%的成本补偿费。")]),
        ("价格", "新生指南提到，中传食堂价格在北京偏高；基本伙尽量用校园卡付钱，否则无法享受餐补，付款时会多收 45% 且无提示。",
         [q("loc-新生指南2026-水印版-76f3d8", "中传的食堂价格在北京也算是偏高的，对比其他学校的食堂还有许多可改进的空间。"),
          q("loc-新生指南2026-水印版-76f3d8", "基本伙尽量用校园卡付钱，否则无法享受餐补，在付款时会多收45%且无提醒。")]),
    ],
    "kuaidi-yizhan": [
        ("校内邮寄地址", "校内邮寄/收件地址：北京市朝阳区定福庄东街 1 号中国传媒大学 XX 学院 / XX 学生公寓 XX 楼（区），XX 收，邮编 100024；收发室在学校南门东侧。",
         [q("20250924-c378a260402", "收发室在学校南门东侧，接收来自邮局的汇款、挂号、挂刷等。邮寄地址格式：北京市朝阳区定福庄东街1号中国传媒大学XX学院/XX学生公寓XX楼（区），XX收邮编：100024")]),
    ],
    "sushe-jiaju": [
        ("中蓝二期床铺", "中蓝二期：3 套上下铺，外框长 200 × 宽 90 × 高 220（厘米），上下铺间距 100，上铺到房顶约 135。",
         [q("d940cbae", "2、房间3 套上下铺，尺寸：外框长200 `*`宽90 `*`高220，上下铺高度：100， 上铺到房顶 高度,135， 床号分布：单上双下。")]),
    ],
    "lib-zixishi": [
        ("中蓝自习室", "中蓝自习室在中蓝一期二层，需要预约时间才可以使用（与立德楼、博学楼空闲教室「无需预约」不同）。",
         [q("d940cbae", "中蓝自习室位置：在中蓝一期二层，需要预约时间才可以使用。")]),
    ],
    "sushe-menjin": [
        ("熄灯", "官方问答只写公寓每天 6:00 开门、24:00 关门，没有单列熄灯时间（寒暑假另行安排）。",
         [q("9bf17365", "学生公寓楼实行封闭管理，每日早6：00开门，24：00关门（寒暑假根据实际情况另行安排）。")]),
    ],
    "xinsheng-junxun": [
        ("床上用品", "军训床上用品：床单自备或到基地自费购买（床 0.9m×1.9m）；被子由基地提供（2m×1.5m），被罩需自备（素色深色系）。",
         [q("loc-附件5-中国传媒大学2025年参训学生应备物资清单-fd6bb2", "被子由基地提供，尺寸为2mx1.5m，被罩颜色为素色深色系"),
          q("loc-附件5-中国传媒大学2025年参训学生应备物资清单-fd6bb2", "床上用品床单（床尺寸0.9m×1.9m，床单颜色为素色深色系）")]),
    ],
}

# ---------------------------------------------------------------- 别名

ADD_ALIASES = {
    "shitang-shijian": ["食堂几点开饭", "几点开饭", "晚上几点没饭", "早饭时间", "午饭时间", "晚饭时间", "食堂几点打烊"],
    "shitang-zhifu": ["食堂能刷微信吗", "食堂能用支付宝吗", "食堂能刷支付宝吗", "食堂能用微信支付吗", "食堂扫码支付"],
    "shitang-wukou": ["食堂多收钱", "多收钱", "多收钱怎么办", "食堂多扣我钱"],
    "shitang-canting": ["食堂贵吗", "食堂贵不贵", "食堂便宜吗", "校外人员能来食堂吃吗", "校外人员能进食堂吗"],
    "lib-jieyue": ["图书馆怎么借书", "怎么借书", "借书流程"],
    "it-mima": ["中传APP怎么登录", "中传APP登录", "中传APP登不上", "中传APP密码忘了"],
    "sushe-xizao": ["宿舍能洗澡吗", "洗澡在哪", "梆子井洗澡在哪", "宿舍热水几点有", "热水几点有", "几点有热水"],
    "sushe-dianqi": ["宿舍可以做饭吗", "宿舍能做饭吗", "宿舍做饭", "宿舍能用电锅吗"],
    "sushe-xiaofang": ["宿舍能抽烟吗", "宿舍可以抽烟吗", "宿舍里能抽烟吗"],
    "hq-goudian": ["宿舍没电了", "宿舍没电", "宿舍电费", "电费怎么交"],
    "xiyi-liangshai": ["洗衣机怎么用", "洗衣机扫码", "洗衣房"],
    "sushe-jiaju": ["中蓝二期床多大", "中蓝宿舍床多大", "床多宽", "宿舍床多宽", "床多长",
                    "学校卖被褥吗", "床上用品要自己买吗", "床上用品怎么买", "被褥", "被子"],
    "kuaidi-yizhan": ["邮寄地址", "收货地址", "快递地址怎么写", "寄件地址", "快递驿站在哪"],
    "xinsheng-junxun": ["军训被子", "军训被子要自己带吗", "军训要带被子吗"],
    "shiwu-zhaoling": ["捡到东西交哪", "捡到东西交给谁"],
}

DROP_ALIASES = {
    # 楼宇速查把「食堂」「快递驿站」当别名，任何带这两个词的问句都被它抢 84 分，
    # 真正该回答的食堂、快递条目反而被压成反问。
    "campus-louming": ["食堂", "快递驿站"],
}

RETITLE = {
    "sushe-jiaju": "宿舍家具与床品（桌子 / 柜子 / 床 / 被子）",
}


def main() -> None:
    p = ROOT / "items.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    by_id = {it["id"]: it for it in data["items"]}
    added_items = 0

    for item in NEW:
        if item["id"] in by_id:
            print(f"已存在，跳过新增：{item['id']}")
            continue
        data["items"].append(item)
        by_id[item["id"]] = item
        added_items += 1

    added_steps = 0
    for iid, steps in EXTRA_STEPS.items():
        it = by_id[iid]
        for when, what, quotes in steps:
            i = len(it["steps"])
            it["steps"].append({"when": when, "what": what})
            it["evidence"][f"steps.{i}"] = ev(*quotes)
            added_steps += 1

    added_aliases = 0
    for iid, aliases in ADD_ALIASES.items():
        it = by_id.get(iid)
        if not it:
            continue
        for a in aliases:
            if a not in it["aliases"]:
                it["aliases"].append(a)
                added_aliases += 1

    dropped = 0
    for iid, aliases in DROP_ALIASES.items():
        it = by_id[iid]
        keep = [a for a in it["aliases"] if a not in aliases]
        dropped += len(it["aliases"]) - len(keep)
        it["aliases"] = keep

    for iid, title in RETITLE.items():
        old = by_id[iid]["title"]
        if old != title:
            if old not in by_id[iid]["aliases"]:
                by_id[iid]["aliases"].append(old)
            by_id[iid]["title"] = title

    data["updated"] = "2026-10-30"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"新增条目 {added_items} 条，追加步骤 {added_steps} 步，补别名 {added_aliases} 个，"
          f"删别名 {dropped} 个，总计 {len(data['items'])}")


if __name__ == "__main__":
    main()
