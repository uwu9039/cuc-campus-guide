"""把 items.json 所有会显示的字段过一遍 _display_text，扫禁用标点。"""
import json
import sys

sys.path.insert(0, ".")
import app

BAD = {
    "“": "左双引号", "”": "右双引号", "‘": "左单引号", "’": "右单引号",
    '"': "直双引号", "'": "直单引号", "「": "直角引号", "」": "直角引号",
    "『": "双直角引号", "』": "双直角引号",
    "—": "破折号", "–": "短破折号", "―": "破折号",
    "：": "冒号", ":": "ASCII 冒号", "。": "句号", "*": "星号", "#": "井号",
    "…": "省略号",
}


def visible(resp):
    for key in ("title", "fee", "location", "hours", "duration", "window", "note",
                "scope_note", "answer"):
        v = resp.get(key)
        if isinstance(v, str) and v:
            yield key, app._display_text(v)
    for i, s in enumerate(resp.get("steps") or []):
        if isinstance(s, dict):
            for k in ("what", "where", "when"):
                if isinstance(s.get(k), str) and s[k]:
                    yield f"steps.{i}.{k}", app._display_text(app._step_what(s) if k == "what" else s[k])
        elif isinstance(s, str) and s:
            yield f"steps.{i}", app._display_text(s)
    for i, m in enumerate(resp.get("materials") or []):
        if isinstance(m, dict) and isinstance(m.get("name"), str):
            yield f"materials.{i}", app._display_text(m["name"])
    for key in ("pitfalls", "advisory"):
        for i, p in enumerate(resp.get(key) or []):
            if isinstance(p, str):
                yield f"{key}.{i}", app._display_text(p)
    for i, s in enumerate(resp.get("slots") or []):
        if isinstance(s, dict):
            for k in ("ask", "why"):
                if isinstance(s.get(k), str):
                    yield f"slots.{i}.{k}", app._display_text(s[k])


d = json.load(open("items.json", encoding="utf-8"))
bad = []
n = 0
for it in d["items"]:
    for field, text in visible(it):
        n += 1
        masked = app._KEEP_RE.sub("□", text)
        for ch in masked:
            if ch in BAD:
                bad.append((it["id"], field, BAD[ch], text[:120]))
                break
print("字段", n, "残留", len(bad))
for b in bad[:60]:
    print(b)
