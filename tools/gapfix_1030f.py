"""一次性修掉「选项点了等于没点」的反问，并补户号经验。

有原文分支的，把槽位接到步骤的 if 条件；没有分支依据的，删掉该槽位。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
BACKUP = ROOT / "_review_items" / "items_before_gapfix_1030f.json"

DROP = {
    "xyk-buka": ["reason", "urgent"],
    "jwc-chengjidan": ["purpose"],
    "jwc-buxuanke": ["action"],
    "jwc-tiyu": ["reason"],
    "it-wangluo": ["where"],
    "it-mima": ["case"],
    "it-vpn": ["device"],
    "jwc-zixiu": ["who"],
    "tizhi-miance": ["stage"],
    "zhuanzhuanye": ["type"],
    "jiangxuejin": ["kind"],
    "chsi-baogao": ["kind"],
    "liuxue-jiaoliu": ["who"],
}

WIRE = {
    "xyk-guashi": {"act": {"0": "挂失", "1": "解挂"}},
    "xyk-yishi": {"role": {"0": "丢卡", "1": "捡到卡"}},
    "xyk-yanqi": {"case": {"0": "正常", "1": "预计延期"}},
    "xueji-xiuxue": {"why": {"2": "生病"}},
    "kaoshi-weiji": {"kind": {"0": "考场违纪/作弊", "1": "学术不端"}},
    "hq-goudian": {"dorm": {"0": "校内 / 中蓝公寓", "1": "梆子井公寓", "2": "校内 / 中蓝公寓"}},
    "dk-zhuxue": {"kind": {"0": "生源地贷款", "1": "校园地贷款"}},
    "xueji-huankao": {"why": {"0": "病 / 意外 / 不可抗力", "1": "病 / 意外 / 不可抗力",
                              "2": "病 / 意外 / 不可抗力"}},
}

HUANKAO_STEP = {
    "when": "个人安排",
    "what": "因事原则上不允许缓考",
    "if": {"why": "个人安排"},
}

GOUDIAN_EXPERIENCE = {"text": "户号去宿管老师那里要", "from": "事实"}


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = {it["id"]: it for it in data["items"]}
    if not BACKUP.exists():
        shutil.copy2(ITEMS, BACKUP)

    for iid, keys in DROP.items():
        it = items[iid]
        before = [s["key"] for s in it.get("slots") or []]
        it["slots"] = [s for s in it.get("slots") or [] if s["key"] not in keys]
        after = [s["key"] for s in it.get("slots") or []]
        assert len(after) == len(before) - len(keys), (iid, before, after)

    for iid, plan in WIRE.items():
        it = items[iid]
        assert len(it.get("slots") or []) >= len(plan), (iid, "槽位缺失")
        for key, idx_map in plan.items():
            for idx, val in idx_map.items():
                row = it["steps"][int(idx)]
                cond = row.setdefault("if", {})
                cond[key] = val

    hk = items["xueji-huankao"]
    assert len(hk["steps"]) == 3
    hk["steps"].append(dict(HUANKAO_STEP))
    hk.setdefault("evidence", {})["steps.3"] = {
        "src": "xueji-2025",
        "quote": "因患急病、患大病、突遇意外伤残或因不可抗力导致无法参加必修课程考试的，允许申请缓考。因事原则上不允许缓考。",
    }

    gd = items["hq-goudian"]
    exp = gd.get("experience") or []
    if not any(isinstance(e, dict) and e.get("text") == GOUDIAN_EXPERIENCE["text"] for e in exp):
        exp.append(dict(GOUDIAN_EXPERIENCE))
    gd["experience"] = exp

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("条目数", len(data["items"]))


if __name__ == "__main__":
    main()
