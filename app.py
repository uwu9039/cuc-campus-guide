"""
校园办事向导 · 后端
- 意图识别：别名表 + 关键词打分（确定性，不走模型）
- 交付物生成：items.json 直接装配（确定性）
- 文书草稿：模板填槽；配了 Key 才用模型润色
- 拍照核对：deepseek-flash 视觉（可选）
"""
from __future__ import annotations

import base64
import contextvars
import functools
import gzip
import json
import os
import queue
import re
import sqlite3
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import prompt_parts as pp

ROOT = Path(__file__).parent
API_BASE = "https://api.deepseek.com"
MODEL = "deepseek-flash"
MATCH_THRESHOLD = 55
# 规则分落在 50~54 这一档：只靠二字组相似度凑出来，差一点够不着。
# 这一档不许直接作答，必须全文复核签字（任务 4，2026-11-04 拍板）。
NEAR_MISS_FLOOR = 50
AMBIGUOUS_GAP = 12

# ---------------------------------------------------------------- env / data


_ENV_MTIME: float | None = None
_ENV_KEYS: set[str] = set()
_HINTED = False


def _hint_key_in_example() -> None:
    """.env 不存在、但 .env.example 里填了 Key —— 最常见的放错位置。"""
    global _HINTED
    if _HINTED:
        return
    example = ROOT / ".env.example"
    try:
        if example.exists():
            for line in example.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DEEPSEEK_API_KEY=") and line.split("=", 1)[1].strip().strip("\"'"):
                    _HINTED = True
                    print("[提示] 检测到 .env.example 里填了 Key，但程序只读 .env。"
                          "请把 Key 写进 .env（模板文件会随仓库公开，别放真 Key）。")
                    return
    except OSError:
        pass
    _HINTED = True


def load_env(force: bool = False) -> None:
    """读 .env；文件被改过就重读，换 Key 不用重启。"""
    global _ENV_MTIME
    env = ROOT / ".env"
    if not env.exists():
        for k in list(_ENV_KEYS):  # 文件被删掉时，把之前注入的键撤掉
            os.environ.pop(k, None)
        _ENV_KEYS.clear()
        _ENV_MTIME = None
        _hint_key_in_example()
        return
    mtime = env.stat().st_mtime
    if not force and mtime == _ENV_MTIME:
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        os.environ[k] = v.strip().strip('"').strip("'")
        _ENV_KEYS.add(k)
    _ENV_MTIME = mtime


def api_key() -> str:
    load_env()
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


load_env()


def _items_file() -> Path:
    """仓库里大文件以 items.json.gz 发布：明文 31MB 走 GitHub 大请求体会超时，
    压缩后 2.8MB。本地有明文时仍优先用明文。"""
    plain = ROOT / "items.json"
    return plain if plain.exists() else ROOT / "items.json.gz"


def _read_items(path: Path) -> dict[str, Any]:
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    return json.loads(raw.decode("utf-8"))


DATA = _read_items(_items_file())
ITEMS: list[dict[str, Any]] = DATA["items"]
ITEM_BY_ID: dict[str, dict[str, Any]] = {i["id"]: i for i in ITEMS}
DATA_UPDATED = DATA.get("updated", "")
_MTIME = _items_file().stat().st_mtime
_SRC_ITEMS: dict[str, list[str]] | None = None


_RELATED_ROWS: list[tuple[dict[str, Any], str, str, str, bool]] | None = None
_WZY_SIBS: dict[str, list[dict[str, Any]]] = {}


def maybe_reload() -> None:
    """改了 items.json 不用重启服务。"""
    global DATA, ITEMS, ITEM_BY_ID, DATA_UPDATED, _MTIME, _SRC_ITEMS, _RELATED_ROWS
    global _WZY_SIBS, _PROPER, _PROPER_MENU
    path = _items_file()
    mtime = path.stat().st_mtime
    if mtime == _MTIME:
        return
    DATA = _read_items(path)
    ITEMS = DATA["items"]
    ITEM_BY_ID = {i["id"]: i for i in ITEMS}
    DATA_UPDATED = DATA.get("updated", "")
    _MTIME = mtime
    _SRC_ITEMS = None
    _RELATED_ROWS = None
    _WZY_SIBS.clear()
    _PROPER = None          # 专名维度是从条目正文抽的，条目换了就得重读
    _PROPER_MENU = None     # 给模型认名字的那份菜单也跟着条目重取
    _SURFACES.clear()


_TABLE_REC: list[dict[str, Any]] | None = None
_TABLE_MTIME = 0.0

# 专名维度（sources/proper.json，由 tools/build_proper.py 从条目原文抽）
_PROPER: dict[str, Any] | None = None


def proper_index() -> dict[str, Any]:
    """{tokens, postings, items}：词表、词→条目、条目→词。文件不在就当这个维度不存在。"""
    global _PROPER
    if _PROPER is not None:
        return _PROPER
    path = ROOT / "sources" / "proper.json"
    if not path.exists():
        _PROPER = {"tokens": [], "postings": {}, "items": {}}
        return _PROPER
    data = json.loads(path.read_text(encoding="utf-8"))
    items = {k: set(v) for k, v in (data.get("items") or {}).items()}
    postings: dict[str, set[str]] = {}
    for iid, toks in items.items():
        for t in toks:
            postings.setdefault(t, set()).add(iid)
    _PROPER = {"tokens": data.get("vocab") or sorted(postings), "postings": postings,
               "items": items}
    return _PROPER


def question_proper(q: str) -> set[str]:
    """问句点到的产品/系统名。按词表回查，不另立一套判断——问句大小写不固定。"""
    if not q:
        return set()
    pi = proper_index()
    if not pi["tokens"]:
        return set()
    ql = q.lower()
    out: set[str] = set()
    latin = pi.get("latin_re")
    if latin is None:
        toks = [t for t in pi["tokens"] if "a" <= t[0] <= "z"]
        # 长的排前面，免得「wps」先吃掉「wps365」
        toks.sort(key=len, reverse=True)
        # 边界只认 ASCII 字母数字：中文在 isalnum 里也算字母，用它是把「统」当墙，
        # 「…系统vpn怎么连」就会被判成 vpn 不成词。
        pat = "|".join(re.escape(t) for t in toks)
        pi["latin_re"] = re.compile(f"(?<![0-9a-z])(?:{pat})(?![0-9a-z])") if pat else None
        pi["latin_toks"] = toks
        latin = pi["latin_re"]
    if latin:
        out.update(m.group(0) for m in re.finditer(latin, ql))
    out.update(t for t in pi["tokens"] if t[0] >= "\u4e00" and t in ql)
    # 用户写的名字少了一截（「office」对条目里的「office365」）时按包含关系对上。
    # 只放宽到四个字母以上，且必须词表里确有这个词的一部分——不是拿词表去猜新别名。
    # 对上之后原词和词表词都留着：判条目「有没有点到这个名字」时要用用户说的那个词。
    for m in re.finditer(r"(?<![0-9a-z])[a-z][a-z0-9]{3,15}(?![0-9a-z])", ql):
        w = m.group(0)
        if any(w == t or w in t or t in w for t in out):
            continue
        near = {t for t in pi["latin_toks"]
                if len(t) >= 4 and (w in t or t in w) and abs(len(t) - len(w)) <= 5}
        if near:
            out.add(w)
            out.update(near)
    return out


_SURFACES: dict[str, str] = {}


_NAME_RE: dict[str, re.Pattern] = {}


def _name_re(t: str) -> re.Pattern:
    """名字怎么在一段文字里认出来：两三个字母的缩写按词边界认，其余照字面找。

    「ps」字面就躺在「wps365」里，纯子串判会把 WPS 条目算成写了 ps——
    2026-11-05 的错答正是这个形状，所以缩写必须有边界。
    """
    rx = _NAME_RE.get(t)
    if rx is None:
        esc = re.escape(t)
        if len(t) < 3 and t.isascii() and t.isalpha():
            rx = re.compile(f"(?<![0-9a-z]){esc}(?![0-9a-z])", re.I)
        else:
            rx = re.compile(esc, re.I)
        _NAME_RE[t] = rx
    return rx


def item_surface(item: dict[str, Any]) -> str:
    """条目自己叫什么：标题、别名、关键词拼在一起，算过一次就留着。"""
    iid = item.get("id", "")
    s = _SURFACES.get(iid)
    if s is None:
        s = _mn(" ".join([str(item.get("title") or "")]
                         + [str(x) for x in (item.get("aliases") or [])]
                         + [str(x) for x in (item.get("keywords") or [])]))
        _SURFACES[iid] = s
    return s


def names_product(item: dict[str, Any], qp: set[str]) -> bool:
    """这个条目有没有点到问句里那个名字。

    正文抽到的专名、标题/别名/关键词的字面，两条路都认；
    名字之间按互为包含算同一个（问「WPS365」不该把写了「WPS」的正版软件条目判成无关）。
    """
    ip = proper_index()["items"].get(item.get("id", ""))
    if ip:
        for a in ip:
            for b in qp:
                if a == b or (len(a) >= 3 and len(b) >= 3 and (a in b or b in a)):
                    return True
    surf = item_surface(item)
    # 长名字照旧按字面找（三万次比对里这路占多数），只有两三个字母的缩写才走边界判定
    return any(t in surf if len(t) >= 3 or not t.isascii() or not t.isalpha()
               else bool(_name_re(t).search(surf)) for t in qp)



def _table_file() -> Path:
    plain = ROOT / "table-rows.json"
    return plain if plain.exists() else ROOT / "table-rows.json.gz"


def table_records() -> list[dict[str, Any]]:
    """逐格的数据行拼成「一条记录」：同一 (doc, row_no) 的格子按列序排好，附带 bigram 索引。

    3.5 万格 ≈ 1.2 万条记录，建一次索引常驻内存，之后每次问只扫一遍 gram 集合。
    """
    global _TABLE_REC, _TABLE_MTIME
    path = _table_file()
    if not path.exists():
        return []
    mtime = path.stat().st_mtime
    if _TABLE_REC is not None and mtime == _TABLE_MTIME:
        return _TABLE_REC
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    rows = json.loads(raw.decode("utf-8"))
    grouped: dict[tuple[str, int], dict[str, Any]] = {}
    for r in rows:
        key = (str(r.get("doc", "")), int(r.get("row_no", 0) or 0))
        g = grouped.setdefault(key, {"doc": key[0], "bucket": r.get("bucket", ""),
                                     "title": r.get("title", ""), "row_no": key[1], "cells": []})
        g["cells"].append((str(r.get("header", "") or ""), str(r.get("value", "") or ""),
                           int(r.get("col", 0) or 0)))
    out: list[dict[str, Any]] = []
    for g in grouped.values():
        g["cells"].sort(key=lambda c: c[2])
        cells = [(h, v) for h, v, _ in g["cells"] if (h or v).strip()]
        if not cells:
            continue
        hay = norm("".join(g["title"] + h + v for h, v in cells))
        if len(hay) < 4:
            continue
        out.append({"doc": g["doc"], "bucket": g["bucket"], "title": g["title"],
                    "row_no": g["row_no"],
                    "text": "；".join(f"{h}：{v}" if h else v for h, v in cells),
                    "grams": bigrams(hay)})
    _TABLE_REC, _TABLE_MTIME = out, mtime
    return out


def table_search(q: str, k: int = 6, min_shared: int = 2) -> list[dict[str, Any]]:
    """按二元 gram 找最像这条问句的数据行；只回原文行与出处，不编造字段。

    先去掉语气词二字组：否则「怎么」「多少」这类框架词能让任意一行都凑够分。
    """
    qg = bigrams(norm(q)) - NOISE_BIGRAMS
    if not qg:
        return []
    scored: list[tuple[int, dict[str, Any]]] = []
    for rec in table_records():
        shared = len(qg & rec["grams"])
        if shared < min_shared:
            continue
        scored.append((shared, rec))
    scored.sort(key=lambda x: (-x[0], x[1]["doc"], x[1]["row_no"]))
    return [{"doc": rec["doc"], "title": rec["title"], "row_no": rec["row_no"],
             "text": rec["text"][:600], "shared": s, **src_label(rec["doc"])}
            for s, rec in scored[:k]]


_CAMPUS: dict[str, Any] | None = None
_CAMPUS_MTIME = 0.0


def _marker_url(name: str, lng: float, lat: float) -> str:
    return (f"https://uri.amap.com/marker?position={lng},{lat}"
            f"&name={urllib.parse.quote('中国传媒大学' + name)}&coordinate=gaode&callnative=0")


def _amap_search_url(keyword: str) -> str:
    """高德网页搜索页可以直接嵌进抽屉，不用 key，也不用登录。"""
    return ("https://www.amap.com/search?query="
            + urllib.parse.quote("中国传媒大学" + keyword) + "&city=北京")


# 官方简称对照表里的楼名/别名，挂到地图点位上，搜「48教」也能找到博学楼
BUILDING_ALIASES = {
    "立德楼": ["1教", "一教", "1号楼"],
    "博学楼": ["48教", "四十八教", "48号楼"],
    "明德楼": ["2号楼"],
    "国重大楼": ["22号楼"],
    "艺术与传播大楼": ["27号楼", "艺传大楼"],
    "图书馆": ["49号楼", "大阅城"],
    "中传礼堂": ["1500报", "1500人报告厅", "大报告厅", "大礼堂"],
    "中传讲堂": ["400报", "400人报告厅", "小讲堂"],
    "中传演播馆": ["1400", "1400平米演播馆", "4K演播馆"],
    "手球馆": ["羽毛球馆", "新利体育馆"],
    "游泳馆": ["水立方"],
    "大学生活动中心": ["大活", "55号楼"],
    "艺术展览中心": ["艺展中心"],
}

# 高德搜索词：场馆缩在楼里时，地图要定位到那栋楼（如礼堂/讲堂→国重大楼）
MAP_QUERY: dict[str, tuple[str, str]] = {
    "立德楼": ("立德楼", "立德楼（1教）"),
    "博学楼": ("48号楼", "48教 = 博学楼（48号楼）"),
    "明德楼（2号楼）": ("明德楼", "明德楼（2号楼）"),
    "国重大楼（22号楼）": ("国重大楼", "国重大楼（22号楼）"),
    "艺术与传播大楼": ("艺术与传播大楼", "艺术与传播大楼（27号楼）"),
    "图书馆": ("图书馆", "图书馆（49号楼·大阅城）"),
    "校医院": ("20号楼", "校医院（20号楼）"),
    "中传礼堂": ("国重大楼", "中传礼堂在国重大楼 1 层"),
    "中传讲堂": ("国重大楼", "中传讲堂在国重大楼 1 层"),
    "中传演播馆": ("中传演播馆", "中传演播馆（2号楼 A 座 2 层）"),
    "手球馆": ("手球馆", "手球馆（51号楼）"),
    "游泳馆": ("游泳馆", "游泳馆"),
    "艺术展览中心": ("艺术展览中心", "艺术展览中心"),
    "大学生活动中心": ("大学生活动中心", "大学生活动中心（55号楼）"),
    "操场（南操场）": ("南操场", "南操场"),
    "主楼": ("主楼", "主楼"),
    "快递驿站（菜鸟驿站）": ("菜鸟驿站", "菜鸟驿站（临建1）"),
    "北苑餐厅": ("北苑餐厅", "北苑餐厅"),
    "溢香苑餐厅": ("溢香苑餐厅", "溢香苑餐厅（40号楼）"),
    "21号楼（国际交流中心）": ("21号楼", "21号楼（国际交流中心）"),
    "21号楼": ("21号楼", "21号楼（国际交流中心）"),
    "30号楼（保卫处综合服务厅）": ("30号楼", "30号楼（保卫处综合服务厅）"),
    "30号楼": ("30号楼", "30号楼（保卫处综合服务厅）"),
    "4K放映厅": ("图书馆", "4K放映厅在图书馆（大阅城）副楼2层"),
    "圆形报告厅": ("图书馆", "圆形报告厅在图书馆（大阅城）副楼2层"),
}


def _merge_campus_coords(data: dict[str, Any]) -> dict[str, Any]:
    """把 campus-map.json 里核实过的坐标并到楼宇清单上；没坐标的仍然只有原文位置。"""
    path = ROOT / "campus-map.json"
    if not path.exists():
        return data
    cm = json.loads(path.read_text(encoding="utf-8"))
    coord = cm.get("pois") or []
    index: dict[str, dict[str, Any]] = {}
    for c in coord:
        for k in [c.get("name", ""), *(c.get("aliases") or [])]:
            nk = norm(k)
            if nk:
                index.setdefault(nk, c)
    pois = data.get("pois") or []
    for p in pois:
        extra_alias = BUILDING_ALIASES.get(p.get("name", ""))
        if extra_alias:
            p["aliases"] = list(dict.fromkeys([*(p.get("aliases") or []), *extra_alias]))
    seen: set[str] = set()
    for p in pois:
        c = index.get(norm(p.get("name", "")))
        if c and c.get("lat") and c.get("lng"):
            p["lat"], p["lng"] = c["lat"], c["lng"]
            p["coord_confidence"] = c.get("confidence", "")
            p["amap_marker"] = _marker_url(p["name"], c["lng"], c["lat"])
        seen.add(norm(p.get("name", "")))
    for c in coord:
        nk = norm(c.get("name", ""))
        if not nk or nk in seen:
            continue
        row = {
            "name": c["name"],
            "place": c.get("address") or (c.get("note") or "")[:40],
            "kind": {"gate": "校门", "canteen": "食堂", "building": "楼宇", "sport": "场馆"}.get(c.get("category", ""), "地点"),
            "src": "campus-map",
            "aliases": c.get("aliases") or [],
            "amap": _amap_search_url(c["name"]),
        }
        if c.get("lat") and c.get("lng"):
            row["lat"], row["lng"] = c["lat"], c["lng"]
            row["coord_confidence"] = c.get("confidence", "")
            row["amap_marker"] = _marker_url(c["name"], c["lng"], c["lat"])
        pois.append(row)
        seen.add(nk)
    data["pois"] = pois
    for p in pois:
        extra_alias = BUILDING_ALIASES.get(p.get("name", ""))
        if extra_alias:
            p["aliases"] = list(dict.fromkeys([*(p.get("aliases") or []), *extra_alias]))
        meta = MAP_QUERY.get(p.get("name", ""))
        if not meta:
            nk = norm(p.get("name", ""))
            meta = next((v for k, v in MAP_QUERY.items() if norm(k) == nk), None)
        keyword, label = meta or (
            re.sub(r"[（(].*?[）)]", "", p.get("name", "")), p.get("name", ""))
        p["map_query"] = keyword
        p["map_label"] = label
        p["amap_search"] = _amap_search_url(keyword)
    data["count"] = len(pois)
    data["coords"] = sum(1 for p in pois if p.get("lat") and p.get("lng"))
    data["coords_note"] = cm.get("notes") or ""
    return data


def campus_data() -> dict[str, Any]:
    global _CAMPUS, _CAMPUS_MTIME
    path = ROOT / "sources" / "campus-pois.json"
    extra = ROOT / "campus-map.json"
    if not path.exists():
        # 精简部署可能没带 sources/，用 campus-map.json 兜底，地点名仍然能链接化。
        if not extra.exists():
            return {"pois": [], "center": None, "count": 0}
        mtime = extra.stat().st_mtime
        if _CAMPUS is None or mtime != _CAMPUS_MTIME:
            _CAMPUS = _merge_campus_coords({"pois": [], "center": None, "count": 0})
            _CAMPUS_MTIME = mtime
        return _CAMPUS
    mtime = path.stat().st_mtime + (extra.stat().st_mtime if extra.exists() else 0)
    if _CAMPUS is None or mtime != _CAMPUS_MTIME:
        _CAMPUS = _merge_campus_coords(json.loads(path.read_text(encoding="utf-8")))
        _CAMPUS_MTIME = mtime
    return _CAMPUS


PLACE_ASK = re.compile(r"在哪|在哪里|在哪儿|在哪个楼|怎么走|怎么去|位置|路线|导航")
_PLACE_SUFFIX = re.compile(r"(在哪里|在哪儿|在哪|在哪个楼|的位置|位置|怎么走|怎么去|路线|导航|呢|啊|呀)+$")

# 只说转专业、没点目标学院时先反问；提到这些词说明是在打听，不是顺口带到
_TRANSFER_ASK = re.compile(
    r"转专业|转入|转到|转去|转进|换专业|接收计划|接收条件"
)
_TRANSFER_CONSULT = re.compile(
    r"咨询|问|想|要|怎么|怎样|如何|条件|要求|流程|政策|规定|时间|难|情况|事宜|哪些|哪个|吗|呢|？|\?"
)
# 问的是转专业的某个具体面（时间/条件/考试…），不该反问学院
_TRANSFER_FACET = re.compile(
    r"时间|什么时候|何时|截止|几月|流程|步骤|材料|条件|要求|考试|面试|名额|比例|"
    r"资格|成绩|绩点|学费|费用|政策|规定|办法|细则|文件|方案|难|双学位|辅修|保研|推免|交换|出国|"
    r"跨学院|跨专业|志愿|课程|学分|再申请|申请|研究生|硕士|博士|导师"
)

# 只问地址的短句：直接给那一处的位置，不再端出整张对照表
PLACE_ONLY = re.compile(
    r"^[^，。？！,?]{2,12}(在哪|在哪里|在哪儿|在哪个楼|怎么走|怎么去|的位置|位置)(呀|啊|呢|嘛)?[？?]?$"
)

# 点名地点时的一句话答复：名称对应 + 官方位置表里的楼层/楼号
PLACE_LINES: dict[str, tuple[str, str, str]] = {
    "立德楼": ("一教 = 1教 = 立德楼（1号楼）", "2025-08-21-4797ab1b",
              "中国传媒大学立德楼即1号教学楼"),
    "博学楼": ("48教 = 四十八教 = 博学楼（48号楼）", "1b97d899",
              "位于48号楼（博学楼）101"),
    "明德楼（2号楼）": ("明德楼 = 2号楼", "1b97d899",
                    "位于2号楼（明德楼）9层913，914"),
    "国重大楼（22号楼）": ("国重大楼 = 22号楼，1层是中传礼堂（1500报）和中传讲堂（400报）", "1b97d899",
                      "位于22号楼（国重大楼）1层"),
    "艺术与传播大楼": ("艺术与传播大楼 = 27号楼，在南操场西边、艺术展览中心北边", "1b97d899",
                 "位于南操场西边，艺术展览中心北边，阳明书院南边。艺传大楼是 2024年新建的楼。"),
    "图书馆": ("图书馆 = 49号楼（大阅城）", "1b97d899",
             "图书馆的位置(办公地点)：\n位于49号楼（大阅城）"),
    "校医院": ("校医院 = 校内20号楼（原幼儿园）", "1b97d899",
             "校医院的位置(办公地点)：\n位于校内20号楼（原幼儿园）"),
    "中传礼堂": ("中传礼堂 = 1500报 = 1500人报告厅，在国重大楼（22号楼）1层", "c497abf6",
              "中传礼堂/中传讲堂/1500 人报告厅/400 人报告厅/1500 报/400 报位于国重大楼的一层。"),
    "中传讲堂": ("中传讲堂 = 400报 = 400人报告厅，在国重大楼（22号楼）1层", "c497abf6",
              "中传礼堂/中传讲堂/1500 人报告厅/400 人报告厅/1500 报/400 报位于国重大楼的一层。"),
    "中传演播馆": ("中传演播馆 = 1400平米演播馆 = 4K演播馆，在2号楼（明德楼）2层，从中传学术中心入口（2号楼西门）进", "c497abf6",
               "中传演播馆位于2 号楼A 座2 层，您可以从中传学术中心入口（2 号楼西门）进入。"),
    "手球馆": ("手球馆 = 羽毛球馆 = 新利体育馆，在51号楼，可走游泳馆北侧地下通道", "c497abf6",
             "手球馆/羽毛球馆位于学校的东北角，您可以从游泳馆北侧的地下通道进入。"),
    "游泳馆": ("游泳馆 = 游泳池 = 水立方", "cd72bce4",
             "游泳馆=游泳池、游泳的地方、游泳馆、水立方"),
    "大学生活动中心": ("大学生活动中心 = 大活 = 55号楼，1层是体育馆", "1b97d899",
                 "大学生活动中心体育馆的位置(办公地点)：\n位于55号楼（大学生活动中心）1层"),
    "艺术展览中心": ("艺术展览中心 = 艺展中心（原南苑餐厅），在南操场西边、艺传大楼南边", "c497abf6",
                "艺术展览中心位于南操场西边，艺术与传播大楼（新建）的南边。"),
    "主楼": ("主楼 = 南门正对着的高楼，东西两边是东配楼、西配楼", "1b97d899",
             "主楼的位置(办公地点)：\n位于中国传媒大学南门正对着的高楼，东西两边分别是东配楼和西配楼。"),
    "操场（南操场）": ("操场 = 南操场 = 南操 = 田径场 = 风雨操场", "cd72bce4",
                  "操场=风雨操场=南操场=南操=田径场"),
    "中传学术中心": ("中传学术中心 = 学术中心，在2号楼（明德楼）正后方，正门朝西", "1b97d899",
                "中传学术中心的位置(办公地点)：\n位于2号楼明德楼正后方，正门朝西。"),
    "快递驿站（菜鸟驿站）": ("快递驿站 = 菜鸟驿站，在临建1（47号楼东侧、44号楼北侧）", "1b97d899",
                     "校内菜鸟驿站的位置(办公地点)：\n位于临建1（47号楼东侧，44号楼北侧）。"),
    "21号楼（国际交流中心）": ("21号楼 = 国际交流中心，在南操场正东边", "1b97d899",
                       "位于南操场正东边，一栋棕色高楼。"),
    "21号楼": ("21号楼 = 国际交流中心，在南操场正东边", "1b97d899",
             "位于南操场正东边，一栋棕色高楼。"),
    "30号楼（保卫处综合服务厅）": ("30号楼 = 保卫处综合服务厅，在南操场正西边", "1b97d899",
                         "位于南操场正西边的二层楼房，艺传大楼正东边，地下停车场西南入口左侧。"),
    "30号楼": ("30号楼 = 保卫处综合服务厅，在南操场正西边", "1b97d899",
             "位于南操场正西边的二层楼房，艺传大楼正东边，地下停车场西南入口左侧。"),
}

# 场馆问题落到「场馆在哪」条目，其余地点落到「楼宇名称与位置速查」
VENUE_PLACE_NAMES = {
    "中传礼堂", "中传讲堂", "中传演播馆", "手球馆", "游泳馆",
    "艺术展览中心", "大学生活动中心", "中传音乐厅", "圆形报告厅", "4K放映厅",
}


_PLACE_QUOTES: dict[str, str] | None = None


def place_quotes() -> dict[str, str]:
    """官方位置表里每处地点的原句：`X的位置(办公地点)：位于…`。"""
    global _PLACE_QUOTES
    if _PLACE_QUOTES is None:
        _PLACE_QUOTES = {}
        path = ROOT / "sources" / "wendao-text" / "1b97d899.txt"
        if path.exists():
            cur = ""
            for raw in path.read_text(encoding="utf-8").splitlines():
                ln = raw.strip()
                m = re.match(r"^\d+、(.+?)的位置\(办公地点\)：$", ln)
                if m:
                    cur = m.group(1).strip()
                    continue
                if cur and ln:
                    _PLACE_QUOTES.setdefault(cur, f"{cur}的位置(办公地点)：{ln}")
                    cur = ""
    return _PLACE_QUOTES


def _place_meta(name: str) -> tuple[str, str, str]:
    if name in PLACE_LINES:
        return PLACE_LINES[name]
    nk = norm(name)
    for k, v in PLACE_LINES.items():
        if norm(k) == nk:
            return v
    return ("", "", "")


def _place_payload(p: dict[str, Any]) -> dict[str, Any]:
    name = p.get("name", "")
    keyword = p.get("map_query") or re.sub(r"[（(].*?[）)]", "", name)
    line, src, quote = _place_meta(name)
    if not line:
        q = place_quotes().get(name, "")
        place = (p.get("place") or "").strip()
        if q and "：" in q:
            place = q.split("：", 1)[1].strip()
            if place.startswith("位于"):
                place = place[2:]
            place = place.rstrip("。")
            src, quote = "1b97d899", q
        line = f"{name}在{place}。" if place else name
    return {
        "name": name,
        "keyword": keyword,
        "label": p.get("map_label") or name,
        "query": "中国传媒大学" + keyword,
        "url": p.get("amap_search") or _amap_search_url(keyword),
        "marker": p.get("amap_marker") or "",
        "place": p.get("place") or "",
        "line": line,
        "src": src,
        "quote": quote,
    }


def _find_span(n: str, q: str) -> int:
    """在 q 里找简称 n；1号楼 不能嵌在 21号楼 里。"""
    start = 0
    while True:
        i = q.find(n, start)
        if i < 0:
            return -1
        before = q[i - 1] if i > 0 else ""
        after = q[i + len(n)] if i + len(n) < len(q) else ""
        if not (n[0].isdigit() and before.isdigit()) and not (n[-1].isdigit() and after.isdigit()):
            return i
        start = i + 1


def _place_names() -> set[str]:
    names: set[str] = set()
    for p in campus_data().get("pois") or []:
        for raw in [p.get("name", ""), *(p.get("aliases") or [])]:
            for n in (norm(raw), norm(re.sub(r"[（(].*?[）)]", "", raw))):
                if len(n) >= 2:
                    names.add(n)
    return names


def map_places(text: str) -> list[dict[str, Any]]:
    """问句里点到哪几处校园地点，就按提到的顺序各给一条；地图用最后提到的那处。"""
    q = norm(_PLACE_SUFFIX.sub("", (text or "").strip()))
    if len(q) < 2:
        return []
    if not PLACE_ASK.search(text) and q not in _place_names():
        return []
    hits: list[tuple[int, int, int, int, dict[str, Any]]] = []
    for p in campus_data().get("pois") or []:
        pname = norm(p.get("name", ""))
        best: tuple[int, int, int] | None = None
        for raw in [p.get("name", ""), *(p.get("aliases") or [])]:
            n = norm(raw)
            if len(n) < 2:
                continue
            pos = _find_span(n, q)
            if pos < 0:
                continue
            cand = (1 if n in pname else 0, len(n), pos)
            if best is None or cand > best:
                best = cand
        if best is None and len(q) >= 2 and q in pname:
            best = (1, len(q), 0)
        if best:
            hits.append((*best, len(pname), p))

    # 同一段字面被多条数据命中时，留最像“本体”的那条：楼名命中优先、名字更短优先
    by_span: dict[tuple[int, int], tuple[int, int, int, int, dict[str, Any]]] = {}
    for pos_len in hits:
        is_name, mlen, pos, nlen, p = pos_len
        span = (pos, mlen)
        cur = by_span.get(span)
        if cur is None or (is_name, -nlen) > (cur[0], -cur[3]):
            by_span[span] = pos_len

    # 同一处地点说了两遍只回一次，位置取最后一次提到的
    by_name: dict[str, tuple[int, dict[str, Any]]] = {}
    for _is_name, _mlen, pos, _nlen, p in by_span.values():
        k = norm(p.get("name", ""))
        prev = by_name.get(k)
        if prev is None or pos >= prev[0]:
            by_name[k] = (pos, p)

    rows = sorted(by_name.values(), key=lambda x: x[0])
    return [_place_payload(p) for _, p in rows[-3:]]


def map_place(text: str) -> dict[str, Any] | None:
    rows = map_places(text)
    return rows[-1] if rows else None


def _place_exact(text: str, places: list[dict[str, Any]]) -> bool:
    """整句只点了这些地点，没再问楼里的某个房间/区域。

    「图书馆在哪」走地点速答；「图书馆外文阅览区在哪」问的是馆内区域，
    不能被「图书馆 = 49号楼」这句话吞掉。
    """
    q = norm(_PLACE_SUFFIX.sub("", (text or "").strip()))
    names = {p.get("name", "") for p in places}
    for p in campus_data().get("pois") or []:
        if p.get("name") not in names:
            continue
        for raw in [p.get("name", ""), *(p.get("aliases") or [])]:
            n = norm(raw)
            if len(n) >= 2:
                q = q.replace(n, "")
    for p in places:
        for raw in (p.get("name", ""), p.get("keyword", ""), p.get("label", "")):
            n = norm(raw)
            if len(n) >= 2:
                q = q.replace(n, "")
    return len(q) <= 1


def _named_place_item(places: list[dict[str, Any]]) -> dict[str, Any] | None:
    """地点本身就是一条具体事项（如快递驿站）时，交给事项回答，信息更全。"""
    names = {norm(p["name"]) for p in places}
    for it in ITEMS:
        # 自动摘录的正文条目不是地点条目，别让它顶掉地图答案
        if it.get("auto") or it.get("archive_only") or it["id"].startswith("campus-"):
            continue
        if re.search(r"借用|预约|申请|办理|查询|入口|清单|对照", it["title"]):
            continue
        for raw in (it["title"], *it.get("aliases", [])):
            k = norm(raw)
            if len(k) < 3:
                continue
            # 只认「地点名本身」或「地点名+位置/地址」：否则「校医院报销」
            # 这种带业务后缀的别名会把问路抢成报销条目。
            for n in names:
                if k == n or (k.startswith(n) and k[len(n):] in ("位置", "地址", "在哪", "在哪里")):
                    return it
    return None


# ---------------------------------------------------------------- matching

PUNCT = re.compile(r"[\s，。！？、；：\"'“”‘’（）()【】\[\]《》—…·.,!?;:]")


def norm(s: str) -> str:
    return PUNCT.sub("", (s or "").lower())


def bigrams(s: str) -> set[str]:
    return {s[i : i + 2] for i in range(len(s) - 1)}


def trigrams(s: str) -> set[str]:
    return {s[i : i + 3] for i in range(len(s) - 2)}


# 这些二字组只表示语气或文书类型，不能作为"说的是同一件事"的证据：
# 「宿舍能不能养猫」不该因为「能不能」粘到「能不能毕业」。
NOISE_BIGRAMS = {
    "能不", "不能", "怎么", "么办", "如何", "可以", "是否", "在哪", "哪儿", "哪里",
    "什么", "时候", "需要", "不用", "我要", "想问", "请问", "一下", "这个", "那个",
    "哪些", "多少", "为什", "行不", "行吗",
    "办法", "规定", "通知", "管理", "实施", "细则", "制度", "方案", "条例", "意见",
}
# 问句框架字：只共享这些字，说明问的是同一个句式，不是同一件事
FRAME_CHARS = set("能不能怎么么吗呢吧啊呀哪里什么时侯需要可以是还行不要")

# 自动抽取的条目常挂着「办法」「申请」这类万能词，单独命中不算线索。
GENERIC_KEYWORDS = {
    "办法", "规定", "通知", "管理", "实施", "细则", "制度", "方案", "条例", "意见",
    "工作", "学生", "学校", "学院", "本科", "研究生", "本科生", "在校生", "全校",
    "申请", "办理", "补办", "流程", "材料", "时间", "地点", "条件", "要求", "手续",
    "报名",
}

# 问句里的语气与套话：拆掉之后「校园卡怎么延期」才能和「校园卡延期」对上。
# 「怎么办」要放在「怎么」前面，否则会剩下一个孤零零的「办」。
_ASK_FILLER = re.compile(r"怎么办|怎么弄|怎样|怎么|如何|咋办|咋整|请问|想问|一下|我要|我想|应该|具体|[呢吗啊呀吧]+$")

# 只当范围词用的场所名：光凭它们命中，不足以确认“没有”这个结论
# （否则「宿舍有电梯吗」会被「宿舍不提供被子」的段落条目当成否定答案）
GENERIC_PLACE = {"宿舍", "校园", "食堂", "图书馆", "教学楼", "教室", "操场", "校医院", "超市"}


TRAILING_PAREN = re.compile(r"[（(][^（()）]*[）)]\s*$")
LEADING_DOC_NO = re.compile(r"^[^\s，,。]{0,12}〔\d{4}〕\s*\d+\s*号\s*")


def core_title(title: str) -> str:
    """去掉标题里的文号和尾部括号补充：
    「中传教字〔2025〕7号 中国传媒大学…办法」→「中国传媒大学…办法」；
    「公共实践场馆预约（演播馆 / 音乐厅）」→「公共实践场馆预约」。"""
    t = LEADING_DOC_NO.sub("", title or "")
    while True:
        nxt = TRAILING_PAREN.sub("", t).strip()
        if nxt == t:
            return t
        t = nxt


def _same_phrase(a: str, b: str) -> bool:
    """「我校本科」和「校本科生」是同一条短语的错位切法，不能算两次命中。"""
    if a in b or b in a:
        return True
    if min(len(a), len(b)) < 3:
        return False
    best = 0
    for i in range(len(a)):
        for j in range(i + best + 1, len(a) + 1):
            if a[i:j] in b:
                best = max(best, j - i)
            else:
                break
    return best / min(len(a), len(b)) >= 0.6


