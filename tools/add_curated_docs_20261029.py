"""把问道短文档整理成可直接回答的条目（2026-10-29）。

每一条 quote 都先校验能在 sources/wendao-text/<src>.txt 里找到（忽略空白）。
"""
import json
import re
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")
SRC = ROOT / "sources"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


TEXTS = {}
for f in (SRC / "wendao-text").glob("*.txt"):
    TEXTS[f.stem] = squash(f.read_text(encoding="utf-8"))


def item(iid, title, aliases, dept, steps, pitfalls=None, contact=None,
         location=None, hours=None, sources=None, kind="service", slots=None):
    ev = {}
    out_steps = []
    for i, (src, what, when) in enumerate(steps):
        q = squash(what)
        assert q in TEXTS[src], f"{iid} steps.{i} 找不到原文: {what[:40]}"
        ev[f"steps.{i}"] = {"src": src, "quote": what}
        out_steps.append({"when": when or f"第 {i+1} 步", "what": what})
    out_pf = []
    for i, (src, what) in enumerate(pitfalls or []):
        assert squash(what) in TEXTS[src], f"{iid} pitfalls.{i} 找不到原文: {what[:40]}"
        ev[f"pitfalls.{i}"] = {"src": src, "quote": what}
        out_pf.append(what)
    if contact:
        src, what = contact
        assert squash(what) in TEXTS[src], f"{iid} contact 找不到原文"
        ev["contact"] = {"src": src, "quote": what}
        contact_text = what
    else:
        contact_text = None
    return {
        "id": iid,
        "title": title,
        "aliases": aliases,
        "keywords": [],
        "dept": dept,
        "channel": ["线上/线下按原文"],
        "audience": ["本科生", "研究生", "教职工"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": out_steps,
        "fee": None,
        "location": location,
        "hours": hours,
        "duration": None,
        "window": None,
        "pitfalls": out_pf,
        "contact": contact_text,
        "slots": slots or [],
        "draft": None,
        "kind": kind,
        "source": sources or [],
        "evidence": ev,
    }


NEW = [
    item(
        "xyy-jiuzhen",
        "校医院就诊流程",
        ["校医院怎么看病", "校医院挂号", "看病流程", "校医院在哪看病", "校医院看病步骤"],
        "校医院",
        [
            ("9cf3926b", "第一步：挂号；", "第 1 步"),
            ("9cf3926b", "第二步：到相关科室就诊；", "第 2 步"),
            ("9cf3926b", "第三步：需检查、治疗或化验者，先到收费处交费后检查、治疗或化验；", "第 3 步"),
            ("9cf3926b", "第四步：开药后到收费处交费；", "第 4 步"),
            ("9cf3926b", "第五步：药房取药后离开或到相应科室治疗。", "第 5 步"),
        ],
        location="校医院",
        sources=[{"title": "校医院就诊流程", "url": "", "checked": "2026-10-29"}],
    ),
    item(
        "xiaomen-jinchu",
        "校门与入校（南门 / 北门 / 西门）",
        ["校门", "哪个门能进", "进校", "入校", "访客进校", "校门门禁", "校外人员进校"],
        "保卫处",
        [
            ("dc22a56a", "中国传媒大学有南门、北门、西门3个校门。", "第 1 步"),
            ("dc22a56a", "每个校门都有门禁，可以用校园卡、人脸识别、预约二维码等方式进出校门。", "第 2 步"),
            ("dc22a56a", "校外人员或校外车辆，需要通过访客预约的方式进校。", "第 3 步"),
        ],
        sources=[{"title": "中国传媒大学基本信息", "url": "", "checked": "2026-10-29"}],
    ),
    item(
        "zxc-chongdian",
        "电动自行车充电桩位置",
        ["电动车充电", "电瓶车充电", "电动自行车", "充电桩在哪", "自行车充电"],
        "后勤保障处",
        [
            ("8f3f1ca5", "可以使用校内的专用电动自行车充电桩充电。", "第 1 步"),
            ("8f3f1ca5", "电动自行车充电桩在学校北门（校内）两侧，学校南门（校内）两侧，国际交流中心（21号楼）东侧，10号楼南侧，11号楼南侧，14号楼南侧，16号楼南侧设有专用充电桩，", "第 2 步"),
        ],
        sources=[{"title": "知识库-家属区管理办公室", "url": "", "checked": "2026-10-29"}],
    ),
    item(
        "baogaoting-yuyue",
        "公共报告厅预约（中传礼堂 / 中传讲堂）",
        ["报告厅预约", "中传礼堂预约", "中传讲堂预约", "1500报", "400报", "圆形报告厅", "借报告厅"],
        "教育服务中心",
        [
            ("0f18a29a", "公共报告厅范围：", "范围"),
            ("0f18a29a", "中传学术中心、中传礼堂、中传讲堂、圆形报告厅；", "范围"),
            ("0f18a29a", "44号楼一层报告厅不属于公共报告厅；", "注意"),
            ("0f18a29a", "https://workflow.cuc.edu.cn/reservation/fe/site/special/special?id=36", "预约入口"),
        ],
        contact=("0f18a29a", "65779277（赵老师）"),
        sources=[{"title": "公共报告厅相关事项", "url": "https://workflow.cuc.edu.cn/reservation/fe/site/special/special?id=36", "checked": "2026-10-29"}],
    ),
    item(
        "shijian-changguan-yuyue",
        "公共实践场馆预约（演播馆 / 音乐厅 / 放映厅）",
        ["演播馆预约", "中传演播馆", "1400平米演播馆", "中传音乐厅", "4K放映厅", "实践场馆"],
        "教育服务中心",
        [
            ("4b3b7735", "接受中传演播馆（1400平米演播馆）、XR演播馆、混录棚、M80演播馆、M100演播馆、高清转播车、中传音乐厅、4K放映厅等公共实践场所的预约申请。", "可预约场馆"),
            ("4b3b7735", "https://workflow.cuc.edu.cn/reservation/fe/site/reservationInfo?id=1230", "预约入口"),
        ],
        sources=[{"title": "服务 · 公共实践场所申请", "url": "https://workflow.cuc.edu.cn/reservation/fe/site/reservationInfo?id=1230", "checked": "2026-10-29"}],
    ),
    item(
        "jiaoshi-jieyong",
        "教室申请 / 借用",
        ["教室预约", "借教室", "教室借用", "48教教室", "1教教室", "博学楼教室", "立德楼教室"],
        "教育服务中心",
        [
            ("4b3b7735", "教室借用，教室预约。目前仅开放博学楼（48教）、立德楼（1教）的教室预约", "第 1 步"),
            ("4b3b7735", "https://workflow.cuc.edu.cn/reservation/fe/site/special/special?id=33&platform_id=19", "预约入口"),
        ],
        contact=("18fe5c7d", "65783385"),
        sources=[{"title": "服务 · 教室申请", "url": "https://workflow.cuc.edu.cn/reservation/fe/site/special/special?id=33&platform_id=19", "checked": "2026-10-29"}],
    ),
    item(
        "shitang-wukou",
        "食堂消费误扣款处理",
        ["食堂多扣钱", "误扣款", "消费异常", "饭卡多扣", "食堂扣错钱"],
        "后勤保障处 / 信息化处",
        [
            ("b825a538", "如出现消费异常，请将本人的学号（工号）、姓名、异常消费信息截图、消费时间证明，发给就餐食堂负责人统一协调相关部门解决。", "第 1 步"),
        ],
        pitfalls=[
            ("b825a538", "我校师生需通过校园卡渠道（校园码、校园卡、NFC电子校园卡）进行就餐支付方能享受基本伙补助。"),
        ],
        sources=[{"title": "误扣款说明公告", "url": "", "checked": "2026-10-29"}],
    ),
    item(
        "zhaosheng-chu",
        "本科招生咨询联系方式",
        ["招生办电话", "招生处", "本科招生咨询", "招生邮箱"],
        "招生处",
        [
            ("9c682277", "电话：010-65779227", "电话"),
            ("9c682277", "邮箱：cucyzb@cuc.edu.cn", "邮箱"),
        ],
        contact=("9c682277", "电话：010-65779227"),
        sources=[{"title": "联系我们 · 中国传媒大学招生处", "url": "", "checked": "2026-10-29"}],
    ),
]

# 信息化服务入口清单：answer 是对官方表格的重排，证据用整段原文
INFO_ANSWER = (
    "校园公告 https://i.cuc.edu.cn/qljggfw/sys/lwPsTzggApp/index.do；"
    "中传云盘 https://pan.cuc.edu.cn（目前只对在校教职工、在校本研学生开放）；"
    "SSL VPN https://vpn.cuc.edu.cn（校外免费访问校内资源）；"
    "学工号查询 https://ry.cuc.edu.cn/main/search/index.html；"
    "校园码 https://sso.cuc.edu.cn/authserver/identityQrCode/getExIdentityQrCode.do（通行、消费、就医）；"
    "正版软件平台 http://software.cuc.edu.cn（Windows、Office、WPS 365、Adobe）；"
    "统一身份认证 https://sso.cuc.edu.cn/personalInfo/personCenter/index.html#/accountsecurity；"
    "校园邮箱 https://mail.cuc.edu.cn；"
    "校园卡 https://pcard.cuc.edu.cn/servicehall/casClient/login（余额、挂失解挂、流水、消费限额）；"
    "问道中传 https://aia.cuc.edu.cn；AI 能力中心 https://aihub.cuc.edu.cn；"
    "信息化服务报修 https://faq.cuc.edu.cn/cgi-bin/web/yunimstart?app=uirsso&bumen=%E4%BF%A1%E6%81%AF%E4%B8%AD%E5%BF%83&times=1，"
    "电话 010-65783878，地点 艺术与传播大楼 1 层 校园生活服务大厅。"
)
raw_info = (SRC / "wendao-text" / "1eb28fae.txt").read_text(encoding="utf-8")
_i1 = raw_info.find("校园公告 | 校园公告入口。")
_i2 = raw_info.find("https://faq.cuc.edu.cn/cgi-bin/web/yunimstart?app=uirsso")
_i2 = raw_info.find("\n", _i2)
info_quote = raw_info[_i1:_i2].strip()
assert _i1 >= 0 and _i2 > _i1, "服务清单整段定位失败"

NEW.append({
    "id": "xinxi-fuwu-daohang",
    "title": "信息化服务入口清单（VPN / 云盘 / 邮箱 / 正版软件 / 校园码）",
    "aliases": ["VPN", "中传云盘", "校园邮箱", "正版软件", "校园码", "学工号查询", "统一身份认证", "信息化报修", "校园卡查询"],
    "keywords": [],
    "dept": "信息化处",
    "channel": ["线上"],
    "audience": ["本科生", "研究生", "教职工"],
    "status": "verified",
    "confidence": "high",
    "materials": [],
    "steps": [],
    "fee": None,
    "location": "艺术与传播大楼 1 层 校园生活服务大厅（报修）",
    "hours": None,
    "duration": None,
    "window": None,
    "pitfalls": ["学校为在校师生提供免费校园邮箱服务，使用人毕业、离校后，邮箱将统一注销，请务必于离校前完成数据备份工作。"],
    "slots": [],
    "draft": None,
    "answer": INFO_ANSWER,
    "kind": "service",
    "source": [{"title": "服务清单 · 信息化处", "url": "", "checked": "2026-10-29"}],
    "evidence": {
        "answer": {"src": "1eb28fae", "quote": info_quote},
        "location": {"src": "1eb28fae", "quote": "报修办理地点：艺术与传播大楼1层 校园生活服务大厅。"},
        "pitfalls.0": {"src": "1eb28fae", "quote": "学校为在校师生提供免费校园邮箱服务，使用人毕业、离校后，邮箱将统一注销，请务必于离校前完成数据备份工作。"},
    },
})


for it in NEW:
    if it["id"] == "xyy-jiuzhen":
        it["evidence"]["location"] = {"src": "9cf3926b", "quote": "校医院就诊流程"}


def main() -> None:
    p = ROOT / "items.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    have = {i["id"] for i in data["items"]}
    added = 0
    for it in NEW:
        if it["id"] in have:
            continue
        data["items"].append(it)
        added += 1
    data["updated"] = "2026-10-29"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"新增 {added} 条，总计 {len(data['items'])}")


if __name__ == "__main__":
    main()
