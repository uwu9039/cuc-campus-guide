"""专名维度（1-B）、定位器、候选池补面（甲）与单词菜单同源合并（7-②）的回归。

盯五件事：
  1. 问句里的产品/系统名取得出来，且中文紧挨着也不丢（VPN 那个坑）。
  2. 库里确有同名条目时，没点到这个名字的条目不许顶在前面；
     库里根本没提这个东西时（校车），闸门必须完全不参与，作答照旧。
  3. 条目自带的定位器（Adobe 全家族的名字与缩写）进词表、能定位到条目；
     两字母的缩写按词边界认，不许从「wps365」里被认出来（2026-11-05 的错答形状）。
  4. 问句点了名而候选池里没一条带它时，带名的条目要补进池尾给模型看——
     闸门只压别人不抬自己，打分又不看正文与定位器，0 分的正答条目模型根本看不见；
     家族名（word/excel 是 Office 的成员）登记上之后，规则腿自己就该落到讲正版office的那条。
  5. 同一份文件里连着编号排下来的条目，在菜单里只算一条；人工整理的菜单不动。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:110])


def real_proper_index():
    pi = app.proper_index()
    if not pi["items"]:
        raise SystemExit("sources/proper.json 没读到，先跑 tools/build_proper.py")
    return pi


# ---- 1. 取词 ----
pi = real_proper_index()
for q, want in [
    ("Adobe软件怎么激活", "adobe"),
    ("校外访问学校系统VPN怎么连？", "vpn"),
    ("WPS365怎么登录", "wps365"),
    ("中传云盘怎么用", "中传云盘"),
    ("融合门户密码忘了", "融合门户"),
]:
    got = app.question_proper(q)
    check("取词 %s" % q, want in got, "取到 %s" % sorted(got))

# ---- 2. 闸门 ----
# 库里没提的东西：问句取不到词或池子里没人写它 → 闸门不动，照旧作答
for q in ["校车时刻表"]:
    qp = app.question_proper(q)
    named = [t for t in pi["postings"]
             if any(t == w or (len(t) >= 3 and len(w) >= 3 and (t in w or w in t)) for w in qp)]
    hit = any(pi["postings"][t] for t in named)
    check("闸门不参与 %s" % q, not hit, "取词 %s / 池内有名条目 %s" % (sorted(qp), hit))

# 池内确有同名条目：闸门开，头条必须自己带这个名字
for q in ["Adobe软件怎么激活", "正版office怎么激活", "ps怎么激活"]:
    qp = app.question_proper(q)
    if not qp:
        continue
    named = [t for t in pi["postings"]
             if any(t == w or (len(t) >= 3 and len(w) >= 3 and (t in w or w in t)) for w in qp)]
    if not any(pi["postings"][t] for t in named):
        continue
    top = app.rank(q)[0][0]
    check("闸门压住头条 %s" % q, app.names_product(top, qp),
          "top1=%s %s" % (top["id"], top["title"][:40]))

# ---- 2b. 定位器（用户拍板：Adobe 全家族的名字与缩写写进条目） ----
ps_ids = pi["postings"].get("ps") or set()
loc_items = [it for it in app.ITEMS if it.get("locators")]
# 带定位器的条目不止 Adobe 那批（office 家族那两条没写 ps），
# 要比的是「自己写了 ps 的条目」和「词表里 ps 底下的条目」是不是同一批。
ps_writers = {it["id"] for it in loc_items
              if "ps" in {str(x).strip().lower() for x in it["locators"]}}
check("定位器进词表", bool(ps_writers) and ps_ids == ps_writers,
      "自写 ps 的条目 %d 条 / ps→%d 条" % (len(ps_writers), len(ps_ids)))
check("问句里的 ps 取得到", "ps" in app.question_proper("ps激活怎么弄"),
      "取到 %s" % sorted(app.question_proper("ps激活怎么弄")))
check("ps 认得出品牌全称那批（adobe 同一批条目）",
      ps_ids <= (pi["postings"].get("adobe") or set()),
      "ps %d 条 / adobe %d 条" % (len(ps_ids), len(pi["postings"].get("adobe") or ())))
wps_item = app.ITEM_BY_ID.get("pt-511bef8105")     # 「（三）正版WPS如何登录？」正文里有 wps365
check("两字母缩写按词边界认：ps 不许从 wps 里被认出来",
      bool(wps_item) and not app.names_product(wps_item, {"ps"}),
      "%s %s" % ((wps_item or {}).get("id"), str((wps_item or {}).get("title"))[:30]))
adobe_item = next((it for it in loc_items if not it.get("archive_only")), None)
check("条目自己写了 ps 才算点了 ps",
      bool(adobe_item) and app.names_product(adobe_item, {"ps"}),
      "%s %s" % ((adobe_item or {}).get("id"), str((adobe_item or {}).get("title"))[:30]))
lost = [it["id"] for it in loc_items
        if not set(str(x).strip().lower() for x in it["locators"]) <= (pi["items"].get(it["id"]) or set())]
check("定位器逐个进了这条目的专名集", not lost, "漏在词表外 %s" % lost[:3])
# 反向：问 WPS 的题不许被 Adobe 的定位器抢走（ps/ae 这些缩写只在 Adobe 那批条目上）
for q in ["正版WPS如何登录", "WPS365怎么登录"]:
    t = app.rank(q)[0][0]
    check("问 WPS 头条不带 Adobe 定位器 %s" % q, not t.get("locators"),
          "top1=%s %s 定位器=%s" % (t["id"], t["title"][:26], bool(t.get("locators"))))

# ---- 2c. 候选池补面（甲）：问句点了名、池子里却没一条带这个名字，把带名的条目端进池子 ----
# 闸门只会压别人（把不带名的压到 54），不会给自己加分；正文与定位器都不参与打分，
# 所以「photoshop怎么安装」这类问法里 Adobe 条目是 0 分，排不进规则前八，
# 模型对着 [Sheet1] 杂表行只能判未收录（2026-11-05 实测）。这一路只补候选，不动打分与门槛。
fill = getattr(app, "proper_fill_candidates", None)
for q, kw in [("photoshop怎么安装", "安装"), ("ps怎么安装", "安装"),
              ("全家桶怎么下载", "下载")]:
    if fill is None:
        check("补面 %s" % q, False, "app.proper_fill_candidates 还没实现")
        continue
    ranked = app.rank(q)
    pool = app.rerank_candidates(q, ranked)
    add = fill(q, ranked, pool)
    ids = [i["id"] for i, _ in add]
    texts = " ".join((i.get("title") or "") + str(i.get("answer") or "")[:120] for i, _ in add)
    check("补面非空 %s" % q, bool(add), "补进 %d 条 %s" % (len(ids), ids[:5]))
    check("补来的条目答得上这件事 %s" % q, kw in texts,
          "补 %d 条里没有讲「%s」的：%s" % (len(ids), kw, texts[:70]))
    check("补的都是问句点名的那批 %s" % q,
          all(app.names_product(i, app.question_proper(q)) for i, _ in add),
          "混进不带名的 %s" % [i["id"] for i, _ in add if not app.names_product(i, app.question_proper(q))][:3])
    check("补面不与池内重复 %s" % q, not (set(ids) & {i["id"] for i, _ in pool}),
          "池内 %d 条 / 补 %d 条" % (len(pool), len(add)))
    check("补面不含存档条目 %s" % q, all(not i.get("archive_only") for i, _ in add),
          "%s" % [i["id"] for i, _ in add if i.get("archive_only")][:3])

# 补面不许把池子撑破：给模型看的条数上限一直是 rerank_candidates 的那个 limit，
# 补完还是不能超过（11-04 扩池实验的结论：池子越大收益越小、跑偏越多）。
for q in ["photoshop怎么安装", "全家桶怎么下载", "ps怎么安装"]:
    if fill is None:
        check("补面后池子不超上限 %s" % q, False, "app.proper_fill_candidates 还没实现")
        continue
    ranked = app.rank(q)
    pool = app.rerank_candidates(q, ranked)
    add = fill(q, ranked, pool)
    check("补面后池子不超上限 %s" % q, len(pool) + len(add) <= app.RERANK_POOL_LIMIT,
          "池内 %d 条 + 补 %d 条 = %d 条，上限 %d"
          % (len(pool), len(add), len(pool) + len(add), app.RERANK_POOL_LIMIT))

# 负控一：池子里已经有人带这个名字 → 通道一个字都不许多补
for q in ["正版Adobe如何安装", "Adobe软件怎么激活", "wps怎么激活"]:
    if fill is None:
        check("已带名不补 %s" % q, False, "app.proper_fill_candidates 还没实现")
        continue
    ranked = app.rank(q)
    pool = app.rerank_candidates(q, ranked)
    named = [i["id"] for i, _ in pool if app.names_product(i, app.question_proper(q))]
    add = fill(q, ranked, pool)
    check("已带名不补 %s" % q, not add, "池内已带名 %d 条，又补了 %d 条" % (len(named), len(add)))

# 负控二：问句没点名 / 库里真没提这个东西 → 不许凭空塞无关条目
for q in ["校园卡丢了怎么补办", "图书馆几点开门", "figma怎么导出"]:
    if fill is None:
        check("不点名不补 %s" % q, False, "app.proper_fill_candidates 还没实现")
        continue
    ranked = app.rank(q)
    pool = app.rerank_candidates(q, ranked)
    add = fill(q, ranked, pool)
    check("不点名不补 %s" % q, not add, "取词 %s / 补 %d 条" % (sorted(app.question_proper(q)), len(add)))

# ---- 2d. 家族名（word/excel/ppt 是 Office 的成员）：闸门认得之后规则腿自己就该落到正版office那条 ----
# 这两句原先一答一不答（excel 靠原文向量碰运气捞到，word 没捞到），补的是同一条数据。
for q in ["word怎么激活", "excel怎么激活"]:
    top = app.rank(q)[0][0]
    check("问 %s 头条自己带名" % q, app.names_product(top, app.question_proper(q)),
          "top1=%s「%s」" % (top["id"], top["title"][:36]))
    check("问 %s 落到讲 office 激活的那条" % q, "office" in (top.get("title") or "").lower(),
          "top1=%s「%s」" % (top["id"], top["title"][:36]))

# Office 家族的名字要挂在讲 office 激活的那条上（同 Adobe 口径：定位器，不进 aliases 不进打分）
office_ids = pi["postings"].get("office") or set()
word_ids = pi["postings"].get("word") or set()
check("office 成得了名字（正文里的小写 office 也登记）", "pt-c688f71bd2" in office_ids,
      "office→%d 条" % len(office_ids))
check("word 能定位到正版office那条", "pt-c688f71bd2" in word_ids,
      "word→%d 条 %s" % (len(word_ids), sorted(word_ids)[:4]))

# ---- 3. 菜单合并 ----
# 只并「同一份文件里连着编号排下来」的那些；人工整理的事项与不同条款各算一条，
# 所以判据是「同一个分组键不许出现两次」，不是「同一个文件只许出一条」。
for word in ["空调", "印章", "体检"]:
    menu = app._topic_menu(word) or {}
    opts = menu.get("disambiguate") or []
    keys = [app._menu_group_key(app.ITEM_BY_ID[o["id"]], o["label"]) for o in opts if o.get("id")]
    named = [k for k in keys if k]
    dup = len(named) - len(set(named))
    check("菜单无同源重复 %s" % word, dup == 0, "%d 个选项，同源重复合并后残留 %d 组" % (len(opts), dup))

    # 关掉合并规则跑同一道题，确实比开着多——证明这一手在起作用，不是题目本身短了
    real = app._menu_group_key
    app._menu_group_key = lambda *_a, **_k: ""
    try:
        base = len((app._topic_menu(word) or {}).get("disambiguate") or [])
    finally:
        app._menu_group_key = real
    check("合并确实减项 %s" % word, len(opts) < base, "不合并 %d 项 → 合并后 %d 项" % (base, len(opts)))

# 人工整理的菜单（绩点走选项①那条链）不该被合并规则动到
for word, want_min in [("绩点", 1)]:
    menu = app._topic_menu(word) or {}
    opts = menu.get("disambiguate") or []
    check("人工菜单不受影响 %s" % word, len(opts) >= want_min or not opts,
          "%d 个选项" % len(opts))

print("failed", failed)
sys.exit(1 if failed else 0)
