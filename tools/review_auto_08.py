"""auto_08 人工复核：整源剔除学院新闻、讲座、党建、获奖、导师简介与过期公示，
保留音小录开学综合版与学生服务大厅中可办事的事实。

判定原则：
- 整源剔除：新闻、活动回顾、党建、获奖、导师简介、过期公示、政治文章
- 同源重复：已被完整条目覆盖的碎片先核对再删
- 标题粘连、地址与寄语混排：按原文连续段落重排，去掉寄语修饰语
- 每条改写后尽量是原文连续片段，否则保留原引文并单独报告
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_08.txt"
LOG = ROOT / "_review_items" / "applied_auto_08.txt"

SOURCE_DIRS = ("", "wechat", "crawl", "cdp", "pdf", "chsi", "moe", "national", "extra",
               "huibian", "local", "wendao-extra", "wendao-text", "attachments/text", "ilib-text")

DROP_SOURCES = {
    "20260505-c2064a269829": "访企拓岗调研新闻",
    "20260122-c4365a266725": "讲座回顾，非办事信息",
    "20260505-c2064a269832": "学生人物报道",
    "20260226-c2064a267061": "团支部获奖新闻",
    "20260225-c4365a267041": "讲座回顾，非办事信息",
    "20260505-c2064a269837": "留学生论坛活动新闻",
    "20260331-c2064a268388": "党建学习教育部署新闻",
    "20260505-c2064a269838": "校友讲座回顾，非办事信息",
    "20260226-c2064a267065": "班级心理辅导活动新闻",
    "2026-10-19-a3061083": "智能体节征集公告，非校园办事",
    "20260122-c4365a266724": "讲座回顾，非办事信息",
    "20260122-c4365a266726": "讲座回顾，非办事信息",
    "20260122-c4365a266730": "讲座回顾，非办事信息",
    "20260225-c2064a267043": "学生获奖新闻",
    "20260225-c4365a267045": "工作坊活动新闻",
    "20260226-c2064a267070": "学生获奖新闻",
    "20260225-c14745a267027": "团委获奖新闻",
    "20260225-c4365a267039": "校友沙龙回顾，非办事信息",
    "20260226-c4365a267062": "讲座回顾，非办事信息",
    "20260505-c2064a269828": "校友企业调研新闻",
    "20260505-c2064a269833": "思政实践活动新闻",
    "20260225-c2064a267044": "留学生调研活动新闻",
    "20260226-c2064a267066": "班级心理辅导活动新闻",
    "20260226-c2064a267068": "班级心理健康班会新闻",
    "20260331-c2064a268396": "两会精神学习活动新闻",
    "20260503-c2064a269816": "讲座回顾，非办事信息",
    "20260122-c4365a266732": "讲座回顾，非办事信息",
    "20260123-c4365a266737": "讲座回顾，非办事信息",
    "20260123-c4365a266738": "讲座回顾，非办事信息",
    "20260225-c14744a267033": "党员大会新闻",
    "20260226-c2064a267067": "班级心理辅导活动新闻",
    "20260226-c4365a267063": "讲座回顾，非办事信息",
    "20260226-c4365a267069": "工作坊活动新闻",
    "20260331-c2064a268392": "赛事培训新闻",
    "20260331-c2064a268395": "讲座回顾，非办事信息",
    "20260503-c2064a269815": "讲座回顾，非办事信息",
    "20260122-c4365a266729": "讲座回顾，非办事信息",
    "20260123-c4365a266734": "讲座回顾，非办事信息",
    "20260123-c4365a266735": "讲座回顾，非办事信息",
    "20260226-c4365a267064": "教改项目活动新闻",
    "20260505-c2064a269834": "党建读书班新闻",
    "20260122-c4365a266728": "讲座回顾，非办事信息",
    "20260122-c4365a266731": "讲座回顾，非办事信息",
    "20260123-c4365a266733": "讲座回顾，非办事信息",
    "20260123-c4365a266736": "讲座回顾，非办事信息",
    "20260331-c2064a268391": "讲座回顾，非办事信息",
    "20260331-c2064a268393": "党支部书记述职考核新闻",
    "20260331-c2064a268397": "非遗体验活动新闻",
    "20260122-c4365a266727": "讲座回顾，非办事信息",
    "20260421-c5332a269358": "导师个人简介，非办事信息",
    "20260505-c2064a269836": "留学生活动新闻",
    "20260225-c4365a267032": "工作坊活动新闻",
    "20260331-c14817a268360": "课程宣传概览，无办事信息",
    "20260421-c5332a269372": "导师个人简介，非办事信息",
    "20260505-c2064a269835": "趣味运动会新闻",
    "20260423-c5332a269524": "导师个人简介，非办事信息",
    "20260423-c5332a269527": "导师个人简介，非办事信息",
    "20260505-c2064a269839": "政治理论文章，非办事信息",
    "20260422-c5332a269476": "导师个人简介，非办事信息",
    "20260423-c5332a269542": "导师个人简介，非办事信息",
    "20260311-c6364a267512": "转专业拟录取公示，已过期",
}

DROPS = {
    # 2026-09-17 音小录答疑：被已有完整条目覆盖或空泛
    "pt-8c1ccef378": "可信电子成绩单内容已被 pt-c723948819 完整覆盖",
    "pt-90b7d27828": "学生证补办第一步已被 pt-6b1c448da1 完整覆盖",
    "pt-92f361e0c1": "空泛评价，无独立事实",
    "pt-bac9f3357a": "泛泛守则，无办事信息",
    "pt-c5fff08bd2": "学生证发放已被 pt-6b1c448da1 完整覆盖",
    "pt-da63373fa5": "节假日审批已被 pt-6b1c448da1 完整覆盖",
    "pt-de0ceefd0c": "仅提问标题，无正文",
    "pt-ec9d6fedda": "学生证审核周期已被 pt-6b1c448da1 完整覆盖",
    # 2026-05-03 学生服务大厅：地址与寄语碎片，人物信息并入逐人条目
    "pt-2c443cfbd8": "办公地址已并入汪立宝条，寄语非办事信息",
    "pt-37e152d91a": "办公地址已并入郑蕾条，寄语非办事信息",
    "pt-3d05d73719": "办公地址已并入惠焕云条，寄语非办事信息",
    "pt-56af0001bc": "办公地址已并入刘宇鹏条，寄语非办事信息",
    "pt-9a9ca950e4": "办公地址已并入郝达瑞条，寄语非办事信息",
    "pt-9db8153695": "办公地址已并入杨丽莉条，寄语非办事信息",
    "pt-a80ccebf72": "办公地址已并入黄建条，寄语非办事信息",
    "pt-b9793bb1da": "办公地址已并入赵竞鹤条，寄语非办事信息",
}

Y = "2026-09-17-88875050"
S = "20260503-c2065a269817"

def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def raw_lines(src: str) -> list[str]:
    for sub in SOURCE_DIRS:
        p = (ROOT / "sources" / sub if sub else ROOT / "sources") / f"{src}.txt"
        if p.exists():
            with p.open("r", encoding="utf-8", newline="") as f:
                return f.read().split("\n")
    raise SystemExit(f"源文件不存在：{src}")


def L(src: str, a: int, b: int | None = None) -> str:
    lines = raw_lines(src)
    if b is None:
        b = a
    return "\n".join(x.strip() for x in lines[a - 1:b])


SPECIAL = {
    "pt-8ad75bc917": L(Y, 82) + "\n" + L(Y, 83, 84),
    "pt-8e9980eb37": L(Y, 210) + "\n" + L(Y, 211),
    "pt-8ec76b19d6": L(Y, 200) + "\n" + L(Y, 201),
    "pt-96aba0caf6": L(Y, 212) + "\n" + L(Y, 213),
    "pt-a1814cd4a0": L(Y, 214) + "\n" + L(Y, 215),
    "pt-a503e0a07b": L(Y, 198) + "\n" + L(Y, 199),
    "pt-d98b7f7cd1": L(Y, 19) + "\n" + "\n".join(L(Y, n) for n in range(20, 27)) + "\n" + L(Y, 27),
    "pt-f424ebcc2a": L(Y, 208) + "\n" + L(Y, 209),
    # 学生服务大厅：大厅位置与九位老师的分工和办公地址
    "pt-d9a72f40e6": L(S, 35) + "\n" + L(S, 38),
    "pt-faa4dc5b18": L(S, 43, 45),
    "pt-17cf68e5ea": L(S, 48, 50),
    "pt-0477a6024b": L(S, 53, 55),
    "pt-57b367ed9d": L(S, 58, 60),
    "pt-8c18faa216": L(S, 63, 65),
    "pt-61fde18d96": L(S, 68, 70),
    "pt-f247e8bd51": L(S, 73, 75),
    "pt-79d9c913ca": L(S, 78, 80),
    "pt-3383af386e": L(S, 83, 85),
}

TITLES = {
    "pt-8ad75bc917": "体育场馆预约入口与场地项目",
    "pt-8e9980eb37": "中传研究生院公众号",
    "pt-8ec76b19d6": "中国传媒大学校医院公众号",
    "pt-96aba0caf6": "白杨创汇公众号",
    "pt-a1814cd4a0": "平安中传公众号",
    "pt-a503e0a07b": "中国传媒大学教育服务中心公众号",
    "pt-d98b7f7cd1": "融合服务门户的功能板块",
    "pt-e0887bf915": "仪器设备借用需导师和管理员两步审批",
    "pt-f424ebcc2a": "中传大外部公众号",
    "pt-fd55c5bc90": "体育场馆预约到场须人脸核销，严禁为他人核销",
    "pt-d9a72f40e6": "信息传播学院一层学生服务大厅",
    "pt-faa4dc5b18": "信息传播学院党政办汪立宝老师分工与办公地址",
    "pt-17cf68e5ea": "信息传播学院党政办郑蕾老师分工与办公地址",
    "pt-0477a6024b": "信息传播学院党政办惠焕云老师分工与办公地址",
    "pt-57b367ed9d": "信息传播学院党政办赵竞鹤老师分工与办公地址",
    "pt-8c18faa216": "信息传播学院科研办黄建老师分工与办公地址",
    "pt-61fde18d96": "信息传播学院教学办郝达瑞老师分工与办公地址",
    "pt-f247e8bd51": "信息传播学院教学办刘宇鹏老师分工与办公地址",
    "pt-79d9c913ca": "信息传播学院学工办杨丽莉老师分工与办公地址",
    "pt-3383af386e": "信息传播学院学工办李琳熙老师分工与办公地址",
}

# 大厅条由两段原文拼接，引文取连续的第二段
QUOTES = {
    "pt-d9a72f40e6": L(S, 38),
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
        raise SystemExit(f"目标条目不在 auto_08 分块内：{outside}")
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
        log.append(f"DROP  {pid}  {reason}  |  {str(items[pid].get('answer') or '')[:50]}")
    for pid in sorted(changes):
        log.append(f"FIX   {pid}  {str(items[pid].get('answer') or '')[:50]}  ->  {changes[pid][:70]}")

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
        if ev:
            if pid in QUOTES:
                ev["quote"] = QUOTES[pid]
            elif squash(new) in texts.get(ev.get("src", ""), ""):
                ev["quote"] = new
    for pid in ("pt-e0887bf915", "pt-fd55c5bc90"):
        retitle(items[pid], items[pid].get("answer") or "")

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"已写回，剩余 {len(data['items'])} 条；日志 {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()