"""综合层三段式的确定性断言（不调模型，跑一遍就知道接线对不对）。

用法：.venv/Scripts/python.exe -X utf8 -u tools/check_synth_20261110.py
退出码 0 = 全过；1 = 有断言失败。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"  ({detail})" if detail else ""))
    if not ok:
        FAILS.append(name)


TUIMIAN = app.ITEM_BY_ID["tuimian-tiaojian"]
LABEL_TM = app.src_label(TUIMIAN["evidence"]["answer"]["src"])["label"]
QUOTE_TM = TUIMIAN["evidence"]["answer"]["quote"]
LABEL_BS = ("中国传媒大学关于专业学位博士研究生攻读学位期间取得创新成果的规定")


def t1_audience() -> None:
    print("[1] 人群过滤：保研题要放行《推免办法》，别的题仍挡研究生文件")
    check("保研题收《推免办法》",
          app._evidence_allowed(LABEL_TM, "四六级没过能毕业吗？能保研吗？"), LABEL_TM[:24])
    check("转专业题仍挡《博士创新成果规定》",
          not app._evidence_allowed(LABEL_BS, "转专业后综合测评怎么算？"))
    check("研究生题收研究生文件",
          app._evidence_allowed(LABEL_BS, "博士研究生创新成果要求"))


def t2_enum() -> None:
    print("[2] 闭集枚举：认得出「共 5 项」，也认得出「被截断」")
    info = app._closed_enum(QUOTE_TM) or {}
    check("推免第十一条 = 穷尽枚举 5 项",
          info.get("closed") is True and info.get("count") == 5,
          json.dumps(info, ensure_ascii=False)[:90])
    check("枚举项含「品行表现」",
          any("品行" in x for x in (info.get("items") or [])))
    trunc = "第三条 国家奖学金的基本申请条件： （一）具有中华人民共和国国籍； （二）热爱社会主义祖国； （三）遵守宪法和法律； （四）诚实守信； （五）在校"
    ti = app._closed_enum(trunc) or {}
    check("截断引文不算穷尽（closed=False）", ti.get("closed") is False, str(ti.get("count")))
    op = "具备下列条件之一者：（一）甲；（二）乙；（三）丙，以及其他情形。"
    oi = app._closed_enum(op) or {}
    check("带「等」不算穷尽", oi.get("closed") is False)
    check("两项不算枚举", app._closed_enum("（一）甲；（二）乙。") is None)


def t3_candidate() -> None:
    print("[3] 取证保底：保研题候选池里必须有资格条款，且标 must")
    q = "挂科了还能保研吗？补考通过算吗？"
    cands = app._synth_candidates(["推免 基本条件 挂科", "补考成绩 推免 排名"],
                                  ["推免资格是否要求无挂科"], question=q)
    hit = [c for c in cands if "推荐免试攻读" in c["quote"] and "基本条件" in c["quote"]]
    check("候选池含推免资格条款", bool(hit), f"{len(cands)} 条候选")
    check("该条被标 must（模型漏挑也会带上）", any(c.get("must") for c in hit))
    # 上限放宽到 80：按事名补检（_entity_rows）每题会多带 8～20 条同事实条款，
    # 池子从 48 涨到 60～70；再多就说明检索失控了。
    check("候选池没有超员太多（≤80）", len(cands) <= 80, str(len(cands)))


def t4_gate() -> None:
    print("[4] 闸门：没挂穷尽枚举的否定句要降级，挂上的要保留")
    ev = [
        {"doc": "a", "quote": "奖学金按月发放到校园银行卡中。", "enum": None},
        {"doc": "b", "quote": QUOTE_TM, "enum": app._closed_enum(QUOTE_TM)},
    ]
    bad = "第十一条共五项，未列四六级 [1]。"
    out, warn = app._gate_negatives(bad, ev)
    check("挂错条款的否定句被降级", "未列" not in out and bool(warn), out[:26])
    good = "第 [2] 条共 5 项，未列四六级 [2]。"
    out2, warn2 = app._gate_negatives(good, ev)
    check("挂在穷尽枚举上的否定句保留", "未列四六级" in out2 and not warn2)
    # 没挂引用同样要降级
    out3, warn3 = app._gate_negatives("条款未要求四六级。", ev)
    check("没挂引用的否定句被降级", "未要求" not in out3 and bool(warn3))


def t5_layers() -> None:
    print("[5] 裁决结构：新格式（premises+verdict）与老格式（layers）都认")
    new = {"premises": [{"name": "资格", "verdict": "未列", "text": "共五项 [2]"},
                        {"name": "成绩", "verdict": "inferable", "text": "据 [1]（推断）"}]}
    layers = app._premise_layers(new)
    check("新格式解析出 2 层", len(layers) == 2)
    check("verdict 归一成 not_listed", layers[0]["verdict"] == "not_listed", layers[0]["verdict"])
    old = {"layers": [{"name": "资格", "text": "…"}, {"name": "成绩", "text": "…"}]}
    check("老格式仍能解析", len(app._premise_layers(old)) == 2)


def t6_menu() -> None:
    print("[6] 菜单：枚举条款要带「共 N 项」摘要，不能只剩前 160 字")
    ev = [{"doc": LABEL_TM, "quote": QUOTE_TM, "enum": app._closed_enum(QUOTE_TM)}]
    menu = app._ev_menu(ev)
    check("菜单含穷尽枚举标注", "穷尽枚举" in menu and "共 5 项" in menu)
    check("菜单含最后一项（品行表现）", "品行表现" in menu)


def t7_robust() -> None:
    print("[7] 闸门只删越界句、不毁整段；元陈述与原文照抄不算裸句")
    ev = [
        {"doc": "a", "quote": "奖学金按月发放到学生校园银行卡中。", "enum": None},
        {"doc": "b", "quote": QUOTE_TM, "enum": app._closed_enum(QUOTE_TM)},
    ]
    mixed = "第十一条共五项，未列四六级 [1]；补考按 60 分计入 GPA [1]。"
    out, _warn = app._gate_negatives(mixed, ev)
    check("越界句删掉、后半句保留", "未列" not in out and "60 分" in out, out[:34])
    only_bad = "第十一条共五项，未列四六级 [1]。"
    out2, _warn2 = app._gate_negatives(only_bad, ev, fallback="兜底句。")
    check("整段被删空时给兜底句（不留空结论）", out2 == "兜底句。", out2)
    meta = "证据里没有禁止同时报名的条款，缺这一口径。"
    out3, warn3 = app._gate_negatives(meta, ev)
    check("元陈述不被闸门动", out3 == meta and not warn3)
    txt = ("证据中无条款规定转专业后借阅权限变化。"
           "学生休学、出国、入伍等特殊原因长时间不住宿舍，均需办理退宿手续。"
           "转专业后排名按比例换算。")
    warns = app._synth_cite_check(
        txt, 2,
        evidence=[{"quote": "学生休学、出国、入伍等特殊原因长时间不住宿舍，均需办理退宿手续。"}])
    check("元陈述与原文照抄都放过，只报真正裸句",
          len(warns) == 1 and "排名按比例换算" in warns[0], str(warns))


def t8_conservative() -> None:
    print("[8] 保守识别：换了几种说法也要能认出「在打太极」")
    dodges = [
        "证据里没有写直接条款。",
        "证据中没有任何条款直接规定挂科能否保研，缺的是资格条件对不及格记录的规则。",
        "证据里没有直接规定校园卡冻结后能否入账，缺这一口径。",
        "因此无法回答二者能否同时修读。",
    ]
    answers = [
        "第 [1] 条共 5 项，未列四六级 [1]。",
        "转专业后排名按比例换算，辅修成绩单独记载 [2]。",
        "证据里没有禁止同时报名的条款 [3]。",
    ]
    check("四种打太极写法都认得出", all(app._looks_conservative(x) for x in dodges))
    check("正常作答不误判", not any(app._looks_conservative(x) for x in answers))


def t9_conclusion() -> None:
    print("[9] 头尾一致：分层答出来了，结论不许继续打太极")
    layers = [
        {"name": "资格", "verdict": "not_listed", "text": "第[1]条第十一条共5项，未列「挂科」[1]。"},
        {"name": "成绩", "verdict": "direct", "text": "不及格课程补考通过后以 60 分计入智育测评[5]。"},
        {"name": "边界", "verdict": "missing", "text": "缺补考记录的排名口径。"},
    ]
    bad = "证据里没有直接规定挂科能否保研，缺这一口径。"
    out = app._fix_conclusion(bad, layers)
    check("保守结论被分层改写", "未列" in out and "60 分" in out, out[:40])
    check("没有分层的回答层内容", "缺补考记录" not in out)
    ok = "第[1]条共5项未列挂科，补考按 60 分计入智育测评[5]。"
    check("本来就是正常结论就不动", app._fix_conclusion(ok, layers) == ok)
    dead = [{"name": "x", "verdict": "missing", "text": "缺规则。"}]
    check("分层全是 missing 时保持原结论", app._fix_conclusion(bad, dead) == bad)


if __name__ == "__main__":
    for fn in (t1_audience, t2_enum, t3_candidate, t4_gate, t5_layers, t6_menu, t7_robust,
               t8_conservative, t9_conclusion):
        fn()
    print()
    if FAILS:
        print(f"FAILED {len(FAILS)}: " + "；".join(FAILS))
        sys.exit(1)
    print("ALL PASS")
