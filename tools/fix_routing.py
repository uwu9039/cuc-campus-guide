"""修路由：多关键词加权 + 同族事项歧义消解。"""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "app.py"
s = p.read_text(encoding="utf-8")

old_kw = """    # 关键词层：口语里最稳定的锚点
    for raw in item.get("keywords", []):
        k = norm(raw)
        if k and k in q:
            best = max(best, 84 + min(8, len(k)))"""
new_kw = """    # 关键词层：命中越多越可信（「校园卡+挂失+解挂」应当压过泛泛的「校园卡」）
    hits = 0
    kw_best = 0
    for raw in item.get("keywords", []):
        k = norm(raw)
        if k and k in q:
            hits += 1
            kw_best = max(kw_best, 84 + min(8, len(k)))
    if hits:
        best = max(best, kw_best + (hits - 1) * 7)"""

old_dis = """    focus = detect_focus(text, top)
    known0 = {**_known_slots(text, top), **(given or {})}
    parts = [_answer_one(top, f, known0) for f in focus]"""
new_dis = """    # 同一族事项分数咬得很紧时先问清是哪一类，别硬猜
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
    parts = [_answer_one(top, f, known0) for f in focus]"""

assert old_kw in s, "关键词段没找到"
assert old_dis in s, "消解段没找到"
s = s.replace(old_kw, new_kw).replace(old_dis, new_dis)
p.write_text(s, encoding="utf-8")
print("已修")
