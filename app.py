"""
校园办事向导 · 后端
- 意图识别：别名表 + 关键词打分（确定性，不走模型）
- 交付物生成：items.json 直接装配（确定性）
- 文书草稿：模板填槽；配了 Key 才用模型润色
- 拍照核对：deepseek-flash 视觉（可选）
"""
from __future__ import annotations

import base64
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

ROOT = Path(__file__).parent
API_BASE = "https://api.deepseek.com"
MODEL = "deepseek-flash"
MATCH_THRESHOLD = 55
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
DATA = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
ITEMS: list[dict[str, Any]] = DATA["items"]
DATA_UPDATED = DATA.get("updated", "")
_MTIME = (ROOT / "items.json").stat().st_mtime


def maybe_reload() -> None:
    """改了 items.json 不用重启服务。"""
    global DATA, ITEMS, DATA_UPDATED, _MTIME
    mtime = (ROOT / "items.json").stat().st_mtime
    if mtime == _MTIME:
        return
    DATA = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    ITEMS = DATA["items"]
    DATA_UPDATED = DATA.get("updated", "")
    _MTIME = mtime


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
    "校医院": ("校医院", "校医院（20号楼）"),
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
    if not path.exists():
        return {"pois": [], "center": None, "count": 0}
    extra = ROOT / "campus-map.json"
    mtime = path.stat().st_mtime + (extra.stat().st_mtime if extra.exists() else 0)
    if _CAMPUS is None or mtime != _CAMPUS_MTIME:
        _CAMPUS = _merge_campus_coords(json.loads(path.read_text(encoding="utf-8")))
        _CAMPUS_MTIME = mtime
    return _CAMPUS


PLACE_ASK = re.compile(r"在哪|在哪里|在哪儿|在哪个楼|怎么走|怎么去|位置|路线|导航")
_PLACE_SUFFIX = re.compile(r"(在哪里|在哪儿|在哪|在哪个楼|的位置|位置|怎么走|怎么去|路线|导航|呢|啊|呀)+$")

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


# ---------------------------------------------------------------- matching

PUNCT = re.compile(r"[\s，。！？、；：\"'“”‘’（）()【】\[\]—…·.,!?;:]")


def norm(s: str) -> str:
    return PUNCT.sub("", (s or "").lower())


def bigrams(s: str) -> set[str]:
    return {s[i : i + 2] for i in range(len(s) - 1)}


TRAILING_PAREN = re.compile(r"[（(][^（()）]*[）)]\s*$")


def core_title(title: str) -> str:
    """去掉标题尾部括号补充：「公共实践场馆预约（演播馆 / 音乐厅）」→「公共实践场馆预约」。"""
    t = title or ""
    while True:
        nxt = TRAILING_PAREN.sub("", t).strip()
        if nxt == t:
            return t
        t = nxt


def score_item(q: str, item: dict[str, Any], blocked: set[str] | None = None) -> int:
    if not q:
        return 0
    blocked = blocked or set()
    best = 0
    keys = [item["title"], core_title(item["title"]), *item.get("aliases", [])]
    for raw in keys:
        a = norm(raw)
        if not a or a in blocked:
            continue
        if a == q:
            return 100
        if a in q:
            best = max(best, 82 + min(10, len(a)))
        elif q in a:
            best = max(best, 70 + min(8, len(q)))

    # 关键词层：命中越多越可信（「校园卡+挂失+解挂」应当压过泛泛的「校园卡」）
    hits = 0
    kw_best = 0
    for raw in item.get("keywords", []):
        k = norm(raw)
        if k and k not in blocked and k in q:
            hits += 1
            kw_best = max(kw_best, 84 + min(8, len(k)))
    if hits:
        best = max(best, kw_best + (hits - 1) * 7)

    # 二元组相似度兜底（同义改写）
    qb = bigrams(q)
    if qb:
        for raw in [*keys, *item.get("keywords", [])]:
            a = norm(raw)
            if len(a) < 2 or a in blocked:
                continue
            ab = bigrams(a)
            if not ab:
                continue
            dice = 2 * len(qb & ab) / (len(qb) + len(ab))
            if dice >= 0.34:
                best = max(best, int(40 + 30 * dice))
    return best


