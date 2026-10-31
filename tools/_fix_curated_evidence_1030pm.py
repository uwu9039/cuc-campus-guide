"""修正 10 条新条目的证据：地点/材料补官方原句，挂错来源的改回原文文件。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"


def ev(src: str, quote: str) -> dict:
    return {"src": src, "quote": quote}


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = {it["id"]: it for it in data["items"]}

    def item(i):
        return items[i]

    # 通识课：地点就是选课系统
    item("tongshi-ke")["evidence"]["location"] = ev(
        "d02e30b4", "学生在每学期规定时间内自行登录我校教务综合管理系统选课")

    # 新生资格复查
    it = item("xinsheng-zige-fucha")
    it["evidence"]["location"] = ev(
        "0ea1c4c5", "新生入学资格复查工作由招生处牵头")
    it["evidence"]["materials.0"] = ev(
        "0ea1c4c5", "负责核查新生的录取通知书、身份证等材料原件")

    # 研究生奖助：地点改为基层单位评审委员会；补材料与两条步骤引文
    it = item("yjs-jiangzhu")
    it["location"] = "各基层单位研究生国家奖学金评审委员会"
    it["evidence"]["location"] = ev(
        "61f74587", "成立研究生国家奖学金评审委员会")
    it["evidence"]["materials.0"] = ev(
        "61f74587", "符合条件的研究生应如实填写《研究生国家奖学金申请表》等申请材料")
    it["evidence"]["steps.2"] = ev(
        "61f74587", "按照评审实施细则择优选出拟获奖研究生")
    it["evidence"]["steps.4"] = {"sources": [
        ev("61f74587", "（一）未按时进行学籍注册；（二）违反校纪校规，受到警告（含）以上处分且处分未被"),
        ev("61f74587", "解除；（三）中期考核未通过；（四）当年档案未到校或不完整"),
    ]}

    # 校园卡退款：地点补引文；没有官方窗口时间，去掉 hours
    it = item("xyk-tuikuan")
    it["evidence"]["location"] = ev(
        "48e1da04", "同学老师请前往艺术与传播大楼1层大厅办理")
    it.pop("hours", None)
    it["evidence"].pop("hours", None)

    # 体育场馆：地点与开放时间补引文
    it = item("tiyu-changguan-yuyue")
    it["location"] = "大学生活动中心 / 手球馆（教育服务中心管理）"
    it["evidence"]["location"] = {"sources": [
        ev("f1e7a343", "大学生活动中心、手球馆的开放时间为15:00-21:00"),
        ev("f1e7a343", "教育服务中心所辖场馆中没有排练室/舞蹈室"),
    ]}
    it["evidence"]["hours"] = ev(
        "f1e7a343", "大学生活动中心、手球馆的开放时间为15:00-21:00")

    # 请假：审批链、材料补引文；审批表没有官方全称，用原文叫法
    it = item("xueji-qingjia")
    it["location"] = "班主任 / 学院 / 本科生院"
    it["evidence"]["location"] = ev(
        "xueji-2025", "请假三天以内，由班主任审批，辅导员、教务员备案；三天以上，还须报学院主管学生工作领导、主管教学领导同意；一学期内请假累计超过一个月的，应报本科生院备案")
    it["materials"][0]["name"] = "请假审批表"
    it["evidence"]["materials.0"] = ev("xueji-2025", "学生请假需填写请假审批表")
    it["evidence"]["materials.1"] = ev("xueji-2025", "学生因病请假应有校医院证明")

    # 学业警示：审批部门与退学警示程序
    it = item("xueye-jingshi")
    it["evidence"]["location"] = ev(
        "xueji-2025", "学业留级应由本人提出申请，经学院主管教学领导同意，本科生院和学校主管本科教学领导批准后方可办理")
    it["evidence"]["steps.4"] = ev(
        "fb6cf13c", "教务处依据成绩管理办法，筛选出达到学业警示退学条件的学生名单并与学院核实")

    # 学籍信息变更：地点与四项材料
    it = item("xueji-xinxi-biangang")
    it["location"] = "本科生院（教务处）"
    it["evidence"]["location"] = ev("fb6cf13c", "教务处为其进行学籍信息变更")
    for i, q in enumerate(["信息变更申请", "家长知情同意书", "身份证、户口簿",
                           "公安机关出具的身份信息修改或变更证明"]):
        it["evidence"][f"materials.{i}"] = ev("fb6cf13c", q)

    # 毕业论文：学院审定、教务处备案
    item("benke-biye-lunwen")["evidence"]["location"] = ev(
        "att-fd2adff7d3", "选题结果报经学院审定，报教务处备案")

    # 团员评议：地点与两条推优步骤的原文
    it = item("tuan-yuan-pingyi")
    it["location"] = "团支部 / 分团委（团总支）"
    it["evidence"]["location"] = ev(
        "9fba5c0633", "党总支、党支部要积极指导分团委（团总支）、团支部认真做好推荐优秀团员做党的发展对象的工作")
    it["evidence"]["steps.4"] = ev(
        "9fba5c0633", "是共青团员的要经过团支部“推优”，经支委会（不设支委会的支部大会）讨论，可确定为发展对象")
    it["evidence"]["steps.5"] = ev(
        "9fba5c0633", "召开团员大会，团支部委员会介绍申请入党的团员情况，团员进行民主评议，提出推荐对象；2、团支部委员会在推荐对象进行认真考察的基础上，讨论确定推荐名单，填写推荐对象审核表，报上一级团组织审定")
    it["steps"][5]["what"] = ("召开团员大会，团支部委员会介绍申请入党的团员情况，团员进行民主评议，提出推荐对象；"
                              "团支部委员会在认真考察的基础上讨论确定推荐名单，填写推荐对象审核表，报上一级团组织审定")

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已修正 10 条证据，条目数", len(data["items"]))


if __name__ == "__main__":
    main()