def score_item(q: str, item: dict[str, Any], blocked: set[str] | None = None) -> int:
    if not q:
        return 0
    # 近词排除：「第二学士学位」和「双学士学位」只差一个限定词，但不是一回事。
    for bad in item.get("exclude", []):
        b = norm(bad)
        if b and b in q:
            return 0
    # 整句就是更宽的上位词时不算：「学士学位」不该落到「双学士学位」条目上
    for bad in item.get("exclude_exact", []):
        if q == norm(bad):
            return 0
    # 条目只在一个语境里有意义时，先要求问句里出现这个语境词：
    # 「体测与评奖」不能把泛泛的「评奖评优有哪些」「毕业离校怎么办」都吸过来
    req = item.get("require")
    if isinstance(req, list) and req:
        if not any((r := norm(str(x))) and r in q for x in req):
            return 0
    blocked = blocked or set()
    best = 0
    qp = _ASK_FILLER.sub("", q)
    is_text = bool(item.get("clause") or item.get("para"))
    keys = [item["title"], core_title(item["title"]), *item.get("aliases", [])]
    for raw in keys:
        a = norm(raw)
        if not a or a in blocked or a in GENERIC_KEYWORDS:
            continue
        if a == q:
            return 100
        if a == qp and len(a) >= 3:
            best = max(best, 97)
            continue
        if is_text:
            # 原文条目是整句摘录，标题长、关键词也是自动抽的：
            # 只认「整句标题出现在问句里」或「问句覆盖了标题大半」，避免泛词误配
            if len(a) >= 6 and len(q) >= 6 and (a in q or (q in a and len(q) * 2 >= len(a))):
                best = max(best, 80 + min(10, len(a)))
            continue
        if a in q:
            sc = 82 + min(10, len(a))
            if q.startswith(a) and len(a) >= 4:
                # 句首往往就是主语：「短视频微专业怎么报名」的主语是短视频微专业，
                # 不该被排在后面的「微专业」总览同分抢走。
                sc += 2
                head_hit = True
            best = max(best, sc)
        elif a in qp and len(a) >= 3:
            # 去掉「怎么」「请问」之后仍原样出现，按整词命中算：
            # 「校园卡怎么延期」里的「校园卡延期」就是条目本名。
            sc = 84 + min(8, len(a))
            if qp.startswith(a) and len(a) >= 4:
                sc += 2
            best = max(best, sc)
        elif q in a:
            best = max(best, 70 + min(8, len(q)))

    title_best = best

    # 关键词层：命中越多越可信（「校园卡+挂失+解挂」应当压过泛泛的「校园卡」）
    matched: list[str] = []
    for raw in item.get("keywords", []):
        k = norm(raw)
        if not k or k in blocked or k in GENERIC_KEYWORDS or k not in q:
            continue
        # 「补考」「有补考」「所有补考」是同一个词的不同切法，不能算三次命中
        if k in matched or any(k != o and _same_phrase(k, o) for o in matched):
            continue
        matched = [o for o in matched if not (o != k and _same_phrase(o, k))]
        matched.append(k)
    hits = len(matched)
    kw_best = max((84 + min(8, len(k)) for k in matched), default=0)
    if hits:
        best = max(best, kw_best + (hits - 1) * 7)

    # 「补考记多少分」这种问法只重合「补考」一个词，但意图非常明确：
    # 命中考试方式词 + 问分数 + 原文就是记分规定，可以答。
    score_intent = bool(
        hits >= 1 and re.search(r"多少分|几分|记多少|多少成绩|按多少", q)
        and any(k in {"补考", "重考", "重修", "缓考", "免修"} for k in matched)
        and re.search(r"六十分|60分|按\d+分|记为零分", item.get("answer") or ""))
    if score_intent:
        best = max(best, 90)

    # 条款条目是一条具体规定，标题就是原文那句：
    # 允许「补考+成绩」这类实词命中，否则自然问句永远够不着。
    if item.get("clause"):
        if title_best >= 70:
            return title_best
        return min(best, 99) if ((hits >= 2 and len(q) >= 5) or score_intent) else 0

    # 段落条目自动抽的关键词噪声大：标题对得上才算，或者命中三个以上关键词；
    # 两句以内的短事实本身就是一个信息点，两个关键词即可。
    if item.get("para"):
        if title_best >= 70:
            return title_best
        short = len(item.get("answer") or "") <= 60
        if score_intent:
            return min(best, 99)
        # 「本科生有补考吗」：短事实里明确回答“没有”的，一个关键词也够。
        # 只认成句的否定词——裸「无」会把「无线网覆盖…」当成“宿舍没有电梯”。
        # 命中的只有「宿舍」这类场所范围词时也不够：它证明不了问的那个东西不存在。
        if (hits >= 1 and short and re.search(r"有没有|有吗|有.*吗|是否存在", q)
                and any(k not in GENERIC_PLACE for k in matched)
                and re.search(r"没有|不存在|不提供|不开设|不允许|不支持|不设|暂无", item.get("answer") or "")):
            return min(best, 99)
        return (min(best, 99) if (hits >= 3 and len(q) >= 8)
                else min(best, 99) if (hits >= 2 and len(q) >= 5 and short) else 0)

    # 二元组相似度兜底（同义改写）
    qb = bigrams(q)
    if qb:
        for raw in [*keys, *item.get("keywords", [])]:
            a = norm(raw)
            if len(a) < 2 or a in blocked or a in GENERIC_KEYWORDS:
                continue
            ab = bigrams(a)
            if not ab:
                continue
            shared_set = qb & ab
            # 只靠语气词/文书类型重合，不算说的是同一件事
            if not shared_set or shared_set <= NOISE_BIGRAMS:
                continue
            shared = len(shared_set)
            # 短问句只共用一个二字词时不认：否则「双学位」会靠「学位」二字
            # 粘到「学位证明书」上，「补卡」会粘到任何带「补」的事项上。
            if shared < 2 and len(q) <= 4:
                continue
            # 「宿舍能不能换」和「宿舍能不能养猫」共享的只是问句框架
            content = {b for b in shared_set if not (set(b) & FRAME_CHARS)}
            if not content:
                continue
            if len(content) < 2 and not any(
                    not (set(t) & FRAME_CHARS) for t in trigrams(q) & trigrams(a)):
                continue
            # 两个泛化二字词拼出来的相似不算同义改写（「双学位申请」vs
            # 「学位证明书申请表」共享「学位」「申请」，但没有一个连续三字片段）。
            if len(q) >= 3 and len(a) >= 3 and not (trigrams(q) & trigrams(a)):
                continue
            dice = 2 * shared / (len(qb) + len(ab))
            if dice >= 0.34:
                best = max(best, int(40 + 30 * dice))
    # 100 只留给标题/别名原样命中：多个关键词叠加最多到 99，
    # 否则「学制」这类问法会被总览的长关键词堆到 106，压过学制条目本身。
    return min(best, 99)


def blocked_keys(qn: str) -> dict[str, set[str]]:
    """长词优先：短词只出现在长词内部时不算数。

    「保留学籍」里的「留学」不能把问题推给出国留学；
    「勤工助学」里的「助学」同理。同一短词在别处独立出现时仍然有效。
    """
    occ: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for it in ITEMS:
        if it.get("archive_only") or it.get("clause") or it.get("para"):
            continue
        for raw in [it["title"], core_title(it["title"]), *it.get("aliases", []), *it.get("keywords", [])]:
            k = norm(raw)
            if not k:
                continue
            start = qn.find(k)
            while start != -1:
                occ.setdefault((it["id"], k), []).append((start, start + len(k)))
                start = qn.find(k, start + 1)

    spans = [(s, e, iid) for (iid, _), lst in occ.items() for s, e in lst]
    blocked: dict[str, set[str]] = {}
    for (iid, k), lst in occ.items():
        if all(
            any(e2 - s2 > e - s and s2 <= s and e2 >= e and iid2 != iid for s2, e2, iid2 in spans)
            for s, e in lst
        ):
            blocked.setdefault(iid, set()).add(k)
    return blocked


def _asks_score_rule(qn: str) -> bool:
    return bool(re.search(r"多少分|几分|记多少|按多少|怎么记|怎么算|如何记|如何算|怎算", qn))


def _rule_affinity(qn: str, item: dict[str, Any]) -> int:
    """同分时，问「记多少分」就优先答得出具体分值的条目。

    补考/重修的规定有十几条，讲报名时间、选课限制的条款和讲记分的条款
    常常同样命中关键词；问的是分数，就该把写着「记为六十分」的那条顶上来。
    """
    if not _asks_score_rule(qn):
        return 0
    # 只认「60 分 / 按 N 分」这类定分规则；
    # 「记为零分」是作弊处理，不是补考记分办法。
    # 人工条目的正文写在 steps/pitfalls 里，不能只看 answer。
    texts = [item.get("answer") or ""]
    texts += [_step_text(s) if isinstance(s, dict) else str(s)
              for s in item.get("steps") or []]
    texts += [str(p) for p in item.get("pitfalls") or []]
    a = "；".join(t for t in texts if t)
    if not re.search(r"六十分|60分|按\d+分", a):
        return 0
    # 标题本身就在讲记分的，比正文顺带提一句更贴题
    return 2 if re.search(r"六十分|60分|按\d+分", item.get("title") or "") else 1


def rank(q: str) -> list[tuple[dict[str, Any], int]]:
    qn = norm(q)
    blocked = blocked_keys(qn)
    # archive_only：存档条目（如转专业接收计划附件）只入库、不参与问答路由
    scored = [(it, score_item(qn, it, blocked.get(it["id"])))
              for it in ITEMS if not it.get("archive_only")]
    # 专名维度（1-B，2026-11-04）：问句点了某个产品/系统名，条目却没点到同一个名字，
    # 就不许顶在前面。原先「Adobe软件怎么激活」靠「激活」两字抢到 86 分，
    # 把真正写 Adobe 的条目挤在池子外——打分只认字面重合，专名没有身份。
    # 只在池子里确有同名条目时动刀：问的是库里根本没提的东西（ps、校车）时照旧作答，
    # 那种情况该说的是「资料里没提到」，不在这条规则里。
    qp = question_proper(q)
    if qp:
        pi = proper_index()
        # 词表里的名字和问句里的名字互为包含就算对上（office ↔ wpsofficepc）
        named = [t for t in pi["postings"]
                 if any(t == w or (len(t) >= 3 and len(w) >= 3 and (t in w or w in t))
                        for w in qp)]
        if any(pi["postings"][t] for t in named):
            scored = [(it, sc if names_product(it, qp) else min(sc, MATCH_THRESHOLD - 1))
                      for it, sc in scored]
    # 自动抽取的制度卡片只是资料，不抢人工整理的服务条目：
    # 分数接近时让人工条目胜出；差距很大（如直接问办法原文）仍返回原文条目。
    hand_best = max((sc for it, sc in scored if not it.get("auto")), default=0)
    # 结构化条目（人工整理的 + 早先抽取的制度卡片）都算"有主的答案"，
    # 原文摘录只在它们都够不着时才顶上来。
    core_best = max((sc for it, sc in scored
                     if not (it.get("clause") or it.get("para"))), default=0)
    # 楼宇速查只回答「在哪」，问办事（怎么预约 / 收费 / 时间）时不该跟事项条目抢；
    # 它把「游泳馆」「校医院」等地点名收成别名，不压住会一直弹「你问的是哪一个」。
    action_q = bool(re.search(
        r"怎么|如何|收费|费用|多少钱|预约|申请|办理|流程|步骤|材料|条件|要求|时间|几点|多久|能不能|可以吗|需要|规定",
        qn))
    adjusted = []
    for it, sc in scored:
        if action_q and it["id"] in ("campus-louming", "campus-jiancheng") and "校园地图" not in qn:
            # 问句把条目本名说全了（「校园楼宇名称与位置速查怎么办」）就照问的那条答，
            # 只有拿地名当由头问别的事（「游泳馆怎么预约」）才降权。
            if _literal_hit(qn, it) < 6:
                sc = min(sc, MATCH_THRESHOLD - 1)
        if it.get("clause") or it.get("para"):
            # 问句就是这条原文的标题时，别压到结构化条目下面：
            # 「…微专业招生对象及条件」点进来就该答那一面。
            if sc < 100 and core_best >= MATCH_THRESHOLD:
                sc = min(sc, MATCH_THRESHOLD - 1)
        elif it.get("auto") and it.get("kind") != "qa" and hand_best >= sc - 12:
            sc = max(0, sc - 12)
        adjusted.append((it, sc))
    # 同分时人工条目优先，避免同年份的制度卡片把服务条目挤下去；
    # 同为自动条目时，问记分的先给写得出分值的条款。
    adjusted.sort(key=lambda x: (-x[1], bool(x[0].get("auto")), -_rule_affinity(qn, x[0])))
    return adjusted


def _literal_hit(qn: str, item: dict[str, Any]) -> int:
    """问句里字面出现的标题 / 别名长度；只给父子条目让位用，不参与打分。"""
    best = 0
    for raw in [item["title"], core_title(item["title"]), *(item.get("aliases") or [])]:
        a = norm(raw)
        if len(a) >= 2 and a in qn:
            best = max(best, len(a))
    return best


def _yield_to_children(q: str,
                       rows: list[tuple[dict[str, Any], int]]) -> list[tuple[dict[str, Any], int]]:
    """合订本父条目和拆出来的子条目同时命中时，问句字面更像谁就留谁。

    同一父条目下命中两个以上子条目（问的是两件事）时，保留父条目作答。
    """
    qn = norm(q)
    by_id = {it["id"]: it for it, _ in rows}
    kids: dict[str, list[str]] = {}
    for iid, it in by_id.items():
        pid = it.get("parent")
        if pid:
            kids.setdefault(pid, []).append(iid)
    if not kids:
        return rows
    lit: dict[str, int] = {}

    def lit_of(iid: str) -> int:
        if iid not in lit:
            lit[iid] = _literal_hit(qn, by_id[iid])
        return lit[iid]

    drop: set[str] = set()
    for pid, children in kids.items():
        if pid not in by_id:
            continue
        plit = lit_of(pid)
        child_hits = [c for c in children if lit_of(c)]
        if len(child_hits) == 1 and lit_of(child_hits[0]) >= plit:
            drop.add(pid)
        elif not child_hits and plit:
            drop.update(children)
    if not drop:
        return rows
    return [(it, sc) for it, sc in rows if it["id"] not in drop]


def distinct_rows(rows: list[tuple[dict[str, Any], int]]) -> list[tuple[dict[str, Any], int]]:
    """同一份文件既有人工条目又有自动抽取时只留一个，别让用户选两个同名文件。"""
    out: list[tuple[dict[str, Any], int]] = []
    seen: set[str] = set()
    for it, sc in rows:
        k = norm(core_title(it["title"]))
        if not k or k in seen:
            continue
        seen.add(k)
        out.append((it, sc))
    return out


def _names_subject(qn: str, item: dict[str, Any]) -> bool:
    """问句里点了这一条自己的名字，才算和另一条咬得紧的候选。

    只有「预约」「补办」「电话」这类通用词重合时，分数往往是关键词层凑出来的；
    拿它反问用户，等于把两条不相干的事摆在一起让人选。
    """
    for raw in (core_title(item.get("title") or ""), *(item.get("aliases") or [])):
        a = norm(raw)
        if len(a) < 3 or a in GENERIC_KEYWORDS or a in GENERIC_PLACE:
            continue
        if a in qn:
            return True
    return False


# ---------------------------------------------------------------- 显示文字
# 回答正文的写法：不用引号、破折号、冒号、句号、星号、井号，不端着模型腔，
# 也不堆比喻。括号里的内容、《》文件名、网址、邮箱、时间、小数、电话原样保留。

_KEEP_RE = re.compile(
    r"（来源[：:][^）]{1,24}）"
    r"|https?:/{0,2}[^\s，。；、）)】》]+"
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"|[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?:/[^\s，。；、）)】》]*)?"
    r"|\d{1,2}[:：]\d{2}(?::\d{2})?"
    r"|\d{3,4}[-—–]\d{7,8}"
    r"|\d+(?:\.\d+)+(?:%|％)?"
    r"|\.[A-Za-z]{2,5}(?![A-Za-z])"
    r"|[A-Za-z]+['’][A-Za-z]+"
)
_RATIO_RE = re.compile(r"(?<![A-Za-z0-9_.：:])(\d{1,4})[:：](\d{1,4})(?![A-Za-z0-9_:：])")
_RATIO_PAIRS = {("16", "9"), ("16", "10"), ("21", "9"), ("32", "9"),
                ("4", "3"), ("3", "2"), ("18", "9")}
_AI_STRICT = r"首先|其次|再次|最后|此外|另外|综上(?:所述)?|总而言之|总的来说"
_AI_LOOSE = (
    r"值得注意的是|需要注意的是|需要说明的是|值得一提的是|"
    r"简单来说|简而言之|换句话说|说到底|说白了|表面看是|归根结底|"
    r"往深了说|说到这|你发现没|说来有趣|这条我认|这流程我熟|"
    r"我理解你的(?:痛苦|焦虑|难处|处境)|你不是一个人|"
    r"按照这个方案|马上去行动|话不多说|不多废话"
)
_AI_BAD_SENTENCE = (
    "你这是把", "凑齐了", "活脱脱", "无异于", "好比", "简直是", "就像是",
    "像极了", "如同一场", "仿佛在", "惊天动地", "排山倒海", "无与伦比",
    "史无前例", "完美解决", "一劳永逸", "天壤之别", "脱胎换骨", "立竿见影",
    "叹为观止", "不可估量",
)


def _drop_bad_sentences(s: str) -> str:
    out = []
    for one in re.split(r"(?<=[。；！？\n])", s):
        if any(k in one for k in _AI_BAD_SENTENCE):
            continue
        out.append(one)
    return "".join(out)


def _strip_ai_tone(s: str) -> str:
    s = re.sub(rf"(^|[。；！？\n])\s*(?:{_AI_STRICT})\s*[，,：:；;]\s*", r"\1", s)
    s = re.sub(rf"(?:{_AI_STRICT})\s*[，,：:；;]\s*", "", s)
    s = re.sub(rf"(^|[。；！？\n])\s*(?:{_AI_LOOSE})\s*[，,：:；;。！？]?\s*", r"\1", s)
    s = re.sub(rf"(?:{_AI_LOOSE})\s*[，,：:；;]\s*", "", s)
    # 「不是A，而是B」只把「而是」改成「，是」，A、B 两边都留着，不能只留 B
    s = re.sub(r"并非([^。；\n]{1,40}?)[，,]?\s*而是", r"并非\1，是", s)
    s = re.sub(r"不是([^。；\n]{1,40}?)[，,]?\s*而是", r"不是\1，是", s)
    return s