def blocked_keys(qn: str) -> dict[str, set[str]]:
    """长词优先：短词只出现在长词内部时不算数。

    「保留学籍」里的「留学」不能把问题推给出国留学；
    「勤工助学」里的「助学」同理。同一短词在别处独立出现时仍然有效。
    """
    occ: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for it in ITEMS:
        if it.get("archive_only"):
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


def rank(q: str) -> list[tuple[dict[str, Any], int]]:
    qn = norm(q)
    blocked = blocked_keys(qn)
    # archive_only：存档条目（如转专业接收计划附件）只入库、不参与问答路由
    scored = [(it, score_item(qn, it, blocked.get(it["id"])))
              for it in ITEMS if not it.get("archive_only")]
    # 自动抽取的制度卡片只是资料，不抢人工整理的服务条目：
    # 分数接近时让人工条目胜出；差距很大（如直接问办法原文）仍返回原文条目。
    hand_best = max((sc for it, sc in scored if not it.get("auto")), default=0)
    adjusted = []
    for it, sc in scored:
        if it.get("auto") and hand_best >= sc - 12:
            sc = max(0, sc - 12)
        adjusted.append((it, sc))
    # 同分时人工条目优先，避免同年份的制度卡片把服务条目挤下去
    return sorted(adjusted, key=lambda x: (-x[1], bool(x[0].get("auto"))))


def public(item: dict[str, Any]) -> dict[str, Any]:
    return {
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
        "source": item.get("source", []),
        "slots": item.get("slots", []),
        "answer": item.get("answer"),
        "note": item.get("note"),
        "advisory": item.get("advisory", []),
        "evidence": item.get("evidence", {}),
    }


# ---------------------------------------------------------------- deepseek


