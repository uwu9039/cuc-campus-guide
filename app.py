"""
校园办事向导 · 后端
- 意图识别：别名表 + 关键词打分（确定性，不走模型）
- 交付物生成：items.json 直接装配（确定性）
- 文书草稿：模板填槽；配了 Key 才用模型润色
- 拍照核对：deepseek-flash 视觉（可选）
"""
from __future__ import annotations

import base64
import gzip
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
from fastapi.staticfiles import StaticFiles
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
    global _WZY_SIBS
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
    r"资格|成绩|绩点|学费|费用|政策|规定|办法|细则|文件|方案|难|双学位|辅修|保研|推免|交换|出国"
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
    "申请", "办理", "流程", "材料", "时间", "地点", "条件", "要求", "手续",
    "报名",
}

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
    blocked = blocked or set()
    best = 0
    is_text = bool(item.get("clause") or item.get("para"))
    keys = [item["title"], core_title(item["title"]), *item.get("aliases", [])]
    for raw in keys:
        a = norm(raw)
        if not a or a in blocked or a in GENERIC_KEYWORDS:
            continue
        if a == q:
            return 100
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
    a = item.get("answer") or ""
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
        if action_q and it["id"] in ("campus-louming", "campus-jiancheng"):
            sc = min(sc, MATCH_THRESHOLD - 1)
        if it.get("clause") or it.get("para"):
            # 问句就是这条原文的标题时，别压到结构化条目下面：
            # 「…微专业招生对象及条件」点进来就该答那一面。
            if sc < 100 and core_best >= MATCH_THRESHOLD:
                sc = min(sc, MATCH_THRESHOLD - 1)
        elif it.get("auto") and hand_best >= sc - 12:
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
        "qr": item.get("qr") or [],
        "pdf": item.get("pdf") or [],
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
    ("hours", "办理时间", r"几点|什么时间|什么时候能办|周几|哪个时段|工作日|周末|上班|开放时间|开馆|闭馆|营业时间|开门|关门|到几点|办公时间|办理时间|服务时间|工作时间|就诊时间"),
    ("location", "办理地点", r"在哪|哪里|哪个楼|去哪儿|地点|几层"),
    ("material", "要带什么", r"带什么|材料|要准备|需要带|证件|照片"),
    ("amount", "数量", r"几本|多少本|多少册|借多少|几张|几份|几个名额"),
    ("duration", "多久出结果", r"多久|几天|多长时间|当场|立等"),
    ("pitfalls", "容易白跑的情况", r"白跑|坑|失败|出错|被拒|注意|办不成"),
    ("steps", "办理流程", r"怎么办|流程|步骤|怎么弄|如何|怎么操作|预约|办卡|报名|怎么申请|报销|怎么报|如何报|缴费|交费|缴纳|怎么交|放假|寒假|暑假|开学|校历"),
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
    # 问的是「带什么材料」，别把整段流程也铺上来；明确问流程时才两样都给
    if "material" in hits and "steps" in hits and not re.search(
            r"怎么办|流程|步骤|如何|怎么|预约|放假", text):
        hits.remove("steps")
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
            ("wendao-index.json", "问道原文"), ("wendao-extra-index.json", "问道原文"),
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
    """按已知条件筛掉不适用分支；一个条件都没给时把各分支原样列出，别交白卷。"""
    rows = item.get("steps") or []
    out = []
    for s in rows:
        cond = s.get("if")
        if cond and not all(known.get(k) == v for k, v in cond.items()):
            continue
        out.append(s)
    return out or rows


def _applicable_steps(item: dict[str, Any], known: dict[str, str]) -> list[str]:
    return [s["what"] for s in _applicable_step_rows(item, known)]


