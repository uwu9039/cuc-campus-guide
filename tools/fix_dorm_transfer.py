"""转宿舍 / 调宿：补「转宿舍」等说法，并把协议里的申请步骤单独拿出来。

原文：
  sources/wendao-text/9bf17365.txt（知识库 · 学生公寓服务中心）
  sources/local/loc-中国传媒大学学生公寓住宿协议书-a9f629.txt
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGREEMENT = "loc-中国传媒大学学生公寓住宿协议书-a9f629"
SERVICE = "9bf17365"

NEW_ALIASES = [
    "转宿舍", "转宿", "转寝室", "转宿舍怎么申请", "转宿舍申请",
    "换宿舍怎么申请", "换宿舍流程", "换宿舍手续", "调宿流程", "调宿申请",
    "宿舍调整流程", "怎么换宿舍", "如何换宿舍", "想换宿舍", "换宿舍找谁",
]


def main() -> None:
    path = ROOT / "items.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    item = next(i for i in data["items"] if i["id"] == "sushe-huansu")
    shutil.copy2(path, path.with_suffix(".json.bak-before-zhuansu"))

    for alias in NEW_ALIASES:
        if alias not in item["aliases"]:
            item["aliases"].append(alias)

    item["steps"] = [
        {"when": "规定",
         "what": "学生不允许私自调换宿舍，发现后本楼管理员会上报给本区管理部做进一步调整"},
        {"when": "申请",
         "what": "乙方因特殊情况确需调整的，须向甲方提出申请，根据实际情况办理调宿"},
        {"when": "协调",
         "what": "到本楼值班室找管理员协调解决"},
    ]
    item["pitfalls"] = ["安排后原则上不再变动"]
    item["evidence"] = {
        "steps.0": {"src": SERVICE,
                    "quote": "学生不允许私自调换宿舍，发现后本楼管理员会上报给本区管理部做进一步调整"},
        "steps.1": {"src": AGREEMENT,
                    "quote": "安排后原则上不再变动，乙方因特殊情况确需调整的，须向甲方提出申请，根据实际情况办理调宿。"},
        "steps.2": {"src": SERVICE, "quote": "到本楼值班室找管理员协调解决"},
        "pitfalls.0": {"src": AGREEMENT, "quote": "安排后原则上不再变动"},
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("已更新 sushe-huansu：别名", len(item["aliases"]), "步骤", len(item["steps"]))


if __name__ == "__main__":
    main()
