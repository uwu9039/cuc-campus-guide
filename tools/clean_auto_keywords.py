"""清掉自动制度卡片里与人工条目重名的宽泛关键词。

自动卡片（auto=True）的关键词是从文档标题里切的，像「招标采购管理」
会盖过人工整理的「招标采购管理（教职工）」。规则：只要自动卡片的关键词
与任一人工条目的标题/别名互相包含，就删掉这个关键词；卡片本身仍可凭
完整标题检索到。

用法：
    python tools/clean_auto_keywords.py          # 清理并写回
    python tools/clean_auto_keywords.py --check  # 只检查，有冲突退出 1
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUNCT = re.compile(r"[\s，。！？、；：\"'“”‘’（）()【】\[\]—…·.,!?;:]")


def norm(s: str) -> str:
    return PUNCT.sub("", (s or "").lower())


def main() -> None:
    path = ROOT / "items.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    hand = [i for i in data["items"] if not i.get("auto")]
    phrases = {
        norm(x)
        for i in hand
        for x in [i["title"], *i.get("aliases", [])]
        if len(norm(x)) >= 2
    }

    removed = []
    for item in data["items"]:
        if not item.get("auto"):
            continue
        keep = []
        for kw in item.get("keywords", []):
            n = norm(kw)
            clash = len(n) >= 2 and any(n in p or p in n for p in phrases)
            if clash:
                removed.append((item["id"], item["title"], kw))
            else:
                keep.append(kw)
        item["keywords"] = keep

    if "--check" in sys.argv:
        if removed:
            for iid, title, kw in removed[:20]:
                print(f"  ✗ {iid} {title[:20]} 关键词「{kw}」与人工条目重名")
            print(f"✗ {len(removed)} 个自动卡片关键词抢路由")
            sys.exit(1)
        print("✓ 自动卡片关键词与人工条目无重名")
        return

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"清理 {len(removed)} 个关键词")
    for iid, title, kw in removed:
        print(f"  - {iid} {title[:24]} ← {kw}")


if __name__ == "__main__":
    main()
