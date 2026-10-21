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
import urllib.error
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


# ---------------------------------------------------------------- matching

PUNCT = re.compile(r"[\s，。！？、；：\"'“”‘’（）()【】\[\]—…·.,!?;:]")


def norm(s: str) -> str:
    return PUNCT.sub("", (s or "").lower())


def bigrams(s: str) -> set[str]:
    return {s[i : i + 2] for i in range(len(s) - 1)}


def score_item(q: str, item: dict[str, Any]) -> int:
    if not q:
        return 0
    best = 0
    keys = [item["title"], *item.get("aliases", [])]
    for raw in keys:
        a = norm(raw)
        if not a:
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
        if k and k in q:
            hits += 1
            kw_best = max(kw_best, 84 + min(8, len(k)))
    if hits:
        best = max(best, kw_best + (hits - 1) * 7)

    # 二元组相似度兜底（同义改写）
    qb = bigrams(q)
    if qb:
        for raw in [*keys, *item.get("keywords", [])]:
            a = norm(raw)
            if len(a) < 2:
                continue
            ab = bigrams(a)
            if not ab:
                continue
            dice = 2 * len(qb & ab) / (len(qb) + len(ab))
            if dice >= 0.34:
                best = max(best, int(40 + 30 * dice))
    return best


def rank(q: str) -> list[tuple[dict[str, Any], int]]:
    scored = [(it, score_item(norm(q), it)) for it in ITEMS]
    return sorted(scored, key=lambda x: -x[1])


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


@app.get("/api/health")
def health() -> dict[str, Any]:
    maybe_reload()
    return {
        "ok": True,
        "items": len(ITEMS),
        "verified": sum(1 for i in ITEMS if i.get("status") == "verified"),
        "model": MODEL,
        "vision": True,
        "key_configured": bool(api_key()),
        "hot_reload": True,
        "data_updated": DATA_UPDATED,
    }


_PRESETS: dict[str, Any] = {}


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
        for fname, kind in (("index.json", "官网"), ("wechat-index.json", "公众号"), ("crawl-index.json", "官网")):
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
                    _SRC_META[key] = {"label": (meta.get("title") or "官网")[:40], "kind": kind,
                                      "date": "", "url": meta.get("url", "")}
    return _SRC_META.get(slug, {"label": slug, "kind": "未知", "date": "", "url": ""})


def _ev_items(ev: dict) -> list[dict[str, str]]:
    if not ev:
        return []
    if "sources" in ev:
        return ev["sources"]
    return [ev]


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
        return {
            "focus": "overview",
            "label": "整体流程",
            "text": " → ".join(steps) if steps else "官方页面没有给出可执行步骤。",
            "quotes": quotes_for("steps."),
            "found": bool(steps),
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

    # 单值字段
    value = item.get(focus)
    return {
        "focus": focus,
        "label": FOCUS_LABEL[focus],
        "text": value,
        "quotes": quotes_for(focus),
        "found": bool(value),
    }


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


def answer_question(text: str, given: dict[str, str] | None = None) -> dict[str, Any]:
    ranked = rank(text)
    top, score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0

    if score < MATCH_THRESHOLD:
        return {
            "matched": False,
            "query": text,
            "normalized": None,
            "reason": "我的事项库里没有这一条，我不编流程。",
            "hints": dept_hints(text),
            "alternatives": [{"id": i["id"], "title": i["title"]} for i, s in ranked[:3] if s > 0],
            "suggestion": "如果学校有这一项的官方页面或通知，给我，我把它做成正式条目（带原文引用）。",
        }

    # 同一族事项分数咬得很紧时先问清是哪一类，别硬猜
    rivals = [(i, sc) for i, sc in ranked[:4] if sc >= MATCH_THRESHOLD]
    if len(rivals) >= 2 and (score - rivals[1][1]) < 8:
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
            "disambiguate": [{"id": i["id"], "title": i["title"]} for i, _ in rivals[:3]],
            "focus": [],
            "quotes": [],
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
    }


class AskReq(BaseModel):
    text: str
    slots: dict[str, str] = {}


@app.post("/api/ask")
def ask(req: AskReq) -> dict[str, Any]:
    maybe_reload()
    text = (req.text or "").strip()
    if len(text) < 2:
        raise HTTPException(400, "请再说得具体一点")
    return answer_question(text, req.slots)


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
