# 检索与判定链优化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把本轮实测确认有收益的五个开关定案为默认值，并补掉三处已知缺陷（同分不定序、复核必跑的等待、候选行元信息不足），全程带回归门。

**Architecture:** 保持「检索四条腿 → RRF 融合 → 模型判分 → 复核 → 两道输出闸 → 组装兜底」的选择式骨架不变，只改默认值、判分口径和调用编排；事实全部来自条目原文，模型不生成新事实。

**Tech Stack:** Python 3.15（`.venv`）、FastAPI/uvicorn 单 worker、SQLite bigram FTS5、DeepSeek `deepseek-flash`（temperature 0.2、json_mode）、无 npm、无 torch/transformers。

**Spec:** 本轮实测证据在 `_review_items/`：`balance_rows.jsonl`（100 题×7 档真实调用）、`token_rows.jsonl` 与 `token_rows_5w.jsonl`（调用次数与 usage）、`frag_stability.jsonl`（判分片配对 21 跑）、`freegen_rows.jsonl`（生成式对照）、`p6_diff.py`/`p6_diff`（档位 diff 工具）。

## 全局约束

- 条目只增不删；新资料只做 upsert/append，重复的不重复接入。
- 改路由主干（`rank`／`_answer_core`／两道闸／融合配额）先请示，批准一条动一条。
- 检索缺口不靠手写别名补，往模型侧提改法并给代价。
- 引用校方原文措辞逐字保留「原则上／暂定／建议」，不得改写成禁止或必须。
- 库里没有的服务不得当作既有服务（无校车）；无官方原文不新造条目。
- 发布前抹去本人身份与本机路径，保留官方公开电话邮箱；第三方令牌绝不进项目目录。
- 本机不装 MSVC 编译器、不装 torch/transformers 之外的重型依赖；py3.15 装不上的东西直接放弃。
- 全量回归（206 题）与浏览器门必须先问再跑。
- 所有 Python 命令用 `./.venv/Scripts/python.exe -X utf8`。
- 本目录不是 git 仓库：计划里的每个任务以「产物落盘＋用户逐条复看」收尾，不写 commit 步骤。

---

## 实测基线（决策依据，全部真实跑，非事后模拟）

100 题带标签集 = 52 道 labeled ＋ 48 道同义不同词 paraphrase。效用 = 答对 − 3×错答。

| 档 | 开关 | 等式 | 准确率 | 覆盖率 | 效用 |
|---|---|---|---|---|---|
| P0 | fusion 裸 | 78＋14＋8 | 84.8% | 92% | 36 |
| P1 | ＋组装 rescue | 78＋15＋7 | 83.9% | 93% | 33 |
| P2 | ＋改写腿 B | 81＋14＋5 | 85.3% | 95% | 39 |
| P3 | 组装改 both | 82＋14＋4 | 85.4% | 96% | 40 |
| P5 | ＋两道闸 | 79＋9＋12 | 89.8% | 88% | 52 |
| P6 | ＋通用做法判分片 | 82＋8＋10 | 91.1% | 90% | 58 |
| P6b | 同码同档重跑 | 81＋9＋10 | 90.0% | 90% | 54 |

尺子分辨率：P6 与 P6b 同题同档 97/100，效用差 4（全部来自一条对↔错翻转）。任何小于 ＋5 效用的单样本增益都算不上结论，必须靠配对复跑或两样本均值。

时长与 token（同时间窗、34 题子集、拦 `ds_chat` 取接口 `usage`）：

| 档 | 并发 1 中位/p90/最大 | 并发 5 中位 | 次调用/题 | tok/题 | 100 题串行 | 100 题 5 并发 |
|---|---|---|---|---|---|---|
| C0 裸 fusion | 6.4s／8.3s／10.0s | 11.6s | 3.62 | 3975 | 656s | 245s |
| C2 定案档 | 9.9s／12.8s／20.0s | 22.7s | 4.79 | 4107 | 1058s | 487s |

C2 的 token 分布：判分 rerank 1.00 次占 40.6%、复核 1.00 次占 34.3%、覆盖面 0.53 次占 9.7%、总括 0.82 次占 6.4%、官方说法 1.00 次占 3.8%（token 极少但占一个完整往返）。字/token 实测 1.62。

---

## Task 1：装闸世界的逐项归因（P7 / P11 / P12 三档）

原 Task 1 只补 rescue 一档。复查发现另有两处边际同样是「装闸前测的」，一并归因；用户 2026-11-07 明令裸词菜单入口不动，所以第四档（P13）取消。

**Files:**
- Modify: `tools/balance_probe.py`（`CONFIGS` 末尾追加三档，已落地）

**Interfaces:**
- Consumes: `do_run()` 的跳过逻辑按 `cfg` 名去重，`balance_rows.jsonl` 逐行 append。
- Produces: `cfg` 为 `P7`／`P11`／`P12` 的各 100 行。

- [x] **Step 1: 追加三档**（已写入 `tools/balance_probe.py`）

