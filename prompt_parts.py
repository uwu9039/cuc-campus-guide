"""Prompt 片段注册表：三处模型调用的 system 文本在这里按 task 装配。

拆片的原则是「固定文本进注册表、动态内容留在调用方」：候选清单、问面表这类
每次都变的字符串由 app 渲染后放进 state，本模块只负责拼装顺序和版本标记。
顺序即成本顺序——固定片段在前，动态片段在后，DeepSeek 的前缀缓存才有命中机会。

版本用于缓存 key：任何一片文本改动，parts_version 就变，旧缓存自动作废。
"""
from __future__ import annotations

import hashlib
import unicodedata
from typing import Any, Callable

VERSION = "1"

# ---------------------------------------------------------------- 固定片段

FRAGMENTS: dict[str, str] = {
    # task=rerank
    "rerank.role": "用户在问校园办事的事。下面是从知识库检索出的候选条目。\n",
    "rerank.judge": (
        "判断要求：\n"
        "- 给每条打 0～100：100=直接回答了用户问的这件事；60=沾边但缺关键信息；0=无关。\n"
        "- 只看关键词重合不算回答。用户问 A，条目讲 B，就是 0 分。\n"
        "- 同一件事既有「整理条目」又有「原文摘录」时，优先选整理条目：它分好了费用、时间、材料，"
        "能回答具体问法；原文摘录只在整理条目完全没覆盖这件事时才选。\n"
        "- best 只能填真正回答了问题的条目 id；都没有就填 null，不要硬选。\n"
    ),
    # 通用做法判分片（2026-11-06 A 案）：学校文件常把一族东西写成一条通用做法，
    # 「ps激活」被判成没答上就是因为原文只写 Adobe 不点名 PS。这片自成一键，要撤就撤这片。
    "rerank.judge_generic": (
        "通用做法与点名条目：\n"
        "- 学校文件常把一族东西写成一条通用做法。例如正版软件只写「Adobe 如何激活登录」，"
        "不会逐个点名 PS、PR、AI。用户问这一族里的某个具体产品或子情形时，"
        "只要这条通用做法就是该校对它唯一的官方做法，就算答上，不要因为原文没点名那个产品就打低分。\n"
        "- 反过来说，条目只给了一个入口、网址或「到平台上查」，没有可执行的做法，"
        "而用户问的是怎么办，这不算答上。\n"
        "- 按前一条判分时，在 why 里写明你用的是通用做法。\n"
    ),
    "rerank.judge_menu": (
        "判断要求：\n"
        "- 用户这一次只输入了一个词，没有说想问哪一面。你要判的是：候选里有没有一条，"
        "它的主题就是用户输入的这个东西本身（它的整体介绍、办理指南、开放安排都算）。\n"
        "- 有就选它，给 70～100：主题对上的原文摘录照样算数，不要因为它是摘录、"
        "或者没回答某个具体问题就不选。\n"
        "- 几条都在讲同一个东西时，选覆盖最全、最像总览的那一条，不要选只讲一个细节的片段。\n"
        "- 给每条打 0～100：主题就是这个词的这件事 80 以上；沾边但讲的是另一件事的片段 40 以下；无关 0。\n"
        "- 只有所有候选都跟用户输入的词不相干时，best 才填 null。\n"
    ),
    "rerank.facet_head": "问面要求：再判断用户这句话问的是这件事的哪一面，",
    "rerank.facet_tail": (
        "。\n"
        "- 问的是整体怎么办、或这些都对不上，facets 返回空数组。\n"
        "- 用户问的是资格准入（能不能办、什么人能办、什么情况下不行）就选「条件与限制」。\n"
    ),
    "rerank.rewrite": (
        "改写要求：把用户问题翻译成 3～5 种校园里的常用说法，口语改书面、补全省略，"
        "一条只表达一个意思，不超过 24 个字。\n"
    ),
    "rerank.json": (
        '只输出 JSON：{"scores": {"条目id": 分数}, "best": "条目id或null", '
        '"why": "一句话理由", "rewrites": ["…"], "facets": ["…"]}'
    ),
    # task=route
    "route.role": (
        "用户在问校园办事的事。请先把他的问题翻译成 3～5 种校园里常用的说法，"
        "再判断下列候选中是否有唯一最匹配的一项。\n"
    ),
    "route.translate": (
        "翻译要求：\n"
        "- 口语改书面，同义替换，补全省略的主语或对象。\n"
        "- 用词贴近学校文件，例如「宿舍换一下」→「调宿申请」「转宿舍办理」；"
        "「卡丢了」→「校园卡挂失」；「成绩单在哪开」→「成绩证明办理」。\n"
        "- 一条只表达一个意思，不超过 24 个字，不要重复原句。\n"
    ),
    "route.pick": "判断要求：只挑一个候选；都不匹配 id 返回 null；不要解释。\n",
    "route.json": '只输出 JSON：{"rewrites": ["…"], "id": "候选id或null"}',
    # task=free_answer
    "free.role": (
        "你在帮中国传媒大学的同学回答校园办事问题。事项库里没有收录这个问题，"
        "请直接给出可执行的回答：先给结论，再说该去哪个部门问。\n"
        "要求：\n"
    ),
    "free.rules": (
        "- 电话、金额、截止日期、文件条款号这类细节，不确定就不要写出具体数值，改成以学校最新通知为准。\n"
        "- 不要声称这是学校原文，不要伪造文件名、链接或文号。\n"
        "- 不要列要准备的材料清单。你没有官方来源，写出来的清单就是编的；"
        "用户问要带什么，就说这一项要问哪个部门，让他按部门答复准备。\n"
        "- 确实不知道就直接说不知道，并指出该问哪个部门；不要用「一般来说」「通常」把猜测写成学校规定。\n"
        "- 用正常的中文标点：逗号、句号、问号、冒号、引号都照常写，不要写成没有句号的流水句。\n"
        "- 不要用 Markdown 的星号、井号、反引号。\n"
        "- 不用首先、其次、最后、此外、值得注意的是、总而言之这类开场词。\n"
        "- 不用不是A而是B、与其说A不如说B、然而A不过B这类转折套话，不用比喻和排比。\n"
    ),
    "free.json": (
        '只输出 JSON：{"answer": "…", "confidence": "low|medium|high", "caveat": "…"}'
    ),
    # task=headline：卡片顶部那句总括。只看正文已经说了什么，不新增任何事实。
    "headline.role": (
        "用户问了一句校园办事的问题，下面是系统从官方条目里查到的答复正文。"
        "请给这次回答写一句总括，它会显示在回答最上面当大标题。\n"
    ),
    "headline.rules": (
        "要求：\n"
        "- 只说正文里已经写到的事实，不许新增：正文没有的数字、日期、金额、电话、网址一律不要写进来。\n"
        "- 不超过 20 个字，写成陈述短语；不要问号，不要引号和书名号。\n"
        "- 正文里一条官方内容都没有时，headline 返回空字符串。\n"
    ),
    "headline.json": '只输出 JSON：{"headline": "…"}',
    # task=condense：把省略式追问补成一句能独立检索的问句。只喂上一轮的「问」，
    # 不喂上一轮的「答」——回答正文里全是上一条事项的词，喂进去检索就跟着跑偏。
    "condense.role": (
        "学生在接着上一句话追问。请把最新这句补全成一句不需要上下文也能看懂的问句。\n"
    ),
    "condense.rules": (
        "要求：\n"
        "- 只补省略的主语和对象，用最近一次问句里的说法；不要新增没问过的条件。\n"
        "- 不要回答问题，不要解释，不超过 30 个字。\n"
        "- 补不出更具体的说法时，原样返回最新这句。\n"
    ),
    "condense.json": '只输出 JSON：{"query": "…"}',
    # task=assemble_plan：把一句问话拆成该由学校文件分开写的几面，并给出官方写法。
    # 拆面是为了解决「用户说口语、原文写官方话」的字面鸿沟，不是替用户设想他没问的事。
    "assemble.plan.role": (
        "学生在问校园办事的一件事。把这件事拆成一张清单：学校里会分开写、各答一部分的几个面。\n"
    ),
    "assemble.plan.rules": (
        "要求：\n"
        "- 只列这句话真正问到的面，最多 3 个；这句话本来就一件事说完了，faces 返回空列表，不要硬凑。\n"
        "- 每个面给 1～2 个 phrases：写成学校文件、通知、章程里对这件事的常见说法，"
        "不要照抄学生的口语。\n"
        "- 说法里必须保留这句话里的主体（哪个部门、哪个地方、哪个东西）；换成另一件事的说法不要给。\n"
        "- 已经答到的面不要再列。\n"
    ),
    "assemble.plan.json": (
        '只输出 JSON：{"faces": [{"face": "面的名字", "phrases": ["官方文件里的常见说法"]}], '
        '"why": "一句话理由"}'
    ),
    # task=assemble_decide：决策层只有否决权，不打分、不改写。
    "assemble.decide.role": (
        "下面几条是学校知识库里和这一个面对得上的条目。判断哪一条真的把这个面说清楚了。\n"
    ),
    "assemble.decide.rules": (
        "要求：\n"
        "- 你只有否决权：某条原文确实把这个面讲到了就 accept，并把它 id 和支撑结论的原话一起给出；"
        "只沾主题、没讲到这个面的，判 no_evidence。\n"
        "- quote 必须从条目原文里一字不差地抄，不许改写、不许把几段拼在一起、不许自己补数字或时间。\n"
        "- 拿不准一律 no_evidence；id 只能从上面列出的条目里选。\n"
    ),
    "assemble.decide.json": (
        '只输出 JSON：{"verdict": "accept|reject|no_evidence", "id": "条目 id 或 null", '
        '"quote": "一字不差的原文", "why": "一句话"}'
    ),
    # task=phrase：只把口语换成官方说法，不拆面也不回答问题。
    # 「图书馆周末开吗」在原文里写的是「周一～周日」，字面桥只能靠这一步搭。
    "phrase.role": "学生在问校园办事的一件事。把他这句话换成学校官方文件里的常见说法。\n",
    "phrase.rules": (
        "要求：\n"
        "- 只换说法，不改意思，不要回答问题。\n"
        "- 每条说法都要保留原句里的主体（哪个部门、哪个地方、哪个东西）。\n"
        "- 给 2～3 条，每条不超过 14 个字；只想不出换法时返回空列表。\n"
    ),
    "phrase.json": '只输出 JSON：{"phrases": ["…"]}',
    # task=ctx_need：这句要不要接着上一条才答得清楚。替掉手写词表主判
    # （_FOLLOW_RE/_GENERIC_TERMS 只留作接口失败时的兜底）。
    "ctx_need.role": (
        "学生一件一件问校园的事，屏幕上还摆着上一条事项。判断最新这句要不要接着上一条"
        "才问得清楚。\n"
    ),
    "ctx_need.rules": (
        "判法：\n"
        "- 这句自己说清楚了问的是哪件事（带着主体，能单独拿去检索），算不需要。\n"
        "- 这句省略了主体，或只问时间、地点、材料、费用、流程、怎么办，"
        "不接上一条就不知道在问哪件事，算需要。\n"
        "- 句子里点了另一件事或另一个地方（「那转专业呢」「图书馆开门吗」），算不需要。\n"
        "- 只回答需不需要，不要回答问题，不要解释理由以外的内容。\n"
    ),
    "ctx_need.json": '只输出 JSON：{"need": true|false, "why": "不超过 15 个字"}',
}