def ds_chat(
    messages: list[dict[str, Any]],
    max_tokens: int = 600,
    json_mode: bool = False,
    thinking: bool = False,
) -> str:
    """deepseek-flash 默认开思考模式，会先烧 max_tokens，短任务必须关掉。

    thinking=True 时不发 temperature（该模式忽略它）。
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
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise HTTPException(502, f"模型接口返回 {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"模型接口调用失败: {e}")
    return payload["choices"][0]["message"]["content"]


# ---------------------------------------------------------------- app

app = FastAPI(title="校园办事向导", version="0.1")


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
    """独立原文检索：按语义近似找段落，只返回原文与出处，不生成答案。"""
    q = (q or "").strip()
    if len(q) < 2:
        raise HTTPException(400, "请再说得具体一点")
    try:
        import vector_index

        hits = vector_index.search(q, k=max(1, min(k, 20)), min_score=0.15)
        counts = vector_index.stats()
    except Exception as e:  # 向量库未建好时明确告知，不静默降级
        raise HTTPException(503, f"原文库未就绪：{e}")
    return {"query": q, "total": len(hits), **counts, "hits": hits}


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
    ("fee", "费用", r"多少钱|多少钱啊|收费|费用|工本费|免费|贵"),
    ("window", "办理时限", r"截止|什么时候前|过期|来得及|有效期|多久内"),
    ("hours", "办理时间", r"几点|什么时间|什么时候能办|周几|哪个时段|工作日|周末|上班"),
    ("location", "办理地点", r"在哪|哪里|哪个楼|去哪儿|地点|几层"),
    ("material", "要带什么", r"带什么|材料|要准备|需要带|证件|照片"),
    ("duration", "多久出结果", r"多久|几天|多长时间|当场|立等"),
    ("pitfalls", "容易白跑的情况", r"白跑|坑|失败|出错|被拒|注意|办不成"),
    ("steps", "办理流程", r"怎么办|流程|步骤|怎么弄|如何|怎么操作"),
]

FOCUS_LABEL = {k: label for k, label, _ in FOCUS_RULES}


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
    """返回最多两个聚焦点，按规则顺序（越具体越靠前）。"""
    hits: list[str] = []
    for key, _label, pattern in FOCUS_RULES:
        if re.search(pattern, text):
            hits.append(key)
    # 太泛的问法（只问"怎么办"）就回到整体
    if not hits or hits == ["steps"]:
        return ["overview"]
    return hits[:2]


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
                    _SRC_META[key] = {"label": lab, "kind": kind,
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


def _applicable_steps(item: dict[str, Any], known: dict[str, str]) -> list[str]:
    """按已知条件筛掉不适用分支，只留这个人要走的那几步。"""
    out = []
    for s in item.get("steps", []):
        cond = s.get("if")
        if cond and not all(known.get(k) == v for k, v in cond.items()):
            continue
        out.append(s["what"])
    return out


def _answer_one(item: dict[str, Any], focus: str, known: dict[str, str] | None = None) -> dict[str, Any]:
    """从结构化数据 + 原文引文里拼出这一面的答案。"""
    ev = item.get("evidence") or {}
    sources = {s["url"] for s in item.get("source", [])}

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
        steps = _applicable_steps(item, known or {})
        answer = item.get("answer")
        return {
            "focus": "overview",
            "label": "官方答复" if answer else "整体流程",
            "text": answer or (" → ".join(steps) if steps else "官方页面没有给出可执行步骤。"),
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
        rows = []
        for s in item.get("steps") or []:
            cond = s.get("if")
            if cond and not all((known or {}).get(k) == v for k, v in cond.items()):
                continue
            rows.append(s)
        return {
            "focus": focus,
            "label": FOCUS_LABEL[focus],
            "text": " → ".join(s.get("what", "") for s in rows) if rows else None,
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
        for opt in s.get("options", []):
            cands = [opt, *(hints.get(opt) or [])]
            if any(norm(c) and norm(c) in q for c in cands):
                known[s["key"]] = opt
                break
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


def llm_route(text: str, candidates: list[tuple[dict[str, Any], int]]) -> dict[str, Any] | None:
    """规则拿不准时，让模型只在候选里挑一个（不生成任何事实）。

    默认关闭，需要 ROUTER_LLM=1。模型返回 null 或异常一律当没选。
    """
    if not candidates:
        return None
    menu = "\n".join(
        f"- {i['id']}：{i['title']}（别名：{'、'.join((i.get('aliases') or [])[:3])}）"
        for i, _ in candidates
    )
    prompt = (
        "用户在问校园办事的事。请从下列候选中挑出唯一最匹配的一项。\n"
        f"{menu}\n\n"
        "要求：只挑一个；都不匹配就返回 null；不要解释。"
        '只输出 JSON：{"id": "候选id或null"}'
    )
    try:
        raw = ds_chat(
            [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            max_tokens=80,
            json_mode=True,
        )
        picked = (json.loads(raw) or {}).get("id")
    except Exception:  # noqa: BLE001
        return None
    for i, _ in candidates:
        if i["id"] == picked:
            return i
    return None


def llm_pick_line(text: str, item: dict[str, Any], lines: list[Any]) -> int | None:
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
        picked = (json.loads(raw) or {}).get("line")
    except Exception:  # noqa: BLE001
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
    if PLACE_ASK.search(text) and not strong:
        return None
    soft = bool(re.search(r"转|换", text))
    plan_words = bool(re.search(r"条件|要求|接收|计划|考核|材料|联系|能不能|可以转|想学|想读", text))
    colleges, majors = _find_entities(text)
    qn = _mn(text)
    if not (strong or soft or (majors and plan_words)) or (not colleges and not majors):
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


def original_hits(text: str, k: int = 3, min_score: float = 0.28) -> list[dict[str, Any]]:
    """规则没命中时，去原文向量库找几段；只给原文线索，不生成事实。"""
    try:
        import vector_index

        return vector_index.search(text, k=k, min_score=min_score)
    except Exception:
        return []


def answer_question(text: str, given: dict[str, str] | None = None,
                    router_llm: bool | None = None) -> dict[str, Any]:
    llm_on = (os.getenv("ROUTER_LLM") == "1") if router_llm is None else router_llm
    places = map_places(text)
    map_hit = places[-1] if places else None

    # 只问地点：直接答点到的这一处，不再端出整张对照表，也不让转专业路由抢走
    if places and (PLACE_ONLY.search(text) or not PLACE_ASK.search(text)):
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
            "item": public(place_item(places)),
            "answers": parts,
            "focus": ["location"],
            "hold": False,
            "followups": [],
            "known": {},
            "quotes": quotes,
            "missing": [],
            "note": (f"官方位置表没有写「{'、'.join(unnamed)}」的具体楼层，这里只给名称、对应楼号和地图定位。"
                     if unnamed else None),
            "map": map_hit,
            **sensitivity(text),
            "router_llm": llm_on,
            "rule_unsure": False,
        }

    tp = transfer_plan(text)
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

    ranked = rank(text)
    top, score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0

    # 纯问地点的短句（「图书馆在哪」）优先给校园地点条目，别落到办这件事的条目上
    place_forced = False
    if PLACE_ONLY.search(text):
        for cand, cand_score in ranked[:4]:
            if cand["id"] in ("campus-louming", "campus-jiancheng") and cand_score >= 70:
                top, score, second = cand, cand_score, 0
                place_forced = True
                break

    # 规则拿不准时，若开启 LLM 兜底，让模型在候选里选（只选，不生成事实）
    # 只在"信息够但规则打平"时让模型裁决；问题太短（如"补卡"）说明用户没说清，应该反问而不是猜
    risky = score < MATCH_THRESHOLD or (len(ranked) > 1 and score - ranked[1][1] < 8)
    informative = len(text.strip()) >= 6
    resolved_by_llm = False
    if risky and informative and llm_on:
        picked = llm_route(text, ranked[:5])
        if picked is not None:
            top = picked
            score = max(score, MATCH_THRESHOLD + 1)
            second = 0
            resolved_by_llm = True

    # 没到阈值但候选分数不低：不硬拒，给出"是不是这个"的选择题
    near = [(i, sc) for i, sc in ranked[:3] if sc >= 38]
    if (not resolved_by_llm) and score < MATCH_THRESHOLD and len(near) >= 2 and (near[0][1] - near[1][1]) < 14:
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
        }

    if score < MATCH_THRESHOLD:
        base = {
            "matched": False,
            "query": text,
            "normalized": None,
            "map": map_hit,
            "hints": dept_hints(text),
            "alternatives": [{"id": i["id"], "title": i["title"]} for i, s in ranked[:3] if s > 0],
            "suggestion": "你要是有这一项的官方页面或通知，发我，我做成带原文的条目。",
        }
        hits = original_hits(text)
        if hits:
            base["original_search"] = hits
            ids: list[str] = []
            for h in hits:
                for iid in h.get("item_ids") or []:
                    if iid not in ids:
                        ids.append(iid)
            related = [
                {"id": iid, "title": next((i["title"] for i in ITEMS if i["id"] == iid), iid)}
                for iid in ids[:3]
            ]
            if related:
                base["related_items"] = related
            base["search_note"] = "规则没对上事项。原文库里这几段可能相关，点开核对原文；没写到的我不补。"
        if STRATEGY.search(text):
            base.update({
                "ambiguous": True,
                "clarify": "选哪条路这种建议，学校文件里没有，我不编。"
                           "你告诉我要办哪件事，我给你文件里的条件和流程：",
                "reason": "这类问题没有原文支撑，转成具体事项",
                "disambiguate": [
                    {"id": i["id"], "title": i["title"], "dept": i.get("dept", ""),
                     "hint": (i.get("aliases") or [""])[0]}
                    for i, _ in ranked[:3]
                ],
                **sensitivity(text),
                "router_llm": llm_on,
                "rule_unsure": risky,
            })
            return base
        if CAMPUS_HINT.search(text):
            base.update({
                "ambiguous": True,
                "clarify": "没对上具体事项。你要办的是下面哪一类？",
                "disambiguate": [
                    {"id": i["id"], "title": i["title"], "dept": i.get("dept", ""),
                     "hint": (i.get("aliases") or [""])[0]}
                    for i, _ in ranked[:3] if _ >= 20
                ] or [
                    {"id": i["id"], "title": i["title"], "dept": i.get("dept", ""),
                     "hint": (i.get("aliases") or [""])[0]}
                    for i in ITEMS
                    if i["id"] in ("jwc-chengjidan", "xyk-buka", "jwc-buxuanke", "jwc-zaidu")
                ],
            })
        base.update({
            **sensitivity(text),
            "router_llm": llm_on,
            "rule_unsure": risky,
        })
        return base

    # 同一族事项分数咬得很紧时先问清是哪一类，别硬猜；
    # 但如果句子里同时点了地点，地点只是背景，选办这件事的条目（别拿楼宇速查去反问答不上）
    rivals = [(i, sc) for i, sc in ranked[:4] if sc >= MATCH_THRESHOLD]
    if (not resolved_by_llm) and not place_forced and len(rivals) >= 2 and (score - rivals[1][1]) < 8:
        if map_hit:
            concrete = [r for r in rivals if not str(r[0].get("id", "")).startswith("campus-")]
            if concrete:
                top, score = concrete[0]
                second = 0
                rivals = []
        if rivals:
            return {
                "matched": True,
                "query": text,
                "normalized": "待确认是哪一类",
                "confidence": round(min(score, 100) / 100, 2),
                "band": "low",
                "ambiguous": True,
                "item": public(top),
                "answers": [],
                "hold": True,
                "followups": [],
                "disambiguate": [
                    {"id": i["id"], "title": i["title"], "dept": i.get("dept", ""),
                     "hint": (i.get("aliases") or [""])[0]}
                    for i, _ in rivals[:3]
                ],
                "clarify": f"你是想问「{rivals[0][0]['title']}」还是「{rivals[1][0]['title']}」？这两个办起来不是一处。",
                **sensitivity(text),
                "router_llm": llm_on,
                "rule_unsure": risky,
                "focus": [],
                "quotes": [],
                "map": map_hit,
            }

    focus = detect_focus(text, top)
    known0 = {**_known_slots(text, top), **(given or {})}
    parts = [_answer_one(top, f, known0) for f in focus]
    found = [p for p in parts if p["found"]]
    missing = [p["label"] for p in parts if not p["found"]]

    known = {**_known_slots(text, top), **(given or {})}
    focus_keys = [p["focus"] for p in parts]
    followups = _followups(top, focus_keys, known)
    blocked = [f for f in followups if f["blocks"]]

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
            idx_line = llm_pick_line(text, top, lines)
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

    normalized = f"{top['title']} · " + "、".join(p["label"] for p in parts)
    quotes: list[dict[str, str]] = []
    seen_q: set[str] = set()
    for p in parts:
        for q in p["quotes"]:
            if q["quote"] not in seen_q:
                seen_q.add(q["quote"])
                quotes.append(q)

    return {
        "matched": True,
        "query": text,
        **sensitivity(text),
        "router_llm": llm_on,
        "rule_unsure": risky,
        "normalized": normalized,
        "confidence": round(min(score, 100) / 100, 2),
        "band": "high" if score >= 75 else "low",
        "ambiguous": score < 100 and (score - second) < AMBIGUOUS_GAP,
        "item": public(top),
        "answers": [] if blocked else parts,
        "focus": focus_keys,
        "hold": bool(blocked),
        "followups": followups,
        "known": known,
        "quotes": quotes,
        "missing": missing,
        "note": (f"官方页面没有写「{'、'.join(missing)}」，我不替它编。" if missing else None),
        "map": map_hit,
    }


class AskReq(BaseModel):
    text: str
    slots: dict[str, str] = {}
    router_llm: bool | None = None   # None=按环境变量；界面开关传 true/false


@app.post("/api/ask")
def ask(req: AskReq) -> dict[str, Any]:
    maybe_reload()
    text = (req.text or "").strip()
    if len(text) < 2:
        raise HTTPException(400, "请再说得具体一点")
    return answer_question(text, req.slots, router_llm=req.router_llm)


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
def index() -> FileResponse:
    return FileResponse(
        ROOT / "index.html",
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.exception_handler(HTTPException)
def http_err(_req, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
