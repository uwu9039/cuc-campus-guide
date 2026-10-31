"""auto_02b 补丁：处理 02 复核后残留的序号、残句、重复词与标题拼接问题。

只改白名单里的 id；输出 _review_items/auto_02b_after.txt 供逐条复看。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "items.json"
OUT = ROOT / "_review_items" / "auto_02b_after.txt"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_02.txt"


def suffix_of(title: str) -> str:
    i = title.rfind(" · ")
    return title[i:] if i >= 0 else ""


REPAIRS: dict[str, str] = {
    # ---------- 08e60b19 本科生院常见问题 ----------
    "pt-6f00a003f4": "向学院确认你须重修的课程本学期是否开课，如本学期有相同课程，系统才会开放重修选课。",
    "pt-b1256eb845": "入学未满一学期或者毕业前一年的，不得转入或转出。",
    "pt-d09811aee7": "休学、保留学籍期满，未在学校规定期限内提出复学申请或者申请审批不合格的，学校可予退学处理。",
    "pt-dd4232acea": "学生申请姓名变更需要上传以下材料：（一）学生本人申请（包含改名原因，本人手写签名、申请时间和手机号码）；（二）学生原名字的身份证复印件（正反面）；（三）学生新名字的身份证复印件（正反面）；（四）学生户口本复印件正面（含姓名、身份证号等信息）；（五）学生户口本复印件背面（含变更项目、变更时间）。",
    "pt-e55b4d32d9": "自修是针对境外交流或转专业的学生，必修课与必修课之间上课时间冲突，无法按照正常课程安排上课时，通过自主学习的方式完成必修课程的学习和考核。",
    "pt-8054df3b8c": "步骤4：输入申诉所需信息及联系信息，申诉完成后可正常登陆。",
    # ---------- 0c732fe9 课程置换与学分认定 ----------
    "pt-2fff7404f8": "采取学分认定方式进行转换的，境（内）外交流的校外课程，学生成绩单中不记载该门课程的名称、学分及成绩，不参与平均分及绩点（GPA）计算。",
    "pt-642a92a3c3": "境（内）外交流修读课程成绩为等级制，如所修读学校提供等级制与百分制成绩转换说明的，按照转换说明进行百分制转换，其中，转换说明为成绩等级区间的，统一取中间值。",
    # ---------- 11bc34c4b4 设备共享借用 ----------
    "pt-de1f88a679": "设备共享借用入口于2023-11-14发布。线上流程上线后，设备共享中心借用申请审批更加便捷。咨询电话：65779263，地址：北京市朝阳区定福庄东街1号中国传媒大学25号楼。",
    # ---------- 16fe5655 WPS365 使用手册 ----------
    "pt-cf7890ffa2": "电脑客户端：点击右上角头像进入个人中心，管理在线设备。",
    "pt-1fdafc586f": "支持按类型、位置、时间等条件搜索；在搜索框输入关键词，即可搜到包含该关键词的文档、文件夹、团队。",
    "pt-285a34017a": "微信：关注“WPS办公助手”公众号，访问“个人中心”，进入“设置”－“账号与安全”，点击“登录设备管理”。",
    "pt-e412cf0e2d": "手机APP：点击头像或右下角的“我”，进入“账号与安全”，点击“登录设备管理”。",
    # ---------- 17b5a33f 人事工作回答 ----------
    "pt-de3f7bef5b": "被查的档案，不能带出阅档室查阅，不能复制、拷贝人事档案材料。",
    # ---------- 18fec1b5 2025 硕士复试录取办法 ----------
    "pt-540a1559ba": "学校不允许研究生同时攻读两个以上（含）不同层次或相同层次的学位。有此情形的考生，应在复试前主动告知我校招生处。",
    # ---------- 1a5c2d43 人事工作回答 ----------
    "pt-a74d595463": "档案管理人员审核鉴别，整理出应归档材料和不在归档范围的材料。",
    # ---------- 18fec1b5 复试考核方式及内容 ----------
    "pt-8a24963163": "复试考核方式：我校2025年全国硕士研究生招生考试复试考核采用现场考试方式进行，考试地点为中国传媒大学。",
}

STRIP_PREFIX: dict[str, str] = {
    "pt-1e2e810899": "1.",
    "pt-221e3f70be": "7.",
    "pt-25cea94ee4": "2.",
    "pt-281f64333a": "3.",
    "pt-2c8c94fef8": "1.",
    "pt-300fa73bb5": "3.",
    "pt-310e9188d6": "（2）",
    "pt-3353510fff": "（1）",
    "pt-34d1c44eb7": "2.",
    "pt-3efb7a7400": "3.",
    "pt-51bb639d19": "（3）",
    "pt-54fd1cfaf7": "4.",
    "pt-aff3d77f24": "2.",
    "pt-b0eb19099d": "2.",
    "pt-b1e862c139": "（4）",
    "pt-c090a58723": "1.",
    "pt-c23548acb4": "1.",
    "pt-dc6d83799b": "2.",
    "pt-e663a885bd": "（3）",
    "pt-f2931691ca": "（2）",
    "pt-fd22dd6d85": "6.",
}

DELETES = {"pt-71ecaa61b6", "pt-4ad48adb78"}

ALIAS_ADD = {"pt-540a1559ba": ["有此情形的考生", "主动告知招生处"]}


def main() -> None:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    items = d["items"]
    idx = {it["id"]: it for it in items}
    changes: list[tuple[str, str, str]] = []
    notes: list[str] = []

    def record(iid: str, it: dict, old: str, new: str) -> None:
        changes.append((iid, old, new))
        it["answer"] = new
        suf = suffix_of(it.get("title") or "")
        head = new[:40] + ("…" if len(new) > 40 else "")
        it["title"] = head + suf
        al = it.get("aliases") or []
        if al and (al[0].endswith("…") or old.startswith(al[0])):
            al[0] = head

    for iid, new in REPAIRS.items():
        it = idx.get(iid)
        if not it:
            notes.append(f"MISSING {iid}")
            continue
        old = it.get("answer") or ""
        if old == new:
            notes.append(f"NO-OP   {iid}")
            continue
        record(iid, it, old, new)

    for iid, pre in STRIP_PREFIX.items():
        it = idx.get(iid)
        if not it:
            notes.append(f"MISSING {iid}")
            continue
        old = it.get("answer") or ""
        if iid in REPAIRS:
            notes.append(f"DUPLICATE-CFG {iid}")
            continue
        if not old.startswith(pre):
            notes.append(f"PREFIX-NOT-FOUND {iid} {pre!r} -> {old[:24]!r}")
            continue
        new = old[len(pre):].lstrip()
        if old == new:
            notes.append(f"NO-OP   {iid}")
            continue
        record(iid, it, old, new)

    for iid, extra in ALIAS_ADD.items():
        it = idx.get(iid)
        if not it:
            notes.append(f"MISSING-AL {iid}")
            continue
        al = it.setdefault("aliases", [])
        for a in extra:
            if a not in al:
                al.append(a)

    before = len(items)
    d["items"] = [it for it in items if it["id"] not in DELETES]
    d["updated"] = "2026-10-30"

    DATA.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    with OUT.open("w", encoding="utf-8") as o:
        for iid, old, new in changes:
            o.write(f"### {iid}\nOLD: {old}\nNEW: {new}\n\n")

    print(f"修改 {len(changes)} 条，删除 {before - len(d['items'])} 条，剩余 {len(d['items'])} 条")
    if notes:
        print("提示：")
        for n in notes:
            print("  ", n)

    ids = []
    for line in CHUNK.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        ids.append(line.split("|", 1)[0].split()[0])
    touched = set(REPAIRS) | set(STRIP_PREFIX) | DELETES
    print(f"02b 配置 {len(touched)} 条，其中在 auto_02 内 {len(set(ids) & touched)} 条，"
          f"不在 chunk 内 {sorted(touched - set(ids))}")


if __name__ == "__main__":
    main()