```python
    # P7 = 关掉组装 rescue：rescue 唯一的独立测量是装闸前的 -3 效用，装闸后从没归因
    ("P7", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "off", "REWRITE_PRE": "B",
            "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.7}),
    # P11 = 关掉改写腿 B：B 的 +6 是装闸前测的，装闸后（有闸兜着）还值多少不知道
    ("P11", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "OFF",
             "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.7}),
    # P12 = 地板 0.7→0.75 实装：事后扫描给 60 vs 61，但被拦下的题真跑会再走组装 rescue，双重计
    ("P12", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "B",
             "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.75}),
```

- [ ] **Step 2: 跑三档**

Run: `./.venv/Scripts/python.exe -X utf8 -u tools/balance_probe.py run --workers 5`
Expected: 其余档「已有产物，跳过」，只补 P7/P11/P12，各约 11～12 分钟。

- [ ] **Step 3: 两两对比**

Run:
```bash
./.venv/Scripts/python.exe -X utf8 _review_items/p6_diff.py P7 P6
./.venv/Scripts/python.exe -X utf8 _review_items/p6_diff.py P11 P6
./.venv/Scripts/python.exe -X utf8 _review_items/p6_diff.py P12 P6
```
Expected: 每对报出三档计数、效用与逐题档位变化。基准是 P6/P6b 的 58、54（均值 56）。

- [ ] **Step 4: 落判据（写进 `_review_items/归因三档_20261107.md`）**

- rescue（P7 vs P6）：P7 ≥ 56 → 默认 `ASSEMBLE=off`；P7 ≤ 51 → 默认 `rescue`；52～55 → 判噪声，默认 `off`，rescue 降为按需开关。
- 改写腿 B（P11 vs P6）：P11 ≥ 56 → B 在装闸世界无收益，默认 `REWRITE_PRE=off`；≤ 51 → 保留 B；中间 → 保留但注明落在噪声带。
- 地板（P12 vs P6）：P12 效用 > 56 且错答不升 → 抬到 0.75；否则维持 0.7。

- [ ] **Step 5: 交用户逐条复看**

对每个「档位变化」的题，把 `balance_rows.jsonl` 里两档的同题行并排列给用户；用户点头前不进 Task 2。


---

## Task 2：五个开关的默认值定案

**Files:**
- Modify: `app.py:3354`（`RETRIEVAL`）、`app.py:3360`（`DECLINE_REFUSES`）、`app.py:3361`（`MIN_ANSWER_CONF`）、`app.py:3952`（`ASSEMBLE`）、`app.py:3979`（`REWRITE_PRE`）
- Modify: `tools/test_decline_gate.py:4`（docstring 里「默认关着」的措辞）
- Test: `tools/test_decline_gate.py`、`tools/test_assemble.py`、`tools/test_rewrite_pre.py`、`tools/test_bm25_leg.py`、`tools/test_prompt_parts.py`

**Interfaces:**
- Consumes: 无（只改 `os.getenv` 的默认字符串）。
- Produces: 生产进程不带任何环境变量时即跑定案组合；探针仍可 `setattr` 覆盖。

- [ ] **Step 1: 先确认测试不依赖旧默认**

Run: `./.venv/Scripts/python.exe -X utf8 tools/test_decline_gate.py`
Expected: 全绿。该套件用 `app.DECLINE_REFUSES = False/True` 显式赋值，改默认不会破坏它；若出现 FAIL，停手，说明有隐式依赖，先修测试再回来。

- [ ] **Step 2: 改五处默认值**

```python
RETRIEVAL_MODE = str(os.getenv("RETRIEVAL", "fusion")).strip().lower()      # 3354
DECLINE_REFUSES = str(os.getenv("DECLINE_REFUSES", "1")).strip().lower() not in ("0", "false", "off", "no")  # 3360
MIN_ANSWER_CONF = float(os.getenv("MIN_ANSWER_CONF", "0.7") or 0)           # 3361
ASSEMBLE_MODE = str(os.getenv("ASSEMBLE", "rescue")).strip().lower()        # 3952 ← 取 Task 1 的判据，可能是 "off"
REWRITE_PRE = str(os.getenv("REWRITE_PRE", "B")).strip().upper()             # 3979
```

- [ ] **Step 3: 加一行注释说明定案依据**

在 `app.py:3354` 上方补：

```python
# 2026-11-07 定案：100 题带标签集实测 对81.5/错8.5/拒10，效用 81.5-3×8.5=56，
# 裸 fusion 同集为 78/14/8 效用 36。逐项证据见 docs/superpowers/plans/2026-11-07-retrieval-judgment-chain.md
```

- [ ] **Step 4: 五个套件复跑**

Run: `for t in test_decline_gate test_assemble test_rewrite_pre test_bm25_leg test_prompt_parts; do ./.venv/Scripts/python.exe -X utf8 tools/$t.py | tail -1; done`
Expected: 每行末尾 `failed 0`。

- [ ] **Step 5: 单题冒烟（不带环境变量）**

Run: `./.venv/Scripts/python.exe -X utf8 -c "import app; d=app.answer_question('学校医保怎么报', router_llm=True); print(d.get('matched'), (d.get('item') or {}).get('id'), d.get('confidence'), (d.get('model_route') or {}).get('gate'))"`
Expected: 答上、置信 ≥0.7、gate 为 `strong_hit`/`None`/`llm_recheck` 之一，且默认值生效（`app.RETRIEVAL_MODE == 'fusion'`、`app.MIN_ANSWER_CONF == 0.7`）。

