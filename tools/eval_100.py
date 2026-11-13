"""100 题评测：50 单问（走关闭链路）＋50 复合问（走综合层），逐题落 JSONL 供人工复读。

复合题分两类：plain（两个诉求都说明白）与 vague（口语、含糊、带前提）。
用法：./.venv/Scripts/python.exe -X utf8 -u tools/eval_100.py [singles|compounds|all]
输出：_review_items/eval100.jsonl（每行一题）
"""
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

SINGLES = [
    "图书馆开放时间", "图书馆怎么借书", "校园卡丢了怎么补办", "校园卡怎么挂失", "校园卡怎么充值",
    "补考怎么报名", "重修怎么申请", "缓考怎么办理", "考试作弊有什么处分", "成绩单怎么开",
    "在读证明怎么开", "学位证什么时候发", "毕业需要多少学分", "转专业需要什么条件", "转专业什么时候报名",
    "保研基本条件", "推免综合成绩怎么算", "国家奖学金怎么申请", "国家助学金怎么申请", "助学贷款怎么办理",
    "勤工助学怎么申请", "家庭经济困难认定怎么办理", "体育课免修怎么办理", "体质健康测试免测怎么申请",
    "体测不及格影响毕业吗", "医保怎么报销", "校医院几点开门", "宿舍怎么报修", "宿舍调换怎么申请",
    "宿舍电器使用规定", "宿舍电费怎么交", "校园网怎么办理", "校园网密码忘了怎么办", "快递在哪里取",
    "学校食堂在哪", "游泳馆怎么预约", "体育场馆怎么预约", "心理咨询怎么预约", "心理咨询在哪里",
    "学生证丢了怎么补", "户口迁移怎么办理", "档案在哪里", "四六级报名时间", "竞赛获奖怎么加分",
    "违纪处分怎么申诉", "休学怎么办理", "复学怎么办理", "退学怎么办理", "请假怎么办理", "新生报到流程",
]

COMPOUND_PLAIN = [
    "休学一年再回来，宿舍还能保留吗？学费怎么算？",
    "转专业后，我之前修的课还算数吗？奖学金还能申请吗？",
    "大四体育课还没修完，能正常毕业吗？体测没达标会怎样？",
    "校园卡丢了，体测报名截止了怎么办？",
    "我是贫困生，国家助学金和助学贷款能同时申请吗？",
    "考试作弊被记过，还能转专业吗？还能保研吗？",
    "宿舍电器被查了会处分吗？会影响保研吗？",
    "辅修和微专业能同时修吗？成绩怎么算？",
    "交换生期间成绩怎么认定？还能评奖学金吗？",
    "延期毕业期间宿舍还能住吗？学费怎么交？",
    "四六级没过能毕业吗？能保研吗？",
    "挂科了还能保研吗？补考通过算吗？",
    "转专业后宿舍要换吗？什么时候换？",
    "休学期间还能申请奖学金吗？医保还能用吗？",
    "实习期间宿舍能保留吗？怎么申请？",
    "党员发展期间转专业有影响吗？",
    "推免和支教保研能同时报吗？",
    "体测免测还能评三好吗？能拿奖学金吗？",
    "校园卡冻结了，奖学金还能打进卡里吗？",
    "转专业后图书馆借的书要还吗？借阅权限变吗？",
    "军训没参加能毕业吗？影响评优吗？",
    "学分不够能提前毕业吗？要什么条件？",
    "辅修学位和主修学位能同时拿吗？",
    "交换项目冲突了体测，能补测吗？",
    "退学后还能复学吗？学费退吗？",
]

