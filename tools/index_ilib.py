"""为 sources/ilib-text 建索引，供 build_clause_items 逐句成条。

索引键必须等于正文文件名（不含 .txt），否则 text_path 找不到文件。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
TEXT_DIR = SRC / "ilib-text"
INDEX = SRC / "ilib-index.json"

# 部门职责页是「完成领导交办的其他工作」这类套话，切出来只会是噪声；
# 联系方式另行整理成结构化条目。
SKIP = {"馆领导", "综合办公室", "借阅服务部", "资源建设部", "特藏建设部",
        "学科服务部", "空间与技术服务部", "教材建设中心", "空间布局"}


def main() -> None:
    out: dict[str, dict] = {}
    for p in sorted(TEXT_DIR.glob("*.txt")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        title = lines[0].strip() if lines else p.stem
        url = ""
        for ln in lines[:8]:
            m = re.match(r"接口[:：]\s*(\S+)", ln) or re.match(r"来源[:：]\s*(\S+)", ln)
            if m:
                url = m.group(1)
                if "/get-classify" in url:
                    break
        body = text.split("\n\n", 1)[1] if "\n\n" in text else text
        label = title.split("·", 1)[-1].strip()
        out[p.stem] = {
            "url": url,
            "title": title,
            "chars": len(body.strip()),
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()[:16],
            "kind": "ilib",
            "skip": label in SKIP,
        }
    INDEX.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"索引 {len(out)} 条，正文 {sum(v['chars'] for v in out.values())} 字")


if __name__ == "__main__":
    main()
