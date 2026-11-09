"""①「改写腿事前并」的三档触发（A/B/C）契约测试。

盯四件事：
  1. REWRITE_PRE=OFF 时一次都不改写，候选池与现在逐条相同（206 基线不漂）。
  2. 改写串必须是官方说法：照抄口语、丢掉主体、短于四字的都丢。
  3. 改写腿只补原句够不着的条目，且最多补 4 个名额——主池的名次顺序不许被改写腿重排。
  4. 三档触发条件各按其言：A 只在 fusion 且规则腿第一名是原文摘录时；
     B 只在 fusion 时每题；C 两种模式每题。改写腿内部不再触发改写（不许递归）。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402
import prompt_parts as pp  # noqa: E402

failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:150])


seen: list[str] = []


def stub(payload=None, boom=False):
    def fake(msgs, **kw):
        prompt = " ".join(m["content"] for m in msgs)
        seen.append(prompt)
        if boom:
            raise RuntimeError("接口挂了")
        if "官方文件里的常见说法" in prompt:
            return json.dumps(payload, ensure_ascii=False)
        return "{}"
    app.ds_chat = fake
    app.api_key = lambda: "test-key"


# ---- 0 片段注册表里得有这块
check("prompt_parts 有 phrase 任务", any(k.startswith("phrase.") for k in pp.FRAGMENTS),
      str([k for k in pp.FRAGMENTS if k.startswith("phrase.")][:6]))
try:
    lay = pp.layout("phrase", {"q": "x"})
    check("phrase 装配固定片在前", bool(lay) and not lay[0].startswith("@"), json.dumps(lay, ensure_ascii=False))
except Exception as e:  # noqa: BLE001
    check("phrase 装配固定片在前", False, repr(e))

# ---- 1 OFF 时不调用
stub({"phrases": ["图书馆开放时间"]})
app.REWRITE_PRE = "OFF"
seen.clear()
r = app.llm_official_phrases("图书馆周末开吗", {})
check("OFF 时不改写", r == [] and not seen, f"调用 {len(seen)} 次 返回 {r}")

# ---- 2 改写串的护栏
app.REWRITE_PRE = "B"
seen.clear()
stub({"phrases": ["图书馆开放时间", "图书馆周末开吗", "体育馆开放时间", "周末", "图书馆开馆时间"]})
r = app.llm_official_phrases("图书馆周末开吗", {})
check("留下的都是官方说法", r == ["图书馆开放时间", "图书馆开馆时间"], json.dumps(r, ensure_ascii=False))
check("改写串有上限", len(r) <= app.REWRITE_PRE_MAX, f"上限 {app.REWRITE_PRE_MAX} 实际 {len(r)}")

stub({"phrases": []}, )
check("模型不给说法时返回空", app.llm_official_phrases("图书馆周末开吗", {}) == [], "")
stub(boom=True)
check("接口异常时返回空不抛", app.llm_official_phrases("图书馆周末开吗", {}) == [], "")

# ---- 3 主池满 14 条时，改写腿换掉尾部的 0 分位，而不是因为没空位而空转
app.RETRIEVAL_MODE = "fusion"
FULL_Q = "想去游个泳什么时候去合适"      # 上一轮实测：这题主池满 14 条，改写腿一个都没进去
ranked = app.rank(FULL_Q)
app.REWRITE_PRE = "OFF"
base_pool = [it["id"] for it, _ in app.rerank_candidates(FULL_Q, ranked, pre_rewrite=False)]
check("样本主池确实是满的 14 条（否则这组断言会空过）", len(base_pool) == app.RERANK_POOL_LIMIT,
      f"实际 {len(base_pool)} 条")
app.REWRITE_PRE = "B"
stub({"phrases": ["游泳何时前往合适"]})
pre_rows = app.rerank_candidates(FULL_Q, ranked)
pre_pool = [it["id"] for it, _ in pre_rows]
check("满池时改写腿仍能把期望条目换进池", "tiyu-yongyongguan" in pre_pool,
      json.dumps({"base有吗": "tiyu-yongyongguan" in base_pool, "并入后有": pre_pool[:12]}, ensure_ascii=False))
check("池子总数不变（不因为补而变大）", len(pre_pool) == len(base_pool),
      f"{len(base_pool)} → {len(pre_pool)}")
check("主池前 8 名原样保住", pre_pool[:app.REWRITE_PRE_KEEP] == base_pool[:app.REWRITE_PRE_KEEP],
      json.dumps(pre_pool[:app.REWRITE_PRE_KEEP], ensure_ascii=False))
lost = [i for i in base_pool if i not in pre_pool]
check("被挤掉的只可能是主池第 9 名以后", set(lost) <= set(base_pool[app.REWRITE_PRE_KEEP:]),
      json.dumps({"挤掉": lost, "尾部": base_pool[app.REWRITE_PRE_KEEP:]}, ensure_ascii=False))
gained = [i for i in pre_pool if i not in base_pool]
check("换进换出的条数相等（池子做替换不是追加）", len(gained) == len(lost) and len(gained) >= 1,
      json.dumps({"换进": gained, "换出": lost}, ensure_ascii=False))
check("替换条数不超上限", len(lost) <= app.REWRITE_PRE_SLOTS,
      f"换掉 {len(lost)} 个 / 上限 {app.REWRITE_PRE_SLOTS}")

# ---- 4 改写腿内部不再触发改写（不许递归）
count = {"n": 0}


def counting(msgs, **kw):
    prompt = " ".join(m["content"] for m in msgs)
    if "官方文件里的常见说法" in prompt:
        count["n"] += 1
        return json.dumps({"phrases": ["图书馆周末开放时间"]}, ensure_ascii=False)
    return "{}"


app.ds_chat = counting
app.REWRITE_PRE = "B"
app.rerank_candidates("图书馆周末开吗", ranked)
check("一次问话只改写一次", count["n"] == 1, f"改写调用 {count['n']} 次")

# ---- 5 三档触发条件
cases = [
    ("OFF", "fusion", True, False), ("OFF", "legacy", True, False),
    ("A", "fusion", True, True), ("A", "fusion", False, False),
    ("A", "legacy", True, False),
    ("B", "fusion", True, True), ("B", "fusion", False, True),
    ("B", "legacy", True, False),
    ("C", "fusion", True, True), ("C", "legacy", True, True), ("C", "legacy", False, True),
]
auto_ranked = [(dict(app.ITEM_BY_ID["pt-560a042fd7"]), 87)]
curated_ranked = [(dict(app.ITEM_BY_ID["xyk-buka"]), 87)]
for mode, ret, top_auto, want in cases:
    app.REWRITE_PRE = mode
    app.RETRIEVAL_MODE = ret
    got = app._rewrite_pre_on(auto_ranked if top_auto else curated_ranked)
    check(f"{mode}/{ret}/第一名{'摘录' if top_auto else '整理'} → 触发={want}", got is want, f"实际 {got}")

app.REWRITE_PRE = "OFF"
app.RETRIEVAL_MODE = "legacy"
print(f"\nfailed {failed}")
sys.exit(1 if failed else 0)
