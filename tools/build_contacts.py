"""从语料里抽取公开联系方式（电话/邮箱/网址），按「用途」归类，生成 contacts.json。

抽取规则：
  - 11 位手机、010- 座机、6577/6578 校内座机
  - 邮箱
  - 上下文：取号码所在行的前后文，用来推断"这是哪个部门、办什么事"
分类依据：来源页面标题 + 正文关键词（报修/购电/成绩单/学籍/网络/图书馆…）

用法：python tools/build_contacts.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"

PHONE_MOBILE = re.compile(r"(?<!\d)(?:1[3-9]\d{9})(?!\d)")
PHONE_LAND = re.compile(r"(?<!\d)(?:010[- ]?\d{8}|6577\d{4}|6578\d{4}|6576\d{4})(?!\d)")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL = re.compile(r"https?://[a-z0-9.-]*cuc\.edu\.cn[^\s\"'）)]*")

# 用途分类：关键词 → 用途名
PURPOSE_RULES: list[tuple[str, re.Pattern]] = [
    ("教师 / 导师", re.compile(r"导师简介|导师|教授|副教授|讲师|教师|电子邮箱")),
    ("校园网 / 网络故障", re.compile(r"校园网|网络认证|上网|wifi|网费|IP地址|无感知")),
    ("校园卡 / 一卡通", re.compile(r"校园卡|一卡通|补卡|挂失|卡务|遗失卡")),
    ("信息化 / 账号", re.compile(r"统一身份|账号|密码|电子邮箱|VPN|信息化处")),
    ("图书馆", re.compile(r"图书馆|借阅|续借|数据库|馆藏|文献")),
    ("宿舍报修 / 水电", re.compile(r"报修|维修|购电|售电|水电|后勤保障")),
    ("成绩单 / 证明", re.compile(r"成绩单|在读证明|盖章|密封")),
    ("学籍 / 学籍异动", re.compile(r"学籍|休学|复学|退学|转专业|保留学籍")),
    ("选课 / 教学运行", re.compile(r"选课|退课|课表|教室借用|教学运行")),
    ("考试 / 四六级", re.compile(r"四六级|CET|考试|缓考|重考|考场")),
    ("奖助 / 贷款", re.compile(r"奖学金|助学金|助学贷款|资助|勤工助学")),
    ("校医院 / 医保", re.compile(r"校医院|门诊|医保|体检|就医")),
    ("财务 / 缴费", re.compile(r"财务|缴费|收费|学费|报销|发票")),
    ("就业 / 档案 / 户口", re.compile(r"就业|档案|户口|派遣|报到证")),
    ("心理 / 咨询", re.compile(r"心理|心港湾")),
    ("保卫 / 安全", re.compile(r"保卫|治安|门禁|消防|大型活动")),
    ("招生 / 学信网", re.compile(r"招生|学信网|学历认证|学位认证")),
]


def purpose_of(title: str, text: str, line: str = "") -> str:
    """先看号码所在行的上下文，再看标题，最后看正文——上下文最准。"""
    for blob in (line, title, text[:400]):
        for name, rx in PURPOSE_RULES:
            if rx.search(blob or ""):
                return name
    return "其他"


def load_indexes() -> dict[str, dict]:
    meta: dict[str, dict] = {}
    for fname in ("index.json", "crawl-index.json", "cdp-index.json", "wechat-index.json",
                  "chsi-index.json", "moe-index.json", "national-index.json",
                  "local-index.json", "huibian-index.json", "extra-index.json"):
        f = SRC / fname
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for k, v in data.items():
            meta[k] = v
    return meta


def context(line: str, limit: int = 60) -> str:
    s = re.sub(r"\s+", " ", line).strip()
    return s[:limit]


def main() -> None:
    meta = load_indexes()
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for p in sorted(SRC.rglob("*.txt")):
        slug = p.stem
        info = meta.get(slug, {})
        title = info.get("title", "") or slug
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue
        if "cuc.edu.cn" in title or True:
            purpose = "其他"
        for i, line in enumerate(text.splitlines()):
            for kind, rx in (("phone", PHONE_MOBILE), ("phone", PHONE_LAND),
                             ("email", EMAIL), ("url", URL)):
                for m in rx.finditer(line):
                    val = m.group(0).rstrip(".,，。")
                    if kind == "url" and not re.search(r"cuc\.edu\.cn/[^\s]*", val):
                        continue
                    if kind == "email":
                        local = val.split("@")[0]
                        if len(local) < 2 or local.isdigit():
                            continue
                    key = (kind, val)
                    if key in seen:
                        continue
                    seen.add(key)
                    ctx_line = context(line, 80)
                    purpose = purpose_of(title, text, ctx_line)
                    # 教师类只对邮箱/网址成立，电话多半是办公室总机
                    if purpose == "教师 / 导师" and kind == "phone":
                        purpose = purpose_of(title, text, "")
                    rows.append({
                        "kind": kind,
                        "value": val,
                        "purpose": purpose,
                        "dept": title[:40],
                        "context": ctx_line,
                        "source_slug": slug,
                        "source_url": info.get("url", ""),
                    })

    # 按用途分组统计
    from collections import Counter
    c = Counter(r["purpose"] for r in rows)
    print(f"抽出 {len(rows)} 条联系方式，覆盖 {len(c)} 类用途")
    for k, v in c.most_common():
        print(f"  {k:<18}{v:>4}")

    out = {"generated": "2026-10-27", "total": len(rows), "items": rows}
    (ROOT / "contacts.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 contacts.json")


if __name__ == "__main__":
    main()