def _display_model_text(s: str) -> str:
    """模型直答保留正常标点；只清 Markdown 记号和模型腔。"""
    s = _drop_bad_sentences(str(s))
    s = _strip_ai_tone(s)
    s = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", s)
    s = re.sub(r"\*\*|__|`", "", s)
    s = re.sub(r"(?m)^\s*[-*•]\s+", "", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    return s.strip()


def _display_text(s: str, model: bool = False) -> str:
    """把一句话改成回答该有的写法；model=True 时保留标点，只清模型腔。"""
    s = str(s)
    if not s.strip():
        return s
    if model:
        return _display_model_text(s)
    s = _strip_ai_tone(s)
    # PDF 转出来的域代码和页码不是正文；横线字符先统一成破折号再按区间处理
    s = s.replace("―", "—")
    s = re.sub(r"(?:MM)?PAGE\s*\\?\*+[A-Z]*", "", s, flags=re.I)
    s = re.sub(r"(?:MM)?PAGE\s*\\?\*?\s*(?:M)?ERGE[A-Z]*\s*\d*", "", s, flags=re.I)
    s = re.sub(r"(?:(?<=^)|(?<=\n)|\s)[—–]\s*\d{1,3}\s*[—–](?=\s|$|\n)", " ", s)
    # 省略号也是标点，直接去掉，标题里的「400报…」变回「400报」
    s = s.replace("…", "")
    # 引号里的星号是官方标记符号，写成“星号”才不丢意思
    s = re.sub(r"[“”「」『』\"']\s*[*＊]\s*[“”「」『』\"']", "星号", s)
    # 星号当通配符或必填标记时也写成“星号”，别直接删掉
    s = re.sub(r"(?<=[名为作写带])\s*[*＊](?=\.)", "星号", s)
    s = re.sub(r"[*＊]\s*(?=为(?![上下]))", "星号", s)
    s = re.sub(r"(?<=带)\s*[*＊]", "星号", s)
    s = re.sub(r"以下简称\s*[：:]", "以下简称", s)
    # 乘号别有别的写法
    s = re.sub(r"(?<=[A-Za-z0-9）)])\s*[*＊]\s*(?=[\u4e00-\u9fffA-Za-z0-9（(])", "×", s)
    # 时间里的全角冒号写成半角，别和正文冒号混在一起
    s = re.sub(r"(?<=\d)：(?=\d{2})", ":", s)
    # 显示比例和师生比不是时间；只在比例语境里把冒号写成「比」
    def _ratio(m: re.Match[str]) -> str:
        left, right = m.group(1), m.group(2)
        near = m.string[max(0, m.start() - 8):m.start()] + m.string[m.end():m.end() + 8]
        strong = ("比例", "宽高", "画幅", "分辨率", "英寸", "师生比")
        weak = ("显示器", "超宽", "屏")
        if any(w in near for w in strong) or (
                any(w in near for w in weak) and (left, right) in _RATIO_PAIRS):
            tail = m.string[m.end():m.end() + 1]
            gap = " " if tail and re.match(r"[\u4e00-\u9fffA-Za-z]", tail) else ""
            return f"{left} 比 {right}{gap}"
        return m.group(0)

    s = _RATIO_RE.sub(_ratio, s)
    # 日期区间先连成一个整体，免得连字符被当成破折号；
    # 「2026年9月2日10:00-9月10日20:00」的连字符两边不都是时刻，时间区间规则接不住
    s = re.sub(
        r"((?:\d{1,4}\s*年\s*)?\d{1,2}\s*月\s*\d{1,2}\s*日(?:\s*\d{1,2}:\d{2})?)"
        r"\s*[-—–~～]+\s*"
        r"((?:次年\s*|翌年\s*)?(?:\d{1,4}\s*年\s*)?\d{1,2}\s*月\s*\d{1,2}\s*日(?:\s*\d{1,2}:\d{2})?)",
        r"\1至\2", s)
    # 跨年区间「9 月 7 日至 2027 年」补一个空格，和「9 月 5 日至 6 日」一致
    s = re.sub(r"(?<=日)至(?=\d)", "至 ", s)
    # 只有月份的区间（9 月—次年 8 月）也写「至」
    s = re.sub(r"(\d\s*月)\s*[-—–~～]+\s*(?=(?:次年|翌年)?\s*\d{1,2}\s*月)", r"\1至", s)
    # 时间区间先连成一个整体，免得破折号被当成标点
    s = re.sub(
        r"(\d{1,2}:\d{2}(?::\d{2})?)\s*[-—–~～]+\s*(\d{1,2}:\d{2}(?::\d{2})?)",
        r"\1至\2", s)
    # 带单位的区间先写「至」；小数马上要被保护起来，之后就连不上了
    s = re.sub(
        r"(?<=\d)\s*[-—–~～]+\s*(?=\d+\s*个?\s*(?:周|天|日|月|年|届|元|档|次|人|间|门|个|分|小时|公里|km|GB|cm|mm|米|位))",
        "至", s)
    keep: list[str] = []

    def stash(m: re.Match[str]) -> str:
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x01"

    s = _KEEP_RE.sub(stash, s)
    # 剩下的波浪线都是区间（周一～周日），统一写成「至」
    s = re.sub(r"[~～]", "至", s)
    # 尺寸里的乘号写成 ×，别当星号删掉
    s = re.sub(r"(?<=\d)[`\s]*\*[`\s]*(?=\d)", "×", s)
    s = re.sub(r"[*#]+", "", s)
    s = re.sub(r"[“”‘’「」『』\"']", "", s)
    # 英文名里的短横是名字的一部分（Wireless CUC–Guest），别当破折号换成逗号；
    # 两边都是数字时留给下面的日期区间规则
    s = re.sub(r"(?<=[A-Za-z])[—–](?=[A-Za-z0-9])|(?<=[A-Za-z0-9])[—–](?=[A-Za-z])", "-", s)
    # 日期区间写成「至」，右侧是数字时留一个空格（9 月 5 日至 6 日）
    s = re.sub(r"(?<=[年月日])\s*[-—–]+\s*(?=\d)", "至 ", s)
    # 纯数字区间也写「至」；带单位的连字符才算区间，完整日期 2026-08-18 不动
    s = re.sub(r"(?<=\d)\s*[—–]+\s*(?=\d)", "至", s)
    s = re.sub(
        r"(\d+(?:\.\d+)?)\s*元\s*[-—–~～]+\s*(\d+(?:\.\d+)?)\s*元",
        r"\1 元至 \2 元", s)
    s = re.sub(
        r"(?<=\d)\s*[-—–]+\s*(?=\d+\s*个?\s*(?:周|天|日|月|年|届|元|档|次|人|间|门|个|分|小时|公里|km|GB|cm|mm|米|位))",
        "至", s)
    # 剩下的双破折号是 prose 里的断句，不是区间
    s = s.replace("——", "，")
    s = re.sub(r"[—–]", "，", s)
    s = re.sub(r"[：:]", "，", s)
    s = s.replace("。", "；")
    s = re.sub(r"(?<=[\u4e00-\u9fff])\.(?=[\u4e00-\u9fff]|$)", "；", s)
    s = s.replace(".", "")
    s = re.sub(r"[，；、]{2,}", lambda m: m.group(0)[0], s)
    s = re.sub(r"(?<=[，；、])\s+|\s+(?=[，；、])", "", s)

    def restore(m: re.Match[str]) -> str:
        return keep[int(m.group(1))]

    s = re.sub(r"\x00(\d+)\x01", restore, s)
    return s.strip(" ，；、")


def _step_what(s: dict[str, Any]) -> str:
    """步骤标签已经显示 when，正文用分隔符重复同一个词时去掉。"""
    what = str(s.get("what") or "")
    when = str(s.get("when") or "").strip()
    if when and what.strip().startswith(when):
        tail = what.strip()[len(when):]
        if tail[:1] in " ：:，,；;、":
            rest = tail.lstrip(" ：:，,；;、")
            if rest:
                return rest
    return what


_STEP_NUM_RE = re.compile(r"^第\s*[一二三四五六七八九十百\d]+\s*步$")


def _step_label(s: dict[str, Any]) -> str:
    """能当小标题用的 when；「第 N 步」只是序号，不当标签。"""
    when = str(s.get("when") or "").strip()
    if not when or _STEP_NUM_RE.match(when):
        return ""
    return when


def _step_text(s: dict[str, Any]) -> str:
    """摘要里的一步：标签加正文，正文里已经带着这个词时不重复。"""
    what = _step_what(s)
    label = _step_label(s)
    if not label or label in what:
        return what
    head = re.split(r"[，；。]", what, maxsplit=1)[0]
    label_chars = set(re.findall(r"[\u4e00-\u9fff]", label))
    if len(label_chars & set(re.findall(r"[\u4e00-\u9fff]", head))) >= 3:
        return what
    return f"{label}，{what}"


def _join_steps(rows: list[Any]) -> str:
    """一步一句地连起来；步骤自带句末标点时不再叠一个分号。"""
    out = []
    for s in rows:
        t = (_step_text(s) if isinstance(s, dict) else str(s)).strip()
        t = t.rstrip("。；;")
        if t:
            out.append(t)
    return "；".join(out)


# 公告结尾的招呼语和落款。整句只由这些词组成、又不带数字和日期的才扔，
# 「欢迎各位同学于 9 月 1 日到 XX 报名」这种带信息的不动
_BULLETIN_DROP = re.compile(
    r"^(?:欢迎[^。；;！？!?\d]{0,20}(?:咨询|报名|参加|查看|关注|选购|前来|办理)"
    r"|特此(?:通知|公告|声明)"
    r"|请同学们相互转告"
    r"|敬请[^。；;！？!?\d]{0,12}周知)$")
# 招呼语挂在句子尾巴上时（「即日起开始招生，欢迎各位同学咨询报名」）单独摘掉这一小节
_BULLETIN_TAIL = re.compile(
    r"[，,；;]\s*(?:欢迎[^，,；;。！？!?\d]{0,20}(?:咨询|报名|参加|查看|关注|选购|前来|办理)"
    r"|请同学们相互转告"
    r"|敬请[^，,；;。！？!?\d]{0,12}周知)(?=[。；;！？!?]|$)")
_SENT_SPLIT = re.compile(r"(?<=[。；;！？!?])")


def _de_bulletin(s: str) -> str:
    """公告语体换成办事答复的说法：「我校」写成「学校」，招呼语去掉。

    数字、日期、部门名、办理方法一个字不动，原文引文那一栏也不经过这里。
    """
    if not isinstance(s, str) or not s:
        return s
    out = s.replace("我校", "学校")
    if not any(w in out for w in ("欢迎", "特此", "周知", "转告")):
        return out
    out = _BULLETIN_TAIL.sub("", out)
    kept = [sent for sent in _SENT_SPLIT.split(out)
            if not _BULLETIN_DROP.match(sent.strip("。；;！？!? \n"))]
    res = "".join(kept).strip(" 。；;！？!?\n")
    # 整段都是招呼语时不能把答案清空，退回原句
    return res or out


def _clean_part(part: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(part, dict):
        return part
    if isinstance(part.get("text"), str):
        part["text"] = _display_text(_de_bulletin(part["text"]))
    steps = part.get("steps")
    if isinstance(steps, list):
        fixed = []
        for s in steps:
            if isinstance(s, dict) and isinstance(s.get("what"), str):
                s = {**s, "what": _display_text(_de_bulletin(_step_what(s))),
                     **{k: _display_text(s[k]) for k in ("where", "when")
                        if isinstance(s.get(k), str)}}
            elif isinstance(s, str):
                s = _display_text(_de_bulletin(s))
            fixed.append(s)
        part["steps"] = fixed
    if isinstance(part.get("lines"), list):
        part["lines"] = [_display_text(x) if isinstance(x, str) else x
                         for x in part["lines"]]
    return part


def _clean_text_item(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    for key in ("title", "answer", "fee", "location", "hours", "duration", "window", "note"):
        if isinstance(out.get(key), str):
            # 标题可能是文件名，不动它的字；正文才做公告语体转换
            out[key] = _display_text(out[key] if key == "title"
                                     else _de_bulletin(out[key]))
    if isinstance(out.get("steps"), list):
        out["steps"] = [
            {**s, "what": _display_text(_de_bulletin(_step_what(s))),
             **{k: _display_text(s[k]) for k in ("where", "when")
                if isinstance(s.get(k), str)}}
            if isinstance(s, dict) else s
            for s in out["steps"]
        ]
    if isinstance(out.get("materials"), list):
        out["materials"] = [
            {**m, "name": _display_text(m["name"])}
            if isinstance(m, dict) and isinstance(m.get("name"), str) else m
            for m in out["materials"]
        ]
    if isinstance(out.get("pitfalls"), list):
        out["pitfalls"] = [_display_text(x) if isinstance(x, str) else x
                           for x in out["pitfalls"]]
    if isinstance(out.get("advisory"), list):
        out["advisory"] = [_display_text(x) if isinstance(x, str) else x
                           for x in out["advisory"]]
    if isinstance(out.get("experience"), list):
        out["experience"] = [
            {**e, "text": _display_text(e["text"])}
            if isinstance(e, dict) and isinstance(e.get("text"), str) else e
            for e in out["experience"]
        ]
    if isinstance(out.get("slots"), list):
        out["slots"] = [
            {**s, **{k: _display_text(s[k]) for k in ("ask", "why")
                     if isinstance(s.get(k), str)}}
            if isinstance(s, dict) else s
            for s in out["slots"]
        ]
    return out


def scope_note(item: dict[str, Any], text: str = "") -> str | None:
    """条目的适用范围提示：问法够泛、条目只覆盖其中一类人时，随回答一起说清楚。

    scope_note 可以是一句话，也可以是若干条 [{text, if}]，按问句命中的关键词各自生效。
    """
    raw = item.get("scope_note")
    if isinstance(raw, str):
        entries = [{"text": raw, "if": item.get("scope_note_if")}]
    elif isinstance(raw, list):
        entries = [e for e in raw if isinstance(e, dict) and isinstance(e.get("text"), str)]
    else:
        return None
    out: list[str] = []
    for entry in entries:
        only = entry.get("if")
        if isinstance(only, list) and only and not any(k in text for k in only):
            continue
        one = entry["text"].strip().rstrip("。；;，,")
        if one:
            out.append(one)
    return "；".join(out) or None


def experience_note(item: dict[str, Any], text: str = "") -> str | None:
    """用户补充的现场经验：明确标成非官方，不跟官方原文混在一起。"""
    raw = item.get("experience")
    if not isinstance(raw, list):
        return None
    out: list[str] = []
    for entry in raw:
        if not isinstance(entry, dict) or not isinstance(entry.get("text"), str):
            continue
        only = entry.get("if")
        if isinstance(only, list) and only and not any(k in text for k in only):
            continue
        src = entry.get("from")
        head = f"非官方补充（来源：{src.strip()}）" if isinstance(src, str) and src.strip() else "非官方补充"
        one = entry["text"].strip().rstrip("。；;，,")
        if one:
            out.append(f"{head}：{one}")
    return "；".join(out) or None


def _source_list(src: Any) -> list[Any]:
    """接口只出去一种来源形状：数组。

    库里两种写法都有（30648 条存单个对象、8574 条存数组），前端按数组渲染，
    拿到对象就在 (item.source || []).filter 处炸掉，整块答面出不来——
    看起来像「没答上」，其实是后端答上了前端没渲染。
    """
    if not src:
        return []
    return list(src) if isinstance(src, list) else [src]


def public(item: dict[str, Any]) -> dict[str, Any]:
    out = _clean_text_item({
        "id": item["id"],
        "title": item["title"],
        "dept": item["dept"],
        "status": item.get("status", "partial"),
        "confidence": item.get("confidence", "medium"),
        "fee": item.get("fee"),
        "location": item.get("location"),
        "hours": item.get("hours"),
        "duration": item.get("duration"),
        "window": item.get("window"),
        "channel": item.get("channel", []),
        "materials": item.get("materials", []),
        "steps": item.get("steps", []),
        "pitfalls": item.get("pitfalls", []),
        "source": _source_list(item.get("source")),
        "slots": item.get("slots", []),
        "answer": item.get("answer"),
        "note": item.get("note"),
        "advisory": item.get("advisory", []),
        "experience": item.get("experience", []),
        "evidence": item.get("evidence", {}),
        "qr": item.get("qr") or [],
        "pdf": item.get("pdf") or [],
    })
    # 自动摘录的卡片标题是切短的原文句子，界面上换成「来源文件 · 短句」。
    # 放在清洗之后再做，收尾那个省略号才不会被 _display_text 吃掉。
    out["title"] = _card_title({**item, "title": out["title"]})
    return out


# ---------------------------------------------------------------- deepseek


def _with_history(
    system_prompt: str,
    user_text: str,
    history: list[dict[str, str]] | None,
    max_turns: int = 6,
    max_chars: int = 3000,
) -> list[dict[str, Any]]:
    """把对话历史塞进 messages 数组，供 ds_chat 消费。

    history 格式：[{"role": "user"|"assistant", "content": "..."}]。
    只取最近 max_turns 轮（每轮 = 1 user + 1 assistant），总字符不超过 max_chars。
    """
    msgs: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if not history:
        msgs.append({"role": "user", "content": user_text})
        return msgs
    pairs = []
    i = 0
    while i < len(history):
        u = history[i]
        a = history[i + 1] if i + 1 < len(history) else None
        if u.get("role") == "user" and a and a.get("role") == "assistant":
            pairs.append((u["content"], a["content"]))
            i += 2
        else:
            i += 1
    kept: list[tuple[str, str]] = []
    total = 0
    for u, a in reversed(pairs[-max_turns:]):
        cost = len(u) + len(a)
        if total + cost > max_chars:
            break
        kept.append((u, a))
        total += cost
    for u, a in reversed(kept):
        msgs.append({"role": "user", "content": u})
        msgs.append({"role": "assistant", "content": a})
    msgs.append({"role": "user", "content": user_text})
    return msgs


DS_RETRY_WAIT = 0.8  # 只等这一次；再久会把整页答案拖到用户以为卡死
DS_RETRY_CODES = {408, 429, 500, 502, 503, 504}


def _ds_fail_text(code: int, detail: str, tried: int) -> str:
    """给用户分开两种失败：被限流（等一会就好）和真连不通（Key 或网络出问题）。"""
    if code == 429:
        return f"模型接口被限流（429），重试 {tried} 次仍被拒: {detail}"
    if code in (401, 403):
        return f"模型接口拒绝访问（{code}），Key 可能失效: {detail}"
    return f"模型接口返回 {code}: {detail}"


# ------------------------------------------------------- 流式回法：每一步模型调用报一帧
# 只有 /api/ask 带 Accept: text/event-stream 时才挂接收器。没挂的时候下面全是
# 一句 if 判断，非流式那条腿（经典版 app.js 与 206 回归）字节都不变。

STEP_LABELS: dict[str, str] = {
    "ctx_need": "续问判定",
    "condense": "问句补全",
    "route": "词条定位",
    "rerank": "候选重排",
    "recheck": "原文复核",
    "second_look": "池外再看",
    "phrase": "官方说法",
    "assemble_plan": "拼装计划",
    "assemble_decide": "逐面裁决",
    "facet_fill": "缺面补检",
    "proper_map": "名称对齐",
    "pick_line": "表格行选定",
    "free_answer": "组织回答",
    "headline": "顶部总括",
}

# 一帧里能露出来的键：全是 model_route 里已有的叫法（前端认得的显示中文名，
# 认得的照原样 key=value）。token 数、原始 prompt、模型名、重试次数不在其中——
# 它们本来也没写进 model_route，这里再挡一道，将来有人顺手塞也漏不出去。
STEP_FIELDS = (
    "gate", "pool", "pool2", "score", "facets", "rewrites", "rescue", "changed",
    "confirmed", "why", "error", "assembly", "verdict", "answers", "fills", "name",
    "asked", "ctx_need", "ctx_need_why", "ctx_need_error", "ctx_need_dropped",
    "condensed_query", "condense_error", "condense_dropped",
    "pre_phrases", "headline_error", "headline_dropped",
)

_STEP_SINK: contextvars.ContextVar[Any] = contextvars.ContextVar("step_sink", default=None)


def _clean_fields(obj: Any) -> dict[str, Any]:
    """只留看得懂、且对人有用那几个键；空值一律丢掉（false／null／空串前端本就不显示）。"""
    if isinstance(obj, tuple):
        obj = next((x for x in obj if isinstance(x, dict)), {})
    if not isinstance(obj, dict):
        return {}
    return {k: v for k, v in obj.items()
            if k in STEP_FIELDS and v not in ("", None, False, [], {})}


class _StepSink:
    """把这一次问答里真实发生的每一次模型调用变成一帧，投进请求线程的队列。"""

    def __init__(self, put: "queue.Queue[Any]") -> None:
        self.q = put
        self.calls = 0
        self.secs = 0.0

    def note_call(self, secs: float) -> None:
        self.calls += 1
        self.secs += secs

    def emit(self, step_id: str, base: int, fields: dict[str, Any]) -> None:
        if self.calls == base:          # 这一腿根本没发过模型调用，不报
            return
        self.q.put(("step", {
            "id": step_id, "label": STEP_LABELS.get(step_id, step_id),
            "t": round(self.secs, 2), "fields": fields,
        }))
        self.secs = 0.0


def steped(step_id: str, pick=None):
    """装饰每一次模型调用：真调用过才补一帧，字段就是这一次真正产出的那些。

    pick 给那几个返回值不是「一目了然的字典」的腿用（压缩出来是一句问话、
    重排出来是「条目＋说法表」这种二元组）。没挂接收器时直接透传，一次快照都不做。
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*a, **kw):
            sink = _STEP_SINK.get()
            if sink is None:
                return fn(*a, **kw)
            base = sink.calls
            status = kw.get("status")
            before = dict(status) if isinstance(status, dict) else {}
            try:
                out = fn(*a, **kw)
            except Exception as e:  # noqa: BLE001
                sink.emit(step_id, base, {"error": _short_err(e)})
                raise
            delta = {k: v for k, v in (status or {}).items() if k not in before or before[k] != v}
            fields = _clean_fields(delta)
            fields.update(_clean_fields(pick(out) if pick else out))
            sink.emit(step_id, base, fields)
            return out
        return wrap
    return deco


def _short_err(e: Exception) -> str:
    if isinstance(e, HTTPException):
        return str(e.detail)[:120]
    return f"{type(e).__name__}: {e}"[:120]


def _sse(event: str, obj: Any) -> str:
    """一帧两行＋空行。json 不换行缩进，值里的换行会被转义，data 恒为单行。"""
    return f"event: {event}\ndata: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _ask_stream(**kw) -> Iterator[str]:
    """边跑边发：模型调用落在工作线程里，主线程从队列里一帧一帧取。

    done 那一帧就是 /api/ask 现在返回的那个 dict，一个键没加没减；
    中途整体挂掉发 err，不静默断流。
    """
    q: queue.Queue[Any] = queue.Queue()

    def work() -> None:
        token = _STEP_SINK.set(_StepSink(q))
        try:
            q.put(("done", clean_response(answer_question(**kw))))
        except Exception as e:  # noqa: BLE001
            q.put(("err", {"error": _short_err(e)}))
        finally:
            _STEP_SINK.reset(token)
            q.put(("end", None))

    threading.Thread(target=work, daemon=True).start()
    while True:
        kind, payload = q.get()
        if kind == "end":
            return
        yield _sse(kind, payload)


def ds_chat(
    messages: list[dict[str, Any]],
    max_tokens: int = 600,
    json_mode: bool = False,
    thinking: bool = False,
) -> str:
    """模型调用的唯一出口；挂了流式接收器就顺手记下这一次花了多久（重试合在一起算）。"""
    sink = _STEP_SINK.get()
    if sink is None:
        return _ds_chat_once(messages, max_tokens, json_mode, thinking)
    t0 = time.perf_counter()
    try:
        return _ds_chat_once(messages, max_tokens, json_mode, thinking)
    finally:
        sink.note_call(time.perf_counter() - t0)


def _ds_chat_once(
    messages: list[dict[str, Any]],
    max_tokens: int = 600,
    json_mode: bool = False,
    thinking: bool = False,
) -> str:
    """deepseek-flash 默认开思考模式，会先烧 max_tokens，短任务必须关掉。

    thinking=True 时不发 temperature（该模式忽略它）。
    限流和 5xx 各重试一次：跑一批回归就能把同一个 Key 打到 429，
    不重试的话人正在用的时候会连着看到「模型接口失败」。
    """
    key = api_key()
    if not key:
        raise HTTPException(503, "未配置 DEEPSEEK_API_KEY")
    body: dict[str, Any] = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "thinking": {"type": "enabled" if thinking else "disabled"},
    }
    if not thinking:
        body["temperature"] = 0.2
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    for attempt in range(2):
        req = urllib.request.Request(
            f"{API_BASE}/chat/completions", data=data, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            if e.code not in DS_RETRY_CODES or attempt:
                raise HTTPException(502, _ds_fail_text(e.code, detail, attempt))
            time.sleep(DS_RETRY_WAIT)
        except urllib.error.URLError as e:
            if attempt:
                raise HTTPException(502, f"模型接口连不通（{e.reason}）")
            time.sleep(DS_RETRY_WAIT)
        except OSError as e:
            if attempt:
                raise HTTPException(502, f"模型接口连不通（{type(e).__name__}: {e}）")
            time.sleep(DS_RETRY_WAIT)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, f"模型接口调用失败: {e}")
    raise HTTPException(502, "模型接口调用失败")


# ---------------------------------------------------------------- app

app = FastAPI(title="校园办事向导", version="0.1")


@app.middleware("http")
async def _ui_no_stale_cache(request, call_next):
    """前端改动后浏览器必须拿到新脚本，否则新功能要用户手动清缓存。"""
    response = await call_next(request)
    path = request.url.path
    if path.endswith((".js", ".css", ".html")):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


class IntakeReq(BaseModel):
    text: str


class DeliverReq(BaseModel):
    item_id: str
    slots: dict[str, str] = {}


class VerifyReq(BaseModel):
    item_id: str
    image: str  # data URL
    materials: list[str] = []


def _facts_total(items: list[dict[str, Any]]) -> int:
    """与 check_quotes.py 同口径：只数需要证据的字段。"""
    n = 0
    for i in items:
        n += sum(1 for k in ("fee", "location", "hours", "duration", "window") if i.get(k))
        n += len(i.get("materials") or [])
        n += len(i.get("steps") or [])
        n += len(i.get("pitfalls") or [])
    return n


def _counts() -> dict[str, Any]:
    verified = sum(1 for i in ITEMS if i.get("status") == "verified")
    thin = sum(1 for i in ITEMS if i.get("status") == "source-thin")
    out: dict[str, Any] = {
        "items": len(ITEMS),
        "verified": verified,
        "source_thin": thin,
        "facts": _facts_total(ITEMS),
        "data_updated": DATA_UPDATED,
    }

    presets_path = ROOT / "presets.json"
    if presets_path.exists():
        pz = json.loads(presets_path.read_text(encoding="utf-8"))
        pids = {k for k in (pz.get("coverage") or {}) if k}
        out["presets"] = pz.get("total", 0)
        if pids:
            out["presets_items"] = len(pids)

    contacts_path = ROOT / "contacts.json"
    if contacts_path.exists():
        ct = json.loads(contacts_path.read_text(encoding="utf-8"))
        out["contacts"] = len(ct.get("items", []))

    corpus_path = ROOT / "sources" / "corpus-index.json"
    if corpus_path.exists():
        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        out["sources"] = len(corpus)
        out["sources_official"] = sum(1 for v in corpus.values() if v.get("official"))

    manifest_path = ROOT / "sources" / "vector" / "manifest.json"
    if manifest_path.exists():
        try:
            mf = json.loads(manifest_path.read_text(encoding="utf-8"))
            out["vector_sources"] = mf.get("sources", 0)
            out["vector_chunks"] = mf.get("chunks", 0)
            out["vector_built"] = mf.get("built", "")
        except json.JSONDecodeError:
            pass
    return out


@app.get("/api/stats")
def stats() -> dict[str, Any]:
    maybe_reload()
    return _counts()


@app.get("/api/health")
def health() -> dict[str, Any]:
    maybe_reload()
    return {
        "ok": True,
        "model": MODEL,
        "vision": True,
        "key_configured": bool(api_key()),
        "hot_reload": True,
        **_counts(),
    }


@app.get("/api/campus")
def campus(q: str = "", limit: int = 30) -> dict[str, Any]:
    """校园 POI：楼宇/机关/实验室/场馆的官方位置，供地图面板和“XX 在哪”用。"""
    data = campus_data()
    pois = data.get("pois") or []
    q = (q or "").strip()
    if q:
        nq = norm(q)
        scored: list[tuple[int, dict[str, Any]]] = []
        for p in pois:
            names = [p.get("name", ""), *p.get("aliases", [])]
            best = 0
            for n in names:
                nn = norm(n)
                if not nn:
                    continue
                if nn == nq:
                    best = max(best, 100)
                elif nn in nq:
                    best = max(best, 80 + min(10, len(nn)))
                elif nq in nn:
                    best = max(best, 60 + min(10, len(nq)))
            if best:
                scored.append((best, p))
        scored.sort(key=lambda x: -x[0])
        pois = [p for _, p in scored[: max(1, min(limit, 100))]]
    else:
        pois = pois[: max(1, min(limit, 500))]
    return {
        "count": len(pois),
        "total": data.get("count", len(data.get("pois") or [])),
        "coords": data.get("coords", 0),
        "center": data.get("center"),
        "note": data.get("note", ""),
        "has_amap_key": bool(os.environ.get("AMAP_KEY", "").strip()),
        "pois": pois,
    }


@app.get("/api/search")
def search(q: str = "", k: int = 8) -> dict[str, Any]:
    """独立原文检索：按语义近似找段落，只返回原文与出处，不生成答案。

    数据表（表格/阅读报告逐行）另走 gram 一路，段落命中里塞不进去。
    """
    q = (q or "").strip()
    if len(q) < 2:
        raise HTTPException(400, "请再说得具体一点")
    try:
        import vector_index

        hits = vector_index.search(q, k=max(1, min(k, 20)), min_score=0.15)
        counts = vector_index.stats()
    except Exception as e:  # 向量库未建好时明确告知，不静默降级
        raise HTTPException(503, f"原文库未就绪：{e}")
    return {"query": q, "total": len(hits), **counts, "hits": hits,
            "rows": table_search(q, k=max(1, min(k, 10)))}


@app.get("/api/plan-file")
def plan_file(college: str = "") -> FileResponse:
    """下载某学院的转专业接收计划 PDF（只允许 transfer-plans.json 里登记的文件）。"""
    plan = _load_plans().get(college)
    if not plan or not plan.get("file"):
        raise HTTPException(404, "没有这份接收计划")
    base = (ROOT / "sources" / "local" / "_files").resolve()
    path = (base / Path(plan["file"]).name).resolve()
    if base not in path.parents or not path.exists():
        raise HTTPException(404, "接收计划文件不在了")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


_PRESETS: dict[str, Any] = {}


@app.get("/api/contacts")
def contacts(purpose: str = "", q: str = "") -> dict[str, Any]:
    """公开联系方式：按用途筛选，或按关键词搜。"""
    f = ROOT / "contacts.json"
    if not f.exists():
        return {"purposes": [], "items": [], "total": 0}
    data = json.loads(f.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if purpose:
        items = [i for i in items if i.get("purpose") == purpose]
    if q:
        kw = q.strip()
        items = [i for i in items if kw in (i.get("value", "") + i.get("dept", "") + i.get("context", ""))]
    purposes = sorted({i.get("purpose", "其他") for i in data.get("items", [])})
    return {"purposes": purposes, "items": items[:120], "total": len(items)}


@app.get("/api/presets")
def presets(limit: int = 8) -> dict[str, Any]:
    """预置问法：按主题分组，界面点一下就提问。"""
    f = ROOT / "presets.json"
    global _PRESETS
    if not _PRESETS or _PRESETS.get("_mtime") != f.stat().st_mtime:
        data = json.loads(f.read_text(encoding="utf-8"))
        data["_mtime"] = f.stat().st_mtime
        _PRESETS = data
    groups = [{"name": g["name"], "items": g["items"][:limit]} for g in _PRESETS.get("groups", [])]
    return {"total": _PRESETS.get("total", 0), "limit": limit, "groups": groups}


@app.get("/api/items")
def list_items() -> dict[str, Any]:
    return {"items": [{"id": i["id"], "title": i["title"], "status": i.get("status")} for i in ITEMS]}


# ------------------------------------------------- 问题归一化 + 聚焦作答
# 一句话问题先被翻译成「事项 + 问的是哪一面」，只答那一面；
# 数据里没有这一面，就直说没有，不拿整条记录糊上去。

FOCUS_RULES: list[tuple[str, str, str]] = [
    ("contact", "该找哪个部门", r"哪个部门|找谁|联系谁|归口|找哪个|问谁|哪个处|谁能管"),
    ("fee", "费用", r"多少钱|收费|费用|工本费|免费|贵|网费|水费|电费|学费(?!减免)|住宿费(?!减免)|杂费|书费"),
    ("window", "办理时限", r"截止|什么时候前|过期|来得及|有效期|多久内"),
    ("hours", "办理时间", r"几点|什么时间|什么时候能办|周几|哪个时段|工作日|周末|上班|开放时间|开馆|闭馆|营业时间|开门|关门|到几点|办公时间|办理时间|服务时间|工作时间|就诊时间"),
    ("location", "办理地点", r"在哪|哪里|哪个楼|去哪儿|地点|几层"),
    ("material", "要带什么", r"带什么|材料|要准备|需要带|证件|照片"),
    ("amount", "数量", r"几本|多少本|多少册|借多少|几张|几份|几个名额"),
    ("duration", "多久出结果", r"多久|几天|多长时间|当场|立等"),
    ("pitfalls", "容易白跑的情况", r"白跑|坑|失败|出错|被拒|注意|办不成"),
    ("conditions", "条件与限制",
     r"什么条件|哪些条件|条件是什么|条件是|需要满足|须满足|满足什么|申请条件|资格是什么|什么资格|具备.{0,4}资格|要求是什么|有什么要求|哪些要求|什么人能|谁能(?:办|申请|报|申请)|什么情况下(?:可以|能|不能)|能不能(?:转|报|申请|办|选)|是否可以(?:转|报|申请|办|选)"),
    ("steps", "办理流程", r"怎么办|流程|步骤|怎么弄|如何|怎么操作|怎么用|怎么使用|预约|办卡|报名|怎么申请|报销|怎么报|如何报|缴费|交费|缴纳|怎么交|放假|寒假|暑假|开学|校历"),
]

FOCUS_LABEL = {k: label for k, label, _ in FOCUS_RULES}
# 模型报问面时说的是这些中文说法，反向映射回规则里的键，认不出的丢掉
FOCUS_BY_LABEL = {label: k for k, label, _ in FOCUS_RULES}
FOCUS_KEYS = {k for k, _label, _p in FOCUS_RULES}


def pick_answer_line(text: str, item: dict[str, Any], lines: list[Any]) -> int | None:
    """表里点了哪一处，就只返回那一行；同名时取更短、更具体的那行。"""
    q = norm(_PLACE_SUFFIX.sub("", (text or "").strip()))
    if len(q) < 2:
        return None
    best: int | None = None
    best_key: tuple[int, int, int] = (-1, 0, 0)

    def consider(idx: int, name: str, line: str) -> None:
        nonlocal best, best_key
        n = norm(name)
        if len(n) < 2:
            return
        pos = _find_span(n, q)
        if pos < 0:
            return
        key = (pos, len(n), -len(norm(line)))
        if key > best_key:
            best, best_key = idx, key

    for i, entry in enumerate(lines):
        if isinstance(entry, dict):
            line = entry.get("line", "")
            for name in [entry.get("name", ""), *(entry.get("names") or [])]:
                consider(i, name, line)
    if best is not None:
        return best
    # 兼容纯字符串行：用条目别名回找（如场馆速查）
    for i, line in enumerate(lines):
        if isinstance(line, dict):
            continue
        for alias in item.get("aliases") or []:
            consider(i, _PLACE_SUFFIX.sub("", alias), line)
    return best


def detect_focus(text: str, item: dict[str, Any]) -> list[str]:
    """返回最多三个聚焦点，按规则顺序（越具体越靠前）。"""
    hits: list[str] = []
    for key, _label, pattern in FOCUS_RULES:
        if re.search(pattern, text):
            hits.append(key)
    # 问的是「带什么材料」，别把整段流程也铺上来；明确问流程时才两样都给
    if "material" in hits and "steps" in hits and not re.search(
            r"怎么办|流程|步骤|如何|怎么|预约|放假", text):
        hits.remove("steps")
    # 问「怎么交钱」时先答流程，再答多少钱；只截两点时不能把流程挤掉
    if "steps" in hits and re.search(
            r"怎么交|怎么缴|如何交|如何缴|怎么缴费|如何缴费|缴费流程|交费流程", text):
        hits = ["steps"] + [h for h in hits if h != "steps"]
    # 太泛的问法（只问"怎么办"）就回到整体
    if not hits or hits == ["steps"]:
        return ["overview"]
    # 问资格的，常常顺带问时间/地点；只端资格那一面会把同句里的另一半问话丢掉。
    # 已经点了「办理流程」就不再补整体——两面读的是同一份流程，补了会把同一步摆两遍。
    if "conditions" in hits and "overview" not in hits and "steps" not in hits:
        hits.insert(hits.index("conditions") + 1, "overview")
    # 一句话里问了三件事（多少钱、几点、带什么）就答三面，别把第三问悄悄扔掉
    return hits[:3]


_SRC_META: dict[str, dict[str, str]] = {}


def src_label(slug: str) -> dict[str, str]:
    """把来源 slug 翻成「谁说的」：官网标题，或公众号名 + 推文标题 + 日期。"""
    if not _SRC_META:
        for fname, kind in (
            ("index.json", "官网"), ("crawl-index.json", "官网"), ("cdp-index.json", "官网"),
            ("wechat-index.json", "公众号"), ("chsi-index.json", "学信网"),
            ("moe-index.json", "教育部"), ("national-index.json", "国家政策"),
            ("extra-index.json", "官网"), ("huibian-index.json", "制度汇编"),
            ("corpus-index.json", "本地文件"),
            ("wendao-index.json", "问道原文"), ("wendao-extra-index.json", "问道原文"),
            ("attachments-text-index.json", "官网附件"),
            # 图书馆的规章、阅读报告、新闻公告只登记在这份索引里；不加载它，
            # 数据表那几百行的出处只能退回内部编号（文献保障-0174252e…）。
            ("ilib-list-index.json", "图书馆"),
        ):
            f = ROOT / "sources" / fname
            if not f.exists():
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            for key, meta in data.items():   # 变量名别用 slug，会把函数参数覆盖掉
                if key in _SRC_META:
                    continue
                if meta.get("kind") == "wechat" or "wechat" in fname:
                    label = f"{meta.get('account','公众号')}｜{meta.get('title','')[:28]}"
                    _SRC_META[key] = {"label": label, "kind": "公众号", "date": meta.get("date", ""), "url": meta.get("url", "")}
                else:
                    lab = (meta.get("title") or "官网")[:40]
                    ps = meta.get("page_start")
                    if ps:
                        lab = f"{lab} · p.{ps}"
                    # 问道补充件自己标了「官方通知 / 会议纪要」，比统一的兜底类别准确
                    real_kind = meta.get("kind") if fname.startswith("wendao-extra") else None
                    _SRC_META[key] = {"label": lab, "kind": real_kind or kind,
                                      "date": meta.get("published", "") or "", "url": meta.get("url", "")}
    return _SRC_META.get(slug, {"label": slug, "kind": "未知", "date": "", "url": ""})


def _ev_items(ev: dict) -> list[dict[str, str]]:
    if not ev:
        return []
    if "sources" in ev:
        return ev["sources"]
    return [ev]


def _best_quote(ev: dict, text: str, min_overlap: int = 4) -> dict[str, str] | None:
    """在一组原文里挑和这句话最贴的一段；贴不上就不硬引。"""
    want = bigrams(norm(text))
    best, best_n = None, 0
    for one in _ev_items(ev):
        q = one.get("quote", "")
        n = len(want & bigrams(norm(q)))
        if n > best_n:
            best, best_n = one, n
    if not want or best is None:
        return None
    # 短句容易靠「号楼」这类常见字凑巧重合，比例也要够
    return best if best_n >= min_overlap and best_n / len(want) >= 0.2 else None


def _applicable_step_rows(item: dict[str, Any], known: dict[str, str]) -> list[dict[str, Any]]:
    """按已知条件筛掉不适用分支；条件还没问清时保留该分支，别把答案删成一行。"""
    rows = item.get("steps") or []
    out = []
    for s in rows:
        cond = s.get("if")
        if cond and any(k in known and known[k] != v for k, v in cond.items()):
            continue
        out.append(s)
    return out or rows


def _applicable_steps(item: dict[str, Any], known: dict[str, str]) -> list[str]:
    return [_step_what(s) for s in _applicable_step_rows(item, known)]


def _narrow_steps(text: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """只按步骤显式标注的 tags 收窄，别拿字面重合去猜——猜错就漏掉另一支。"""
    if len(rows) <= 2 or not (text or "").strip():
        return rows
    tagged = [s for s in rows if isinstance(s, dict) and s.get("tags")]
    if not tagged:
        return rows
    qn = norm(text)
    # 命中更长的 tag 说明问得更具体：「上床下桌」该压过泛泛的「床」，
    # 但只差一个字的并列问法（「床和桌子多大」）仍然一起给。
    scored = []
    for s in tagged:
        hit = max((len(norm(str(t))) for t in s["tags"] if norm(str(t)) and norm(str(t)) in qn), default=0)
        if hit:
            scored.append((hit, s))
    if not scored:
        return rows
    top = max(n for n, _ in scored)
    hits = [s for n, s in scored if n >= top - 1]
    # 带 if 的是并列分支，不是先后步骤，砍掉一支会把另一种情况答错；
    # 但问句命中的都是不带分支的通用步骤时（如「快递地址怎么写」），可以只留那一步
    if any(isinstance(s, dict) and s.get("if") for s in rows) and any(
            isinstance(s, dict) and s.get("if") for s in hits):
        return rows
    return hits


def _flow_rows(item: dict[str, Any], known: dict[str, str], text: str) -> list[dict[str, Any]]:
    """先按条件筛分支，再按问句收窄；用户已经选过的分支不能再被 tags 收窄掉。"""
    rows = _applicable_step_rows(item, known or {})
    narrowed = _narrow_steps(text, rows)
    forced = [
        s for s in rows
        if isinstance(s, dict) and isinstance(s.get("if"), dict) and s["if"]
        and all(known.get(k) == v for k, v in s["if"].items())
    ]
    if not forced:
        return narrowed
    keep = {id(s) for s in narrowed} | {id(s) for s in forced}
    return [s for s in rows if id(s) in keep]


_PHONE_ALL = re.compile(
    r"全部|所有|一页|清单|完整|每个部门|哪里查|在哪查|哪儿查|怎么查|哪里看|在哪看")
_PHONE_ITEM_ID = "bumen-dianhua"


def _phone_menu(text: str, top: dict[str, Any]) -> dict[str, Any] | None:
    """一页速查别一口气甩九个号码：问得笼统时先让用户选部门。"""
    if top.get("id") != _PHONE_ITEM_ID or _PHONE_ALL.search(text):
        return None
    rows = [s for s in (top.get("steps") or []) if isinstance(s, dict)]
    if len(rows) < 3 or len(_narrow_steps(text, rows)) < len(rows):
        return None
    opts = []
    for s in rows:
        label = _step_label(s)
        num = re.search(r"\d{4,}(?:\s*[、，,]\s*\d{4,})*", _step_what(s))
        opts.append({
            "id": top["id"],
            "title": f"{label}咨询电话",
            "label": label,
            "dept": num.group(0) if num else "",
        })
    opts.append({"id": top["id"], "title": "所有部门电话", "label": "全部部门", "dept": "一页看完"})
    return {
        "matched": True,
        "query": text,
        "normalized": "各部门电话 · 请选择部门",
        "confidence": 0.6,
        "band": "low",
        "ambiguous": True,
        "item": public(top),
        "answers": [],
        "hold": True,
        "followups": [],
        "disambiguate": opts,
        "clarify": "要查哪个部门的电话？选一个，我把号码给你。",
        "focus": [],
        "quotes": [],
        "map": None,
        "rule_unsure": False,
    }


_FACET_COVER = {
    "办理时间": re.compile(
        r"\d{1,2}:\d{2}|[0-9]+\s*点|开门|关门|开放时间|营业|供应|值班|服务时间|工作时间"),
    "费用": re.compile(
        r"\d+\s*元|免费|收费|自理|自费|付费|价格|工本费|缴费|购电|交费|"
        r"学费|交纳|缴纳|退还|结算|减免|资助|补偿"),
    "要带什么": re.compile(
        r"携带|带上?|材料|证件|服装|帽子|上衣|裤子|鞋|物品|自备|准备|"
        r"申请表|证明|准考证|身份证"),
    "办理地点": re.compile(
        r"位于|位置|地点|地址|楼内|区内|馆内|厅内|层|室|楼|门|侧|"
        r"平台|网站|网址|线上|网上|APP|app|系统|公众号|微信|邮箱|邮寄"),
    "办理时限": re.compile(
        r"\d+\s*(?:天|日|个工作日|周|月|年)内|截止|之前|以前|有效期|过期"),
    "多久出结果": re.compile(
        r"\d+\s*(?:天|日|个工作日|周|个月|月|年)|"
        r"[一二三四五六七八九十两]+(?:天|日|周|个月|月|年)|当场|立等|即时"),
    "数量": re.compile(r"\d+\s*(?:本|册|个|张|份|间|条|次|门|人)"),
    "条件与限制": re.compile(
        r"条件|资格|准入|门槛|不得|不能|仅限|只限|须|应当|需要|符合|不符合|不接受|面向|除外"),
}


def _facet_covered(label: str, parts: list[dict[str, Any]]) -> bool:
    """答复正文里已经写到这一面时，别再补一句「官方页面没有写」。"""
    pat = _FACET_COVER.get(label)
    if not pat:
        return False
    for p in parts:
        if not p.get("found"):
            continue
        chunks = [p.get("text") or ""]
        for s in p.get("steps") or []:
            if isinstance(s, dict):
                chunks.extend(str(s.get(k) or "") for k in ("what", "where", "when"))
            else:
                chunks.append(str(s))
        for ln in p.get("lines") or []:
            if isinstance(ln, dict):
                chunks.extend(str(ln.get(k) or "") for k in ("text", "what", "label"))
            else:
                chunks.append(str(ln))
        if pat.search(" ".join(chunks)):
            return True
    return False


def _part_body(p: dict[str, Any]) -> str:
    """一面的答复正文（步骤、清单都算进去），用来比两面重不重叠。"""
    chunks = [str(p.get("text") or "")]
    for s in p.get("steps") or []:
        chunks.append(" ".join(str(s.get(k) or "") for k in ("what", "where", "when"))
                      if isinstance(s, dict) else str(s))
    for ln in p.get("lines") or []:
        chunks.append(str(ln.get("text") if isinstance(ln, dict) else ln))
    return " ".join(chunks)


def _body_overlap(new_body: str, parts: list[dict[str, Any]]) -> bool:
    """要补的这一面里，七成以上的说法已经在别处出现过——那就是同一份内容摆两遍。"""
    want = bigrams(norm(new_body)) - NOISE_BIGRAMS
    if not want:
        return True
    have: set[str] = set()
    for p in parts:
        have |= bigrams(norm(_part_body(p))) - NOISE_BIGRAMS
    return len(want & have) / len(want) >= 0.7


# 问句里的疑问词、助词和单字虚词都当分隔符用，剥掉之后剩下的才是「用户点名要的东西」
# 「就」不在里面：就业比副词「就」常见得多，切开就把「基层就业项目」切碎了
_CLAUSE_SPLIT = re.compile(r"[，,、；;？?！!\n]|(?:还有|以及|顺便|另外|再问)")
_ASK_WORDS = re.compile(
    r"能不能|可不可以|可以吗|行不行|是不是|要不要|有没有|算不算|或者|几点|分别|各自|"
    r"怎么办|怎么样|怎么|怎样|如何|什么样|什么|哪些|哪个|哪种|哪里|哪儿|多少|多久|"
    r"多长时间|什么时候|为何|为什么|能否|是否|需要|应该|可以|能够|几|时候|情况|问题|"
    r"一下|这个|那个|这种|那种|请问|想知道|告诉|说说|讲讲|查一下|麻烦|"
    r"吗|呢|啊|吧|呀|的|了|着|过|我|你|他|她|它|咱|这|那|"
    r"都|还|也|又|再|才|只|很|太|更|最|极|挺|别|"
    r"是|有|要|会|能|可|该|看|问|说|想|得|地|和|跟|与|或|及|于|对|从|向|为|以|"
    r"在|去|到|把|被|给|让|叫|使")
# 这些词就算没在答案里出现，也不代表漏答了一问：泛指的动词和身份词
_ASK_IGNORE = {
    "学校", "中国传媒大学", "中传", "学生", "本科生", "研究生", "新生", "毕业生",
    "老师", "同学", "办理", "申请", "手续", "流程", "规定", "政策", "官方", "通知",
    "东西", "事项", "内容", "办法", "确定", "提交", "参加", "记录", "帮忙", "帮忙办",
    "怎么办", "怎么弄", "什么样", "一回事", "报名",
}
# 虚词剥完之后剩下的碎词，开头是这些字就说明切坏了，不报
_ASK_DANGLING = "者业点个些们等里内上中"
# 结尾粘着这几个字才去掉：「绩点里」报成「绩点」，「转其他学院」削掉「其他」后不留碎词。
# 不能拿 _ASK_DANGLING 去尾，那会把「微专业」削成「微专」
_ASK_TAIL = "里中内其"
# 多分句的问句里，只有真的在发问的那一句才算「问了没答」；
# 「户口迁到学校后，身份证丢了怎么补办」前半句是背景，不是问题
_CLAUSE_ASKING = re.compile(
    r"[？?]|吗|呢|怎么|怎样|如何|什么|哪|多少|几|多久|能否|是否|能不能|可不可以|"
    r"要不要|有没有|算不算|是不是")


def _ask_terms(clause: str) -> list[str]:
    """把一个分句里用户点名的实词挑出来。"""
    s = _ASK_WORDS.sub(" ", _mn(clause))
    seen: list[str] = []
    for raw in s.split():
        # 尾巴上粘着的虚字去掉，「绩点里」报成「绩点」，用户才认得出是自己的词
        t = raw.rstrip(_ASK_TAIL)
        if len(t) < 2 or t in _ASK_IGNORE or t[0] in _ASK_DANGLING:
            continue
        if any(t in o or o in t for o in seen):
            continue
        seen.append(t)
    return seen


# 「有哪几种」这类问的是清单，答案里没有并列项就算没答上
_ENUM_ASK = re.compile(r"有哪几种|哪几种|分几种|有哪几类|哪几类")
# 用户嘴里的词和官方文件里的词对不上时，按同一件事算
_ASK_VARIANT = {
    "交钱": ("缴费", "交费", "缴纳", "交纳", "收费", "免费", "元"),
    "退钱": ("退还", "退款", "结算", "退费"),
    "给钱": ("发放", "补贴", "资助", "元"),
    "多久": ("工作日", "天内", "日内", "周内", "期限"),
    "在哪": ("位于", "地址", "楼", "层", "室"),
    "丢": ("遗失", "丢失", "挂失", "补办"),
    "赔": ("赔偿", "遗失", "倍"),
    "罚款": ("滞纳", "处罚", "元"),
    "免训": ("免训", "免于", "缓训"),
    "违约": ("违约", "解约", "赔偿"),
    "满足": ("符合", "满足", "达到"),
}


def _covered(term: str, hay: str, meta: str) -> bool:
    """答案里写到了这个词。

    四字词按两字一段比，免得「用吹风机」因为答案写的是「禁止使用电吹风」就判成没答；
    条目标题、别名、关键词也算，那说明这条就是讲它的，缺的只是某一面的数据。
    """
    both = f"{hay} {meta}"
    if term in both:
        return True
    for v in _ASK_VARIANT.get(term, ()):
        if v in both:
            return True
    if len(term) < 3:
        return False
    return any(term[i:i + 2] in both for i in range(len(term) - 1))


def _unasked(text: str, top: dict[str, Any],
             parts: list[dict[str, Any]]) -> list[str]:
    """问句点了、答案里却没说到的那几问，用用户自己的词报出来。

    比的是这次给出的答案（正文、步骤、引文），加上条目自己的标题和关键词，
    所以这句话只对得上眼前的回答，不会把「库里有」说成「库里没有」。
    多分句的问句报整个分句（「能分期吗」），单分句的报缺的那个词（「免训」）。
    """
    chunks: list[str] = []
    for p in parts:
        # 面标题也算答到了：卡片上摆着「条件与限制」那一块，就不能再说「条件这一问没答到」
        chunks.append(str(p.get("label") or ""))
        chunks.append(str(p.get("text") or ""))
        for s in p.get("steps") or []:
            if isinstance(s, dict):
                chunks.extend(str(s.get(k) or "") for k in ("what", "where", "when"))
            else:
                chunks.append(str(s))
        for ln in p.get("lines") or []:
            chunks.append(str(ln.get("text") if isinstance(ln, dict) else ln))
        for q in p.get("quotes") or []:
            chunks.append(str(q.get("quote") if isinstance(q, dict) else q))
    hay = _mn(" ".join(chunks))
    meta = _mn(" ".join([
        str(top.get("title") or ""),
        " ".join(top.get("aliases") or []),
        " ".join(top.get("keywords") or []),
    ]))
    # 问的是清单，答案里却没有并列项，就是没答上
    listed = hay.count("、") + hay.count("；") >= 2
    clauses = [c.strip() for c in _CLAUSE_SPLIT.split(text or "") if len(_mn(c)) >= 4]
    multi = len(clauses) >= 2
    out: list[str] = []
    for clause in clauses:
        if multi and not _CLAUSE_ASKING.search(clause):
            # 「户口迁到学校了，毕业怎么迁出去」前半句是背景，不是问题，别拿它去比答案
            continue
        if _ENUM_ASK.search(clause):
            if listed:
                continue
            # 报「XX的种类」，别报「有哪几种」——后者拼进「这一问，这次没答到」读不通。
            # 多分句的问句走下面报原话那条路，不受这里影响。
            subj = [t for t in _ask_terms(clause) if not _ENUM_ASK.search(t)]
            miss = [f"{subj[0]}的种类" if subj else "种类清单"]
        else:
            miss = [t for t in _ask_terms(clause) if not _covered(t, hay, meta)]
            if not miss:
                continue
        if multi:
            # 报原话，别报剥完虚词的碎词；太长的分句截到 16 字
            piece = re.sub(r"[\s，,、；;？?！!]+$", "", clause)[:16]
        else:
            piece = "、".join(miss[:2])
        if piece and not any(piece in o or o in piece for o in out):
            out.append(piece)
    return out[:2]


def _answer_hay(parts: list[dict[str, Any]]) -> str:
    """这次真正给用户看的正文和步骤，拼成一串好拿去比词。"""
    chunks: list[str] = []
    for p in parts:
        chunks.append(str(p.get("text") or ""))
        for s in p.get("steps") or []:
            if isinstance(s, dict):
                chunks.extend(str(s.get(k) or "") for k in ("what", "where", "when"))
            else:
                chunks.append(str(s))
        for ln in p.get("lines") or []:
            chunks.append(str(ln.get("text") if isinstance(ln, dict) else ln))
    return _mn(" ".join(chunks))


def _quote_support(quote: str, hay: str) -> int:
    """这句原文和正文重合了多少个双字词，重合越多越能撑住结论。"""
    q = _mn(quote)
    if len(q) < 2 or not hay:
        return 0
    return sum(1 for i in range(len(q) - 1) if q[i:i + 2] in hay)


def _order_quotes(quotes: list[dict[str, Any]],
                  parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把最能撑住这次结论的原文排到前面。

    原来引文是按 evidence 的键名顺序端的：答的是第 6 步，端出来的却是第 0、1 步的原文，
    用户一对照就觉得引文和结论对不上。这里只改顺序，一条引文都不增不删不改字。
    """
    if len(quotes) < 2:
        return quotes
    hay = _answer_hay(parts)
    if not hay:
        return quotes
    return sorted(quotes, key=lambda q: -_quote_support(str(q.get("quote") or ""), hay))


def _answer_one(item: dict[str, Any], focus: str, known: dict[str, str] | None = None,
                text: str = "") -> dict[str, Any]:
    """从结构化数据 + 原文引文里拼出这一面的答案。"""
    ev = item.get("evidence") or {}

    def quotes_for(*prefixes: str) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        seen: set[str] = set()
        for k, v in ev.items():
            if not any(k.startswith(p) for p in prefixes):
                continue
            for one in _ev_items(v):
                q = one.get("quote", "")
                if not q or q in seen:
                    continue
                seen.add(q)
                meta = src_label(one.get("src", ""))
                out.append({"quote": q, "src": one.get("src", ""), **meta})
        return out

    if focus == "overview":
        rows = _flow_rows(item, known or {}, text)
        steps = [
            {"when": _step_label(s), "what": _step_what(s)}
            if isinstance(s, dict) else {"what": str(s)}
            for s in rows
        ]
        answer = item.get("answer")
        return {
            "focus": "overview",
            "label": "官方答复" if answer else "整体流程",
            "text": answer or (_join_steps(rows) if rows
                              else "官方页面没有给出可执行步骤。"),
            "steps": steps,
            "quotes": quotes_for("answer") if answer else quotes_for("steps."),
            "found": bool(answer or steps),
        }

    if focus == "material":
        names = [m["name"] for m in item.get("materials", [])]
        return {
            "focus": focus,
            "label": FOCUS_LABEL[focus],
            "text": "、".join(names) if names else None,
            "quotes": quotes_for("materials."),
            "found": bool(names),
        }

    if focus == "steps":
        rows = _flow_rows(item, known or {}, text)
        return {
            "focus": focus,
            "label": FOCUS_LABEL[focus],
            "text": _join_steps(rows) if rows else None,
            "steps": rows,
            "quotes": quotes_for("steps."),
            "found": bool(rows),
        }

    if focus == "pitfalls":
        ps = item.get("pitfalls") or []
        return {
            "focus": focus,
            "label": FOCUS_LABEL[focus],
            "text": "；".join(ps) if ps else None,
            "quotes": quotes_for("pitfalls."),
            "found": bool(ps),
        }

    if focus == "conditions":
        # 资格类问法要的是「谁能办、什么情况下不行」，别把逾期提醒这类注意事项一起端上来；
        # 一条都没筛着时按「官方没写这一面」处理：拿全量注意事项顶上，等于把不相干的话贴上「条件」的标签。
        ps = item.get("pitfalls") or []
        keep = re.compile(r"不得|不能|不接受|仅限|只限|须|应当|需要|符合|除外|排除|面向|资格|条件")
        idxs = [i for i, p in enumerate(ps) if keep.search(p)]
        rows = [ps[i] for i in idxs]
        return {
            "focus": focus,
            "label": FOCUS_LABEL[focus],
            "text": "；".join(rows) if rows else None,
            "quotes": quotes_for(*[f"pitfalls.{i}" for i in idxs]),
            "found": bool(rows),
        }

    if focus == "contact":
        contact = item.get("contact") or item.get("dept")
        qs = quotes_for("contact")
        return {
            "focus": focus,
            "label": FOCUS_LABEL[focus],
            "text": contact,
            "quotes": qs,
            "quoted": bool(qs),
            "found": bool(contact),
        }

    # 同一地点分两个园区（快递驿站 / 电动车充电桩）：按用户说的园区取分支。
    # 单值 location 只写了其中一个园区，直接端出去会把另一处答错。
    if focus == "location" and (known or {}).get("campus"):
        rows, qs, seen = [], [], set()
        for n, s in enumerate(item.get("steps") or []):
            if (s.get("if") or {}).get("campus") != known["campus"]:
                continue
            rows.append(s.get("what", ""))
            for one in _ev_items((item.get("evidence") or {}).get(f"steps.{n}")):
                if one.get("quote") and one["quote"] not in seen:
                    seen.add(one["quote"])
                    qs.append({"quote": one["quote"], "src": one.get("src", ""),
                               **src_label(one.get("src", ""))})
        if rows:
            return {
                "focus": "location", "label": FOCUS_LABEL["location"],
                "text": " ".join(rows), "found": True, "quotes": qs,
            }

    # 问「在哪」而条目没单列 location：官方答复里就写着楼/层/室时，直接给答复
    if focus == "location" and not item.get("location") and item.get("answer") \
            and re.search(r"号楼|楼|层|室|厅|馆|校区|地址|位于", item["answer"]):
        steps = _applicable_steps(item, known or {})
        return {
            "focus": "overview",
            "label": "官方答复",
            "text": item["answer"],
            "steps": steps,
            "quotes": quotes_for("answer"),
            "found": True,
        }

    # 单值字段
    value = item.get(focus)
    return {
        "focus": focus,
        "label": FOCUS_LABEL[focus],
        "text": value,
        "quotes": quotes_for(focus),
        "found": bool(value),
    }


def place_parts(places: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for h in places:
        quotes = []
        if h.get("quote") and h.get("src"):
            quotes = [{"quote": h["quote"], "src": h["src"], **src_label(h["src"])}]
        out.append({
            "focus": "location", "label": "位置",
            "text": h.get("line") or h.get("name", ""),
            "found": True, "quotes": quotes,
        })
    return out


def place_item(places: list[dict[str, Any]]) -> dict[str, Any]:
    want = ("campus-changguan-weizhi" if places[-1].get("name") in VENUE_PLACE_NAMES
            else "campus-louming")
    return next((i for i in ITEMS if i["id"] == want), ITEMS[0])


def _place_slot_item(places: list[dict[str, Any]]) -> dict[str, Any] | None:
    """地点本身带分支问题（快递驿站分校内 / 梆子井）时返回该条目。"""
    names = {h.get("keyword", "") for h in places} | {h.get("name", "") for h in places}
    names = {n for n in names if len(n) >= 3}
    if not names:
        return None
    for it in ITEMS:
        if not it.get("slots"):
            continue
        tags = [t for t in [it.get("title", ""), *(it.get("aliases") or []),
                            *(it.get("keywords") or [])] if len(t) >= 3]
        if any(n in t or t in n for n in names for t in tags):
            return it
    return None


def related_contacts(text: str, k: int = 3) -> list[dict[str, Any]]:
    """没命中条目时，按用途/部门带出公开电话和邮箱，省得用户再点一层。"""
    f = ROOT / "contacts.json"
    if not f.exists():
        return []
    q = norm(text)
    if len(q) < 2:
        return []
    qb = bigrams(q)
    scored: list[tuple[int, dict[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for c in json.loads(f.read_text(encoding="utf-8")).get("items", []):
        hay = norm((c.get("purpose") or "") + (c.get("dept") or ""))
        shared = len(qb & bigrams(hay))
        if shared < 1:
            continue
        key = (str(c.get("kind")), str(c.get("value")))
        if key in seen:
            continue
        seen.add(key)
        scored.append((shared, c))
    scored.sort(key=lambda x: -x[0])
    return [{
        "kind": c.get("kind"), "value": c.get("value"), "purpose": c.get("purpose"),
        "dept": c.get("dept"), "source_url": c.get("source_url"),
    } for _, c in scored[:k]]


def dept_hints(text: str) -> list[dict[str, Any]]:
    """事项库没覆盖时，按学校分工给归口线索（联想层，非官方流程）。"""
    try:
        data = json.loads((ROOT / "departments.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    q = norm(text)
    out = []
    for dep in data.get("departments", []):
        hit = [kw for kw in dep.get("scope", []) if norm(kw) and norm(kw) in q]
        if hit:
            out.append({
                "name": dep["name"],
                "url": dep["url"],
                "matched": hit[:3],
                "basis": dep.get("basis", ""),
            })
    return out[:2]


def _known_slots(text: str, item: dict[str, Any]) -> dict[str, str]:
    """从问题里抽已经说过的条件，避免重复问。"""
    q = norm(text)
    known: dict[str, str] = {}
    for s in item.get("slots", []):
        hints = s.get("hints") or {}
        hits = [
            opt for opt in s.get("options", [])
            if any(norm(c) and norm(c) in q for c in [opt, *(hints.get(opt) or [])])
        ]
        # 一句里同时点了两个选项（「生源地和校园地有什么区别」）时不预判，
        # 两边都列出来，别拿第一个选项把另一个分支筛掉。
        if len(hits) == 1:
            known[s["key"]] = hits[0]
    return known


def _followups(
    item: dict[str, Any], focus_keys: list[str], known: dict[str, str]
) -> list[dict[str, Any]]:
    """只问还缺的、且真的会改变答案的问题。"""
    out: list[dict[str, Any]] = []
    overview = "overview" in focus_keys
    for s in item.get("slots", []):
        if s["key"] in known:
            continue
        decides = s.get("decides") or []
        blocking = s.get("blocking", True)
        blocks = blocking and (bool(set(decides) & set(focus_keys)) or (overview and bool(decides)))
        if not blocks:
            continue
        out.append(
            {
                "key": s["key"],
                "question": s["ask"],
                "why": s.get("why") or "这一项会改变答案",
                "options": s.get("options", []),
                "decides": decides,
                "blocks": True,
            }
        )
    return out


@steped("route", pick=lambda out: {"rewrites": out[1], "changed": out[0] is not None} if isinstance(out, tuple) and out[1] else {})
def llm_route(
    text: str, candidates: list[tuple[dict[str, Any], int]],
    history: list[dict[str, str]] | None = None,
    status: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """规则拿不准时，让模型先把问题翻译成多种校园说法，再在候选里挑。

    只做「翻译 + 挑一个」，不生成任何事实。模型给的改写会拿回规则里重新检索，
    用来补上候选池没覆盖到的条目。默认开启，命令行设 ROUTER_LLM=0 可关；
    模型异常一律当没选，不影响原有回答，但失败原因会记进 status。
    """
    if not candidates:
        return None, []
    menu = "\n".join(
        f"- {i['id']}：{i['title']}（别名：{'、'.join((i.get('aliases') or [])[:4])}）"
        for i, _ in candidates
    )
    prompt = pp.assemble("route", {"menu": menu})
    try:
        msgs = _with_history(prompt, text, history)
        raw = ds_chat(
            msgs,
            max_tokens=220,
            json_mode=True,
        )
        data = json.loads(raw) or {}
    except Exception as e:  # noqa: BLE001
        if status is not None:
            status["error"] = _llm_err_text(e)
        return None, []
    if not isinstance(data, dict):
        return None, []
    picked = data.get("id")
    rewrites = _clean_rewrites(data.get("rewrites"), text)
    for i, _ in candidates:
        if i["id"] == picked:
            return i, rewrites
    return None, rewrites


def _clean_rewrites(raw: Any, text: str) -> list[str]:
    out: list[str] = []
    if not isinstance(raw, list):
        return out
    src = norm(text)
    for one in raw:
        q = str(one or "").strip()
        n = norm(q)
        if not n or n == src or n in {norm(x) for x in out}:
            continue
        if len(n) < 2 or len(n) > 24:
            continue
        out.append(q)
        if len(out) >= 6:
            break
    return out


ASSOC_MIN = 70   # 模型没调用成功时，改写只能靠关键词兜底：这条地板留着
ASSOC_GAP = 5    # 且要与第二名拉开差距，避免拿改写去猜


def rewrite_ranked(rewrites: list[str], limit: int = 12) -> list[tuple[dict[str, Any], int]]:
    """把模型自己给出的校园说法逐条拿去检索，合成一个新候选池。

    用户怎么说、缩写成什么样，没人能预先列全；能列全的是模型转译出来的说法。
    这个池子只负责「把可能相关的条目端到模型面前」，定条的仍然是模型。
    """
    best: dict[str, int] = {}
    for q in rewrites:
        for it, sc in rank(q):
            if sc <= 0:
                continue
            if it["id"] not in best or sc > best[it["id"]]:
                best[it["id"]] = sc
        if len(best) >= limit * 3:
            break
    rows = sorted(((ITEM_BY_ID[i], s) for i, s in best.items()),
                  key=lambda x: -x[1])
    return rows[:limit]


def assoc_pick(rewrites: list[str]) -> tuple[dict[str, Any], int] | None:
    """把模型给的校园说法逐条拿回规则里检索，取最强的一条。

    只在「规则拿不准 + 开启模型裁决」时调用，正常强命中不经过这里。
    """
    best: tuple[dict[str, Any], int] | None = None
    for q in rewrites:
        rows = rank(q)
        if not rows:
            continue
        it, sc = rows[0]
        rival = rows[1][1] if len(rows) > 1 else 0
        if sc < ASSOC_MIN or sc - rival < ASSOC_GAP:
            continue
        if best is None or sc > best[1]:
            best = (it, sc)
    return best


@steped("free_answer", pick=lambda out: {"gate": "generated"} if out else {})
def llm_free_answer(text: str, history: list[dict[str, str]] | None = None,
                    status: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """事项库一条都没对上时，才让模型直接回答。

    只由 miss 分支调用；命中了任何条目的问答路径不经过这里，
    所以已有条目的回答不受影响。生成内容只随响应返回，不写进 items.json。
    """
    prompt = pp.assemble("free_answer", {})
    try:
        msgs = _with_history(prompt, text, history)
        raw = ds_chat(
            msgs,
            max_tokens=700,
            json_mode=True,
        )
        data = json.loads(raw) or {}
        if status is not None:
            status["asked"] = True
    except Exception as e:  # noqa: BLE001
        if status is not None:
            status["error"] = _llm_err_text(e)
        return None
    answer = str(data.get("answer") or "").strip()
    if len(answer) < 8:
        return None
    conf = str(data.get("confidence") or "low").strip()
    return {
        "text": answer[:1500],
        "confidence": conf if conf in ("low", "medium", "high") else "low",
        "caveat": str(data.get("caveat") or "").strip()[:200] or None,
        "model": MODEL,
        "disclaimer": "这段回答由模型直接生成，没经过事项库和官方原文核对，用之前自己再确认一次。",
    }


def with_free_answer(resp: dict[str, Any], text: str, llm_on: bool,
                     history: list[dict[str, str]] | None = None,
                     status: dict[str, Any] | None = None) -> dict[str, Any]:
    if llm_on:
        gen = llm_free_answer(text, history, status=status)
        if gen:
            resp["llm_answer"] = gen
    if status is not None:
        resp["model_route"] = status
    return resp


HEADLINE_PUNCT = re.compile(r"[?？“”《》「」『』]")
HEADLINE_LINK = re.compile(r"https?://|www\.|[a-z0-9-]+\.(?:cn|com|net|org|edu|gov)(?:\.[a-z]{2,3})?",
                           re.IGNORECASE)
HEADLINE_PHONE = re.compile(r"\d{3,4}-\d{2,4}-\d{4}")


def _headline_ok(head: str, body: str) -> bool:
    """总括能不能用：长度、标点、网址、电话过关，数字必须逐段在正文里出现过。

    数字不是一律禁——「学校共有 8 个餐厅」正文里逐字有，丢了反而不如模型写的。
    要拦的是正文里没有的数字，那才是模型自己编的。
    """
    if not head or len(head) > 24:
        return False
    if HEADLINE_PUNCT.search(head) or HEADLINE_LINK.search(head):
        return False
    runs = re.findall(r"\d+", head)
    if HEADLINE_PHONE.search(head) or any(len(r) >= 5 for r in runs):
        return False
    body_runs = set(re.findall(r"\d+", body))
    return all(r in body_runs for r in runs)


@steped("headline", pick=lambda out: {"gate": "ok"} if out else {})
def llm_headline(text: str, body: str, llm_on: bool,
                 status: dict[str, Any] | None = None) -> str | None:
    """卡片顶部那句总括，只概括已经答出来的正文；不合格就回退条目标题。

    带数字的一律拦掉：模型很自然会把「8 个餐厅」「400-168-6616」写进标题，
    而标题后面不跟引文，等于把没核对过的数值放到最显眼的位置。
    """
    if not llm_on or not api_key() or not body:
        return None
    prompt = pp.assemble("headline", {"q": text, "body": body[:1200]})
    try:
        raw = ds_chat([{"role": "system", "content": prompt}],
                      max_tokens=80, json_mode=True)
        data = json.loads(raw) or {}
    except Exception as e:  # noqa: BLE001
        if status is not None:
            status["headline_error"] = _llm_err_text(e)
        return None
    head = str(data.get("headline") or "").strip()
    if not _headline_ok(head, body):
        if status is not None and head:
            status["headline_dropped"] = head[:40]
        return None
    return head


def _headline_body(parts: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for part in parts:
        if not part.get("found"):
            continue
        if part.get("text"):
            out.append(str(part["text"]))
        out.extend(str(s.get("what") if isinstance(s, dict) else s)
                   for s in (part.get("steps") or []))
        out.extend(str(line) for line in (part.get("lines") or []))
    return "\n".join(x for x in out if x.strip())


CONDENSE_MAX = 30


def _history_questions(history: list[dict[str, str]] | None, limit: int = 3) -> list[str]:
    """上一轮只取「问」，不取「答」：回答正文里全是上一条事项的词，喂进检索就跟着跑偏。"""
    return [str(m.get("content") or "").strip()
            for m in (history or []) if m.get("role") == "user"][-limit:]


@steped("ctx_need")
def llm_needs_context(text: str, ctx_title: str, prev_q: str = "",
                      status: dict[str, Any] | None = None) -> bool | None:
    """这句要不要接着上一条才答得清楚；判不出来返回 None，由调用方退回词表。

    词表判续问只有两种错法，而这两种都错在词表本身：句里带「怎么」就判续问，
    自带主体的句子（「滑雪」「校园卡丢了怎么补办」）被拼上上一条；词表没覆盖的
    续问（「几天能办好」）判独立，答不上。一次几十字的调用替掉这两半。
    """
    if not ctx_title or not api_key():
        return None
    prompt = pp.assemble("ctx_need", {"title": ctx_title, "prev_q": prev_q, "q": text})
    try:
        data = json.loads(ds_chat([{"role": "system", "content": prompt}],
                                  max_tokens=60, json_mode=True)) or {}
    except Exception as e:  # noqa: BLE001
        if status is not None:
            status["ctx_need_error"] = _llm_err_text(e)
        return None
    if not isinstance(data, dict):
        return None
    need = data.get("need")
    if not isinstance(need, bool):
        if status is not None and "need" in data:
            status["ctx_need_dropped"] = str(need)[:20]
        return None
    if status is not None:
        status["ctx_need"] = "yes" if need else "no"
        status["ctx_need_why"] = str(data.get("why") or "")[:40]
    return need


_REF_HEAD = ("那", "这", "它", "该", "还", "也", "要", "多少", "几", "多久", "什么", "怎么")


def _looks_elliptic(t: str) -> bool:
    """这句是不是「指代式追问」：缺主语/对象，靠上一条才说得通。

    「那要带什么材料」「几天能办好」「周末呢」是；「饿了」「下雨了」这种自带新话题的不是。
    补全把上一条主题补进开头时，只有这一种才放行。
    """
    s = str(t or "").strip()
    return s.startswith(_REF_HEAD) or s.endswith(("呢", "吗", "么"))


@steped("condense", pick=lambda out: {"condensed_query": out} if out else {})
def llm_condense(text: str, history: list[dict[str, str]] | None,
                 status: dict[str, Any] | None = None) -> str | None:
    """把省略式追问补成一句能独立检索的问句；补不出就用原句，绝不断整轮。

    照抄上一问、超长、空串都算没补成——照抄会把用户已经问过的东西再检索一遍，
    还不如原句加上上下文标题那条老路。
    """
    asked = _history_questions(history)
    if not asked or not api_key():
        return None
    prompt = pp.assemble("condense", {"history": "；".join(asked), "q": text})
    try:
        raw = ds_chat([{"role": "system", "content": prompt}],
                      max_tokens=80, json_mode=True)
        data = json.loads(raw) or {}
    except Exception as e:  # noqa: BLE001
        if status is not None:
            status["condense_error"] = _llm_err_text(e)
        return None
    out = str(data.get("query") or "").strip()
    if not out or len(out) > CONDENSE_MAX or out in asked or out == text:
        if status is not None and out:
            status["condense_dropped"] = out[:40]
        return None
    # 补全句必须从用户原话开头，除非原话本身是「指代式追问」（那/这/它/还/要/几天…，
    # 或以呢/吗收尾）——那种把上一条的主题补进开头是正常的。
    # 「饿了」这种没有指代词的新话题被拼成「宿舍购电饿了怎么办理」时，前缀就是旧话题盖上来：
    # 后面的说法、重排、复核都沿着旧话题走，复核还会判「答上了」。
    if not out.startswith(text) and not _looks_elliptic(text):
        if status is not None:
            status["condense_dropped"] = out[:40]
        return None
    return out


@steped("pick_line", pick=lambda out: {"gate": "ok"} if isinstance(out, int) else {})
def llm_pick_line(text: str, item: dict[str, Any], lines: list[Any],
                  status: dict[str, Any] | None = None) -> int | None:
    """问的是具体哪一处时，让模型只从官方原文行里挑一行，不生成任何内容。"""
    menu = "\n".join(
        f"{i}. {(l.get('line') if isinstance(l, dict) else l)}"
        for i, l in enumerate(lines)
    )
    prompt = (
        f"下面是「{item['title']}」的官方原文行，编号从 0 开始：\n{menu}\n\n"
        "用户只问了其中一处。请挑出最对应的那一行编号；问的是整张表就返回 -1。"
        "只输出 JSON：{\"line\": 0}。不要解释，不要改写原文。"
    )
    try:
        raw = ds_chat(
            [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            max_tokens=60,
            json_mode=True,
        )
        if status is not None:
            status["asked"] = True
        picked = (json.loads(raw) or {}).get("line")
    except Exception as e:  # noqa: BLE001
        if status is not None:
            status["error"] = _llm_err_text(e)
        return None
    if isinstance(picked, int) and 0 <= picked < len(lines):
        return picked
    return None


# 敏感词 = 被路由审计证明「会引起错误跳转或反问」的词（tools/derive_sensitive.py 生成）
# 策略型提问：问"怎么选/值不值/规划"，官方文件里没有答案，需要转成具体办理事项
STRATEGY = re.compile(r"策略|怎么选|如何选择|值不值|值得吗|规划|建议|前景|好不好|哪个好|要不要|该不该|值不值得|还是.*好")
CAMPUS_HINT = re.compile(r"学籍|选课|成绩|考试|证明|校园卡|宿舍|网络|图书馆|医疗|报销|奖|助|贷|"
                         r"转专业|休学|复学|毕业|学位|留学|档案|户口|场馆|报修|体测")

_SENSITIVE: list[str] = []


def _load_sensitive() -> list[str]:
    """读 sensitive.json；没有就退回一组保守的默认词。"""
    f = ROOT / "sensitive.json"
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            words = [w["w"] for w in data.get("words", []) if w.get("w")]
            if words:
                return words
        except Exception:  # noqa: BLE001
            pass
    return ["申诉", "休学", "复学", "处分", "验证码"]


def sensitivity(text: str) -> dict[str, Any]:
    """判断问题是否属于"测试证明容易跳错"的一类，给出是否建议开启模型裁决。"""
    global _SENSITIVE
    if not _SENSITIVE:
        _SENSITIVE = _load_sensitive()
    hits = [w for w in _SENSITIVE if w in text]
    return {"hits": hits, "sensitive": bool(hits), "suggest_llm": bool(hits)}


_PLANS: dict[str, Any] = {}


def _load_plans() -> dict[str, Any]:
    global _PLANS
    f = ROOT / "transfer-plans.json"
    if not f.exists():
        return {}
    mt = f.stat().st_mtime
    if _PLANS.get("_mtime") != mt:
        data = json.loads(f.read_text(encoding="utf-8"))
        data["_mtime"] = mt
        _PLANS = data
    return _PLANS


_MAJOR_ALIASES: dict[str, Any] = {}


def _load_major_aliases() -> dict[str, Any]:
    global _MAJOR_ALIASES
    f = ROOT / "major-aliases.json"
    if not f.exists():
        return {}
    mt = f.stat().st_mtime
    if _MAJOR_ALIASES.get("_mtime") != mt:
        data = json.loads(f.read_text(encoding="utf-8"))
        data["_mtime"] = mt
        _MAJOR_ALIASES = data
    return _MAJOR_ALIASES


def _mn(s: str) -> str:
    """NFKC 后再套 norm：全角括号、空格、标点都去掉，专有名词才好比。"""
    return norm(unicodedata.normalize("NFKC", s or ""))


def _major_key(s: str) -> str:
    """专业名比对键：去掉「(至2024)」年代标记和结尾的「专业」。"""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[（(]\s*至\s*\d{4}\s*[)）]", "", s)
    k = _mn(s)
    return k[:-2] if k.endswith("专业") else k


_TRANSFER_CACHE: dict[str, Any] = {}


def _transfer_entities() -> dict[str, Any]:
    """把 16 份计划 + 2026 版简称表摊平成可匹配的「学院/专业」实体，按文件 mtime 缓存。"""
    plans, aliases = _load_plans(), _load_major_aliases()
    stamp = (plans.get("_mtime"), aliases.get("_mtime"))
    if _TRANSFER_CACHE.get("stamp") == stamp:
        return _TRANSFER_CACHE["data"]

    colleges: list[dict[str, Any]] = []
    seen_college: set[tuple[str, str]] = set()

    def add_college(name: str, plan_college: str, display: str, has_plan: bool) -> None:
        key = _mn(name)
        if len(key) < 2 or (key, plan_college) in seen_college:
            return
        seen_college.add((key, plan_college))
        colleges.append({"kind": "college", "key": key, "college": plan_college,
                         "display": display, "has_plan": has_plan})

    for label, meta in (aliases.get("colleges") or {}).items():
        pc = meta.get("plan_college") or label
        for nm in [label, *(meta.get("aliases") or []), pc]:
            add_college(nm, pc, pc if nm == pc else label, bool(meta.get("has_plan")))
    for college, plan in plans.items():
        if college == "_mtime":
            continue
        for nm in [college, *(plan.get("aliases") or [])]:
            add_college(nm, college, college, True)

    majors: list[dict[str, Any]] = []
    for entry in aliases.get("majors") or []:
        names: list[tuple[str, str, int]] = []
        if entry.get("abbr"):
            names.append((_mn(entry["abbr"]), "简称", 3))
        clean = re.sub(r"[（(]\s*至\s*\d{4}\s*[)）]", "",
                       unicodedata.normalize("NFKC", entry.get("major", "")))
        full = _major_key(clean)
        if full:
            names.append((full, "专业名", 2))
        base = re.match(r"^([^（(]+)", clean)
        if base and _major_key(base.group(1)) != full:
            names.append((_major_key(base.group(1)), "专业名", 1))
        for inside in re.findall(r"[（(]([^）)]+)[)）]", clean):
            ik = _mn(inside)
            if len(ik) >= 3:
                names.append((ik, "方向", 2))
                if ik.endswith("方向") and len(ik) > 4:
                    names.append((ik[:-2], "方向", 2))
        for key, how, pri in names:
            if len(key) < 2:
                continue
            majors.append({"kind": "major", "key": key, "how": how, "pri": pri,
                           "entry": entry})
    data = {"colleges": colleges, "majors": majors}
    _TRANSFER_CACHE.update({"stamp": stamp, "data": data})
    return data


PLAN_NOTE = ("以下为 2025 年秋季学期接收计划的完整提取：学院、专业、年级和条件/材料/考核/联系方式"
             "均按 PDF 原表保留，不删行；专业简称按《中国传媒大学本科专业简称（2026年版）》对应。"
             "2026 年是否沿用、是否新设或停招，以本科生院和学院当年通知为准。")

NO_PLAN_NOTE = ("2026年版专业简称表里有这个学院，但现有 16 份 2025 年秋季学期接收计划中没有它。"
                "这不代表不能转，具体要看学院当年通知；我不拿别的学院的文件顶替。")

_STATUS_NOTE = {
    "until": "该专业 {until} 年起停招，2025 年接收计划未单列。",
    "until_listed": "该专业名称 {until} 年起停招；下面展示的是接收计划中对应的「{plan_major}」行。",
    "unlisted": "该专业在 2026 年版简称表中仍为现行专业，但 2025 年接收计划未单列；下面是该学院整份计划。",
    "no_plan": "2026 年版简称表列有这个专业，但 16 份 2025 年接收计划中没有它所在的学院。",
}
_STATUS_ORDER = {"current": 0, "unlisted": 1, "until_listed": 2, "until": 3, "no_plan": 4}


def _major_focus(entries: list[dict[str, Any]], college: str = "") -> dict[str, Any] | None:
    """同一个简称可能有多条（舆情、游艺）：先按学院过滤，再优先现行专业。"""
    if college:
        same = [e for e in entries
                if e["entry"].get("plan_college") == college or e["entry"].get("college") == college]
        if same:
            entries = same
        else:
            return None
    if not entries:
        return None
    return sorted(entries, key=lambda e: (
        _STATUS_ORDER.get(e["entry"].get("status", ""), 9),
        e["entry"].get("id", 0),
    ))[0]


def _building_spans(text: str) -> list[tuple[int, int]]:
    """文本里命中的楼宇/场馆名区间；学院名不算，免得把「新闻学院」也当楼屏蔽。"""
    qn = _mn(text)
    spans: list[tuple[int, int]] = []
    for p in campus_data().get("pois") or []:
        for raw in [p.get("name", ""), *(p.get("aliases") or [])]:
            n = _mn(raw)
            if len(n) < 2 or not n.endswith(("楼", "馆", "厅", "场", "门")):
                continue
            start = 0
            while True:
                i = qn.find(n, start)
                if i < 0:
                    break
                spans.append((i, i + len(n)))
                start = i + 1
    return spans


def _find_entities(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """在一句话里找学院和专业；长名优先，互不重叠。"""
    data = _transfer_entities()
    qn = _mn(text)
    blocks = _building_spans(text)
    groups: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    for row in [*data["majors"], *data["colleges"]]:
        key = row["key"]
        start = qn.find(key)
        while start != -1:
            groups.setdefault((row["kind"], start, start + len(key)), []).append(row)
            start = qn.find(key, start + 1)

    ordered = []
    for (kind, start, end), rows in groups.items():
        best = max(r.get("pri", 2) for r in rows)
        rows = [r for r in rows if r.get("pri", 2) == best]
        ordered.append({"kind": kind, "start": start, "end": end,
                        "rows": rows, "len": end - start})
    # 长名优先；同长时专业优先于学院（「新闻」既像学院简称又像专业简称时，落到新闻学）
    ordered.sort(key=lambda g: (-g["len"], 0 if g["kind"] == "major" else 1, g["start"]))

    accepted: list[dict[str, Any]] = []
    for group in ordered:
        if any(s <= group["start"] and group["end"] <= e for s, e in blocks):
            continue
        overlap = any(
            group["start"] < a["end"] and a["start"] < group["end"]
            and not (group["start"] == a["start"] and group["end"] == a["end"]
                     and group["kind"] != a["kind"])
            for a in accepted
        )
        if overlap:
            continue
        accepted.append(group)

    colleges = [g for g in accepted if g["kind"] == "college"]
    majors = [g for g in accepted if g["kind"] == "major"]
    return colleges, majors


def transfer_plan(text: str) -> dict[str, Any] | None:
    """问「转去 XX 学院 / 转 XX 专业要什么条件」时，直接给完整接收计划。"""
    strong = bool(re.search(r"转专业|转入|转到|转去|转进|换专业|接收计划|接收条件", text))
    # 微专业名里常带「数智」「传播」这类学院/专业词，且「招生对象及条件」
    # 会命中 plan_words；不能让微专业的问法落到转专业接收计划上。
    if "微专业" in text:
        return None
    # 辅修、双学位是独立招生项目，带专业名问材料 / 条件时同样不该落到转专业计划；
    # 只有问句本身明确在说转专业，才继续看接收计划。
    if ("辅修" in text or "双学位" in text) and not strong:
        return None
    if PLACE_ASK.search(text) and not strong:
        return None
    soft = bool(re.search(r"转|换", text))
    plan_words = bool(re.search(r"条件|要求|接收|计划|考核|材料|联系|能不能|可以转|想学|想读", text))
    colleges, majors = _find_entities(text)
    qn = _mn(text)
    # 只报简称（数媒技 / 游艺）或「学院+专业」（新闻学院舆情）也按转专业计划答
    abbr_hit = any(_mn(r["entry"].get("abbr") or "") == qn
                   for g in majors for r in g["rows"])
    # 「学院+专业」只当整句就是在说这两个词（如「新闻学院舆情」）才算转专业；
    # 否则「2026年秋季数智品牌传播微专业招生简章」里的「数智」「传播」会把微专业简章劫走
    pair_only = False
    if colleges and majors and not (strong or soft or plan_words):
        rest = qn
        for g in sorted(colleges + majors, key=lambda g: g["start"], reverse=True):
            rest = rest[:g["start"]] + rest[g["end"]:]
        rest = re.sub(r"[\s，。、？?！!的学专业学院]", "", rest)
        # 「数智电竞多少钱」里的「数智」「电竞」是微专业名，不是学院+专业；
        # 只有整句真的只剩这两个词（或纯问法）时才按转专业答。
        pair_only = rest in {"", "怎么样", "如何", "呢", "吗", "情况", "好不好", "难不难"}
    if not (strong or soft or (majors and plan_words)
            or pair_only or abbr_hit) or (not colleges and not majors):
        return None

    # 一句话里提了两个学院（「从新闻学院转电视学院」）时，认「转」字后面的目标学院
    target = -1
    for word in ("转到", "转去", "转入", "转至", "换到", "换去", "转", "换"):
        target = qn.rfind(word)
        if target != -1:
            break
    college_group = None
    if colleges:
        after = [g for g in colleges if g["start"] >= target] if target != -1 else []
        if after:
            college_group = sorted(after, key=lambda g: g["start"])[-1]
        else:
            college_group = sorted(colleges, key=lambda g: g["start"])[0]

    college = college_group["rows"][0]["college"] if college_group else ""
    display = college_group["rows"][0]["display"] if college_group else ""

    focus_group = None
    if majors:
        pool = majors
        if college_group:
            others = [g for g in majors
                      if not (g["start"] == college_group["start"]
                              and g["end"] == college_group["end"])]
            if others:
                pool = others
        if college:
            same = [g for g in pool
                    if any(r["entry"].get("plan_college") == college
                           or r["entry"].get("college") == college for r in g["rows"])]
            focus_group = same[0] if same else None
        else:
            focus_group = pool[0]

    picked = _major_focus(focus_group["rows"], college) if focus_group else None
    if picked:
        entry = picked["entry"]
        college = entry.get("plan_college") or entry.get("college") or college
        if entry.get("college") and entry.get("college") != entry.get("plan_college"):
            display = entry["college"]
        elif not display:
            display = college
    elif not college and focus_group:
        entry = focus_group["rows"][0]["entry"]
        college = entry.get("plan_college") or entry.get("college") or ""
        display = entry.get("college") or college

    if not college:
        return None

    plans = _load_plans()
    plan = plans.get(college)
    focus = None
    if picked:
        entry = picked["entry"]
        note = entry.get("note") or ""
        status = entry.get("status", "")
        if status in _STATUS_NOTE and status != "current":
            note = "；".join(x for x in (
                note,
                _STATUS_NOTE[status].format(until=entry.get("until") or "",
                                            plan_major=entry.get("plan_major") or ""),
            ) if x)
        focus = {
            "query": picked["key"],
            "matched_by": picked["how"],
            "abbr": entry.get("abbr", ""),
            "major": entry.get("major", ""),
            "college": entry.get("college", college),
            "plan_college": entry.get("plan_college") or college,
            "plan_major": entry.get("plan_major", ""),
            "status": status,
            "until": entry.get("until"),
            "note": note,
            "ambiguous": bool(entry.get("ambiguous")),
        }

    if not plan:
        plan_out = {
            "college": college,
            "college_label": display or college,
            "renamed": bool(display and display != college),
            "focus": focus,
            "majors": [],
            "file": "",
            "note": NO_PLAN_NOTE,
            "no_plan": True,
        }
        return {
            "college": college, "display": display or college, "no_plan": True,
            "plan": plan_out, "focus": focus, "parts": [], "file": "",
            "note": NO_PLAN_NOTE,
        }

    selected = None
    if focus and focus.get("plan_major"):
        want = _major_key(focus["plan_major"])
        selected = next((m for m in plan.get("majors") or []
                         if _major_key(m.get("name", "")) == want), None)

    parts: list[dict[str, Any]] = []
    blocks = selected.get("blocks") if selected else []
    if not blocks:
        blocks = [plan]  # 学院整体列（第一个专业以前没有单列时，整份计划的汇总）
    for label, key in (("接收条件", "conditions"), ("材料要求", "materials"),
                       ("考核安排", "exam"), ("联系方式", "contacts")):
        lines = []
        seen: set[str] = set()
        for block in blocks:
            for q in block.get(key) or []:
                q = (q or "").strip()
                if not q or q in seen:
                    continue
                seen.add(q)
                lines.append(q)
        if not lines:
            continue
        parts.append({
            "focus": key, "label": label,
            "text": "；".join(lines) if key != "contacts" else " · ".join(lines),
            "lines": lines, "found": True,
            "quotes": [{"quote": q, "src": plan["slug"]} for q in lines],
        })
    if selected:
        note_lines = []
        for block in selected.get("blocks") or []:
            note_lines.extend(q for q in block.get("note") or [] if q)
        if note_lines:
            parts.append({
                "focus": "note", "label": "备注",
                "text": "；".join(note_lines), "lines": note_lines, "found": True,
                "quotes": [{"quote": q, "src": plan["slug"]} for q in note_lines],
            })

    plan_out = {
        "college": college,
        "college_label": display or college,
        "renamed": bool(display and display != college),
        "focus": focus,
        "majors": plan.get("majors") or [],
        "file": plan.get("file", ""),
        "full_text": plan.get("full_text", ""),
        "note": PLAN_NOTE,
    }
    return {"college": college, "display": display or college, "no_plan": False,
            "plan": plan_out, "focus": focus, "selected": selected,
            "parts": parts, "file": plan.get("file", ""), "note": PLAN_NOTE}


def original_hits(text: str, k: int = 3, min_score: float = 0.28,
                  status: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """规则没命中时，去原文向量库找几段；只给原文线索，不生成事实。"""
    try:
        import vector_index

        hits = vector_index.search(text, k=k, min_score=min_score)
        if not hits and vector_index.load() is None and status is not None:
            status["vector_error"] = "原文向量库没建（sources/vector 缺失）"
        return hits
    except Exception as e:  # noqa: BLE001
        if status is not None:
            status["vector_error"] = _llm_err_text(e)
        return []


def _src_item_index() -> dict[str, list[str]]:
    """原文 doc slug → 引用它的条目。

    向量库里的 item_ids 是建库时的快照，条目新增后会对不上；
    这里按条目证据里的 src 现算，保证新条目也能被 rerank 捞到。
    """
    global _SRC_ITEMS
    if _SRC_ITEMS is None:
        m: dict[str, list[str]] = {}
        for it in ITEMS:
            for ev in (it.get("evidence") or {}).values():
                for one in _ev_items(ev):
                    s = str(one.get("src") or "").strip()
                    if s:
                        m.setdefault(s, []).append(it["id"])
        _SRC_ITEMS = m
    return _SRC_ITEMS


# 2026-11-07 定案：100 题带标签集两个独立样本 对82/错8/拒10 与 对81/错9/拒10，
# 效用 (82-24)/2=56，裸 fusion 同集 78/14/8 效用 36。三档归因（关组装 45、关改写腿 38、
# 地板抬到 0.75 反涨错答）与各档判据见
# docs/superpowers/plans/2026-11-07-retrieval-judgment-chain.md 与 _review_items/归因三档_20261107.md
RETRIEVAL_MODE = str(os.getenv("RETRIEVAL", "fusion")).strip().lower()

# 两道输出闸（2026-11-06 平衡实测定案，2026-11-07 起开）。
# DECLINE_REFUSES：模型看完候选说「都没答上」时，不要再拿规则腿第一名替它作答。
#   100 题带标签实测里，这一条把错答 14→9，代价是要和改写腿一起上——单独用会赔 6 条答对。
# MIN_ANSWER_CONF：置信低于地板的命中转拒答。实测 0.7 与 0.8 等价，0.9 会把覆盖打到 59%；
#   装闸后再扫 0.75 反而多放进错答（P12），地板停在 0.7。
DECLINE_REFUSES = str(os.getenv("DECLINE_REFUSES", "1")).strip().lower() not in ("0", "false", "off", "no")
MIN_ANSWER_CONF = float(os.getenv("MIN_ANSWER_CONF", "0.7") or 0)

# —— 2026-11-07 剩下的四件候选：一律先按「关」装进来，边际在最终世界里实测完才拍默认值。
# TIE_BREAK：模型给分严格并列时按候选池名次取靠前那条。治的是「同一题两跑换了条目」。
TIE_BREAK = str(os.getenv("TIE_BREAK", "0")).strip().lower() not in ("0", "false", "off", "no")
# RECHECK_SKIP_ABOVE：最终得分（规则分与模型分取大）到线就不再全文复核。0=一律复核（现行）。
#   省的是每题 1.00 次调用、约 34% token；风险是复核正是兜「高分错答」的那道，所以阈值必须实测。
RECHECK_SKIP_ABOVE = int(float(os.getenv("RECHECK_SKIP_ABOVE", "0") or 0))
# PHRASE_CACHE：同一句问话的官方说法只问模型一次，键是整句归一＋prompt 版本（改了 prompt 自动作废）。
PHRASE_CACHE = str(os.getenv("PHRASE_CACHE", "0")).strip().lower() not in ("0", "false", "off", "no")
# POOL_META：候选行补上归口、适用对象和出处文档名，让模型判「谁管的」而不是只看标题。
POOL_META = str(os.getenv("POOL_META", "0")).strip().lower() not in ("0", "false", "off", "no")
# STRONG_HIT（2026-11-09 定案）：强命中免检线。分数语义见 score_item：100=标题/别名原样命中，
#   97=去掉问法词后原样命中，98/99=关键词叠加（函数末尾封顶 99）。旧线 96 把「关键词叠到 99」
#   也算强命中——2026-11-09 靶向复测：把 99 分放回判定层后，「考试不及格」0/8 → 8/8，
#   「宿舍电器」「超市」「补考重修」两臂不变、0 次拒答。默认走 literal。
#   取值："literal"（默认，只认 100 与 97）｜"96"（旧行为，含 99）｜其它数字按阈值。
STRONG_HIT_MODE = str(os.getenv("STRONG_HIT", "literal")).strip().lower()


def _strong_hit(score: int) -> bool:
    """这条规则分够不够格整块跳过模型判定层。"""
    if STRONG_HIT_MODE == "literal":
        return score >= 97 and score != 99
    try:
        return score >= float(STRONG_HIT_MODE)
    except ValueError:
        return score >= 96


def _output_gate(model_route: dict[str, Any], score: int) -> str:
    """这题该不该从「答」改成「不答」。返回原因串，空串表示照常答。"""
    if DECLINE_REFUSES and model_route.get("gate") == "llm_declined":
        return "decline_gate"
    if MIN_ANSWER_CONF and 0 < score < MIN_ANSWER_CONF * 100:
        return "conf_floor"
    return ""
FTS_DB = ROOT / "kb.sqlite"
_FTS_CON: Any = None


def _fts_con():
    """BM25 腿的连接。库不在就当这条腿没有，原有回答不受影响。"""
    global _FTS_CON
    if _FTS_CON is None:
        if not FTS_DB.exists():
            return None
        _FTS_CON = sqlite3.connect(f"file:{FTS_DB.as_posix()}?mode=ro", uri=True,
                                   check_same_thread=False)
    return _FTS_CON


def _gram_terms(q: str) -> list[str]:
    """和建库那侧的 bigrams() 同一切词法，否则查询串和索引对不上。"""
    toks: list[str] = []
    for run in re.findall(r"[一-鿿]+|[^\s一-鿿]+", q or ""):
        if len(run) == 1 and "\u4e00" <= run <= "\u9fff":
            toks.append(run + "　")
        elif "\u4e00" <= run[0] <= "\u9fff":
            toks.extend(run[i:i + 2] for i in range(len(run) - 1))
        else:
            toks.append(run.lower())
    out: list[str] = []
    for t in toks:
        if t not in out:
            out.append(t)
    return out


def _fts_rows(kind: str, text: str, k: int) -> list[tuple[dict[str, Any], float]]:
    con = _fts_con()
    toks = _gram_terms(text)
    if con is None or not toks:
        return []
    expr = " OR ".join('"' + t.replace('"', "") + '"' for t in toks)
    try:
        rows = con.execute(
            "select ref, bm25(search) from search where search match ? and kind=? "
            "order by 2 limit ?", (expr, kind, max(k * 8, 80))).fetchall()
    except sqlite3.Error:
        return []
    out: list[tuple[dict[str, Any], float]] = []
    seen: set[str] = set()
    for ref, sc in rows:
        if ref in seen or ref not in ITEM_BY_ID:
            continue
        seen.add(ref)
        out.append((ITEM_BY_ID[ref], sc))
        if len(out) >= k:
            break
    return out


def bm25_hits(text: str, k: int = 30) -> list[tuple[dict[str, Any], float]]:
    """BM25 腿：字段级块进 FTS5，按内置 bm25() 名次取条目（值越小越相关）。"""
    return _fts_rows("full", text, k)


def _meta_text(it: dict[str, Any]) -> str:
    """名目串：标题＋别名＋关键词，与建库时 meta 行同一拼法。"""
    return " ".join([str(it.get("title") or "")]
                    + [str(a) for a in (it.get("aliases") or [])]
                    + [str(w) for w in (it.get("keywords") or [])])


def meta_hits(text: str, k: int = 20) -> list[tuple[dict[str, Any], float]]:
    """名目腿：先用 FTS 取候选，再按二字组覆盖率重排。

    bm25() 的长度归一化在这里是反效果——二三十个字的摘录标题天然比几百字的
    名目串得分高，而「学校医保」要的恰恰是别名里写着「医保报销」「校医院报销」
    的那条学生口径条目。覆盖率优先、不罚长度，谁把问句里的词占全了谁在前。
    """
    con = _fts_con()
    toks = _gram_terms(text)
    if con is None or not toks:
        return []
    expr = " OR ".join('"' + t.replace('"', "") + '"' for t in toks)
    try:
        rows = con.execute(
            "select distinct ref from search where search match ? and kind='meta' limit ?",
            (expr, max(k * 10, 200))).fetchall()
    except sqlite3.Error:
        return []
    qset = set(toks)
    scored: list[tuple[dict[str, Any], float]] = []
    for (ref,) in rows:
        it = ITEM_BY_ID.get(ref)
        if it is None:
            continue
        meta = _meta_text(it)
        cover = len(qset & set(_gram_terms(meta))) / len(qset)
        scored.append((it, round(cover, 4)))
    # 同覆盖率下整理条目优先（它分好了费用、时间、材料，摘录只是一个片段），
    # 再看名目串更短的——别名越贴，说明这个词就是这件事的本名。
    scored.sort(key=lambda x: (-x[1], 1 if x[0].get("auto") else 0, len(_meta_text(x[0])), x[0]["id"]))
    return scored[:k]


def vector_item_hits(text: str, k: int = 30,
                     status: dict[str, Any] | None = None) -> list[tuple[dict[str, Any], float]]:
    """向量腿：原文 chunk 命中后换算回条目，取法与现行候选池一致。"""
    hits = original_hits(text, k=12, min_score=0.15, status=status)
    src_items = _src_item_index()
    out: list[tuple[dict[str, Any], float]] = []
    seen: set[str] = set()
    for h in hits:
        slug = str(h.get("source") or h.get("doc") or "").split("~")[0]
        for iid in dict.fromkeys(list(h.get("item_ids") or []) + src_items.get(slug, [])):
            if iid in seen or iid not in ITEM_BY_ID:
                continue
            seen.add(iid)
            out.append((ITEM_BY_ID[iid], float(h.get("score") or 0.0)))
            if len(out) >= k:
                return out
    return out


def rrf_fuse(lists: list[tuple[str, list[tuple[str, float]]]], limit: int = 32,
             k: int = 60) -> list[tuple[str, float, dict[str, Any]]]:
    """Reciprocal Rank Fusion：只认名次不认原分，量纲不同的三路也能合。

    某一路 0 命中不该把条目筛掉——大佬那边 bm25 为 0 的照样进结果，靠 dense 撑住。
    """
    score: dict[str, float] = {}
    meta: dict[str, dict[str, Any]] = {}
    blank = {name: None for name, _entries in lists}
    for name, entries in lists:
        for rank, (key, _sc) in enumerate(entries, 1):
            score[key] = score.get(key, 0.0) + 1.0 / (k + rank)
            meta.setdefault(key, dict(blank))[name] = rank
    ordered = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [(key, sc, meta[key]) for key, sc in ordered]


def fused_candidates(text: str, top_ranked: list[tuple[dict[str, Any], int]],
                     limit: int = 12,
                     status: dict[str, Any] | None = None) -> list[tuple[dict[str, Any], float, dict[str, Any]]]:
    """三路融合出候选池：规则腿、BM25 全文腿、向量腿。每条带各腿名次。

    名额先按腿轮流给（snake merge），剩下的按 RRF 补。纯 RRF 排序下，
    只出现在一条腿里的条目分数永远比不过两条腿都命中的 14 条摘录，
    而「学校医保」要捞的正是只在 BM25 或向量里出现的那条学生口径条目。
    """
    rule = [(it["id"], float(sc)) for it, sc in top_ranked[:40]]
    mt = [(it["id"], sc) for it, sc in meta_hits(text, k=20)]
    bm = [(it["id"], sc) for it, sc in bm25_hits(text, k=40)]
    vec = [(it["id"], sc) for it, sc in vector_item_hits(text, k=30, status=status)]
    lists = [("rule", rule), ("meta", mt), ("bm25", bm), ("vec", vec)]

    scored = rrf_fuse(lists, limit=len(rule) + len(bm) + len(vec) + len(mt) + 1)
    rrf = {key: (sc, meta) for key, sc, meta in scored}
    # 名额按腿分配而不是纯 snake：四路轮转时 12 个名额只够每条腿的前 3 名，
    # 名目腿第 4 名之后的整理条目就再也进不来（11-06 实测 xyy-gongfei 卡在第 4~6 名）。
    quota = {"rule": 4, "meta": 4, "bm25": 3, "vec": 3}
    order: list[str] = []
    for name, entries in lists:
        for key, _sc in entries[:quota.get(name, 3)]:
            if key not in order:
                order.append(key)
    for key, _sc, _meta in scored:
        if key not in order:
            order.append(key)

    out: list[tuple[dict[str, Any], float, dict[str, Any]]] = []
    for key in order[:limit]:
        it = ITEM_BY_ID.get(key)
        if it is not None and key in rrf:
            out.append((it, rrf[key][0], rrf[key][1]))
    if status is not None:
        status["fusion"] = {"rule": len(rule), "meta": len(mt), "bm25": len(bm),
                            "vec": len(vec), "pool": len(out)}
    return out


RERANK_POOL_LIMIT = 14    # 给模型判断的候选池条数上限：11-04 扩池实验的结论是池子越大越容易挑跑偏


def rerank_candidates(
    text: str, ranked: list[tuple[dict[str, Any], int]], limit: int = RERANK_POOL_LIMIT,
    status: dict[str, Any] | None = None, pre_rewrite: bool = True,
) -> list[tuple[dict[str, Any], int]]:
    """规则前排 + 向量命中文档里的条目，合成给模型判断的候选池。

    规则只按关键词打分，问「游泳馆开放时间」会被「图书馆开放时间」抢走；
    向量能捞到游泳馆那段原文，再由模型判断哪条真的回答了问题。

    RETRIEVAL=fusion 时池子改由三路 RRF 融合给出。A/B 只换这一处：
    每条仍带规则腿的分，判分阈值、门、模型调用一概不动。

    pre_rewrite=False 是给改写腿自己用的：官方说法再检一遍时不许再触发一次改写。
    """
    if pre_rewrite and _rewrite_pre_on(ranked):
        return _with_pre_legs(
            rerank_candidates(text, ranked, limit, status, pre_rewrite=False),
            text, limit, status)
    if RETRIEVAL_MODE == "fusion":
        rule_scores = {it["id"]: sc for it, sc in ranked[:400]}
        fused_pool: list[tuple[dict[str, Any], int]] = []
        fused_seen: set[str] = set()
        for it, _sc, _meta in fused_candidates(text, ranked, limit=limit, status=status):
            if it["id"] in fused_seen or it.get("archive_only"):
                continue
            fused_seen.add(it["id"])
            fused_pool.append((it, int(rule_scores.get(it["id"], 0))))
            if len(fused_pool) >= limit:
                break
        if status is not None:
            status["fusion_ids"] = [it["id"] for it, _ in fused_pool]
        return fused_pool

    pool: list[tuple[dict[str, Any], int]] = []
    seen: set[str] = set()

    def add(it: dict[str, Any], sc: int) -> None:
        if len(pool) >= limit or it["id"] in seen or it.get("archive_only"):
            return
        seen.add(it["id"])
        pool.append((it, sc))

    for it, sc in ranked[:8]:
        if sc > 0:
            add(it, sc)

    src_items = _src_item_index()
    qn = norm(text)
    qb = bigrams(qn)
    extra: list[tuple[int, int, dict[str, Any]]] = []
    for h in original_hits(text, k=8, min_score=0.18, status=status):
        slug = str(h.get("source") or h.get("doc") or "").split("~")[0]
        ids = list(h.get("item_ids") or []) + src_items.get(slug, [])
        doc_pick: list[tuple[int, int, dict[str, Any]]] = []
        for iid in dict.fromkeys(ids):
            it = ITEM_BY_ID.get(iid)
            if not it or it.get("archive_only") or it["id"] in seen:
                continue
            sc = score_item(qn, it)
            cover = len(qb & bigrams((it.get("title") or "") + " " + (it.get("answer") or "")))
            if sc <= 0 and cover <= 0:
                continue
            doc_pick.append((sc, cover, it))
        doc_pick.sort(key=lambda x: (-x[0], -x[1]))
        extra.extend(doc_pick[:2])

    extra.sort(key=lambda x: (-x[0], -x[1]))
    for sc, _cover, it in extra:
        add(it, sc)
    return pool


RERANK_MIN = 75     # 顶掉一个已达阈值的规则首选，模型至少要给到这么多
RERANK_ACCEPT = 60  # 规则本来就没到阈值时，接住模型的最低分（低于 RERANK_MIN 算软命中）
RERANK_MARGIN = 10  # 换掉规则首选，必须比规则首选高出这么多


# 模型接口报错时给人看的一句话，别把 JSON 尾巴甩到界面上
def _llm_err_text(e: Exception) -> str:
    s = str(getattr(e, "detail", None) or e).strip()
    s = re.sub(r"\s*\{.*$", "", s).strip().rstrip(" :：")
    return (s[:120] or "模型接口调用失败")


def _rerank_hint(item: dict[str, Any]) -> str:
    text = item.get("answer") or ""
    if not text:
        for s in item.get("steps") or []:
            text = str(s.get("what") or "")
            if text:
                break
    return text.replace("\n", " ")[:70]


TIE_SEEN: list[str] = []    # 归因用：这一趟里出现过同分并列的题（开关关着也记，只数不改）


def _tie_break(pool: list[tuple[dict[str, Any], int]], scores: dict[str, int],
               best: dict[str, Any] | None) -> dict[str, Any] | None:
    """模型给分严格并列时，按候选池名次取靠前那一条；不是并列一律不动。

    并列时模型选的哪条取决于采样运气（同题两跑换条目就是这个原因）。名次顺序是模型
    自己在候选行里看到的顺序，用它定序不改动模型的判断范围。判死（best=None）不动，
    免得定序把「都没答上」救成某一条。
    """
    if best is None or not scores:
        return best
    my = scores.get(best["id"])
    if my is None or my < max(scores.values()):
        return best
    if TIE_BREAK is False and len([1 for v in scores.values() if v == my]) > 1:
        TIE_SEEN.append(best["id"])
    if not TIE_BREAK:
        return best
    for it, _ in pool:
        if scores.get(it["id"]) == my:
            return it
    return best


_OPAQUE_DOC = re.compile(r"^[a-z]+-[0-9a-f]{6,}")


def _doc_label(it: dict[str, Any]) -> str:
    """出处文档名；附件这类只有内部 id 的不摆，摆上去模型也读不出信息。"""
    src = it.get("source") or []
    if isinstance(src, dict):
        src = [src]
    for s in src:
        t = str((s or {}).get("title") or "").strip()
        if t and not _OPAQUE_DOC.match(t):
            return t[:34]
    return "—"


def _pool_row(it: dict[str, Any], hint: str, with_kind: bool = True) -> str:
    """候选池里的一行。

    with_kind=True 是候选重排那套（条目类型＋归口两栏），False 是逐面裁决那套（只有标题）。
    POOL_META 打开才追加 归口／适用对象／出处文档名 三栏：模型判「这条是谁管的、对谁有效」
    靠的就是这两栏，只看标题会把留学生条款当成通用条款端上来。关着时两处的字节与今天相同。
    """
    row = f"- {it['id']}｜{(it.get('title') or '')[:50]}"
    if with_kind:
        row += f"｜{'原文摘录' if it.get('auto') else '整理条目'}｜{it.get('dept') or '—'}"
    if POOL_META:
        aud = "、".join(str(a) for a in (it.get("audience") or [])) or "—"
        if not with_kind:
            row += f"｜归口:{it.get('dept') or '—'}"
        row += f"｜适用:{aud}｜出处:{_doc_label(it)}"
    return f"{row}｜{hint}"


@steped("rerank", pick=lambda out: {"rewrites": out[1]} if isinstance(out, tuple) and len(out) > 1 and out[1] else {})
def llm_rerank(
    text: str, pool: list[tuple[dict[str, Any], int]],
    history: list[dict[str, str]] | None = None,
    status: dict[str, Any] | None = None,
    menu_mode: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    """让 DeepSeek Flash 判断候选里哪条真的回答了问题，并给出校园说法改写。

    这是判断层，不生成事实：只打分、挑条目、认问的是哪一面；改写拿回规则里二次检索。
    模型说「一条都没答上」和「接口没调用成功」是两件事，前者 item=None，后者返回 None。
    menu_mode 是给「用户只输入一个词」的菜单裁决用的：那句输入里没有问题，
    按「有没有答上某个具体问题」去判，候选全是原文摘录时模型一律返回 null。
    """
    menu = "\n".join(
        _pool_row(it, _rerank_hint(it) or "（无摘要）")
        for it, _ in pool
    )
    facet_menu = "、".join(label for _k, label, _p in FOCUS_RULES)
    prompt = pp.assemble("rerank", {"menu": menu, "facet_menu": facet_menu,
                                    "menu_mode": menu_mode})
    try:
        msgs = _with_history(prompt, text, history)
        raw = ds_chat(
            msgs,
            max_tokens=480,
            json_mode=True,
        )
        data = json.loads(raw) or {}
    except Exception as e:  # noqa: BLE001
        if status is not None:
            status["error"] = _llm_err_text(e)
        return None, []
    if not isinstance(data, dict):
        if status is not None:
            status["error"] = "模型返回的不是 JSON"
        return None, []
    rewrites = _clean_rewrites(data.get("rewrites"), text)
    raw_scores = data.get("scores")
    scores: dict[str, int] = {}
    if isinstance(raw_scores, dict):
        for k, v in raw_scores.items():
            try:
                scores[str(k)] = max(0, min(100, int(float(v))))
            except (TypeError, ValueError):
                continue
    # 问面只认规则里已有的那些，模型自己造的词一律丢掉
    facets = [FOCUS_BY_LABEL[str(x).strip()]
              for x in (data.get("facets") or [])
              if isinstance(x, str) and str(x).strip() in FOCUS_BY_LABEL]
    why = str(data.get("why") or "").strip()[:160]
    best_id = str(data.get("best") or "").strip()
    best = ITEM_BY_ID.get(best_id) if best_id and best_id != "null" else None
    if best is None:
        # 看过并否掉了：和调用失败不一样，要把「问过了」这件事记下来
        return {"item": None, "score": 0, "scores": scores, "why": why, "facets": facets}, rewrites
    return {
        "item": best,
        # 模型没给这一条打分时按 60 计：可以软命中，不足以顶掉已达阈值的规则首选
        "score": scores.get(best["id"], RERANK_ACCEPT),
        "scores": scores,
        "why": why,
        "facets": facets,
    }, rewrites


# —— 复核层：模型腿选完之后，再看一次「准备回答」到底答没答上 ——
# 摘要版（只给 70 字）实测改坏 8 题：整理条目的内容常在 steps 里，摘要只看得见第一步，
# 模型就判「答不上」并把题改派给沾边的原文摘录。给条目全貌之后新增改坏 0 题。
# 实测口径与逐题复看：_review_items/实验_复核看全文vs现行_20261104.md、
# _review_items/问题清单与修改建议_20261104全量.md
RECHECK_PROMPT = (
    "用户在问校园办事的事。系统已经选出一条，准备完整这样回答：\n"
    "问题：{q}\n"
    "条目 {chosen_id}（{chosen_title}）：\n{chosen_full}\n\n"
    "下面是候选条目（每条只显示一句摘要）：\n{menu}\n\n"
    "复核要求（只判断，不要自己编事实）：\n"
    "- verdict 判「准备回答」有没有答上用户问的这件事：yes=答上了；partial=答上了但缺关键信息；no=答的是另一件事。\n"
    "- 摘要里没有、正文里有的内容，算答上了；不要因为候选摘要更细就换。\n"
    "- best 填你认为最合适的那一条 id；就选现在这条也填它的 id；全都答不上填 null。\n"
    "- best_answers 单独回答「换成 best 这一条，到底答不答得上用户问的这件事」：yes/no。"
    "只是话题沾边、讲的仍是别的考试或别的部门，就填 no。\n"
    '只输出 JSON：{{"verdict": "yes|partial|no", "best": "条目id或null", '
    '"best_answers": "yes|no", "why": "一句话理由"}}'
)

SECOND_LOOK_PROMPT = (
    "用户在问校园办事的事。系统准备回答的那一条（{chosen_id}）复核后判定答不上用户问的这件事，不再用它。\n"
    "问题：{q}\n\n"
    "下面是库里其余沾边的条目，这次给每条的正文（每条截 300 字）：\n{menu}\n\n"
    "判断要求（只看这些文字，不要自己编事实）：\n"
    "- 逐条判它有没有答上用户问的这件事，答上才选；话题沾边、讲的是别的考试或别的部门，都不算。\n"
    "- best 填最合适那一条的 id；全都答不上填 null。\n"
    "- best_answers 单独回答「best 这一条到底答不答得上」：yes/no。\n"
    '只输出 JSON：{{"best": "条目id或null", "best_answers": "yes|no", "why": "一句话理由"}}'
)


def _item_full_text(item: dict[str, Any], limit: int = 600) -> str:
    """条目全貌：正文＋全部步骤＋材料＋费用/时间/地点＋易错，给复核看，截 limit 字。"""
    parts = [str(item.get("answer") or "")]
    for s in item.get("steps") or []:
        head = "、".join(str(x) for x in [s.get("name"), s.get("what"), s.get("where"), s.get("how")] if x)
        if head:
            parts.append(head)
    for m in item.get("materials") or []:
        if m.get("name"):
            parts.append(f"材料：{m['name']}" + (f"（{m.get('note')}）" if m.get("note") else ""))
    for k in ("fee", "hours", "location", "window", "duration"):
        if item.get(k):
            parts.append(f"{k}：{item[k]}")
    for p in item.get("pitfalls") or []:
        parts.append(f"注意：{p}")
    return "\n".join(x for x in parts if x).strip().replace("\n", " ")[:limit]


@steped("recheck")
def llm_recheck(text: str, chosen: dict[str, Any],
                pool: list[tuple[dict[str, Any], int]]) -> dict[str, Any]:
    """判「准备回答」答没答上，并问「换成那条答不答得上」。失败返回 {"error": …}。"""
    menu = "\n".join(
        f"- {it['id']}｜{(it.get('title') or '')[:50]}｜{'原文摘录' if it.get('auto') else '整理条目'}"
        f"｜{it.get('dept') or '—'}｜{_rerank_hint(it) or '（无摘要）'}"
        for it, _ in pool
    )
    prompt = RECHECK_PROMPT.format(
        q=text, chosen_id=chosen["id"], chosen_title=(chosen.get("title") or "")[:40],
        chosen_full=_item_full_text(chosen), menu=menu,
    )
    try:
        raw = ds_chat(
            [{"role": "system", "content": "你是校园办事问答的复核员，只判断不改写事实。"},
             {"role": "user", "content": prompt}],
            max_tokens=300, json_mode=True,
        )
        data = json.loads(raw) or {}
    except Exception as e:  # noqa: BLE001
        return {"error": _llm_err_text(e)}
    if not isinstance(data, dict):
        return {"error": "模型返回的不是 JSON"}
    best = str(data.get("best") or "").strip()
    return {
        "verdict": str(data.get("verdict") or "").strip().lower(),
        "best": "" if best in ("", "null") else best,
        "answers": str(data.get("best_answers") or "").strip().lower(),
        "why": str(data.get("why") or "").strip()[:180],
    }


def offpool_candidates(text: str, seen_ids: set[str], exclude_id: str,
                        k: int = 10) -> list[dict[str, Any]]:
    """复核说答不上之后，第一次没送进候选池的沾边条目（按规则分取前 k）。"""
    qn = norm(text)
    qb = bigrams(qn)
    rows: list[tuple[int, int, dict[str, Any]]] = []
    for it, sc in rank(text):
        if it.get("archive_only") or it["id"] in seen_ids or it["id"] == exclude_id or sc <= 0:
            continue
        cover = len(qb & bigrams((it.get("title") or "") + " " + (it.get("answer") or "")))
        rows.append((sc, cover, it))
    rows.sort(key=lambda x: (-x[0], -x[1]))
    return [it for _, _, it in rows[:k]]


@steped("second_look")
def llm_second_look(text: str, chosen_id: str,
                    cands: list[dict[str, Any]]) -> dict[str, Any]:
    """第二次确认：把池外条目的正文摊开，问有没有哪一条真答得上。"""
    if not cands:
        return {"best": "", "answers": "", "why": "", "none_in_library": True}
    menu = "\n".join(
        f"- {it['id']}｜{(it.get('title') or '')[:50]}｜{'原文摘录' if it.get('auto') else '整理条目'}"
        f"｜{it.get('dept') or '—'}｜{_item_full_text(it, 300)}"
        for it in cands
    )
    prompt = SECOND_LOOK_PROMPT.format(q=text, chosen_id=chosen_id, menu=menu)
    try:
        raw = ds_chat(
            [{"role": "system", "content": "你是校园办事问答的复核员，只判断不改写事实。"},
             {"role": "user", "content": prompt}],
            max_tokens=240, json_mode=True,
        )
        data = json.loads(raw) or {}
    except Exception as e:  # noqa: BLE001
        return {"error": _llm_err_text(e)}
    if not isinstance(data, dict):
        return {"error": "模型返回的不是 JSON"}
    best = str(data.get("best") or "").strip()
    return {
        "best": "" if best in ("", "null") else best,
        "answers": str(data.get("best_answers") or "").strip().lower(),
        "why": str(data.get("why") or "").strip()[:180],
    }


FACET_MENU_LABEL = "整体流程"
# 「整体流程／官方答复」是 overview 那一面的两种说法，规则里的问面标签没有它们
_FACET_BY_MENU = {FACET_MENU_LABEL: "overview", "官方答复": "overview"}

FACET_FILL_PROMPT = (
    "用户在问校园办事的事，一句话里问了两面。系统已经答了其中一面，这是给出去的内容：\n"
    "问题：{q}\n\n已答内容：\n{answered}\n\n"
    "系统认为下面这几问还没答到：{missing}\n"
    "条目 {item_id}（{item_title}）的正文全貌：\n{item_full}\n\n"
    "判断要求（只判断，不要自己编事实）：\n"
    "- covers：上面「已答内容」其实有没有答到「{missing}」这一问？答到了填 yes，"
    "哪怕它用的词和问句不一样（说了整周开放时间就算答了「周末开吗」）。\n"
    "- 没答到才填 no，并从这些问面里挑一个真能答上这一问的：{facets}。\n"
    "- facet 填选中的问面名字；这些问面都没法答这一问时填 null。\n"
    "- snippet 从条目正文里逐字抄出能回答这一问的那一句，不许改写、不许拼接；"
    "正文里没有这么一句就填 null。\n"
    "- fills 照抄「没答到」那一栏里的说法，只能填一条。\n"
    '只输出 JSON：{{"covers": "yes|no", "facet": "问面名或null", "snippet": "原文一句或null", '
    '"fills": "原话或null", "why": "一句话理由"}}'
)

PROPER_MAP_MIN_POSTINGS = 5    # 至少 5 条条目写过这个名字，才摆给模型当候选名
PROPER_MAP_ADD = 8             # 一次最多端进候选池的条目数
PROPER_MAP_SCOPE = 60          # 名字菜单只从规则排前 60 的条目里取，别把一池子名字全摊开
PROPER_MAP_GLOSS = 14          # 每个名字后面挂的出处片段长度
PROPER_MAP_MAX = 20            # 菜单最多摆 20 个名字，多了按这次的相关度截断

PROPER_MAP_PROMPT = (
    "用户在问校园办事的事，句子里出现了一个用字母写的名称：{said}\n"
    "系统认得的名称只有下面这些（都是这次相关的条目里确实写过的，括号里是它的出处）：\n{names}\n\n"
    "判断要求：\n"
    "- 从上面列表里挑一个和用户说的名称指同一个软件、同一个系统或同一个品牌："
    "简称、缩写、母品牌、俗称都算。\n"
    "- 按实际归属判，不要按拼写像不像判：用户说的若是某个品牌下的产品，就选那个品牌；"
    "括号里的出处写明是哪家软件，就按那家判。\n"
    "- 列表里没有能对上的一定填 null，不要挑一个话题沾边的凑数。\n"
    '只输出 JSON：{{"name": "列表里的名称或null", "why": "一句话理由"}}'
)


def _facet_menu(parts: list[dict[str, Any]]) -> list[str]:
    """还没答过的问面，用模型看得懂的中文说法列出来。"""
    have = {p.get("focus") for p in parts}
    labels = [label for key, label, _p in FOCUS_RULES if key not in have]
    if "overview" not in have:
        labels.insert(0, FACET_MENU_LABEL)
    return labels


def _facet_key(label: str) -> str:
    return _FACET_BY_MENU.get(label, "") or FOCUS_BY_LABEL.get(label, "")


def _answered_brief(parts: list[dict[str, Any]]) -> str:
    """给模型看的「已经答了什么」：每面的标题＋正文，截 900 字。"""
    rows = [f"〔{p.get('label')}〕{_part_body(p)}" for p in parts if p.get("found")]
    return " \n".join(rows)[:900]


@steped("facet_fill")
def llm_facet_fill(text: str, item: dict[str, Any], parts: list[dict[str, Any]],
                   unasked: list[str],
                   known: dict[str, str] | None = None) -> dict[str, Any]:
    """一题两问：模型判「眼前这段答没覆盖第二问」，没覆盖再由它挑这一条目里能答的那一面。

    规则侧的 _unasked 只会按字面比对，一周开放时间答得上「周末开吗」却对不上字面，
    所以这一判断交给模型（2026-11-05 拍板②）。补进来的那一面必须有条目原文撑著：
    模型摘的句子在正文里逐字找不到就不算，声明照旧说「这一问没答到」。
    """
    if not unasked:
        return {"gate": "declined", "why": "系统没报出缺哪一问"}
    prompt = FACET_FILL_PROMPT.format(
        q=text, answered=_answered_brief(parts), missing="；".join(str(u) for u in unasked),
        item_id=item.get("id", ""), item_title=(item.get("title") or "")[:60],
        item_full=_item_full_text(item, 900), facets="、".join(_facet_menu(parts)),
    )
    try:
        data = json.loads(ds_chat(
            [{"role": "system", "content": "你是校园办事问答的复核员，只判断不改写事实。"},
             {"role": "user", "content": prompt}],
            max_tokens=260, json_mode=True)) or {}
    except Exception as e:  # noqa: BLE001
        return {"gate": "error", "error": _llm_err_text(e)}
    if not isinstance(data, dict):
        return {"gate": "error", "error": "模型返回的不是 JSON"}
    why = str(data.get("why") or "").strip()[:180]
    covers = str(data.get("covers") or "").strip().lower()
    if covers == "yes":
        return {"gate": "covered", "why": why}
    if covers != "no":
        return {"gate": "declined", "why": why or "模型没判出覆盖情况"}
    fills = str(data.get("fills") or "").strip()
    if fills not in unasked:
        return {"gate": "declined", "why": f"补的不是系统报的那一问（{fills[:24]}）"}
    key = _facet_key(str(data.get("facet") or "").strip())
    if not key or key in {p.get("focus") for p in parts}:
        return {"gate": "declined", "why": f"问面挑不出或已经答过（{data.get('facet')}）"}
    snippet = str(data.get("snippet") or "")
    if len(_mn(snippet)) < 6 or _mn(snippet) not in _mn(_item_full_text(item, 4000)):
        return {"gate": "declined", "why": "摘的原文在条目正文里逐字找不到"}
    part = _answer_one(item, key, known or {}, text)
    if not part.get("found"):
        return {"gate": "declined", "why": "这一面条目里没写"}
    if _body_overlap(_part_body(part), parts):
        return {"gate": "declined", "why": "补进来会和已答内容重复"}
    return {"gate": "filled", "part": part, "fills": fills, "why": why}


# ---------------------------------------------------------------- 跨条目组装（#56）
# 「图书馆周末开吗」和「学校医保」是同一件事的两面：前者口语和官方说法对不上，
# 检索四条腿没有一条够得着答案条目；后者条目找到了，但一个条目只讲了整件事的一面。
# 两层都靠同一个机制：先让模型把这句话拆成学校文件里会分开写的几面，每面换成
# 官方说法再检索一遍，然后让模型在「这一面的候选」里行使否决权——只认逐字原文，
# 它自己一个字都不写。拼装只在 ASSEMBLE 打开时发生。

# 2026-11-07 定案：关掉组装的归因档 P7 效用 45，开着 56（58/54 两样本），差值远在 ±4 噪声带外。
# 旧那条 206 基线是组装关着时录的，再拿它逐字段 diff 会看到差异，那不是漂移。
ASSEMBLE_MODE = str(os.getenv("ASSEMBLE", "rescue")).strip().lower()   # off | fill | rescue | both
ASSEMBLE_MAX_FACES = 3      # 再多就是在替用户设想他没问的事
ASSEMBLE_PER_FACE = 6       # 端到模型面前的池子条数
ASSEMBLE_QUOTE_MIN = 6      # 短到这个数以下的「原文」撑不住一个面
ASSEMBLE_CONF_CAP = 0.7     # 拼出来的答案天花板：它没经过整条事项的流程校验


def _assemble_on(entry: str) -> bool:
    return ASSEMBLE_MODE in ("both", entry)


def _phrase_useful(ph: str, text: str) -> bool:
    """改写串得还是同一件事，而且真的换了说法。

    两头都闸住：跑偏到另一件事（「图书馆周末开吗」改写成「体育馆开放时间」）靠
    二字组重合挡掉；照抄口语（改写成「周末」）等于没改写，白跑一次检索，挡掉。
    """
    p = _mn(ph)
    if len(p) < 4 or _mn(text) in p or p in _mn(text):
        return False
    grams = [g for g in _gram_terms(text) if len(g) == 2 and "　" not in g]
    return any(g in p for g in grams)


# ①「改写腿事前并」：检索前先让模型把口语换成官方说法，用这些说法再检一遍，
# 只补原句四条腿都够不着的条目，主池的名次顺序不动。REWRITE_PRE 选触发范围。

# 2026-11-07 定案：装闸之后单独归因，关掉改写腿 B 的 P11 效用 38，开着 56，错答 8.5→13。
REWRITE_PRE = str(os.getenv("REWRITE_PRE", "B")).strip().upper()   # OFF | A | B | C
REWRITE_PRE_MAX = 3      # 一次最多取三条官方说法
REWRITE_PRE_SLOTS = 4    # 改写腿最多换掉主池尾部 4 个名额
REWRITE_PRE_KEEP = 8     # 主池前 8 名锁死：改写腿只动第 9 名以后的尾部


def _rewrite_pre_on(ranked: list[tuple[dict[str, Any], int]]) -> bool:
    """三档触发：A 只在融合且规则腿第一名是原文摘录时；B 融合每题；C 两种模式每题。"""
    mode = REWRITE_PRE
    if mode == "OFF" or not ranked:
        return False
    if mode == "C":
        return True
    if RETRIEVAL_MODE != "fusion":
        return False
    if mode == "B":
        return True
    if mode == "A":
        return bool(ranked[0][0].get("auto"))
    return False


_PHRASE_CACHE: dict[str, list[str]] = {}
PHRASE_CACHE_MAX = 512    # 一句键存一条说法表；满了整表清空，不做 LRU（这是省调用不是做缓存库）


@steped("phrase", pick=lambda out: {"pre_phrases": out} if out else {})
def llm_official_phrases(text: str, status: dict[str, Any] | None = None) -> list[str]:
    """同一件事，换成学校文件里可能的写法。只换说法，不拆面也不回答。

    PHRASE_CACHE 打开时按「整句归一＋prompt 版本」缓存结果：改一个字就是另一句话，
    不会把上一句的说法套下来；prompt 文本一改，版本变了旧缓存自动作废。
    """
    if REWRITE_PRE == "OFF":
        return []
    key = pp.cache_key("phrase", {"q": text}, text) if PHRASE_CACHE else ""
    if key and key in _PHRASE_CACHE:
        out = list(_PHRASE_CACHE[key])
        if out and status is not None:
            status["pre_phrases"] = out
        return out
    prompt = pp.assemble("phrase", {"q": text})
    try:
        data = json.loads(ds_chat(
            [{"role": "system", "content": prompt},
             {"role": "user", "content": "只输出 JSON。"}],
            max_tokens=200, json_mode=True)) or {}
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(data, dict):
        return []
    out: list[str] = []
    for x in data.get("phrases") or []:
        ph = str(x).strip()
        if ph and _phrase_useful(ph, text) and ph not in out:
            out.append(ph)
        if len(out) >= REWRITE_PRE_MAX:
            break
    if key:
        if len(_PHRASE_CACHE) >= PHRASE_CACHE_MAX:
            _PHRASE_CACHE.clear()
        _PHRASE_CACHE[key] = list(out)
    if out and status is not None:
        status["pre_phrases"] = out
    return out


def _with_pre_legs(pool: list[tuple[dict[str, Any], int]], text: str, limit: int,
                   status: dict[str, Any] | None) -> list[tuple[dict[str, Any], int]]:
    """官方说法检出来的条目换掉主池尾部，池子总数不变。

    上一版写成「只填主池剩下的空位」，而主池常年是满的 14 条——改写腿于是整体空转，
    48 问实测里 A/B/C 三档命中一模一样就是这么来的。尾部那些位置本来摆着
    模型给 0 分的无关条目（校园卡补卡、成绩单、留级在每道题的池子里轮班），
    拿它们换掉不违背 11-04「池子越大越容易挑跑偏」的结论。
    """
    phrases = llm_official_phrases(text, status)
    if not phrases:
        return pool
    legs = [rerank_candidates(ph, rank(ph), limit=limit, pre_rewrite=False) for ph in phrases]
    have = {it["id"] for it, _ in pool}
    extras: list[tuple[dict[str, Any], int]] = []
    depth = 0
    while len(extras) < REWRITE_PRE_SLOTS and depth < limit:
        for rows in legs:
            if depth >= len(rows):
                continue
            it, sc = rows[depth]
            if it["id"] in have or it.get("archive_only"):
                continue
            have.add(it["id"])
            extras.append((it, sc))
            if len(extras) >= REWRITE_PRE_SLOTS:
                break
        depth += 1
    if not extras:
        return pool
    drop = min(len(extras), max(0, len(pool) - REWRITE_PRE_KEEP))
    before = [it["id"] for it, _ in pool]
    if drop:
        pool = pool[:len(pool) - drop] + extras[:drop]
    if status is not None:
        status["pre_added"] = drop
        status["pre_dropped"] = before[len(before) - drop:] if drop else []
    return pool


@steped("assemble_plan")
def llm_faces_plan(text: str, parts: list[dict[str, Any]],
                   status: dict[str, Any] | None = None) -> dict[str, Any]:
    """这句问话在学校文件里分几面写，每面官方会怎么说。"""
    if not _assemble_on("fill") and not _assemble_on("rescue"):
        return {"gate": "off", "faces": []}
    answered = "；".join(str(p.get("label") or "") for p in parts if p.get("found"))
    prompt = pp.assemble("assemble_plan", {"q": text, "answered": answered})
    try:
        data = json.loads(ds_chat(
            [{"role": "system", "content": prompt},
             {"role": "user", "content": "只输出 JSON。"}],
            max_tokens=320, json_mode=True)) or {}
    except Exception as e:  # noqa: BLE001
        return {"gate": "error", "error": _llm_err_text(e), "faces": []}
    if not isinstance(data, dict):
        return {"gate": "error", "error": "模型返回的不是 JSON", "faces": []}
    faces: list[dict[str, Any]] = []
    for f in data.get("faces") or []:
        if not isinstance(f, dict):
            continue
        name = str(f.get("face") or "").strip()[:24]
        if not name or (answered and _mn(name) in _mn(answered)):
            continue
        phrases = [str(x).strip() for x in (f.get("phrases") or [])
                   if _phrase_useful(str(x), text)][:2]
        if not phrases:
            continue
        faces.append({"face": name, "phrases": phrases})
        if len(faces) >= ASSEMBLE_MAX_FACES:
            break
    if status is not None:
        status.setdefault("assembly", {})["faces"] = [f["face"] for f in faces]
    return {"gate": "ok" if faces else "empty", "faces": faces,
            "why": str(data.get("why") or "")[:160]}


def face_pool(phrases: list[str], limit: int = ASSEMBLE_PER_FACE,
              exclude_ids: set[str] | None = None) -> list[tuple[dict[str, Any], float, dict[str, Any]]]:
    """按官方说法逐串走一遍现行检索，取最好名次合成这一面的池子。"""
    skip = set(exclude_ids or ())
    lists = []
    for ph in phrases[:2]:
        rows = rerank_candidates(ph, rank(ph), limit=limit, pre_rewrite=False)
        lists.append((ph, [(it["id"], float(sc)) for it, sc in rows if it["id"] not in skip]))
    fused = rrf_fuse(lists, limit=limit * 2)
    out: list[tuple[dict[str, Any], float, dict[str, Any]]] = []
    for key, sc, legs in fused:
        it = ITEM_BY_ID.get(key)
        if it is None or it.get("archive_only"):
            continue
        out.append((it, sc, legs))
        if len(out) >= limit:
            break
    return out


def _face_meta_head(it: dict[str, Any], legs: dict[str, Any]) -> str:
    """这一面是从哪份文件的哪一条拼来的，摆给用户看。"""
    src = ""
    for s in (it.get("source") or []):
        if isinstance(s, dict) and s.get("title"):
            src = str(s["title"])[:28]
            break
    bits = ["原文摘录" if it.get("auto") else "整理条目", it.get("dept") or "归口未写"]
    if src:
        bits.append(src)
    for name, pos in list((legs or {}).items())[:2]:
        bits.append(f"按「{name[:12]}」排第 {pos}")
    return " · ".join(bits)


@steped("assemble_decide")
def llm_face_decide(text: str, face: dict[str, Any],
                    pool: list[tuple[dict[str, Any], float, dict[str, Any]]]) -> dict[str, Any]:
    """这一面到底有没有条目真讲到了——模型只有否决权，正文一律用逐字原文。"""
    if not pool:
        return {"gate": "empty_pool"}
    menu = "\n".join(
        _pool_row(it, _item_full_text(it, 240), with_kind=False)
        for it, _sc, _legs in pool
    )
    prompt = pp.assemble("assemble_decide", {"q": text, "face": face.get("face", ""), "menu": menu})
    try:
        data = json.loads(ds_chat(
            [{"role": "system", "content": prompt},
             {"role": "user", "content": "只输出 JSON。"}],
            max_tokens=420, json_mode=True)) or {}
    except Exception as e:  # noqa: BLE001
        return {"gate": "error", "error": _llm_err_text(e)}
    if not isinstance(data, dict):
        return {"gate": "error", "error": "模型返回的不是 JSON"}
    verdict = str(data.get("verdict") or "").strip().lower()
    why = str(data.get("why") or "")[:160]
    if verdict != "accept":
        return {"gate": verdict or "no_evidence", "why": why}
    cid = str(data.get("id") or "")
    hit = next(((it, sc, legs) for it, sc, legs in pool if it["id"] == cid), None)
    if hit is None:
        return {"gate": "off_pool", "why": f"点了池外条目 {cid[:24]}"}
    it, _sc, legs = hit
    quote = str(data.get("quote") or "").strip()
    hay = _mn(_item_full_text(it, 4000) + " " + " ".join(
        str(one.get("quote") or "") for one in _ev_items((it.get("evidence") or {}).get("answer"))))
    if len(_mn(quote)) < ASSEMBLE_QUOTE_MIN or _mn(quote) not in hay:
        return {"gate": "quote_missing", "why": "抄的原文在条目里逐字找不到"}
    one = _best_quote((it.get("evidence") or {}).get("answer"), quote) or {}
    src = one.get("src", "")
    part = {
        "focus": "assembly",
        "label": face.get("face") or "另一面",
        "text": quote,
        "steps": [],
        "quotes": [{"quote": one.get("quote") or quote, "src": src, **src_label(src)}] if one or quote else [],
        "found": True,
        "from": it["id"],
        "from_title": _short_title(it.get("title") or ""),
        "meta": _face_meta_head(it, legs),
    }
    return {"gate": "accept", "part": part, "why": why}


def assemble_faces(text: str, parts: list[dict[str, Any]],
                   exclude_ids: set[str] | None = None,
                   status: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """缺的那几面：换官方说法重检一遍，逐面让模型否决，只把逐字原文拼进来。"""
    if not (_assemble_on("fill") or _assemble_on("rescue")):
        return []
    plan = llm_faces_plan(text, parts or [], status)
    if plan["gate"] != "ok":
        if status is not None:
            status.setdefault("assembly", {})["plan"] = plan["gate"]
        return []
    used = {str(p.get("from")) for p in (parts or []) if p.get("from")} | set(exclude_ids or ())
    out: list[dict[str, Any]] = []
    trace: dict[str, Any] = {}
    for face in plan["faces"]:
        pool = face_pool(face["phrases"], exclude_ids=used)
        d = llm_face_decide(text, face, pool)
        trace[face["face"]] = d.get("gate")
        if d["gate"] != "accept":
            continue
        part = d["part"]
        if _body_overlap(_part_body(part), (parts or []) + out):
            trace[face["face"]] = "duplicated"
            continue
        out.append(part)
        used.add(part["from"])
    if status is not None:
        status.setdefault("assembly", {}).update(trace)
    return out


def _assembled_answer(text: str, asm: list[dict[str, Any]], base: dict[str, Any],
                      score: int) -> dict[str, Any]:
    """拼装答案：条目摆第一面那条，置信封顶，并说清这是拼出来的。"""
    quotes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in asm:
        for q in p.get("quotes") or []:
            if q.get("quote") and q["quote"] not in seen:
                seen.add(q["quote"])
                quotes.append(q)
    base.update({
        "matched": True,
        "confidence": round(min(ASSEMBLE_CONF_CAP, max(score, 55) / 100), 2),
        "band": "mid",
        "item": public(ITEM_BY_ID.get(asm[0]["from"]) or {}),
        "answers": asm,
        "quotes": quotes,
        "focus": ["assembly"],
        "normalized": "、".join(p["label"] for p in asm),
        "suggestion": None,
        "next_actions": ["这几面是从不同文件里拼起来的，办之前按最新通知再确认一次"],
        "note": "这一问检索没能对上整件事的条目，下面是逐字摘自其他官方条目的相关面：" +
                "、".join(f"「{p['label']}」来自《{p['from_title']}》" for p in asm),
    })
    return base


def _unmatched_name(q: str) -> str:
    """问句里像产品/系统名、词表却不认识的那截字母；没有就返回空。

    只认拉丁片段：中文简称本来就要靠字面和词表对，对不上说明它不是名字。
    """
    ql = _mn(q)
    frags = [m.group(0) for m in re.finditer(r"(?<![0-9a-z])[a-z][a-z0-9]{1,15}(?![0-9a-z])", ql)]
    if not frags:
        return ""
    qp = question_proper(ql)
    if not qp:
        return max(frags, key=len)
    unknown = [f for f in frags if not any(f == t or (len(f) >= 3 and len(t) >= 3 and (f in t or t in f))
                                          for t in qp)]
    return max(unknown, key=len) if unknown else ""


_PROPER_MENU: list[str] | None = None


def proper_name_menu() -> list[str]:
    """词表里确有分量的专名（全量），摆给模型做「用户这个叫法对应库里哪个名字」。"""
    global _PROPER_MENU
    if _PROPER_MENU is None:
        pi = proper_index()
        _PROPER_MENU = sorted(t for t, ids in pi["postings"].items()
                              if len(ids) >= PROPER_MAP_MIN_POSTINGS)
    return _PROPER_MENU


def _name_gloss(item: dict[str, Any], name: str) -> str:
    """条目原文里点到这个名字的那一小段，摆给模型看它到底属于哪家。"""
    hay = f"{item.get('title') or ''} {item.get('answer') or ''}"
    m = _name_re(name).search(hay)
    if not m:
        return (item.get("title") or "").strip()[:PROPER_MAP_GLOSS]
    return hay[max(0, m.start() - 6):m.start() + PROPER_MAP_GLOSS].strip()


def proper_menu_for(ranked: list[tuple[dict[str, Any], int]]) -> list[tuple[str, str]]:
    """这次的候选条目里确实写过的名字：菜单收窄到本问，不摊开整张词表。

    摊开 293 个名字，模型会照拼写凑——「ps」对上「wps」，端进 8 条 WPS 条目，
    答出 WPS 登录，比不映射更糟（2026-11-05 实测）。收窄加出处，是按实际归属判。
    """
    pi = proper_index()
    scope = ranked[:PROPER_MAP_SCOPE]
    freq: dict[str, int] = {}
    gloss: dict[str, str] = {}
    for it, _sc in scope:
        for t in pi["items"].get(it.get("id") or "", ()):
            if len(pi["postings"].get(t, ())) < PROPER_MAP_MIN_POSTINGS:
                continue
            freq[t] = freq.get(t, 0) + 1
            if t not in gloss:
                g = _name_gloss(it, t)
                if g:
                    gloss[t] = g
    ordered = sorted(freq, key=lambda t: (-freq[t], -len(pi["postings"][t]), t))
    return [(t, gloss.get(t, "")) for t in ordered[:PROPER_MAP_MAX]]


@steped("proper_map")
def llm_proper_map(text: str, said: str,
                   menu: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    """把词表外的叫法对到词表里已有的名字上（ps → adobe）。

    模型只能从菜单里选，报出来的名字必须字面在菜单里，对不上就当没有这件事；
    它填 null 也不硬凑——「问的东西库里没有」本来就是要说出口的。
    """
    pairs = menu if menu is not None else [(n, "") for n in proper_name_menu()]
    names = {n for n, _g in pairs}
    if not names:
        return {"name": "", "why": "这次相关的条目里没写过别的名字"}
    listed = "、".join(f"{n}（{g}）" if g else n for n, g in pairs)
    try:
        data = json.loads(ds_chat(
            [{"role": "system", "content": "你在帮校园办事问答认名字，只做映射不编事实。"},
             {"role": "user", "content": PROPER_MAP_PROMPT.format(said=said, names=listed)}],
            max_tokens=120, json_mode=True)) or {}
    except Exception as e:  # noqa: BLE001
        return {"name": "", "error": _llm_err_text(e)}
    if not isinstance(data, dict):
        return {"name": "", "error": "模型返回的不是 JSON"}
    why = str(data.get("why") or "").strip()[:120]
    name = str(data.get("name") or "").strip().lower()
    if name and name not in names:
        return {"name": "", "why": why, "rejected": name}
    return {"name": name, "why": why}


def proper_map_extra(ranked: list[tuple[dict[str, Any], int]], name: str,
                     have_ids: set[str], limit: int = PROPER_MAP_ADD) -> list[tuple[dict[str, Any], int]]:
    """条目自己写了这个名字、又没进过这次候选池的那些，按规则原序端进去。"""
    ids = proper_index()["postings"].get(name) or set()
    if not ids or not name:
        return []
    return [(it, sc) for it, sc in ranked
            if it["id"] in ids and it["id"] not in have_ids and not it.get("archive_only")][:limit]


PROPER_FILL_ADD = 8     # 池子里一条都没点名时，最多补几条进去
PROPER_FILL_SWAP = 4    # 池子里有带名但都不及格时，最多换掉池尾几条（与改写腿同一个量级）


def proper_fill_candidates(q: str, ranked: list[tuple[dict[str, Any], int]],
                           pool: list[tuple[dict[str, Any], int]],
                           limit: int = PROPER_FILL_ADD) -> list[tuple[dict[str, Any], int]]:
    """问句点了产品名，候选池里却没一条带它——把带这个名字的条目补进池尾给模型看。

    闸门只会把不带名的条目压到 54，不会给带名的加分；打分又不看正文与定位器，
    所以「photoshop怎么安装」时那些 Adobe 安装条目是 0 分、排不进规则前八，
    模型对着六条 [Sheet1] 杂表行只能判未收录（2026-11-05 实测：把同一条塞进池子，
    模型立刻给 70 分并答对）。只补候选，打分、75/60/10 门槛与复核一行不动。
    """
    qp = question_proper(q)
    # 「池里有带名条目」不等于「这一面有人答」：入口清单、卸载提醒这类条目名字对得上、
    # 规则分却是 0，模型拿着它们只会判未收录（photoshop 怎么安装 2026-11-09 实测 3/3 拒答）。
    # 只有带名、而且规则腿真给了及格分的条目，才算这一面已经有人答，不必再补。
    if not qp or any(names_product(it, qp) and sc >= MATCH_THRESHOLD for it, sc in pool):
        return []
    named: set[str] = set()
    for t, ids in proper_index()["postings"].items():
        if any(t == w or (len(t) >= 3 and len(w) >= 3 and (t in w or w in t)) for w in qp):
            named |= ids
    if not named:
        return []
    have = {it["id"] for it, _sc in pool}
    # 池子常年是满的 14 条：补面不是往后追加，是替换池尾（调用方按这个数换）。
    # 尾巴本来就摆着 0 分的无关条目，换掉不违背扩池实验的结论。
    limit = min(limit, PROPER_FILL_SWAP)
    if limit <= 0:
        return []
    # 名字本身不参与「像不像在问这件事」的比较：带名的条目当然都带名，
    # 把名字挖掉剩下的那截（「怎么安装」「怎么下载」）才是排序依据。
    hole = norm(q)
    for w in sorted(qp, key=len, reverse=True):
        hole = hole.replace(w, "\x00")
    qb = {g for seg in hole.split("\x00") for g in bigrams(seg)}
    # 问句里点的是哪个动作：装/下/激活…。带名条目里一堆目录页和泛化入口，
    # 光按二字组重合排会把「（四）如何安装？……12」这种目录行排进来，
    # 模型挑中它就答成「安装后点击登录」。动作词进标题、正文像步骤的，往前排。
    act = next((a for a in ("安装", "下载", "激活", "登录", "卸载", "重装") if a in hole), "")
    order = {it["id"]: k for k, (it, _sc) in enumerate(ranked)}
    cand: list[tuple[int, int, dict[str, Any]]] = []
    for iid in named:
        it = ITEM_BY_ID.get(iid)
        if it is None or iid in have or it.get("archive_only"):
            continue
        title = norm(it.get("title") or "")
        body = norm(str(it.get("answer") or "")[:200])
        hay = title + " " + body
        cover = len(qb & bigrams(hay))
        exact = 2 if act and any(f"{w}{act}" in title for w in ("如何", "怎么", "怎样")) else 0
        proc = min(2, sum(1 for w in ("方法", "步骤", "点击", "下载", "打开", "输入") if w in hay))
        # 目录页：正文基本是页码和省略号，答不了一件事
        toc = 1 if (body.count("…") >= 3 or (body and sum(
            1 for ch in body if ch.isdigit() or ch == ".") / len(body) > 0.3)) else 0
        cand.append((-(cover + exact + proc - 3 * toc), order.get(iid, len(ranked)), it))
    cand.sort()
    return [(it, 0) for _q, _rank, it in cand[:limit]]


NUM_ONLY = re.compile(r"^\s*(\d{1,3})\s*(?:号楼|号|楼|教)?\s*[。.、,，!！?？]*\s*$")


def _poi_by_number(n: str) -> dict[str, Any] | None:
    """纯楼号输入落到校园地图的地点：1→立德楼（1教）、48→博学楼（48教）。"""
    want = {f"{n}号楼", f"{n}号", f"{n}楼", f"{n}教"}
    prefix = f"{n}号楼"
    for p in campus_data().get("pois") or []:
        for raw in [p.get("name", ""), *(p.get("aliases") or [])]:
            name = norm(raw)
            if name in want or name.startswith(prefix):
                return p
    return None


def _louming_line(n: str) -> tuple[dict[str, Any], int] | None:
    """校园地图 POI 没有的楼号，回退到楼宇名称对照表。"""
    item = ITEM_BY_ID.get("campus-louming")
    if not item:
        return None
    pats = (
        re.compile(rf"(?:=|＝)[^=＝]{{0,4}}{n}号楼"),
        re.compile(rf"（{n}号楼）"),
        re.compile(rf"(?:在|位于){n}号楼"),
        re.compile(rf"(?:=|＝)\s*{n}教"),
    )
    for idx, entry in enumerate(item.get("answer_lines") or []):
        if not isinstance(entry, dict):
            continue
        if any(p.search(entry.get("line", "")) for p in pats):
            return item, idx
    return None


def _known_building_numbers() -> list[int]:
    cands: set[int] = set()
    for p in campus_data().get("pois") or []:
        for raw in [p.get("name", ""), *(p.get("aliases") or [])]:
            m = re.fullmatch(r"(\d{1,3})号楼", norm(raw))
            if m:
                cands.add(int(m.group(1)))
    for entry in (ITEM_BY_ID.get("campus-louming") or {}).get("answer_lines") or []:
        for m in re.finditer(r"(\d{1,3})号楼", entry.get("line", "")):
            cands.add(int(m.group(1)))
    return sorted(x for x in cands
                  if _poi_by_number(str(x)) is not None or _louming_line(str(x)) is not None)


def number_answer(text: str, n: str, llm_on: bool) -> dict[str, Any] | None:
    poi = _poi_by_number(n)
    if poi is not None:
        hit = _place_payload(poi)
        parts = place_parts([hit])
        quotes = [q for p in parts for q in p["quotes"]]
        return {
            "matched": True,
            "query": text,
            "normalized": f"校园地点 · {hit['name']}",
            "confidence": 0.95,
            "band": "high",
            "ambiguous": False,
            "item": public(ITEM_BY_ID.get("campus-louming") or place_item([hit])),
            "answers": parts,
            "focus": ["location"],
            "hold": False,
            "followups": [],
            "known": {},
            "quotes": quotes,
            "missing": [],
            "note": None,
            "map": hit,
            **sensitivity(text),
            "router_llm": llm_on,
            "rule_unsure": False,
        }
    line_hit = _louming_line(n)
    if line_hit is not None:
        item, idx = line_hit
        entry = item["answer_lines"][idx]
        line = entry.get("line", "")
        one = _best_quote(item.get("evidence") or {}, line)
        qs = ([{"quote": one.get("quote", ""), "src": one.get("src", ""),
                **src_label(one.get("src", ""))}] if one else [])
        parts = [{"focus": "location", "label": "位置", "text": line,
                  "found": True, "quotes": qs}]
        return {
            "matched": True,
            "query": text,
            "normalized": f"校园地点 · {entry.get('name') or n + '号楼'}",
            "confidence": 0.9,
            "band": "high",
            "ambiguous": False,
            "item": public(item),
            "answers": parts,
            "focus": ["location"],
            "hold": False,
            "followups": [],
            "known": {},
            "quotes": qs,
            "missing": [],
            "note": None,
            "map": None,
            **sensitivity(text),
            "router_llm": llm_on,
            "rule_unsure": False,
        }
    return None


_TOPIC_FACET = re.compile(
    r"报名|费用|学费|收费|免费|多少钱|时间|什么时候|何时|几月|流程|条件|要求|材料|地点|地址|电话|联系|怎么|如何|在哪|"
    r"申请|办理|补办|查询|预约|截止|清单|步骤|多久|几年|难|政策|规定|名额|比例|资格|绩点|成绩|考试|面试|吗|呢"
)


def _menu_label(title: str) -> str:
    """菜单里的短标签；点击时仍用完整标题当问句。"""
    t = core_title(re.split(r"\s*·\s*", title or "")[0].strip())
    return t if len(t) <= 36 else t[:35] + "…"


# 自动摘录的卡片标题最多显示这么多个字的正文，超过就收在最后一个完整分句上
_CARD_TITLE_CAP = 32


def _card_title(item: dict[str, Any]) -> str:
    """自动摘录的卡片，标题是切短了的原文句子，直接给用户看像是页面坏了。

    换成「来源文件 · 完整分句…」：来源摆前面，句子收在最后一个逗号上，没闭合的括号
    连着里面半截话一起去掉。这只是显示层的写法，items.json 里的 title 一个字不动。
    """
    title = str(item.get("title") or "")
    if not item.get("auto") or " · " not in title:
        return title
    sent, _, src = title.rpartition(" · ")
    sent, src = sent.strip(), src.strip()
    if not sent or not src:
        return title
    cut = False
    for op, cl in (("（", "）"), ("(", ")")):
        if sent.count(op) > sent.count(cl):
            sent = sent[:sent.rfind(op)].rstrip("，,、；; ")
            cut = True
    if len(sent) > _CARD_TITLE_CAP:
        head = sent[:_CARD_TITLE_CAP]
        i = max(head.rfind("，"), head.rfind("；"))
        sent = (head[:i] if i >= 8 else head).rstrip("，,、；; ")
        cut = True
    # 摘录时切在半句话上的，尾巴上会留个逗号或分号（「保卫部审批备案；」），
    # 摆到界面上像没写完，去掉并补省略号说明后面还有
    trimmed = sent.rstrip("，,、；;：: ")
    if trimmed != sent:
        sent, cut = trimmed, True
    if not sent:
        return title
    return f"{src} · {sent}{'…' if cut else ''}"


def _card_label(item: dict[str, Any]) -> str:
    """联想列表里的短标签：自动摘录换成「来源文件 · 短句」，人工条目照旧。"""
    if not item.get("auto"):
        return _menu_label(item.get("title", ""))
    t = _card_title(item)
    return t if len(t) <= 40 else t[:39] + "…"


def _menu_dept(item: dict[str, Any]) -> str:
    d = (item.get("dept") or "").strip()
    if d and d != "中国传媒大学":
        return d
    srcs = item.get("source") or []
    if isinstance(srcs, (str, dict)):
        srcs = [srcs]
    if srcs:
        first = srcs[0]
        raw = first.get("title") if isinstance(first, dict) else src_label(str(first)).get("label")
        t = re.split(r"\s*·\s*", str(raw or ""))[0].strip()
        return t[:24] + ("…" if len(t) > 24 else "")
    return d


def _menu_group_key(item: dict[str, Any], label: str) -> str:
    """同一份文件里连着编号排下来的条目，在菜单里只算一条。

    长汇编按自然段切条目，「空调使用注意事项」一个小问能刷出七条选项，
    用户看到的是同一份文件占满屏幕。这里只并自动摘录的条目，人工整理的事项条目不动。
    """
    if not item.get("auto"):
        return ""
    srcs = item.get("source") or []
    if isinstance(srcs, (str, dict)):
        srcs = [srcs]
    if not srcs:
        return ""
    first = srcs[0]
    src = ""
    if isinstance(first, dict):
        src = str(first.get("slug") or first.get("title") or first.get("url") or "")
    else:
        raw = str(first or "")
        src = src_label(raw).get("label") or raw
    if not src:
        return ""
    seg = _mn(re.split(r"[｜:：]", label)[0])
    return f"{src}\u0001{seg if len(seg) >= 6 else _mn(label)[:12]}"


def _wzy_options() -> list[dict[str, Any]] | None:
    overviews = [i for i in ITEMS if i["id"].startswith("wzy26-") and i.get("pdf")]
    general = ITEM_BY_ID.get("doc-20260724-c6479a272951")
    if not overviews or general is None:
        return None
    opts = [{"id": general["id"], "title": general["title"],
             "label": "2026 年秋季微专业招生总览",
             "dept": "11 份招生简章 PDF · 身份验证二维码"}]
    for it in overviews:
        opts.append({"id": it["id"], "title": it["title"],
                     "label": it["title"].replace("2026年秋季", "").replace("微专业招生简章", ""),
                     "dept": f"{it.get('dept') or ''} · 简章 PDF · 报名二维码"})
    return opts


_RELATED_TAIL = re.compile(
    r"(?:怎么|如何|可以)?(?:报名|办理|申请|补办|查询|预约|缴费|充值|挂失|解挂|开通|使用|续期|延期|"
    r"丢了|没了|不见了|掉了|遗失|怎么办|怎么弄|流程|条件|要求|材料|时间|地点|费用|收费|免费|多少钱|在哪|多久|截止|"
    r"电话|联系方式|政策|规定|怎么.{1,2})[？?。.!！]*(?:吗|呢|啊|呀)?$"
)


_RELATED_BAD_START = re.compile(r"^(?:此处|如图|如下图|输入|点击|设置|选择|打开|进入|登录|填|勾选|确认|注意|例如|比如|其中|同时|如果)")
_OCR_MIX = re.compile(r"[\u4e00-\u9fff]\d[\u4e00-\u9fff]")


def _related_title_ok(title: str) -> bool:
    """自动摘录的标题是原文切句，太长、带省略号、串字的一律不摆进联想。"""
    t = (title or "").strip()
    return (len(t) <= 48 and "…" not in t and not _OCR_MIX.search(t)
            and not _RELATED_BAD_START.search(t))


_WZY_FACET_ORDER = ["audience", "quota", "duration", "mode", "cert", "enroll",
                    "contact", "fee", "courses", "intro", "goal", "req"]


def _wzy_siblings(top: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    """问某个微专业时，把它自己的招生对象、学制、学费、课程等一并摆出来。"""
    tid = top.get("id", "")
    prog = ""
    for it in ITEMS:
        oid = it.get("id", "")
        if (it.get("pdf") and oid.startswith("wzy26-")
                and (tid == oid or tid.startswith(oid + "-")) and len(oid) > len(prog)):
            prog = oid
    if not prog:
        return []
    if prog in _WZY_SIBS:
        return _WZY_SIBS[prog]
    order = {k: i for i, k in enumerate(_WZY_FACET_ORDER)}
    sib = [it for it in ITEMS if it["id"].startswith(prog + "-") and it["id"] != tid]

    def key(it: dict[str, Any]) -> tuple[int, str]:
        tail = it["id"][len(prog) + 1:]
        return (order.get(tail.split("-")[0], 50), tail)

    sib.sort(key=key)
    full = (ITEM_BY_ID.get(prog, {}).get("title") or "").replace("2026年秋季", "").replace("招生简章", "").strip()
    out = []
    for it in sib[:limit]:
        t = core_title(it["title"])
        short = t[len(full):].strip(" ·") if full and t.startswith(full) else _menu_label(it["title"])
        out.append({"id": it["id"], "title": it["title"],
                    "label": short or "招生简章总览",
                    "dept": _menu_dept(it), "hint": (it.get("aliases") or [""])[0]})
    _WZY_SIBS[prog] = out
    return out


def _related_items(text: str, top: dict[str, Any],
                   manual_limit: int = 6, auto_limit: int = 8) -> list[dict[str, Any]]:
    """短问句答完后，把同词的其他事项一并摆出来：人工条目优先，再给原文摘录。"""
    sib = _wzy_siblings(top)
    if sib:
        return sib
    token = re.sub(r"[\s？?。.!！，,、]+$", "", (text or "").strip())
    tn = _mn(token)
    # 「微专业怎么报名」「校园卡丢了怎么办」一层层剥掉问的那一面，剩下的名词当联想词；
    # 原句也留着，标题本身就是完整问法时仍能接上
    head = tn
    for _ in range(3):
        nxt = _RELATED_TAIL.sub("", head).strip()
        if nxt == head or len(nxt) < 2:
            break
        head = nxt
    tokens = [t for t in dict.fromkeys([head, tn]) if 2 <= len(t) <= 10]
    if not tokens:
        return []
    global _RELATED_ROWS
    if _RELATED_ROWS is None:
        _RELATED_ROWS = [
            (it, _mn(it["title"]), _mn(" ".join(it.get("aliases") or [])),
             _mn(" ".join(it.get("keywords") or [])), bool(it.get("auto")))
            for it in ITEMS
        ]
    picked: list[tuple[dict[str, Any], int]] = []
    for it, tt, aliases, kws, is_auto in _RELATED_ROWS:
        if it["id"] == top["id"] or it.get("archive_only"):
            continue
        if is_auto and not _related_title_ok(it["title"]):
            continue
        hit = next((t for t in tokens if t in tt), None)
        if hit:
            sc = 3 if tt.startswith(hit) else 2
        elif any(t in aliases or t in kws for t in tokens):
            if it.get("auto"):
                continue   # 自动摘录只看标题：关键词命中的条款离题太远
            sc = 1
        else:
            continue
        if not it.get("auto"):
            sc += 4
        picked.append((it, sc))
    picked.sort(key=lambda r: (-r[1], len(r[0]["title"])))
    out: list[dict[str, Any]] = []
    seen = {norm(_menu_label(top["title"]))}
    n_manual = n_auto = 0
    for it, _ in picked:
        key = norm(_menu_label(it["title"]))   # 同名的原文摘录只留一条
        if key in seen:
            continue
        if it.get("auto"):
            if n_auto >= auto_limit:
                continue
            n_auto += 1
        else:
            if n_manual >= manual_limit:
                continue
            n_manual += 1
        seen.add(key)
        out.append({"id": it["id"], "title": it["title"], "label": _card_label(it),
                    "dept": _menu_dept(it), "hint": (it.get("aliases") or [""])[0]})
        seen.add(norm(core_title(it["title"])))   # 同名的原文摘录只留一条
    return out


# 标题里用斜杠或顿号并列了好几件事，才算「宽泛父条目」：
# 「奖学金评定（国家 / 国家励志 / 校励志 / 优秀本科生）」是，
# 「电子学生交通卡申领」不是——后者本来就只讲一件事，不该被抢
_BROAD_PARENT = re.compile(r"[/／、]")
_QUAL_MIN, _QUAL_MAX = 3, 12

# 问句去掉限定词之后剩下那一面的口语说法，和卡片正文里的官方写法对不上，按同一件事算。
# 只用在挑子条目这一步。_ASK_VARIANT 那张表 _covered 也在用，动它会牵连「没答到」的判断，不碰。
_CHILD_FACET = {
    "多少钱": ("元", "金额", "标准", "费用", "收费", "免费"),
    "钱": ("元", "金额", "标准", "费用", "收费", "退还", "发放"),
    "条件": ("条件", "资格", "要求", "须具备"),
    "材料": ("材料", "证明", "申请书", "表格"),
    "时间": ("时间", "日期", "截止", "学期", "学年"),
    "地点": ("地点", "地址", "楼", "室", "窗口"),
    "在哪": ("位于", "地址", "楼", "室", "窗口"),
}


def _title_qualifier(title: str, qn: str) -> str:
    """标题开头这一段正好是问句里的限定词，就把它取出来，取最长的那一段。

    「国家励志奖学金怎么申请」对上子条目「国家励志奖学金按学年申请和评审」，
    拿到的限定词是「国家励志奖学金」，不是「国家」。
    """
    tn = _mn(core_title(title))
    for n in range(min(len(tn), _QUAL_MAX), _QUAL_MIN - 1, -1):
        p = tn[:n]
        if p and p in qn:
            return p
    return ""


def _child_facet(cand: dict[str, Any], rest: str) -> tuple[int, int]:
    """问句里剩下那一面，这张卡片答没答上。返回（剩下几个实词，答上几个）。

    「国家励志奖学金多少钱」去掉限定词剩「多少钱」，三张卡片原始分都是 96，
    只有写「5000元」那张答得上这一面，就提它。
    """
    hay = _mn(f"{cand.get('title') or ''} {cand.get('answer') or ''}")
    for s in cand.get("steps") or []:
        if isinstance(s, dict):
            hay += " " + _mn(" ".join(str(s.get(k) or "") for k in ("what", "where", "when")))
        else:
            hay += " " + _mn(str(s))
    terms = list(dict.fromkeys(
        c for c in _ASK_WORDS.sub(" ", rest).split() if len(c) >= 2))
    hits = sum(1 for t in terms if t in hay)
    asked = len(terms)
    # 用户嘴里的「多少钱」和文件里的「每生每学年5000元」对不上，按同一件事算。
    # 这类词也要算进「问了几面」：「多少钱」剥掉疑问词只剩一个「钱」字，
    # 不算进去就会被当成没问具体哪一面，白白提了第一张卡片。
    for k, vs in _CHILD_FACET.items():
        if k in rest:
            asked += 1
            if any(v in hay for v in vs):
                hits += 1
    return asked, hits


def _promoted_child(text: str, top: dict[str, Any]) -> tuple[dict[str, Any], int] | None:
    """问句点了限定词、top 却是并列好几件事的宽泛父条目时，找出该提上来的子条目。

    相关事项那一步已经把对的卡片排在前面了，只是分数被父条目压住。三道门槛：
    一、限定词得是子条目标题的开头，而父条目的完整标题里没有原样写过它。
       「报到证怎么办」的父条目就叫「毕业生户口与档案（报到证、户档暂留）」，
       它本来就在讲报到证，不该被「报到证遗失补办」抢走。
    二、子条目按没被降权的原始分算，得真的高过父条目。降权才是它被压住的原因，
       原始分还输就说明父条目更对题：「研究生国家奖学金怎么申请」子条目 88 对父条目 92，不换。
    三、问句除了限定词还点了具体一面时，子条目得答得上这一面，答不上就宁可留在父条目。
       「国家励志奖学金条件」三张卡片都没写条件，父条目反而四种奖学金都讲到了。
    一条都不改数据，只改这一次拿哪条作答。
    """
    qn = _mn(text or "")
    if not qn or not _BROAD_PARENT.search(str(top.get("title") or "")):
        return None
    # 比的是完整标题：core_title 会把「（国家 / 国家励志 / …）」整段括注削掉，
    # 削掉之后就看不出父条目已经写过这个限定词了
    pfull = _mn(str(top.get("title") or ""))
    qnorm = norm(text or "")
    parent_raw = score_item(qnorm, top)
    best: tuple[dict[str, Any], int] | None = None
    best_hit = 0
    for c in _related_items(text, top):
        cid = c.get("id")
        if not cid or cid == top.get("id"):
            continue
        qual = _title_qualifier(str(c.get("title") or ""), qn)
        if not qual or qual in pfull:
            continue        # 父条目自己就写了这个限定词，不用换
        cand = ITEM_BY_ID.get(cid)
        if cand is None or cand.get("archive_only"):
            continue
        raw = score_item(qnorm, cand)
        if raw < MATCH_THRESHOLD or raw <= parent_raw:
            continue        # 光标题像不算，子条目本来就该赢才提
        n_terms, hits = _child_facet(cand, qn.replace(qual, " ", 1))
        if n_terms == 0:
            return cand, raw            # 只点了限定词，没问具体哪一面，排第一那张就行
        if hits > best_hit:
            best, best_hit = (cand, raw), hits
    return best


_TOPIC_MENUS: list[dict[str, Any]] | None = None


def _topic_menus() -> list[dict[str, Any]]:
    """topic-menus.json：用户勾选过的「单词 → 固定选项」清单。"""
    global _TOPIC_MENUS
    if _TOPIC_MENUS is None:
        try:
            raw = json.loads((ROOT / "topic-menus.json").read_text(encoding="utf-8"))
            _TOPIC_MENUS = raw.get("menus") or []
        except (OSError, ValueError):
            _TOPIC_MENUS = []
    return _TOPIC_MENUS


def _curated_topic_menu(text: str) -> dict[str, Any] | None:
    """人工勾选的选项菜单：单词命中就摊开固定选项，不再扫出上百条关键词噪声。"""
    token = re.sub(r"[\s？?。.!！，,、]+$", "", (text or "").strip()).strip()
    token = re.sub(r"(吗|呢|啊|吧|呀)$", "", token).strip()
    tn = _mn(token)
    if not tn:
        return None
    for menu in _topic_menus():
        if tn not in {_mn(t) for t in (menu.get("triggers") or [])}:
            continue
        opts: list[dict[str, Any]] = []
        first: dict[str, Any] | None = None
        for row in menu.get("options") or []:
            it = ITEM_BY_ID.get(row.get("item") or "")
            if not it:
                continue
            first = first or it
            opts.append({
                "id": it["id"],
                "title": row.get("ask") or it["title"],
                "label": row.get("label") or _menu_label(it["title"]),
                "dept": row.get("dept") or _menu_dept(it),
            })
        if len(opts) < 2 or first is None:
            continue
        # 登记了 default 的菜单不反问：先按那一条直答，其余选项交给答案下面的相关事项。
        # 只有 topic-menus.json 里点过 default 的词才走这条路，别的菜单照旧摊选项。
        default = ITEM_BY_ID.get(menu.get("default") or "")
        if default is not None and not any(o["id"] == default["id"] for o in opts):
            default = None
        if default is not None:
            return {
                "matched": True,
                "query": text,
                "normalized": None,
                "confidence": 0.9,
                "band": "high",
                "ambiguous": False,
                "item": public(default),
                "answers": [],
                "hold": False,
                "followups": [],
                "disambiguate": [o for o in opts if o["id"] != default["id"]],
                "clarify": None,
                "focus": [],
                "quotes": [],
                "map": None,
                **sensitivity(text),
                "router_llm": False,
                "rule_unsure": False,
                "_default_pick": default["id"],
            }
        return {
            "matched": True,
            "query": text,
            "normalized": f"{menu.get('name') or token} · {len(opts)} 个选项",
            "confidence": 0.55,
            "band": "low",
            "ambiguous": True,
            "item": public(first),
            "answers": [],
            "hold": True,
            "followups": [],
            "disambiguate": opts,
            "clarify": menu.get("clarify") or f"「{token}」有下面几项，先点一个：",
            "focus": [],
            "quotes": [],
            "map": None,
            **sensitivity(text),
            "router_llm": False,
            "rule_unsure": False,
        }
    return None


def _topic_menu(text: str) -> dict[str, Any] | None:
    """单个词输入：把相关的条目全摊成选项，先让用户挑，不硬猜一个答案。"""
    token = re.sub(r"[\s？?。.!！，,、]+$", "", (text or "").strip()).strip()
    tn = _mn(token)
    if not (2 <= len(tn) <= 10) or re.search(r"\s", token):
        return None
    if PLACE_ASK.search(token) or re.search(r"^[0-9]+(号楼|号|楼|教)?$", token):
        return None

    curated = _curated_topic_menu(token)
    if curated:
        return curated

    if tn == "微专业":
        opts = _wzy_options()
        if opts:
            return {
                "matched": True,
                "query": text,
                "normalized": "微专业 · 11 个专业与总览",
                "confidence": 0.6,
                "band": "low",
                "ambiguous": True,
                "item": public(ITEM_BY_ID["doc-20260724-c6479a272951"]),
                "answers": [],
                "hold": True,
                "followups": [],
                "disambiguate": opts,
                "clarify": "「微专业」相关的都在这儿：先看总览，或直接点一个专业。",
                "focus": [],
                "quotes": [],
                "map": None,
                **sensitivity(text),
                "router_llm": False,
                "rule_unsure": False,
            }
        return None

    if _TOPIC_FACET.search(tn):
        return None

    rows: list[tuple[dict[str, Any], int]] = []
    strong = False
    for it in ITEMS:
        if it.get("archive_only"):
            continue
        aliases = " ".join(it.get("aliases") or [])
        hay = _mn(" ".join([it["title"], aliases, " ".join(it.get("keywords") or [])]))
        if tn not in hay:
            continue
        tt = _mn(it["title"])
        if not it.get("auto") and (
            tt == tn
            or tn in {_mn(a) for a in (it.get("aliases") or [])}
            or (len(tn) >= 4 and tt.startswith(tn))
        ):
            strong = True   # 已有专门条目能直接答，别再摊菜单
        if tt == tn:
            sc = 8
        elif tt.startswith(tn):
            sc = 7
        elif tn in tt:
            sc = 5
        elif tn in _mn(aliases):
            sc = 4
        elif tn in _mn(" ".join(it.get("keywords") or [])):
            sc = 3
        else:
            sc = 2
        if not it.get("auto"):
            sc += 2   # 人工整理的事项排在自动摘录的条款前面
        rows.append((it, sc))
    if strong:
        return None
    if len(rows) < 3:
        return None
    rows.sort(key=lambda x: (-x[1], bool(x[0].get("auto")), len(x[0]["title"])))
    rows = distinct_rows(rows)
    opts: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    seen_src: set[str] = set()
    if tn in _place_names():
        # 地点类单词：位置排第一，后面接所有相关事项，点「在哪」才走地点卡
        opts.append({"id": "", "title": f"{token}在哪",
                     "label": f"{token} · 位置与到达", "dept": "校园地点 · 地图定位"})
        seen.add((norm(token), norm("校园地点")))
    for it, _ in rows:
        label = _menu_label(it["title"])
        dept = _menu_dept(it)
        key = (norm(label), norm(dept))
        if key in seen:
            continue
        gkey = _menu_group_key(it, label)
        if gkey and gkey in seen_src:
            continue
        seen.add(key)
        if gkey:
            seen_src.add(gkey)
        opts.append({"id": it["id"], "title": it["title"], "label": label, "dept": dept})
        if len(opts) >= 120:
            break
    return {
        "matched": True,
        "query": text,
        "normalized": f"{token} · {len(opts)} 条相关事项",
        "confidence": 0.45,
        "band": "low",
        "ambiguous": True,
        "item": public(rows[0][0]),
        "answers": [],
        "hold": True,
        "followups": [],
        "disambiguate": opts,
        "clarify": (f"「{token}」相关的都在这儿：先看位置，或点一条具体事项。"
                    if tn in _place_names() and len(opts) > 1
                    else f"「{token}」相关的条目有 {len(opts)} 条，先点一个看原文："),
        "focus": [],
        "quotes": [],
        "map": None,
        **sensitivity(text),
        "router_llm": False,
        "rule_unsure": False,
        "_rows": rows,
        "_place_menu": tn in _place_names(),
    }


MENU_PICK_MIN = 60   # 模型从单词菜单里定下一条的地板，和规则没到阈值时接住模型的分一致


def _new_model_route() -> dict[str, Any]:
    return {
        "asked": False, "gate": None, "error": None, "pool": 0,
        "changed": False, "confirmed": False, "score": 0, "why": "",
        "facets": [], "rewrites": [], "vector_error": None,
        "pool2": 0, "rescue": None,
    }


def _menu_llm_pick(text: str, rows: list[tuple[dict[str, Any], int]],
                   history: list[dict[str, str]] | None,
                   status: dict[str, Any]) -> tuple[dict[str, Any], int, list[str]] | None:
    """单词菜单先交给模型裁决一次：定得下来就直答，定不下来才摊选项。

    菜单在评分和模型裁决之前就 return 了，模型原本看不见这些候选。
    候选优先按来源页收拢再送出去：同一页的三四段摘录一起给，等于让模型在
    一页纸的段落里做选择题，答不出用户要的是哪件事。整份菜单只有一页时
    收拢后只剩一条，那就照原样给，让模型挑这一页里最贴的那段。
    """
    pool: list[tuple[dict[str, Any], int]] = []
    seen_page: set[str] = set()
    for it, sc in rows:
        page = _menu_dept(it)
        if page in seen_page:
            continue
        seen_page.add(page)
        pool.append((it, sc))
        if len(pool) >= 12:
            break
    if len(pool) < 2:
        pool = rows[:12]
    if len(pool) < 2:
        return None
    status["pool"] = len(pool)
    rr, _rewrites = llm_rerank(text, pool, history, status=status, menu_mode=True)
    if rr is None:
        status["gate"] = "menu_error"
        return None
    status["asked"] = True
    best = rr["item"]
    if best is None:
        status["gate"] = "menu_declined"
        return None
    status["score"] = rr["score"]
    status["why"] = rr.get("why") or ""
    if rr["score"] < MENU_PICK_MIN:
        status["gate"] = "menu_low"
        return None
    status["gate"] = "menu_pick"
    return best, rr["score"], (rr.get("facets") or [])


def _transfer_clarify(text: str, tp: dict[str, Any] | None,
                      map_hit: dict[str, Any] | None) -> dict[str, Any] | None:
    """只说「转专业」没点学院：先反问转去哪个学院，16 个有接收计划的学院直接点。"""
    if tp or not _TRANSFER_ASK.search(text):
        return None
    if _TRANSFER_FACET.search(text):
        return None
    if not (len(text.strip()) <= 14 or _TRANSFER_CONSULT.search(text)):
        return None
    named_colleges, named_majors = _find_entities(text)
    if named_colleges or named_majors:
        return None
    seen_college: dict[str, dict[str, Any]] = {}
    for c in _transfer_entities()["colleges"]:
        seen_college.setdefault(c["college"], c)
    opts = [
        {"id": "", "title": f"转专业到{c['display']}",
         "dept": "2025 秋接收计划" if c["has_plan"] else "暂无接收计划",
         "hint": c["college"]}
        for c in sorted(seen_college.values(), key=lambda c: (not c["has_plan"], c["college"]))
    ]
    return {
        "matched": True,
        "query": text,
        "normalized": "转专业 · 等你说转去哪个学院",
        "confidence": 0.5,
        "band": "low",
        "ambiguous": True,
        "item": public(next(i for i in ITEMS if i["id"] == "zhuanzhuanye")),
        "answers": [],
        "hold": True,
        "followups": [],
        "disambiguate": opts,
        "clarify": "转专业要先看目标学院的接收计划。你要转去哪个学院？",
        "focus": [],
        "quotes": [],
        "map": map_hit,
        **sensitivity(text),
        "router_llm": False,
        "rule_unsure": False,
    }


_FOLLOW_RE = re.compile(
    r"^(?:那|那么|这个|那个|它|然后|还有|另外|再|如果)|"
    r"还要|需要带|带什么|要带什么|准备什么|哪些材料|什么材料|"
    r"多长时间|多久|什么时候|几点|在哪|哪里|哪儿|去哪儿|去哪里|怎么|如何|多少|"
    r"多少钱|费用|流程|时间|地点|电话|材料|证件|条件|要求|"
    r"可以吗|能不能|行不行|要不要|用不用|需要|预约|然后呢"
)

_GENERIC_TERMS = {
    "要带什么", "带什么", "带什么东西", "准备什么", "要准备什么",
    "多久", "多长时间", "在哪", "在哪里", "哪儿", "怎么办", "怎么弄",
    "费用", "多少钱", "流程", "材料", "条件", "电话", "时间", "地点",
    "可以吗", "能不能", "然后呢", "预约",
}


_ANAPHORA_RE = re.compile(r"^(?:那|那么|这个|那个|它|然后|还有|另外|再|如果)|还要|然后呢|你说的")


def _is_followup(text: str) -> bool:
    """这句是不是接着上一问说的。

    只认两种：句子自己带指代（「那」「它」「还有」开头），或者整句就是光秃秃的泛问
    （「多久」「多少钱」「怎么办」）。老版本只要句里有「怎么」就判续问，
    「饿了怎么办」「校园卡丢了怎么补办」这种自带主体的句子会被拼上上一条事项，
    答成上一件事（2026-11-06 用户实测）。
    """
    t = norm(text)
    if not t:
        return False
    if _ANAPHORA_RE.search(t):
        return True
    return t in _GENERIC_TERMS or (len(t) <= 4 and bool(_FOLLOW_RE.search(t)))


def _mentions_other_item(text: str, ctx_id: str) -> bool:
    """句子里点了别的事项或地点（「那转专业呢」「图书馆要预约吗」），就别套上一条。"""
    q = norm(text)
    ctx = ITEM_BY_ID.get(ctx_id) or {}
    ctx_text = norm(ctx.get("title", "") + "".join(ctx.get("aliases") or []))
    for name in _place_names():
        if len(name) >= 2 and name in q and name not in ctx_text:
            return True
    for it, sc in rank(text)[:8]:
        if it["id"] == ctx_id or sc < MATCH_THRESHOLD:
            continue
        names = [it.get("title", ""), *(it.get("aliases") or [])]
        kws = it.get("keywords") or []
        for name in [*names, *kws]:
            nn = norm(name)
            if len(nn) < 2 or nn in _GENERIC_TERMS:
                continue
            if len(nn) >= 3 and nn in q:
                return True
            if len(nn) == 2 and nn in q and sc >= 70 and name in kws:
                return True
    return False


def _llm_on(router_llm: bool | None) -> bool:
    """模型裁决开不开：界面开关传了以开关为准，没传按环境变量 ROUTER_LLM（默认开）。"""
    if router_llm is None:
        return str(os.getenv("ROUTER_LLM", "1")).strip().lower() not in ("0", "false", "off", "no")
    return bool(router_llm)


def _context_needed(text: str, ctx: dict | None, prev_q: str,
                    status: dict[str, Any], llm_on: bool = True) -> bool:
    """这句要不要接上一条才答得清楚。

    主判交给模型（llm_needs_context），接口不通才退回手写词表：词表判续问只有两半，
    两半都错过——句里带「怎么」就判续问，把「滑雪」「校园卡丢了怎么补办」这种自带主体的
    句子拼上上一条；词表没写的「几天能办好」判独立，答不上。
    模型判完不再叠 `_mentions_other_item`：那道闸是给词表兜底的，它按 rank 前 8 名
    里「名字撞进句子」的条目否决，而那些条目是「周末」「办好“」这类碎词命中的无关摘录
    （11-07 实测：模型已判「几天能办好」「周末呢」要接上一条，两道闸把它们全否了，
    「周末呢」因此被套上博物馆预约表 0.86 错答）。「句子里点了别的事算不需要」
    这条判法已经写进 ctx_need 的规则，模型自己会判（D 类实测判得对）。
    关模型（规则模式）时不发这次调用，退回词表。
    """
    if not ctx:
        return _is_followup(text)
    need = llm_needs_context(text, ctx.get("title", ""), prev_q, status) if llm_on else None
    if need is not None:
        return need
    return _is_followup(text) and not _mentions_other_item(text, ctx["id"])


def _contextual_text(text: str, ctx: dict | None, need: bool,
                     standalone: str = "") -> tuple[str, str | None, str]:
    """返回（检索串, 上一条 id, 判分串）。

    检索串可以带上一条（要把那一件事的条目捞进候选池），判分串不能带：
    候选行里就写着那条标题，题面开头摆着它，模型只要看到字面重合就能给高分，
    这一问变成自己证明自己答得上（2026-11-06「滑雪」被转接到服务大厅）。
    压缩出独立问句时只用它——那本来就是一句完整的话，再拼标题是双份上文。
    """
    if not ctx or not need:
        return text, None, ""
    if standalone:
        return standalone, ctx["id"], standalone
    return (f"{ctx['title']}，{text}", ctx["id"],
            f"{text}\n（上一句问的是「{ctx['title']}」，这一句接着它问）")


def _answer_core(text: str, given: dict[str, str] | None = None,
                 router_llm: bool | None = None,
                 history: list[dict[str, str]] | None = None,
                 pick_id: str = "", judge_text: str = "") -> dict[str, Any]:
    # judge_text：判分与复核看的题面。续问时检索串拼了上一条事项的标题，判分串不能拼——
    # 候选行里就写着那条标题，题面再开头摆一次，模型看到字面重合就能给高分，
    # 等于自己证明自己答得上。不带时（绝大多数单轮）判分串就是题面，行为一字不变。
    jt = judge_text or text
    # pick_id：用户在反问菜单里点了某一条。这一条是他挑的，直接打开它，
    # 不能再走一遍路由——同一个词回炉只会把同样的选项再摊一次。
    # 模型裁决默认开着：规则模式在方向词（迁入/迁出）、身份限定词（留学生/研究生）
    # 和具体条款这几类问题上会自信地答错，48 题实测里模型层改判 10 次、8 次改对。
    # 界面开关传 true/false 时以开关为准；要在命令行关掉，设 ROUTER_LLM=0。
    llm_on = _llm_on(router_llm)
    picked = pick_id if (pick_id and pick_id in ITEM_BY_ID) else ""
    num = NUM_ONLY.match(text or "")
    if num:
        hit = number_answer(text, num.group(1), llm_on)
        if hit is not None:
            return hit
        nums = "、".join(str(x) for x in _known_building_numbers())
        return {
            "matched": False,
            "query": text,
            "normalized": None,
            "topic": f"{num.group(1)}号楼",
            "map": None,
            "hints": [],
            "contacts": [],
            "alternatives": [{"id": "campus-louming",
                              "title": (ITEM_BY_ID.get("campus-louming") or {}).get("title", "")}],
            "next_actions": [
                f"校园地图里没有「{num.group(1)}号楼」的对应名称。已收录楼号：{nums}",
                "也可以直接问「立德楼在哪」「48教怎么走」",
            ],
            "suggestion": "只输入楼号时，我只按校园地图的楼号对照表回答。",
            "confidence": 0.0,
            "band": "none",
            "focus": [],
            "quotes": [],
            "answers": [{
                "focus": "overview",
                "label": "校园地图未收录",
                "text": None,
                "steps": [],
                "quotes": [],
                "found": False,
            }],
            **sensitivity(text),
            "router_llm": llm_on,
            "rule_unsure": False,
        }
    places = map_places(text)
    map_hit = places[-1] if places else None
    place_slot = _place_slot_item(places)

    # 转专业先反问学院，别让「转专业」这个单词进联想菜单
    tp = None if picked else transfer_plan(text)
    clarify = None if picked else _transfer_clarify(text, tp, map_hit)
    if clarify:
        return clarify

    # 单个词：先把相关事项全摊成选项（地点词的第一项是「在哪」，仍走地点卡）
    # 摊之前先让模型在候选里定一次：定得下来就直答，定不下来才摊选项。
    menu_pick: tuple[dict[str, Any], int, list[str]] | None = None
    menu_mr: dict[str, Any] | None = None
    menu_default_opts: list[dict[str, Any]] = []
    menu = None if picked else _topic_menu(text)
    if menu:
        rows = menu.pop("_rows", [])
        is_place_menu = menu.pop("_place_menu", False)
        default_pick = menu.pop("_default_pick", "")
        # 地点词不交给模型：菜单第一项本来就是「在哪」，点了直接出定位，
        # 模型挑中某条原文反而会把地点答案挤掉。
        if rows and not is_place_menu and llm_on and api_key():
            menu_mr = _new_model_route()
            menu_pick = _menu_llm_pick(text, rows, history, menu_mr)
        if menu_pick is None and default_pick in ITEM_BY_ID:
            # 这个词在 topic-menus.json 里登记了主答：按这一条答，其余选项挂在答案下面
            picked = default_pick
            menu_default_opts = menu.get("disambiguate") or []
        elif menu_pick is None:
            if places and _place_exact(text, places):
                menu["item"] = public(_named_place_item(places) or place_item(places))
                menu["map"] = map_hit
            if menu_mr is not None:
                menu["model_route"] = menu_mr
                menu["router_llm"] = True
            return menu

    # 只问地点：直接答点到的这一处，不再端出整张对照表，也不让转专业路由抢走
    # 例外：这个地点本身分几种情况（快递驿站分校内 / 梆子井），先问清再答，
    # 否则只会报一个点位，另一处的答案被吞掉。
    if places and not picked and not place_slot and _place_exact(text, places) and (
        PLACE_ONLY.search(text) or not PLACE_ASK.search(text)
    ):
        parts = place_parts(places)
        quotes: list[dict[str, str]] = []
        for p in parts:
            quotes.extend(p["quotes"])
        unnamed = [h["name"] for h in places if not h.get("src")]
        return {
            "matched": True,
            "query": text,
            "normalized": "校园地点 · " + "、".join(h["name"] for h in places),
            "confidence": 0.99,
            "band": "high",
            "ambiguous": False,
            "item": public(_named_place_item(places) or place_item(places)),
            "answers": parts,
            "focus": ["location"],
            "hold": False,
            "followups": [],
            "known": {},
            "quotes": quotes,
            "missing": [],
            "note": (f"官方位置表没有写「{'、'.join(unnamed)}」的具体位置，这里只给名称、公开出处和地图定位。"
                     if unnamed else None),
            "map": map_hit,
            **sensitivity(text),
            "router_llm": llm_on,
            "rule_unsure": False,
        }

    if tp:
        quotes, seen = [], set()
        for p in tp["parts"]:
            for q in p["quotes"]:
                if q["quote"] not in seen:
                    seen.add(q["quote"])
                    quotes.append({"quote": q["quote"], **src_label(q["src"])})
        focus = tp.get("focus") or {}
        target = ""
        if focus.get("major"):
            target = (f"{focus['abbr']} → {focus['major']}"
                      if focus.get("abbr") and focus["abbr"] != focus["major"]
                      else focus["major"])
        if tp.get("no_plan"):
            normalized = f"转专业 · {tp['display']}（暂无接收计划）"
            if target:
                normalized += f" · {target}"
        else:
            normalized = f"转专业 · {tp['display']}接收计划"
            if target:
                normalized += f" · {target}"
        file_url = ""
        if tp.get("file"):
            file_url = f"/api/plan-file?college={urllib.parse.quote(tp['college'])}"
            if tp.get("plan"):
                tp["plan"]["file_url"] = file_url
        return {
            "matched": True,
            "query": text,
            "normalized": normalized,
            "confidence": 0.95, "band": "high",
            "item": public(next(i for i in ITEMS if i["id"] == "zhuanzhuanye")),
            "answers": tp["parts"], "hold": False, "followups": [],
            "focus": [p["focus"] for p in tp["parts"]],
            "quotes": quotes, "note": tp.get("note"),
            "plan": tp.get("plan"),
            "plan_no_file": tp.get("no_plan", False),
            "plan_file": file_url,
            "map": map_place(text),
            **sensitivity(text), "router_llm": False, "rule_unsure": False,
        }

    ranked = _yield_to_children(text, rank(text))
    # 「快递驿站在哪」这类地点问句容易被楼宇速查以泛词抢走，先落回带分支的地点条目
    if place_slot:
        idx = next((n for n, (it, _) in enumerate(ranked)
                    if it["id"] == place_slot["id"] and _ >= MATCH_THRESHOLD), None)
        if idx:
            ranked.insert(0, ranked.pop(idx))
    top, score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0

    # 只有自动抽取的制度卡片勉强沾边时不硬答：这类卡片是资料，
    # 低分命中往往只共享「学位」「办法」等泛词，答了反而误导。
    if top.get("auto") and score < 70:
        score = 0

    # 纯问地点的短句（「图书馆在哪」）优先给校园地点条目，别落到办这件事的条目上
    place_forced = False
    if not picked and PLACE_ONLY.search(text) and not place_slot and "在哪" not in top["title"]:
        for cand, cand_score in ranked[:4]:
            if cand["id"] in ("campus-louming", "campus-jiancheng") and cand_score >= 70:
                top, score, second = cand, cand_score, 0
                place_forced = True
                break

    # 规则拿不准时，若开启 LLM 兜底，让模型在候选里选（只选，不生成事实）。
    # 候选池除了规则前排，还从向量命中的原文段落反查条目，
    # 由 DeepSeek Flash 判断哪条真的回答了问题，而不是只看关键词重合。
    # 96 分以上的强命中不送模型，避免把已经答对的条目改坏；问句长短不再设门槛。
    top_title = core_title(top["title"]) if top else ""
    rival = next((sc for it, sc in ranked[1:]
                  if core_title(it["title"]) != top_title), 0)
    # 「差一点」按规则原始分算：模型抬完分再判就永远判不到这一档。
    rule_score = score
    near_miss = NEAR_MISS_FLOOR <= rule_score < MATCH_THRESHOLD
    risky = score < MATCH_THRESHOLD or (rival > 0 and score - rival < 8 and score < 90)
    rc_signed: bool | None = None   # None＝复核没参与（规则模式、用户点选、菜单、地点强答）
    resolved_by_llm = False
    soft_match = False
    rerank_info: dict[str, Any] | None = None
    pool: list[tuple[dict[str, Any], int]] = []
    # 模型这一层到底有没有参与，是要给用户看的：没问、问了、报错，三样得分开。
    model_route: dict[str, Any] = menu_mr if menu_mr is not None else _new_model_route()
    if picked:
        # 用户从选项里点了这一条：答案就按这一条给，规则和模型都不许再换
        top, score, second = ITEM_BY_ID[picked], 90, 0
        resolved_by_llm = True
        model_route["gate"] = "menu_default" if menu_default_opts else "user_pick"
    elif menu_pick is not None:
        # 单词菜单已由模型定下一条：用它，别再让规则评分和第二轮裁决改回去
        chosen, chosen_score, chosen_facets = menu_pick
        top, score, second = chosen, chosen_score, 0
        resolved_by_llm = True
        soft_match = chosen_score < RERANK_MIN
        model_route["changed"] = True
        model_route["rescue"] = "menu_pick"
        model_route["facets"] = chosen_facets
    elif not llm_on:
        model_route["gate"] = "router_off"
    elif not api_key():
        model_route["gate"] = "no_key"
    elif place_forced:
        model_route["gate"] = "place_forced"
    elif _strong_hit(score):
        model_route["gate"] = "strong_hit"
    if llm_on and not picked and menu_pick is None and not _strong_hit(score) and not place_forced:
        rule_top_id = top["id"] if top else ""
        pool = rerank_candidates(text, ranked, status=model_route)
        model_route["pool"] = len(pool)
        # 用户点了个词表里没有的名字（ps 这类简称），候选里没人写它：先让模型把这叫法
        # 对到库里已有的名字上，再把写了那个名字的条目按规则原序端进池子。
        # 只加候选、不加门槛——下面 rerank 的 75/60/10 三道闸照样把关，规则腿一行不动。
        said = _unmatched_name(text)
        if said:
            pmenu = proper_menu_for(ranked)
            pm = llm_proper_map(text, said, pmenu)
            name = pm.get("name") or ""
            extra = proper_map_extra(ranked, name, {it["id"] for it, _ in pool})
            if extra:
                pool = pool + extra
                model_route["pool"] = len(pool)
            model_route["proper_map"] = {
                "said": said, "name": name, "added": len(extra), "menu": len(pmenu),
                "why": pm.get("why", ""), "error": pm.get("error", ""),
            }
        # 名字在词表里、池子里却一条都没带它（0 分的正答条目进不了规则前八）：
        # 上面那条映射只管词表不认识的名字，这一路管认识的——补的仍是候选，门槛不动。
        fill = proper_fill_candidates(text, ranked, pool)
        if fill:
            # 池子尾巴换掉，不往后追加：总数仍是 14，验的还是同一份池子大小
            pool = pool[:max(0, RERANK_POOL_LIMIT - len(fill))] + fill
            model_route["pool"] = len(pool)
            model_route["proper_fill"] = [it["id"] for it, _sc in fill]
        rewrites: list[str] = []
        rr = None
        if not pool:
            model_route["gate"] = "no_candidates"
        else:
            rr, rewrites = llm_rerank(jt, pool, history, status=model_route)
        if rr is not None:
            best = rr["item"]
            bsc = rr["score"]
            rule_llm = rr["scores"].get(rule_top_id, 0)
            model_route["asked"] = True
            model_route["facets"] = rr.get("facets") or []
            model_route["why"] = rr.get("why") or ""
            model_route["score"] = bsc
            # 规则本来就没到阈值时，模型是唯一还能对上事项的人，60 分就接；
            # 要顶掉一个已达阈值的规则首选，仍须 75 分且比规则首选高出 10 分。
            floor = RERANK_MIN if score >= MATCH_THRESHOLD else RERANK_ACCEPT
            better = bool(best) and bsc >= floor and (
                score < MATCH_THRESHOLD
                or (best["id"] != rule_top_id and bsc - rule_llm >= RERANK_MARGIN)
            )
            if better and best is not None and (
                    best["id"] != rule_top_id or score < MATCH_THRESHOLD):
                top, score = best, max(score, bsc)
                second = 0
                resolved_by_llm = True
                soft_match = bsc < RERANK_MIN
                model_route["changed"] = best["id"] != rule_top_id
                model_route["confirmed"] = best["id"] == rule_top_id
            rerank_info = {
                "used": True,
                "pool": len(pool),
                "rule_top": rule_top_id,
                "best": best["id"] if best else None,
                "score": bsc if best else 0,
                "rule_score": rule_llm,
                "changed": resolved_by_llm,
                "soft": soft_match,
                "facets": model_route["facets"],
                "why": rr.get("why") or "",
            }
            if best is None:
                # 模型看完候选说「都没答上」：这时不能再拿它的改写给关键词运气开门，
                # 否则一句含糊的「转其他学院」会被顶成高置信的无关事项。
                model_route["gate"] = "llm_declined"
        elif risky:
            # rerank 不可用时退回旧路：先让模型翻译，再拿改写回规则检索
            model_route["gate"] = "rerank_unavailable"
            # 别复用 picked：那是用户点选的条目 id。这里把它改成模型选的条目，
            # 下面的复核入口看到 picked 非空就整块跳过，等于模型自己选的题没人复核。
            route_pick, rewrites = llm_route(jt, ranked[:8], history, status=model_route)
            if route_pick is not None and not pool:
                # 候选池空着（规则腿 0 分、向量补面也没捞到）时，ranked[:8] 全是 0 分的无关
                # 条目——0 分并列，谁排第一是原表顺序的巧合。把这种池子端到模型面前让它「挑一条」，
                # 挑中就是错答：「滚木」被答成校园卡补卡就是这么来的，而复核那条路又因为候选池空
                # 被跳过。有候选池（含向量补面来的）照旧接，改写照旧留给下面 rewrite_pool
                # 那条有 rerank 打分把关的救场路。
                model_route["pick_dropped"] = route_pick["id"]
                route_pick = None
            if route_pick is not None:
                top = route_pick
                score = max(score, MATCH_THRESHOLD + 1)
                second = 0
                resolved_by_llm = True
                soft_match = score < RERANK_MIN
                model_route["asked"] = True
                model_route["changed"] = True
        if not resolved_by_llm and rewrites and score < MATCH_THRESHOLD:
            # 规则答不上来时，用模型自己给的说法重建候选池，再让模型判一遍。
            # 用户会用什么缩写没人能预先列全，列别名是白费；把条目端到模型面前才是正路。
            pool2 = rewrite_ranked(rewrites)
            model_route["pool2"] = len(pool2)
            rr2 = None
            if pool2:
                rr2, _ = llm_rerank(jt, pool2, history, status=model_route)
            if rr2 is not None and rr2["item"] is not None and rr2["score"] >= RERANK_ACCEPT:
                top, score = rr2["item"], max(score, rr2["score"])
                second = 0
                resolved_by_llm = True
                soft_match = rr2["score"] < RERANK_MIN
                model_route["asked"] = True
                model_route["changed"] = True
                model_route["rescue"] = "rewrite_pool"
                model_route["score"] = rr2["score"]
                model_route["why"] = rr2.get("why") or model_route["why"]
                if rr2.get("facets"):
                    model_route["facets"] = rr2["facets"]
                rerank_info = {
                    "used": True, "pool": len(pool2), "rule_top": top["id"],
                    "best": top["id"], "score": rr2["score"], "rule_score": 0,
                    "changed": True, "soft": soft_match,
                    "facets": model_route["facets"], "why": model_route["why"],
                    "from": "rewrite_pool",
                }
            elif rr2 is None:
                # 模型这一轮没调用成功，才退回关键词地板（原来那条 70 分 + 拉开 5 分的路）
                assoc = assoc_pick(rewrites)
                if assoc is not None and assoc[0]["id"] != top["id"]:
                    top, score = assoc
                    second = 0
                    resolved_by_llm = True
                    soft_match = score < RERANK_MIN
                    model_route["asked"] = True
                    model_route["changed"] = True
                    model_route["rescue"] = "keyword_fallback"
        if rewrites:
            model_route["rewrites"] = rewrites

    # 复核：模型腿把这条定下来之后，再看一次它到底答没答上用户问的这件事。
    # 范围＝模型模式的正常作答路径。用户自己点选的（picked）不许再改；
    # 单词菜单（menu_pick）与地点强答（place_forced）没进过 206 题实测，不动。
    recheck_none = ""          # 非空＝复核判答不上，走「没收录」那一栏，值就是给人看的那句
    recheck_declined = ""      # 被复核判答不上的那一条，别再挂在「相关事项」里让用户去点
    recheck_switch = False     # 复核换过去的那条按用户点选那条同样的方式渲染
    if (llm_on and api_key() and not picked and menu_pick is None
            and not place_forced and top is not None):
        rc_pool = pool or rerank_candidates(text, ranked, status=model_route)
        rc_ids = {it["id"] for it, _ in rc_pool}
        model_route["pool"] = len(rc_pool)
        cur = top["id"]
        if not rc_ids or (RECHECK_SKIP_ABOVE and score >= RECHECK_SKIP_ABOVE):
            # 候选池空着没有可比条目，或判分已经高到不必再看全文——都不多烧这一次调用。
            # 阈值比的是最终得分（规则分与模型分取大）；skipped 不进签字白名单，
            # 所以 50~54 那档 near-miss 照样被闸住，跳过高分不会把门开松。
            model_route["recheck"] = {"gate": "skipped"}
        else:
            rc = llm_recheck(jt, top, rc_pool)
            best_id = rc.get("best") or ""
            if "error" in rc:
                # 复核自己挂了不能把答得上顶掉：照现行答案给，把失败记在状态里
                rc_gate = "error"
            elif rc.get("verdict") == "no" and (not best_id or rc.get("answers") != "yes"):
                # 说「没收录」之前，先看第一次没送进候选池的那些条目里有没有真答得上的
                cands = offpool_candidates(text, rc_ids, cur)
                look = llm_second_look(jt, cur, cands)
                hit_id = "" if look.get("error") else (look.get("best") or "")
                rc_gate = "say_none"
                model_route["recheck_second"] = {
                    "candidates": len(cands), "best": hit_id,
                    "answers": look.get("answers", ""), "why": look.get("why", ""),
                    "error": look.get("error", ""),
                }
                if hit_id and look.get("answers") == "yes" and hit_id in ITEM_BY_ID:
                    top, score, second = ITEM_BY_ID[hit_id], 90, 0
                    resolved_by_llm, recheck_switch = True, True
                    rc_gate = "second_look"
                    model_route["asked"] = True
                    model_route["changed"] = True
                    model_route["rescue"] = "offpool_second_look"
                else:
                    recheck_none = (
                        "学校文件里没写这件事。" if look.get("none_in_library") else
                        "库里沾边的原文讲的都是别的事，你问的这一点我没对上能回答的原文。")
                    recheck_declined = cur
            elif best_id and best_id != cur and rc.get("answers") == "yes" and best_id in rc_ids:
                top, score, second = ITEM_BY_ID[best_id], 90, 0
                resolved_by_llm, recheck_switch = True, True
                rc_gate = "switch"
                model_route["asked"] = True
                model_route["changed"] = True
            elif best_id and best_id != cur:
                # 想换但护栏拦住：不在候选池里，或模型自己说换成它也答不上
                rc_gate = "rejected"
            else:
                rc_gate = "keep"
            model_route["recheck"] = {
                "gate": rc_gate, "verdict": rc.get("verdict", ""), "best": best_id,
                "answers": rc.get("answers", ""), "why": rc.get("why", ""),
                "error": rc.get("error", ""),
            }

    rc_gate_seen = str((model_route.get("recheck") or {}).get("gate") or "")
    if rc_gate_seen:
        # 复核看过全文、认了这条（或换成另一条）才算签字；
        # 接口失败、没有可比候选、想换被护栏拦住、判「没收录」，都不算。
        rc_signed = rc_gate_seen in ("keep", "switch", "second_look")
    # 50~54 这一档只能由复核签字开门。复核没参与的路径（规则模式、用户点选、
    # 菜单、地点强答）保持原样，不在这条规则里改行为。
    near_miss_unsigned = bool(near_miss and llm_on and api_key()
                              and not picked and menu_pick is None and not place_forced
                              and rc_signed is False)
    if near_miss:
        model_route["near_miss"] = {"recheck": rc_signed or "", "blocked": near_miss_unsigned}
    near_miss_note = ("这一条只是字面上沾了一点边，模型看过原文全文没确认，我不拿它当答案。"
                      if near_miss_unsigned else "")
    if near_miss_unsigned and top is not None:
        # 模型没确认的那条，别再挂到「相关事项」里请用户去点
        recheck_declined = recheck_declined or top["id"]

    # 没到阈值但候选分数不低：不硬拒，给出"是不是这个"的选择题
    # 自动抽取的制度卡片不参与选择题：两个同名文件让用户选，等于没答
    alt_rows = distinct_rows([(i, sc) for i, sc in ranked[:6]
                              if sc >= 38 and not i.get("auto")])
    near = [(i, sc) for i, sc in alt_rows[:3] if _names_subject(norm(text), i)]
    if (not resolved_by_llm) and (not recheck_none) and score < MATCH_THRESHOLD \
            and len(near) >= 2 and (near[0][1] - near[1][1]) < 14:
        return {
            "matched": True,
            "query": text,
            "normalized": "待确认是哪一类",
            "confidence": round(near[0][1] / 100, 2),
            "band": "low",
            "ambiguous": True,
            "item": public(near[0][0]),
            "answers": [],
            "hold": True,
            "followups": [],
            "disambiguate": [
                {"id": i["id"], "title": i["title"], "dept": i.get("dept", ""),
                 "hint": (i.get("aliases") or [""])[0]}
                for i, _ in near
            ],
            "clarify": f"没太确定，你是想问「{near[0][0]['title']}」还是「{near[1][0]['title']}」？",
            "focus": [],
            "quotes": [],
            "map": map_hit,
            **sensitivity(text),
            "router_llm": llm_on,
            "rule_unsure": risky,
            "rerank": rerank_info,
            "model_route": model_route,
            "soft_match": soft_match,
        }

    # 两道输出闸：模型判死就不再替它作答、置信不到地板就转拒答。
    # 落进拒答分支以后，组装层的 rescue 照样会在里面跑——这两道闸关掉的是「拿规则腿第一名硬答」，
    # 不是「逐字摘自官方条目的拼答」，所以不会把 #56 的收益一起砍掉。
    refused_by = _output_gate(model_route, score)
    if refused_by:
        model_route["refused_by"] = refused_by
    if score < MATCH_THRESHOLD or recheck_none or near_miss_unsigned or refused_by:
        miss_hints = dept_hints(text)
        miss_contacts = related_contacts(text)
        # 归口线索 / 公开联系方式两栏都可能为空，为空时卡片上没有部门那一栏，
        # 不能让用户「按上面的」去找。两个界面渲染的栏不一样，这里不指位置。
        dept_action = ("按公开联系方式里的部门查最新通知，或直接打电话问"
                       if miss_contacts else
                       "打开公开联系方式，挑一个对得上的部门打电话问")
        alt_miss = [i for i, _ in alt_rows[:3] if i["id"] != recheck_declined]
        # 「换个更具体的说法」的例子不写死：先用模型自己给的校园说法（rewrites），
        # 它才是真看过这句问话、真联想过的；模型没给（规则模式/接口挂）才退回候选事项标题。
        ex = [w.strip() for w in (model_route.get("rewrites") or [])
              if w.strip() and norm(w) != norm(text)]
        if not ex:
            ex = [str(i.get("title") or "").strip() for i in alt_miss if str(i.get("title") or "").strip()]
        more_hint = "换个更具体的说法" + ("，比如" + "、".join(f"「{x}」" for x in ex[:3]) if ex else "")
        base = {
            "matched": False,
            "query": text,
            "normalized": None,
            "topic": text.strip()[:24],
            "map": map_hit,
            "hints": miss_hints,
            "contacts": miss_contacts,
            "rerank": rerank_info,
            "model_route": model_route,
            "alternatives": [
                {"id": i["id"], "title": i["title"]}
                for i in alt_miss
            ],
            "next_actions": [
                more_hint,
                dept_action,
                "找到官方通知后，以通知上写的为准",
            ],
            "suggestion": recheck_none or near_miss_note or "这一项我没对上官方原文，给不出办理流程。",
            "confidence": 0.0 if (recheck_none or near_miss_unsigned or refused_by) else round(score / 100, 2),
            "band": "none",
            "focus": [],
            "quotes": [],
            "answers": [{
                "focus": "overview",
                # 库里其实有一条沾边的，只是模型看完全文没确认——不写成「未收录」
                "label": "相近但没确认" if near_miss_unsigned else "知识库未收录",
                "text": None,
                "steps": [],
                "quotes": [],
                "found": False,
            }],
        }
        # 检索四条腿都没把答案端到模型面前时，最后再试一次：让模型把这句话换成
        # 学校文件里的说法重新检索，逐面否决（#56 的拒答兜底）。
        if _assemble_on("rescue") and llm_on and api_key():
            asm = assemble_faces(jt, [], set(), model_route)
            if asm:
                return _assembled_answer(text, asm, base, score)
        hits = original_hits(text, status=model_route)
        if hits:
            base["original_search"] = hits
            src_items = _src_item_index()
            ids: list[str] = []
            for h in hits:
                slug = str(h.get("source") or h.get("doc") or "").split("~")[0]
                for iid in list(h.get("item_ids") or []) + src_items.get(slug, []):
                    if iid not in ids:
                        ids.append(iid)
            related = [
                {"id": iid,
                 "title": (ITEM_BY_ID.get(iid) or {}).get("title", iid),
                 # title 还是原来那句，点下去要用它去问；label 才是给人看的写法
                 "label": _card_label(ITEM_BY_ID.get(iid) or {"title": iid})}
                for iid in [x for x in ids if x != recheck_declined][:3]
            ]
            if related:
                base["related_items"] = related
            base["search_note"] = "没找到对应的事项。下面几段原文可能相关，点开核对；原文没写的内容不会出现在这里。"
        if STRATEGY.search(text):
            base.update({
                "ambiguous": True,
                "clarify": "学校文件里没写该选哪条路，这部分我不替你判断。"
                           "你要办的是哪件事？我按文件里的条件和流程答：",
                "reason": "这类问题没有原文支撑，得说清楚要办哪件事才能答",
                "disambiguate": [
                    {"id": i["id"], "title": i["title"], "dept": i.get("dept", ""),
                     "hint": (i.get("aliases") or [""])[0]}
                    for i, _ in distinct_rows(ranked[:3]) if i["id"] != recheck_declined
                ],
                **sensitivity(text),
                "router_llm": llm_on,
                "rule_unsure": risky,
            })
            return with_free_answer(base, jt, llm_on, history, status=model_route)
        if CAMPUS_HINT.search(text):
            near_opts = [
                {"id": i["id"], "title": i["title"], "dept": i.get("dept", ""),
                 "hint": (i.get("aliases") or [""])[0]}
                for i, _ in alt_rows[:3] if i["id"] != recheck_declined
            ]
            if near_opts:
                base.update({
                    "ambiguous": True,
                    "clarify": "没对上具体事项。你要办的是下面哪一类？",
                    "disambiguate": near_opts,
                })
        base.update({
            **sensitivity(text),
            "router_llm": llm_on,
            "rule_unsure": risky,
        })
        return with_free_answer(base, jt, llm_on, history, status=model_route)

    # 同一族事项分数咬得很紧时，先答最像的那一条，把另一条放进「相关事项」；
    # 不拿「你是想问 A 还是 B」把回答整个拦住——点进来是要办事的。
    # 但如果句子里同时点了地点，地点只是背景，选办这件事的条目（别拿楼宇速查去反问答不上）
    rivals_all = distinct_rows([(i, sc) for i, sc in ranked[:5]
                                if sc >= MATCH_THRESHOLD and not i.get("auto")])
    rivals = ([rivals_all[0]] if rivals_all else []) + [
        (i, sc) for i, sc in rivals_all[1:] if _names_subject(norm(text), i)
    ]
    compound: list[dict[str, Any]] = []
    if (not resolved_by_llm) and not place_forced and len(rivals) >= 2 and (score - rivals[1][1]) < 8:
        if map_hit:
            concrete = [r for r in rivals if not str(r[0].get("id", "")).startswith("campus-")]
            if concrete:
                top, score = concrete[0]
                second = 0
                rivals = []
        if rivals:
            # 问的是具体一面（收费 / 几点 / 在哪…），而只有第一个候选真记了这一面：
            # 别再反问「你问的是 A 还是 B」，直接答有数据的那条
            facet_field = next(
                (f for k, _label, pattern in FOCUS_RULES
                 if re.search(pattern, text)
                 for f in [{"fee": "fee", "hours": "hours", "location": "location",
                            "duration": "duration", "window": "window",
                            "material": "materials", "contact": "dept"}.get(k)]
                 if f),
                None,
            )
            if (facet_field and rivals[0][0].get(facet_field)
                    and not any(r[0].get(facet_field) for r in rivals[1:])):
                top, score = rivals[0]
                rivals = []
        if rivals:
            top, score = rivals[0]
            compound = [i for i, _ in rivals[1:3]]

    # 宽泛父条目压住了带限定词的子条目时，把子条目提上来作答，父条目退回相关事项。
    # 只认问句里点了限定词、子条目自己也够得着命中线的情况，别的不动。
    promoted_from: dict[str, Any] | None = None
    if not resolved_by_llm and score < 100:
        kid = _promoted_child(text, top)
        if kid is not None:
            promoted_from = top
            top, score = kid[0], max(kid[1], score)
            rivals = []

    menu = None if (picked or recheck_switch) else _phone_menu(text, top)
    if menu:
        menu.update(**sensitivity(text), router_llm=llm_on)
        return menu

    focus = detect_focus(text, top)
    # 正则一个问面都没认出时（退回整体流程），用模型认出的问面补上：
    # 只铺整条流程会把「要什么条件」这类问题答成流程；这一面数据里真没有时，
    # 走的是「官方页面没有写」那句声明，不是沉默。
    focus_by_llm = False
    if focus == ["overview"] and model_route["facets"]:
        cand = [f for f in model_route["facets"] if f in FOCUS_KEYS and f != "overview"][:2]
        if cand:
            focus = cand
            focus_by_llm = True
    known0 = {**_known_slots(text, top), **(given or {})}
    parts = [_answer_one(top, f, known0, text) for f in focus]
    found = [p for p in parts if p["found"]]
    missing = [p["label"] for p in parts if not p["found"]]

    # 问「在哪」顺带问了怎么办时，别只甩一个地址
    if (not PLACE_ONLY.search(text)
            and any(p["found"] for p in parts)
            and all(p["focus"] == "location" for p in parts if p["found"])):
        ov = _answer_one(top, "overview", known0, text)
        if ov["found"]:
            parts.append(ov)
            missing = [m for m in missing if m != "整体流程"]

    known = {**_known_slots(text, top), **(given or {})}
    focus_keys = [p["focus"] for p in parts]
    followups = _followups(top, focus_keys, known)
    blocked = [f for f in followups if f["blocks"]]

    # 反问不能让用户一无所获，也不能把「要带什么」「在哪」换成流程：
    # 材料、地点、费用这类事实面照常给，分支流程等用户回答后再补。
    if blocked:
        base_part = _answer_one(top, "overview", known, text)
        fact_focus = {"material", "location", "fee", "hours", "window",
                      "duration", "contact", "amount", "pitfalls"}
        keep = [p for p in parts if p["found"] and p["focus"] in fact_focus]
        if keep:
            parts = keep + ([base_part] if base_part["found"] else [])
        elif base_part["found"]:
            parts = [base_part]
        else:
            parts = [p for p in parts if p["found"]]
        focus_keys = [p["focus"] for p in parts]
        missing = [m for m in missing if m not in ("官方答复", "整体流程")]

    # 聚焦项一个都没命中时退回整体答复，别交白卷
    if not any(p["found"] for p in parts):
        ov = _answer_one(top, "overview", known, text)
        if ov["found"]:
            parts = [ov]
            focus_keys = ["overview"]
            # 保留 missing：问「多少钱」而简章没写费用时，
            # 不能拿流程顶上来还不吭声，要明说这一面没有收录。

    # 是非型问句（能不能/可以吗/同时）命中条目里的易错条款时，把那条直接答出来
    if re.search(r"能不能|可以吗|能同时|是否|行不行|会不会", text):
        for idx_pf, pf in enumerate(top.get("pitfalls") or []):
            key = "同时" if "同时" in text else ""
            if key and key not in pf:
                continue
            ev = (top.get("evidence") or {}).get(f"pitfalls.{idx_pf}")
            if not ev:
                continue
            parts.append({
                "focus": "pitfalls", "label": "注意", "text": pf,
                "found": True, "quotes": [{"quote": ev.get("quote", ""), "src": ev.get("src", "")}],
            })
            break

    # 点了表里的哪一处，就只答那一行；整张表不再往外端
    lines = top.get("answer_lines") or []
    if lines and top.get("id") in ("campus-changguan-weizhi", "campus-jiancheng", "campus-louming"):
        idx_line = pick_answer_line(text, top, lines)
        if idx_line is None and llm_on and (PLACE_ASK.search(text) or len(norm(text)) <= 12):
            idx_line = llm_pick_line(text, top, lines, status=model_route)
        rest = [p for p in parts if p["focus"] not in ("overview", "location")]
        if idx_line is not None:
            entry = lines[idx_line]
            line = entry.get("line", "") if isinstance(entry, dict) else entry
            one = _best_quote((top.get("evidence") or {}).get("answer"), line)
            qs = ([{"quote": one.get("quote", ""), "src": one.get("src", ""),
                    **src_label(one.get("src", ""))}] if one else [])
            parts = [{"focus": "location", "label": "位置", "text": line,
                      "found": True, "quotes": qs}] + rest
            missing = [m for m in missing if m not in ("官方答复", "办理地点")]
        elif map_hit:
            parts = place_parts([map_hit]) + rest
            missing = [m for m in missing if m not in ("官方答复", "办理地点")]

    # 一题两问：后半句没认出问面、按现在的答案也确实没答到时，补第二面。
    # 「怎么租」「要空腹吗」这类问法没人能列全词表，「这段答没答到第二问」也只有模型判得出来
    # （2026-11-05 拍板②）：规则侧的 _unasked 按字面比对，说了整周开放时间也对不上「周末开吗」。
    # 模型补的那一面必须有条目原文逐字撑著；它不接手（判已答到、挑不出、接口失败）时，
    # 照原来的路子试一次整体流程那一面——补进来若与已答内容七成重合、或缺的那一问没少，都不补，
    # 端出来只会让用户同时看到答案和「这一问没答到」两句互相打脸的话（206 题里 7 题全卡在这）。
    # 「已答面是流程／步骤就不补」这条老闸门只留给规则腿：模型腿里「办理流程」恰恰是最常见的第一面，
    # 它答得上「怎么预约」却往往不含「收费吗」，这一问只有读了全文的模型判得出来。
    filled_pieces: list[str] = []
    flow_first = any(p["focus"] in ("overview", "steps") for p in parts)
    if not blocked and any(p["found"] for p in parts):
        unasked_before = _unasked(text, top, parts)
        # 模型腿的触发比规则腿宽一档：「收费吗」对上「前 5 次免费」时字面比对判已答到，
        # detect_focus 报出的问面（missing）才知道那一问其实没影（2026-11-05 实测 f1/f4 卡在这）。
        # 两样不并列喂：模型会照抄成「怎么收费；费用」一条，反而撞在自己那条照抄校验上（本轮 f2/f3）。
        # 所以有用户原话就只报原话；原话一条都对不上，才改用问面标签——且限一问真有两问的问句：
        # 「贵重物品怎么报案」里的「贵」会被 fee 规则认成「费用」，单问句拿标签触发就会补出一面假缺口
        # （2026-11-05 实测 f4 补进「该找哪个部门」，还悄悄撤了缺问声明）。规则腿的兜底仍只认字面那几问。
        two_asks = len([c for c in _CLAUSE_SPLIT.split(text or "")
                        if len(_mn(c)) >= 2 and _CLAUSE_ASKING.search(c)]) >= 2
        signals = unasked_before or (list(missing) if two_asks else [])
        if signals:
            add = None
            if llm_on and api_key():
                ff = llm_facet_fill(text, top, parts, signals, known)
                model_route["facet_fill"] = {k: ff[k] for k in ("gate", "fills", "why", "error") if k in ff}
                if ff["gate"] == "filled":
                    add, filled_pieces = ff["part"], [ff["fills"]]
            if add is None and unasked_before and not flow_first:
                ov = _answer_one(top, "overview", known, text)
                if ov["found"] and not _body_overlap(_part_body(ov), parts) \
                        and set(_unasked(text, top, parts + [ov])) < set(unasked_before):
                    add = ov
            if add is not None:
                parts.append(add)
                focus_keys = [p["focus"] for p in parts]

    # 「学校医保」这类大词：条目挑对了也只讲到整件事的一面。把缺的几面换成官方说法
    # 重检一遍，逐面让模型否决，只把逐字原文拼进来（#56；ASSEMBLE 关着时整块不跑）。
    if _assemble_on("fill") and llm_on and api_key() and not blocked and any(p["found"] for p in parts):
        asm = assemble_faces(jt, parts, {top["id"]}, model_route)
        if asm:
            parts = parts + asm
            focus_keys = [p["focus"] for p in parts]

    # 已经有内容可看时，不再单开一面写「没有收录」，缺的部分交给 note 逐项说清
    if any(p["found"] for p in parts):
        parts = [p for p in parts if p["found"]]
    # 问的是「不能带什么」，禁携清单就是答案，别再补「官方页面没有写要带什么」
    if missing and re.search(r"不能带|不能携带|禁带|禁携|不准带|不可以带|不让带", text):
        missing = [m for m in missing if m != "要带什么"]
    # 正文里已经写到这一面，就别再补「官方页面没有写」
    if missing:
        missing = [m for m in missing if not _facet_covered(m, parts)]

    normalized = f"{_short_title(top['title'])} · " + "、".join(p["label"] for p in parts)
    # 每一面的引文先按和这一面正文的重合度排，答的是第 6 步就别把第 0 步的原文摆在最前
    for p in parts:
        if len(p.get("quotes") or []) > 1:
            p["quotes"] = _order_quotes(p["quotes"], [p])
    quotes: list[dict[str, str]] = []
    seen_q: set[str] = set()
    for p in parts:
        for q in p["quotes"]:
            if q["quote"] not in seen_q:
                seen_q.add(q["quote"])
                quotes.append(q)
    # 汇总那一栏是「核对原文」里给用户看的，同样把撑得住结论的排前面
    quotes = _order_quotes(quotes, parts)

    # 判「是否还有别的可选」时按去重后的候选算，同名自动卡片不算第二选项
    second_clean = 0 if resolved_by_llm else next((sc for _, sc in distinct_rows(ranked[:3])[1:2]), 0)
    # 还在反问、或问的是另一个园区时，别把地图定到校内那个点
    show_map = None if blocked or (map_hit and known.get("campus") not in (None, "", "校内")) else map_hit
    related = _related_items(text, top)
    # 子条目提上来之后，原来那条宽泛父条目别丢：通用流程还在那条里，放进相关事项
    if promoted_from is not None and promoted_from["id"] not in {r.get("id") for r in related}:
        related = [{"id": promoted_from["id"], "title": promoted_from["title"],
                    "label": _card_label(promoted_from),
                    "dept": promoted_from.get("dept", "")}, *related]
    compound_note = None
    if compound:
        have = {r.get("id") for r in related}
        extra = [{"id": i["id"], "title": i["title"], "dept": i.get("dept", "")}
                 for i in compound if i["id"] != top["id"] and i["id"] not in have]
        if extra:
            related = extra + related
            compound_note = f"问句里还点到「{extra[0]['title']}」，相关内容放在下面的相关事项里。"
    # 登记了主答的单词菜单：这个词还能问的几件事排在最前面，答完抬头就能点
    if menu_default_opts:
        have = {r.get("id") for r in related}
        related = [o for o in menu_default_opts
                   if o.get("id") not in have and o.get("id") != top["id"]] + related
    # 问句里点了、这一条根本没写的东西，用用户自己的词说出来，别让他以为答全了。
    # 正在反问用户时不说这句：那时候答案本来就是半截的，两句叠在一起自相矛盾。
    unasked = [] if blocked else _unasked(text, top, parts)
    if filled_pieces:
        # 模型认这一面答得上那一问，补都补进答案了，就不许在同一张卡片上说「这一问没答到」。
        # 只在模型补掉的那几问上收口，其余照旧逐项声明。
        # 它照抄的可能是问面标签（「费用」）而不是用户原话（「收费吗」），
        # 所以同属那一面的原话一起收口，别让答案和声明各说一半。
        labs = {p for p in filled_pieces if p in FOCUS_BY_LABEL}
        unasked = [u for u in unasked if u not in filled_pieces and not (
            labs & {FOCUS_LABEL.get(k, "") for k in detect_focus(u, top)})]
    # 不加书名号：_display_text 会把「」一律剥掉，留着反而读不通
    unasked_note = (f"{'、'.join(unasked)}这一问，这次没答到。"
                    if unasked else None)
    # 模型只有 60～74 把握时接管的条目：照常给答案，但要把把握不够这件事说出来
    soft_note = (None if not soft_match or blocked else
                 "这一条是模型从相近事项里挑的，把握不到 75%，办之前按最新通知再确认一次。")
    # 数据表的行不进作答（2026-11-04 拍板「准确至上」）：逐格表格行没有办理上下文，
    # 顶在正文里等于拿一行数字当结论。只在答案下面留一个指向原文检索的链接。
    # 门槛取 4 个二字组，比 /api/search 更严——凑不满这个重合度就连链接都不给。
    rows_count = 0 if blocked else len(table_search(text, k=3, min_shared=4))
    return {
        "matched": True,
        "query": text,
        **sensitivity(text),
        "router_llm": llm_on,
        "resolved_by_llm": resolved_by_llm,
        "rerank": rerank_info,
        "model_route": model_route,
        "soft_match": soft_match,
        "focus_by_llm": focus_by_llm,
        # 已经在反问用户了，就不再说「规则没把握」——两句话叠在一起自相矛盾；
        # 地点分支条目（快递驿站）问清园区后给出的答案不再提示没把握
        "rule_unsure": risky and not blocked and not place_slot,
        "normalized": normalized,
        "confidence": round(min(score, 100) / 100, 2),
        "band": "high" if score >= 75 else "low",
        "ambiguous": score < 100 and (score - second_clean) < AMBIGUOUS_GAP,
        "item": public(top),
        "answers": parts,
        "headline": llm_headline(text, _headline_body(parts), llm_on, model_route),
        "focus": focus_keys,
        "hold": bool(blocked),
        "followups": followups,
        "known": known,
        "quotes": quotes,
        "missing": missing,
        "unasked": unasked,
        "note": "；".join(
            b.strip().rstrip("。；;，,") for b in (
                scope_note(top, text),
                experience_note(top, text),
                compound_note,
                unasked_note,
                soft_note,
                f"官方页面没有写「{'、'.join(missing)}」，我不能替学校补。" if missing else None,
            ) if b
        ) or None,
        "related": related,
        "map": show_map,
        "table_link": ({"q": text, "count": rows_count} if rows_count else None),
    }


_TITLE_NUM_PREFIX = re.compile(r"^[一二三四五六七八九十]+、|^（[一二三四五六七八九十]+）|^\([0-9]+\)")


def _short_title(title: Any, limit: int = 24) -> str:
    """把条目短名收拾得能放进「理解成」那一行。

    汇编切片的标题里常带章节号、竖线分隔的下一段、整条网址，直接端出来
    最显眼的那行就没法看了。这里只删不改写：截到第一段，去掉网址和章节号。
    """
    t = re.sub(r"https?://\S+|www\.\S+", "", str(title or ""))
    t = t.split("｜")[0]
    t = _TITLE_NUM_PREFIX.sub("", t.strip()).strip()
    t = re.sub(r"\s+", " ", t).strip(" ，,。;；、")
    return t[:limit] + "…" if len(t) > limit else t


def answer_question(text: str, given: dict[str, str] | None = None,
                    router_llm: bool | None = None,
                    context_item: str | None = None,
                    context_slots: dict[str, str] | None = None,
                    history: list[dict[str, str]] | None = None,
                    pick_item: str | None = None) -> dict[str, Any]:
    """续问接住上一件事；独立的新问题照样按原样路由。

    pick_item 是用户在反问菜单里点的那一条：直接打开它，不再重新路由。
    """
    orig = text
    # 「这句要不要接上一条」先判一次，判完才知道检索串、压缩和判分串各拿什么。
    # 历史只在真续问时才起作用，而且用完就丢：压成一句独立问句后，检索、重排、
    # 自由生成三条腿都只看见这句话。判独立的句子一个字的历史都不喂——上一轮回答
    # 的原文一旦进 prompt，改写和打分就跟着上一件事走（2026-11-06 实测：带一轮
    # 购电历史，「饿了怎么办」一次拒答、一次答成供餐时间）。
    note: dict[str, Any] = {}
    ctx = ITEM_BY_ID.get(context_item or "")
    asked = _history_questions(history)
    need = False if pick_item else _context_needed(orig, ctx, asked[-1] if asked else "",
                                                   note, _llm_on(router_llm))
    standalone = llm_condense(orig, history, note) if (need and history) else ""
    q = standalone or orig
    search, ctx_id, judge = _contextual_text(q, ctx, need, standalone)
    history = None
    if ctx_id:
        given = {**(context_slots or {}), **(given or {})}
    resp = _answer_core(search, given, router_llm, history, pick_id=pick_item or "",
                        judge_text=judge)
    if ctx_id:
        resp["query"] = orig
        resp["context_item"] = ctx_id
    if standalone:
        resp["condensed_query"] = standalone
    if note:
        resp.setdefault("model_route", {}).update(note)
    return resp


class AskReq(BaseModel):
    text: str
    slots: dict[str, str] = {}
    router_llm: bool | None = None   # None=按环境变量；界面开关传 true/false
    context_item: str | None = None
    context_slots: dict[str, str] = {}
    messages: list[dict[str, str]] = []
    pick_item: str | None = None     # 反问菜单里点开的条目 id


def clean_response(resp: dict[str, Any]) -> dict[str, Any]:
    """把回答正文统一成规定写法；原文引文与文书草稿不动。"""
    for p in resp.get("answers") or []:
        _clean_part(p)
    for key in ("clarify", "note", "normalized"):
        if isinstance(resp.get(key), str):
            resp[key] = _display_text(resp[key])
    for f in resp.get("followups") or []:
        if not isinstance(f, dict):
            continue
        for key in ("question", "why"):
            if isinstance(f.get(key), str):
                f[key] = _display_text(f[key])
    gen = resp.get("llm_answer")
    if isinstance(gen, dict):
        for key in ("text", "caveat"):
            if isinstance(gen.get(key), str):
                gen[key] = _display_text(gen[key], model=True)
    return resp


@app.post("/api/ask")
def ask(req: AskReq, request: Request) -> Any:
    maybe_reload()
    text = (req.text or "").strip()
    if len(text) < 2 and not NUM_ONLY.match(text):
        raise HTTPException(400, "请再说得具体一点")
    kw = dict(
        text=text, given=req.slots, router_llm=req.router_llm,
        context_item=req.context_item, context_slots=req.context_slots,
        history=req.messages or None, pick_item=req.pick_item,
    )
    # /field 带这个头来看流：每一步模型调用跑完就发一帧，最后 done 就是下面那个 dict。
    # 经典版 app.js 不带这个头，走的还是原来那一条，一个字节都不变。
    if "text/event-stream" in (request.headers.get("accept") or ""):
        return StreamingResponse(_ask_stream(**kw), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    return clean_response(answer_question(**kw))


@app.post("/api/intake")
def intake(req: IntakeReq) -> dict[str, Any]:
    maybe_reload()
    text = (req.text or "").strip()
    if len(text) < 2:
        raise HTTPException(400, "请再说得具体一点")
    ranked = rank(text)
    top, top_score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0
    ambiguous = top_score < 100 and (top_score - second) < AMBIGUOUS_GAP
    matched = top_score >= MATCH_THRESHOLD

    return {
        "matched": matched,
        "ambiguous": ambiguous,
        "band": "high" if top_score >= 75 else "low",
        "confidence": round(min(top_score, 100) / 100, 2),
        "item": public(top) if matched else None,
        "ask": top.get("slots", []) if matched else [],
        "alternatives": [
            {"id": i["id"], "title": i["title"], "score": s, "status": i.get("status")}
            for i, s in ranked[:3]
            if s > 0
        ],
        "reason": "别名精确命中" if top_score >= 95 else ("别名近似命中" if matched else "未命中任何事项"),
    }


@app.post("/api/deliver")
def deliver(req: DeliverReq) -> dict[str, Any]:
    maybe_reload()
    item = next((i for i in ITEMS if i["id"] == req.item_id), None)
    if not item:
        raise HTTPException(404, "没有这个事项")
    payload = public(item)
    payload["slots_filled"] = req.slots

    draft = item.get("draft")
    if draft:
        text = draft["template"]
        for k, v in req.slots.items():
            text = text.replace(f"【{k}】", v)

        # 【情况说明】只认确定性模板。拼不出来就留占位符让人自己填。
        # 理由：实测模型会自行编造起因（如"个人课程安排冲突"），
        # 文书里出现一个不存在的理由，比留空危险得多。
        reason_text = ""
        reason = draft.get("reason")
        if reason:
            filled = reason
            for k, v in req.slots.items():
                filled = filled.replace(f"【{k}】", v)
            if "【" not in filled:
                reason_text = filled
        placeholder = "【请补充具体原因】"
        text = text.replace("【情况说明】", reason_text.rstrip("。") if reason_text else placeholder)
        payload["draft"] = {
            "title": draft["title"],
            "text": text,
            "complete": bool(reason_text),
            "filled_by": "template" if reason_text else "user",
        }
    else:
        payload["draft"] = None

    return payload


@app.post("/api/verify")
def verify(req: VerifyReq) -> dict[str, Any]:
    maybe_reload()
    item = next((i for i in ITEMS if i["id"] == req.item_id), None)
    if not item:
        raise HTTPException(404, "没有这个事项")
    if not api_key():
        raise HTTPException(503, "未配置 DEEPSEEK_API_KEY，拍照核对不可用")
    if not req.image.startswith("data:image/"):
        raise HTTPException(400, "请上传图片")

    names = req.materials or [m["name"] for m in item.get("materials", [])]
    prompt = (
        f"这是办理「{item['title']}」需要带的材料清单：{json.dumps(names, ensure_ascii=False)}。\n"
        "请看这张照片里都有什么，逐项判断清单上的每一项是否出现在照片中。\n"
        "只输出 JSON：{\"checks\":[{\"name\":\"材料名\",\"status\":\"有|缺|看不清\",\"note\":\"一句话依据\"}],"
        "\"summary\":\"一句话总结还缺什么\"}\n"
        "看不清就写「看不清」，不要猜。不存在于清单的物件不必列出。"
    )
    raw = ds_chat(
        [
            {"role": "system", "content": "你是办事材料核对助手。严格按 JSON 输出，不臆测。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": req.image, "detail": "low"}},
                ],
            },
        ],
        max_tokens=800,
        json_mode=True,
    )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(502, f"模型输出不是合法 JSON：{raw[:200]}")
    return parsed


@app.get("/")
def index(request: Request) -> RedirectResponse:
    # 首次进入直接落到手机端向导页；双栏工作台挪到 /desk。
    # 用 302 而不是永久重定向，入口以后想改不会被浏览器缓存住。
    # 查询串原样带过去：/?q=我要开个证明 这类演示与分享链接要照常能提问。
    query = request.url.query
    return RedirectResponse(url=f"/field?{query}" if query else "/field", status_code=302)


@app.get("/desk")
def desk() -> FileResponse:
    return FileResponse(
        ROOT / "web-next" / "index.html",
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.get("/classic")
def classic() -> FileResponse:
    return FileResponse(
        ROOT / "web-next" / "classic.html",
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.get("/field")
def field() -> FileResponse:
    return FileResponse(
        ROOT / "web-next" / "field.html",
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.exception_handler(HTTPException)
def http_err(_req, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


# 新版界面（web-next）直接由 FastAPI 托管；旧版留在 /classic。
# 挂在最后，API 路由先匹配，静态资源不会抢 /api/*。
app.mount("/", StaticFiles(directory=ROOT / "web-next", html=True), name="ui")
