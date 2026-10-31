"""按人工逐条复核结论修正图书馆批次条目。

repair: answer/title 改为原文中的干净子串（写完再校验引文仍是原文子串）
drop:   纯客套、附件目录、断句残片、重复条目
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
SRC_DIRS = [ROOT / "sources", ROOT / "sources" / "ilib-text"]

REPAIR = {
    "pt-842c5af9b6": "如果需要暂时离开座位，可在触屏机再次刷卡进行暂离操作，系统将为您保留规定的时长。",
    "pt-8ef5e2ebdd": "步骤1：选择预约结束时间，然后选择空间(注：现场选座的开始时间均为当前时间）。",
    "pt-926a440130": "在本次预约未结束时可以续座此座位，可在触屏机再次刷卡进行续座操作。",
    "pt-a267e899c7": "通过自选可以选择位于几楼、什么空间的座位。",
    "pt-bd5104bbd5": "读者在图书馆微信公众号“中传大阅城”上预约，在预约时间前30分钟后25分钟内通过图书馆的入馆闸机进入会自动签到。",
    "pt-e1ed59b4e7": "读者可以通过关注中国传媒大学企业号，接收座位预约的信息提示。",
    "pt-4f9c529e74": "如未到结束时间需要结束此次使用，可在触屏机再次刷卡进行结束使用操作，在结束时间到达后离开，无需进行任何操作。",
    "pt-800b407908": "直接点击您所需要预约的时长按钮即可。",
    "pt-e7d299a0dc": "选座：此环节是指没有网上预约的读者在触屏机上可以选座。",
    "pt-3b961fa56c": "凡具有图书馆阅览权限的本校师生（需通过答题闯关）预约使用。",
    "pt-0c46fde97f": "图书采访馆员定期上传图书征订目录，读者可按期浏览征订目录，勾选图书进行荐购。",
    "pt-11641f202c": "如果您推荐的是中文图书，在芸悦读服务开启期间，建议您先使用芸悦读服务，符合条件且无馆藏的图书可快递到您手中，借阅更便捷。",
    "pt-5ec881852e": "“芸台购”平台在芸悦读服务未开启期间可以作为图书荐购平台，为读者提供新书一站式浏览和荐购服务，此渠道还可以第一时间了解荐购图书有无馆藏，无馆藏的图书可以一键点击推荐购买。",
    "pt-79754deb2c": "图书馆6层为库本文献阅览区，门口设有图书监测系统，本层图书资料只能在本层阅览。",
    "pt-1faba07566": "本征集启事自发布之日起，持续有效。",
    "pt-465341c234": "非本校知名学者出版的信息传播类学科代表性成果。",
}

DROP = {
    "pt-aac2d03d64",  # 尊敬的读者，您好！
    "pt-60c5a7a898",  # 感谢您对图书馆的关心…（客套）
    "pt-a5a7adf026",  # 欢迎本科同学选修本课程（宣传语）
    "pt-a68480c4b6",  # 附件目录 + 正文粘连
    "pt-0ce5bea5f3",  # 邮寄地址+个人手机+附件正文粘连
    "pt-2a4aa6f397",  # 表格竖线残留，且与 lib-kaifang-shijian 重复
    "pt-c856679e5b",  # （2）点击微服务中的“芸悦读”；
    "pt-cc7903725c",  # （3）在个人中心里使用校园网账号密码进行登录。
    "pt-87cdda44db",  # 课程字段粘连，lib-jiangzuo 已覆盖
    "pt-ac65cc15a5",  # “空间签到使用签到空间…”标题与正文粘连
    "pt-2211db8174",  # 与 pt-1ba18246a5 重复
    "pt-cbc1b4444b",  # “学生也可自主申报…”残片
    "pt-ab9b3805a2",  # “参照《体育评价…》。”残片
    "pt-fd6b958de9",  # “学生参与级美育活动”原文断字，语义不全
}

MANUAL = {
    "lib-jieyue": {
        "replace": [("只续一次", "")],
        "append_steps": [
            {"when": "开通权限（网页）", "what": "也可在图书馆主页 lib.cuc.edu.cn 点击入馆教育系统，答题闯关成功后开通借阅权限。", "where": "图书馆主页"},
        ],
    },
    "lib-daping-yuelan": {
        "append_steps": [
            {"when": "使用范围", "what": "大屏阅览区资源有限，仅供师生视频剪辑、创作、写论文、编程等专业用途，请勿用于玩游戏、看小视频等娱乐用途。"},
        ],
    },
}


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def load_sources() -> dict[str, str]:
    out = {}
    for d in SRC_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*.txt"):
            out[str(p)] = squash(p.read_text(encoding="utf-8", errors="ignore"))
    return out


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = data["items"]
    sources = load_sources()

    repaired = dropped = 0
    by_id = {i["id"]: i for i in items}
    for iid, new in REPAIR.items():
        item = by_id[iid]
        ev = item.setdefault("evidence", {}).setdefault("answer", {})
        src = ev.get("src") or ""
        pool = [t for path, t in sources.items() if Path(path).stem == src]
        joined = "\n".join(pool)
        if squash(new) not in joined:
            raise SystemExit(f"引文不在原文：{iid} {src}")
        item["answer"] = new
        item["title"] = new[:40].rstrip("，。；")
        ev["quote"] = new
        repaired += 1

    kept = []
    for item in items:
        if item["id"] in DROP:
            dropped += 1
            continue
        kept.append(item)
    data["items"] = kept

    by2 = {i["id"]: i for i in kept}
    for iid, rule in MANUAL.items():
        item = by2[iid]
        for old, new in rule.get("replace", []):
            for step in item.get("steps") or []:
                if old in (step.get("what") or ""):
                    step["what"] = step["what"].replace(old, new).strip("，。； ")
        for step in rule.get("append_steps", []):
            if not any((s.get("what") or "") == step["what"] for s in item.get("steps") or []):
                item.setdefault("steps", []).append(step)

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"修复 {repaired} 条，删除 {dropped} 条，手工更新 {len(MANUAL)} 条，总数 {len(kept)}")


if __name__ == "__main__":
    main()
