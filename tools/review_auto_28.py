"""auto_28 人工复核：创新创业学分、体育课程、信息化新生指南、违纪处理、毕业团组织转接。

判定原则（与 auto_17/18/19/20/21/22/23/24/25/26/27 一致）：
- 保留学生可执行的规则、期限、费用、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除面向教职工、网站管理员、项目负责人的程序性文字
- 删除已由现行服务条目完整覆盖的重复段落
- 删除案例故事、劝学套话、残句与表格粘连

整源判断：
- e146f4b6：行政事业性国有资产管理条例，国务院规章，非校园办事（与 auto_27 同源）
- e35b1978：预约入校 OCR 残缺，入校流程已由 fangke-yuyue / xiaomen-jinchu 覆盖
- e9466a16：2024 年中国画博士班招生简章，时效已过
- e9b74298：共青团中央与教育部意见，面向各级团委的工作部署
- ec7add9e：学校“十四五”发展规划，办学目标与建设任务

保留来源：
- e2df7556：创新创业学分认定标准、申报时间、材料与弄虚作假处理
- e4444074：体育课学分构成、专项选择、考核、重考重修免修缓考
- e49b3229：后勤各中心办公地点与电话、公众号入口、垃圾分类
- e53b97c8：校园卡、邮箱、企业微信、校园网认证、正版软件与 AI 平台；
  校园卡与统一认证的办卡、激活、改密、人脸照片已由 xyk-* / it-* 覆盖
- ea0b59c6：考试违纪与作弊的分级处理、学术不端处理
- ebd32b2d：毕业生团组织关系转接类型、时间节点与去向
- ec1b7c4b：图书馆查收查引、查重、馆际互借、报修与代找图书入口
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_28.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_28.json"
LOG = ROOT / "_review_items" / "applied_auto_28.txt"

DROP_SOURCES = {
    "e146f4b6": "行政事业性国有资产管理条例，非校园办事",
    "e35b1978": "预约入校 OCR 残缺，入校流程已由 fangke-yuyue 覆盖",
    "e9466a16": "2024 年中国画博士班招生简章，时效已过",
    "e9b74298": "共青团中央与教育部意见，面向各级团委的工作部署",
    "ec7add9e": "学校“十四五”发展规划，办学目标与建设任务",
}

# 创新创业学分：认定标准、申报时间与材料
e2df7556_KEEP = {
    "pt-20a5757823",  # 每年4月申报
    "pt-8fe03f4ccc",  # 4月1-15申报、16-30认定
    "pt-caa1f91aae",  # 全国/国际竞赛 5/4/3 学分
    "pt-d1af3df5f9",  # 省部级竞赛 3/2/1 学分
    "pt-324127ad35",  # 校级竞赛一等 1 学分
    "pt-2c45c3191c",  # 国家发明专利前三 3 学分
    "pt-2f3e0ea69e",  # SCI/EI 第一作者 3 学分
    "pt-95c6c9f76b",  # 核心期刊第一作者 3 学分
    "pt-be76f8d37c",  # 市级以上文学艺术创作 3/2/1
    "pt-ebac88d945",  # 集体二等奖参与者 1 学分
    "pt-d08e3c1e0d",  # 大创/北京市科研训练结题 3 学分
    "pt-2f85b848b0",  # 创业训练项目结题 3 学分
    "pt-6bf6a3eaf9",  # 创业实践 6/12/3/2 学分
    "pt-249915f109",  # 多个创业项目只能选一项
    "pt-7f7742006f",  # 相同项目按最高级别认定
    "pt-81a8fe48af",  # 创新学分可作实践学分
    "pt-c5754f2749",  # 创业学分可作实践学分
    "pt-9d8c6f7767",  # 申请表交本科教学办
    "pt-d8cc295a5b",  # 5月中旬教务处登录
    "pt-4a22cea36f",  # 争议可书面申请
    "pt-898b41d4fc",  # 弄虚作假取消资格
}
e2df7556_REASON = "制定目的、解释条款、竞赛定义、汇总表流转等程序性文字"

# 体育课程：学分、专项、考核与特殊考核
e4444074_KEEP = {
    "pt-6e5ea88496",  # 体育必修4学分构成
    "pt-159c17426d",  # 四学期考核
    "pt-1abea4cc15",  # 至少2专项、游泳必选一次
    "pt-33b8c67ef5",  # 学期选项制、男女分班
    "pt-1ec2e9fa7b",  # 选定项目不得更改
    "pt-9a988d7fea",  # 成绩综合评定内容
    "pt-12315013df",  # 不及格可重考
    "pt-27e6df8f99",  # 体育缓考流程
    "pt-a78c2103bc",  # 缓考下学期初、按期末占比
    "pt-f633602914",  # 四次体测且达标
    "pt-f30a5a6d6f",  # 2022级起执行
}
e4444074_REASON = "通知抬头、解释条款、与 jwc-bukao / jwc-chongxiu / jwc-tiyu 重复的表述"

# 后勤：各中心地址电话与服务入口
e49b3229_KEEP = {
    "pt-0549a2336c",  # 节能与运行保障中心 65779308
    "pt-2ea5fa0356",  # 饮食服务中心 65779623
    "pt-328c9ea830",  # 校园管理中心 65783600
    "pt-8c87dc7944",  # 后勤服务电话 65783074
    "pt-8bf1875cd9",  # 后勤公众号
    "pt-a0582076fc",  # 公寓中心与家委会电话
    "pt-a6ba500645",  # 公众号栏目与在线选床、报修、购电
    "pt-d0c5e64dbe",  # 报修、空调审批、场地审批
    "pt-e1f3ed0d67",  # 垃圾分类
    "pt-ea37af188b",  # 后勤办公地点
    "pt-ea60f89937",  # 服务监管中心 65783018
}
e49b3229_REASON = "部门职能介绍、服务理念、节能倡议与工程管理职责"

# 信息化新生指南：校园卡与统一认证以外的服务
e53b97c8_KEEP = {
    "pt-0b1173f183",  # WPS365 内容
    "pt-71ebfa618e",  # 正版软件服务平台
    "pt-92ee6239ee",  # 正版软件内容
    "pt-5abaf0d3a6",  # 个人邮箱申请步骤
    "pt-f752179955",  # 企业微信绑定
    "pt-66f40598c5",  # 交通联名卡备选
    "pt-6a5c52dfcb",  # 校园卡与公交卡余额分开
    "pt-0d7eb2fb8b",  # 关闭私有地址避免重复登录
    "pt-aea65cc4d2",  # 校园网认证页面
    "pt-9921dc6ef5",  # 智能体开发平台
    "pt-c2230b1f05",  # AI 能力中心
    "pt-a53284c4b3",  # 中传智算云
    "pt-9ad895bf30",  # 问道中传
    "pt-21ae2ae3e3",  # 融合服务门户
    "pt-b5198027d5",  # 中传云盘
}
e53b97c8_REASON = "校园卡、统一认证、人脸、交通卡与邮箱开通已由 xyk-* / it-* 覆盖，社团与平台入口碎片"

# 考试与学术违纪：分级处理
ea0b59c6_KEEP = {
    "pt-ceaea27d74",  # 口头警告情形
    "pt-527e460ffd",  # 警告至严重警告情形
    "pt-0ec592114b",  # 作弊记过/留校察看并零分
    "pt-0ae71dc086",  # 作弊行为第8-11项
    "pt-33dd72fa8a",  # 作弊行为第3-7项
    "pt-93170727f2",  # 严重作弊开除学籍
    "pt-19ac072fea",  # 代写买卖论文开除
    "pt-1d67ffe604",  # 学术不端处理
    "pt-94678c17cc",  # 发表作品抄袭处理
    "pt-38780f24de",  # 交流学生违纪通知学籍单位
}
ea0b59c6_REASON = "调查取证程序、笔录表格与废止旧规定条款"

# 毕业团组织关系转接：类型、时间与去向
ebd32b2d_KEEP = {
    "pt-027c6d603a",  # 未升学未就业转常住地
    "pt-087701253f",  # 申请期8月31日前
    "pt-38710763d0",  # 常住地接收困难转户籍地
    "pt-3f05a33692",  # 入团志愿书首要档案
    "pt-41fee0797f",  # 已落实单位转单位团组织
    "pt-4bc1d585b5",  # 不得转居住地或户籍地
    "pt-5dc8b2e59a",  # 升学1个月内建组织
    "pt-5f3cf43603",  # 6个月以上应转
    "pt-7c6acf21f3",  # 参军入伍特殊单位库
    "pt-7fe0aa6b75",  # 团员配合转接与档案
    "pt-81cf57bb33",  # 出国境保留组织关系
    "pt-91141d034b",  # 档案纳入学籍或人事档案
    "pt-a8ba5227a1",  # 接收方不得无故拒接
    "pt-b788cb3db5",  # 审核期9月1-30
    "pt-c949a1a028",  # 延迟毕业集中管理
    "pt-cc294d399f",  # 未转出专门支部管理
    "pt-e93bc0b8ac",  # 单位无团组织转驻地
    "pt-ef04a33bef",  # 学校保留6个月最长1年
    "pt-f66db35d49",  # 单位有团组织编入
    "pt-fc787bb6d4",  # 严禁按未就业转户籍
    "pt-fe57b64ad5",  # 10月31日前完成
}
ebd32b2d_REASON = "各级团组织职责、指导检查要求与标题式碎片"

# 图书馆服务入口：查收查引、查重、馆际互借、报修与代找图书
ec1b7c4b_KEEP = {
    "pt-0d06cd3b93",
    "pt-2233873b01",
    "pt-2df9c1bcd6",
    "pt-3eb65aa086",
    "pt-58e75c33c3",
    "pt-5fcad7aa3b",
    "pt-a315a9339a",
}
ec1b7c4b_REASON = ""

KEEP_SOURCES = [
    ("e2df7556", e2df7556_KEEP, e2df7556_REASON),
    ("e4444074", e4444074_KEEP, e4444074_REASON),
    ("e49b3229", e49b3229_KEEP, e49b3229_REASON),
    ("e53b97c8", e53b97c8_KEEP, e53b97c8_REASON),
    ("ea0b59c6", ea0b59c6_KEEP, ea0b59c6_REASON),
    ("ebd32b2d", ebd32b2d_KEEP, ebd32b2d_REASON),
    ("ec1b7c4b", ec1b7c4b_KEEP, ec1b7c4b_REASON),
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
