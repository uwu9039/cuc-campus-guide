"""心理咨询补预约电话；出分条目去掉校历里的「七、」序号残留。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"


def main() -> None:
    data = json.loads(P.read_text(encoding="utf-8"))
    items = {i["id"]: i for i in data["items"]}

    xl = items["xinli-zixun"]
    if not any(s.get("when") == "预约电话" for s in xl["steps"]):
        xl["steps"].append({
            "when": "预约电话",
            "what": "学生心理健康中心 65779209 咨询，心港湾 65783881，主任 65783077",
        })
    xl["evidence"]["steps.{}".format(len(xl["steps"]) - 1)] = {
        "src": "18fe5c7d",
        "quote": "学生心理健康中心：65779209（咨询）、65783881（心港湾）、65783077（主任），23号楼北侧303/心港湾",
    }

    cj = items["jwc-chufen-shijian"]
    old = cj["steps"][1]
    if old.get("when") == "本学期考试周":
        cj["steps"][1] = {
            "when": "2026至2027学年第一学期考试周",
            "what": "考试周为 1 月 4 日至 15 日",
        }
        cj["evidence"]["steps.1"] = {
            "src": "loc-中国传媒大学2026-2027学年校历-406d2e",
            "quote": "七、考试周\n1 月 4 日-15 日",
        }
    if not any(s.get("when") == "实际出分速度" for s in cj["steps"]):
        cj["steps"].append({
            "when": "实际出分速度",
            "what": "期末后出分的速度也很慢，可能要到开学前一周左右才能出完所有课的成绩",
        })
        cj["evidence"]["steps.{}".format(len(cj["steps"]) - 1)] = {
            "src": "loc-新生指南2026-水印版-76f3d8",
            "quote": "期末后出分的速度也很慢，可能要到开学前一周左右才能出完所有课的成绩。",
        }

    P.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("ok", len(items))


if __name__ == "__main__":
    main()
