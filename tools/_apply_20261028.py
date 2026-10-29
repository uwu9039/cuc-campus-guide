"""一次性数据修复：删重复学信网条目、补缓考/勤工助学/校园卡充值/网费、修转专业两说。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


texts = {p.stem: squash(p.read_text(encoding="utf-8")) for p in SRC.rglob("*.txt")}

NEW = [
    {
        "id": "xueji-huankao",
        "title": "缓考申请",
        "aliases": ["缓考", "申请缓考", "缓考怎么申请", "病了考不了", "考试去不了", "期末考不了"],
        "keywords": ["缓考", "延期考试", "因病缺考"],
        "dept": "本科生院 / 学院",
        "channel": [],
        "audience": ["本科生"],
        "status": "verified",
        "confidence": "high",
        "materials": [{"name": "缓考申请及证明材料（考前规定时间内提交）"}],
        "steps": [
            {"when": "第 1 步", "what": "在考前规定时间内提交缓考申请及证明材料"},
            {"when": "第 2 步", "what": "审批通过后生效；逾期不予补办"},
            {"when": "第 3 步", "what": "缓考一般安排在下一学期初与重考同时进行"},
        ],
        "fee": None,
        "location": None,
        "hours": None,
        "duration": "下一学期初与重考同时进行",
        "window": "考前规定时间内",
        "pitfalls": [
            "因事原则上不允许缓考；只有急病、大病、意外伤残或不可抗力才算",
            "同一课程申请缓考原则上仅限一次",
            "缓考成绩按期末考试成绩占比计入总成绩，成绩单标注“缓考”",
        ],
        "slots": [
            {
                "key": "why",
                "ask": "是因病 / 意外，还是因为实习、出行等个人安排？",
                "options": ["病 / 意外 / 不可抗力", "个人安排"],
                "required": True,
                "decides": ["steps"],
                "why": "因事原则上不允许缓考，先分清原因再往下走",
            }
        ],
        "draft": None,
        "source": [
            {
                "title": "中国传媒大学本科生学籍管理规定（中传教字〔2025〕195号）",
                "url": "https://jwc.cuc.edu.cn/2025/1118/c13082a263811/page.htm",
                "checked": "2026-10-28",
            }
        ],
        "evidence": {
            "materials.0": {"src": "xueji-2025", "quote": "缓考须在考前规定时间内提交申请及证明材料"},
            "steps.0": {"src": "xueji-2025", "quote": "缓考须在考前规定时间内提交申请及证明材料"},
            "steps.1": {"src": "xueji-2025", "quote": "审批通过后生效，逾期不予补办"},
            "steps.2": {"src": "xueji-2025", "quote": "缓考一般安排在下一学期初与重考同时进行"},
            "duration": {"src": "xueji-2025", "quote": "缓考一般安排在下一学期初与重考同时进行"},
            "window": {"src": "xueji-2025", "quote": "缓考须在考前规定时间内提交申请及证明材料"},
            "pitfalls.0": {
                "src": "xueji-2025",
                "quote": "因患急病、患大病、突遇意外伤残或因不可抗力导致无法参加必修课程考试的，允许申请缓考。因事原则上不允许缓考。",
            },
            "pitfalls.1": {"src": "xueji-2025", "quote": "同一课程申请缓考原则上仅限一次"},
            "pitfalls.2": {
                "src": "xueji-2025",
                "quote": "考试成绩按期末考试成绩占比计入课程总成绩，成绩单标注“缓考”",
            },
        },
        "note": "学籍规定只写了“考前规定时间内提交申请及证明材料”，没写具体表单名称和受理部门——以学院 / 本科生院当学期通知为准。",
    },
    {
        "id": "xszz-qingong",
        "title": "勤工助学（校内岗位）",
        "aliases": ["勤工助学", "勤工助学怎么申请", "勤工俭学", "校内勤工助学", "助学岗位", "校内打工"],
        "keywords": ["勤工助学", "勤工俭学", "助学岗位", "校内岗位"],
        "dept": "学生工作部（处）学生资助中心",
        "channel": ["线上系统", "设岗单位"],
        "audience": ["本科生"],
        "status": "verified",
        "confidence": "high",
        "materials": [
            {"name": "《中国传媒大学学生勤工助学申请表》（在系统内填写）"},
            {"name": "校园银行卡（用于发放酬金）"},
        ],
        "steps": [
            {
                "when": "第 1 步",
                "what": "每学期初登录学校勤工助学管理系统，选择拟申请岗位，填写申请表",
                "where": "学校勤工助学管理系统",
            },
            {"when": "第 2 步", "what": "学生资助中心（勤工助学管理办公室）审核并推荐至设岗单位"},
            {"when": "第 3 步", "what": "设岗单位对学生进行面试和试用"},
            {"when": "第 4 步", "what": "协商一致后签订《中国传媒大学学生勤工助学岗位协议书》"},
            {
                "when": "酬金标准",
                "what": "固定岗位每岗每小时 12 元、每岗每月 480 元；临时岗位按小时计酬，每小时 12 元",
            },
            {"when": "发放", "what": "按考勤发放：每月月底前设岗单位上报考勤，财务处发放到校园银行卡"},
        ],
        "fee": None,
        "location": "线上（学校勤工助学管理系统）+ 设岗单位",
        "hours": None,
        "duration": None,
        "window": "每学期初",
        "pitfalls": [
            "每周不超过 8 小时、每月不超过 40 小时，不能影响上课",
            "岗位分固定岗位和临时岗位",
            "学生私自在校外兼职不在本办法规定之列",
            "适用于在籍注册的本科生、高职生、第二学士学位学生",
        ],
        "slots": [],
        "draft": None,
        "source": [
            {
                "title": "中国传媒大学勤工助学管理办法（学生工作规章制度汇编 2025）",
                "url": "https://xsc.cuc.edu.cn/2023/0904/c2753a259796/page.htm",
                "checked": "2026-10-28",
                "page": 312,
                "compilation": "学生工作规章制度汇编2025",
            }
        ],
        "evidence": {
            "materials.0": {"src": "hb921f79f1f2", "quote": "如实填写《中国传媒大学学生勤工助学申请表》"},
            "materials.1": {"src": "hb921f79f1f2", "quote": "由财务处直接发放到学生校园银行卡中"},
            "steps.0": {
                "src": "hb921f79f1f2",
                "quote": "每学期初由学生本人提出申请，登陆学校勤工助学管理系统，选择拟申请岗位，如实填写《中国传媒大学学生勤工助学申请表》",
            },
            "steps.1": {
                "src": "hb921f79f1f2",
                "quote": "学生工作部（处）勤工助学管理办公室对学生申请进行审核并推荐至设岗单位，由设岗单位对学生进行面试和试用",
            },
            "steps.2": {"src": "hb921f79f1f2", "quote": "由设岗单位对学生进行面试和试用"},
            "steps.3": {
                "src": "hb921f79f1f2",
                "quote": "通过面试和试用后，聘用双方就服务内容、时间、报酬、权利、义务、违约责任等进行协商，在协商一致的基础上签订《中国传媒大学学生勤工助学岗位协议书》，用工关系正式建立",
            },
            "steps.4": {
                "sources": [
                    {
                        "src": "hb921f79f1f2",
                        "quote": "固定岗位：按月计酬，每岗每小时12元，以每月40小时工时计算，每岗每月480元",
                    },
                    {
                        "src": "hb921f79f1f2",
                        "quote": "临时岗位：按小时计酬，每岗每小时12元",
                    },
                ]
            },
            "steps.5": {
                "src": "hb921f79f1f2",
                "quote": "岗位酬金按考勤发放，由设岗单位每月月底前上报考勤，经学生工作部（处）勤工助学管理办公室核实后，由财务处直接发放到学生校园银行卡中",
            },
            "location": {"src": "hb921f79f1f2", "quote": "登陆学校勤工助学管理系统"},
            "window": {"src": "hb921f79f1f2", "quote": "每学期初由学生本人提出申请"},
            "pitfalls.0": {
                "src": "hb921f79f1f2",
                "quote": "学生参加勤工助学的时间原则上每周不超过8小时，每月不超过40小时",
            },
            "pitfalls.1": {"src": "hb921f79f1f2", "quote": "勤工助学岗位分为固定岗位和临时岗位"},
            "pitfalls.2": {
                "src": "hb921f79f1f2",
                "quote": "勤工助学活动由学校统一组织和管理，学生私自在校外兼职的行为，不在本办法规定之列",
            },
            "pitfalls.3": {
                "src": "hb921f79f1f2",
                "quote": "本办法适用于我校在籍注册的本科生、高职生、第二学士学位学生",
            },
        },
        "note": None,
    },
    {
        "id": "xyk-chongzhi",
        "title": "校园卡充值",
        "aliases": [
            "校园卡怎么充值",
            "饭卡充值",
            "饭卡怎么充值",
            "一卡通充值",
            "校园卡充钱",
            "校园卡没钱了",
            "给校园卡充钱",
        ],
        "keywords": ["校园卡充值", "饭卡充值", "一卡通充值", "校园卡充钱", "饭卡充钱"],
        "dept": "信息化处",
        "channel": ["微信", "中传 APP", "企业微信", "自助机", "人工窗口"],
        "audience": ["本科生", "研究生"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": [
            {
                "when": "第 1 步",
                "what": "关注“中国传媒大学信息门户”公众号 → 综合服务 → 校园卡；也可用中传 APP「i·中传」或企业微信的“校园卡”模块",
            },
            {"when": "第 2 步", "what": "在“校园卡”界面点击“校园卡充值”，输入金额，点击“充值”"},
            {"when": "第 3 步", "what": "充值实时到账；也可在圈存机 / 自助充值机或校园卡服务中心人工充值"},
        ],
        "fee": None,
        "location": "线上（微信 / 中传 APP / 企业微信）；人工：校园卡服务中心（艺术与传播大楼 1 层校园生活服务大厅）",
        "hours": None,
        "duration": "实时到账",
        "window": None,
        "pitfalls": [
            "首次使用需要通过统一身份认证登录",
            "校园卡一般不得透支",
            "自助设备充值：圈存机绑定银行卡转账，或自助充值机现金充值；人工充值到校园卡服务中心",
        ],
        "slots": [],
        "draft": None,
        "source": [
            {
                "title": "校园卡使用指南 · 信息化处",
                "url": "https://its.cuc.edu.cn/2022/1027/c12936a200464/page.htm",
                "checked": "2026-10-28",
            },
            {
                "title": "中国传媒大学校园卡管理办法",
                "url": "https://its.cuc.edu.cn/2022/0702/c8488a194625/page.htm",
                "checked": "2026-10-28",
            },
        ],
        "evidence": {
            "steps.0": {
                "src": "20221027-c12936a200464",
                "quote": "关注并打开“中国传媒大学信息门户”公众号；进入“中国传媒大学信息门户”界面，打开下方“综合服务”菜单，点击“校园卡”即可进入校园卡功能页",
            },
            "steps.1": {
                "src": "20221027-c12936a200464",
                "quote": "在“校园卡”界面点击“校园卡充值”即可进入充值系统；输入充值金额，点击下方“充值”按钮；充值实时到账。",
            },
            "steps.2": {
                "src": "8eae7f42f0",
                "quote": "校园卡持卡人可使用自助设备、微信进行充值，也可人工充值。自助设备充值时，持卡人可在圈存机上与绑定的银行卡实现转账，或在自助充值机上现金充值；人工充值可到校园卡服务中心办理。",
            },
            "location": {
                "src": "20221027-c12936a200464",
                "quote": "校园卡服务中心（艺术与传播大楼1层校园生活服务大厅）",
            },
            "duration": {"src": "20221027-c12936a200464", "quote": "充值实时到账"},
            "pitfalls.0": {
                "src": "20221027-c12936a200464",
                "quote": "首次使用需要通过统一身份认证登录",
            },
            "pitfalls.1": {"src": "8eae7f42f0", "quote": "校园卡一般不得透支"},
            "pitfalls.2": {
                "src": "8eae7f42f0",
                "quote": "自助设备充值时，持卡人可在圈存机上与绑定的银行卡实现转账，或在自助充值机上现金充值；人工充值可到校园卡服务中心办理。",
            },
        },
        "note": None,
    },
    {
        "id": "it-wangfei",
        "title": "校园网网费与流量",
        "aliases": [
            "网费",
            "网费怎么交",
            "网费在哪交",
            "校园网网费",
            "校园网怎么收费",
            "流量超了",
            "超出流量",
            "校园网限速",
            "上网流量",
        ],
        "keywords": ["网费", "校园网网费", "流量", "限速", "超出流量"],
        "dept": "信息化处",
        "channel": ["线上认证", "校园卡缴费"],
        "audience": ["本科生", "研究生"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": [
            {"when": "第 1 步", "what": "用统一身份认证账号密码接入校园网（有线 / 无线）"},
            {"when": "第 2 步", "what": "认证页没弹出时，用浏览器打开 https://net.cuc.edu.cn 认证"},
            {"when": "第 3 步", "what": "缴费：校园卡可交纳校园网网费"},
        ],
        "fee": None,
        "location": "线上（浏览器认证页 net.cuc.edu.cn）",
        "hours": None,
        "duration": None,
        "window": None,
        "pitfalls": [
            "每月赠送 50G 流量，超出后限速",
            "无感知认证依赖设备 MAC 地址，需在网络设置里关闭“私有地址”",
            "报修：宿舍网络 移动 13911312873 / 联通 15699840801；校园卡及网络 65783878",
        ],
        "slots": [],
        "draft": None,
        "source": [
            {
                "title": "校园网认证服务 · 信息化处",
                "url": "https://its.cuc.edu.cn/2023/0221/c8498a202280/page.htm",
                "checked": "2026-10-28",
            },
            {
                "title": "中国传媒大学校园卡管理办法",
                "url": "https://its.cuc.edu.cn/2022/0702/c8488a194625/page.htm",
                "checked": "2026-10-28",
            },
        ],
        "evidence": {
            "steps.0": {
                "src": "20230221-c8498a202280",
                "quote": "校园网已与学校统一身份认证平台联通，师生员工通过统一身份认证平台的账号密码进行网络连接认证",
            },
            "steps.1": {
                "src": "20230221-c8498a202280",
                "quote": "未联网时，若认证页面未能自动弹出，用户可通过浏览器访问网络认证地址: https://net.cuc.edu.cn 打开该页面进行网络连接认证",
            },
            "steps.2": {
                "src": "8eae7f42f0",
                "quote": "校园卡具有持卡人身份认证、人脸识别、图书借阅、校内餐厅就餐、超市消费、学生宿舍出入、学校主要楼宇出入、交纳校园网网费、自助交纳电费、自助打印成绩单、学校医院就医缴费、会议签到、考勤等功能。",
            },
            "location": {
                "src": "20230221-c8498a202280",
                "quote": "用户可通过浏览器访问网络认证地址",
            },
            "pitfalls.0": {
                "src": "20230221-c8498a202280",
                "quote": "校园网目前执行的收费标准为每月赠送50G流量，超出后将进行限速，请节约使用",
            },
            "pitfalls.1": {
                "src": "20230221-c8498a202280",
                "quote": "该功能依赖于用户设备终端MAC地址，请在网络设置页面关闭“私有地址”等选项，以正常使用无感知认证功能",
            },
            "pitfalls.2": {
                "sources": [
                    {
                        "src": "20230221-c8498a202280",
                        "quote": "移动：13911312873 联通：15699840801",
                    },
                    {
                        "src": "20230221-c8498a202280",
                        "quote": "校园卡及网络报修电话 65783878",
                    },
                ]
            },
        },
        "note": "官方只写了“每月赠送 50G 流量，超出后限速”和校园卡可交网费，没有公布超额资费——具体扣费以计费系统为准。",
    },
]

CONFLICT = {
    "text": "同一件事有两个官方说法：2024 办法写“每年春季学期组织一次”，2025 修订写“原则上每学年组织一次，通常安排在秋季学期”——以本科生院当年通知为准",
    "evidence": {
        "sources": [
            {"src": "hb89efe99078", "quote": "第九条 转专业工作于每年春季学期组织一次。"},
            {"src": "zhuanzhuanye-2025", "quote": "原则上每学年组织一次，通常安排在秋季学期进行"},
        ]
    },
}


def check_ev(item: dict) -> list[str]:
    bad = []
    for field, ev in (item.get("evidence") or {}).items():
        items = ev.get("sources") if "sources" in ev else [ev]
        for one in items:
            src = one.get("src", "")
            q = squash(one.get("quote", ""))
            if src not in texts:
                bad.append(f"{item['id']} {field}: 来源不存在 {src}")
            elif not q or q not in texts[src]:
                bad.append(f"{item['id']} {field}: 原文找不到 {one.get('quote','')[:50]}")
    return bad


def main() -> None:
    path = ROOT / "items.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    before = len(data["items"])
    data["items"] = [i for i in data["items"] if not i["id"].startswith("rule-chsi")]
    removed = before - len(data["items"])

    ids = {i["id"] for i in data["items"]}
    added = 0
    for item in NEW:
        if item["id"] in ids:
            raise SystemExit(f"id 已存在：{item['id']}")
        data["items"].append(item)
        ids.add(item["id"])
        added += 1

    for item in data["items"]:
        if item["id"] == "hq-goudian":
            item["keywords"] = ["购电", "电费", "没电", "电费充值"]
            for a in ["电费怎么充值", "电费充值", "宿舍电费"]:
                if a not in item["aliases"]:
                    item["aliases"].append(a)
        if item["id"] == "chsi-baogao":
            if "学信网" not in item["keywords"]:
                item["keywords"].append("学信网")
        if item["id"] == "zhuanzhuanye":
            item.setdefault("pitfalls", []).append(CONFLICT["text"])
            item.setdefault("evidence", {})[f"pitfalls.{len(item['pitfalls']) - 1}"] = CONFLICT["evidence"]

    bad = []
    for item in data["items"]:
        bad.extend(check_ev(item))
    if bad:
        print("\n".join(bad))
        raise SystemExit(f"证据校验失败 {len(bad)} 条，未写入")

    data["updated"] = "2026-10-28"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"删除 {removed} 条，新增 {added} 条，总数 {len(data['items'])}")


if __name__ == "__main__":
    main()
