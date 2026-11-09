"""官方说法的问句级缓存：同一句话不重问模型，不同句不受影响。

盯三件事：
  1. 同一归一化问句两次调用，模型只被问一次。
  2. 关掉开关时每次都真调（默认值留给归因跑完再拍）。
  3. 缓存按整句归一化，改一个字就是另一句话，不许把上一句的说法套下来。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

failed = 0


def check(name, ok, detail=""):
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:140])


check("缓存容器已定义", hasattr(app, "_PHRASE_CACHE"), "模块里没有 _PHRASE_CACHE")
check("开关已定义", hasattr(app, "PHRASE_CACHE"), "模块里没有 PHRASE_CACHE")

app.api_key = lambda: "x"
n = []
# 这两条要能过 `_phrase_useful`：保留原句的二字组，又是真的换了说法（否则被校验丢掉，缓存就成空表）
PHRASED = '{"phrases": ["图书馆周末开放时间", "图书馆周六周日开馆安排"]}'
WANT = ["图书馆周末开放时间", "图书馆周六周日开馆安排"]


def fake(msgs, **kw):
    n.append(msgs)
    return PHRASED


app.ds_chat = fake
app._PHRASE_CACHE.clear()
app.PHRASE_CACHE = True
a1 = app.llm_official_phrases("图书馆周末开吗")
a2 = app.llm_official_phrases("图书馆周末开吗")
check("同问只调一次模型", len(n) == 1, f"实际 {len(n)} 次")
check("第二次拿到同一份说法", a1 == a2 == WANT, f"{a1} vs {a2}")

app.llm_official_phrases("食堂周末几点开门")
check("换问句照常调模型", len(n) == 2, f"实际 {len(n)} 次")

app._PHRASE_CACHE.clear()
app.PHRASE_CACHE = False
n.clear()
app.llm_official_phrases("图书馆周末开吗")
app.llm_official_phrases("图书馆周末开吗")
check("关掉开关时每次真调", len(n) == 2, f"实际 {len(n)} 次")

print("failed", failed)
sys.exit(1 if failed else 0)
