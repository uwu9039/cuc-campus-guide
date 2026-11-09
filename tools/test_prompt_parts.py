"""分片底座的回归：注册表装配顺序、版本标记、缓存 key，以及 app 里不许再留内联文本。

盯四件事：
  1. 固定片段必须排在动态候选之前，否则前缀缓存永远命不中。
  2. 任一片文本改动，parts_version 必须变（缓存靠它作废）。
  3. 缓存 key 只认 task＋版本＋归一化问句：大小写与空格不影响，task 不同不影响彼此。
  4. 三处模型调用的固定文本只能存在注册表里一份，app.py 不许再内联，防止改一处漏两处。
  5. 判分口径这类要单独试撤的文本必须自成一片，且不得掺候选内容。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import prompt_parts as pp  # noqa: E402

failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:130])


STATE_A = {"menu": "- a｜校园卡补卡｜整理条目｜—｜服务台办理", "facet_menu": "整体流程、所需材料",
           "menu_mode": False}
STATE_B = {"menu": "- b｜学校医保｜整理条目｜校医院｜参保与缴费", "facet_menu": "整体流程、所需材料",
           "menu_mode": False}

# 1. 前缀一致：候选清单之前的文本必须逐字节相同
full_a = pp.assemble("rerank", STATE_A)
full_b = pp.assemble("rerank", STATE_B)
cut = full_a.index(STATE_A["menu"])
check("候选之前的前缀与候选无关", full_a[:cut] == full_b[:full_b.index(STATE_B["menu"])],
      f"前缀 {cut} 字")
check("候选清单出现在前缀之后", full_a.startswith(full_a[:cut]) and STATE_A["menu"] in full_a[cut:],
      "")

# 菜单裁决版与普通版只差判分片
menu_s = pp.assemble("rerank", {**STATE_A, "menu_mode": True})
check("menu_mode 只换判分片", menu_s.count("判断要求：") == 1
      and "用户这一次只输入了一个词" in menu_s
      and "只看关键词重合不算回答" not in menu_s, "")

# 1b. 通用做法判分片（2026-11-06 A 案）：独立一片、只进普通裁决、不进菜单版
check("判分片在注册表里独立成键", "rerank.judge_generic" in pp.FRAGMENTS,
      str([k for k in pp.FRAGMENTS if "generic" in k]))
lay_menu = pp.layout("rerank", {**STATE_A, "menu_mode": True})
check("通用做法片只进普通判分，不进菜单判分",
      "rerank.judge_generic" in pp.layout("rerank", STATE_A) and "rerank.judge_generic" not in lay_menu,
      json.dumps(pp.layout("rerank", STATE_A), ensure_ascii=False))
gen = pp.assemble("rerank", STATE_A)
check("片子里同时给了正反两头", "算答上" in gen and "没有可执行的做法" in gen, gen[-500:])
check("这片是纯固定文本，不掺候选", STATE_A["menu"] not in pp.FRAGMENTS["rerank.judge_generic"]
      and pp.FRAGMENTS["rerank.judge_generic"].strip(), repr(pp.FRAGMENTS["rerank.judge_generic"][:60]))

route = pp.assemble("route", STATE_A)
free = pp.assemble("free_answer", STATE_A)
check("三个 task 各自成套", "候选id或null" in route and "confidence" in free
      and "scores" not in route, "")

# 2. 版本随文本变
v0 = pp.parts_version("rerank", STATE_A)
pp.FRAGMENTS["rerank.judge"] += " "
v1 = pp.parts_version("rerank", STATE_A)
pp.FRAGMENTS["rerank.judge"] = pp.FRAGMENTS["rerank.judge"][:-1]
check("改一片文本版本就变", v0 != v1 and pp.parts_version("rerank", STATE_A) == v0,
      f"{v0} -> {v1}")

# 3. 缓存 key
k1 = pp.cache_key("rerank", STATE_A, "PS 激活")
k2 = pp.cache_key("rerank", STATE_A, "ps激活")
k3 = pp.cache_key("route", STATE_A, "ps激活")
check("归一化后同问句同 key", k1 == k2, f"{k1} {k2}")
check("换 task 换 key", k1 != k3, "")
pp.FRAGMENTS["rerank.rewrite"] += " "
k4 = pp.cache_key("rerank", STATE_A, "ps激活")
pp.FRAGMENTS["rerank.rewrite"] = pp.FRAGMENTS["rerank.rewrite"][:-1]
check("文本一改旧 key 立刻失效", k4 != k1, f"{k1} -> {k4}")

# 4. app.py 不许再内联固定片段
src = (ROOT / "app.py").read_text(encoding="utf-8")
inline = [
    "只看关键词重合不算回答",
    "用词贴近学校文件",
    "不用不是A而是B",
    "只能从这些说法里选，最多两个",
]
left = [s for s in inline if s in src]
check("app.py 里的内联片段已搬空", not left, f"残留 {left}")
check("app.py 已引用注册表", "import prompt_parts" in src and "assemble(" in src, "")

# 5. 顶部总括：不合格的一律不用，回退条目标题
import app  # noqa: E402

calls = []
app.api_key = lambda: "test-key"      # 桩：不依赖本机有没有配 Key


def stub(payload, boom=False):
    def fake(msgs, **kw):
        calls.append(msgs[0]["content"])
        if boom:
            raise RuntimeError("接口挂了")
        return payload
    app.ds_chat = fake


def head(payload, text="食堂有哪些", body="学校共有 8 个餐厅", llm_on=True, status=None,
         boom=False):
    stub(payload, boom)
    return app.llm_headline(text, body, llm_on, status)


check("正常总括照用", head('{"headline": "食堂与餐厅一览"}') == "食堂与餐厅一览", "")
check("正文里有的数字可以留",
      head('{"headline": "8 个餐厅都能刷卡"}') == "8 个餐厅都能刷卡", "")
check("正文里没有的数字就丢", head('{"headline": "9 个餐厅都能刷卡"}') is None, "")
check("电话样式就算正文里有也丢",
      head('{"headline": "打 400-168-6616 咨询"}',
           body="遇到问题拨打 400-168-6616") is None, "")
check("五位以上数字就丢", head('{"headline": "最高 12000 元"}', body="最高 12000 元") is None, "")
check("带网址就丢", head('{"headline": "去 software.cuc.edu.cn 下载"}') is None, "")
check("带问号就丢", head('{"headline": "食堂在哪吃？"}') is None, "")
check("超长就丢", head('{"headline": "这" * 30}') is None, "")
check("空串不用", head('{"headline": ""}') is None, "")

n_before = len(calls)
got = head('{"headline": "行"}', llm_on=False)
check("模型关了就不发调用", got is None and len(calls) == n_before, f"调用数 {len(calls)}")

st: dict = {}
got = head('{"headline": "行"}', boom=True, status=st)
check("接口挂了只记不响", got is None and bool(st.get("headline_error")), str(st)[:80])

got = head('{"headline": "随便"}')
check("总括看得到问句和正文", got == "随便" and "问句：食堂有哪些" in calls[-1]
      and "答复正文：" in calls[-1], calls[-1][:60] if calls else "")

st2: dict = {}
got = head('{"headline": "9 个餐厅"}', status=st2)
check("被丢掉的总括留了记录", got is None and st2.get("headline_dropped") == "9 个餐厅", str(st2)[:80])

print("failed", failed)
sys.exit(1 if failed else 0)
