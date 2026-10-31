"""auto_07 人工复核：剔除新闻、活动预告与商业广告，保留并修顺
欧洲预科、韩国国际本科、辅修、成绩单、后勤指南、宿舍用电、
体育场馆预约、学生证补办等可办事事实。

判定原则：
- 整源剔除：学院新闻、人物感想、过期活动、商业广告、泛泛宣传
- 同源重复：只保留信息最全的一条，其余碎片先并入再删
- 标题粘连、条文截断：从官方原文按连续段落补齐，保留原文限定语与笔误
- 每条改写后都要求是原文连续片段，否则保留原引文并单独报告
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_07.txt"
LOG = ROOT / "_review_items" / "applied_auto_07.txt"

SOURCE_DIRS = ("", "wechat", "crawl", "cdp", "pdf", "chsi", "moe", "national", "extra",
               "huibian", "local", "wendao-extra", "wendao-text", "attachments/text", "ilib-text")

DROP_SOURCES = {
    "2025-05-01-6ab7ffbe": "印象艺考商业广告",
    "2025-08-01-76d0ea89": "大学生心理健康专题新闻，非本校办事信息",
    "20250605-c14744a256551": "学院党建培训新闻",
    "20250605-c14744a256559": "学院党建培训新闻",
    "20250605-c14744a256560": "学院党建培训新闻",
    "20250624-c14744a257612": "中央八项规定知识竞赛新闻",
    "20251020-c14745a261245": "2025级军训纪实，学生感想汇编",
    "20251025-c2065a261495": "2025年校友返校日活动，已过期",
    "20251101-c14745a261713": "学院新闻",
    "20251101-c4365a261714": "全国师资班新闻，非校内办事",
    "20251201-c14744a264613": "主题党日新闻",
    "20251201-c4366a264601": "学院新闻",
    "20251202-c4365a264687": "学术研讨会新闻",
    "20251202-c2065a264692": "仅标题与图片，无正文",
    "20251230-c14745a265735": "学院新闻",
    "20251230-c14745a265741": "团学活动新闻",
    "20251230-c2065a265732": "汉服活动预告，活动已结束",
    "20251231-c14745a265747": "健步走活动新闻",
    "20251231-c14745a265755": "学院新闻",
    "2026-05-02-5a55132a": "印象艺考商业广告",
    "2026-05-04-ce1d26c0": "印象艺考商业广告",
    "2026-05-20-99ae633a": "中国教育报署名文章，非办事信息",
    "2026-06-07-a609a04b": "印象艺考商业广告",
    "20250401-c6364a253846": "2025年辅修招生，已过期",
}

DROPS = {
    # 2025-07-20 欧洲名校预科项目
    "pt-17efd8b667": "泛泛宣传，无办事信息",
    "pt-4c5dd27ac3": "泛泛宣传，无办事信息",
    "pt-65a9f3d1e1": "师资宣传，无办事信息",
    "pt-761e8680a1": "泛泛宣传，无办事信息",
    "pt-7710a5d835": "碎片，已并入课程设置条",
    # 2025-08-21 新生指南生活篇
    "pt-0be7d861e7": "已并入星光餐厅条",
    "pt-2da3d03903": "已并入中传美食广场条",
    "pt-2f1aa603ca": "已并入中蓝餐厅条",
    "pt-39421cf8bc": "开篇抒情，无办事信息",
    "pt-73a6f3c410": "已并入中蓝餐厅条",
    "pt-8fe5b59f93": "开篇抒情，无办事信息",
    "pt-a289ebf9f9": "已并入星光餐厅条",
    "pt-a749ac0fe9": "栏目导语，无办事信息",
    "pt-a96ba06e55": "指向表格的碎片，无实质内容",
    "pt-af4e412ea2": "已并入星光餐厅条",
    "pt-d5582b6886": "已并入北苑餐厅条",
    "pt-da58e22680": "抒情提问，无办事信息",
    "pt-f09f484b56": "结尾抒情，无办事信息",
    "pt-fbe8d3be43": "开篇抒情，无办事信息",
    "pt-fdf095c572": "开篇抒情，无办事信息",
    "pt-b2b5572ee2": "30G流量与2023年官方50G标准冲突，生活指南沿用旧文案",
    "pt-49695df568": "已并入宿舍免费用电与购电条",
    "pt-47e5972bbc": "已并入校园网认证页面条",
    "pt-1c1c479a09": "已并入宿舍维修与报修条",
    "pt-f5301208d5": "已并入校医院科室设置条",
    "pt-f90d213792": "已并入北苑餐厅条",
    "pt-a4792e997c": "已并入北苑餐厅条",
    "pt-b576e8d39e": "已并入梆子井食堂条",
    # 2026-09-17 音小录答疑
    "pt-0aecd10bdc": "仅提问标题，无正文",
    "pt-1f446a827a": "仅提问标题，无正文",
    "pt-3f6c396678": "宣传语，无办事信息",
    "pt-47635f5e01": "仅提问标题，无正文",
    "pt-5e09005877": "仅提问标题，无正文",
    "pt-74a3e68395": "宣传语，无办事信息",
    "pt-82bf8292de": "仅提问标题，无正文",
    # 20250924 后勤服务指南
    "pt-c7fd8e9585": "截断残句",
    "pt-9357048a02": "已并入后勤微信公众平台条",
    # 2026-03-26 可信电子成绩单
    "pt-3f3f1224c7": "宣传语，无办事信息",
    "pt-b13f8f010e": "转发引导语，无办事信息",
    # 20250401 2026 辅修招生
    "pt-2fb3925e80": "附件指向语，附件未入库",
    "pt-cc8c55cc92": "简章指向语，无独立事实",
    # 2025-03-05 音小录答疑
    "pt-bf4f63b14e": "宣传语，无办事信息",
    "pt-f0a1a94f55": "提问碎片，无办事信息",
    "pt-f7f6216f32": "结尾祝语，无办事信息",
    # 2026-06-05 韩国国际本科项目
    "pt-eb24e09e86": "报名材料碎片，已并入完整材料清单",
    "pt-ad3dbeade9": "报名材料碎片，已并入完整材料清单",
    "pt-3b879d1099": "报名材料碎片，已并入完整材料清单",
    "pt-902d7f6899": "报名材料碎片，已并入完整材料清单",
    "pt-c7c4796f75": "发放规则碎片，已并入完整规则",
    "pt-d7a4a6737c": "发放规则碎片，已并入完整规则",
    "pt-18b7221056": "发放规则碎片，已并入完整规则",
    "pt-cd897b3ef6": "与免测试入学条件条目重复",
    "pt-48e1319dc9": "已并入专业课程条",
    "pt-84ebb72f0b": "优势宣传，标题粘连",
    "pt-f8e2252946": "师资宣传，标题粘连",
    "pt-ac6b58e98f": "优势宣传，标题粘连",
    "pt-32dbf371cd": "就业宣传碎片",
    "pt-f679f7c542": "就业宣传碎片",
    "pt-16c246fcf6": "就业宣传碎片",
    "pt-cff1c8c73c": "地缘优势宣传，标题粘连",
    "pt-3d26ba1c7b": "地缘优势宣传碎片",
    "pt-14c1eb0223": "地缘优势宣传碎片",
    "pt-e62ae67130": "性价比宣传，标题粘连",
    "pt-be38f67fc0": "奖学金宣传碎片",
    "pt-620068a001": "韩国留学导语，无办事信息",
    "pt-24420cf2dd": "学校概况，标题粘连",
    "pt-7a5373bd2e": "学科概况碎片",
    "pt-c1138ccb56": "学科概况碎片",
    "pt-bb79d2a5b9": "学校位置介绍，非办事信息",
    "pt-96fe701e89": "爱思学中介广告",
}


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def raw_lines(src: str) -> list[str]:
    for sub in SOURCE_DIRS:
        p = (ROOT / "sources" / sub if sub else ROOT / "sources") / f"{src}.txt"
        if p.exists():
            # 源文件混有孤立 \r，禁用通用换行，行号与编辑器一致
            with p.open("r", encoding="utf-8", newline="") as f:
                return f.read().split("\n")
    raise SystemExit(f"源文件不存在：{src}")


def L(src: str, a: int, b: int | None = None) -> str:
    lines = raw_lines(src)
    if b is None:
        b = a
    return "\n".join(x.strip() for x in lines[a - 1:b])


def cut(text: str, marker: str) -> str:
    if marker not in text:
        raise SystemExit(f"裁剪标记不存在：{marker[:30]}")
    return text.split(marker, 1)[0]


def after(text: str, marker: str) -> str:
    if marker not in text:
        raise SystemExit(f"截取标记不存在：{marker[:30]}")
    return text.split(marker, 1)[1]


SPECIAL = {
    # 2025-07-20 欧洲名校预科项目（海南校区）
    "pt-3a96c78f8a": L("2025-07-20-26c18fef", 15),
    "pt-135a06b8fb": L("2025-07-20-26c18fef", 139, 145),
    "pt-4b7f0290b5": L("2025-07-20-26c18fef", 31, 35),
    "pt-a2c5a8aa52": L("2025-07-20-26c18fef", 36, 41),
    "pt-cf17716c97": L("2025-07-20-26c18fef", 83, 85),
    "pt-b5e5ed7c44": L("2025-07-20-26c18fef", 69, 70),
    # 2025-08-21 新生指南生活篇（跳过图片行，保留餐厅名与正文）
    "pt-3bbb082f00": L("2025-08-21-4797ab1b", 102) + "\n" + L("2025-08-21-4797ab1b", 104, 105),
    "pt-069153cba1": L("2025-08-21-4797ab1b", 106) + "\n" + L("2025-08-21-4797ab1b", 108, 109),
    "pt-5416b2c2de": L("2025-08-21-4797ab1b", 110) + "\n" + L("2025-08-21-4797ab1b", 112, 113),
    "pt-7552c07142": L("2025-08-21-4797ab1b", 114) + "\n" + L("2025-08-21-4797ab1b", 116, 117),
    "pt-892e906e2b": L("2025-08-21-4797ab1b", 118) + "\n" + L("2025-08-21-4797ab1b", 120, 121),
    "pt-15895b09a5": L("2025-08-21-4797ab1b", 128, 130),
    "pt-c0d673eacc": L("2025-08-21-4797ab1b", 53, 54),
    "pt-bbf0abda98": L("2025-08-21-4797ab1b", 61, 62),
    "pt-fcbffdfa19": L("2025-08-21-4797ab1b", 85, 86),
    "pt-b2c4c1df76": L("2025-08-21-4797ab1b", 100, 101),
    "pt-56e7bbb587": L("2025-08-21-4797ab1b", 93),
    "pt-67fbecdbbd": L("2025-08-21-4797ab1b", 87, 89),
    "pt-8208350ee9": L("2025-08-21-4797ab1b", 90, 92),
    # 2026-09-17 音小录答疑
    "pt-48f2190582": L("2026-09-17-88875050", 115, 118),
    "pt-6b1c448da1": L("2026-09-17-88875050", 180, 186),
    "pt-7e81887d5d": L("2026-09-17-88875050", 90, 92),
    # 20250924 后勤服务指南
    "pt-06432dd193": L("20250924-c378a260402", 27, 28),
    "pt-0b74ff156b": L("20250924-c378a260402", 41),
    "pt-607de73a90": L("20250924-c378a260402", 104, 105),
    "pt-69291cd1fb": L("20250924-c378a260402", 93, 96),
    "pt-7843870d1e": L("20250924-c378a260402", 35, 36),
    "pt-89ab09d9ac": L("20250924-c378a260402", 117, 118),
    "pt-d68ff55e05": L("20250924-c378a260402", 109, 111),
    # 2026-03-26 2007—2019届本科生可信电子成绩单
    "pt-c1105cd200": L("2026-03-26-b99505f2", 2, 5),
    # 2026-01-15 寒假成绩单与证明办理
    "pt-3279338055": L("2026-01-15-d04bf4f8", 19, 23),
    "pt-f224dd32a5": L("2026-01-15-d04bf4f8", 11, 13),
    # 20250401 2026年辅修招生
    "pt-dfe0946855": L("20250401-c6364a268919", 58, 68),
    # 2025-03-05 音小录答疑
    "pt-c723948819": L("2025-03-05-ac111b0f", 37, 39),
    # 2026-06-05 韩国国际本科名校项目
    "pt-0ef2504851": L("2026-06-05-360f0c14", 7),
    "pt-b5636afb0a": L("2026-06-05-360f0c14", 56),
    "pt-f51686c186": L("2026-06-05-360f0c14", 58),
    "pt-aa41427287": L("2026-06-05-360f0c14", 60),
    "pt-51ddd6c588": L("2026-06-05-360f0c14", 64, 69),
    "pt-546489ce13": L("2026-06-05-360f0c14", 72),
    "pt-bb8cb560df": L("2026-06-05-360f0c14", 73, 77),
    "pt-a757955fd0": L("2026-06-05-360f0c14", 78, 81),
    "pt-6e891ac4e3": L("2026-06-05-360f0c14", 27, 28),
    "pt-5d64521e67": L("2026-06-05-360f0c14", 31),
    "pt-17071d3433": L("2026-06-05-360f0c14", 33),
    "pt-dcfd6ae085": L("2026-06-05-360f0c14", 35),
}

TITLES = {
    "pt-3a96c78f8a": "中国传媒大学欧洲名校预科项目（海南校区）简介",
    "pt-135a06b8fb": "欧洲名校预科项目收费标准",
    "pt-4b7f0290b5": "欧洲名校预科项目2025年招生专业",
    "pt-a2c5a8aa52": "欧洲名校预科项目国内课程设置",
    "pt-cf17716c97": "欧洲名校预科项目证书和学位",
    "pt-b5e5ed7c44": "欧洲名校预科项目合作院校：爱尔兰国立艺术设计学院",
    "pt-3bbb082f00": "北苑餐厅",
    "pt-069153cba1": "中蓝餐厅",
    "pt-5416b2c2de": "梆子井食堂",
    "pt-7552c07142": "星光餐厅",
    "pt-892e906e2b": "中传美食广场",
    "pt-15895b09a5": "校园网认证页面与无感知认证设置",
    "pt-c0d673eacc": "校医院科室设置",
    "pt-bbf0abda98": "本科生住宿安排",
    "pt-fcbffdfa19": "宿舍免费用电与购电",
    "pt-b2c4c1df76": "食堂概况",
    "pt-56e7bbb587": "宿舍维修与报修",
    "pt-67fbecdbbd": "中蓝公寓供电与购电",
    "pt-8208350ee9": "梆子井公寓供电与购电",
    "pt-48f2190582": "录音棚预约资格与入口",
    "pt-6b1c448da1": "学生证补办流程",
    "pt-7e81887d5d": "体育场馆预约确认与系统开放时间",
    "pt-06432dd193": "学生公寓服务",
    "pt-0b74ff156b": "公寓区“一站式”学生社区",
    "pt-607de73a90": "收发服务",
    "pt-69291cd1fb": "后勤报修服务",
    "pt-7843870d1e": "校内公寓位置",
    "pt-89ab09d9ac": "后勤微信公众平台",
    "pt-d68ff55e05": "意见反馈渠道",
    "pt-c1105cd200": "2007—2019届本科毕业生成绩单支持线上自助办理",
    "pt-3279338055": "2020届以前毕业生邮件申请电子版材料",
    "pt-f224dd32a5": "可信电子凭证系统",
    "pt-dfe0946855": "2026年辅修招生专业与报名时间",
    "pt-c723948819": "本科生可信电子成绩单系统",
    "pt-0ef2504851": "中国传媒大学国际预科项目介绍",
    "pt-b5636afb0a": "韩国国际本科项目2026年报名时间",
    "pt-f51686c186": "韩国国际本科项目招生对象",
    "pt-aa41427287": "韩国国际本科项目免测试入学条件",
    "pt-51ddd6c588": "韩国国际本科项目报名材料",
    "pt-546489ce13": "韩国国际本科项目入学奖学金申请标准",
    "pt-bb8cb560df": "韩国国际本科项目入学奖学金发放规则",
    "pt-a757955fd0": "韩国国际本科项目收费标准",
    "pt-6e891ac4e3": "韩国国际本科项目经济与管理方向专业",
    "pt-5d64521e67": "韩国国际本科项目语言课程",
    "pt-17071d3433": "韩国国际本科项目专业课程",
    "pt-dcfd6ae085": "韩国国际本科项目通识课程",
}


def load_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    for sub in SOURCE_DIRS:
        base = ROOT / "sources" / sub if sub else ROOT / "sources"
        for f in base.glob("*.txt"):
            texts[f.stem] = squash(f.read_text(encoding="utf-8"))
    return texts


def retitle(item: dict, new_answer: str) -> None:
    old = item.get("title", "")
    suffix = ""
    if " · " in old:
        suffix = " · " + old.rsplit(" · ", 1)[1]
    title = TITLES.get(item["id"], new_answer[:40] + ("…" if len(new_answer) > 40 else ""))
    title = title.replace("\n", " ")
    item["title"] = title + suffix
    aliases = item.get("aliases") or []
    if aliases:
        aliases[0] = title
        item["aliases"] = aliases


def main() -> None:
    dry = "--dry-run" in sys.argv
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = {it["id"]: it for it in data["items"]}
    texts = load_texts()

    chunk_ids = []
    for line in CHUNK.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunk_ids.append(line.split()[0])
    chunk_set = set(chunk_ids)

    drops = dict(DROPS)
    src_counts: dict[str, int] = {}
    for pid in chunk_ids:
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if src in DROP_SOURCES:
            drops[pid] = DROP_SOURCES[src]
            src_counts[src] = src_counts.get(src, 0) + 1

    changes = {}
    for pid, new in SPECIAL.items():
        if new and new != items[pid].get("answer"):
            changes[pid] = new

    overlap = set(drops) & set(changes)
    if overlap:
        raise SystemExit(f"同一条既删又改：{overlap}")
    targets = set(drops) | set(changes)
    outside = sorted(targets - chunk_set)
    if outside:
        raise SystemExit(f"目标条目不在 auto_07 分块内：{outside}")
    missing = [pid for pid in targets if pid not in items]
    if missing:
        raise SystemExit(f"条目不存在：{missing}")

    not_in_source = []
    for pid, new in changes.items():
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if squash(new) not in texts.get(src, ""):
            not_in_source.append((pid, src, new[:60]))

    log: list[str] = []
    for src, n in sorted(src_counts.items()):
        log.append(f"SOURCE {src}  删除 {n} 条：{DROP_SOURCES[src]}")
    for pid, reason in sorted(drops.items()):
        log.append(f"DROP  {pid}  {reason}  |  {items[pid].get('answer', '')[:50]}")
    for pid in sorted(changes):
        log.append(f"FIX   {pid}  {items[pid].get('answer', '')[:50]}  ->  {changes[pid][:70]}")

    print(f"整源剔除 {len(src_counts)} 个来源，删除 {len(drops)} 条，修改 {len(changes)} 条，当前 {len(data['items'])} 条")
    if not_in_source:
        print(f"\n改写后不是原文连续片段 {len(not_in_source)} 条（保留原引文）：")
        for pid, src, head in not_in_source:
            print(f"  {pid} {src} {head}")

    if dry:
        print("\n".join(log))
        return

    for pid in drops:
        data["items"].remove(items[pid])
    for pid, new in changes.items():
        it = items[pid]
        it["answer"] = new
        retitle(it, new)
        ev = (it.get("evidence") or {}).get("answer")
        if ev and squash(new) in texts.get(ev.get("src", ""), ""):
            ev["quote"] = new

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"已写回，剩余 {len(data['items'])} 条；日志 {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()