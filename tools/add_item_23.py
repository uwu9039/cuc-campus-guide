"""补第 23 条（账号激活），并给「校园网连不上」补第二个官方来源。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
have = {i["id"] for i in d["items"]}

ACT = "20220922-c8508a199117"   # 统一身份认证账号激活
NET = "20220922-c8498a199120"   # 访问校园网

item = {
    "id": "it-jihuo",
    "title": "统一身份认证账号激活",
    "aliases": ["账号激活", "激活账号", "新生怎么登录", "学号查不到", "登录不了数字校园"],
    "keywords": ["激活", "账号激活", "学号查询"],
    "dept": "信息化处",
    "channel": ["线上系统"],
    "audience": ["本科生", "研究生"],
    "status": "verified",
    "confidence": "high",
    "materials": [{"name": "本人证件号与姓名（查学工号时）"},
                  {"name": "可接收短信的手机号（绑定时）"}],
    "steps": [
        {"when": "第 1 步", "what": "中传 APP 免登录进「i·中传」→「学号查询」，输入证件号与姓名查到学工号", "where": "中传 APP"},
        {"when": "第 2 步", "what": "「我的」→「登录」→「账号激活」", "where": "中传 APP"},
        {"when": "第 3 步", "what": "按提示输入学号、姓名、证件号验证，绑定手机号并设置密码", "where": "线上"},
    ],
    "fee": None,
    "location": "中传 APP（「我的」→「登录」）",
    "hours": None,
    "duration": None,
    "window": None,
    "pitfalls": ["统一身份认证用户名就是工号/学号，没激活等于所有业务系统都进不去"],
    "slots": [],
    "draft": None,
    "source": [{"title": "统一身份认证账号激活 · 信息化处",
                "url": "https://its.cuc.edu.cn/2022/0922/c8508a199117/page.htm", "checked": "2026-10-20"}],
    "evidence": {
        "pitfalls.0": {"src": ACT, "quote": "师生员工的统一身份认证用户名是工号/学号，需激活后使用"},
        "steps.0": {"src": ACT, "quote": "进入“i·中传”版块，点击“学号查询”,输入相应证件号与姓名等信息，点击“查询”按钮查询获得学工号"},
        "steps.1": {"src": ACT, "quote": "在中传APP“我的”页面点击“登录”按钮"},
        "steps.2": {"src": ACT, "quote": "点击“账号激活”，按提示输入“学号、姓名、证件号”验证个人信息后，完成绑定手机号、设置密码等激活操作"},
        "materials.0": {"src": ACT, "quote": "输入“学号、姓名、证件号”验证个人信息"},
        "materials.1": {"src": ACT, "quote": "完成绑定手机号、设置密码等激活操作"},
        "location": {"src": ACT, "quote": "在中传APP“我的”页面点击“登录”按钮"},
    },
}

if item["id"] not in have:
    d["items"].append(item)
    print("新增：统一身份认证账号激活")

for it in d["items"]:
    if it["id"] != "it-wangluo":
        continue
    # 第二个官方来源：访问校园网（讲清两种 SSID 与认证页地址）
    it["steps"].insert(2, {"when": "连不上时", "what": "无线网有两种：Wireless CUC 与 Wireless CUC–Guest，连上后浏览器弹登录页",
                           "where": "教学楼 / 食堂 / 图书馆"})
    it["evidence"]["steps.2"] = {"sources": [
        {"src": NET, "quote": "无线网SSID为“Wireless CUC”和“Wireless CUC–Guest”，为两种不同的接入方式"},
        {"src": NET, "quote": "选中“Wireless CUC”，点击连接，浏览器会自动跳出登录页面"},
    ]}
    it["evidence"]["steps.3"] = {"sources": [
        {"src": NET, "quote": "认证页面网址：net.cuc.edu.cn"},
        {"src": "20230221-c8498a202280", "quote": "用户可通过浏览器访问网络认证地址: https://net.cuc.edu.cn 打开该页面进行网络连接认证"},
    ]}
    it["source"].append({"title": "访问校园网 · 信息化处",
                         "url": "https://its.cuc.edu.cn/2022/0922/c8498a199120/page.htm",
                         "checked": "2026-10-20"})
    print("校园网条目已补第二个官方来源（访问校园网）")

p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print("条目总数：", len(d["items"]))