- [ ] **Step 6: 交用户复看**

列出「改了哪 5 行、每行的判据出自哪张表」，等用户点头再进 Task 3。

---

## Task 3：同分不定序（模型给分并列时按候选池名次定序）

**Files:**
- Modify: `app.py`（`llm_rerank` 内，约 `3697-3708` 拿到 `best` 之后）
- Create: `tools/test_tie_break.py`

**Interfaces:**
- Consumes: `pool: list[tuple[dict, int]]`（已按融合名次排好）、`scores: dict[str, int]`、`best: dict | None`。
- Produces: `_tie_break(pool, scores, best) -> dict | None`，同分时返回池子里更靠前的那条。

- [ ] **Step 1: 写失败的测试**

```python
# tools/test_tie_break.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

failed = 0
def check(name, ok, detail=""):
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:120])

def it(i, auto):
    return {"id": i, "title": i, "auto": auto}

pool = [(it("a", True), 91), (it("b", False), 88), (it("c", False), 70)]
check("同分取池子靠前", app._tie_break(pool, {"a": 85, "b": 85, "c": 85}, it("c", False))["id"] == "a", "")
check("更高分不被动", app._tie_break(pool, {"a": 80, "b": 90}, it("b", False))["id"] == "b", "")
check("模型没给分原样返回", app._tie_break(pool, {}, it("b", False))["id"] == "b", "")
check("None 原样返回", app._tie_break(pool, {"a": 85}, None) is None, "")
check("并列里含整理条目时按池子顺序，不按类型改写",
      app._tie_break([(it("x", True), 90), (it("y", False), 85)], {"x": 86, "y": 86}, it("y", False))["id"] == "x", "")
print("failed", failed)
sys.exit(1 if failed else 0)
```

- [ ] **Step 2: 跑，确认失败**

Run: `./.venv/Scripts/python.exe -X utf8 tools/test_tie_break.py`
Expected: `AttributeError: module 'app' has no attribute '_tie_break'`。

- [ ] **Step 3: 写最小实现**

在 `app.py` 的 `llm_rerank` 之前插入：

```python
def _tie_break(pool: list[tuple[dict[str, Any], int]], scores: dict[str, int],
               best: dict[str, Any] | None) -> dict[str, Any] | None:
    """模型给分并列时按候选池名次取靠前那条。

    「礼拜天想去图书馆看书能去不」两次跑都是 85 分，一次挑开放时间、一次挑别的条目：
    分数打平时挑哪条全靠采样，同一问句会给出不同答案。池子名次是确定量，用它兜。
    """
    if best is None:
        return None
    bs = scores.get(best["id"])
    if bs is None:
        return best
    rivals = [it for it, _ in pool if scores.get(it["id"]) == bs]
    return rivals[0] if rivals else best
```

并在 `llm_rerank` 里 `best = ITEM_BY_ID.get(best_id) ...` 之后、返回 `score` 之前接一行：

```python
    best = _tie_break(pool, scores, best)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `./.venv/Scripts/python.exe -X utf8 tools/test_tie_break.py`
Expected: `failed 0`。

- [ ] **Step 5: 量效果（同题可复现性）**

Run: `./.venv/Scripts/python.exe -X utf8 -u tools/frag_stability.py`
Expected: 汇总段里「同模式三遍档位不一致」的题数从 4/7 降到 ≤1/7；产物落 `_review_items/frag_stability.jsonl`（覆盖前先在旁边存 `_20261106.jsonl` 副本）。

- [ ] **Step 6: 一次 100 题量测，确认没把错答搬进来**

在 `tools/balance_probe.py` 的 `CONFIGS` 追加 `("P8", 与 P6 同 env)`（此时代码已含定序），跑一档后用
`./.venv/Scripts/python.exe -X utf8 _review_items/p6_diff.py P6 P8` 对比。
Expected: 错答 ≤ P6 两样本最大值 9；同题同档一致率升。达不到就回退本任务的 `llm_rerank` 接线（保留函数不被调用即等于回退）。

---

## Task 4：复核调用的编排（降等待，先扫阈值再定）

**Files:**
- Modify: `app.py:5605` 附近（`rc = llm_recheck(text, top, rc_pool)`）
- Modify: `app.py` 开关区（新增 `RECHECK_SKIP_ABOVE`）
- Create: `tools/test_recheck_skip.py`

**Interfaces:**
- Consumes: 判分给出的 `score`（0～100）。
- Produces: `RECHECK_SKIP_ABOVE: int`（0=一律复核，即现行行为）；跳过时在 `model_route` 里记 `"recheck": "skipped"`。

- [ ] **Step 1: 写失败的测试**

```python
# tools/test_recheck_skip.py：断言「高分跳过、低分照旧」，用桩计数 llm_recheck
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

failed = 0
def check(name, ok, detail=""):
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:120])

