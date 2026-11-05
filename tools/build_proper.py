"""从条目原文里抽「产品/系统专名」维度，产出 sources/proper.json。

为什么做：打分只认字面重合，「Adobe软件怎么激活」能靠「激活」顶到「统一身份认证账号激活」
上——专名在条目池里没有身份。这里把原文里出现的产品与系统名抽成维度，供 rank 做硬条件。

词表不手写：
- 拉丁名按词边界切（Adobe / WPS365 / VPN / Office），过滤 URL、域名与文件格式碎片；
- 中文名按原文的构词后缀抽（…系统 / …平台 / …门户 / …客户端 / …小程序 / …公众号 / …云盘 / …办事大厅），
  抽到的是正文里这么用的词，不是我凭空想的映射。
两边都要求至少 SUPPORT 个条目用过，孤例不算专名。

条目自带的 locators（人工写进数据的名字与缩写，如 Adobe 全家族的 ps/pr/ae）另走一路：
不过 _ok_latin（两字母缩写正是它挡掉的），也不受 SUPPORT 门槛限制——那是拍板写进去的定位器，
不是从正文里猜出来的。

用法：./.venv/Scripts/python.exe tools/build_proper.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
DST = ROOT / "sources" / "proper.json"
SUPPORT = 3
MAX_ITEMS = 1200          # 一个词被 1200 条以上条目用过，它就是通用词不是专名

URL_RE = re.compile(r"https?://\S+", re.I)
DOMAIN_RE = re.compile(r"[\w.-]+\.(?:edu|com|cn|org|net|gov|edu\.cn)(?:\.\w+)?", re.I)
PATH_RE = re.compile(r"[\w.-]*[?&=/][\w%./=&-]+")
# 只认字母数字连写：带连字符的拉丁串在 PDF 里多半是断行残片（associa-tion），
# 连字符留在字符集里会把一个词劈成 tion / atio 这种碎片，碎片进专名只会误降权。
LATIN_RE = re.compile(r"(?<![0-9A-Za-z])[A-Za-z][A-Za-z0-9]{1,15}(?![0-9A-Za-z])")
CN_SUFFIX = "系统|平台|门户|客户端|小程序|公众号|云盘|办事大厅|一体化平台|网上办事大厅|应用"
CN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]{2,8}(?:" + CN_SUFFIX + r")")
# 内部编号与碎片：文档 slug、纯十六进制、带年份的短横串
SLUG_RE = re.compile(r"^(?:[a-z]{1,8}[-_])?(?:[0-9a-f]{6,}|\d{4,})$")
HEXISH_RE = re.compile(r"^[a-z]{1,8}[0-9a-f]{6,}$")
# 一两个字母加数字是表格编号（A4、B008、Sheet1），不是产品名
LABEL_RE = re.compile(r"^(?:[a-z]{1,2}\d{0,4}|sheet\d*|table\d*|图\d*)$", re.I)
# 网页与文档的结构词，出现在正文里是路径或占位符，不是名字
ARTIFACT_RE = re.compile(
    r"^(?:part|section|chapter|fig|figure|image|img|editor|files?|file|page|mail|web"
    r"|data|test|demo|user|name|code|type|info|list|view|index|main|admin|x{3,})"
    r"(?:\d{1,4})?$")

# 这些拉丁串是文件/网页碎片或通用缩写，不是产品名
STOP = {
    "com", "cn", "www", "http", "https", "pdf", "doc", "docx", "xls", "xlsx", "ppt",
    "pptx", "png", "jpg", "jpeg", "gif", "bmp", "mp4", "mp3", "zip", "rar", "txt",
    "edu", "gov", "net", "org", "qq", "weixin", "wechat", "html", "htm", "php", "jsp",
    "api", "id", "no", "vs", "etc", "eg", "kb", "mb", "gb", "pc", "tel", "fax", "app",
    "new", "and", "for", "the", "andthe", "co", "inc", "edu", "vip", "cms", "oa",
    "true", "false", "null", "none", "src", "url", "uid", "res", "key", "name",
}


def _ok_latin(raw: str) -> bool:
    """原文里怎么写的，决定这个词是不是个名字。

    产品名的写法就那么几种：全大写（VPN）、首字母大写（Adobe）、带数字（WPS365）。
    PDF 正文里的断词残片是「WPSO PSOf SOff Offi」这种大小写乱串的形态，
    宁可漏，不可把残片当专名——残片进词表只会误降权。
    """
    t = raw.lower()
    if t in STOP or LABEL_RE.match(t) or SLUG_RE.match(t) or HEXISH_RE.match(t):
        return False
    has_digit = any(c.isdigit() for c in t)
    if not has_digit and not any(c.isupper() for c in raw):
        return False
    if len(t) < 3 and not has_digit:
        return False
    # 大小写形态：全大写 / 首字母大写（至少五个字）/ 大写接数字，其余按残片丢掉。
    # 首字母大写要五个字以上，是因为 PDF 断词残片常长成「Asso」「Inte」这种半截词，
    # 而 Adobe、Office、Springer 都够长。
    if not (raw.isupper() or (raw.istitle() and len(raw) >= 5)
            or re.fullmatch(r"[A-Z]{2,}[0-9]{1,6}", raw)
            or re.fullmatch(r"[A-Z]{2,}[A-Z][a-z]{3,}", raw)     # WPSOffice 这种连写名
            or (has_digit and re.fullmatch(r"[A-Za-z]+[0-9][A-Za-z0-9]*", raw))):
        return False
    if ARTIFACT_RE.match(t):
        return False
    return True


def item_text(item: dict) -> str:
    """条目的可读文字：标题、别名、关键词加上正文各字段。

    slots 是自动切的碎词、also_from 是文档编号，都不算原文用词，不进这里。
    """
    chunks: list[str] = [str(item.get("title") or "")]
    for k in ("aliases", "keywords"):
        chunks.extend(str(x) for x in (item.get(k) or []))
    for k in ("materials", "steps", "pitfalls", "contact"):
        v = item.get(k)
        if isinstance(v, list):
            for x in v:
                chunks.append(x if isinstance(x, str) else " ".join(
                    str(y) for y in (x.values() if isinstance(x, dict) else [])))
        elif v:
            chunks.append(str(v))
    for k in ("answer", "location", "para", "clause", "note", "summary"):
        if item.get(k):
            chunks.append(str(item[k]))
    ev = item.get("evidence")
    if isinstance(ev, dict):
        for v in ev.values():
            if isinstance(v, str):
                chunks.append(v)
            elif isinstance(v, list):
                chunks.extend(str(x) if isinstance(x, str) else " ".join(
                    str(y) for y in (x.values() if isinstance(x, dict) else [])) for x in v)
    return " ".join(chunks)


def extract(text: str) -> set[str]:
    t = PATH_RE.sub(" ", DOMAIN_RE.sub(" ", URL_RE.sub(" ", text)))
    out = {m.group(0).lower() for m in LATIN_RE.finditer(t) if _ok_latin(m.group(0))}
    out |= {m.group(0) for m in CN_RE.finditer(t)}
    return {x for x in out if x not in STOP}


def loc_names(item: dict) -> set[str]:
    """条目自带的定位器：小写，并按比对用的形态去掉空格。

    比对两头形态不一样——问句是按原样小写比（有空格），条目表面文字走 norm（空格被当标点删掉）。
    所以「after effects」这种带词界的名字两个写法都收下，少一个就有一头认不出。
    """
    out: set[str] = set()
    for x in item.get("locators") or []:
        t = str(x).strip().lower()
        if not t:
            continue
        out.add(t)
        tight = re.sub(r"\s+", "", t)
        if tight:
            out.add(tight)
    return out



def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    counts: Counter[str] = Counter()
    per_item: dict[str, list[str]] = {}
    forced: set[str] = set()          # 定位器：拍板写进数据的名字，不受孤例门槛管
    for it in items:
        toks = extract(item_text(it)) | loc_names(it)
        forced |= loc_names(it)
        if toks:
            per_item[it["id"]] = sorted(toks)
            counts.update(toks)
    vocab = {k for k, c in counts.items() if SUPPORT <= c < MAX_ITEMS} | forced
    # 短词容易被长词包含（「校园卡系统」含「校园卡」），只留各自独立的词
    items_map = {iid: sorted(t for t in toks if t in vocab) for iid, toks in per_item.items()}
    items_map = {iid: t for iid, t in items_map.items() if t}
    postings: dict[str, list[str]] = defaultdict(list)
    for iid, toks in items_map.items():
        for t in toks:
            postings[t].append(iid)
    payload = {
        "version": 2,
        "built_from": "items.json",
        "support": SUPPORT,
        "vocab": sorted(postings.keys()),
        "vocab_counts": {t: len(ids) for t, ids in postings.items()},
        "items": items_map,
    }
    DST.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    n_loc = sum(1 for it in items if it.get("locators"))
    print("条目", len(items), "有专名的条目", len(items_map), "词表", len(postings),
          "带定位器的条目", n_loc, "定位器词", len(forced))
    top = sorted(postings.items(), key=lambda kv: -len(kv[1]))[:40]
    for t, ids in top:
        print(f"  {t}\t{len(ids)}")
    print("wrote", DST, DST.stat().st_size, "bytes")


if __name__ == "__main__":
    sys.exit(main())
