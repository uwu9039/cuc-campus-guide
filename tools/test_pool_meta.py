"""候选行补元信息的回归：开关关着时字节与今天相同，打开时多摆模型判「谁管的、对谁有效」那两栏。

盯四件事：
  1. POOL_META=False（默认）时，两条腿（候选重排、逐面裁决）的行格式与改动前逐字节相同——
     归因档要能复现现行，开关不能偷偷改 prompt。
  2. 打开后，行里出现适用对象与出处文档名；归口在逐面裁决那套里补上（它本来没有）。
  3. 缺字段不崩：没有 audience、source 只有内部 id 的，写「—」而不是把 att-xxxx 摆给模型。
  4. 元信息只进 prompt，不进 done 帧的响应字段（那是给人排查用的另一套）。
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
    print(("PASS" if ok else "FAIL"), name, "|", detail[:160])


IT = {"id": "xyy-gongfei", "title": "学生公费医疗报销（享受范围、就诊转诊）",
      "auto": False, "dept": "校医院", "audience": ["本科生", "研究生"],
      "source": [{"title": "学生公费医疗常见问题解答（校医院）"}]}
ATT = {"id": "pt-19197277b0", "title": "第二节违反治安管理及校园秩序行为的处",
       "auto": True, "dept": "中国传媒大学", "source": [{"title": "att-c86ee325fa"}]}
BARE = {"id": "x-bare", "title": "没有归口没有适用对象", "auto": False}

# ---- 1 关着时逐字节等于旧写法
app.POOL_META = False
old_rerank = (f"- {IT['id']}｜{IT['title'][:50]}｜{'整理条目'}｜{IT['dept']}｜摘要X")
old_decide = f"- {ATT['id']}｜{ATT['title'][:50]}｜正文X"
check("关着时重排行与旧写法相同", app._pool_row(IT, "摘要X") == old_rerank,
      app._pool_row(IT, "摘要X"))
check("关着时逐面裁决行与旧写法相同",
      app._pool_row(ATT, "正文X", with_kind=False) == old_decide,
      app._pool_row(ATT, "正文X", with_kind=False))

# ---- 2 打开后多两栏
app.POOL_META = True
r1 = app._pool_row(IT, "摘要X")
check("打开后有适用对象", "适用:本科生、研究生" in r1, r1)
check("打开后有出处文档名", "出处:学生公费医疗常见问题解答" in r1, r1)
r2 = app._pool_row(IT, "正文X", with_kind=False)
check("逐面裁决那套补上归口", "归口:校医院" in r2 and "整理条目" not in r2, r2)

# ---- 3 缺字段与内部 id
r3 = app._pool_row(ATT, "正文X")
check("只有内部 id 的出处写—而不是 att-xxxx",
      "出处:—" in r3 and "att-c86ee325fa" not in r3, r3)
r4 = app._pool_row(BARE, "正文X")
check("缺归口缺适用对象不崩", "归口" not in r4 or "适用:—" in r4, r4)

# ---- 4 元信息不进 done 帧的响应字段
app.api_key = lambda: "test-key"
seen = []
app.ds_chat = lambda msgs, **kw: seen.append(msgs) or (
    '{"scores": {}, "best": null, "why": "", "rewrites": [], "facets": []}')
d = app.answer_question("公费医疗怎么报销", router_llm=True)
blob = str(d)
row = next((m["content"] for ms in seen for m in ms if "出处:" in m.get("content", "")), "")
check("出处栏进了 prompt", bool(row), f"看过 {len(seen)} 次调用")
check("响应字段里没有摆给模型的候选行", "出处:学生公费医疗" not in blob, blob[:120])

print("failed", failed)
sys.exit(1 if failed else 0)