app.RETRIEVAL_MODE = "fusion"
app.DECLINE_REFUSES = True
app.MIN_ANSWER_CONF = 0.7
app.api_key = lambda: "x"
HI = '{"scores":{"t1":90},"best":"t1","why":"写到了","rewrites":[],"facets":[]}'
LO = '{"scores":{"t1":60},"best":"t1","why":"沾边","rewrites":[],"facets":[]}'

calls = []
real_recheck = app.llm_recheck
def spy_recheck(*a, **kw):
    calls.append(1)
    return {"verdict": "yes", "best": a[1], "best_answers": "yes", "why": "桩"}
app.llm_recheck = spy_recheck

def ask(payload):
    app.ds_chat = lambda msgs, **kw: payload
    return app.answer_question("宿舍怎么购电", router_llm=True)

calls.clear(); ask(HI)
app.RECHECK_SKIP_ABOVE = 85
ask(HI)
check("高分跳过复核", len(calls) == 0, f"实际调用 {len(calls)}")
calls.clear()
app.RECHECK_SKIP_ABOVE = 85
ask(LO)
check("低分照旧复核", len(calls) == 1, f"实际调用 {len(calls)}")
calls.clear()
app.RECHECK_SKIP_ABOVE = 0
ask(HI)
check("默认值 0 时行为不变", len(calls) == 1, f"实际调用 {len(calls)}")
app.llm_recheck = real_recheck
print("failed", failed)
sys.exit(1 if failed else 0)
```

- [ ] **Step 2: 跑，确认失败**

Run: `./.venv/Scripts/python.exe -X utf8 tools/test_recheck_skip.py`
Expected: `AttributeError: module 'app' has no attribute 'RECHECK_SKIP_ABOVE'`。

- [ ] **Step 3: 加开关并复用现成的 skipped 分支**

开关区（`app.py:3361` 之后）：

```python
RECHECK_SKIP_ABOVE = int(float(os.getenv("RECHECK_SKIP_ABOVE", "0") or 0))  # 判分到此分数就不再看全文复核；0=一律复核
```

`app.py:5601` 那段本来就是「没有可比候选就不多烧一次调用」，把高分跳过并进同一个条件，不要新造状态形状：

```python
        if not rc_ids or (RECHECK_SKIP_ABOVE and score >= RECHECK_SKIP_ABOVE):
            # 候选池空着，或判分已经高到不需要再看全文，都不多烧一次调用
            model_route["recheck"] = {"gate": "skipped"}
        else:
            rc = llm_recheck(text, top, rc_pool)
```

注意连带影响：`skipped` 不在 `rc_signed` 的白名单（`keep/switch/second_look`）里，所以 50~54 那档 near-miss 的「必须复核签字才开门」路径会照样拒答。跳过阈值只允许远高于 54（本任务只扫 75/85/95），低于 60 的阈值不许进默认值。

- [ ] **Step 4: 跑测试确认通过**

Run: `./.venv/Scripts/python.exe -X utf8 tools/test_recheck_skip.py`
Expected: `failed 0`。

- [ ] **Step 5: 三档阈值实测（这一步是决策依据，不许跳）**

在 `tools/balance_probe.py` 追加 `P9a/P9b/P9c`（env 同 P6，分别 `RECHECK_SKIP_ABOVE=75/85/95`），跑三档：

Run: `./.venv/Scripts/python.exe -X utf8 -u tools/balance_probe.py run --workers 5`
Expected: 每档报出 `对/错答/拒答`。同时用 `tools/token_probe.py --workers 1` 量每题中位时长。

- [ ] **Step 6: 落判据**

只接受「错答 ≤ 9 且每题中位时长下降 ≥2s」的阈值进默认值；三个都不满足就把 `RECHECK_SKIP_ABOVE` 留默认 0（等于不改行为），并把这条写进「不做清单」。

---

## Task 5：官方说法调用的结果缓存（省一个往返）

**Files:**
- Modify: `app.py:4001`（`llm_official_phrases`）
- Create: `tools/test_phrase_cache.py`

**Interfaces:**
- Consumes: `norm(text)`（`app.py:736`）。
- Produces: 模块级 `_PHRASE_CACHE: dict[str, list[str]]`，`PHRASE_CACHE` 开关（默认 1）。

- [ ] **Step 1: 写失败的测试**

```python
# tools/test_phrase_cache.py：同一问句两次调用，模型只被问一次
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

failed = 0
def check(name, ok, detail=""):
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:120])

app.api_key = lambda: "x"
n = []
PHRASED = '{"phrases": ["开放时间", "周一～周日"]}'


def fake(msgs, **kw):
    n.append(1)
    return PHRASED


