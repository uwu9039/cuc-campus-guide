"""同一批题分别跑「改前基线」和「改后链路」，落盘供判读与对比。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/_run30.py before     # 读 _app_before.py（改前快照）
  ./.venv/Scripts/python.exe -X utf8 -u tools/_run30.py after      # 读 app.py（现链路）
输出：_review_items/compound30_before.jsonl / compound30_after.jsonl
"""
import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from compound30_20261110 import QUESTIONS  # noqa: E402
MODULE = "compound30_20261110"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "after"
    mod_name = sys.argv[2] if len(sys.argv) > 2 else MODULE
    rep = sys.argv[3] if len(sys.argv) > 3 else ""
    qs = __import__(mod_name).QUESTIONS
    tag = "controls6" if "controls6" in mod_name else "compound30"
    if which == "before":
        core = load_module(ROOT / "_app_before.py", "app_before")
        out = ROOT / f"_review_items/{tag}_before{rep}.jsonl"
    else:
        import app as core  # noqa: F401
        out = ROOT / f"_review_items/{tag}_after{rep}.jsonl"

    with out.open("w", encoding="utf-8") as fh:
        for n, (kind, q) in enumerate(qs, 1):
            t0 = time.time()
            try:
                s = core.synthesize_answer(q)
            except Exception:  # noqa: BLE001
                fh.write(json.dumps({"type": kind, "q": q,
                                     "error": traceback.format_exc()[-200:]},
                                    ensure_ascii=False) + "\n")
                print(f"[{n}] ERR {q}")
                continue
            sec = round(time.time() - t0, 1)
            if not s:
                rec = {"type": kind, "q": q, "sec": sec, "synth": None}
            else:
                rec = {
                    "type": kind, "q": q, "sec": sec,
                    "conclusion": s["conclusion"],
                    "layers": [{"name": x.get("name"), "verdict": x.get("verdict"),
                                "text": x.get("text")} for x in s["layers"]],
                    "boundary": s.get("boundary") or "",
                    "warnings": s.get("warnings") or [],
                    "verdicts": s.get("verdicts"),
                    "evidence": [{"doc": e.get("doc", "")[:40],
                                  "quote": (e.get("quote") or "")[:400],
                                  "closed": bool((e.get("enum") or {}).get("closed")),
                                  "count": (e.get("enum") or {}).get("count"),
                                  "must": bool(e.get("must"))} for e in s["evidence"]],
                }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{n}] {sec}s {kind} | {q[:30]}")
    print("done ->", out)


if __name__ == "__main__":
    main()
