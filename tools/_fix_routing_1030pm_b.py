"""按 206 题评测结果补别名、排除词和两条缺失步骤。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"


def add(lst: list, *vals: str) -> None:
    for v in vals:
        if v not in lst:
            lst.append(v)


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    by = {it["id"]: it for it in data["items"]}

    def aliases(i, *vals):
        it = by[i]
        it.setdefault("aliases", [])
        add(it["aliases"], *vals)

    def keywords(i, *vals):
        it = by[i]
        it.setdefault("keywords", [])
        add(it["keywords"], *vals)

    def exclude(i, *vals):
        it = by[i]
        it.setdefault("exclude", [])
        add(it["exclude"], *vals)

    aliases("jiaoshi-jieyong", "公共教室", "公共教室借用", "借用公共教室")
    aliases("lib-jieyue", "自助借还机", "借还机", "刷卡借书", "自助还书")
    aliases("lib-xiaoyou-rg", "校友能借书吗", "校友能用图书馆吗", "校友可以借书吗")
    by["xyy-menzhen-shijian"]["keywords"] = [
        k for k in by["xyy-menzhen-shijian"]["keywords"] if k != "校医院"]
    keywords("xyy-gongfei", "转诊单")
    aliases("xueji-huankao", "考试请假", "病假考试", "考试病了")
    exclude("zhuanzhuanye", "研究生", "硕士", "博士", "研一", "研二", "研三")
    keywords("shijian-changguan-yuyue", "演播馆", "音乐厅", "放映厅", "实践场馆")
    keywords("baogaoting-yuyue", "报告厅", "礼堂", "讲堂")
    aliases("rule-hbaab1311592", "研究生中期考核")
    keywords("rule-hbaab1311592", "中期考核", "学位论文中期考核")
    exclude("benke-biye-lunwen", "研究生", "硕士", "博士", "学位论文")

    # 缴费：票据查询、换绑银行卡
    it = by["xinsheng-jiaofei"]
    aliases("xinsheng-jiaofei", "电子票据", "缴费票据", "发票下载", "票据查询",
            "银行卡绑定", "换绑银行卡")
    keywords("xinsheng-jiaofei", "票据", "电子票据", "银行卡")
    steps = it["steps"]
    steps.append({"when": "票据查询",
                  "what": "缴费结束 5 个工作日后，学校统一开具中央非税收入电子票据；登录「校园统一支付平台」，点击【交易查询】-【已缴费信息】查询并下载票据",
                  "where": "校园统一支付平台"})
    steps.append({"when": "换绑银行卡",
                  "what": "在校生更换绑定银行卡，可在「校园统一支付平台」点击【个人信息】-【银行卡修改】，输入新卡号后修改；也可在中传 App 内操作",
                  "where": "校园统一支付平台 / 中传 App"})
    ev = it["evidence"]
    ev[f"steps.{len(steps) - 2}"] = {
        "src": "46e2780a",
        "quote": "学校将在缴费结束5个工作日后统一开具中央非税收入电子票据"}
    ev[f"steps.{len(steps) - 1}"] = {
        "src": "46e2780a",
        "quote": "点击【个人信息】-【银行卡修改】，在新卡号处输入需绑定的银行卡号，点击修改"}

    # 校友：电子校友卡申领与权益
    it = by["xy-xiaoyou"]
    aliases("xy-xiaoyou", "校友卡", "电子校友卡", "校友卡怎么办理", "校友卡有什么用")
    keywords("xy-xiaoyou", "校友卡", "电子校友卡")
    steps = it["steps"]
    steps.append({"when": "校友卡",
                  "what": "通过校友认证审核后，刷新或重新登录中传 APP，进入「i中传」-「校友卡」上传证件照，审核通过后即可查看个人电子校友卡",
                  "where": "中传 APP"})
    steps.append({"when": "校友卡权益",
                  "what": "电子校友卡可免预约参观传媒博物馆、校史馆，购买「梧桐忆品」「中传创品」文创享校友专属优惠，与实体校友卡具有同等使用效力；实体校友卡申领即将开放",
                  "where": "传媒博物馆 / 校史馆 / 文创店"})
    ev = it["evidence"]
    ev[f"steps.{len(steps) - 2}"] = {
        "src": "810b65ec",
        "quote": "在通过校友认证审核后，刷新APP/重新登录账号进入APP，进入“i中传”-“校友卡”页面，上传证件照即可申领校友卡，证件照审核通过后，即可查看个人电子校友卡"}
    ev[f"steps.{len(steps) - 1}"] = {"sources": [
        {"src": "810b65ec",
         "quote": "可免预约参观传媒博物馆、校史馆（团体参观请提前预约）"},
        {"src": "810b65ec",
         "quote": "电子校友卡具有与实体校友卡同等使用效力。实体校友卡的申领即将开放，敬请期待"},
    ]}

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已补充别名/排除词/步骤，条目数", len(data["items"]))


if __name__ == "__main__":
    main()