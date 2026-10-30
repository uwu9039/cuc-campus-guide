"""给新条目补预置问法：人工拟口语问法，逐条验证确实路由回该条目后再写入 presets.json。"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import app as core  # noqa: E402
from gen_presets import group_of, stem  # noqa: E402

CHIPS = {
    "sushe-kongtiao": ["宿舍有空调吗", "宿舍空调电费怎么算", "中蓝公寓是中央空调吗"],
    "sushe-weiyu": ["宿舍有独立卫浴吗", "宿舍是公共卫浴吗", "中蓝宿舍有独立卫生间吗"],
    "sushe-yangtai": ["宿舍有阳台吗", "哪些宿舍有阳台"],
    "sushe-zhiyinshui": ["宿舍有直饮水吗", "宿舍有洗衣机吗", "宿舍饮水机在哪"],
    "sushe-fangxing": ["宿舍几人间", "宿舍住几个人"],
    "sushe-chuanglian": ["宿舍能挂床帘吗", "宿舍查寝吗"],
    "sushe-chuangpin": ["宿舍有被子吗", "床上用品要自己买吗", "学校发被子吗"],
    "sushe-sheshi": ["宿舍条件怎么样", "宿舍有哪些设施", "宿舍环境怎么样"],
    "sushe-jiaju": ["宿舍桌子规格", "宿舍床多大", "中蓝宿舍一期桌子长宽是多少", "柜子多大"],
    "tiyu-xiaoyuanpao": ["校园跑多少次", "校园跑怎么计分", "校园跑用什么软件", "阳光长跑"],
    "banwei-roles": ["班干部有哪些", "班委有哪些", "团支部委员有哪些"],
    "banwei-xuanju": ["班委怎么选", "班委什么时候换届", "班委任职有积分吗"],
    "lib-zixishi": ["自习室在哪", "自习室开放时间", "自习室要预约吗"],
    "shiwu-zhaoling": ["校园卡丢了怎么查", "失物招领在哪"],
    "putonghua-peixun": ["普通话培训", "普通话培训班"],
    "jiaoshi-zige": ["教师资格证", "教师资格认定"],
}

data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
by_id = {i["id"]: i for i in data["items"]}
presets = json.loads((ROOT / "presets.json").read_text(encoding="utf-8"))
existing = {p for g in presets["groups"] for p in g["items"]}
groups = {g["name"]: g for g in presets["groups"]}
cov = presets["coverage"]

added, misses = 0, []
for iid, chips in CHIPS.items():
    item = by_id.get(iid)
    if not item:
        misses.append((iid, "-", "条目不存在"))
        continue
    stems = {stem(q) for q in cov.get(iid, [])}
    for q in chips:
        if q in existing or stem(q) in stems:
            continue
        r = core.answer_question(q)
        got = (r.get("item") or {}).get("id")
        if got != iid:
            misses.append((iid, q, got or "未命中"))
            continue
        gname = group_of(item["title"])
        groups.setdefault(gname, {"name": gname, "items": []})["items"].append(q)
        cov.setdefault(iid, []).append(q)
        existing.add(q)
        stems.add(stem(q))
        added += 1

presets["generated"] = date.today().isoformat()
presets["total"] = sum(len(g["items"]) for g in groups.values())
presets["groups"] = list(groups.values())
(ROOT / "presets.json").write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"新增问法 {added} 条，总计 {presets['total']} 条；未采用 {len(misses)} 条")
for iid, q, got in misses:
    print(f"  ✗ {iid:<20} {q:<16} -> {got}")
