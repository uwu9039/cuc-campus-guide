"""auto_26 人工复核：图书馆手册（二）、课程评价、校园网、硕士网上确认、公寓信息、控烟等。

判定原则（与 auto_17/18/19/20/21/22/23/24/25 一致）：
- 保留学生可执行的规则、期限、费用、材料、地点、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除面向教职工、财务经办、资产管理员、招标投标人的程序性文字
- 删除残句、表格粘连、模板占位与无信息宣传语
- 已有精选条目完整覆盖的主题，删除原始段落，避免重复接入

整源判断：
- cd88b59e：收费票据管理办法，面向财务经办与开票点
- d02e30b4：通识选课办法，五类课程、8+8 学分、第二学期起选、试听补退选、
  原则上不再补退改、成绩不删除均已由 tongshi-ke 覆盖
- d5087dbc：政府采购招标公告，面向供应商
- d8fe6f48：可信电子系统说明 OCR 严重残缺，操作与成绩单办理已由 jwc-chengjidan 覆盖
- d9a4220c：国有资产管理处职责
- da4dc285：科研专项新闻
- chsi-ben：学信档案身份核验四种方式与 010-67410388 已由 chsi-heshi 覆盖
- chsi-xue：学历/学位查询页导航碎片，已由 chsi-baogao 覆盖
- chsi-yan：16 位验证码、新版报告样式已由 chsi-baogao 覆盖

保留来源：
- c5181fe8：只留古籍阅览与复制、研讨间人数与预约、借书查污损、防火卷帘门；
  借阅、赔偿、楼层、守则、座位、空间预约、开放时间、馆藏规模与数据库介绍均已由 lib-* 覆盖
- c99c4ed3：随堂评价 72 小时内、期末必评、入口二维码、老师可见可回复等问答
- campus-n：流量包4 与 30 元包月不限量、6 终端、自然月清零、2026-11-01 执行时间
- cdad8214：高职实践请假与累计请假留级规则，现行请假条目未含
- cfc80003：打印准考证/申请表、学生确认、填写联系方式三个易漏步骤
- cff85639：照片规格、报考点资格、社保与户籍材料、学历学籍核验、审核流程
- chsi-fan：学历查询范围 2001 年以来、学位查询范围 2008-09-01 以来
- d7defa17：出院 1 个月内交 305、发票明细/处方/诊断证明盖章、建行卡复印件、咨询电话
- d940cbae：各楼床铺规格与朝向、独立卫浴分布、80 度电与电卡、梆子井位置与超市
- d960110e：控烟办法中学生违规三档处理、禁烟区域、吸烟区设置、违规情形与校外人员处理
- da6bcf3c：团籍三材料与补办、重新认定、京粤闽系统、重置密码、介绍信与自行脱团
- dad294b6：京内诊断证明书签章要求、京外知情同意书与下载位置
- dba806a6：提前 3 天预约、礼堂与圆形报告厅容量、使用后清理与转账、超时扣押金、
  学院活动折扣、冲突让位、安全与禁烟规定
- dc7c261c：退学与留级情形及流程、保留学籍与保留入学资格、转学、自修、
  肄业证书、学士学位证明、结业换毕业、成绩单免费 3 份、证书遗失补办、代办委托书
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_26.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_26.json"
LOG = ROOT / "_review_items" / "applied_auto_26.txt"

DROP_SOURCES = {
    "cd88b59e": "收费票据管理办法，面向财务经办与开票点",
    "d02e30b4": "通识选课办法，全部规则已由 tongshi-ke 覆盖",
    "d5087dbc": "政府采购招标公告，面向供应商",
    "d8fe6f48": "可信电子系统说明 OCR 残缺，办理方式已由 jwc-chengjidan 覆盖",
    "d9a4220c": "国有资产管理处职责",
    "da4dc285": "科研专项新闻",
    "chsi-ben": "学信档案身份核验已由 chsi-heshi 覆盖",
    "chsi-xue": "学历与学位查询页导航碎片，已由 chsi-baogao 覆盖",
    "chsi-yan": "在线验证报告说明已由 chsi-baogao 覆盖",
}

# 图书馆手册（二）：古籍阅览复制、研讨间人数、借书查污损、防火卷帘门
c5181fe8_KEEP = {
    "pt-604fc211aa", "pt-8f50cc8f61", "pt-7ff85a2354", "pt-9877ea6381",
    "pt-db75bdfa64", "pt-bebd91b480", "pt-98562060e4", "pt-ac3dc260ab",
    "pt-9cab741900", "pt-a843576be1", "pt-e0b1a32e4b", "pt-d3df6d1cd0",
}
c5181fe8_REASON = "借阅赔偿、楼层布局、行为守则、座位与空间预约、开放时间、馆藏与数据库介绍"

# 课程质量评价：只留带规则的答复，删除问题句与口号
c99c4ed3_KEEP = {
    "pt-0cfb0f7cf1", "pt-8a1999ccf6", "pt-8b24ab4045", "pt-9dde52b044",
    "pt-a13fe293e5", "pt-b4b9966da4", "pt-b84e4dffe7", "pt-c810c6574e",
    "pt-cb77851e4c", "pt-ee99d0808f", "pt-f8135d3e67", "pt-74298deb1f",
    "pt-9a5c3903db", "pt-635adf7243",
}
c99c4ed3_REASON = "只有提问句、口号式鼓励与重复表述"

# 校园网：流量包4、包月不限量、自然月清零与执行时间未进精选条目
campus_n_KEEP = {"pt-6fe1dadad7", "pt-bae6b67cc4", "pt-97a4caa30b"}
campus_n_REASON = "校内不计费、互联网计量、认证页查询已由 net-2026-* 与 it-wangfei 覆盖"

# 高职学籍：实践请假与累计请假留级
cdad8214_KEEP = {"pt-9bef749ed7", "pt-c37760b003"}
cdad8214_REASON = ""

# 2025 转专业操作手册：只留打印准考证/申请表与填写联系方式
cfc80003_KEEP = {"pt-6f2a98a2d5", "pt-c7ef081c0c"}
cfc80003_REASON = "界面截图说明、节点展示与系统确认步骤已由 zhuanzhuanye 覆盖"

# 硕士网上确认：考点资格、照片规格、材料与审核流程
cff85639_KEEP = {
    "pt-01304f1c6c", "pt-0b39411b94", "pt-14dfabf6ee", "pt-196c1ffc71",
    "pt-1db342ffbe", "pt-247eada9d8", "pt-2560ed1b44", "pt-25e1aac54a",
    "pt-2bfdb9d9b9", "pt-2c3b98408d", "pt-31d388c279", "pt-33fbcc04a6",
    "pt-34f2928a54", "pt-3537e862ab", "pt-3619d10d82", "pt-36ac9f68c1",
    "pt-36e2315355", "pt-386f529226", "pt-3d1dc68ace", "pt-445d54f955",
    "pt-455a2f0ddd", "pt-6420d7a20d", "pt-64c71f1f7a", "pt-7566ae33d1",
    "pt-797b766282", "pt-7ad3f275ff", "pt-8637135b01", "pt-9457d714fa",
    "pt-96384a4993", "pt-9740f80e72", "pt-99febed2a9", "pt-9fb1b5aa19",
    "pt-a1a6d6de63", "pt-a505eae798", "pt-af3067f2dd", "pt-af5ee59385",
    "pt-bf460a6962", "pt-cd9d8fb7fb", "pt-d0d19a0ff7", "pt-dda36d623c",
    "pt-e7469b1c12", "pt-e8daafef3c", "pt-f67243d802",
}
cff85639_REASON = "公告抬头、重复的“谨慎上传”提示与显而易见的流程说明"

# 学信网查询范围
chsi_fan_KEEP = {"pt-71b48cb9ed", "pt-fc8c0c751c"}
chsi_fan_REASON = "查询范围罗列与页面导航文字"

# 公费医疗：2025-2026 第二学期报销材料与 305 室投递
d7defa17_KEEP = {
    "pt-2394c401d5", "pt-405e9a8ee8", "pt-46b9103568", "pt-6686f99c25",
    "pt-e82b6d7b53", "pt-f8443be4c4", "pt-c54ca90da9", "pt-c7054657d2",
    "pt-f8e46b803a", "pt-9952fec7ff", "pt-1241a75e5c", "pt-20fdf61c82",
}
d7defa17_REASON = "通知抬头与已过期的 2025 年发票补报时限"

# 公寓信息：床铺规格朝向、卫浴分布、电卡、梆子井位置与超市
d940cbae_KEEP = {
    "pt-1f6d91ada4", "pt-58348e2cf5", "pt-7b3628229d", "pt-8486eff594",
    "pt-956ff2d193", "pt-a7e8120a6d", "pt-d3b08d7bc7", "pt-d67c0979a2",
    "pt-dedcdb07c9", "pt-e8fc7784e5", "pt-ee35b15baa", "pt-035ac0bc80",
    "pt-26e89d7ac4",
}
d940cbae_REASON = "门禁人脸识别、家具尺寸、上下铺编号、80 度免费电、无楼栋名的朝向碎片与开篇导航已由 sushe-* 覆盖"

# 控烟：学生处理、禁烟区域、吸烟区、违规情形与校外人员
d960110e_KEEP = {
    "pt-18b4b397f5", "pt-5536ab2e50", "pt-a2086b38dc", "pt-c33bda0271",
    "pt-e719ba39e2", "pt-c8d21dd235", "pt-6df727730f", "pt-170976a1fb",
    "pt-0ac2144402", "pt-84898431c9", "pt-734e8855a6", "pt-858115028d",
    "pt-0382703f58",
}
d960110e_REASON = "领导小组组成、部门职责、教职工处分、季度巡查与制定目的"

# 党团组织关系：材料补办、重新认定、系统与介绍信
da6bcf3c_KEEP = {
    "pt-449166e99b", "pt-98bfd2eb68", "pt-5f489b9cbb", "pt-49db6ff9d7",
    "pt-25c3e41f5b",
    "pt-d2b86eb910", "pt-bb5547ed99", "pt-24bc0c8a19", "pt-931a3603f2",
    "pt-e5a8cdef9a", "pt-e3a3705784", "pt-d2201f6830", "pt-d23e8d6169",
    "pt-454431f1af", "pt-a8385c7052", "pt-6e9ab2b525", "pt-4e25e35eba",
    "pt-87f389e65c", "pt-35f6029ccb", "pt-6c07d21720", "pt-908717da5e",
    "pt-0863c5a8d5", "pt-77b3caab34", "pt-6a8d58528d", "pt-307f53c584",
    "pt-0d19b18341",
}
da6bcf3c_REASON = "标题与口号、纯提问句、重复的问答导语与页面操作细节"

# 体育免修：京内诊断证明签章、京外知情同意书
dad294b6_KEEP = {"pt-0c70d19e10", "pt-a1733cf1a7", "pt-a87a207a8d"}
dad294b6_REASON = "附件表格粘连与 OCR 残句"

# 公共报告厅：预约、容量、使用后清理、收费与安全
dba806a6_KEEP = {
    "pt-2e34f7d617", "pt-0869dfa940", "pt-34a971a50c", "pt-746aaeb23b",
    "pt-55c751a77b", "pt-5fb815fa8c", "pt-da77c224b7", "pt-1de4dcc3f5",
    "pt-6d570df7cb", "pt-2bf04f2d24", "pt-0815555958", "pt-2a53c9ed0f",
    "pt-1276663d29", "pt-f4925b420f", "pt-6fe9837580", "pt-9cdf638d6f",
    "pt-fe6a18b85b", "pt-df4835c444", "pt-ecdeb9b985", "pt-35278830e0",
    "pt-b87eca28b3",
}
dba806a6_REASON = "A/B/C/D 类定义与逐档费率、价格下调审批、解释与施行条款、章节残句"

# 本科生院融合门户：学籍异动、证明办理与材料规则
dc7c261c_KEEP = {
    "pt-136df2a05d", "pt-623c1b6b1d", "pt-a806ce2516", "pt-4cdfbfb9a2",
    "pt-50c6d0473f", "pt-7153b04754", "pt-85f1c8d3b8", "pt-77eb730b66",
    "pt-15cb476543", "pt-233d53f47e", "pt-379e416295",
    "pt-470f7ddc70", "pt-5e8f755738", "pt-0f22e6883a", "pt-4146265426",
    "pt-9805da9893", "pt-29df0c33c6", "pt-89dd48b111", "pt-3b11887a16",
    "pt-37de98057e", "pt-549f52add6", "pt-3d231eb323", "pt-45af2d958c",
    "pt-ad2316a921", "pt-b53896abc3",
}
dc7c261c_REASON = "教改项目、慕课、教材等教师面向服务，留级与补退选、复学与转专业确认已由 xueji-liuji、jwc-buxuanke、xueji-fuxue、zhuanzhuanye 覆盖"

KEEP_SOURCES = [
    ("c5181fe8", c5181fe8_KEEP, c5181fe8_REASON),
    ("c99c4ed3", c99c4ed3_KEEP, c99c4ed3_REASON),
    ("campus-n", campus_n_KEEP, campus_n_REASON),
    ("cdad8214", cdad8214_KEEP, cdad8214_REASON),
    ("cfc80003", cfc80003_KEEP, cfc80003_REASON),
    ("cff85639", cff85639_KEEP, cff85639_REASON),
    ("chsi-fan", chsi_fan_KEEP, chsi_fan_REASON),
    ("d7defa17", d7defa17_KEEP, d7defa17_REASON),
    ("d940cbae", d940cbae_KEEP, d940cbae_REASON),
    ("d960110e", d960110e_KEEP, d960110e_REASON),
    ("da6bcf3c", da6bcf3c_KEEP, da6bcf3c_REASON),
    ("dad294b6", dad294b6_KEEP, dad294b6_REASON),
    ("dba806a6", dba806a6_KEEP, dba806a6_REASON),
    ("dc7c261c", dc7c261c_KEEP, dc7c261c_REASON),
]


def main() -> None:
    dry = "--dry-run" in sys.argv
    original = ITEMS.read_text(encoding="utf-8")
    data = json.loads(original)
    items = {it["id"]: it for it in data["items"]}

    chunk_ids = []
    for line in CHUNK.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunk_ids.append(line.split()[0])
    chunk_set = set(chunk_ids)

    drops: dict[str, str] = {}
    src_counts: dict[str, int] = {}
    for pid in chunk_ids:
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        for prefix, reason in DROP_SOURCES.items():
            if src.startswith(prefix):
                drops[pid] = reason
                src_counts[prefix] = src_counts.get(prefix, 0) + 1
                break

    unused = set(DROP_SOURCES) - set(src_counts)
    if unused:
        raise SystemExit(f"整源剔除清单有误，分块内找不到：{sorted(unused)}")

    for prefix, keep, reason in KEEP_SOURCES:
        missing = keep - chunk_set
        if missing:
            raise SystemExit(f"{prefix} 保留清单有误，条目不在分块内：{sorted(missing)}")
        seen = 0
        for pid in chunk_ids:
            src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
            if not src.startswith(prefix):
                continue
            seen += 1
            if pid in keep:
                continue
            drops[pid] = reason
        print(f"{prefix} 本块 {seen} 条，保留 {len(keep)} 条")

    log: list[str] = []
    for src, n in sorted(src_counts.items()):
        log.append(f"SOURCE {src}  删除 {n} 条：{DROP_SOURCES[src]}")
    for pid, reason in sorted(drops.items()):
        snippet = str(items[pid].get("answer") or "")[:50].replace("\n", " ")
        log.append(f"DROP  {pid}  {reason}  |  {snippet}")

    survivors = [pid for pid in chunk_ids if pid not in drops]
    print(f"整源剔除 {len(src_counts)} 个来源，删除 {len(drops)} 条，"
          f"当前 {len(data['items'])} 条，存留 {len(survivors)} 条")

    if dry:
        print("\n".join(log))
        return

    for pid in drops:
        data["items"].remove(items[pid])

    if not BACKUP.exists():
        BACKUP.write_text(original, encoding="utf-8")
    tmp = ITEMS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, ITEMS)
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"已写回，剩余 {len(data['items'])} 条；备份 {BACKUP.relative_to(ROOT)}；日志 {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
