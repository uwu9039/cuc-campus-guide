"""把已采集的官方页面批量转成条目（第二批）。所有事实都必须带原文引文。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
have = {i["id"] for i in d["items"]}


def ev(src, *quotes):
    rows = [{"src": src, "quote": q} for q in quotes]
    return rows[0] if len(rows) == 1 else {"sources": rows}


NEW = [
    {
        "id": "xyk-guashi", "title": "校园卡挂失 / 解挂",
        "aliases": ["挂失", "解挂", "卡丢了要挂失", "卡找回来了", "卡被捡到了"],
        "keywords": ["挂失", "解挂", "冻结"],
        "dept": "信息化处", "channel": ["线上系统", "线下窗口"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "本人有效身份证件（窗口解挂时）"}],
        "steps": [
            {"when": "挂失", "what": "通过校园卡系统入口点击「卡片挂失」", "where": "线上"},
            {"when": "解挂", "what": "本人持有效身份证件到校园卡服务中心办理，或在校园卡中点「卡片解挂」自行解挂",
             "where": "艺术与传播大楼1层 校园生活服务大厅"},
        ],
        "fee": None, "location": "艺术与传播大楼1层 校园生活服务大厅（窗口解挂）",
        "hours": None, "duration": None, "window": None,
        "pitfalls": ["校园卡服务中心不受理无证解除挂失，也不能代办解挂"],
        "slots": [{"key": "act", "ask": "是要挂失，还是卡找回来了要解挂？", "options": ["挂失", "解挂"],
                   "required": True, "decides": ["steps", "materials"],
                   "why": "挂失线上就能做；解挂要本人带证件，或自己在卡里点解挂"}],
        "draft": None,
        "source": [{"title": "校园卡使用指南 · 信息化处",
                    "url": "https://its.cuc.edu.cn/2022/1027/c12936a200464/page.htm", "checked": "2026-10-20"}],
        "evidence": {
            "steps.0": ev("20221027-c12936a200464", "校园卡遗失应及时挂失。本人可通过校园卡系统入口进入。点击“卡片挂失”按照系统流程进行挂失"),
            "steps.1": ev("20221027-c12936a200464", "需本人持有效身份证件到校园卡服务中心（艺术与传播大楼1层校园生活服务大厅）办理或本人在校园卡中，通过点击“卡片解挂”按钮自行解挂"),
            "materials.0": ev("20221027-c12936a200464", "需本人持有效身份证件到校园卡服务中心"),
            "location": ev("20221027-c12936a200464", "校园卡服务中心（艺术与传播大楼1层校园生活服务大厅）"),
            "pitfalls.0": ev("20221027-c12936a200464", "校园卡服务中心不受理无证解除挂失和代办解除挂失业务"),
        },
    },
    {
        "id": "xyk-yishi", "title": "遗失卡查询 / 捡到卡登记",
        "aliases": ["卡丢了怎么找", "捡到卡怎么办", "遗失卡查询", "捡到卡登记"],
        "keywords": ["遗失卡", "捡到卡", "找卡"],
        "dept": "信息化处", "channel": ["线上系统"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [],
        "steps": [
            {"when": "丢卡人", "what": "企业微信或中传 APP 点「校园卡」→「遗失卡查询」→「查询」", "where": "线上"},
            {"when": "捡卡人", "what": "点「捡到卡登记」，填失主学工号、姓名、自己的联系地址和手机号后提交", "where": "线上"},
        ],
        "fee": None, "location": "线上：中国传媒大学企业微信 / 中传 APP",
        "hours": None, "duration": None, "window": None,
        "pitfalls": ["这是「找卡 / 登记」通道，不等于挂失；卡确实丢了应先挂失"],
        "slots": [{"key": "role", "ask": "你是丢卡的一方，还是捡到卡的一方？", "options": ["丢卡", "捡到卡"],
                   "required": True, "decides": ["steps"], "why": "入口相同，但两边做的事相反"}],
        "draft": None,
        "source": [{"title": "遗失卡丢失-登记服务 · 信息化处",
                    "url": "https://its.cuc.edu.cn/2024/0407/c10717a218312/page.htm", "checked": "2026-10-20"}],
        "evidence": {
            "steps.0": ev("20240407-c10717a218312", "校园卡丢失时，想要查询自己卡是否已被他人捡到。可以通过中国传媒大学企业微信或中传app，点击“校园卡”，进入“遗失卡查询”界面"),
            "steps.1": ev("20240407-c10717a218312", "点击“捡到卡登记”，填写失主学工号、姓名，自己联系地址和手机号等信息，点击“提交”"),
            "location": ev("20240407-c10717a218312", "可以通过中国传媒大学企业微信或中传app"),
        },
    },
    {
        "id": "xyk-yanqi", "title": "校园卡延期（延期毕业）",
        "aliases": ["延期毕业校园卡", "卡到期了", "学生卡延期", "毕业日期改"],
        "keywords": ["延期", "校园卡有效期", "毕业日期"],
        "dept": "信息化处 / 教务处", "channel": ["线下窗口", "线上系统"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "校园卡（毕业日期正常时现场修改）"}],
        "steps": [
            {"when": "情况 A", "what": "毕业日期正常：带卡到校园生活服务大厅改毕业日期，或打 65783878 / 线上客服修改",
             "where": "艺术与传播大楼1层"},
            {"when": "情况 B", "what": "预计毕业信息不正常：联系教务处（65773223、65773222）办理延期手续", "where": "教务处"},
        ],
        "fee": None, "location": "艺术与传播大楼1层 校园生活服务大厅",
        "hours": None, "duration": None,
        "window": "本科生卡有效期 4 年；研究生 3–5 年，以学制为准",
        "pitfalls": ["预计毕业信息不正常时，改卡没用，得先去教务处办延期手续",
                     "留学生延期联系国际交流与合作处（65779359）"],
        "slots": [{"key": "case", "ask": "你的毕业日期信息是正常的，还是预计要延期？", "options": ["正常", "预计延期"],
                   "required": True, "decides": ["steps"], "why": "两种情况找的部门不一样"}],
        "draft": None,
        "source": [{"title": "学生卡延期指南 · 信息化处",
                    "url": "https://its.cuc.edu.cn/2023/1117/c10285a213870/page.htm", "checked": "2026-10-20"}],
        "evidence": {
            "window": ev("20231117-c10285a213870", "本科生校园卡有效期为4年，研究生（研、博）校园卡有效期为3-5年，以各专业学制年限为准"),
            "steps.0": ev("20231117-c10285a213870", "如果毕业日期正常，可以带上校园卡，到艺术与传播大楼1层校园生活服务大厅进行毕业日期修改；或者可以通过信息化处联系电话（65783878）、线上客服联系修改"),
            "steps.1": ev("20231117-c10285a213870", "如果预计毕业信息不正常请学生联系教务处（联系电话65773223，65773222），办理延期手续等"),
            "location": ev("20231117-c10285a213870", "到艺术与传播大楼1层校园生活服务大厅进行毕业日期修改"),
            "materials.0": ev("20231117-c10285a213870", "可以带上校园卡"),
            "pitfalls.0": ev("20231117-c10285a213870", "如果预计毕业信息不正常请学生联系教务处"),
            "pitfalls.1": ev("20231117-c10285a213870", "留学生可以联系国际交流与合作处（港澳台事物办），联系电话（65779359）"),
        },
    },
    {
        "id": "it-jiaotong", "title": "电子学生交通卡申领",
        "aliases": ["学生公交卡", "交通卡怎么领", "一卡通学生卡", "地铁优惠卡"],
        "keywords": ["交通卡", "公交卡", "一卡通", "地铁"],
        "dept": "信息化处 / 北京市政交通一卡通", "channel": ["线上系统"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "手机 NFC（申领与使用前置）"}],
        "steps": [{"when": "申领", "what": "打开「北京一卡通」App，开启手机 NFC，点首页「高校服务」，按提示在线申领",
                   "where": "北京一卡通 App"}],
        "fee": None, "location": "线上：北京一卡通 App", "hours": None, "duration": None, "window": None,
        "pitfalls": ["不是实体卡，需要手机支持 NFC", "优惠是北京公交 2.5 折，全国 300+ 城市公共交通可用"],
        "slots": [],
        "draft": None,
        "source": [{"title": "学生电子交通卡申领 · 信息化处",
                    "url": "https://its.cuc.edu.cn/2023/1020/c8495a212881/page.htm", "checked": "2026-10-20"}],
        "evidence": {
            "steps.0": ev("20231020-c8495a212881", "打开“北京一卡通”，打开手机NFC设置，点击首页“高校服务”， 按提示操作即可在线申领电子学生卡"),
            "materials.0": ev("20231020-c8495a212881", "打开手机NFC设置"),
            "location": ev("20231020-c8495a212881", "打开“北京一卡通”"),
            "pitfalls.0": ev("20231020-c8495a212881", "可将卡片添加到手机“钱包”APP中设置为默认卡"),
            "pitfalls.1": ev("20231020-c8495a212881", "电子学生交通卡带公交联合标识，可享受北京公交2.5折的优惠"),
        },
    },
    {
        "id": "it-ganzhi", "title": "校园网无感知认证",
        "aliases": ["每次都要输密码", "免认证上网", "无感认证", "wifi老要登录"],
        "keywords": ["无感知", "无感认证", "免认证"],
        "dept": "信息化处", "channel": ["线上系统"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "统一身份认证账号（首次认证用）"}],
        "steps": [{"when": "设置", "what": "先到认证页用统一身份认证联网，再按页面提示开启「无感知认证」",
                   "where": "https://net.cuc.edu.cn"}],
        "fee": None, "location": "线上：https://net.cuc.edu.cn",
        "hours": None, "duration": None, "window": None,
        "pitfalls": ["无感知靠记录终端 MAC 地址实现，需自己主动设置"],
        "slots": [],
        "draft": None,
        "source": [{"title": "无感知认证 · 信息化处",
                    "url": "https://its.cuc.edu.cn/2023/0225/c8477a202334/page.htm", "checked": "2026-10-20"}],
        "evidence": {
            "steps.0": ev("20230225-c8477a202334", "通过认证页面（https://net.cuc.edu.cn）输入统一身份认证账号密码联网"),
            "materials.0": ev("20230225-c8477a202334", "用户终端初次需输入统一身份认证账号密码联网"),
            "location": ev("20230225-c8477a202334", "通过认证页面（https://net.cuc.edu.cn）"),
            "pitfalls.0": ev("20230225-c8477a202334", "“无感知认证”通过在认证系统记录用户终端MAC地址实现，需由用户主动设置"),
        },
    },
    {
        "id": "it-renlian", "title": "自助人脸照片上传（门禁）",
        "aliases": ["人脸识别进不去", "刷脸失败", "照片采集", "门禁录脸"],
        "keywords": ["人脸", "照片采集", "刷脸", "门禁"],
        "dept": "信息化处", "channel": ["线上系统"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "本人人脸照片（JPG，>100KB，纯色背景、正面免冠、无反光）"}],
        "steps": [
            {"when": "途径一", "what": "统一身份认证激活后登录「中传 APP」→「i·中传」→「照片采集入口」", "where": "中传 APP"},
            {"when": "途径二", "what": "进入中国传媒大学企业微信 →「照片采集」", "where": "企业微信"},
        ],
        "fee": None, "location": "线上：中传 APP / 企业微信",
        "hours": None, "duration": None, "window": None,
        "pitfalls": ["照片要求硬：>100KB、纯色背景、正面免冠、无遮挡无反光、人脸占 2/3 以上、JPG、不能美颜"],
        "slots": [],
        "draft": None,
        "source": [{"title": "自助人脸照片上传 · 信息化处",
                    "url": "https://its.cuc.edu.cn/2023/1013/c8477a212636/page.htm", "checked": "2026-10-20"}],
        "evidence": {
            "steps.0": ev("20231013-c8477a212636", "①途径一：统一身份认证账号激活后，使用该账号登录“中传APP”，进入“i·中传”版块，点击“照片采集入口”录入人脸照片"),
            "steps.1": ev("20231013-c8477a212636", "②途径二：进入中国传媒大学企业微信后，点击“照片采集”录入人脸照片"),
            "materials.0": ev("20231013-c8477a212636", "上传照片要求：大于100KB，简单背景（最好纯色），正面免冠，无遮挡，无反光，人脸占比至少2/3以上，JPG格式，不要使用美颜和滤镜功能"),
            "pitfalls.0": ev("20231013-c8477a212636", "上传照片要求：大于100KB，简单背景（最好纯色），正面免冠，无遮挡，无反光，人脸占比至少2/3以上"),
        },
    },
    {
        "id": "it-shensu", "title": "统一身份认证账号申诉",
        "aliases": ["收不到验证码", "换了手机号", "账号申诉", "身份信息有误"],
        "keywords": ["申诉", "验证码", "换手机号"],
        "dept": "信息化处", "channel": ["线上系统"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [],
        "steps": [{"when": "入口", "what": "中传 APP →「我的」→「登录」→ 输入账号 → 点「账号申诉」", "where": "中传 APP"}],
        "fee": None, "location": "线上：中传 APP", "hours": None, "duration": None, "window": None,
        "pitfalls": ["手机号收不到验证码、手机号变更、身份信息有误，都走「账号申诉」，不必跑窗口"],
        "slots": [],
        "draft": None,
        "source": [{"title": "统一身份认证之账号申诉 · 信息化处",
                    "url": "https://its.cuc.edu.cn/2023/0516/c8508a208993/page.htm", "checked": "2026-10-20"}],
        "evidence": {
            "steps.0": ev("20230516-c8508a208993", "4.点击“账号申诉”"),
            "pitfalls.0": ev("20230516-c8508a208993", "如果您的手机号收不到验证码或者手机号变更需要绑定新的手机号，或者身份信息有误，都可以点击“账号申诉”进行解决"),
        },
    },
    {
        "id": "it-youxiang", "title": "校园邮箱开通",
        "aliases": ["学校邮箱", "edu邮箱", "邮箱怎么开通", "mail.cuc.edu.cn"],
        "keywords": ["邮箱", "mail", "edu"],
        "dept": "信息化处", "channel": ["线上系统"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "统一身份认证账号"}],
        "steps": [{"when": "开通", "what": "打开 mail.cuc.edu.cn，点「新用户开通」或「统一身份认证登录」，认证后首次登录自动开通",
                   "where": "mail.cuc.edu.cn"}],
        "fee": "免费", "location": "线上：https://mail.cuc.edu.cn",
        "hours": None, "duration": None, "window": None,
        "pitfalls": ["毕业离校后邮箱统一注销，走之前必须备份数据", "每人只能有一个个人邮箱，学号/工号是主账号"],
        "slots": [],
        "draft": None,
        "source": [{"title": "校园邮箱使用说明 · 信息化处",
                    "url": "https://its.cuc.edu.cn/2024/0813/c8502a241958/page.htm", "checked": "2026-10-20"}],
        "evidence": {
            "steps.0": ev("20240813-c8502a241958", "打开网址https://mail.cuc.edu.cn ，进入校园邮箱主页"),
            "fee": ev("20240813-c8502a241958", "学校为在校师生提供免费校园邮箱服务"),
            "location": ev("20240813-c8502a241958", "打开网址https://mail.cuc.edu.cn"),
            "pitfalls.0": ev("20240813-c8502a241958", "使用人毕业、离校后，邮箱将统一注销，请务必于离校前完成数据备份工作"),
            "pitfalls.1": ev("20240813-c8502a241958", "每位师生只能拥有一个个人邮箱，学号/工号为主账号"),
        },
    },
    {
        "id": "xy-xiaoyou", "title": "校友返校（入校）",
        "aliases": ["校友进校", "毕业了怎么进学校", "回学校怎么进", "校友码"],
        "keywords": ["校友", "返校", "入校"],
        "dept": "校友会 / 信息化处", "channel": ["线上系统"],
        "audience": ["校友"], "status": "verified", "confidence": "high",
        "materials": [{"name": "在校时学工号（用于查校友码）"}],
        "steps": [
            {"when": "第 1 步", "what": "中传 APP →「i中传」→「学工号查询」，查在校时的学工号", "where": "中传 APP"},
            {"when": "第 2 步", "what": "「我的」→「登录」，用学号和密码登录", "where": "中传 APP"},
            {"when": "第 3 步", "what": "点「i中传」获取校园码，刷校园码或身份证进出校门", "where": "校门"},
        ],
        "fee": None, "location": "线上：中传 APP", "hours": None, "duration": None, "window": None,
        "pitfalls": ["忘密码在「我的→登录→忘记密码」重置", "校友返校分个人返校和集体返校两种情况"],
        "slots": [],
        "draft": None,
        "source": [{"title": "校友返校指南 · 信息化处",
                    "url": "https://its.cuc.edu.cn/2023/1110/c10268a213617/page.htm", "checked": "2026-10-20"}],
        "evidence": {
            "steps.0": ev("20231110-c10268a213617", "进入中传APP，点击“i中传”版块中的“学工号查询”查询本人在校时的学工号"),
            "steps.2": ev("20231110-c10268a213617", "登录后，点击“i中传”获取校园码，刷校园码或身份证进出校门"),
            "pitfalls.0": ev("20231110-c10268a213617", "若忘记密码，可进入中传APP，在“我的”板块中的“登录”处点击“忘记密码”"),
            "pitfalls.1": ev("20231110-c10268a213617", "校友返校包括个人返校和集体返校两种情况"),
        },
    },
]

added = 0
for it in NEW:
    if it["id"] in have:
        continue
    d["items"].append(it)
    added += 1

d["updated"] = "2026-10-20"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"新增 {added} 条，累计 {len(d['items'])} 条")