COMPOUND_VAGUE = [
    "我现在有点饿，附近有啥能吃的？校园卡没钱能先吃吗？",
    "我大二上挂了一门，还想保研，来得及吗？",
    "我是班长，转专业以后这个加分还算吗？",
    "家里突然没钱了，学费交不上，学校能不能先让我上课？",
    "我下学期要去当兵，回来还能接着读吗，宿舍怎么办？",
    "老师说我论文查重没过，会影响我拿学位吗，还有什么补救？",
    "我想休学去创业，一年以后回来还能选原来的课吗？",
    "我体育一直不好，体测年年不过，是不是毕不了业？",
    "我室友天天打游戏到半夜，我能换宿舍吗？会影响我评奖吗？",
    "我上学期申请了助学贷款，这学期转专业了，贷款会断吗？",
    "我护照要过期了，学校能开什么证明吗？",
    "我要出国交换，学分怎么转回来，保研还算吗？",
    "我补考过了，成绩单上会显示补考吗，考研复试看得到吗？",
    "我被记过了，还能入党吗？毕业有影响吗？",
    "我选了微专业，主修课冲突了，能退吗，钱退不退？",
    "我宿舍电费超了，学校会不会直接断电？怎么恢复？",
    "我校园卡丢了，正好要体测，能用身份证吗？",
    "我大四了还没修完体育，能延期毕业吗，要交钱吗？",
    "我转专业没成功，还能申请转学吗？",
    "我申请了国家奖学金，还能同时拿助学金吗？",
    "我体测免测了，体育课还要上吗，学分怎么算？",
    "我要延期毕业，医保还管我吗？宿舍还能住吗？",
    "我大一退过一门课，成绩单上有记录吗，保研看吗？",
    "我交换回来晚了，错过推免报名，还有别的办法吗？",
    "我导师说研究生不能换，但我真的想换，有什么后果？",
]


def brief_answers(d):
    return [{"label": p.get("label"), "text": (p.get("text") or "")[:160]}
            for p in (d.get("answers") or [])]


def run_single(q):
    t0 = time.time()
    d = app.answer_question(q, router_llm=True)
    it = d.get("item") or {}
    return {"mode": "single", "q": q, "sec": round(time.time() - t0, 1),
            "matched": d.get("matched"), "hold": d.get("hold"),
            "item": it.get("id"), "title": (it.get("title") or "")[:40],
            "conf": d.get("confidence"), "answers": brief_answers(d),
            "clarify": (d.get("clarify") or "")[:60]}


def run_compound(q, kind):
    t0 = time.time()
    s = app.synthesize_answer(q)
    sec = round(time.time() - t0, 1)
    if not s:
        return {"mode": "compound", "kind": kind, "q": q, "sec": sec, "synth": None}
    return {"mode": "compound", "kind": kind, "q": q, "sec": sec,
            "conclusion": s["conclusion"],
            "layers": [{"name": l["name"], "text": l["text"]} for l in s["layers"]],
            "boundary": s["boundary"], "warnings": s["warnings"],
            "evidence_count": len(s["evidence"]),
            "evidence_docs": [e["doc"][:30] for e in s["evidence"]]}


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    out = Path("_review_items/eval100.jsonl")
    out.parent.mkdir(exist_ok=True)
    n = 0
    with out.open("w", encoding="utf-8") as fh:
        if which in ("all", "singles"):
            for q in SINGLES:
                try:
                    rec = run_single(q)
                except Exception:  # noqa: BLE001
                    rec = {"mode": "single", "q": q, "error": traceback.format_exc()[-200:]}
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                n += 1
                print(f"[{n}] single {rec.get('matched')} {(rec.get('title') or '')[:18]} | {q}")
        if which in ("all", "compounds"):
            for kind, group in (("plain", COMPOUND_PLAIN), ("vague", COMPOUND_VAGUE)):
                for q in group:
                    try:
                        rec = run_compound(q, kind)
                    except Exception:  # noqa: BLE001
                        rec = {"mode": "compound", "kind": kind, "q": q,
                               "error": traceback.format_exc()[-200:]}
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                    n += 1
                    print(f"[{n}] {kind} {rec.get('sec')}s | {q}")
    print(f"done {n} -> {out}")


if __name__ == "__main__":
    main()
