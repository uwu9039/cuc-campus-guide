"""修 6 处路由冲突：校园卡泛词、宿舍 WiFi 故障、辅修问法、电话速查预置问法。

- lib-zizhu-dayin：打印条不再把「校园卡」当关键词，避免所有校园卡问法先落到打印
- xinsheng-xiaoyuanka：新生办卡条让出「补卡」语义，补卡交给 xyk-buka
- xyk-buka：接收「校园卡消磁 / 坏了 / 补卡」等具体说法
- it-wangluo：接收宿舍 WiFi 断连类说法，连不上归故障条、怎么连归宿舍覆盖条
- bumen-dianhua：电话速查是陈述性清单，按 kind=notice 不预设「怎么办」问法

用法：python tools/fix_routing_1031.py [--dry-run]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
BACKUP = ROOT / "_review_items" / "items_before_routing_1031.json"
LOG = ROOT / "_review_items" / "applied_routing_1031.txt"


def add_unique(seq: list[str], extra: list[str]) -> list[str]:
    out = list(seq)
    for x in extra:
        if x not in out:
            out.append(x)
    return out


def main() -> None:
    dry = "--dry-run" in sys.argv
    original = ITEMS.read_text(encoding="utf-8")
    data = json.loads(original)
    idx = {it["id"]: it for it in data["items"]}
    log: list[str] = []

    def show(tag: str, it: dict) -> None:
        log.append(f"{tag}  {it['id']}  {it['title']}")
        log.append(f"     aliases : {it.get('aliases')}")
        log.append(f"     keywords: {it.get('keywords')}")
        log.append(f"     kind    : {it.get('kind')}")

    it = idx["lib-zizhu-dayin"]
    show("BEFORE", it)
    it["keywords"] = [k for k in it.get("keywords", []) if k != "校园卡"]
    show("AFTER ", it)

    it = idx["xinsheng-xiaoyuanka"]
    show("BEFORE", it)
    it["aliases"] = [a for a in it.get("aliases", []) if a != "校园卡补卡"]
    it["keywords"] = [k for k in it.get("keywords", []) if k != "补卡"]
    show("AFTER ", it)

    it = idx["xyk-buka"]
    show("BEFORE", it)
    it["aliases"] = add_unique(it.get("aliases", []), [
        "校园卡补卡", "校园卡消磁", "卡片消磁", "校园卡坏了", "校园卡怎么补",
    ])
    show("AFTER ", it)

    it = idx["it-wangluo"]
    show("BEFORE", it)
    it["aliases"] = add_unique(it.get("aliases", []), [
        "宿舍wifi连不上", "宿舍无线网连不上", "宿舍网连不上",
        "宿舍wifi断了", "宿舍无线网断了",
    ])
    show("AFTER ", it)

    it = idx["bumen-dianhua"]
    show("BEFORE", it)
    it["kind"] = "notice"
    show("AFTER ", it)

    text = "\n".join(log)
    print(text)
    if dry:
        return

    if not BACKUP.exists():
        BACKUP.write_text(original, encoding="utf-8")
    tmp = ITEMS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, ITEMS)
    LOG.write_text(text + "\n", encoding="utf-8")
    print(f"\n已写回，备份 {BACKUP.relative_to(ROOT)}，日志 {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
