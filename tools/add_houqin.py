"""从后勤服务指南建两条：宿舍报修、宿舍购电。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
have = {i["id"] for i in d["items"]}
HQ = "20250924-c378a260402"
HQL = [{"title": "后勤服务指南 · 后勤综合服务网",
        "url": "https://zchq.cuc.edu.cn/2025/0924/c378a260402/page.htm",
        "checked": "2026-10-21"}]

NEW = [
    {
        "id": "hq-baoxiu",
        "title": "宿舍 / 设施报修（后勤）",
        "aliases": ["宿舍报修", "东西坏了", "水管漏水", "门锁坏了", "灯不亮", "物业报修"],
        "keywords": ["报修", "维修", "物业", "坏了", "漏水"],
        "dept": "后勤保障处", "channel": ["线上系统", "报修电话"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [],
        "steps": [
            {"when": "电话", "what": "拨打 24 小时热线 65783000 报修", "where": "电话"},
            {"when": "线上", "what": "关注「中国传媒大学后勤保障处」公众号 →「微服务」→「物业报修」", "where": "微信公众号"},
        ],
        "fee": None, "location": "线上（公众号）/ 电话 65783000", "hours": "电话 24 小时", "duration": None, "window": None,
        "pitfalls": ["公众号微信号是 cuc_houqin，别关注错号"],
        "slots": [],
        "draft": None,
        "source": HQL,
        "evidence": {
            "steps.0": {"src": HQ, "quote": "电话报修：拨打24小时热线65783000"},
            "steps.1": {"src": HQ, "quote": "线上报修：关注“中国传媒大学后勤保障处”公众号，进入“微服务”-“物业报修”"},
            "location": {"src": HQ, "quote": "电话报修：拨打24小时热线65783000"},
            "hours": {"src": HQ, "quote": "拨打24小时热线65783000"},
            "pitfalls.0": {"src": HQ, "quote": "微信号“cuc_houqin”"},
        },
    },
    {
        "id": "hq-goudian",
        "title": "宿舍购电（后勤）",
        "aliases": ["宿舍没电了", "买电", "充值电费", "电费怎么交", "公寓购电"],
        "keywords": ["购电", "电费", "充值", "没电"],
        "dept": "后勤保障处", "channel": ["线上系统", "线下窗口"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [],
        "steps": [
            {"when": "校内 / 中蓝公寓", "what": "公众号「微服务」→「公寓购电」，绑定电表后移动支付；或到艺术与传播大楼一层校园生活服务大厅售电窗口",
             "where": "公众号 / 服务大厅"},
            {"when": "梆子井公寓", "what": "支付宝或微信「生活缴费」→「电费」；或带校园卡到中国农业银行窗口按客户编号购电", "where": "线上 / 农行"},
        ],
        "fee": None, "location": "线上公众号 / 艺术与传播大楼一层校园生活服务大厅售电窗口",
        "hours": None, "duration": None, "window": None,
        "pitfalls": ["校内及中蓝公寓绑定电表的验证码是 000000", "不同公寓楼购电方式不一样，别照搬别人的做法"],
        "slots": [{"key": "dorm", "ask": "你住哪个公寓？", "options": ["校内 / 中蓝公寓", "梆子井公寓"], "required": True,
                   "decides": ["steps"], "why": "两种公寓的购电入口完全不同"}],
        "draft": None,
        "source": HQL,
        "evidence": {
            "steps.0": {"src": HQ, "quote": "关注“中国传媒大学后勤保障处”微信公众号—微服务—公寓购电，绑定电表后通过移动支付直接购买；或到艺术与传播大楼一层校园生活服务大厅售电窗口购电"},
            "steps.1": {"src": HQ, "quote": "梆子井学生公寓宿舍学生购电方式：通过支付宝或微信里的“生活缴费”下的“电费”服务模块"},
            "location": {"src": HQ, "quote": "到艺术与传播大楼一层校园生活服务大厅售电窗口购电"},
            "pitfalls.0": {"src": HQ, "quote": "绑定电表验证码为：000000"},
        },
    },
]

added = 0
for it in NEW:
    if it["id"] in have:
        continue
    d["items"].append(it)
    added += 1
d["updated"] = "2026-10-21"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"新增 {added} 条，累计 {len(d['items'])} 条")
