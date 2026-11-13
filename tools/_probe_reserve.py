# -*- coding: utf-8 -*-
"""针对仍漏的要点，测「规则短句单独建小池 + 前插合并」能不能捞回来。"""
import sys

sys.path.insert(0, ".")
import app  # noqa: E402


def norm(s):
    return "".join(str(s or "").split()).lower()


def probe(q, queries, tokens, prem=None):
    prem = prem or [q]
    cands = app._synth_candidates(queries, prem, question=q)
    raw = norm(" ".join(str(c["quote"]) for c in cands))
    print("  pool=%d %s" % (len(cands), {t: (norm(t) in raw) for t in tokens}))
    for c in cands:
        hit = [t for t in tokens if norm(t) in norm(c["quote"])]
        if hit:
            print("     ", hit, str(c.get("item_id")), "|", str(c["quote"])[:100])


print("== case2 10000")
for rq in ["国家奖学金 标准 每生每学年 元 金额 发放",
           "本专科生 国家奖学金 每生每年 10000 元",
           "国家奖学金 资助标准 本专科生 研究生"]:
    print(" rule:", rq)
    probe("国家奖学金一年发多少钱", [rq], ["10000", "1万", "本专科"])

print("== case11 8000 (单独池)")
probe("国家奖学金和国家励志奖学金能同时拿吗",
      ["国家奖学金 标准 每生每学年 元 金额 发放"], ["8000"])

print("== case11 8000 (混进主池, 看是否被 cap 挤掉)")
probe("国家奖学金和国家励志奖学金能同时拿吗",
      ["国家奖学金 国家励志奖学金 兼得 规定",
       "国家励志奖学金 评审办法 同时获得",
       "国家奖学金 评审办法 同一学年",
       "国家奖学金 标准 每生每学年 元 金额 发放"], ["8000"])

print("== case12 12元/480")
probe("勤工助学一小时多少钱？一个月最多干多久",
      ["勤工助学 计酬 每月 40 小时 每小时 标准"], ["12元", "480", "40小时"])

print("== case4 160小时")
probe("记过处分会影响入党吗", ["处分 期限 起算 届满 解除 程序"], ["160小时"])

print("== case6 结业")
probe("论文查重没过能拿学位吗", ["查重 重复率 超过 比例 不及格 结业 撤销"], ["结业"])

print("== case5 正式学籍")
probe("休学后医保还能用吗", ["休学 期间 享受 不享受 停发 中止"], ["正式学籍"])
