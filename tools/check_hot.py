"""重点问法回归：把压测里抓到的跑偏问题钉死，防止改关键词后复发。

只测确定性规则（不调用 LLM）：每条问法必须命中指定事项，且不能弹反问。
用法：python tools/check_hot.py    失败时退出码 1
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402

CASES: list[tuple[str, str]] = [
    # 曾经的跑偏点
    ("缓考怎么申请", "xueji-huankao"),
    ("生病了不能考试怎么办", "xueji-huankao"),
    ("勤工助学怎么申请", "xszz-qingong"),
    ("校内勤工助学", "xszz-qingong"),
    ("校园卡怎么充值", "xyk-chongzhi"),
    ("饭卡怎么充值", "xyk-chongzhi"),
    ("校园卡没钱了", "xyk-chongzhi"),
    ("网费怎么交", "it-wangfei"),
    ("校园网网费", "it-wangfei"),
    ("流量超了怎么办", "it-wangfei"),
    # 容易被新条目抢走的旧问法
    ("宿舍电费怎么交", "hq-goudian"),
    ("宿舍电费怎么充值", "hq-goudian"),
    ("校园卡丢了怎么办", "xyk-buka"),
    ("校园卡挂失", "xyk-guashi"),
    ("助学贷款怎么申请", "dk-zhuxue"),
    ("国家助学贷款要带什么", "dk-zhuxue"),
    ("出国留学怎么申请", "liuxue-jiaoliu"),
    ("当兵保留学籍", "xueji-baoliu"),
    # 学信网重复条目清理后
    ("学信网在线验证报告怎么办", "chsi-baogao"),
    ("在线验证报告怎么申请", "chsi-baogao"),
    # 自动制度卡片抢路由
    ("招标采购怎么办", "gzc-zhaobiao"),
    ("招标采购管理流程", "gzc-zhaobiao"),
    # 常用主路径
    ("转专业什么时候能申请", "zhuanzhuanye"),
    ("成绩复核怎么申请", "jwc-chengji-fuhe"),
    ("成绩复议申请单", "jwc-kaoshi"),
    ("四六级报名", "jwc-cet"),
    ("在读证明", "jwc-zaidu"),
    ("宿舍报修找谁", "hq-baoxiu"),
    # 补办毕业/学位证明（"补办"曾把校园卡补卡顶上来）
    ("补办毕业证明", "doc-20240412-c6366a218572"),
    ("毕业证明怎么补", "doc-20240412-c6366a218572"),
]


def main() -> None:
    fails = 0
    for q, want in CASES:
        d = app.answer_question(q)
        got = (d.get("item") or {}).get("id")
        ok = bool(d.get("matched")) and got == want and not d.get("disambiguate")
        if not ok:
            fails += 1
            print(f"  ✗ {q:<24} 期望 {want}  实际 {got}（matched={d.get('matched')}, 反问={bool(d.get('disambiguate'))}）")
    print(f"重点问法 {len(CASES)} 条，通过 {len(CASES) - fails} 条，失败 {fails} 条")
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    main()