app.ds_chat = fake
app._PHRASE_CACHE.clear()
a1 = app.llm_official_phrases("图书馆周末开吗")
a2 = app.llm_official_phrases("图书馆周末开吗")
check("同问只调一次模型", len(n) == 1, f"实际 {len(n)} 次")
check("第二次拿到同一份说法", a1 == a2, f"{a1} vs {a2}")
app.PHRASE_CACHE = False
app.llm_official_phrases("图书馆周末开吗")
check("关掉开关时每次真调", len(n) == 2, f"实际 {len(n)} 次")
print("failed", failed)
sys.exit(1 if failed else 0)
```

- [ ] **Step 2: 跑，确认失败**

Run: `./.venv/Scripts/python.exe -X utf8 tools/test_phrase_cache.py`
Expected: `AttributeError: module 'app' has no attribute '_PHRASE_CACHE'`。

- [ ] **Step 3: 实现缓存**

`app.py:4001` 之前加：

```python
PHRASE_CACHE = str(os.getenv("PHRASE_CACHE", "1")).strip().lower() not in ("0", "false", "off", "no")
_PHRASE_CACHE: dict[str, list[str]] = {}
_PHRASE_CACHE_MAX = 256
```

`llm_official_phrases` 体内，取 key 与读写：

```python
    key = norm(text)
    if PHRASE_CACHE and key in _PHRASE_CACHE:
        return list(_PHRASE_CACHE[key])
```

拿到 `phrases` 之后、`return phrases` 之前：

```python
    if PHRASE_CACHE:
        if len(_PHRASE_CACHE) >= _PHRASE_CACHE_MAX:
            _PHRASE_CACHE.pop(next(iter(_PHRASE_CACHE)))
        _PHRASE_CACHE[key] = list(phrases)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `./.venv/Scripts/python.exe -X utf8 tools/test_phrase_cache.py`
Expected: `failed 0`。

- [ ] **Step 5: 冒烟**

Run: `./.venv/Scripts/python.exe -X utf8 -c "import app; app.PHRASE_CACHE=True; [app.answer_question('图书馆周末开吗', router_llm=True) for _ in range(2)]; print(len(app._PHRASE_CACHE))"`
Expected: 输出 `1`，两问都成功返回。

---

## Task 6：候选行补元信息（归口、适用对象、文档名）

**Files:**
- Modify: `app.py:3658-3662`（`llm_rerank` 的 menu 行）、`app.py` 组装层 `face_pool`/`llm_face_decide` 的候选行
- Modify: `tools/test_prompt_parts.py`（新增 1c 段）

**Interfaces:**
- Consumes: 条目字段 `dept`、`audience`、`source`（数组，元素含 `title`）。字段名已核对：`xyy-gongfei` 上存在 `audience`/`dept`/`source`。
- Produces: 判分与分面否决的 prompt 里每条候选带「归口｜适用对象｜出自」，模型判「只给入口不算答上」时看得见出处。

- [ ] **Step 1: 写失败的测试**

在 `tools/test_prompt_parts.py` 末尾追加一段（沿用该文件既有的 `check()` 与桩风格）：

```python
# ---- 1c 候选行元信息
seen_prompts = []
app.api_key = lambda: "x"
app.ds_chat = lambda msgs, **kw: (seen_prompts.append(msgs[0]["content"]),
                                 '{"scores":{},"best":null,"why":"","rewrites":[],"facets":[]}')[1]
pool = [({"id": "t1", "title": "学生公费医疗报销", "dept": "校医院", "audience": "全日制本科生",
          "source": [{"title": "学生公费医疗常见问题解答（校医院）"}], "answer": "门诊报销 80%"}, 80)]
app.llm_rerank("医保怎么报销", pool)
p = seen_prompts[-1]
check("候选行归口带标签", "归口 校医院" in p, p[:120])
check("候选行带适用对象", "适用 全日制本科生" in p, p[:120])
check("候选行带文档名", "出自 学生公费医疗常见问题解答" in p, p[:120])
print("failed", failed)
```

- [ ] **Step 2: 跑，确认失败**

Run: `./.venv/Scripts/python.exe -X utf8 tools/test_prompt_parts.py`
Expected: 三条 FAIL（现行候选行只有 id｜标题｜类型｜归口｜摘要，没有适用对象和文档名）。

- [ ] **Step 3: 改候选行**

`app.py:3658-3662` 换成：

```python
    menu = "\n".join(
        f"- {it['id']}｜{it['title'][:50]}｜{'原文摘录' if it.get('auto') else '整理条目'}"
        f"｜归口 {it.get('dept') or '—'}｜适用 {str(it.get('audience') or '—')[:24]}"
        f"｜出自 {str((it.get('source') or [{}])[0].get('title') or '—')[:28]}"
        f"｜{_rerank_hint(it) or '（无摘要）'}"
        for it, _ in pool
    )
```

同形状改组装层的分面否决候选行（`app.py:4143-4146`）：

```python
    menu = "\n".join(
        f"- {it['id']}｜{(it.get('title') or '')[:50]}"
        f"｜归口 {it.get('dept') or '—'}｜适用 {str(it.get('audience') or '—')[:24]}"
        f"｜{_item_full_text(it, 240)}"
        for it, _sc, _legs in pool
    )
```

（`_face_meta_head` 已经带「出自哪份文件」，那处不动。）

- [ ] **Step 1b: 分面否决那条也要测**

在同一测试里续一段，桩掉 `ds_chat` 抓 prompt：