# ---------------------------------------------------------------- 动态片段
# 值取 state 里的键，渲染完补两个换行（候选清单与规则之间空一行的现行写法）

DYNAMIC: dict[str, Callable[[dict[str, Any]], str]] = {
    "rerank.pool": lambda st: f"{st['menu']}\n\n",
    "route.pool": lambda st: f"{st['menu']}\n\n",
    "rerank.facet_menu": lambda st: f"只能从这些说法里选，最多两个：{st['facet_menu']}",
    "headline.body": lambda st: f"问句：{st['q']}\n答复正文：\n{st['body']}\n\n",
    "condense.history": lambda st: f"之前问过：{st['history']}\n最新这句：{st['q']}\n\n",
    "assemble.plan.query": lambda st: f"问句：{st['q']}\n\n",
    "assemble.plan.answered": lambda st: f"已经答到的：{st['answered'] or '（还没有）'}\n\n",
    "assemble.decide.face": lambda st: f"问句：{st['q']}\n要答的这个面：{st['face']}\n\n",
    "assemble.decide.pool": lambda st: f"{st['menu']}\n\n",
    "phrase.query": lambda st: f"问句：{st['q']}\n\n",
    "ctx_need.pair": lambda st: (f"上一条事项：{st['title']}\n"
                                 f"上一条问的是：{st['prev_q'] or '（没记）'}\n"
                                 f"最新这句：{st['q']}\n\n"),
}


