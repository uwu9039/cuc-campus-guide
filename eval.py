"""30 条评测集：跑意图识别准确率 + 追问覆盖率 + 拒答正确率。

用法：
    .venv\\Scripts\\python.exe eval.py            # 本地规则评测（不需要 Key）
    .venv\\Scripts\\python.exe eval.py --baseline # 额外跑 DeepSeek 裸模型对照（需要 Key）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import app as core  # noqa: E402

# (问题, 期望事项 id, 类型)  类型: normal / vague / trap / absent
CASES: list[tuple[str, str | None, str]] = [
    ("校园卡丢了怎么办", "xyk-buka", "normal"),
    ("饭卡坏了刷不出来", "xyk-buka", "normal"),
    ("校园卡消磁了要补办吗", "xyk-buka", "normal"),
    ("我要开成绩单", "jwc-chengjidan", "normal"),
    ("出国用的成绩单怎么弄", "jwc-chengjidan", "normal"),
    ("成绩单要密封盖章", "jwc-chengjidan", "normal"),
    ("开个在读证明", "jwc-zaidu", "normal"),
    ("在读证明需要盖章吗", "jwc-zaidu", "normal"),
    ("选课没选上怎么办", "jwc-buxuanke", "normal"),
    ("想退一门课", "jwc-buxuanke", "normal"),
    ("成绩不对能复核吗", "jwc-kaoshi", "normal"),
    ("想申请自修", "jwc-zixiu", "normal"),
    ("体育课能免修吗", "jwc-tiyu", "normal"),
    ("交换的学分怎么认定", "jwc-zhuanhuan", "normal"),
    ("六级怎么报名", "jwc-cet", "normal"),
    ("校外怎么上知网", "it-vpn", "normal"),
    ("校园网密码忘了", "it-mima", "normal"),
    ("数字校园登不上", "it-mima", "normal"),
    ("宿舍wifi连不上", "it-wangluo", "normal"),
    ("饭卡没了刷不了饭", "xyk-buka", "vague"),
    ("想补个卡", "xyk-buka", "vague"),
    ("四六级成绩单在哪打印", "jwc-cet", "vague"),
    ("我要打印成绩单还要盖章", "jwc-chengjidan", "vague"),
    ("课表上有门课错了", "jwc-buxuanke", "vague"),
    ("我要办个证明", None, "trap"),
    ("卡的事怎么弄", None, "trap"),
    ("毕业证明书丢了能补吗", "doc-20240412-c6366a218572", "normal"),
    ("宿舍能不能换", None, "absent"),
    ("奖学金怎么申请", "jiangxuejin", "normal"),
    ("图书馆能续借吗", None, "absent"),
    ("研究生能换导师吗", None, "absent"),
    ("学历证书电子注册备案表怎么申请", "chsi-baogao", "normal"),
    ("想转学去别的学校", "moe-zhuanxue", "normal"),
]

# (问题, 期望聚焦点逗号串) —— 验证"把问题翻译成能问的字段"这一步
FOCUS_CASES: list[tuple[str, str]] = [
    ("成绩单密封章几点能办", "hours"),
    ("成绩单在哪办", "location"),
    ("校园卡补卡多少钱", "fee"),
    ("补卡带什么", "material"),
    ("体育免修要多久", "duration"),
    ("选课什么时候截止", "window"),
    ("补卡会不会白跑", "pitfalls"),
    ("成绩单办理流程", "overview"),
    ("补卡", "overview"),
    ("成绩单密封章几点的会议室在哪", "hours,location"),
    ("校园网连不上要带什么", "material"),
    ("体育免修多少钱", "fee"),
]

# 同族对照：同一类事项里的近邻问题，必须分别落到不同条目上
# 每组至少两条，验证"互抢"没有把答案抢错
FAMILY_CASES: list[tuple[str, list[tuple[str, str]]]] = [
    ("校园卡四件事", [
        ("校园卡丢了怎么补", "xyk-buka"),
        ("校园卡挂失怎么办", "xyk-guashi"),
        ("捡到一张校园卡交到哪", "xyk-yishi"),
        ("毕业了校园卡还能延期吗", "xyk-yanqi"),
    ]),
    ("统一身份认证三件事", [
        ("统一身份认证密码忘了", "it-mima"),
        ("统一身份认证账号被锁了申诉", "it-shensu"),
        ("统一身份认证账号怎么激活", "it-jihuo"),
    ]),
    ("学籍四件事", [
        ("想休学一年怎么办", "xueji-xiuxue"),
        ("休学后怎么复学", "xueji-fuxue"),
        ("想退学要办什么", "xueji-tuixue"),
        ("保留学籍怎么申请", "xueji-baoliu"),
    ]),
    ("考试三件事", [
        ("考试作弊被抓什么后果", "kaoshi-weiji"),
        ("成绩不对想复核", "jwc-kaoshi"),
        ("四六级怎么报名", "jwc-cet"),
    ]),
    ("体育两件事", [
        ("体育课能免修吗", "jwc-tiyu"),
        ("体测能申请免测吗", "tizhi-miance"),
    ]),
    ("资助四件事", [
        ("助学贷款怎么申请", "dk-zhuxue"),
        ("助学金怎么评", "zxj-guojia"),
        ("奖学金怎么申请", "jiangxuejin"),
        ("入伍学费补偿怎么算", "zb-zizhu"),
    ]),
    ("学信网两件事", [
        ("学历电子注册备案表怎么弄", "chsi-baogao"),
        ("学信网核验一直不过", "chsi-heshi"),
    ]),
    ("学籍流转三件事", [
        ("想转专业", "zhuanzhuanye"),
        ("想转学去别的学校", "moe-zhuanxue"),
        ("休学怎么办", "xueji-xiuxue"),
    ]),
    ("申诉两件事", [
        ("被处分了不服怎么申诉", "moe-shensu"),
        ("账号被锁了怎么申诉", "it-shensu"),
    ]),
    ("证明两件事", [
        ("开在读证明", "jwc-zaidu"),
        ("成绩单密封盖章", "jwc-chengjidan"),
    ]),
]

BASELINE_PROMPT = (    "你是校园办事助手。用户会问一个问题，你要判断它对应哪一类事务。"
    "可选类别：" + "、".join(f"{i['id']}({i['title']})" for i in core.ITEMS) +
    "。若都不匹配，返回 null。"
    '只输出 JSON：{"id": "类别id或null", "confidence": 0到1}'
)


def baseline(text: str) -> str | None:
    try:
        raw = core.ds_chat(
            [{"role": "system", "content": BASELINE_PROMPT}, {"role": "user", "content": text}],
            max_tokens=120,
            json_mode=True,
        )
        return (json.loads(raw).get("id") or None)
    except Exception:  # noqa: BLE001
        return None


def main() -> None:
    use_baseline = "--baseline" in sys.argv and bool(core.api_key())
    rows, hits, asked, refused, refused_ok, base_hits = [], 0, 0, 0, 0, 0

    for q, expect, kind in CASES:
        ranked = core.rank(q)
        top, score = ranked[0]
        matched = score >= core.MATCH_THRESHOLD
        got = top["id"] if matched else None
        ok = got == expect
        hits += ok

        need_ask = matched and bool(top.get("slots"))
        asked += need_ask
        if expect is None:
            refused += 1
            refused_ok += 1 if got is None else 0

        b = baseline(q) if use_baseline else "-"
        if use_baseline and b == expect:
            base_hits += 1

        rows.append((q, expect, got, score, kind, ok, b))

    n = len(CASES)
    print(f"\n{'问题':<26}{'期望':<16}{'实际':<16}{'分':>4}  类型   结果")
    print("-" * 88)
    for q, exp, got, sc, kind, ok, b in rows:
        print(f"{q:<26}{(exp or '拒绝'):<16}{(got or '拒绝'):<16}{sc:>4}  {kind:<6} {'OK' if ok else 'FAIL'}")
    print("-" * 88)
    print(f"识别准确率：{hits}/{n} = {hits / n:.1%}")
    print(f"需追问事项数：{asked}（这些事项在交付前必须补槽位）")
    print(f"拒答正确率：{refused_ok}/{refused}（库里没有的事项必须说没有）")
    if use_baseline:
        print(f"裸模型对照准确率：{base_hits}/{n} = {base_hits / n:.1%}")

    # ---- 聚焦作答：问题是否被正确翻译成「事项 + 问的是哪一面」 ----
    focus_hits = 0
    print(f"\n{'问题':<24}{'期望聚焦':<16}{'实际聚焦':<16}结果")
    print("-" * 74)
    for q, expect_focus in FOCUS_CASES:
        d = core.answer_question(q)
        got_f = ",".join(d.get("focus") or []) if d.get("matched") else "-"
        ok = got_f == expect_focus
        focus_hits += ok
        print(f"{q:<24}{expect_focus:<16}{got_f:<16}{'OK' if ok else 'FAIL'}")
    print("-" * 74)
    print(f"聚焦准确率：{focus_hits}/{len(FOCUS_CASES)} = {focus_hits / len(FOCUS_CASES):.1%}")

    # ---- 同族对照：近邻问题会不会互相抢 ----
    print("\n同族对照（同类事项里的近邻问题必须各归各位）")
    print("-" * 74)
    fam_total = fam_hits = 0
    fam_rows = []
    for family, cases in FAMILY_CASES:
        bad = []
        for q, expect in cases:
            ranked = core.rank(q)
            top, score = ranked[0]
            got = top["id"] if score >= core.MATCH_THRESHOLD else None
            fam_total += 1
            if got == expect:
                fam_hits += 1
            else:
                g = next((i["title"] for i in core.ITEMS if i["id"] == got), got or "拒绝")
                w = next((i["title"] for i in core.ITEMS if i["id"] == expect), expect)
                bad.append(f"{q} → 抢到了「{g}」，应为「{w}」")
        fam_rows.append((family, len(cases), bad))
        print(f"{family:<16}{len(cases) - len(bad)}/{len(cases)} {'OK' if not bad else 'FAIL'}")
        for b in bad:
            print(f"    ✗ {b}")
    print("-" * 74)
    print(f"同族对照准确率：{fam_hits}/{fam_total} = {fam_hits / fam_total:.1%}")

    out = ROOT / "eval-report.md"
    lines = [
        "# 评测报告",
        "",
        f"- 用例数：{n}",
        f"- 规则识别准确率：**{hits / n:.1%}**（{hits}/{n}）",
        f"- 拒答正确率：{refused_ok}/{refused}",
        f"- 事项库：{len(core.ITEMS)} 条，其中已核验 {sum(1 for i in core.ITEMS if i.get('status') == 'verified')} 条",
        "",
        "| 问题 | 期望 | 实际 | 分数 | 类型 | 结果 |",
        "|---|---|---|---|---|---|",
    ]
    for q, exp, got, sc, kind, ok, _b in rows:
        lines.append(f"| {q} | {exp or '拒绝'} | {got or '拒绝'} | {sc} | {kind} | {'OK' if ok else 'FAIL'} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n已写入 {out.name}")


if __name__ == "__main__":
    main()
