"""判读器：把「作答 / 诚实拒答 / 含糊」判成可统计的三类，并做确定性的越界检查。

判读（对每条回答，模型只看回答本身，不看是改前还是改后，也不看库里有没有）：
  answered  给出了对问题的实质回答（能/不能、未列某条件、未发现禁止条款、按 X 办理）
  refused   只说明证据里没有、缺哪条规则，没给结论
  mixed     一半给出结论、一半说没有
越界检查（确定性，不调模型）：回答里出现的数字、条款号，在证据里找不到 → 记为 overclaim。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/_judge30.py <jsonl> [jsonl...]
输出：_review_items/judged_<原文件名>
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

PROMPT = (
    "你在给校园问答系统的回答做归类。只根据回答本身判断，不要去猜学校有没有规定。\n"
    "三类：\n"
    "· answered：对问题给出了实质回答——能/不能、要/不要、未列某项条件、"
    "未发现禁止性条款、按某流程办理、具体数字/口径。\n"
    "· refused：只说明证据里没有、缺哪条规则，通篇没给可用的结论。\n"
    "· mixed：一部分问到了、另一部分只说明没有。\n"
    '只输出 JSON：{"kind": "answered|refused|mixed", "why": "不超过 30 字"}'
)

NUM = re.compile(r"\d+(?:\.\d+)?")
ARTICLE = re.compile(r"第\s*[一二三四五六七八九十百零〇\d]{1,4}\s*条")
YEAR = re.compile(r"(?:19|20)\d{2}\s*年?|〔(?:19|20)\d{2}〕")
CITE = re.compile(r"\[\d+\]")   # 引用编号 [11] 不是数字主张，别当成越界
_CN = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
       "六": 6, "七": 7, "八": 8, "九": 9}


def _art_num(s: str) -> int | None:
    """把「第十一条」「第 11 条」都折成 11，免得中文/阿拉伯写法不同就算越界。"""
    body = re.sub(r"[第条\s]", "", s)
    if not body:
        return None
    if body.isdigit():
        return int(body)
    if body == "十":
        return 10
    if body.startswith("十"):
        return 10 + _CN.get(body[1:], 0)
    if "十" in body:
        a, _, b = body.partition("十")
        return _CN.get(a, 0) * 10 + (_CN.get(b, 0) if b else 0)
    return _CN.get(body)


def ask_judge(q: str, answer: str) -> dict:
    try:
        raw = app.ds_chat([{"role": "system", "content": PROMPT},
                           {"role": "user", "content": f"问题：{q}\n\n回答：\n{answer}"}],
                          max_tokens=120, json_mode=True)
        data = json.loads(raw) or {}
        kind = str(data.get("kind") or "").strip().lower()
        return {"kind": kind if kind in ("answered", "refused", "mixed") else "mixed",
                "why": str(data.get("why") or "")[:40]}
    except Exception as e:  # noqa: BLE001
        return {"kind": "judge_error", "why": repr(e)[:40]}


def overclaim(rec: dict) -> list[str]:
    """回答里的数字/条款号，证据里一个都找不到 → 越界。

    改前的记录只存了出处文件名（没有引文全文），做不了这个检查，返回空表并跳过，
    免得把每条数字都算成越界。

    年份（2021 年、〔2025〕号）和「第 X 条」先剔掉再比：前者多半出现在文件名里，
    后者由 ARTICLE 单独查；混在一起只会把「中传教字〔2021〕210号」当成越界。
    """
    if not rec.get("evidence"):
        return []
    text = " ".join([rec.get("conclusion") or ""]
                    + [x.get("text") or "" for x in (rec.get("layers") or [])]
                    + [rec.get("boundary") or ""])
    hay = " ".join((e.get("quote") or "") for e in (rec.get("evidence") or []))
    bad: list[str] = []
    hay_arts = {n for n in (_art_num(a) for a in ARTICLE.findall(hay)) if n}
    for a in ARTICLE.findall(text):
        n = _art_num(a)
        if n and n not in hay_arts:
            bad.append(a)
    rest = YEAR.sub(" ", ARTICLE.sub(" ", CITE.sub(" ", text)))
    hay_rest = YEAR.sub(" ", hay)
    # 问句里本来就有的数字（「体测 80 分吗」）不算越界：回答复述问题不算自己编数字
    asked = set(NUM.findall(rec.get("q") or ""))
    for n in NUM.findall(rest):
        if len(n) >= 2 and n not in hay_rest and n not in asked:
            bad.append(n)
    return sorted(set(bad))[:4]


def main() -> None:
    for name in sys.argv[1:]:
        src = ROOT / "_review_items" / name
        rows = [json.loads(line) for line in src.open(encoding="utf-8")]
        out = ROOT / "_review_items" / f"judged_{name}"
        with out.open("w", encoding="utf-8") as fh:
            for i, rec in enumerate(rows, 1):
                if not rec.get("conclusion"):
                    rec["judge"] = {"kind": "no_output", "why": ""}
                else:
                    answer = rec["conclusion"] + "\n" + "\n".join(
                        f"- {x.get('name')}：{x.get('text')}" for x in rec.get("layers") or [])
                    rec["judge"] = ask_judge(rec["q"], answer[:1800])
                rec["overclaim"] = overclaim(rec)
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                print(f"[{i}/{len(rows)}] {rec['judge']['kind']:<10} "
                      f"越界={rec['overclaim']} | {rec['q'][:26]}")
        print("done ->", out)


if __name__ == "__main__":
    main()