def _narrow_steps(text: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """只按步骤显式标注的 tags 收窄，别拿字面重合去猜——猜错就漏掉另一支。"""
    if len(rows) <= 2 or not (text or "").strip():
        return rows
    # 带 if 的是并列分支，不是先后步骤，按关键词砍掉一支会把另一种情况答错
    if any(isinstance(s, dict) and s.get("if") for s in rows):
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
    return [s for n, s in scored if n >= top - 1]


def _answer_one(item: dict[str, Any], focus: str, known: dict[str, str] | None = None,
                text: str = "") -> dict[str, Any]:
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
        rows = _narrow_steps(text, _applicable_step_rows(item, known or {}))
        steps = [s["what"] for s in rows]
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
        rows = _narrow_steps(text, _applicable_step_rows(item, known or {}))
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


def llm_route(
    text: str, candidates: list[tuple[dict[str, Any], int]]
) -> tuple[dict[str, Any] | None, list[str]]:
    """规则拿不准时，让模型先把问题翻译成多种校园说法，再在候选里挑。

    只做「翻译 + 挑一个」，不生成任何事实。模型给的改写会拿回规则里重新检索，
    用来补上候选池没覆盖到的条目。默认关闭，需要 ROUTER_LLM=1；
    模型异常一律当没选，不影响原有回答。
    """
    if not candidates:
        return None, []
    menu = "\n".join(
        f"- {i['id']}：{i['title']}（别名：{'、'.join((i.get('aliases') or [])[:4])}）"
        for i, _ in candidates
    )
    prompt = (
        "用户在问校园办事的事。请先把他的问题翻译成 3～5 种校园里常用的说法，"
        "再判断下列候选中是否有唯一最匹配的一项。\n"
        f"{menu}\n\n"
        "翻译要求：\n"
        "- 口语改书面，同义替换，补全省略的主语或对象。\n"
        "- 用词贴近学校文件，例如「宿舍换一下」→「调宿申请」「转宿舍办理」；"
        "「卡丢了」→「校园卡挂失」；「成绩单在哪开」→「成绩证明办理」。\n"
        "- 一条只表达一个意思，不超过 24 个字，不要重复原句。\n"
        "判断要求：只挑一个候选；都不匹配 id 返回 null；不要解释。\n"
        '只输出 JSON：{"rewrites": ["…"], "id": "候选id或null"}'
    )
    try:
        raw = ds_chat(
            [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            max_tokens=220,
            json_mode=True,
        )
        data = json.loads(raw) or {}
    except Exception:  # noqa: BLE001
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


ASSOC_MIN = 70   # 联想改写在规则里重新检索，至少要命中标题/别名才认
ASSOC_GAP = 5    # 且要与第二名拉开差距，避免拿改写去猜


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


def llm_free_answer(text: str) -> dict[str, Any] | None:
    """事项库一条都没对上时，才让模型直接回答。

    只由 miss 分支调用；命中了任何条目的问答路径不经过这里，
    所以已有条目的回答不受影响。生成内容只随响应返回，不写进 items.json。
    """
    prompt = (
        "你在帮中国传媒大学的同学回答校园办事问题。事项库里没有收录这个问题，"
        "请直接给出可执行的回答：先给结论，再给要准备的东西和该去哪个部门办。\n"
        "要求：\n"
        "- 不确定的细节（电话、金额、截止日期、文件条款号）一律不要编，写「以学校最新通知为准」。\n"
        "- 不要声称这是学校原文，不要伪造文件名、链接或文号。\n"
        "- 确实不知道就直说，并指出大概该问哪个部门。\n"
        '只输出 JSON：{"answer": "…", "confidence": "low|medium|high", "caveat": "…"}'
    )
    try:
        raw = ds_chat(
            [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            max_tokens=700,
            json_mode=True,
        )
        data = json.loads(raw) or {}
    except Exception:  # noqa: BLE001
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
        "disclaimer": "以下内容由大模型直接生成，没有经过事项库和官方原文核对。",
    }


def with_free_answer(resp: dict[str, Any], text: str, llm_on: bool) -> dict[str, Any]:
    if llm_on:
        gen = llm_free_answer(text)
        if gen:
            resp["llm_answer"] = gen
    return resp


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
    # 微专业名里常带「数智」「传播」这类学院/专业词，且「招生对象及条件」
    # 会命中 plan_words；不能让微专业的问法落到转专业接收计划上。
    if "微专业" in text:
        return None
    strong = bool(re.search(r"转专业|转入|转到|转去|转进|换专业|接收计划|接收条件", text))
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


def original_hits(text: str, k: int = 3, min_score: float = 0.28) -> list[dict[str, Any]]:
    """规则没命中时，去原文向量库找几段；只给原文线索，不生成事实。"""
    try:
        import vector_index

        return vector_index.search(text, k=k, min_score=min_score)
    except Exception:
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


def rerank_candidates(
    text: str, ranked: list[tuple[dict[str, Any], int]], limit: int = 14
) -> list[tuple[dict[str, Any], int]]:
    """规则前排 + 向量命中文档里的条目，合成给模型判断的候选池。

    规则只按关键词打分，问「游泳馆开放时间」会被「图书馆开放时间」抢走；
    向量能捞到游泳馆那段原文，再由模型判断哪条真的回答了问题。
    """
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
    for h in original_hits(text, k=8, min_score=0.18):
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


RERANK_MIN = 75     # 模型判定「真的回答了问题」的最低分
RERANK_MARGIN = 10  # 换掉规则首选，必须比规则首选高出这么多


def _rerank_hint(item: dict[str, Any]) -> str:
    text = item.get("answer") or ""
    if not text:
        for s in item.get("steps") or []:
            text = str(s.get("what") or "")
            if text:
                break
    return text.replace("\n", " ")[:70]


def llm_rerank(
    text: str, pool: list[tuple[dict[str, Any], int]]
) -> tuple[dict[str, Any] | None, list[str]]:
    """让 DeepSeek Flash 判断候选里哪条真的回答了问题，并给出校园说法改写。

    这是判断层，不生成事实：只打分、挑条目；改写拿回规则里二次检索。
    """
    menu = "\n".join(
        f"- {it['id']}｜{it['title'][:50]}｜{'原文摘录' if it.get('auto') else '整理条目'}"
        f"｜{it.get('dept') or '—'}｜{_rerank_hint(it) or '（无摘要）'}"
        for it, _ in pool
    )
    prompt = (
        "用户在问校园办事的事。下面是从知识库检索出的候选条目。\n"
        f"{menu}\n\n"
        "判断要求：\n"
        "- 给每条打 0～100：100=直接回答了用户问的这件事；60=沾边但缺关键信息；0=无关。\n"
        "- 只看关键词重合不算回答。用户问 A，条目讲 B，就是 0 分。\n"
        "- 同一件事既有「整理条目」又有「原文摘录」时，优先选整理条目：它分好了费用、时间、材料，"
        "能回答具体问法；原文摘录只在整理条目完全没覆盖这件事时才选。\n"
        "- best 只能填真正回答了问题的条目 id；都没有就填 null，不要硬选。\n"
        "改写要求：把用户问题翻译成 3～5 种校园里的常用说法，口语改书面、补全省略，"
        "一条只表达一个意思，不超过 24 个字。\n"
        '只输出 JSON：{"scores": {"条目id": 分数}, "best": "条目id或null", '
        '"why": "一句话理由", "rewrites": ["…"]}'
    )
    try:
        raw = ds_chat(
            [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            max_tokens=480,
            json_mode=True,
        )
        data = json.loads(raw) or {}
    except Exception:  # noqa: BLE001
        return None, []
    if not isinstance(data, dict):
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
    best_id = str(data.get("best") or "").strip()
    best = ITEM_BY_ID.get(best_id) if best_id and best_id != "null" else None
    if best is None:
        return None, rewrites
    return {
        "item": best,
        "score": scores.get(best["id"], RERANK_MIN),
        "scores": scores,
        "why": str(data.get("why") or "").strip()[:160],
    }, rewrites


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


def _menu_dept(item: dict[str, Any]) -> str:
    d = (item.get("dept") or "").strip()
    if d and d != "中国传媒大学":
        return d
    srcs = item.get("source") or []
    if srcs:
        t = re.split(r"\s*·\s*", str(srcs[0].get("title") or ""))[0].strip()
        return t[:24] + ("…" if len(t) > 24 else "")
    return d


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
        out.append({"id": it["id"], "title": it["title"], "label": _menu_label(it["title"]),
                    "dept": _menu_dept(it), "hint": (it.get("aliases") or [""])[0]})
        seen.add(norm(core_title(it["title"])))   # 同名的原文摘录只留一条
    return out


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
            "clarify": menu.get("clarify") or f"「{token}」相关问题，先点一个：",
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
        seen.add(key)
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
    }


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


def answer_question(text: str, given: dict[str, str] | None = None,
                    router_llm: bool | None = None) -> dict[str, Any]:
    llm_on = (os.getenv("ROUTER_LLM") == "1") if router_llm is None else router_llm
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
    tp = transfer_plan(text)
    clarify = _transfer_clarify(text, tp, map_hit)
    if clarify:
        return clarify

    # 单个词：先把相关事项全摊成选项（地点词的第一项是「在哪」，仍走地点卡）
    menu = _topic_menu(text)
    if menu:
        if places and _place_exact(text, places):
            menu["item"] = public(_named_place_item(places) or place_item(places))
            menu["map"] = map_hit
        return menu

    # 只问地点：直接答点到的这一处，不再端出整张对照表，也不让转专业路由抢走
    # 例外：这个地点本身分几种情况（快递驿站分校内 / 梆子井），先问清再答，
    # 否则只会报一个点位，另一处的答案被吞掉。
    if places and not place_slot and _place_exact(text, places) and (
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
    if PLACE_ONLY.search(text) and not place_slot and "在哪" not in top["title"]:
        for cand, cand_score in ranked[:4]:
            if cand["id"] in ("campus-louming", "campus-jiancheng") and cand_score >= 70:
                top, score, second = cand, cand_score, 0
                place_forced = True
                break

    # 规则拿不准时，若开启 LLM 兜底，让模型在候选里选（只选，不生成事实）。
    # 比旧版多做一步：候选池除了规则前排，还从向量命中的原文段落反查条目，
    # 由 DeepSeek Flash 判断哪条真的回答了问题，而不是只看关键词重合。
    # 90 分以上、问句又够长的强命中不送模型，避免把已经答对的条目改坏。
    top_title = core_title(top["title"]) if top else ""
    rival = next((sc for it, sc in ranked[1:]
                  if core_title(it["title"]) != top_title), 0)
    risky = score < MATCH_THRESHOLD or (rival > 0 and score - rival < 8 and score < 90)
    informative = len(text.strip()) >= 6
    resolved_by_llm = False
    rerank_info: dict[str, Any] | None = None
    if llm_on and informative and score < 96 and not place_forced:
        rule_top_id = top["id"]
        pool = rerank_candidates(text, ranked)
        rewrites: list[str] = []
        rr = None
        if len(pool) >= 2:
            rr, rewrites = llm_rerank(text, pool)
        if rr is not None:
            best = rr["item"]
            bsc = rr["score"]
            rule_llm = rr["scores"].get(rule_top_id, 0)
            better = bool(best) and bsc >= RERANK_MIN and (
                score < MATCH_THRESHOLD
                or (best["id"] != rule_top_id and bsc - rule_llm >= RERANK_MARGIN)
            )
            if better and best["id"] != rule_top_id:
                top, score = best, max(score, bsc)
                second = 0
                resolved_by_llm = True
            rerank_info = {
                "used": True,
                "pool": len(pool),
                "rule_top": rule_top_id,
                "best": best["id"] if best else None,
                "score": bsc if best else 0,
                "rule_score": rule_llm,
                "changed": resolved_by_llm,
                "why": rr.get("why") or "",
            }
        elif risky:
            # rerank 不可用时退回旧路：先让模型翻译，再拿改写回规则检索
            picked, rewrites = llm_route(text, ranked[:8])
            if picked is not None:
                top = picked
                score = max(score, MATCH_THRESHOLD + 1)
                second = 0
                resolved_by_llm = True
        if not resolved_by_llm and rewrites and score < MATCH_THRESHOLD:
            # 只有规则本身答不上来时，才用模型翻译出的校园说法重新检索；
            # 规则已经强命中（如「补考成绩怎么记」93 分）时不再拿改写去换条目。
            assoc = assoc_pick(rewrites)
            if assoc is not None and assoc[0]["id"] != top["id"]:
                top, score = assoc
                second = 0
                resolved_by_llm = True

    # 没到阈值但候选分数不低：不硬拒，给出"是不是这个"的选择题
    # 自动抽取的制度卡片不参与选择题：两个同名文件让用户选，等于没答
    alt_rows = distinct_rows([(i, sc) for i, sc in ranked[:6]
                              if sc >= 38 and not i.get("auto")])
    near = alt_rows[:3]
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
            "rerank": rerank_info,
        }

    if score < MATCH_THRESHOLD:
        base = {
            "matched": False,
            "query": text,
            "normalized": None,
            "topic": text.strip()[:24],
            "map": map_hit,
            "hints": dept_hints(text),
            "contacts": related_contacts(text),
            "rerank": rerank_info,
            "alternatives": [
                {"id": i["id"], "title": i["title"]}
                for i, s in alt_rows[:3]
            ],
            "next_actions": [
                "换个更具体的说法，比如「校园卡补卡」「开成绩单」",
                "按上面的归口部门查最新通知，或直接打公开电话",
                "找到官方通知后发我，我按原文做成条目",
            ],
            "suggestion": "你要是有这一项的官方页面或通知，发我，我做成带原文的条目。",
            "confidence": round(score / 100, 2),
            "band": "none",
            "focus": [],
            "quotes": [],
            "answers": [{
                "focus": "overview",
                "label": "知识库未收录",
                "text": None,
                "steps": [],
                "quotes": [],
                "found": False,
            }],
        }
        hits = original_hits(text)
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
                {"id": iid, "title": (ITEM_BY_ID.get(iid) or {}).get("title", iid)}
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
                    for i, _ in distinct_rows(ranked[:3])
                ],
                **sensitivity(text),
                "router_llm": llm_on,
                "rule_unsure": risky,
            })
            return with_free_answer(base, text, llm_on)
        if CAMPUS_HINT.search(text):
            near_opts = [
                {"id": i["id"], "title": i["title"], "dept": i.get("dept", ""),
                 "hint": (i.get("aliases") or [""])[0]}
                for i, _ in alt_rows[:3]
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
        return with_free_answer(base, text, llm_on)

    # 同一族事项分数咬得很紧时先问清是哪一类，别硬猜；
    # 但如果句子里同时点了地点，地点只是背景，选办这件事的条目（别拿楼宇速查去反问答不上）
    rivals = distinct_rows([(i, sc) for i, sc in ranked[:5]
                            if sc >= MATCH_THRESHOLD and not i.get("auto")])
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
                "rerank": rerank_info,
                "focus": [],
                "quotes": [],
                "related": _related_items(text, top),
                "map": map_hit,
            }

    focus = detect_focus(text, top)
    known0 = {**_known_slots(text, top), **(given or {})}
    parts = [_answer_one(top, f, known0, text) for f in focus]
    found = [p for p in parts if p["found"]]
    missing = [p["label"] for p in parts if not p["found"]]

    known = {**_known_slots(text, top), **(given or {})}
    focus_keys = [p["focus"] for p in parts]
    followups = _followups(top, focus_keys, known)
    blocked = [f for f in followups if f["blocks"]]

    # 反问不能让用户一无所获：把不依赖分支的通用答复先端出来，
    # 具体分支等用户回答后再补（如成绩单先给线上自助下载，再问要不要密封）。
    if blocked:
        base_part = _answer_one(top, "overview", known, text)
        if base_part["found"]:
            parts = [base_part]
            focus_keys = ["overview"]
            missing = []
        else:
            decided = {k for f in blocked for k in f.get("decides") or []}
            parts = [p for p in parts if p["found"] and p["focus"] not in decided]
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

    # 判「是否还有别的可选」时按去重后的候选算，同名自动卡片不算第二选项
    second_clean = 0 if resolved_by_llm else next((sc for _, sc in distinct_rows(ranked[:3])[1:2]), 0)
    # 还在反问、或问的是另一个园区时，别把地图定到校内那个点
    show_map = None if blocked or (map_hit and known.get("campus") not in (None, "", "校内")) else map_hit
    return {
        "matched": True,
        "query": text,
        **sensitivity(text),
        "router_llm": llm_on,
        "resolved_by_llm": resolved_by_llm,
        "rerank": rerank_info,
        # 已经在反问用户了，就不再说「规则没把握」——两句话叠在一起自相矛盾；
        # 地点分支条目（快递驿站）问清园区后给出的答案不再提示没把握
        "rule_unsure": risky and not blocked and not place_slot,
        "normalized": normalized,
        "confidence": round(min(score, 100) / 100, 2),
        "band": "high" if score >= 75 else "low",
        "ambiguous": score < 100 and (score - second_clean) < AMBIGUOUS_GAP,
        "item": public(top),
        "answers": parts,
        "focus": focus_keys,
        "hold": bool(blocked),
        "followups": followups,
        "known": known,
        "quotes": quotes,
        "missing": missing,
        "note": (f"官方页面没有写「{'、'.join(missing)}」，我不替它编。" if missing else None),
        "related": _related_items(text, top),
        "map": show_map,
    }


class AskReq(BaseModel):
    text: str
    slots: dict[str, str] = {}
    router_llm: bool | None = None   # None=按环境变量；界面开关传 true/false


@app.post("/api/ask")
def ask(req: AskReq) -> dict[str, Any]:
    maybe_reload()
    text = (req.text or "").strip()
    if len(text) < 2 and not NUM_ONLY.match(text):
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
        ROOT / "web-next" / "index.html",
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.get("/classic")
def classic() -> FileResponse:
    return FileResponse(
        ROOT / "index.html",
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.exception_handler(HTTPException)
def http_err(_req, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


# 新版界面（web-next）直接由 FastAPI 托管；旧版留在 /classic。
# 挂在最后，API 路由先匹配，静态资源不会抢 /api/*。
app.mount("/", StaticFiles(directory=ROOT / "web-next", html=True), name="ui")
