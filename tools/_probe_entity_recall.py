"""探针：把问句里的「事名」单独检索，能不能把漏掉的条款捞回池子。

动机（金标准诊断）：『转专业以后宿舍要换吗』的候选池里一条调宿条款都没有——
plan 给的短句被「转专业」占满，宿舍相关的条目排不进来。
本探针只测「按事名再检索一次」能捞回多少，不改代码。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

# 校园域的事名表（第一批，只覆盖金标准/评测里出现过的）
NOUNS = [
    "转专业", "宿舍", "调宿", "换宿舍", "医保", "公费医疗", "奖学金", "国家奖学金",
    "励志奖学金", "助学金", "助学贷款", "图书馆", "借阅", "校园卡", "挂失", "补卡",
    "论文", "查重", "学位", "毕业论文", "体测", "免测", "免修", "体育课", "处分", "记过",
    "入党", "党员", "学费", "学分", "考试", "补考", "重修", "缓考", "休学", "复学",
    "退学", "毕业", "延期毕业", "推免", "保研", "勤工助学", "综测", "综合测评",
]

CASES = [
    ("转专业以后宿舍要换吗", ["调宿", "宿舍"]),
    ("论文查重没过能拿学位吗", ["30%", "结业", "撤销"]),
    ("国家奖学金一年发多少钱", ["8000", "10000"]),
    ("延期毕业还能住宿舍吗", ["不提供住宿"]),
    ("校园卡丢了还能进图书馆吗", ["补卡", "20 元", "借阅权限"]),
]


def main() -> None:
    for q, needles in CASES:
        base = app._synth_candidates(
            app._synth_plan(q, {})[1] or app._synth_plan(q, {})[0],
            app._synth_plan(q, {})[0], question=q)
        base_hay = " ".join(c["quote"] for c in base).replace(" ", "")
        nouns = [n for n in NOUNS if n in q]
        extra: list[str] = []
        for n in nouns:
            for it, _s in app.bm25_hits(n, k=15):
                for _k, v in (it.get("evidence") or {}).items():
                    for one in app._ev_items(v):
                        quote = str((one or {}).get("quote") or "").strip()
                        if len(app._mn(quote)) < 12:
                            continue
                        if quote not in extra:
                            extra.append(quote)
        extra_hay = " ".join(extra).replace(" ", "")
        print("=" * 74)
        print(q, "| 事名:", nouns)
        for nd in needles:
            print(f"   {nd:10} 原池={'有' if nd in base_hay else '无'} "
                  f"加事名检索={'有' if nd in extra_hay else '无'}")
        print(f"   原池 {len(base)} 条；事名补检 {len(extra)} 条")


if __name__ == "__main__":
    main()
