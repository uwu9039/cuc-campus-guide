"""补齐第二批条目里缺证据的字段：能引原文的补引文，不能的降级成 advisory。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))

PATCH = {
    "xyk-yishi": {
        "drop_pitfall": 0,
        "advisory_add": "「遗失卡查询 / 捡到卡登记」只是找卡与登记通道，不等于挂失；卡确实丢了应先挂失（此条为推断，非原文）",
    },
    "it-renlian": {
        "evidence": {
            "location": {"src": "20231013-c8477a212636", "quote": "使用该账号登录“中传APP”"},
        }
    },
    "it-shensu": {
        "evidence": {
            "location": {"src": "20230516-c8508a208993", "quote": "中国传媒大学APP，点击“我的”模块，点击“登录”"},
        }
    },
    "it-youxiang": {
        "evidence": {
            "materials.0": {"src": "20240813-c8502a241958", "quote": "通过学校统一身份认证后，邮箱会在首次登录时自动开通"},
        }
    },
    "xy-xiaoyou": {
        "evidence": {
            "location": {"src": "20231110-c10268a213617", "quote": "进入中传APP"},
            "materials.0": {"src": "20231110-c10268a213617", "quote": "查询本人在校时的学工号"},
            "steps.1": {"src": "20231110-c10268a213617", "quote": "点击“我的”模块，点击“登录”，输入学号和密码登录"},
        }
    },
}

for it in d["items"]:
    patch = PATCH.get(it["id"])
    if not patch:
        continue
    if "drop_pitfall" in patch:
        idx = patch["drop_pitfall"]
        it["pitfalls"].pop(idx)
        it["evidence"].pop(f"pitfalls.{idx}", None)
        it.setdefault("advisory", []).append(patch["advisory_add"])
    for k, v in (patch.get("evidence") or {}).items():
        it["evidence"][k] = v

p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print("已补齐")
