"""条目生成器 v2：分区式切分，保证「切完拼回去 = 原文」，不丢任何正文。

与 v1（tools/build_clause_items.py）的五点差别，都是 2026-11-04 用户批准的改法：

1. 遍历磁盘正文文件，不再只遍历索引登记的键（v1 漏掉 ilib-list-index 整批 1,028 份）。
2. 门槛不再丢内容：v1 的 no_sentence / not_chinese / table 五道门槛实测误杀 170 万字。
   这版把正文按「分区」处理——每个字符要么进条目引文，要么进数据表，要么被判为噪声并逐条留痕。
3. 结构切分：认 第X章/第X条/一、/（一）/1./①/•/附件N 为切点，一个分点一条，
   标题保留编号与整条标题文字（v1 的 make_title 会把分点编号抹掉）。
4. 噪声分两级：版式垃圾（页码、孤立标点）不断句，可以并进同一条；
   站点导航（菜单串、面包屑、发布者/浏览数）必须断段，绝不和正文粘成一条。
   站点版式串另用语料词频表识别（同一短串在多份文件里重复出现=模板，不是内容），不手写别名。
5. 引文保真：answer 是「读起来干净」的文字，quote 是原文里连续的字符区间（含被 answer 略掉的页码）。
   tools/check_quotes.py 只校验 quote ⊂ 原文，所以引文永远逐字可查；
   answer 的每个字都来自 quote（子序列关系），差额全在噪声台账里可追。

用法：
    python tools/build_items_v2.py --dry-run                 # 只看统计与样张
    python tools/build_items_v2.py --limit 40                # 前 40 份文件试跑
    python tools/build_items_v2.py --dump-chrome             # 导出版式词频表供人工复看
    python tools/build_items_v2.py --apply                   # 写 items.json（自动备份，只增不删）
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
OUT = ROOT / "_review_items"
sys.path.insert(0, str(ROOT / "tools"))
import build_clause_items as V1  # noqa: E402

SKIP_DIRS = {"_quarantine", "vector"}
SKIP_FILES = {"wendao-verify.md"}   # 我们自己生成的下载核验表，不是官方资料，别混进知识库
TEXT_EXT = {".txt", ".md", ".html", ".htm"}
CHECKED = "2026-11-04"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def is_subseq(small: str, big: str) -> bool:
    """small 的每个字按顺序出现在 big 里（big 可能夹着被略掉的页码残片）。"""
    if not small:
        return False
    it = iter(big)
    return all(c in it for c in small)


# ---------- 行分类 ----------
META_HEAD = re.compile(
    r"^(发布时间|发布时间[:：]|发布[:：]|发布者[:：]|发布人[:：]|浏览次数|阅读次数|点击次数|点击数|阅读量|"
    r"来源[:：]|作者[:：]|栏目[:：]|编辑[:：]|责任编辑|发布者|录入|校对|审核[:：]|字号|分享到|收藏|打印本页|关闭窗口|二维码)")
FULL_META = re.compile(r"^[^。；]{0,30}?(发布者|发布人|浏览次数|阅读次数|发布时间)[:：].{0,40}"
                       r"([：:]\s*[\d\-/: ]+){1,4}$")
MENU_RUN = re.compile(r"(菜单|链接|首页|返回|更多|详细|下一页|上一页|分享|打印|关闭|搜索|导航|入口|大厅|专区|下载|上传|订阅)")

PROV_RX = re.compile(r"^(来源|栏目|作者|编辑|发布时间|页面发布时间|采集时间)[：:]\s*(.+)$")
PROV_FIELD = {"来源": "url_note", "栏目": "column", "作者": "author", "编辑": "editor",
              "发布时间": "published", "页面发布时间": "published", "采集时间": "crawled"}


def provenance_of(noise: list[tuple[int, int, str, str]]) -> dict[str, str]:
    """爬虫写在正文前面的那几行元数据，抽成条目字段——字仍在噪声台账里（不丢），但答案不再是一串「来源：」。

    只认文件开头 400 字以内的，正文中间出现的「作者：」是文章本身的内容，不能当页眉剥掉。
    """
    out: dict[str, str] = {}
    for a, _b, t, why in noise:
        if why != "meta" or a > 400:
            continue
        m = PROV_RX.match(t.strip())
        if m and m.group(1) in PROV_FIELD:
            v = m.group(2).strip()[:200]
            d = re.fullmatch(r"(\d{4}-\d{1,2}-\d{1,2})(\d{2}:\d{2}(:\d{2})?)", v)
            if d:                                  # 归一化把日期与时刻之间的空格吃了，补回来
                v = f"{d.group(1)} {d.group(2)}"
            out.setdefault(PROV_FIELD[m.group(1)], v)
    return out


def line_action(ln: str, chrome: set[str]) -> tuple[str, str]:
    """keep=正文 / join=版式残片（可并进同一条）/ block=站点模板（必须断段）"""
    if V1.JUNK.search(ln):
        return "block", "junk"
    if V1.NAV.fullmatch(ln) or ln in V1.NAV_WORDS:
        return "block", "nav"
    if ln in chrome:
        return "soft", "chrome"
    if re.match(r"^(当前位置|您现在的位置|所在位置)", ln):
        return "block", "breadcrumb"
    if META_HEAD.match(ln) or FULL_META.match(ln):
        return "block", "meta"
    if V1.MENU.search(ln) and not re.search(r"[。；]", ln):
        return "block", "menu"
    if len(MENU_RUN.findall(ln)) >= 3 and not re.search(r"[。；]", ln):
        return "block", "menuwords"
    if len(ln) <= 24 and len(V1.NAV_RUN.findall(ln)) >= 2:
        return "block", "navrun"
    if re.search(r"</?[a-zA-Z!][^>]*>", ln) or ln in {"-->", "{"} or ln.startswith("{缩略图") or ln == "{标题}":
        return "block", "html"
    if re.fullmatch(r"\d{4}\s*[年/-]\s*\d{1,2}\s*[月/-]\s*\d{1,2}\s*[日号]?([星期周]\d?)?([\s:：0-9]|\uff1a)*", ln):
        return "join", "date"
    if re.fullmatch(r"[-—–]?\s*\d{1,4}\s*[-—–]?", ln) or re.fullmatch(r"第?\s*\d{1,4}\s*页", ln):
        return "join", "pageno"
    if re.fullmatch(r"[0-9\W]{1,8}", ln):
        return "join", "digits"
    if re.fullmatch(r"[，、；：,.．;:／/|＿_—\-\*\#\+]{1,12}", ln):
        return "join", "punct"
    if re.match(r"^(附件图片|图片\d*|图\d+|摄)\s*$", ln) or re.match(r"^[（(]完?[）)]$", ln):
        return "join", "mark"
    if ln.startswith("_upload/") or ("/images/" in ln and len(ln) < 40):
        return "join", "img"
    return "keep", ""


def is_navish(ln: str) -> bool:
    return bool(ln) and (ln in V1.NAV_WORDS or V1.NAV.fullmatch(ln) is not None)


# ---------- 分段：块内每个字符都带原文位置 ----------
def segments(raw: str, chrome: set[str]) -> tuple[list[list[dict]], list[tuple[int, int, str, str]]]:
    """返回 (段列表, 噪声台账)。段=正文行的连续块；噪声块按类型决定断不断段。

    版式词频表里的短串只在「左右邻句也是模板」时才丢——
    「关于印发」「（试行）」这类跨行断开的标题不能当模板，否则标题被啃掉半截。
    """
    rn = norm(raw)
    lines = [norm(l) for l in raw.splitlines()]
    lines = [l for l in lines if l]
    pos = 0
    segs: list[list[dict]] = []
    cur: list[dict] = []
    noise: list[tuple[int, int, str, str]] = []
    tail: list[tuple[int, int, str, str]] = []      # 还没被正文吸收的残片
    for idx, ln in enumerate(lines):
        i = rn.find(ln, pos)
        if i < 0:
            i = rn.find(ln)
            if i < 0:
                continue
        pos = i + len(ln)
        act, why = line_action(ln, chrome)
        if act == "soft":
            nb = [lines[idx - 1] if idx else "", lines[idx + 1] if idx + 1 < len(lines) else ""]
            near = [x for x in nb if x]
            act = "block" if any(x in chrome or is_navish(x) for x in near) else "keep"
            why = "chrome" if act == "block" else ""
        if act == "keep":
            if tail:
                tail = []                            # 残片落在两个正文行之间，随所属区间一起进引文
            cur.append({"text": ln, "start": i})
        elif act == "join":
            if cur:
                tail.append((i, pos, ln, why))       # 段尾残片：后面若还有正文就被吸收，否则记噪声
            else:
                noise.append((i, pos, ln, why))
        else:
            if cur:
                segs.append(cur)
                cur = []
            noise.extend(tail)
            tail = []
            noise.append((i, pos, ln, why))
    if cur:
        segs.append(cur)
    noise.extend(tail)
    return segs, noise


# ---------- 结构切分 ----------
LEVELS = [
    (1, re.compile(r"^第[一二三四五六七八九十百零〇\d]+[章篇部节]")),
    (2, re.compile(r"^第[一二三四五六七八九十百零〇\d]+条")),
    (3, re.compile(r"^[一二三四五六七八九十百]{1,3}、")),
    (4, re.compile(r"^[（(]\s*[一二三四五六七八九十\d]{1,3}\s*[）)]")),
    (5, re.compile(r"^\d+[.．、]|\d+\.\d+[.．、]")),
    (6, re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]")),
    (7, re.compile(r"^[-·•●○◆★☆▪]\s*[^\s-]")),
    (4, re.compile(r"^附件\s*\d*[：:]|^附件\d+")),
    (6, re.compile(r"^(注|备注|说明)[：:]")),
]


def head_of(ln: str) -> tuple[int, str] | None:
    for lvl, rx in LEVELS:
        m = rx.match(ln)
        if m and len(ln) >= 2:
            return lvl, ln[:34]
    return None


SENT_END = re.compile(r"[。！？；]")
LABEL_MAX = 44
PUNCT_ANY = re.compile(r"[，。！？；：、,、（）()《》〔〕“”\"']")


def label_kind(text: str) -> str:
    """标题行的两种：head=章节/条款标题（带编号或以冒号收尾），menu=不带标点的短词（菜单/目录词）。

    带竖线或制表符的是表格单元格，不是菜单词——它们整块进数据表。
    """
    if not text or len(text) > LABEL_MAX or SENT_END.search(text):
        return ""
    if "|" in text or "\t" in text:
        return ""
    if head_of(text) or text[-1] in "：:":
        return "head"
    if len(text) <= 16 and not PUNCT_ANY.search(text):
        return "menu"
    return ""


def flat_table_unit(text: str) -> bool:
    """拍平的表格内容：Word/Excel 表格变成「10000.00北京市发改委…学费元/生.学年」或竖线串，不是句子。

    收费公示表一行常被拍成两三个金额 + 「元/生.学年」+ 文件号，够不上四条金额，
    所以补一条：整段一句完整话都没有（无句号），却有两个以上金额和收费单位——就是表，不是答案。
    """
    big = re.findall(r"\d[\d,]{3,}|\d+\.\d{2}", text)
    if text.count("。") > 1:
        return False
    if len(big) >= 4 or text.count("|") >= 3:
        return True
    return text.count("。") == 0 and len(big) >= 2 and (
        "元/生" in text or ("元/年" in text and "收费" in text))


DOT_LEADER = re.compile(r"[.…·]{6,}")
HARD_JUNK = re.compile(
    "[\u0590-\u05ff\u0600-\u06ff\u0780-\u07bf\u0900-\u0fff"      # 希伯来/阿拉伯/叙利亚/印度系/藏文
    "\u1000-\u11ff\u1200-\u137f\u1780-\u17ff"                   # 缅甸/格鲁吉亚/韩文谚文字母/埃塞/高棉
    "\u0e00-\u0eff\x00-\x08\x0e-\x1f]")                        # 泰文老挝 + 控制符


def junk_kind(text: str) -> str:
    """这段字要入库，但不能当答案：目录点线页 / ToUnicode 表坏了抽出来的乱码。

    只看形状不看内容——两者都是抽取产物，字照旧被引文与位图认领（一个字不丢），
    只是不该抢在真答案前面端给用户。
    乱码的判据是「生僻文字比正文还多」：真公文里出现阿拉伯文、韩文、藏文都是零星的
    专名或例句，汉字数字字母一定压过它们；一旦反过来，就是抽取环节坏了。
    """
    j = len(HARD_JUNK.findall(text))
    core = len(re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text))
    if j >= 3 and j > core:
        return "乱码"
    if DOT_LEADER.search(text):
        return "目录"
    return ""


def answerable(text: str) -> bool:
    """够不够格当答案：有句末标点，或者本来就够长。只有一句标题的段留在库里查得到，但不抢路由。"""
    return bool(SENT_END.search(text)) or len(re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text)) >= 40


def build_units(seg: list[dict]) -> list[dict]:
    """一个连续正文块 → 结构单元序列。

    规则：
    1. 章节标题行（head）只进标题链，它的字并进下一条正文的引文区间——
       「第一章总则」不再单独成一条空条目，标题字也一个字不丢。
    2. 三行以上连着的裸短词（menu）判为站点目录串，自己成一条并标 archive_only：
       不是办事答案，但要挂在库里查得到（每个文件都要成条目）。
    3. 带编号的正文（「第X条……。」）自己成条，编号留在正文里（v1 会把编号抹掉）。
    4. 折行的句子照原样接在上一条后面，绝不当标题；段尾孤立标题并进上一条，不留白。
    """
    heads: list[tuple[int, str]] = []
    units: list[dict] = []
    cur: dict | None = None
    groups: list[dict] = []

    def head_str() -> str:
        return " ".join(t for _l, t in heads)

    def push_label(lvl: int, label: str) -> None:
        nonlocal heads
        if lvl == 9 and heads and heads[-1][0] == 9:
            heads[-1] = (9, (heads[-1][1] + "、" + label)[:LABEL_MAX])
        else:
            heads = [(l, t) for l, t in heads if l < lvl] + [(lvl, label)]

    def close() -> None:
        nonlocal cur
        if cur:
            units.append(cur)
            cur = None

    def carry() -> list[tuple[str, int]]:
        out = [c for g in groups for c in g["chars"]]
        groups.clear()
        return out

    def take_menu() -> list[tuple[str, int]]:
        """末尾连着三行以上的裸短词=目录串，整块（含它前面的标题行）单独成条。

        必须整块切走：标题行留在 groups 里会被并进再下一条，那条的区间就跨过目录串，
        同一段字被两条各认领一次（重复认领）。
        """
        k = 0
        while k < len(groups) and groups[len(groups) - 1 - k]["kind"] == "menu":
            k += 1
        if k < 3:
            return []
        return carry()

    for p in seg:
        t = p["text"]
        chars = [(c, p["start"] + i) for i, c in enumerate(t)]
        h = head_of(t)
        kind = label_kind(t)
        if kind:
            push_label(h[0] if h else 9, t[:24])
            groups.append({"kind": kind, "chars": chars})
            continue
        menu = take_menu()
        if menu:
            close()
            units.append({"head": head_str(), "chars": menu, "menu": True})
        pre = carry()
        if h:
            close()
        if cur and pre:
            close()                          # 标题插在两条正文之间：另起一条，字符位置才能保持递增
        if cur is None:
            cur = {"head": head_str(), "chars": pre + chars, "menu": False}
        else:
            cur["chars"].extend(chars)
    menu = take_menu()
    if menu:
        close()
        units.append({"head": head_str(), "chars": menu, "menu": True})
    if groups:
        rest = carry()
        if cur:
            cur["chars"].extend(rest)
        elif units:
            units[-1]["chars"].extend(rest)
        else:
            units.append({"head": head_str(), "chars": rest, "menu": True})
    close()
    for u in units:
        u["pre_start"] = u["chars"][0][1]
        u["text"] = "".join(c[0] for c in u["chars"])
    return [u for u in units if u["text"]]


def split_parts(text: str, limit: int = 200, hard: int = 420) -> list[tuple[int, int]]:
    """在一段正文里按句切，返回 [(偏移, 长度)]，不丢任何字符。

    切点优先在 。！？； 之后；一个句末标点都没有时，仍要在 hard 处按逗号/顿号/空格强制断，
    否则整段万字会成一条（「超过 hard 强制在逗号断」这条规则原本形同虚设）。
    不足 12 字的残段并进前一段（绝不丢弃）。
    """
    n = len(text)
    if n <= limit:
        return [(0, n)]
    marks = [m.start() + 1 for m in re.finditer(r"[。！？；]", text)]
    parts: list[tuple[int, int]] = []
    start = 0
    i = 0
    while start < n:
        if n - start <= limit:
            parts.append((start, n - start))
            break
        while i < len(marks) and marks[i] <= start:      # 跳过已用掉的切点
            i += 1
        best = -1
        j = i
        while j < len(marks) and marks[j] <= start + limit:
            best = marks[j]
            j += 1
        if best > start:                                  # 首选：limit 内最靠后的句末
            parts.append((start, best - start))
            start = best
            continue
        nxt = marks[i] if i < len(marks) else -1          # 次选：hard 内的句末
        if nxt != -1 and nxt <= start + hard:
            parts.append((start, nxt - start))
            start = nxt
            continue
        cut = max((text.rfind(c, start + 40, start + hard)             # 兜底：强制断
                   for c in "，,、；:： 　"), default=-1)
        if cut <= start + 20:
            cut = min(start + hard, n)
        parts.append((start, cut - start))
        start = cut
    merged: list[tuple[int, int]] = []
    for off, ln in parts:
        if ln <= 0:
            continue
        if merged and ln < 12:
            s, l = merged[-1]
            merged[-1] = (s, l + ln)
            continue
        merged.append((off, ln))
    if len(merged) > 1 and merged[-1][1] < 12:
        s, l = merged[-2]
        merged[-2] = (s, l + merged[-1][1])
        merged.pop()
    out = [p for p in merged if p[1] > 0]
    pos = 0
    for off, ln in out:
        if off != pos:
            return [(k, min(hard, n - k)) for k in range(0, n, hard)]   # 不连续就退回定长：不丢也不重
        pos += ln
    return out if pos == n else [(k, min(hard, n - k)) for k in range(0, n, hard)]


# ---------- 文档分类（分泳道） ----------
BANSHI_RX = re.compile(
    r"办理|申请材料|递交|提交|受理|审批|报销|开具|盖章|转专业|转学|户口|迁|选课|退课|补考|重修|请假"
    r"|入住|退宿|宿舍|校园卡|挂失|充值|证明|预约|报名|报到|注册|流程|步骤|第[一二三四五六七八九十]步"
    r"|办理时间|办理地点|联系人|咨询电话|办公时间|指南|须知|办法|细则|规定|FAQ|常见问题")
PROMO_RX = re.compile(r"举行|座谈|荣获|获奖|喜报|签约|调研|参观|访问|交流|开幕|闭幕|纪念|庆典|展演|展览|论坛|讲座|慰问|致辞|视察|召开")
LIST_TITLE = re.compile(r"(录取名单|拟录取.{0,6}名单|复试名单|调剂名单|名单公示|名册|名单$)")


def is_namelist(head: str, body: str) -> bool:
    """真的名单：开头就是「××录取名单」，正文几乎没有成句的句子（名字+数字的清单）。

    招生简章、推免办法里也会提一句「录取名单」，不能因此整份不入库。
    """
    if not LIST_TITLE.search(head):
        return False
    n = len(body)
    marks = body.count("。") + body.count("；")
    return marks <= max(2, n // 600)
NEWS_BUCKETS = {"crawl", "cdp", "wechat", "extra", "ilib", "ilib-text", "ilib-list-text"}
LANE_PARAMS = {                      # kind -> (limit, hard, routable)
    "规章正文": (200, 420, True),
    "办事新闻": (200, 420, True),
    "长文正文": (240, 480, True),
    "短页": (240, 480, True),
    "宣传稿": (800, 1600, False),
    "普通公告": (800, 1600, False),
    "整篇挂上": (800, 1600, False),   # 目录/表格泳道里其实没有表的文件（如阅读报告只有元数据页）
}


def classify(title: str, body: str, bucket: str, n_units: int, chars: int) -> str:
    blob = (title or "") + " " + body[:1500]
    if is_namelist((title or "") + body[:80], body):
        return "名单"
    if bucket == "ilib-list-text" or (bucket.startswith("ilib") and re.search(r"阅读|书目|期刊|目录", blob)):
        return "书目目录"
    if n_units >= 5 and chars >= 1200:
        return "规章正文"
    if bucket in NEWS_BUCKETS and PROMO_RX.search(blob) and not body[:1200].count("办理"):
        return "宣传稿"
    if bucket in NEWS_BUCKETS and len(set(BANSHI_RX.findall(blob))) >= 2:
        return "办事新闻"
    if bucket in NEWS_BUCKETS:
        return "普通公告"
    if chars >= 1200:
        return "长文正文"
    return "短页"


# ---------- 表格泳道 ----------
def table_rows_of(raw_lines: list[str]) -> tuple[list[str], list[list[str]]]:
    """从原始行解析表格：带 | 或制表符的行算一行；单元格数不足时把后续单列行补齐。"""
    cols: list[str] = []
    rows: list[list[str]] = []
    pending: list[str] = []
    for line in raw_lines:
        t = line.strip()
        if not t:
            continue
        if t.count("|") >= 2:
            cells = [c.strip() for c in re.split(r"\s*\|\s*", t) if c.strip()]
        elif "\t" in t and len(t.split("\t")) >= 2:
            cells = [c.strip() for c in t.split("\t") if c.strip()]
        else:
            if not cells_ok(pending, cols):
                continue
            pending.append(t)
            continue
        if not cols and len(cells) >= 2:
            cols = cells
            continue
        if not cells_ok(pending, cols):
            pending = []
        if len(cells) < len(cols) and cols:
            pending.extend(cells)
            if cells_ok(pending, cols):
                rows.append(pending)
                pending = []
        else:
            if pending:
                rows.append(pending)
                pending = []
            rows.append(cells)
    if pending and cols and len(pending) == len(cols):
        rows.append(pending)
    return cols, rows


def cells_ok(pending: list[str], cols: list[str]) -> bool:
    return bool(cols) and len(pending) + 1 >= len(cols)


# ---------- 单文件处理 ----------
def process(path: Path, meta: dict, chrome: set[str], items_out: list, rows_out: list,
            report_out: list, ledger: list) -> None:
    rel = str(path.relative_to(SRC))
    raw = path.read_text(encoding="utf-8", errors="ignore")
    rn = norm(raw)
    bucket = path.relative_to(SRC).parts[0] if len(path.relative_to(SRC).parts) > 1 else "(根)"
    key = path.stem
    own = [0] * len(rn)
    stat = {"overlap": 0}

    def claim(a: int, b: int) -> bool:
        ok = True
        for i in range(a, min(b, len(rn))):
            if own[i]:
                stat["overlap"] += 1
                ok = False
            else:
                own[i] = 1
        return ok

    raw_lines = raw.splitlines()
    pipe_lines = sum(1 for l in raw_lines if l.count("|") >= 2)
    tab_lines = sum(1 for l in raw_lines if "\t" in l and len(l.split("\t")) >= 3)
    n_ls = max(1, sum(1 for l in raw_lines if l.strip()))
    segs, noise = segments(raw, chrome)
    for f, v in provenance_of(noise).items():
        meta.setdefault(f, v)
    body_chars = sum(len(p["text"]) for s in segs for p in s)
    for a, b, t, why in noise:
        claim(a, b)
    pieces_text = "".join(p["text"] for s in segs for p in s)
    kind = classify(meta.get("title", ""), pieces_text[:4000], bucket,
                    sum(len(s) for s in segs), body_chars)

    # 表格/目录/名单：整份走数据表，不切条目
    if kind in ("书目目录", "名单") or (pipe_lines + tab_lines) >= 12 and (pipe_lines + tab_lines) / n_ls >= 0.5:
        cols, rows = ([], []) if kind == "名单" else table_rows_of(raw_lines)
        if kind != "名单" and not rows and body_chars >= 1:
            # 判成目录、其实没有表（阅读报告那类只有标题+来源+发布时间的元数据页）：整篇挂成条目
            kind = "整篇挂上"
        else:
            lane = "名单(按决策不处理)" if kind == "名单" else "数据表"
            for ri, cells in enumerate(rows):
                for ci, val in enumerate(cells):
                    s = norm(val)
                    if not s:
                        continue
                    for k in range(0, len(s), 300):      # 超长单元格切着存，别把后半截丢了
                        rows_out.append({"doc": key, "bucket": bucket, "row_no": ri, "col": ci,
                                         "header": cols[ci] if ci < len(cols) else "",
                                         "value": s[k:k + 300], "title": meta.get("title", "")})
            for s in segs:
                if s:
                    claim(s[0]["start"], s[-1]["start"] + len(s[-1]["text"]))
            ledger.append({"file": rel, "kind": kind, "lane": lane, "noise": [
                {"span": [a, b], "text": t[:60], "why": w} for a, b, t, w in noise],
                "rows": len(rows)})
            report_out.append({"file": rel, "title": (meta.get("title") or "")[:60], "chars": len(rn),
                               "items": 0, "rows": len(rows), "noise": len(noise),
                               "missing": sum(1 for x in own if not x), "overlap": stat["overlap"],
                               "kind": kind, "units": len(segs), "note": lane})
            return

    if not body_chars:
        note = "空页/仅噪声"
        report_out.append({"file": rel, "title": (meta.get("title") or "")[:60], "chars": len(rn),
                           "items": 0, "rows": 0, "noise": len(noise),
                           "missing": sum(1 for x in own if not x), "overlap": stat["overlap"],
                           "kind": kind, "units": 0, "note": note})
        ledger.append({"file": rel, "kind": kind, "lane": note, "noise": [
            {"span": [a, b], "text": t[:60], "why": w} for a, b, t, w in noise], "rows": 0})
        return

    limit, hard, routable = LANE_PARAMS.get(kind, (240, 480, True))
    n_items = 0
    n_rows_unit = 0
    dropped: list[tuple[int, int, str, str]] = []
    for seg in segs:
        for unit in build_units(seg):
            chars, text = unit["chars"], unit["text"]
            if not text:
                continue
            if flat_table_unit(text):               # 拍平的学费表/预算表：进数据表
                claim(unit["pre_start"], chars[-1][1] + 1)
                for off, ln in split_parts(text, 300, 300):    # 整块存不下就按 300 字切开，一个字不落在外面
                    rows_out.append({"doc": key, "bucket": bucket, "row_no": n_rows_unit, "col": 0,
                                     "header": unit["head"][:40], "value": text[off:off + ln],
                                     "title": meta.get("title", "")})
                    n_rows_unit += 1
                continue
            for off, ln in split_parts(text, limit, hard):
                i, j = off, off + ln
                a = unit["pre_start"] if i == 0 else chars[i][1]
                b = chars[j - 1][1] + 1
                seg_text = text[i:j]
                quote = rn[a:b]
                if not is_subseq(norm(seg_text), quote):  # answer 的每个字都必须来自这段原文
                    dropped.append((a, b, seg_text[:40], "subseq"))
                    continue
                if not claim(a, b):
                    dropped.append((a, b, seg_text[:40], "overlap"))
                    continue
                if flat_table_unit(seg_text):
                    # 整块没判出来、切到这一段才露出表格形状：同样归数据表，别当答案
                    rows_out.append({"doc": key, "bucket": bucket, "row_no": n_rows_unit, "col": 0,
                                     "header": unit["head"][:40], "value": seg_text,
                                     "title": meta.get("title", "")})
                    n_rows_unit += 1
                    continue
                n_items += 1
                ok = routable and not unit.get("menu") and body_chars >= 8
                if ok:
                    jk = junk_kind(seg_text) or ("" if answerable(seg_text) else "无句末且不足 40 字")
                    if jk:
                        DEMOTE[jk] += 1
                        ok = False
                items_out.append(make_item(key, meta, kind, unit["head"], seg_text, quote, a, b, ok))

    # 落在两条条目之间的版式残片（页码等）：单独记账，不留白
    k = 0
    while k < len(rn):
        if own[k]:
            k += 1
            continue
        m = k
        while m < len(rn) and not own[m]:
            m += 1
        claim(k, m)
        dropped.append((k, m, rn[k:m][:40], "residual"))
        k = m

    missing = sum(1 for x in own if not x)
    report_out.append({"file": rel, "title": (meta.get("title") or "")[:60], "chars": len(rn),
                       "items": n_items, "rows": n_rows_unit, "noise": len(noise), "missing": missing,
                       "overlap": stat["overlap"], "kind": kind, "units": len(segs),
                       "residual": sum(e - s for s, e, _t, w in dropped if w == "residual"),
                       "note": ""})
    ledger.append({"file": rel, "kind": kind, "lane": "条目", "noise": [
        {"span": [a, b], "text": t[:60], "why": w} for a, b, t, w in noise],
        "dropped": [{"span": [a, b], "text": t, "why": w} for a, b, t, w in dropped], "rows": 0})



def make_item(key: str, meta: dict, kind: str, head: str, seg: str, quote: str,
              a: int, b: int, routable: bool) -> dict:
    body = norm(seg)
    iid = "pt-" + hashlib.sha1(body.encode("utf-8")).hexdigest()[:10]
    title = seg[:56]
    if head and head not in title:
        title = f"{head}｜{title}"
    title = re.sub(r"\s+", " ", title)[:64]
    src = {"title": meta.get("title") or key, "url": meta.get("url") or "",
           "slug": key, "checked": CHECKED}
    for f in ("published", "author", "column", "editor", "url_note"):
        if meta.get(f):
            src[f] = meta[f]
    return {
        "id": iid,
        "title": title,
        "aliases": [seg[:30]] if len(seg) <= 30 else [],
        "keywords": V1.make_keywords(seg, title, VOCAB),
        "dept": "中国传媒大学",
        "channel": [],
        "audience": ["本科生", "研究生"],
        "status": "verified",
        "confidence": "medium",
        "materials": [], "steps": [], "fee": None, "location": None, "hours": None,
        "duration": None, "window": None, "pitfalls": [], "contact": None, "slots": [],
        "draft": None,
        "answer": seg,
        "source": src,
        "evidence": {"answer": {"src": key, "quote": quote, "span": [a, b]}},
        "auto": True,
        "auto_kind": kind,
        "archive_only": not routable,
    }


VOCAB: set[str] = set()
CHROME: set[str] = set()
DEMOTE: "collections.Counter" = collections.Counter()


def list_files() -> list[Path]:
    files = []
    for p in sorted(SRC.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT or p.name.startswith("_"):
            continue
        if set(p.relative_to(SRC).parts) & SKIP_DIRS:
            continue
        if p.name in SKIP_FILES:
            continue
        files.append(p)
    return files


def build_chrome(files: list[Path], min_docs: int = 18) -> tuple[set[str], dict[str, int]]:
    """版式词频表：同一短串在多份不同文件里反复出现 = 站点模板，不是内容。
    结构标题（第X章/一、/（一））与带数字的行不进表，避免误杀正文。"""
    docs: dict[str, set[str]] = collections.defaultdict(set)
    for p in files:
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line in raw.splitlines():
            ln = norm(line)
            if not ln or len(ln) > 22 or head_of(ln):
                continue
            if SENT_END.search(ln) or re.search(r"\d", ln) or "：" in ln or ":" in ln:
                continue
            docs[ln].add(p.stem)
    lex = {k for k, v in docs.items() if len(v) >= min_docs}
    return lex, {k: len(v) for k, v in docs.items() if k in lex}


def load_meta() -> dict[str, dict]:
    """从所有索引里取标题与 url；索引没有的退回文件名。"""
    meta: dict[str, dict] = {}

    def put(key, row):
        if not key:
            return
        cur = meta.setdefault(key, {})
        for f in ("title", "url", "collection"):
            if row.get(f) and not cur.get(f):
                cur[f] = row[f]

    reg = json.loads((SRC / "doc-registry.json").read_text(encoding="utf-8"))["docs"]
    for d in reg:
        put(d["key"], {"title": d.get("title"), "url": d.get("url"), "collection": d.get("collection")})
    for name in ("local-index.json", "attachments-text-index.json", "crawl-index.json", "cdp-index.json",
                 "extra-index.json", "huibian-index.json", "wechat-index.json", "chsi-index.json",
                 "moe-index.json", "national-index.json", "corpus-index.json", "index.json",
                 "ilib-list-index.json"):
        p = SRC / name
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = data.values() if isinstance(data, dict) else data
        for v in rows:
            if not isinstance(v, dict):
                continue
            f = str(v.get("file") or v.get("name") or v.get("saved") or "")
            put(Path(f).stem if f else "", {"title": v.get("title"), "url": v.get("url")})
    for name in ("wendao-index.json", "wendao-extra-index.json"):
        p = SRC / name
        if not p.exists():
            continue
        for k, v in json.loads(p.read_text(encoding="utf-8")).items():
            f = str(v.get("file") or "")
            stem = Path(f).stem if f else ""
            head = stem.split("_")[0]
            key = head if re.fullmatch(r"[0-9a-f]{8}", head or "") else stem
            put(key, {"title": v.get("title"), "url": v.get("url"), "collection": "wendao"})
            put(k, {"title": v.get("title"), "url": v.get("url"), "collection": "wendao"})
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="只处理路径里含这个串的文件")
    ap.add_argument("--dump-chrome", action="store_true")
    ap.add_argument("--chrome-min", type=int, default=18)
    args = ap.parse_args()

    global VOCAB
    data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    kept = data["items"]
    VOCAB = V1.build_vocab([it for it in kept if not it.get("auto")])

    files = list_files()
    t0 = time.perf_counter()
    lex, counts = build_chrome(files, args.chrome_min)
    global CHROME
    CHROME = lex
    print(f"版式词频表 {len(lex)} 条（出现在 ≥{args.chrome_min} 份文件的短串），用时 {time.perf_counter()-t0:.0f}s")
    if args.dump_chrome:
        OUT.mkdir(exist_ok=True)
        rows = sorted(((counts[k], k) for k in lex), reverse=True)
        (OUT / "v2_chrome.json").write_text(
            json.dumps([{"docs": d, "text": t} for d, t in rows], ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"已导出 _review_items/v2_chrome.json（{len(rows)} 条，按出现文件数排序）")
        return

    if args.only:
        files = [p for p in files if args.only in str(p.relative_to(SRC))]
    if args.limit:
        files = files[: args.limit]

    meta_all = load_meta()
    items_out: list[dict] = []
    rows_out: list[dict] = []
    report: list[dict] = []
    ledger: list[dict] = []
    t1 = time.perf_counter()
    for p in files:
        key = p.stem
        m = dict(meta_all.get(key) or {"title": key})
        try:
            process(p, m, CHROME, items_out, rows_out, report, ledger)
        except Exception as e:  # noqa: BLE001
            report.append({"file": str(p.relative_to(SRC)), "title": m.get("title", ""),
                           "error": f"{type(e).__name__}: {e}"})
    dur = time.perf_counter() - t1

    # 去重：与既有条目逐字重合的段不再发第二遍（条目只增不删 + 重复的不要重复接入）
    by_doc: dict[str, str] = {}
    for it in kept:
        srcs = {v.get("src") for v in (it.get("evidence") or {}).values() if isinstance(v, dict)}
        if isinstance(it.get("source"), dict) and it["source"].get("slug"):
            srcs.add(it["source"]["slug"])
        blob = norm(it.get("answer") or "")
        for v in (it.get("evidence") or {}).values():
            if isinstance(v, dict) and v.get("quote"):
                blob += norm(v["quote"])
        for s in srcs:
            if s:
                by_doc[s] = by_doc.get(s, "") + blob
    final, dupe, dup_old, mirror = [], 0, 0, 0
    owner: dict[str, dict] = {}
    for it in kept:
        b = norm(it.get("answer") or "")
        if b:
            owner.setdefault(b, it)
    for it in items_out:
        b = norm(it["answer"])
        if not b:
            dupe += 1
            continue
        if b in owner:
            dupe += 1
            # 同一句话在镜像页里出现第二遍：不再发第二条，但把这份文件挂到那条的来源上——
            # 「每个文件都成条目」和「重复的不要重复接入」两头都要守住。
            old = owner[b]
            slug = (it.get("source") or {}).get("slug") or ""
            if slug and slug not in old.setdefault("also_from", []):
                old["also_from"].append(slug)
                mirror += 1
            continue
        old = by_doc.get(it["source"]["slug"], "")
        if old and len(b) >= 10 and b in old:
            dup_old += 1
            continue
        owner[b] = it
        final.append(it)

    used: dict[str, str] = {}
    for it in kept:
        used[it["id"]] = ""
    for it in final:
        iid = it["id"]
        if iid in used:
            it["id"] = iid + "-" + hashlib.sha1(it["source"]["slug"].encode()).hexdigest()[:4]
        used[it["id"]] = ""

    merged = kept + final
    arch = sum(1 for it in final if it.get("archive_only"))
    tot_chars = sum(len(norm(it["answer"])) for it in final)
    miss = sum(r.get("missing", 0) or 0 for r in report)
    over = sum(r.get("overlap", 0) or 0 for r in report)
    resid = sum(r.get("residual", 0) or 0 for r in report)
    err = [r for r in report if r.get("error")]
    print(f"处理 {len(files)} 份文件，用时 {dur:.0f}s")
    print(f"保留既有条目 {len(kept)} 条")
    print(f"新增条目 {len(final)} 条（archive_only {arch} 条），段间重复 {dupe} 段（其中 {mirror} 段把文件挂到已有条目来源上）、与既有条目重合 {dup_old} 段")
    print(f"数据表行 {len(rows_out)} 行；新增引文合计 {tot_chars/1e4:.1f} 万字")
    print(f"占用位图缺口（真漏的字）合计 {miss/1e4:.1f} 万字；重复认领 {over} 字；两条之间的版式残片 {resid} 字")
    print(f"处理出错 {len(err)} 份；条目总量 {len(merged)}")
    print("分类：", dict(collections.Counter(r.get("kind") for r in report).most_common()))
    print("泳道：", dict(collections.Counter(r.get("note") for r in report if r.get("note")).most_common()))
    print("降级为不抢路由（字仍在库里，只是不当答案）：", dict(DEMOTE.most_common()))
    bad = [r for r in report if (r.get("missing") or 0) > 0 and not r.get("error")]
    print(f"缺口 >0 字的文件 {len(bad)} 份")
    for r in sorted(bad, key=lambda x: -(x.get("missing") or 0))[:10]:
        print(f"   漏 {r['missing']:>7d} 字｜{r['kind']:8s}｜{str(r['title'])[:36]}｜{r['file']}")
    if err:
        for r in err[:10]:
            print("   出错：", r["file"], r["error"])

    OUT.mkdir(exist_ok=True)
    (OUT / "v2_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "v2_new_items.json").write_text(json.dumps(final, ensure_ascii=False), encoding="utf-8")
    (OUT / "v2_table_rows.json").write_text(json.dumps(rows_out, ensure_ascii=False), encoding="utf-8")
    (OUT / "v2_noise_ledger.json").write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    if args.apply:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        shutil.copy(ROOT / "items.json", OUT / f"items_before_v2_{stamp}.json")
        wrapper = {k: v for k, v in data.items() if k != "items"}   # version/updated/policy 不能被切分器抹掉
        wrapper["updated"] = time.strftime("%Y-%m-%d")
        wrapper["items"] = merged
        (ROOT / "items.json").write_text(json.dumps(wrapper, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
        # 随包发布的两份压缩副本：仓库里没有 _review_items/，云端只能靠它们重建条目池与数据表
        (ROOT / "items.json.gz").write_bytes(gzip.compress(
            (ROOT / "items.json").read_bytes(), 9, mtime=0))
        (ROOT / "table-rows.json.gz").write_bytes(gzip.compress(
            json.dumps(rows_out, ensure_ascii=False).encode("utf-8"), 9, mtime=0))
        print(f"已写入 items.json（备份 _review_items/items_before_v2_{stamp}.json）")
        print(f"同步刷新 items.json.gz {len((ROOT / 'items.json.gz').read_bytes())/1048576:.2f} MB、"
              f"table-rows.json.gz {len((ROOT / 'table-rows.json.gz').read_bytes())/1048576:.2f} MB")
    else:
        print("（dry-run，未写 items.json）")


if __name__ == "__main__":
    main()
