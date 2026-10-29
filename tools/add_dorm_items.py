"""补生活事务类条目：宿舍电器、洗浴、换宿、门禁、钥匙、住宿证明、退宿、洗衣、快递。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


TEXTS = {}
for sub in ("wendao-text", "crawl", "cdp", "extra", "local"):
    for f in (SRC / sub).glob("*.txt"):
        TEXTS[f.stem] = squash(f.read_text(encoding="utf-8", errors="ignore"))


def make(iid, title, aliases, dept, steps, pitfalls=None, location=None,
         contact=None, answer=None, sources=None):
    ev = {}
    out_steps = []
    for i, (src, what, when) in enumerate(steps):
        assert squash(what) in TEXTS[src], f"{iid} steps.{i} 找不到: {what[:40]}"
        ev[f"steps.{i}"] = {"src": src, "quote": what}
        out_steps.append({"when": when or f"第 {i+1} 步", "what": what})
    out_pf = []
    for i, (src, what) in enumerate(pitfalls or []):
        assert squash(what) in TEXTS[src], f"{iid} pitfalls.{i} 找不到: {what[:40]}"
        ev[f"pitfalls.{i}"] = {"src": src, "quote": what}
        out_pf.append(what)
    contact_text = None
    if contact:
        src, what = contact
        assert squash(what) in TEXTS[src], f"{iid} contact 找不到"
        ev["contact"] = {"src": src, "quote": what}
        contact_text = what
    if location:
        src, what = location
        assert squash(what) in TEXTS[src], f"{iid} location 找不到"
        ev["location"] = {"src": src, "quote": what}
        location_text = what
    else:
        location_text = None
    if answer:
        src, what = answer
        assert squash(what) in TEXTS[src], f"{iid} answer 找不到"
        ev["answer"] = {"src": src, "quote": what}
        answer_text = what
    else:
        answer_text = None
    return {
        "id": iid, "title": title, "aliases": aliases, "keywords": [], "dept": dept,
        "channel": ["电话", "微信公众号"], "audience": ["本科生", "研究生"],
        "status": "verified", "confidence": "high", "materials": [], "steps": out_steps,
        "fee": None, "location": location_text, "hours": None, "duration": None,
        "window": None, "pitfalls": out_pf, "contact": contact_text, "slots": [],
        "draft": None, "answer": answer_text, "kind": "service",
        "source": sources or [], "evidence": ev,
    }


NEW = [
    make(
        "sushe-dianqi",
        "宿舍电器使用规则（吹风机 / 电煮锅 / 大功率）",
        ["宿舍能用什么电器", "吹风机", "电煮锅", "大功率电器", "违章电器", "电磁炉", "电暖器", "宿舍限电"],
        "后勤保障处 学生公寓服务中心",
        [
            ("9bf17365", "宿舍内禁止吸烟，严禁使用明火，禁止存放和使用酒精炉、煤油炉、液化气灶等有明火的器具，禁止点蜡烛照明，禁止燃烧蚊香驱蚊，禁止饲养宠物（猫、狗、兔子、蜥蜴、蛇等）；", "禁止事项"),
            ("9bf17365", "禁止使用电吹风、电冰箱、洗衣机、电炉、电热杯、电热褥、电暖器、电磁加热装置、电阻加热装置等电器，若宿舍内存放以上物品，一经发现以使用违章电器论处，予以没收（没收物品交由相关部门处理），并按照相关规定处理。", "禁止电器"),
            ("9bf17365", "学生公寓为同学们配备了公共电吹风机。设立位置：公寓楼值班室的一层大厅处，每楼层隔层设有一个电吹风处。", "吹风机在哪"),
            ("9bf17365", "各学生公寓楼均已安装空调机，供学生免费使用（电费自理），其中中蓝公寓（二期）为中央空调。", "空调"),
        ],
        pitfalls=[
            ("9bf17365", "学生公寓内严禁使用违规电器、明火器具；禁止使用其他可能危害人身安全和公共财产安全的设备。"),
        ],
        sources=[{"title": "知识库 · 学生公寓服务中心", "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=9bf17365e1e543f38dc410b2a34e0686", "checked": "2026-10-29"}],
    ),
    make(
        "sushe-xizao",
        "宿舍洗浴与热水时间",
        ["洗澡时间", "热水时间", "浴室", "洗浴", "公共浴室", "宿舍有热水吗"],
        "后勤保障处 学生公寓服务中心",
        [
            ("9bf17365", "各公寓楼供洗澡水时间：24小时供应", "热水"),
            ("9bf17365", "假期各公寓楼供水时间为：24小时供应（具体以实际为准）。", "假期"),
        ],
        pitfalls=[
            ("9bf17365", "具体以实际为准"),
        ],
        sources=[{"title": "知识库 · 学生公寓服务中心", "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=9bf17365e1e543f38dc410b2a34e0686", "checked": "2026-10-29"}],
    ),
    make(
        "sushe-huansu",
        "换宿舍 / 调宿",
        ["换宿舍", "调宿", "换寝", "调换宿舍", "宿舍调整"],
        "后勤保障处 学生公寓服务中心",
        [
            ("9bf17365", "学生不允许私自调换宿舍，发现后本楼管理员会上报给本区管理部做进一步调整", "规定"),
            ("9bf17365", "到本楼值班室找管理员协调解决", "怎么办"),
        ],
        pitfalls=[
            ("loc-中国传媒大学学生公寓住宿协议书-a9f629", "安排后原则上不再变动，乙方因特殊情况确需调整的，须向甲方提出申请，根据实际情况办理调宿。"),
        ],
        sources=[{"title": "知识库 · 学生公寓服务中心", "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=9bf17365e1e543f38dc410b2a34e0686", "checked": "2026-10-29"}],
    ),
    make(
        "sushe-menjin",
        "公寓开放与门禁时间",
        ["宿舍门禁", "公寓几点关门", "晚归", "宿舍开门时间", "公寓开放时间"],
        "后勤保障处 学生公寓服务中心",
        [
            ("9bf17365", "学生公寓楼实行封闭管理，每日早6：00开门，24：00关门（寒暑假根据实际情况另行安排）。", "开放时间"),
            ("9bf17365", "学校全面实施公寓人脸识别系统，学院、辅导员、研究生院及学生工作部有权限进行门禁查询，了解学生出入公寓楼情况。", "门禁方式"),
        ],
        pitfalls=[("9bf17365", "寒暑假根据实际情况另行安排")],
        sources=[{"title": "知识库 · 学生公寓服务中心", "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=9bf17365e1e543f38dc410b2a34e0686", "checked": "2026-10-29"}],
    ),
    make(
        "sushe-yaoshi",
        "宿舍钥匙丢了怎么办",
        ["钥匙丢了", "宿舍钥匙", "门锁坏了", "忘带钥匙"],
        "后勤保障处 学生公寓服务中心",
        [("9bf17365", "到本楼值班室找管理员协调解决", "第 1 步")],
        sources=[{"title": "知识库 · 学生公寓服务中心", "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=9bf17365e1e543f38dc410b2a34e0686", "checked": "2026-10-29"}],
    ),
    make(
        "sushe-zhengming",
        "住宿证明怎么开",
        ["住宿证明", "住校证明", "开住宿证明"],
        "后勤保障处 学生公寓服务中心",
        [("9bf17365", "学生持有效证件（校园卡、身份证、学生证等）到学生公寓服务中心办公室开具", "第 1 步")],
        location=("9bf17365", "学生公寓办公室在校内 55号楼（游泳馆入口）二层 201室。"),
        sources=[{"title": "知识库 · 学生公寓服务中心", "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=9bf17365e1e543f38dc410b2a34e0686", "checked": "2026-10-29"}],
    ),
    make(
        "sushe-tuixiu",
        "退宿 / 校外住宿（走读）",
        ["退宿", "走读", "校外住宿", "搬出去住", "不住宿舍"],
        "后勤保障处 学生公寓服务中心",
        [
            ("9bf17365", "在后勤综合服务网下载中心（网址：https://zchq.cuc.edu.cn/147/list.htm）—下载《中国传媒大学学生申请校外住宿审批表》（一式四份）", "第 1 步"),
            ("9bf17365", "学生填写个人信息", "第 2 步"),
            ("9bf17365", "经学院意见、学生工作处意见签字及盖章到本楼办理相关退宿手续（清空个人物品，退还宿舍钥匙）", "第 3 步"),
            ("9bf17365", "持一式四份的审批表交到学生公寓办公室（校内 55号楼游泳馆入口二层 201室）（加盖中国传媒大学后勤保障处公章）。", "第 4 步"),
            ("9bf17365", "以上手续完成后，学生公寓办公室通知学生领取（校内 55号楼游泳馆入口二层 201室）审批表，由同学分别交由学生所属学院、学生工作处、财务处存档。", "第 5 步"),
        ],
        pitfalls=[("9bf17365", "学生休学、出国、入伍等特殊原因长时间不住宿舍，均需办理退宿手续。")],
        sources=[{"title": "知识库 · 学生公寓服务中心", "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=9bf17365e1e543f38dc410b2a34e0686", "checked": "2026-10-29"}],
    ),
    make(
        "xiyi-liangshai",
        "洗衣与公共设施（洗烘机 / 吹风机 / 微波炉）",
        ["洗衣机", "洗衣房", "洗烘机", "烘干机", "晾衣服", "吹风机在哪", "微波炉"],
        "后勤保障处",
        [
            ("20250924-c378a260402", "每楼一层值班室提供公共吹风机、微波炉；直饮水机、自助洗烘机及洗鞋设备需扫码使用。", "公共设施"),
            ("9bf17365", "学生公寓为同学们配备了公共电吹风机。设立位置：公寓楼值班室的一层大厅处，每楼层隔层设有一个电吹风处。", "吹风机位置"),
        ],
        sources=[{"title": "后勤服务指南", "url": "https://zchq.cuc.edu.cn/2025/0924/c378a260402/page.htm", "checked": "2026-10-29"}],
    ),
    make(
        "kuaidi-yizhan",
        "快递驿站位置",
        ["快递", "菜鸟驿站", "取快递", "快递柜", "快递地址", "寄快递"],
        "后勤保障处",
        [
            ("1b97d899", "校内菜鸟驿站的位置(办公地点)：", "校内"),
            ("1b97d899", "位于临建1（47号楼东侧，44号楼北侧）。", "校内"),
            ("d940cbae", "梆子井快递收货地址:北京市朝阳区三间房镇中国传媒大学梆子井学公寓，菜鸟驿站在梆子井公寓大门西侧。", "梆子井"),
        ],
        location=("1b97d899", "位于临建1（47号楼东侧，44号楼北侧）。"),
        sources=[{"title": "校园地图（附教学楼名称）", "url": "https://www.cuc.edu.cn/tsxy/list.htm", "checked": "2026-10-29"}],
    ),
]


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

    # 梆子井充电桩补进已有条目
    for it in data["items"]:
        if it["id"] == "zxc-chongdian":
            q = "梆子井公寓有电动车充电桩，具体位置在篮球场西侧。"
            if all(q != s["what"] for s in it["steps"]):
                it["steps"].append({"when": "梆子井", "what": q})
                it["evidence"][f"steps.{len(it['steps'])-1}"] = {"src": "9bf17365", "quote": q}

    # 清掉三条纯噪音的自动条目（文档本身仍在 sources/）
    drop = {"rule-78137397a4", "rule-9bf17365", "rule-d940cbae"}
    before = len(data["items"])
    data["items"] = [i for i in data["items"] if i["id"] not in drop]
    removed = before - len(data["items"])

    data["updated"] = "2026-10-29"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"新增 {added} 条，清理 {removed} 条噪音，总计 {len(data['items'])}")


if __name__ == "__main__":
    main()
