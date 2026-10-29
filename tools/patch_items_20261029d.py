"""给公费医疗条目各步骤补 tags，问哪种情形就只列对应的几步。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"

TAGS = {
    "享受范围": ["范围", "哪些人", "谁能"],
    "起止时间": ["起止", "什么时候享受", "有效期"],
    "就诊": ["就诊", "看病"],
    "转诊": ["转诊"],
    "急诊": ["急诊"],
    "急诊报销": ["急诊", "急诊报销"],
    "住院": ["住院"],
    "报销比例": ["比例", "报销多少", "报多少"],
    "寒暑假": ["寒暑假", "假期", "放假"],
    "报销材料": ["材料", "门诊报销"],
    "住院报销材料": ["住院", "材料"],
    "新生疫苗": ["疫苗", "接种", "打疫苗"],
    "不予报销": ["不报销", "不予报销", "不能报", "哪些不能"],
}


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    item = next(i for i in data["items"] if i["id"] == "xyy-gongfei")
    for s in item["steps"]:
        if s["when"] in TAGS:
            s["tags"] = TAGS[s["when"]]
    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("tagged", sum(1 for s in item["steps"] if s.get("tags")))


if __name__ == "__main__":
    main()
