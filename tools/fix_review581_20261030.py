"""581 题逐条复核后的条目修订：限定语回填、标题式步骤合并、错字与断行修正。

只改回答正文，不改 evidence 引文；删并步骤时同步重排 evidence 下标。
脚本可重复执行，已改过的条目会跳过。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"


def main() -> None:
    data = json.loads(P.read_text(encoding="utf-8"))
    by_id = {it["id"]: it for it in data["items"]}
    changed = []

    def step_text(item: dict, idx: int) -> str:
        s = item["steps"][idx]
        return s.get("what", "") if isinstance(s, dict) else str(s)

    # 校园卡延期：把官方「如果…可以」的条件写回句子，别压成无条件命令
    it = by_id["xyk-yanqi"]
    if not step_text(it, 0).startswith("毕业日期正常的话"):
        it["steps"][0]["what"] = (
            "毕业日期正常的话，带卡到校园生活服务大厅改毕业日期，或打 65783878 / 线上客服修改")
        it["steps"][1]["what"] = (
            "预计毕业信息不正常的话，联系教务处（65773223、65773222）办理延期手续")
        changed.append(it["id"])

    # 校园卡补卡：材料先写钱再写人到场，别把「本人」当物品
    it = by_id["xyk-buka"]
    it["materials"] = [
        {"name": "微信支付，工本费 20 元"},
        {"name": "本人到场，在自助补卡机现场办理"},
    ]
    changed.append(it["id"])

    # 在读证明：分支条件补成「的话」，单独出现时也能看懂
    it = by_id["jwc-zaidu"]
    if "的话" not in step_text(it, 0):
        it["steps"][0]["what"] = "自费出国（境）留学的话，通过可信电子成绩单系统自助申请下载在读证明"
        it["steps"][1]["what"] = (
            "京籍（含学校集体户口）因私短期出国的话，通过可信电子成绩单系统自助申请下载在读证明")
        it["steps"][2]["what"] = "非京籍因私短期出国的话，填四份表格，持表到本科生院办理盖章"
        it["location"] = "本科生院（仅非京籍因私短期出国）"
        changed.append(it["id"])

    # 校园卡充值：中传 APP 与 i·中传 之间补字，避免显示成 APPi·中传
    it = by_id["xyk-chongzhi"]
    if "中传 APP 里的 i·中传" not in step_text(it, 0):
        it["steps"][0]["what"] = (
            "关注中国传媒大学信息门户公众号 → 综合服务 → 校园卡；"
            "也可用中传 APP 里的 i·中传 或企业微信的校园卡模块")
        it["steps"][1]["what"] = "在校园卡界面点击校园卡充值，输入金额，点击充值"
        it["steps"][2]["what"] = (
            "充值实时到账；也可在圈存机 / 自助充值机或校园卡服务中心人工充值")
        changed.append(it["id"])

    # 校园跑：软件名和前后文分开写
    it = by_id["tiyu-xiaoyuanpao"]
    if "闪动校园 APP" not in step_text(it, 0):
        it["steps"][0]["what"] = "中传的阳光长跑在闪动校园 APP 上进行"
        it["steps"][9]["what"] = (
            "闪动校园 APP 存在违规获取过多用户信息和违规使用用户信息的情况，"
            "如果不允许信息获取的话软件会无法运行，所以请注意个人隐私安全")
        changed.append(it["id"])

    # 快递驿站：把「位置」标题行并进正文，去掉半角括号与断词
    it = by_id["kuaidi-yizhan"]
    if not step_text(it, 0).startswith("校内菜鸟驿站位于"):
        it["steps"] = [
            {"when": "校内", "what": "校内菜鸟驿站位于临建1（47号楼东侧，44号楼北侧）",
             "if": {"campus": "校内"}},
            {"when": "梆子井", "what": (
                "梆子井快递收货地址是北京市朝阳区三间房镇中国传媒大学梆子井学生公寓，"
                "菜鸟驿站在梆子井公寓大门西侧"), "if": {"campus": "梆子井"}},
            {"when": "校内邮寄地址", "what": (
                "校内邮寄或收件地址为北京市朝阳区定福庄东街 1 号中国传媒大学 XX 学院 / "
                "XX 学生公寓 XX 楼（区），XX 收，邮编 100024；收发室在学校南门东侧")},
        ]
        ev = it["evidence"]
        ev["steps.0"] = ev.pop("steps.1")
        ev["steps.1"] = ev.pop("steps.2")
        ev["steps.2"] = ev.pop("steps.3")
        changed.append(it["id"])

    # 公共报告厅：范围标题行与名单合并
    it = by_id["baogaoting-yuyue"]
    if not step_text(it, 0).startswith("公共报告厅包括"):
        it["steps"] = [
            {"when": "范围", "what": "公共报告厅包括中传学术中心、中传礼堂、中传讲堂、圆形报告厅"},
            {"when": "注意", "what": "44号楼一层报告厅不属于公共报告厅"},
            {"when": "预约入口", "what": (
                "https://workflow.cuc.edu.cn/reservation/fe/site/special/special?id=36")},
        ]
        ev = it["evidence"]
        ev["steps.0"] = ev.pop("steps.1")
        ev["steps.1"] = ev.pop("steps.2")
        ev["steps.2"] = ev.pop("steps.3")
        changed.append(it["id"])

    # 教室借用：去掉导航标签式的重复开头
    it = by_id["jiaoshi-jieyong"]
    if step_text(it, 0).startswith("教室借用，教室预约。"):
        it["steps"][0]["what"] = "目前仅开放博学楼（48教）、立德楼（1教）的教室预约"
        changed.append(it["id"])

    # 公寓门禁：删掉「熄灯」这条自我说明，官方没有的内容不装成步骤
    it = by_id["sushe-menjin"]
    if len(it["steps"]) > 2 and it["steps"][2].get("when") == "熄灯":
        it["steps"] = it["steps"][:2]
        it["evidence"].pop("steps.2", None)
        changed.append(it["id"])

    # 宿舍家具：去掉步骤里自带的问句、断词和多余空格
    it = by_id["sushe-jiaju"]
    if step_text(it, 1).startswith("中蓝宿舍一期桌子长宽是多少"):
        it["steps"][1]["what"] = (
            "中蓝宿舍一期桌子长宽为 850×550×750 或 650×450×750mm，"
            "公寓家具购置年度和批次不同，具体尺寸也会有不同")
        it["steps"][2]["what"] = (
            "房间内的双层铁床以 2000×900×2200 的为主，衣柜以 500×600×2000 的为主，"
            "电脑桌以 850×550×750 的为主")
        changed.append(it["id"])

    # 校历：网址和后面的中文之间补空格
    it = by_id["xiaoli-2026-2027"]
    if "cuc.edu.cn 常用服务" not in (it.get("location") or ""):
        it["location"] = "教务处网站 jwc.cuc.edu.cn 常用服务 → 校历"
        changed.append(it["id"])

    # 校医院就诊：when 已经写了第几步，what 不再重复
    it = by_id["xyy-jiuzhen"]
    if step_text(it, 0).startswith("第一步"):
        for i, s in enumerate(it["steps"], 1):
            s["what"] = s["what"].replace(f"第{['一','二','三','四','五'][i-1]}步：", "")
            s["what"] = s["what"].rstrip("；。")
        changed.append(it["id"])

    # 国家助学金：补上官方管理办法里的申请与评审步骤
    it = by_id["zxj-guojia-guo"]
    if not any(s.get("when") == "申请方式" for s in it["steps"]):
        it["steps"].extend([
            {"when": "申请方式", "what": (
                "国家助学金按学年申请和评审，符合条件的学生向所在学院提出申请，"
                "填写《中国传媒大学国家助学金申请表》")},
            {"when": "评审流程", "what": (
                "学院依据家庭经济困难程度进行初审，拟定资助等级，汇总盖章后统一上报"
                "学生工作部（处）学生资助中心；学生资助中心审核名单、组织评审，"
                "提出初步名单及档次，报学校学生奖助工作领导小组审批")},
            {"when": "发放", "what": "学校按月将国家助学金发放到受助学生的校园银行卡中"},
        ])
        it["evidence"]["steps.4"] = {"sources": [
            {"src": "att-589cc56b95", "quote": "凡符合资助条件的学生均可向所在学院提出申请"},
            {"src": "att-589cc56b95", "quote": "《中国传媒大学国家助学金申请表》"},
        ]}
        it["evidence"]["steps.5"] = {"sources": [
            {"src": "att-589cc56b95", "quote": "统一上报学生工作部（处）学生资助中心。"},
            {"src": "att-589cc56b95", "quote": "报学校学生奖助工作领导小组审批"},
        ]}
        it["evidence"]["steps.6"] = {
            "src": "att-589cc56b95",
            "quote": "学校按月将国家助学金发放到受助学生的校园银行",
        }
        changed.append(it["id"])

    P.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("changed", len(changed), changed)


if __name__ == "__main__":
    main()
