"""auto_27 人工复核：2025 修学指南、学位授予细则、实验室安全、入学复查与网站群手册。

判定原则（与 auto_17/18/19/20/21/22/23/24/25/26 一致）：
- 保留学生可执行的规则、期限、费用、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除面向教职工、网站管理员、项目负责人的程序性文字
- 删除已由现行服务条目完整覆盖的重复段落
- 删除案例故事、劝学套话、残句与表格粘连

整源判断：
- dd2f540b：2023 级新生入学资格复查，校内部门工作安排，非学生办理事项
- dd5b83b1：网站群后台操作指南，面向网站管理员
- ddee070c：专业学位博士答辩办法，面向培养单位与导师的内部流程
- e146f4b6：行政事业性国有资产管理条例，国务院规章，非校园办事

保留来源：
- dcc459b1：2025 修学指南，只保留 xueji-* / jwc-* / zhuanzhuanye / fuxiu-baoming /
  tongshi-ke 未覆盖的规则：重考仅一次与成绩核算、缓考 24 小时、保留学籍与休学次数、
  辅修 25/40 学分、微专业、毕业审查时间、成绩单记录不删除、大英分级、处分等级与后果；
  案例故事与宣传语整段删除
- dc7c261c：辅修学习经历证明、保留入学资格、证书损坏补办、照片规格、委托盖章、
  课程免修流程、非京籍因私出境材料、保留入学资格期满入学；教师教改与教材条目删除
- dfb6c69a：实验室安全，只保留学生进实验室要遵守的培训准入、禁止行为、用电与消防、
  危险品与废弃物、特种设备、应急要求；领导小组、责任书模板、督查与处分程序删除
- e04716c7：学士学位授予条件、不授予情形、学分超限、外语水平测试与免试、补授学位
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_27.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_27.json"
LOG = ROOT / "_review_items" / "applied_auto_27.txt"

DROP_SOURCES = {
    "dd2f540b": "2023 级新生入学资格复查，校内部门工作安排，非学生办理事项",
    "dd5b83b1": "网站群后台操作指南，面向网站管理员",
    "ddee070c": "专业学位博士答辩办法，面向培养单位与导师的内部流程",
    "e146f4b6": "行政事业性国有资产管理条例，非校园办事",
}

# 修学指南：保留现行条目未覆盖的规则
dcc459b1_KEEP = {
    "pt-067d2b3602",  # 同一课程仅限重考一次
    "pt-c9cb3d15a3",  # 重考按期末考试成绩占比核算
    "pt-4f95f5d466",  # 缓考提前24小时系统申请
    "pt-3e04580063",  # 选修课不能缓考
    "pt-29653344b4",  # 选修课不组织重考重修
    "pt-c3bd0df72b",  # 缓考后下学期报名考试
    "pt-2c71d44853",  # 保留学籍最多两次
    "pt-6a5c95cf21",  # 创业休学4次、其他2次
    "pt-7ae5b2fd84",  # 休学以学年为单位
    "pt-d71aa6d403",  # 学制4年、最长6年、创业8年
    "pt-144200096b",  # 创业休学证明材料
    "pt-47eb2af82f",  # 保留学籍期间退课
    "pt-4b7a11253c",  # 辅修专业证书25学分
    "pt-7d086d05ba",  # 辅修学士学位40学分+GPA2.0
    "pt-5cddde4aca",  # 辅修与主修学分分别计算
    "pt-343f7587cf",  # 主修毕业辅修终止
    "pt-aa7be489ab",  # 辅修申请五周内
    "pt-d1479dac63",  # 只能修读一个辅修、主修必修全及格
    "pt-8a749286c4",  # 微专业12-20学分、半年或一年
    "pt-56347299f0",  # 微专业大二及以上可报
    "pt-706dc6068f",  # 微专业证书
    "pt-445d8f19b5",  # 微专业学分兑换通识拓展
    "pt-6008ccf727",  # 毕业资格审查五月中旬
    "pt-759895b09a",  # 毕业审核学分清单
    "pt-358c74d3c2",  # 重修重考缓考记录不能删除
    "pt-6778e3f952",  # 选课未退成绩单体现
    "pt-8c79c1de27",  # 大英分级与学分
    "pt-4b0c4e691b",  # 兴趣课程置换大英须4学分
    "pt-12dbe409cb",  # 大英限选不能重考重修
    "pt-4d070ff592",  # 实践创新创业2学分
    "pt-0e0d2e4d64",  # 创新创业学分认定时间
    "pt-b6b750b672",  # 军事技能学分不足无法毕业
    "pt-f497aec809",  # 作弊处分等级
    "pt-1e079f3ee7",  # 违纪处分等级
    "pt-a03de979ce",  # 作弊课程零分
    "pt-aa32b550d3",  # 帮助他人作弊同罪
    "pt-e7b08771b9",  # 处分期间不能评奖评优
    "pt-75169c0c7d",  # 第二次作弊退学
    "pt-2c489b1d44",  # 艺术类12学分留级
    "pt-14adf40cc3",  # 疾病不能继续学习退学
    "pt-6cb31dbd6e",  # 选课形式
    "pt-e702b34316",  # 预选抽签以课表为准
    "pt-172053f7c9",  # 不按要求选课的后果
    "pt-59e7b67049",  # 考试分类
    "pt-598618959a",  # 擅自缺考零分
    "pt-97ec505a86",  # 电子凭证问题邮箱与热线
    "pt-13a3563476",  # 中外合作办学专业互转限制
    "pt-6ff1502ac3",  # 中外合作不能转非中外合作
    "pt-7d69c70de1",  # 一二年级可申请转专业
}
dcc459b1_REASON = "案例故事、劝学套话、已由 xueji-* / jwc-* / zhuanzhuanye 覆盖的重复段落"

# 本科生院服务补遗：辅修证明、保留入学资格、证书补办、照片规格与免修流程
dc7c261c_KEEP = {
    "pt-c3a81d4d42",  # 辅修/双学位学习经历证明
    "pt-c960d9f343",  # 保留入学资格一年
    "pt-cbf0cabcee",  # 证书损坏补办交回原件
    "pt-cc15253afb",  # 照片命名与30K
    "pt-cf2aab7149",  # 本人盖章或委托书
    "pt-eca735c057",  # 课程免修流程
    "pt-fdcb1e4622",  # 非京籍因私出境材料
    "pt-ff295ef17d",  # 保留入学资格期满两周前申请入学
}
dc7c261c_REASON = "教改项目、教材与申报书，面向教师；成绩单与转专业流程已由现行条目覆盖"

# 实验室安全：学生进入实验室要遵守的规则
dfb6c69a_KEEP = {
    "pt-05069f5e20",  # 安全教育培训后按规程实验
    "pt-c88bf00085",  # 掌握办法与规程后方可操作
    "pt-5f64110155",  # 仪器设备培训后操作
    "pt-4c8d9e0164",  # 禁止吸烟烹饪留宿
    "pt-42e7a1e11c",  # 消防器材与通道
    "pt-1ccd386343",  # 用电保护与不得超负荷
    "pt-56a469cdf0",  # 废气废物废液处理
    "pt-2a68776b21",  # 清理实验剩余物与垃圾
    "pt-7bff42da7a",  # 化学品分类分项存放
    "pt-2cbc0522b8",  # 易制毒与剧毒品管理
    "pt-46a7495b30",  # 压力容器等特殊操作
    "pt-74d2385284",  # 特种设备培训取证
    "pt-69e6218b26",  # 知晓应急电话与设施位置
    "pt-a01b9c0675",  # 了解应急程序并参加演练
    "pt-d11577569f",  # 离开时检查水电门窗
}
dfb6c69a_REASON = "领导小组、责任书模板、督查程序、事故处理与处分条款"

# 学士学位授予：条件、不授予情形、外语测试与补授
e04716c7_KEEP = {
    "pt-25a60eb19f",  # 作弊处分未解除不授予
    "pt-263bf1f103",  # 补授学士学位
    "pt-2b5139b68d",  # 退学经历免外语测试
    "pt-3a6b230e49",  # 2018-2020级执行旧细则
    "pt-4a5b3284dd",  # 外语免试对象
    "pt-4e7fb5f6c3",  # 未获毕业证不授予
    "pt-62630b85b7",  # 学分超限不授予
    "pt-64add54ad1",  # 表演专业学位英语二级
    "pt-7352f57a6c",  # 学位授予基本条件
    "pt-737590480d",  # 四级达六级标准
    "pt-9327d71686",  # 未通过外语或超年限不授予
    "pt-a7a70a6830",  # 学术剽窃处记过不授予
    "pt-a835d9b9aa",  # 外语测试与处分解除
    "pt-ac2b6f02e1",  # 第二学士学位英语专业免试
    "pt-c2546d2909",  # 艺术类学位英语三级
    "pt-c4dfbc2cc6",  # 2021级开始执行
    "pt-fc30fbaf62",  # 音乐剧双学位班外语要求
}
e04716c7_REASON = "解释权、印发日期、学院与教务处内部审核程序"

KEEP_SOURCES = [
    ("dcc459b1", dcc459b1_KEEP, dcc459b1_REASON),
    ("dc7c261c", dc7c261c_KEEP, dc7c261c_REASON),
    ("dfb6c69a", dfb6c69a_KEEP, dfb6c69a_REASON),
    ("e04716c7", e04716c7_KEEP, e04716c7_REASON),
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
