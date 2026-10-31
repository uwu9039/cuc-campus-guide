"""1030 第二批：修正步骤标签收窄过度、专用条目被通用条目压住、逾期/赔偿问法。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def add_tags(item: dict, index: int, tags: list[str]) -> None:
    row = item["steps"][index]
    cur = list(row.get("tags") or [])
    for t in tags:
        if t not in cur:
            cur.append(t)
    row["tags"] = cur


def drop_tags(item: dict, index: int, tags: list[str]) -> None:
    row = item["steps"][index]
    cur = [t for t in (row.get("tags") or []) if t not in tags]
    if cur:
        row["tags"] = cur
    else:
        row.pop("tags", None)


def drop_keys(item: dict, keys: list[str]) -> None:
    for field in ("aliases", "keywords"):
        if isinstance(item.get(field), list):
            item[field] = [k for k in item[field] if k not in keys]


def main() -> None:
    path = ROOT / "items.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    by = {it["id"]: it for it in data["items"]}

    # 1. 因公出国：单个环节上的「审批 / 申请」标签会把「审批流程」问法收窄成一步
    jiaogong = by["jiaogong-yingong-chuguo"]
    add_tags(jiaogong, 0, ["申请"])
    drop_tags(jiaogong, 2, ["审批"])

    # 2. 访客预约：入校这一步也是预约流程的一部分
    fangke = by["fangke-yuyue"]
    add_tags(fangke, 3, ["预约"])
    fangke["scope_note"] = (
        "家长进校按访客预约办理；能不能提前到校、能提前几天进校，公开页面没有说明"
    )
    fangke["scope_note_if"] = ["提前", "早到", "早一天"]

    # 3. 临时困难补助 / 学费减免 / 外来人员：申请是一条链，不能只答第一步
    linshi = by["linshi-kunnan-buzhu"]
    add_tags(linshi, 3, ["申请"])
    add_tags(linshi, 4, ["申请"])

    xuefei = by["xuefei-jianmian"]
    add_tags(xuefei, 1, ["减免"])
    add_tags(xuefei, 3, ["申请"])

    laifang = by["sushe-laifang"]
    add_tags(laifang, 2, ["申请"])
    add_tags(laifang, 3, ["申请"])

    # 4. 通用条目抢走「换宿舍 / 退宿」专用条目：撤掉重复的别名词与关键词
    gongyu = by["xinsheng-gongyu"]
    drop_keys(gongyu, ["换宿舍", "调宿", "退宿"])

    zhusufei = by["sushe-zhusufei"]
    if isinstance(zhusufei.get("keywords"), list):
        zhusufei["keywords"] = [k for k in zhusufei["keywords"] if k != "退宿"]

    tuixiu = by["sushe-tuixiu"]
    if "退宿" not in (tuixiu.get("keywords") or []):
        tuixiu.setdefault("keywords", []).append("退宿")

    # 5. 购电条目补上查剩余电量，别只答怎么买
    goudian = by["hq-goudian"]
    if not any("剩余电量" in (s.get("what") or "") for s in goudian["steps"]):
        goudian["steps"].append({
            "when": "查剩余电量",
            "what": "校内、中蓝公寓学生在「中国传媒大学后勤保障处」公众号「微服务」"
                    "—「公寓购电」绑定后，通过小 e 购电查询剩余电量。",
        })
        goudian["evidence"]["steps.2"] = {
            "src": "9bf17365",
            "quote": "校内、中蓝公寓学生查询宿舍电量可关注“中国传媒大学后勤保障处”"
                     "微信公众号“微服务”--“公寓购电”绑定后通过小e购电进行剩余电量查询。",
        }

    # 6. 图书馆逾期 / 赔偿：标出对应步骤，问哪一面就只给哪一面
    jieyue = by["lib-jieyue"]
    add_tags(jieyue, 6, ["逾期", "超期"])
    add_tags(jieyue, 7, ["赔偿", "污损", "丢失"])
    add_tags(jieyue, 8, ["赔偿"])
    jieyue["scope_note"] = (
        "公开规定写的是逾期归还停止借阅，没有写逾期罚款；污损、丢失才按书价赔偿"
    )
    jieyue["scope_note_if"] = ["罚款", "罚钱", "逾期费", "滞纳金"]

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("items", len(data["items"]))


if __name__ == "__main__":
    main()