```python
seen2 = []
app.ds_chat = lambda msgs, **kw: (seen2.append(msgs[0]["content"]),
                                  '{"verdict":"no_evidence","id":null,"quote":"","why":""}')[1]
app.llm_face_decide("图书馆周末开吗", {"face": "开放时段"},
                    [({"id": "t2", "title": "图书馆开放时间", "dept": "图书馆",
                       "audience": "全校师生", "answer": "周一～周日 8:00-22:00"}, 1.0, {})])
check("分面候选行带归口", "归口 图书馆" in seen2[-1], seen2[-1][:120])
check("分面候选行带适用对象", "适用 全校师生" in seen2[-1], seen2[-1][:120])
```

- [ ] **Step 4: 跑测试确认通过**

Run: `./.venv/Scripts/python.exe -X utf8 tools/test_prompt_parts.py`
Expected: `failed 0`（原 24 项 + 新 3 项）。

- [ ] **Step 5: 一次 100 题量测**

`CONFIGS` 追加 `("P10", env 同 P6)` 跑一档。Expected: 判死误伤（`p6_diff.py` 报的那一项）从 1～2 降到 0，且错答不升；升了就回退候选行改动，改回原行只保留 `audience`。

- [ ] **Step 6: 量 prompt 变长的代价**

Run: `./.venv/Scripts/python.exe -X utf8 -u tools/token_probe.py --workers 1 --only C2`
Expected: 判分 rerank 的单次输入 tok 从 1396 涨多少要报出来；涨幅超过 15% 就先砍掉「出自」只留适用对象。

---

## Task 7：标签修正（量具本身）

**Files:**
- Modify: `_exp_review_20261104/questions_20261104.json`
- Create: `tools/check_expect.py`

**Interfaces:**
- Produces: 每题 `expect` 覆盖所有「正文逐字能答该题」的条目；后续效用数不再被标签窄误判。

- [ ] **Step 1: 写校验脚本（先只报告，不改数据）**

```python
"""标签体检：模型跨档真实挑中过、但不在 expect 里的条目，以及 expect 指向空正文的条目。

用法：./.venv/Scripts/python.exe -X utf8 tools/check_expect.py report
判读：命中字面重叠≥2 个二字组即列出，是否真能答题必须人工看 quote，不许脚本自动加。
"""
from __future__ import annotations
import io, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = ROOT / "_review_items" / "balance_rows.jsonl"
ITEMS = json.load(io.open(ROOT / "items.json", encoding="utf-8"))["items"]
BY_ID = {it["id"]: it for it in ITEMS}


def body(it):
    t = str(it.get("answer") or "")
    for s in it.get("steps") or []:
        t += str(s.get("what") or "")
    return t


def bigrams(s):
    s = "".join(str(s).split())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def main():
    by_q = {}
    for line in io.open(ROWS, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        by_q.setdefault(r["q"], {"expect": set(r.get("expect") or []), "picked": set()})
        if r.get("got"):
            by_q[r["q"]]["picked"].add(r["got"])
    narrow = empty = 0
    for q, d in by_q.items():
        qb = bigrams(q)
        for i in sorted(d["picked"] - d["expect"]):
            it = BY_ID.get(i)
            if not it:
                continue
            ov = len(qb & bigrams(str(it.get("title") or "") + body(it)))
            if ov >= 2:
                narrow += 1
                print(f"[窄标签] {q} | 漏 {i} | 重叠{ov} | {str(it.get('title'))[:40]}")
        for i in sorted(d["expect"]):
            it = BY_ID.get(i)
            if it and not body(it).strip():
                empty += 1
                print(f"[空正文] {q} | expect {i} | {str(it.get('title'))[:40]}")
    print(f"合计 疑似窄标签 {narrow} 条，疑似空正文 {empty} 条")


if __name__ == "__main__":
    sys.exit(main())
```

报告两栏：`疑似窄标签`（模型两次挑中但不在 expect 的 id，取 `balance_rows.jsonl` 全部档）、`疑似空正文`（expect 指向 `answer` 为空的条目）。

- [ ] **Step 2: 跑报告**

Run: `./.venv/Scripts/python.exe -X utf8 tools/check_expect.py report`
Expected: 至少列出已知的三族——寒假（`pt-024886d2eb` 正文有「八、寒假1月18日开始」）、Adobe 族、图书馆周末族。

- [ ] **Step 3: 逐条对原文后再改 json**

每条改动必须在 `_review_items/标签修正_20261107.md` 里留下「题｜加了哪个 id｜该 id 正文的逐字片段」，用户复看后才写回 json。不许用脚本批量塞 id。

- [ ] **Step 4: 标签改完重算效用（不重跑模型）**

Run: `./.venv/Scripts/python.exe -X utf8 tools/balance_probe.py analyze`
Expected: 各档效用按新标签重算，P6/P6b/P5 的相对差不变或收敛。

---

## Task 8：遗留两处（需要用户拍板，不自动做）

**Files:**
- `app.py` 专名维度过滤（1-B，`rank` 内约 1010-1060）
- 前端渲染 `table_rows`

- [ ] **Step 1:** 长汇编误答残留：列出实测仍错的题号给用户，确认「继续做」还是「收口」，不自行扩大改动面。
- [ ] **Step 2:** 数据表：现状是后端带 `table_rows`、前端不渲染，且 3% 的假表行吃掉 59% 命中。要么前端渲染、要么后端不下发，二选一由用户定；两个都不选就维持现状并记入不做清单。