def layout(task: str, state: dict[str, Any]) -> list[str]:
    if task == "rerank":
        judge = "rerank.judge_menu" if state.get("menu_mode") else "rerank.judge"
        parts = ["rerank.role", "@rerank.pool", judge]
        if judge == "rerank.judge":
            parts.append("rerank.judge_generic")
        return parts + ["rerank.facet_head", "@rerank.facet_menu", "rerank.facet_tail",
                        "rerank.rewrite", "rerank.json"]
    if task == "route":
        return ["route.role", "@route.pool", "route.translate",
                "route.pick", "route.json"]
    if task == "free_answer":
        return ["free.role", "free.rules", "free.json"]
    if task == "headline":
        return ["headline.role", "@headline.body", "headline.rules", "headline.json"]
    if task == "condense":
        return ["condense.role", "@condense.history", "condense.rules", "condense.json"]
    if task == "assemble_plan":
        return ["assemble.plan.role", "@assemble.plan.query", "@assemble.plan.answered",
                "assemble.plan.rules", "assemble.plan.json"]
    if task == "assemble_decide":
        return ["assemble.decide.role", "@assemble.decide.face", "@assemble.decide.pool",
                "assemble.decide.rules", "assemble.decide.json"]
    if task == "phrase":
        return ["phrase.role", "@phrase.query", "phrase.rules", "phrase.json"]
    if task == "ctx_need":
        return ["ctx_need.role", "@ctx_need.pair", "ctx_need.rules", "ctx_need.json"]
    raise KeyError(f"未知 task：{task}")


def assemble(task: str, state: dict[str, Any]) -> str:
    out = []
    for key in layout(task, state):
        if key.startswith("@"):
            out.append(DYNAMIC[key[1:]](state))
        else:
            out.append(FRAGMENTS[key])
    return "".join(out)


def norm_query(text: str) -> str:
    s = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    return "".join(s.split())


def parts_version(task: str, state: dict[str, Any]) -> str:
    # 固定片段按内容进哈希，动态片段只按名字进——候选每次都不一样，不该让版本跟着抖
    parts = []
    for key in layout(task, state):
        if key.startswith("@"):
            parts.append(f"{key}@dyn")
        else:
            parts.append(f"{key}@{VERSION}:{FRAGMENTS[key]}")
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]


def cache_key(task: str, state: dict[str, Any], query: str) -> str:
    raw = f"{task}|{parts_version(task, state)}|{norm_query(query)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
