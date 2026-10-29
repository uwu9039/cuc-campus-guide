"""把官方正文切成条款级条目：每个信息点一条，答案就是原文本身。

用法：
    python tools/build_clause_items.py --dry-run   # 只看统计和样例
    python tools/build_clause_items.py --apply     # 写入 items.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"

INDEXES = {
    "corpus": ("index.json", ""),
    "wendao": ("wendao-index.json", "wendao-text"),
    "huibian": ("huibian-index.json", "huibian"),
    "extra": ("extra-index.json", "extra"),
    "cdp": ("cdp-index.json", "cdp"),
    "crawl": ("crawl-index.json", "crawl"),
    "national": ("national-index.json", "national"),
    "moe": ("moe-index.json", "moe"),
    "chsi": ("chsi-index.json", "chsi"),
    "local": ("local-index.json", "local"),
    "wechat": ("wechat-index.json", "wechat"),
}
TEXT_DIRS = ("wendao-text", "huibian", "extra", "cdp", "crawl", "national",
             "moe", "chsi", "local", "wechat", "pdf", "wendao-extra")

CLAUSE = re.compile(r"第[一二三四五六七八九十百零〇\d]+条")
PAGE_NO = re.compile(r"(?m)^\s*(?:[-—]\s*)?\d{1,3}(?:\s*[-—])?\s*$")
# PDF 页码会粘在句子中间：「违反国家-3-招生考试规定」
INLINE_PAGE = re.compile(r"(?<!\d)[-—–]\s*\d{1,3}\s*[-—–](?!\d)")

# 学生自编指南不是官方文件，不能当依据
UNOFFICIAL = {"loc-新生指南2026-水印版-76f3d8"}
SUB_NO = re.compile(r"^[（(]?[一二三四五六七八九十\d]{1,3}[）)、.．]|^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]\s*")
BOILER = re.compile(r"^(本办法|本规定|本细则|本制度|本通知|本意见).{0,40}(施行|解释|生效)|自(发布|印发|公布|下发)之日起|未尽事宜")
NAV = re.compile(r"^(首页|部门简介|机构设置|联系我们|规章制度|法律法规|政策文件|管理规定|通知公告|思政教育|专题教育|常用下载|友情链接)$")

# 网页模板、Word 转换残留、附件图片路径：都不是正文信息点
JUNK = re.compile(
    r"Normal0?false|EN-US|Microsoft|MS Mincho|_upload/|/article/images|^\s*\[附件\]|"
    r"^\s*[-—]\s*\d{1,3}\s*[-—]\s*$|^\s*第?\s*\d{1,3}\s*页\s*$|"
    r"版权所有|技术支持|京ICP备|文保网安备案|访问量[:：]|打印本页|关闭窗口"
)
# Word 表格按列抽出来会把标题打散：「时 ？补考 间」。
# 这种残片本身不是内容，后面紧跟的才是答案。
GARBLED_HEAD = re.compile(r"^(?=.*？)(?!.*？$)(?!.*[。；，、]).{1,12}$")
NAV_WORDS = {
    "首页", "关于我们", "部门概况", "机构设置", "联系我们", "规章制度", "法律法规",
    "政策文件", "通知公告", "思政教育", "专题教育", "常用下载", "友情链接", "部门简介",
    "党建工作", "服务指南", "下载专区", "意见反馈", "网站地图", "无障碍", "登录", "注册",
    "信息化服务", "IT服务", "校园卡服务", "校园网服务", "校园网认证服务", "信息化处",
}
META_PREFIX = re.compile(r"^发布时间[:：].{0,30}?浏览次数[:：]\s*\d+\s*")
META_LINE = re.compile(r"^(发布时间|浏览次数|来源|作者|编辑|字号|阅读次数|分享到)[:：]")
CAPTION = re.compile(r"^(图|表)\s*\d+([.．、]\s*|\s+)")
MENU = re.compile(r"菜单链接|平台使用手册|常用业务平台|推免专区|服务大厅|办事大厅|智慧校园门户")
BAD_TITLE = re.compile(r"^(PDF|DOC|DOCX|XLS|附件\d*|文档|未知|无标题|下载|index|page|详情)$", re.I)
# 新闻稿不是办事依据：事件报道里没有可执行的办理信息
NEWS_TITLE = re.compile(r"新闻|动态|要闻|喜报|捷报|举行|召开|开幕|闭幕|表彰|获奖|大赛|论坛|讲座|预告|回顾|相册|风采|专访|报道|座谈会|交流会")
NAV_RUN = re.compile(r"学院简介|学院领导|行政机构|学者风采|师资队伍|人才培养|科学研究|党建工作|学生工作|校友之家|联系我们|机构设置|现任领导")
INFO = re.compile(
    "规定|办法|应当|必须|不得|严禁|禁止|可以|申请|办理|提交|负责|时间|地点|电话|"
    "网址|邮箱|地址|条件|材料|费用|标准|要求|通知|公示|审核|审批|备案|登记|领取|"
    "填写|参加|安排|联系|开放|截止|资格|范围|对象|程序|流程|期限|工作日|系统|平台|"
    "网站|教室|楼|元|小时|天|月|年|学分|成绩|考试|课程|学籍|宿舍|校园卡|校园网|"
    "补考|重考|缓考|重修|免修|GPA|成绩单|"
    "奖学金|助学金|医保|档案|户口|就业|毕业|学位|报名|录取|缴费|收费|预约|借用|"
    "损坏|赔偿|处罚|处分|安全|消防|用电|卫生|维修|服务|管理|建设|组织|活动|培训"
)
GENERIC_TITLE = {
    "总则", "附则", "适用范围", "职责", "职责分工", "其他", "其他规定",
    "基本原则", "工作要求", "工作职责", "组织机构", "监督管理", "解释",
}
STOP = set(
    "中国传媒大学 学生 学校 学院 规定 办法 管理 工作 相关 有关 进行 应当 可以 不得 严禁 "
    "按照 负责 以及 或者 其他 本 该 其 为 在 对 于 与 和 及 等 由 从 向 请 需 须 应 能 "
    "要 有 无 不 未 已 将 把 被 所 而 并 但 如 若 则 者 的 了 是 一 二 三 四 五 六 七 八 九 十".split()
)
EXTRA_TERMS = (
    "学籍 学分 绩点 补考 缓考 重修 转专业 辅修 双学位 双学士学位 奖学金 助学金 助学贷款 "
    "勤工助学 宿舍 公寓 门禁 退宿 调宿 校园卡 补卡 挂失 解挂 校园网 流量 计费 邮箱 教务 "
    "本科生院 研究生院 学生工作部 后勤保障处 保卫处 财务处 图书馆 校医院 医保 报销 档案 "
    "户口 就业 三方协议 实习 请假 销假 处分 申诉 体测 军训 社团 志愿 竞赛 保研 考研 出国 "
    "交流 交换 证明 盖章 申请表 材料 流程 时限 费用 条件 资格 名单 公示 复核 审批 备案 "
    "登记 违规 处罚 安全 消防 用电 电器 宠物 饲养 吸烟 控烟 噪音 作息 卫生 维修 报修 热水 "
    "洗浴 洗衣 快递 食堂 餐厅 校车 停车 充电桩 场馆 预约 礼堂 操场 游泳馆 教室 自习 选课 "
    "退课 成绩 考试 四六级 普通话 教师资格 毕业 学位 结业 肄业 休学 复学 退学 转学 延长学制 "
    "学信网 学历 学位认证 档案 派遣 落户 身份证 银行卡 补助 补贴 保险 体检 疫苗 传染病 "
    "实验室 论文 查重 答辩 导师 培养方案 课程 教材 教室 借用 场地 活动 海报 审批 值班 巡查"
    "消防设施 疏散通道 电动车 电池 充电 明火 违禁 电器 管制刀具 危险物品 治安 诈骗 报警"
).split()


def sq(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def load_indexes() -> dict[str, dict]:
    docs: dict[str, dict] = {}
    for coll, (fname, folder) in INDEXES.items():
        p = SRC / fname
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for slug, meta in data.items():
            if not isinstance(meta, dict):
                continue
            title = meta.get("title") or ""
            if not title:
                continue
            cur = docs.setdefault(str(slug), {
                "slug": str(slug), "title": title, "url": meta.get("url") or "",
                "page": meta.get("page_start") or "", "collections": set(),
                "published": meta.get("published") or meta.get("fetched_at") or "",
                "folder": folder,
            })
            cur["collections"].add(coll)
            if meta.get("url") and not cur["url"]:
                cur["url"] = meta["url"]
            if folder:
                cur["folder"] = folder
    return docs


def text_path(doc: dict) -> Path | None:
    slug = doc["slug"]
    cands = []
    if doc.get("folder"):
        cands.append(SRC / doc["folder"] / f"{slug}.txt")
    cands += [SRC / d / f"{slug}.txt" for d in TEXT_DIRS]
    cands.append(SRC / f"{slug}.txt")
    for p in cands:
        if p.exists():
            return p
    return None


def clean_body(raw: str) -> str:
    s = PAGE_NO.sub("", raw)
    s = INLINE_PAGE.sub("", s)
    s = re.sub(r"[ \t\u3000]+", "", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def raw_quote(raw_sq: str, text: str, cursor: int) -> tuple[str, int] | None:
    """在原文里定位这段清洗后的文字，取回连续原文当证据。

    清洗会删掉页脚、附件路径等整行，清洗后的文字因此不再是原文的连续子串。
    这里用首尾锚点取回原文区间：答案仍用干净文本，证据用原文。
    """
    q = sq(text)
    if not q:
        return None
    i = raw_sq.find(q, cursor)
    if i >= 0:
        return raw_sq[i:i + len(q)], i + len(q)
    for n in (24, 18, 12, 8, 6):
        head = q[:n]
        hi = raw_sq.find(head, cursor)
        if hi < 0:
            continue
        for m in (24, 18, 12, 8, 6):
            tail = q[-m:]
            ti = raw_sq.find(tail, hi)
            if ti < 0:
                continue
            end = ti + len(tail)
            # 首尾之间多出来的只能是页脚/附件路径之类的版式噪声
            if end - hi > len(q) + 600:
                continue
            return raw_sq[hi:end], end
    return None


def clean_lines(text: str) -> list[str]:
    """按行清洗：去掉 Word 残留、附件路径、页脚和导航词。"""
    out: list[str] = []
    for ln in text.replace("\r", "\n").split("\n"):
        s = ln.strip()
        if not s or JUNK.search(s) or NAV.fullmatch(s) or s in NAV_WORDS:
            continue
        if GARBLED_HEAD.match(s):
            continue
        m = META_PREFIX.match(s)
        if m:
            s = s[m.end():].strip()
            if not s:
                continue
        elif META_LINE.match(s):
            continue
        s = CAPTION.sub("", s).strip()
        if not s:
            continue
        out.append(re.sub(r"[ \t\u3000]+", "", s))
    # 正文开头连着一串无标点的短行，基本都是导航栏
    i = 0
    while i < len(out) and len(out[i]) <= 12 and not re.search(r"[。！？；：]$", out[i]):
        i += 1
    if i >= 3 and sum(len(x) for x in out[:i]) <= 160:
        out = out[i:]
    return out


def quality_problem(s: str) -> str | None:
    """返回丢弃原因；None 表示可以入库。

    长度不是门槛：官方原文再短，只要是一句完整的话，就是一个信息点。
    """
    body = sq(s)
    if len(body) < 6:
        return "too_short"
    # 极短的必须是说完的整句，不能是标题残片
    if len(body) < 12 and not re.search(r"[。！？；]$", s.strip()):
        return "too_short"
    if JUNK.search(s):
        return "junk"
    if MENU.search(s):
        return "menu"
    if len(NAV_RUN.findall(s)) >= 3:
        return "menu"
    if len(re.findall(r"\.{3}|…", s[:90])) >= 2:
        return "menu"
    if not re.search(r"[。；！？]", s):
        return "no_sentence"
    zh = len(re.findall(r"[\u4e00-\u9fff]", s))
    if zh / max(1, len(body)) < 0.55:
        return "not_chinese"
    if len(set(body)) <= 8:
        return "repeat"
    return None


def clause_units(text: str, raw_sq: str) -> list[tuple[str, str, str]]:
    lines = clean_lines(text)
    joined = "\n".join(lines)
    heads = list(CLAUSE.finditer(joined))
    out: list[tuple[str, str, str]] = []
    cursor = 0
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(joined)
        body = clean_body(joined[m.end():end]).replace("\n", "")
        if quality_problem(body):
            continue
        for part in split_long(body):
            if quality_problem(part):
                continue
            rq = raw_quote(raw_sq, part, cursor)
            if not rq:
                continue
            quote, cursor = rq
            out.append((m.group(0), part, quote))
    return out


def para_units(text: str, raw_sq: str) -> list[tuple[str, str]]:
    """按行拼段落：PDF 的硬换行接上，遇到句末标点或条目编号就断开。"""
    lines = clean_lines(text)
    paras: list[str] = []
    buf = ""
    for ln in lines:
        if re.match(r"^(第[一二三四五六七八九十百零〇\d]+[章节]|[一二三四五六七八九十]+、|\d+[.．、])", ln) and buf:
            paras.append(buf)
            buf = ""
        buf += ln
        if re.search(r"[。！？；]$", ln) or len(buf) >= 520:
            paras.append(buf)
            buf = ""
    if buf:
        paras.append(buf)
    out: list[tuple[str, str]] = []
    cursor = 0
    for p in paras:
        if quality_problem(p):
            continue
        for part in split_long(p):
            if quality_problem(part):
                continue
            rq = raw_quote(raw_sq, part, cursor)
            if not rq:
                continue
            quote, cursor = rq
            out.append((part, quote))
    return out


def doc_short(title: str) -> str:
    # 先去掉括号里的文号，再按文号前缀剥壳：
    # 反过来会把「…规定（中传教字〔2025〕195号）」剥成孤零零一个「）」。
    t = re.sub(r"《|》", "", title)
    t = re.sub(r"中国传媒大学", "", t)
    t = re.sub(r"[（(][^）)]*[）)]", "", t)
    t = re.sub(r"^.*?〔\d{4}〕\s*\d+\s*号[_\s]*", "", t)
    t = re.sub(r"^.*?\[\d{4}\]\s*\d+\s*号[_\s]*", "", t)
    t = re.sub(r"[（）()〔〕\[\]]", "", t)
    t = t.strip(" _-—、，,：:")
    if len(t) < 2:
        t = re.sub(r"[（(].*$", "", title).strip()
    return (t or title)[:18]


def doc_title(doc: dict, text: str) -> str:
    """索引标题缺失或只是「PDF」时，退回正文第一行当标题。"""
    t = (doc.get("title") or "").strip()
    if t and not BAD_TITLE.match(t) and len(t) >= 4:
        return t
    for ln in clean_lines(text)[:6]:
        if 4 <= len(ln) <= 40 and not re.search(r"[。；，、]", ln):
            return ln
    return t or "官方文件"


def split_long(text: str, limit: int = 180) -> list[str]:
    """一条里往往写着好几件事：一句一条，每点都成为独立条目。

    只有「特殊成绩标识。」这类不足一句话的残句才和下一句合并；
    分号不切（「标注；补考通过记六十分」说的是同一件事）；
    单句超长时再退回按分号切。
    """
    if len(text) <= 24:
        return [text]
    sents = [s for s in re.split(r"(?<=[。！？])", text) if s.strip()]
    if len(sents) <= 1:
        return [text]
    parts: list[str] = []
    buf = ""
    for s in sents:
        if buf and (len(buf) + len(s) > limit or len(buf) >= 24):
            parts.append(buf)
            buf = ""
        buf += s
        if len(buf) >= limit:
            parts.append(buf)
            buf = ""
    if buf:
        parts.append(buf)
    out: list[str] = []
    for p in parts:
        if len(p) <= limit * 2:
            out.append(p)
            continue
        sub, curbuf = [], ""
        for s in re.split(r"(?<=[；])", p):
            if len(curbuf) + len(s) > limit and curbuf:
                sub.append(curbuf)
                curbuf = ""
            curbuf += s
        if curbuf:
            sub.append(curbuf)
        out.extend(sub)
    return out


LEAD_CONJ = re.compile(r"^(其中|但是|但|因此|所以|此外|另外|同时|并且|而且|以及|即|则|并|且)[，,、]?")


def make_title(body: str, head: str, short: str) -> str:
    b = body.strip()
    b = SUB_NO.sub("", b)
    first = re.split(r"[。；！？]", b)[0].strip()
    t = first if len(sq(first)) >= 8 else b[:42].strip()
    # 「其中，必修课程…」离开上文就不知道指哪门课，承接词不进标题
    prev = None
    while prev != t:
        prev = t
        t = LEAD_CONJ.sub("", t).strip()
    t = t.strip("，、：:; .．·-")
    if len(sq(t)) < 6:
        t = b[:24].strip()
    if len(t) > 38:
        t = t[:38].rstrip("，、：:; ") + "…"
    if not t or t in GENERIC_TITLE:
        t = f"{head} {t}".strip() if head else t
    if short and short.strip(" ）()") and short not in t:
        t = f"{t} · {short}"
    return t[:64]


def make_keywords(text: str, title: str, vocab: set[str]) -> list[str]:
    found = [w for w in vocab if len(w) >= 2 and w not in STOP and w in text]
    found.sort(key=lambda w: (-len(w), w))
    out: list[str] = []
    for w in found:
        if w not in out:
            out.append(w)
        if len(out) >= 8:
            break
    if len(out) < 4:
        clean = re.sub(r"[\s，。；：、（）()·].*", "", title)
        # 只补三字以上的词；两字碎片（「有补」）会把不同短语粘在一起
        for n in (4, 3):
            for i in range(0, max(0, min(len(clean), 18) - n + 1)):
                g = clean[i:i + n]
                if g in STOP or any(ch in "的了和及与或在为" for ch in g):
                    continue
                if g not in out:
                    out.append(g)
                if len(out) >= 8:
                    break
            if len(out) >= 8:
                break
    return out[:8]


def build_vocab(items: list[dict]) -> set[str]:
    vocab = {t for t in EXTRA_TERMS if len(t) >= 2}
    for it in items:
        if it.get("auto"):
            continue
        for field in ("aliases", "keywords"):
            for w in it.get(field) or []:
                w = str(w).strip()
                if 2 <= len(w) <= 10:
                    vocab.add(w)
        for chunk in re.split(r"[·/（）()、，,\s]+", it.get("title") or ""):
            chunk = chunk.strip()
            if 3 <= len(chunk) <= 10:
                vocab.add(chunk)
    return vocab


def existing_coverage(items: list[dict]) -> tuple[list[str], list[str]]:
    """已有条目（人工 + 结构化自动条目）已经答过的原文，不再重复切。"""
    quotes, answers = [], []
    def walk(ev):
        if isinstance(ev, dict):
            q = ev.get("quote")
            if q:
                quotes.append(sq(q))
            for v in ev.values():
                walk(v)
        elif isinstance(ev, list):
            for v in ev:
                walk(v)
    for it in items:
        walk(it.get("evidence"))
        if it.get("answer"):
            answers.append(sq(it["answer"]))
    return quotes, answers


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--sample", type=int, default=12)
    ap.add_argument("--random", action="store_true")
    ap.add_argument("--rebuild", action="store_true", help="先删掉已有的自动条目再重建")
    ap.add_argument("--include-news", action="store_true", help="新闻/活动报道也逐句成条（默认跳过）")
    args = ap.parse_args()

    data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    items = data["items"]
    if args.rebuild:
        # 只重建本脚本产的 pt- 条目；早先的结构化 auto 条目要留着
        items = [i for i in items if not i["id"].startswith("pt-")]
        data["items"] = items
    have_ids = {i["id"] for i in items}
    vocab = build_vocab(items)
    quotes, answers = existing_coverage(items)

    docs = load_indexes()
    units: dict[str, dict] = {}
    stat = Counter()
    doc_units = Counter()

    for doc in docs.values():
        p = text_path(doc)
        if not p:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if len(text) < 200:
            continue
        if NEWS_TITLE.search(doc.get("title") or "") and not args.include_news:
            stat["news_skip"] += 1
            continue
        if doc["slug"] in UNOFFICIAL:
            stat["unofficial_skip"] += 1
            continue
        stat["docs"] += 1
        raw_sq = sq(text)
        cl = clause_units(text, raw_sq)
        if cl:
            stat["clause_docs"] += 1
            for head, body, quote in cl:
                key = sq(body)
                units.setdefault(key, {"text": body, "quote": quote, "head": head, "doc": doc, "kind": "clause"})
        else:
            stat["para_docs"] += 1
            for para, quote in para_units(text, raw_sq):
                key = sq(para)
                units.setdefault(key, {"text": para, "quote": quote, "head": "", "doc": doc, "kind": "para"})

    # 同一段文字出现在多份文件里时，优先独立文件、带链接、非汇编
    chosen: dict[str, dict] = {}
    for key, u in units.items():
        cur = chosen.get(key)
        if not cur:
            chosen[key] = u
            continue
        def score(x):
            d = x["doc"]
            s = 0
            if "汇编" in d["title"]:
                s -= 30
            if d.get("url"):
                s += 5
            if d.get("published"):
                s += 2
            if "corpus" in d["collections"] or "wendao" in d["collections"]:
                s += 3
            return s
        if score(u) > score(cur):
            chosen[key] = u

    new_items = []
    for key, u in chosen.items():
        text = u["text"]
        bad = quality_problem(text)
        if bad:
            stat[bad] += 1
            continue
        best = max((len(q) for q in quotes if len(q) >= 12 and q in key), default=0)
        covered = best / len(key)
        if covered >= 0.9 or any(key in a for a in answers if len(a) >= len(key)):
            stat["covered"] += 1
            continue
        short = doc_short(doc_title(u["doc"], text))
        title = make_title(text, u["head"], short)
        kws = make_keywords(text, title, vocab)
        aliases = []
        for a in (re.sub(r"\s*·\s*.*$", "", title), title):
            a = a.strip()
            if 3 <= len(a) <= 40 and a not in aliases:
                aliases.append(a)
        if u["kind"] != "clause":
            for k in kws[:4]:
                if k not in aliases:
                    aliases.append(k)
        boiler = bool(BOILER.search(key)) and len(key) < 180
        # 每条官方原文都是条目；只有「本办法自发布之日起施行」这类
        # 纯手续套话不参与问答路由，但仍然保留在条目库里。
        archive = boiler
        iid = "pt-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        while iid in have_ids:
            iid += "x"
        source = {
            "title": doc_title(u["doc"], text),
            "url": u["doc"].get("url") or "",
            "checked": "2026-10-29",
        }
        if u["doc"].get("page"):
            source["page"] = u["doc"]["page"]
        item = {
            "id": iid,
            "title": title,
            "aliases": aliases[:6],
            "keywords": kws,
            "dept": "中国传媒大学",
            "channel": [],
            "audience": ["本科生", "研究生"],
            "status": "verified",
            "confidence": "medium",
            "materials": [],
            "steps": [],
            "fee": None,
            "location": None,
            "hours": None,
            "duration": None,
            "window": None,
            "pitfalls": [],
            "contact": None,
            "slots": [],
            "draft": None,
            "answer": text,
            "kind": "clause" if u["kind"] == "clause" else "paragraph",
            "source": [source],
            "evidence": {"answer": {"src": u["doc"]["slug"], "quote": u["quote"]}},
            "auto": True,
            "clause": u["kind"] == "clause",
            "para": u["kind"] == "para",
        }
        if archive:
            item["archive_only"] = True
        new_items.append(item)
        doc_units[u["doc"]["slug"]] += 1

    # 标题重复的只留第一条，避免同一句话在不同年份重复成多条
    seen_titles: set[str] = set()
    deduped = []
    for it in new_items:
        k = sq(it["title"])
        if k in seen_titles:
            continue
        seen_titles.add(k)
        deduped.append(it)
    new_items = deduped

    stat["units"] = len(chosen)
    stat["new_items"] = len(new_items)
    stat["archive_only"] = sum(1 for i in new_items if i.get("archive_only"))
    stat["clause_items"] = sum(1 for i in new_items if i["kind"] == "clause")
    stat["para_items"] = sum(1 for i in new_items if i["kind"] == "paragraph")
    print("统计：", dict(stat))
    rows = new_items
    if args.random:
        rows = __import__("random").sample(new_items, min(args.sample, len(new_items)))
    for it in rows[: args.sample]:
        print("-", it["title"], "|", it["keywords"][:4], "|", it["answer"][:60].replace("\n", " "))

    report = {
        "updated": "2026-10-29",
        **{k: v for k, v in stat.items()},
        "by_doc_top": doc_units.most_common(30),
    }
    (SRC / "clause-coverage.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    if args.out:
        Path(args.out).write_text(
            json.dumps(new_items, ensure_ascii=False), encoding="utf-8")
        print("written", args.out, len(new_items))
    if args.apply:
        data["items"].extend(new_items)
        data["updated"] = "2026-10-29"
        (ROOT / "items.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("written items.json, total", len(data["items"]))
    else:
        print("dry-run：未写入 items.json")


if __name__ == "__main__":
    main()
