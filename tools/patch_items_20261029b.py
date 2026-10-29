"""补材料字段与校历步骤标签；改写前先核对引文确实存在。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"

SRC_FILES = {
    "loc-2026级本科生入学须知-校本部-2cdd30": ROOT / "sources/local/loc-2026级本科生入学须知-校本部-2cdd30.txt",
    "013d48a620": ROOT / "sources/extra/013d48a620.txt",
    "f917f291": ROOT / "sources/wendao-text/f917f291.txt",
}


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def ev(src: str, quote: str) -> dict:
    text = squash(SRC_FILES[src].read_text(encoding="utf-8"))
    assert squash(quote) in text, f"引文不存在：{src} :: {quote[:40]}"
    return {"src": src, "quote": quote}


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = data["items"]
    by_id = {i["id"]: i for i in items}

    hukou = by_id["xinsheng-hukou"]
    hukou["materials"] = [
        {"name": "户口迁移证（籍贯、出生地填到市（区）、县一级，加盖“户口专用”章）"},
        {"name": "《录取通知书》（迁移证姓名须与录取通知书一致）"},
    ]
    hukou["evidence"]["materials.0"] = ev(
        "loc-2026级本科生入学须知-校本部-2cdd30",
        "户口迁移证中的各项内容（包括姓名、民族、出生日期、身份证号码、籍贯、出生地、原住址等）必须填写清楚、完整",
    )
    hukou["evidence"]["materials.1"] = ev(
        "loc-2026级本科生入学须知-校本部-2cdd30",
        "户口迁移证上的姓名必须与《录取通知书》中的姓名一致。",
    )

    med = by_id["xyy-gongfei"]
    med["materials"] = [
        {"name": "校园卡或学生证、身份证（就诊、报销时出示）"},
        *med["materials"],
        {"name": "急诊报销：诊断证明、急诊病历、处方（收据或诊断证明加盖急诊诊断专用章）"},
        {"name": "住院报销：身份证复印件、本人建行卡复印件"},
    ]
    med["evidence"]["materials.3"] = ev(
        "f917f291", "就诊时请携带校园卡或学生证、身份证等有效证件"
    )
    med["evidence"]["materials.4"] = ev(
        "013d48a620",
        "急诊报销时，须携带诊断证明、急诊病历、处方并在收据或诊断证明上加盖急诊诊断专用章，方予报销。",
    )
    med["evidence"]["materials.5"] = ev(
        "f917f291", "身份证复印、本人建行卡复印"
    )

    tags = {
        "第一学期": ["学期", "开学"],
        "学生报到": ["报到", "开学"],
        "上课": ["上课", "开学"],
        "本科新生军训": ["军训"],
        "秋季学期活动": ["读书周", "运动会"],
        "考试与寒假": ["放假", "寒假", "考试"],
        "第二学期": ["学期", "开学"],
        "第二学期节点": ["读书周", "运动会"],
        "夏季学期及暑假": ["放假", "暑假"],
        "上课时间": ["上课时间", "作息"],
        "节假日": ["放假", "节假日", "国庆", "元旦"],
    }
    for s in by_id["xiaoli-2026-2027"]["steps"]:
        if s["when"] in tags:
            s["tags"] = tags[s["when"]]

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("patched", len(items))


if __name__ == "__main__":
    main()
