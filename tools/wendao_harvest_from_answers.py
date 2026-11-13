"""从问道回答里抽出引用文件（fileId），把库里没有的原文下载下来。

用法：python tools/wendao_harvest_from_answers.py aia-runs/xxx.jsonl [more.jsonl...]
输出：
  sources/wendao/<fileId前8>_<文件名>  新增原文
  sources/wendao/index.json            追加登记
  _wendao_harvest_report.tsv           本次抓取清单（新下载 / 已有 / 失败）
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wendao_download as wd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "sources" / "wendao" / "index.json"
REPORT = ROOT / "_wendao_harvest_report.tsv"

LINK = re.compile(r"\[([^\]]{2,300}?)\]\((https://aihub\.cuc\.edu\.cn/doc/view/fileview\?fileId=([0-9a-f]{32})[^)]*)\)")


def clean(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    return t


def main() -> None:
    rows = []
    seen: dict[str, str] = {}
    for f in sys.argv[1:]:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            for m in LINK.finditer(rec.get("a") or ""):
                fid = m.group(3)
                t = clean(m.group(1))
                # 同一个 fileId 取最短的标题（通常是文件名本身，后面那串是页码/片段）
                if fid not in seen or len(t) < len(seen[fid]):
                    seen[fid] = t
    print(f"回答里出现的不同文件 {len(seen)} 份")

    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    have = {fid for fid, r in index.items() if r.get("path") and (ROOT / r["path"]).exists()}
    print(f"库内已有 {len(have)} 份")

    new = 0
    for i, (fid, title) in enumerate(seen.items(), 1):
        if fid in have:
            rows.append(("已有", fid[:8], title, index[fid].get("name", ""), ""))
            continue
        try:
            url, name = wd.resolve(fid)
            data = wd.get(url, timeout=180)
            if len(data) < 200:
                raise RuntimeError(f"文件过小 {len(data)}")
            mime = "pdf" if data[:4] == b"%PDF" else ("zip" if data[:2] == b"PK" else "bin")
            dest = wd.OUT / f"{fid[:8]}_{name}"
            dest.write_bytes(data)
            index[fid] = {
                "id": fid, "title": title, "url": url,
                "path": str(dest.relative_to(ROOT)), "name": name,
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "kind": mime, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            new += 1
            rows.append(("新增", fid[:8], title, name, str(len(data))))
            print(f"[{i}] 收 {len(data)//1024:>6} KB  {name[:70]}")
        except Exception as e:  # noqa: BLE001
            rows.append(("失败", fid[:8], title, "", str(e)[:160]))
            print(f"[{i}] ✗ {title[:50]}：{e}")
        INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.3)

    REPORT.write_text(
        "状态\tfileId前8\t标题\t文件名\t字节/错误\n" + "\n".join("\t".join(r) for r in rows),
        encoding="utf-8")
    print(f"\n新增 {new} 份；报告 {REPORT.name}")


if __name__ == "__main__":
    main()
