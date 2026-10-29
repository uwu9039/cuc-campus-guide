"""按业务板块自查：能不能答 / 有没有预置问法 / 有没有原文。

用法：python tools/selfcheck.py
输出：selfcheck.md + 终端汇总
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")

# (板块, [(主题, [匹配关键词...])])
BOARDS: list[tuple[str, list[tuple[str, list[str]]]]] = [
    ("一、本科教务", [
        ("选课规则/时间/退课/重修选课", ["选课", "退课", "重修"]),
        ("学籍异动（休学/复学/转专业/退学）", ["休学", "复学", "转专业", "退学", "保留学籍"]),
        ("成绩记载/绩点/复核", ["成绩", "绩点", "复核", "成绩单"]),
        ("考试安排/考场纪律/违纪", ["考试", "违纪", "考场"]),
        ("重考/缓考报名", ["重考", "缓考"]),
        ("在读证明", ["在读证明"]),
        ("修学指南/本科生院服务清单", ["修学指南", "服务清单", "本科生院"]),
    ]),
    ("二、研究生", [
        ("研究生学籍", ["研究生学籍"]),
        ("研究生入学须知", ["研究生入学", "入学须知"]),
        ("博士招生/初试", ["博士", "招生简章"]),
        ("研究生院服务事项", ["研究生院"]),
    ]),
    ("三、新生入学", [
        ("报到流程/迎新", ["报到", "迎新", "新生"]),
        ("党团组织关系转接", ["团组织关系", "党组织关系"]),
        ("信息化服务开通", ["信息化服务", "账号开通"]),
    ]),
    ("四、信息化服务", [
        ("统一身份认证/申诉/密码", ["统一身份", "账号申诉", "密码"]),
        ("校园网", ["校园网", "网络"]),
        ("WPS+365", ["WPS"]),
        ("高性能计算", ["高性能"]),
        ("融合门户各部门事项", ["融合门户"]),
    ]),
    ("五、吃住行生活", [
        ("学生公寓/调换/退宿", ["公寓", "退宿", "调宿"]),
        ("食堂/饮食服务/投诉", ["食堂", "饮食", "服务监管"]),
        ("快递服务中心", ["快递"]),
        ("教室使用", ["教室"]),
        ("校园管理/家属区", ["校园管理", "家属区"]),
    ]),
    ("六、场馆与设备", [
        ("体育场馆/预约", ["体育场馆", "场馆预约"]),
        ("公共实践场馆", ["实践场馆"]),
        ("设备共享借用", ["设备共享", "设备借用"]),
    ]),
    ("七、医疗", [
        ("门急诊时间/科室", ["门急诊", "校医院"]),
        ("公费医疗/报销", ["公费医疗", "报销"]),
    ]),
    ("八、安全与户籍", [
        ("户籍常见问题", ["户籍"]),
        ("无犯罪记录证明/政审", ["无犯罪记录", "政审"]),
        ("预约入校", ["预约入校", "入校"]),
    ]),
    ("九、财务", [
        ("报销/资金支付/票据", ["报销", "资金支付", "票据"]),
        ("科研经费/收入分配/捐赠", ["科研项目经费", "收入分配", "捐赠配比"]),
        ("内部控制/财务管理办法", ["内部控制", "财务管理办法"]),
        ("财务处服务事项", ["财务处"]),
    ]),
    ("十、资产与采购", [
        ("国有资产/固定资产/处置", ["国有资产", "固定资产", "资产处置"]),
        ("招标采购/修缮工程", ["招标", "采购", "修缮"]),
        ("国资处业务指南", ["国资处"]),
    ]),
    ("十一、老师与职工", [
        ("退休/困难补助/处分/访问学者", ["退休", "困难补助", "教职工处分", "访问学者"]),
        ("教职工政审/入职材料", ["政审"]),
        ("因公出国（境）", ["因公出国"]),
        ("教师手册/课程质量评价", ["教师手册", "课程质量评价"]),
    ]),
    ("十二、党建与团学", [
        ("推优入党/发展党员/党员教育", ["推优", "发展党员", "党员教育"]),
        ("组织员队伍", ["组织员"]),
        ("发展团员/团组织转接", ["发展团员", "团组织关系"]),
    ]),
    ("十三、科研与实验室", [
        ("科研机构/国际合作项目", ["科研机构", "国际合作科研"]),
        ("基本科研业务费", ["基本科研业务费"]),
        ("实验室工作管理办法", ["实验室"]),
    ]),
    ("十四、学校概况与办公", [
        ("学校简介/章程/基础数据/十四五", ["学校简介", "章程", "十四五"]),
        ("部门职责/分类汇总", ["部门职责", "部门分类"]),
        ("印章/OA/签报/档案馆/法治", ["印章", "OA", "签报", "档案馆", "法治"]),
    ]),
    ("十五、培训", [
        ("非学历教育项目", ["非学历教育"]),
    ]),
]


def load_all() -> tuple[list[dict], list[str], list[str]]:
    items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]
    presets = json.loads((ROOT / "presets.json").read_text(encoding="utf-8"))
    preset_qs = [p["q"] for g in presets["groups"] for p in g["items"]] if isinstance(presets["groups"][0]["items"][0], dict) else [q for g in presets["groups"] for q in g["items"]]
    corpus_titles = []
    for fname in ("index.json", "crawl-index.json", "cdp-index.json", "wechat-index.json",
                  "chsi-index.json", "moe-index.json", "national-index.json",
                  "extra-index.json", "huibian-index.json"):
        f = ROOT / "sources" / fname
        if f.exists():
            corpus_titles += [m.get("title", "") for m in json.loads(f.read_text(encoding="utf-8")).values()]
    return items, preset_qs, corpus_titles


def hit(texts: list[str], keys: list[str]) -> str | None:
    for t in texts:
        if any(k in (t or "") for k in keys):
            return t
    return None


def main() -> None:
    items, presets, corpus = load_all()
    item_texts = []
    for it in items:
        item_texts.append(" ".join([it.get("title", "")] + list(it.get("aliases") or []) + list(it.get("keywords") or [])))

    rows = []
    total = can_answer = has_data = 0
    for board, topics in BOARDS:
        for topic, keys in topics:
            total += 1
            it = hit(item_texts, keys)
            doc = hit(corpus, keys)
            q = hit(presets, keys)
            status = "✅ 能答" if it else ("⚠️ 有资料无条目" if doc else "❌ 无资料")
            if it:
                can_answer += 1
            if doc:
                has_data += 1
            rows.append((board, topic, status, bool(it), bool(doc), bool(q)))

    print(f"板块 {len(BOARDS)} 个，主题 {total} 项")
    print(f"能直接答：{can_answer}/{total}　有原文：{has_data}/{total}")
    for board, topics in BOARDS:
        sub = [r for r in rows if r[0] == board]
        ok = sum(1 for r in sub if r[3])
        print(f"  {board:<14}{ok}/{len(sub)} 可答")

    lines = ["# 自查：15 个板块能不能答", "",
             f"- 主题 {total} 项：**能直接答 {can_answer}**、有原文 {has_data}",
             "", "| 板块 | 主题 | 能答 | 有原文 | 有预置问法 |", "|---|---|---|---|---|"]
    for board, topic, status, it, doc, q in rows:
        lines.append(f"| {board} | {topic} | {'✅' if it else '—'} | {'✅' if doc else '—'} | {'✅' if q else '—'} |")
    (ROOT / "selfcheck.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n已写入 selfcheck.md")


if __name__ == "__main__":
    main()
