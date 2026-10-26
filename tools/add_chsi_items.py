"""学信网条目：在线验证报告（学历/学籍/学位）+ 本人身份核验。

原文全部来自学信网公开页面，来源标注为「学信网（教育部学生服务与素质发展中心）」。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
have = {i["id"] for i in d["items"]}

YZ = "chsi-yanzheng"
BR = "chsi-benren"
XW = "chsi-xuewei"

SRC_YZ = [{"title": "在线验证报告 · 学信网（教育部学生服务与素质发展中心）",
           "url": "https://www.chsi.com.cn/xlcx/bgcx.jsp", "checked": "2026-10-26"}]
SRC_BR = [{"title": "查询本人学籍学历学位信息方法 · 学信网",
           "url": "https://www.chsi.com.cn/xlcx/brcxff.jsp", "checked": "2026-10-26"}]

ITEMS = [
    {
        "id": "chsi-baogao",
        "title": "学信网在线验证报告（学历 / 学籍 / 学位）",
        "aliases": ["在线验证报告", "学历证书电子注册备案表", "学籍在线验证报告", "学位在线验证报告",
                    "学信网报告", "教育部学籍在线验证报告", "备案表"],
        "keywords": ["在线验证报告", "电子注册备案表", "学籍在线验证", "学位在线验证", "验证码"],
        "dept": "学信网（教育部学生服务与素质发展中心）", "channel": ["线上系统"],
        "audience": ["本科生", "研究生", "校友"], "status": "verified", "confidence": "high",
        "materials": [{"name": "本人身份证"}, {"name": "与学籍一致的姓名、手机号"}],
        "steps": [
            {"when": "准备", "what": "注册并登录学信网账号，进入学信档案", "where": "chsi.com.cn → 学信档案"},
            {"when": "申请", "what": "在“在线验证”里申请对应报告：学籍 / 学历 / 学位三类", "where": "在线验证"},
            {"when": "使用", "what": "把报告交给对方，对方用 16 位在线验证码在学信网核验真伪", "where": "验证真伪页"},
        ],
        "fee": "免费",
        "location": "学信网（线上办理）",
        "hours": None,
        "duration": None,
        "window": "自 2018 年 1 月 1 日起免费申请",
        "pitfalls": [
            "三类报告不是一回事：学籍报告证明在读，学历备案表证明已毕业，学位报告证明学位",
            "2019 年 3 月 15 日起新申请的报告，在线验证码是 16 位",
            "2025 年 3 月 27 日起启用新版《教育部学籍在线验证报告》，旧版样式已变",
        ],
        "slots": [{"key": "kind", "ask": "你要哪一类报告？", "required": True,
                   "options": ["学籍在线验证报告（在读）", "学历证书电子注册备案表（已毕业）", "学位在线验证报告"],
                   "decides": ["steps"], "why": "三类报告对应三种状态，用人单位要的往往只是其中一种"}],
        "draft": None,
        "source": SRC_YZ,
        "evidence": {
            "steps.0": {"src": YZ, "quote": "注册学信网账号，登录学信档案"},
            "steps.2": {"src": YZ, "quote": "2019年3月15日起，新申请的《教育部学籍在线验证报告》及《教育部学历证书电子注册备案表》的在线验证码升级为16位"},
            "fee": {"src": YZ, "quote": "自2018年1月1日起，学信网将对《教育部学籍在线验证报告》及《教育部学历证书电子注册备案表》提供免费申请服务"},
            "window": {"src": YZ, "quote": "自2018年1月1日起"},
            "pitfalls.0": {"src": YZ, "quote": "1.《教育部学籍在线验证报告》（含中文版和翻译件（英文））"},
            "pitfalls.2": {"src": YZ, "quote": "2025年3月27日起，启用新版《教育部学籍在线验证报告》"},
            "materials.1": {"src": BR, "quote": "（凭身份证、姓名、手机号）"},
        },
        "advisory": [
            "求职、考研复试、留学常要的是「学历证书电子注册备案表」或「学籍在线验证报告」，先问对方要哪一种再申请",
            "报告有有效期，过期可在线延长，不必重新申请",
        ],
    },
    {
        "id": "chsi-heshi",
        "title": "学信档案本人身份核验（实人核验）",
        "aliases": ["学信网核验", "实人核验", "学信档案登录不了", "身份证核验", "学信网查不到学籍"],
        "keywords": ["实人核验", "身份核验", "学信档案", "查不到学籍", "核验失败"],
        "dept": "学信网（教育部学生服务与素质发展中心）", "channel": ["线上系统"],
        "audience": ["本科生", "研究生", "校友"], "status": "verified", "confidence": "high",
        "materials": [{"name": "本人身份证"}, {"name": "本人姓名与手机号"}, {"name": "身份证照片（走上传核验方式时）"}],
        "steps": [
            {"when": "方式 1", "what": "用学信网 App 做实人核验", "where": "学信网 App"},
            {"when": "方式 2", "what": "用支付宝做实人核验", "where": "支付宝"},
            {"when": "方式 3", "what": "上传本人身份证照片申请实人核验（工作日 9:00–17:00）", "where": "学信网"},
            {"when": "方式 4", "what": "输入高等教育的学业信息进行核验", "where": "学信网"},
        ],
        "fee": None, "location": "学信网（线上）", "hours": "上传身份证方式：工作日 9:00-17:00",
        "duration": None, "window": None,
        "pitfalls": ["核验不通过时，客服电话 010-67410388，邮箱 kefu@chsi.com.cn", "身份证照片核验只在工作日 9:00-17:00 处理"],
        "slots": [],
        "draft": None,
        "source": SRC_BR,
        "evidence": {
            "steps.0": {"src": BR, "quote": "方式 1：使用学信网App进行实人核验"},
            "steps.1": {"src": BR, "quote": "方式 2：使用支付宝进行实人核验"},
            "steps.2": {"src": BR, "quote": "方式 3：上传本人身份证相关照片申请实人核验（工作日9:00-17:00；客服电话010-67410388）"},
            "steps.3": {"src": BR, "quote": "方式 4：通过输入高等教育的学业信息进行核验"},
            "materials.0": {"src": BR, "quote": "（凭身份证、姓名、手机号）"},
        },
        "advisory": ["查不到学籍通常是身份核验没过或姓名/证件号与学籍库不一致，先试学业信息核验方式"],
    },
]

added = 0
for it in ITEMS:
    if it["id"] in have:
        continue
    d["items"].append(it)
    added += 1
d["updated"] = "2026-10-26"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"新增 {added} 条学信网条目，共 {len(d['items'])} 条")