---

## Task 9：验收门

- [ ] **Step 1: 单测全跑**

两套跑法要分开：绝大多数套件是直接跑的脚本，`test_field_ui*` 走 unittest。

Run:
```bash
for f in tools/test_*.py; do case "$f" in *field_ui*) continue;; esac; ./.venv/Scripts/python.exe -X utf8 "$f" | tail -1; done
./.venv/Scripts/python.exe -m unittest discover -s tools -p "test_field*.py" 2>&1 | tail -3
```
Expected: 前者每行 `failed 0`；后者 `OK`。全量流水线里 `clean_auto_keywords` 固定失败属已知噪声，不在本门内。

- [ ] **Step 2: 100 题定案档两样本**

Run: `./.venv/Scripts/python.exe -X utf8 -u tools/balance_probe.py run --workers 5`
Expected: 对 ≥81、错 ≤9、拒 10±2；两样本同题同档 ≥97/100。

- [ ] **Step 3: 同问三跑一致性（多轮四类集）**

沿用 `_review_items/` 里的多轮脚本与「带历史三跑」口径：历史污染四类集不许出现「独立新问题带历史」。

- [ ] **Step 4: 206 全量回归（先请示）**

Run（获批准后）: `./.venv/Scripts/python.exe -X utf8 tools/eval_questions.py --llm --out aia-runs/local-answers-定案.jsonl`，再用 `tools/review_206_read.py --base <旧基线> --out _review_items/eval_206_read_定案.txt --label 定案` 生成逐条对照文件。
Expected: 逐字段 diff 无意外漂移；用户逐条复看。

---

## Task 10：发布

- [ ] **Step 1:** `./.venv/Scripts/python.exe -X utf8 tools/privacy_scan.py`（命中本机路径与身份必须清零）
- [ ] **Step 2:** 重生成 `items.json.gz` 并核对与明文一致；令牌只走系统 temp，不进项目目录。
- [ ] **Step 3:** 组装自包含上云目录，在包内实测起服务，用 Task 9 Step 2 的子集冒烟。
- [ ] **Step 4:** 魔搭推包（走 git＋令牌；`PartAlreadyExistError` 只能开新会话），发布前 `release-notes.md` 补本轮定案与逐项判据。

---

## Task 11：上下文入口 B＋C（2026-11-07 用户批准，已完成）

用户报的现象：上一问「学生综合服务大厅在哪」，再问「滑雪」被转接到服务大厅。根因不在检索，
在上下文入口——app.py:6181 那块只看「上一遍答得薄不薄」，不看这句是不是续问。

改法与逐条实测见 `_review_items/上下文BC_20261107.md`。四处接线：

- C：`llm_needs_context`（prompt task `ctx_need`，193 tok）主判续问，替掉 `_FOLLOW_RE`/`_GENERIC_TERMS`
  主判；接口失败与规则模式退回词表。
- 删掉 6181 的「答得薄就拼标题重试」整块（`_answer_is_thin`/`_answer_weight` 一起删）。
- 模型判接之后不再叠 `_mentions_other_item`：它按 rank 前 8 名的碎词命中（`办好“`、`周末`）
  否决真续问，改前把「周末呢」推成了博物馆预约表 0.86 错答。
- B：`_answer_core(judge_text=…)`——检索串带上文，判分／复核／逐面／自由生成看用户原话，
  上文另起一行标注，不再拼进题面（自证污染）。

量测：桩测 `tools/test_context_gate.py` 17 条断言全过；多轮四类集 `tools/ctx_probe.py` 8/8 段
符合期望（含「滑雪」两条拒答、「几天能办好」「周末呢」两条接住）。代价每题 +210 tok（约 5%）、
+0.6～1.2s。206 基线不带 context_item，一次判定都不发，不会漂。

未跑：带 context_item 的 206 版（约 20 分钟，要先请示）。

## Task 12：最优搭配——四件候选在最终世界的归因（2026-11-07 进行中）

最终世界 F0 = 定案档（fusion ＋ rescue ＋ 改写腿 B ＋ 两道闸 ＋ 地板 0.7 ＋ judge_generic）
＋ 11-07 的上下文 B＋C。四件候选一律先按「关」装进代码，各自单独打开跑一档：

| 档 | 只动这一个 | 装法 |
|---|---|---|
| F1 | `TIE_BREAK=1` | app.py `_tie_break`，接在 llm_rerank 取 best 之后 |
| F2 | `RECHECK_SKIP_ABOVE=85` | 复核入口并进「候选池空着」那个分支 |
| F3 | `RECHECK_SKIP_ABOVE=95` | 同上，另一档 |
| F4 | `POOL_META=1` | `_pool_row` 给候选重排与逐面裁决两套行各补 归口／适用对象／出处文档名 |
| F5 | `PHRASE_CACHE=1` | 键＝整句归一＋prompt 版本；空结果也存 |

F0 跑两遍（F0a／F0b）当尺子的分辨率，不再是引用昨天的数。

### 判据（跑之前写死）

- 效用 = 答对 − 3×错答；三档计数（对／错答／拒答）；分辨率 = F0a 与 F0b 的逐题差，
  低于这个带的边际一律算噪声，不许叫收益。
