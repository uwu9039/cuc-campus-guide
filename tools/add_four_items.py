"""补 4 个拒答条目：新生报到军训、图书馆借阅、毕业生户口档案、教材发放。

引文一律从语料原文里按锚点抠取，保证逐字一致。
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"


def grab(slug_rel: str, anchor: str, limit: int = 200) -> str:
    """允许锚点中间夹换行（PDF 折行会把词拆开）。"""
    body = (SRC / slug_rel).read_text(encoding="utf-8")
    pat = r"\s*".join(re.escape(c) for c in anchor)
    m = re.search(pat, body)
    if not m:
        raise SystemExit(f"锚点找不到：{anchor} (in {slug_rel})")
    seg = body[m.start():m.start() + limit]
    seg = re.split(r"。", seg, maxsplit=1)[0]
    return re.sub(r"\s*\n\s*", "", seg).strip()


XB = "local/loc-2026级本科生入学须知-校本部-2cdd30.txt"
TS = "cdp/20260529-c2753a271140.txt"
HK = "huibian/hb49833f4409.txt"
SS = "local/loc-中国传媒大学2026级新生售书单-be2342.txt"

q_report = grab(XB, "2026 级本科新生的报到时间为")
q_train = grab(XB, "军训时间为")
q_bag = grab(XB, "新生收到《录取通知书》后")
q_lib1 = grab(TS, "（一）读者凭校园“一卡通”")
q_lib2 = grab(TS, "（三）借出图书逾期归还者")
q_lib3 = grab(TS, "（二）若需办理续借手续")
q_hk = grab(HK, "（一）在北京落实就业单位并解决落户的学生")
q_hk2 = grab(HK, "（六）需要办理户档暂留手续的")
q_book = grab(SS, "中国传媒大学2026年秋季教材发放清单")

ITEMS = [
    {
        "id": "xinsheng-baodao",
        "title": "新生报到与军训（2026 级本科）",
        "aliases": ["新生报到", "报到流程", "军训", "开学报到", "新生入学"],
        "keywords": ["报到", "军训", "新生入学", "录取通知书"],
        "dept": "本科生院 / 学生工作部（处）（武装部）", "channel": ["线下窗口", "线上系统"],
        "audience": ["本科生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "录取通知书"}, {"name": "个人档案（含团组织关系，密封完好）"}],
        "steps": [
            {"when": "报到时间", "what": "2026 级本科新生报到时间为 2026 年 9 月 5 日—6 日", "where": "校本部"},
            {"when": "军训", "what": "军训时间为 2026 年 9 月 17 日—30 日", "where": "学校"},
            {"when": "请假", "what": "因故不能按期报到，须事先书面向所在学院、本科生院请假", "where": "学院 / 本科生院"},
            {"when": "带档案", "what": "先与高中确认档案转递方式，推荐本人自带；密封条须完好", "where": "原高中 / 学院"},
        ],
        "fee": None, "location": "校本部", "hours": None, "duration": None, "window": None,
        "pitfalls": ["学校不安排接站", "未经请假逾期不报到按放弃入学资格处理"],
        "slots": [],
        "draft": None,
        "source": [{"title": "中国传媒大学 2026 级本科生入学须知（校本部）", "checked": "2026-10-27",
                    "url": "", "file": "2026级本科生入学须知（校本部）.pdf"}],
        "evidence": {
            "steps.0": {"src": "loc-2026级本科生入学须知-校本部-2cdd30", "quote": q_report},
            "steps.1": {"src": "loc-2026级本科生入学须知-校本部-2cdd30", "quote": q_train},
            "steps.3": {"src": "loc-2026级本科生入学须知-校本部-2cdd30", "quote": q_bag},
        },
        "advisory": ["2027 级的具体日期以当年入学须知为准，这里写的是 2026 级"],
    },
    {
        "id": "lib-jieyue",
        "title": "图书馆借阅（借书、续借、逾期）",
        "aliases": ["图书馆借书", "借阅", "续借", "书到期", "借书证"],
        "keywords": ["借阅", "续借", "逾期", "图书馆"],
        "dept": "图书馆", "channel": ["线下窗口"],
        "audience": ["本科生", "研究生", "教职工"], "status": "verified", "confidence": "high",
        "materials": [{"name": "校园一卡通"}],
        "steps": [
            {"when": "借书", "what": "凭校园“一卡通”按借阅权限在图书馆借阅图书", "where": "图书馆"},
            {"when": "续借", "what": "按有关规定自行办理续借手续", "where": "图书馆（线上可办）"},
        ],
        "fee": None, "location": "图书馆", "hours": None, "duration": None, "window": None,
        "pitfalls": ["借出图书逾期归还者，停止借阅"],
        "slots": [],
        "draft": None,
        "source": [{"title": "中国传媒大学图书馆文献借阅规定", "checked": "2026-10-27", "url": ""}],
        "evidence": {
            "steps.0": {"src": "20260529-c2753a271140", "quote": q_lib1},
            "steps.1": {"src": "20260529-c2753a271140", "quote": q_lib3},
            "pitfalls.0": {"src": "20260529-c2753a271140", "quote": q_lib2},
            "materials.0": {"src": "20260529-c2753a271140", "quote": q_lib1},
        },
        "advisory": ["可借册数与借期按读者类型不同，规定里另有分档，问馆员最快"],
    },
    {
        "id": "biye-hukou-dangan",
        "title": "毕业生户口与档案（报到证、户档暂留）",
        "aliases": ["三方协议", "报到证", "档案去哪了", "户口迁移", "户档暂留", "毕业户口"],
        "keywords": ["报到证", "户档暂留", "户口迁移", "档案", "就业科"],
        "dept": "学生工作部（处）就业科 / 保卫部（处）户籍科", "channel": ["线下窗口"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "报到证（在就业科办理）"}, {"name": "户口卡或户口迁移证"}],
        "steps": [
            {"when": "北京就业且落户", "what": "到户籍科领户口卡，持户口卡和报到证到单位报到", "where": "户籍科 → 单位"},
            {"when": "外埠就业且落户", "what": "到户籍科领户口迁移证，持迁移证和报到证到单位报到", "where": "户籍科 → 单位"},
            {"when": "暂不就业/考研/出国", "what": "户口迁回原籍，迁往地址要落实到家庭户口详细地址", "where": "户籍科"},
            {"when": "需要缓迁", "what": "在就业科办户档暂留手续，再持证明到户籍科备案", "where": "就业科 → 户籍科"},
        ],
        "fee": None, "location": "学生工作部（处）就业科 / 保卫部（处）户籍科",
        "hours": None, "duration": None, "window": None,
        "pitfalls": ["户档暂留期间只办与迁户相关的手续，户口卡一律不外借"],
        "slots": [],
        "draft": None,
        "source": [{"title": "中国传媒大学集体户口管理暂行规定 · 制度汇编 p.55", "checked": "2026-10-27",
                    "url": "https://xsc.cuc.edu.cn/2023/0904/c2753a259796/page.htm"}],
        "evidence": {
            "steps.0": {"src": "hb49833f4409", "quote": q_hk},
            "steps.3": {"src": "hb49833f4409", "quote": q_hk2},
            "pitfalls.0": {"src": "hb49833f4409", "quote": q_hk2},
        },
        "advisory": ["「三方协议怎么签」属于就业手续，这份规定只覆盖户口与报到证环节"],
    },
    {
        "id": "jiaocai-fafang",
        "title": "教材清单与发放",
        "aliases": ["教材在哪买", "教材", "售书单", "买书", "教材费"],
        "keywords": ["教材", "售书单", "教材发放", "订书"],
        "dept": "本科生院 / 教材供应", "channel": ["线下窗口"],
        "audience": ["本科生"], "status": "verified", "confidence": "medium",
        "materials": [],
        "steps": [
            {"when": "查清单", "what": "按班级查看《教材发放清单》，含课程、书号、教材名、出版社、定价、册数",
             "where": "本科生院 / 学院"},
        ],
        "fee": None, "location": "本科生院", "hours": None, "duration": None, "window": None,
        "pitfalls": [],
        "slots": [],
        "draft": None,
        "source": [{"title": "中国传媒大学 2026 年秋季教材发放清单（新生售书单）", "checked": "2026-10-27",
                    "url": "", "file": "中国传媒大学2026级新生售书单.xlsx"}],
        "evidence": {"steps.0": {"src": "loc-中国传媒大学2026级新生售书单-be2342", "quote": q_book}},
        "advisory": ["购买渠道与结算方式清单里没写，问学院教务老师"],
    },
]

p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
have = {i["id"] for i in d["items"]}
added = 0
for it in ITEMS:
    if it["id"] in have:
        continue
    d["items"].append(it)
    added += 1
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"新增 {added} 条，共 {len(d['items'])}")
for k, v in (("报到", q_report), ("军训", q_train), ("借阅", q_lib1), ("户口", q_hk)):
    print(f"  {k}: {v[:60]}")
