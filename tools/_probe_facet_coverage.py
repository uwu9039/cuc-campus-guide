"""查「问到的面没答到」有多普遍：问句里的面词，答案里是否出现。

这是用户最在意的那类毛病：库里有这一面（比如转专业后宿舍不作调整），答案只答了流程、没提宿舍。
只读，不写任何东西。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

# (问句, 必须出现的面词)  —— 面词取问句里的关键名词，不是泛词
CASES = [
    ("转专业以后宿舍要换吗", ["宿舍"]),
    ("转专业了图书馆借的书要还吗", ["借", "还"]),
    ("转专业以后班长加分还算吗", ["加分"]),
    ("转专业会影响保研吗", ["推免", "保研"]),
    ("转专业要交学费吗", ["学费"]),
    ("转专业之后学籍怎么处理", ["学籍"]),
    ("休学期间还能申请奖学金吗", ["奖学金"]),
    ("休学后医保还能用吗", ["医保"]),
    ("国家奖学金对体测有要求吗", ["体测"]),
    ("国家奖学金一年发多少钱", ["元", "万"]),
    ("勤工助学一个月能挣多少", ["元"]),
    ("助学金和助学贷款能同时申请吗", ["助学贷款"]),
    ("体测免测了还要上体育课吗", ["体育课"]),
    ("宿舍电费超了会断电吗", ["断"]),
    ("校园卡丢了还能进图书馆吗", ["图书馆"]),
    ("考试作弊会被记入档案吗", ["档案"]),
    ("记过处分会影响入党吗", ["入党", "党员"]),
    ("论文查重没过能拿学位吗", ["学位"]),
    ("延期毕业还能住宿舍吗", ["宿舍"]),
    ("退学之后学费退吗", ["学费"]),
]


def main() -> None:
    miss = 0
    for q, keys in CASES:
        d = app.answer_question(q, router_llm=False)
        blob = " ".join(str(a.get("text") or "") for a in (d.get("answers") or []))
        blob += " " + " ".join(str(x.get("quote") or "") for x in (d.get("quotes") or []))
        title = (d.get("item") or {}).get("title") or ""
        hit = [k for k in keys if k in blob]
        ok = len(hit) == len(keys)
        miss += not ok
        print(f"{'覆盖' if ok else '缺面'} | {q[:20]:22} | 条目={title[:22]:24} | "
              f"缺={[k for k in keys if k not in blob]}")
    print(f"\n{miss}/{len(CASES)} 题没把问的那一面答出来")


if __name__ == "__main__":
    main()