- **F1 TIE_BREAK**：效用不低于 F0a／F0b 的低者；且并列发生率 >0（从 balance_rows 的模型分数
  离线数，不另跑）。并列发生率为 0 就直接关——没有病，不吃药。
- **F2/F3 复核跳过**：必须同时满足四条才采纳该阈值——① 错答 ≤ F0 错答＋1；② 拒答不增超过 2；
  ③ 每题中位时长下降 ≥2s；④ 跳过率 ≥30%。三档都不满足就 `RECHECK_SKIP_ABOVE` 留默认 0，
  写进「不做清单」。50~54 那档不受影响（`skipped` 不在签字白名单，测试钉住）。
- **F4 POOL_META**：效用要 ≥ F0 ＋ 分辨率才算真涨；同时 token 涨幅 ≤15%、闸的误伤数不升。
  任何一条不过就关。
- **F5 PHRASE_CACHE**：100 题里没有重复问句，边际天然是零，不配跑一整档；只跑
  ① 单测（同问一次、换问照常）②调用数探针（同一句连问两遍，第二次模型调用数必须少 1）
  ③ 一次 34 题 token 档确认没间接影响。三条过就开。
- 交付物是**开关定案**（哪些开、哪些关、哪些不做），不是一张数据表。

### 实测

（跑完填）

## 失败模式与护栏

| 改动 | 会怎么错 | 护栏 | 期望输出 |
|---|---|---|---|
| 判分片（通用做法算答上） | 把「只给一个入口/网址」也放成答上 | 同一片里写了反向判据；实测 微专业 一条错答转拒答 | 拒答不减错答，错答不增 |
| 两道闸 | 模型偶发判死把本来能答对的题闸掉（实测 1～2 条） | Task 6 补元信息降误伤；判据是误伤数，不看覆盖率单独涨 | 误伤 0～1 |
| 同分定序 | 池子名次本身跑偏时，定序放大错选 | 只在分数严格相等时动；更高分一律不顶 | 同题三跑一致 |
| 高分跳复核 | 把「高分错答」放回（复核正是兜它的） | 必须三档阈值实测过；错答 >9 就回退 | 错答 ≤9 |
| phrase 缓存 | 缓存把旧问句的说法套到新问句 | key 用 `norm(text)` 全句归一；开关默认可关 | 同问省 1 次往返，异问不受影响 |
| 候选行加元信息 | prompt 变长，token 与延迟上涨 | 涨幅 >15% 就砍字段 | 误伤降、token 涨幅已知 |
| 上下文判定 C | 模型判 no 而其实是续问（少接）→ 拒答或答成独立问题 | 用户重问带主体即可恢复；错接看不见、少接看得见，本轮接受后者；接口失败与规则模式退回词表 | 「滑雪」类错接 0 条，四类集 8/8 |
| 判分串 B | 判分时看不到拼好的题面，省略式续问被当成无主语问句 | 上文另起一行标注给模型；压缩出独立问句时判分串就用那一句 | 判分串以用户原话开头，接住的续问照样答对 |

## 明确不做（各带证据）

- 交叉编码器 reranker：权重 1112.5 MB，pyyaml 无 cp315 轮子、源码构建要 MSVC；机制与覆盖率不匹配。
- 覆盖率优先重排全文腿：实测学校医保 15→59、校园卡 1→16，是长度奖励。
- 候选池 14→20：11-04 扩池实验结论是池子越大越容易挑跑偏，收益小风险大。
- 手写别名补词：违反「缺口往模型侧提改法」。
- 裸词菜单入口（`_curated_topic_menu`，app.py:4856，返回点在 4912 写死 `confidence: 0.55, band: "low"`）过闸或改反问：用户 2026-11-07 明令「那条先别改」。留档事实是——它不进 `_answer_core`，两道闸对它无效，两个样本里 `公费医疗报销` 各计一条 0.55 错答（效用比事后扫描低 3 就是这一条），将来要动先过用户。
- 长文档树形导航＋强制叶子原文：2026-11-07 实测丢掉。54 份长规章文档覆盖 67/100 题，只走出 7 个 accept，accept 里 0 条命中期望条目；唯一一道现行答错的题（考试不及格）树接过去仍是错的（落到研究生条款，本科无补考）。代价每题 3 次调用、5 秒。证据与逐条判定见 `_review_items/树形导航实验_20261107.md`。
- 判死转反问卡：闸的误伤只剩 1 条，收益低于成本，排在 Task 6 之后再看数。
- 拒答卡「再问一次」按钮：实测重掷 2/20 救回、0/20 变错，但 9/10 点了仍拒答，用户看到「要点两次」。
- DeepSeek 思考档：8.5× token，净效应≈噪声。

## 上线顺序

Task 1（归因）→ Task 2（默认值）→ Task 3（同分定序）→ Task 6（元信息）→ Task 4（跳复核）→ Task 5（缓存）→ Task 7（标签）→ Task 9（验收门）→ Task 10（发布）。
Task 8 随时插，取决于用户拍板。回滚单位就是五个开关与三处接线，任何一档实测变坏，只退那一处。
