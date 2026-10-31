"""auto_29 人工复核：毕业生团组织转接、研究生学籍、本科国奖、体育课、场馆与推免。

判定原则（与 auto_17/18/19/20/21/22/23/24/25/26/27/28 一致）：
- 保留学生可执行的规则、期限、费用、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除面向教职工、后勤职工、项目负责人的程序性文字
- 删除已由现行服务条目完整覆盖的重复段落
- 删除残句、表格粘连、模板占位与无信息宣传语

整源判断：
- ec7add9e：学校“十四五”发展规划，办学目标与建设任务
- ef97da2a：2024 版本科生转专业管理办法，现行 2025 版在 auto_34
- f021d42b：收费票据管理办法，面向财务经办与票据管理员
- f685575d：行政单位国有资产管理暂行办法，非校园办事

保留来源：
- ef0c5328：毕业生团组织关系转接的去向、介绍信、支部 ID 与系统操作；
  组织生活会流程、团员评议与支部建设职责不保留（评议规则已由 tuan-yuan-pingyi 覆盖）
- ef77c7fb：研究生休学、保留学籍、复学、退学、转专业、转学、毕业结业与考核规则；
  适用范围、两级管理、送达方式、解释权与施行日期不保留
- eff9507a：本科生国家奖学金金额、年级、成绩与体测条件、兼得与取消资格
- f0b26842：体育课学时学分、专项选择、重考重修、缓考免修、游泳考核与体测补测；
  通知抬头、组织实施、解释条款与 2018/2019 级执行时间不保留
- f1e7a343：场馆预约本人使用、团体规则、手球馆免费、乒乓球与形体教室位置；
  系统时间与违约次数已由 tiyu-changguan-yuyue 覆盖，体育部电话已由 tiyu-jianshenfang 覆盖
- f2edb8b4：推免基本条件、综合成绩构成、权重、一票否决、取消资格与申诉；
  领导小组组成、名额分配过程与学院细则制定不保留
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_29.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_29.json"
LOG = ROOT / "_review_items" / "applied_auto_29.txt"

DROP_SOURCES = {
    "ec7add9e": "学校“十四五”发展规划，办学目标与建设任务",
    "ef97da2a": "2024 版本科生转专业管理办法，现行 2025 版在 auto_34",
    "f021d42b": "收费票据管理办法，面向财务经办与票据管理员",
    "f685575d": "行政单位国有资产管理暂行办法，非校园办事",
}

# 毕业生团组织关系转接
ef0c5328_KEEP = {
    "pt-082424fdf8",  # 拒转拒接可向上一级团组织反映
    "pt-0c0ff3314b",  # 介绍信抬头写转入支部名称
    "pt-17c4d594b1",  # 年度团籍注册结合教育评议
    "pt-181f011aa8",  # 未确认名称暂不填写，特殊去向在备注标注
    "pt-20355e1d84",  # 升学团员在新生组织创建后申请转出
    "pt-289cbafa43",  # 错误转未落实支部的处理
    "pt-31629dc299",  # 转至外部系统团组织操作
    "pt-35b5a365c8",  # 参军入伍由支部账号转移
    "pt-3cd0398b24",  # 升学工作入伍均需转接
    "pt-3d91fe8fc6",  # 未拿到毕业证可转未落实支部
    "pt-43db64af80",  # 名称不准确会失败
    "pt-4767b8edda",  # 转接是必须办理的手续
    "pt-4b365996ac",  # 试用期用人单位应接收
    "pt-4d7935951e",  # 本校未落实支部介绍信不填抬头
    "pt-4f1e353c0c",  # 智慧团建默认账号密码
    "pt-5176d8fdab",  # 未落实支部是中转站
    "pt-54096987f8",  # 查询组织全称是否存在
    "pt-5523c32083",  # 线上转出流程
    "pt-56f9c237dd",  # 升学退伍兵等转入未落实支部
    "pt-6650643e7b",  # 保留团籍党员可不参加评议
    "pt-69df54415a",  # 不得无故拒转拒接
    "pt-6dfa0d9acc",  # 个人申诉换手机号
    "pt-831355ccdb",  # 手机端无法发起可由支部代发
    "pt-83ce34f060",  # 毕业生团员标记升学或工作
    "pt-83f74b875a",  # 外部转移适用智慧团建
    "pt-840adb6d25",  # 出国学习转出国境支部 3013360
    "pt-8554dbd752",  # 申诉反馈与被拒处理
    "pt-87aa7def29",  # 涉密单位参照，未就业转学社衔接支部
    "pt-8e853bbe4c",  # 入党后是否还需转接
    "pt-920cf6e77e",  # 无法提供纸质盖章介绍信
    "pt-98d5364f22",  # 介绍信日期与电子章
    "pt-a79df484c1",  # 毕业团员 100% 标记
    "pt-b16e81d9a5",  # 28 岁不再保留团籍
    "pt-b2045b21f8",  # 香港同学出国无需线上操作
    "pt-bf0f8378c9",  # 参军入伍与涉密单位由团支书发起
    "pt-c042fb9b48",  # 出国支部名称填写
    "pt-c8aef7a584",  # 未落实就业标记其他
    "pt-ce7f2fe443",  # 忘记密码两种处理方式
    "pt-d38f907a54",  # 智慧团建需完成当地报到
    "pt-d651a6b5ad",  # 团组织 ID 仅京内使用
    "pt-d72c3b8c5e",  # 什么情况转未落实支部
    "pt-dc9543aa53",  # 不及时转接的影响
    "pt-df552d2b5d",  # 学校未落实支部 3216280 保留 6 个月最长 1 年
    "pt-e2fbacb849",  # 不合格团员暂缓团籍注册
    "pt-e9ab438b3f",  # 延迟毕业转入相应年份支部
    "pt-ee52b78db5",  # 已入党未满 28 仍需转接
    "pt-f3200fab62",  # 已落实单位转单位团组织
    "pt-fb31c1f978",  # 青春北京入口
}
ef0c5328_REASON = "组织生活会流程、团员评议细则与支部建设职责，评议规则已由 tuan-yuan-pingyi 覆盖"

# 研究生学籍：休学、复学、退学、转专业、毕业与考核
ef77c7fb_KEEP = {
    "pt-00cccf69c3",  # 休学后离校，路费自理
    "pt-01e105158e",  # 保留入学资格康复后重新办理入学
    "pt-0312313fc9",  # 延期申请时间与审批
    "pt-059137a5c7",  # 复查不合格取消入学资格
    "pt-065fa3f0f2",  # 结业后补答辩时间
    "pt-09121822d2",  # 公共课和已开设课程原则上只能在本校学习
    "pt-0ec550ecf7",  # 转专业第一学年结束前一个月申请
    "pt-16ad0dad21",  # 取消学籍情形
    "pt-1ca8efa93a",  # 网络课程成绩合格取得学分
    "pt-1f3add73e9",  # 应予休学情形
    "pt-208522d7ce",  # 违规取得入学资格取消学籍
    "pt-22739aea9e",  # 退学后学分保留两年
    "pt-229f5ba38a",  # 旷考零分须重修
    "pt-27f220574d",  # 保留入学资格期限与一周内离校
    "pt-2a88b37e67",  # 休学办理流程
    "pt-2d111086fd",  # 入学三个月内复查
    "pt-3100c8e395",  # 伪造诊断不得复学
    "pt-34395cc5c7",  # 休学创业增加两年
    "pt-34b06c02e5",  # 各类研究生基本学制
    "pt-3aa93f65f0",  # 保留学籍期满前一个月复学
    "pt-3ccacf7827",  # 毕业条件
    "pt-3cd1be3e81",  # 退学发肄业证书或学习证明
    "pt-4725537ade",  # 特殊招生形式不得转专业
    "pt-4c66cf0791",  # 缓考参加下一次考核
    "pt-4e189487ee",  # 不得转学情形
    "pt-511ab9eb75",  # 缓考未准以旷考论，缺课四分之一不得考核
    "pt-52053977a8",  # 退学两周内办理离校
    "pt-570c61d89b",  # 保留学籍以学期为单位
    "pt-573691e7de",  # 博士与非全日制不受理转专业
    "pt-5f95dfbcec",  # 未缴学费不予注册
    "pt-65f4ef0d68",  # 最长有效修业年限
    "pt-6b65647cb3",  # 延期后仍不能完成发证书
    "pt-6bb248f52d",  # 转学申请条件
    "pt-74a0d83a4a",  # 未请假以旷课论，特殊原因可缓考
    "pt-75bc9fc7df",  # 新生请假不超过两周
    "pt-786393431f",  # 本人申请退学流程
    "pt-825424d511",  # 定向就业转专业需单位同意
    "pt-829e1e3c34",  # 外校课程需盖章
    "pt-85151c4b2b",  # 答辩未通过按结业
    "pt-85f7d8c943",  # 补考 60 分并标注
    "pt-8ac95f01ec",  # 作弊成绩无效零分
    "pt-8be52a520b",  # 每学期开学两周内注册
    "pt-8ea96ac4d3",  # 退学后两年内办就业手续
    "pt-8fe8720aba",  # 提前毕业申请
    "pt-928b23f619",  # 擅自离校不发肄业证书
    "pt-96ddb1ca9b",  # 保留入学资格情形
    "pt-9983875670",  # 转专业审批与公示
    "pt-9bc62ab132",  # 保留入学资格期满前两周申请
    "pt-9dacae15d2",  # 受处分后表现好可补考重修
    "pt-a25ac1053b",  # 应予退学情形
    "pt-a567b1193a",  # 应办理保留学籍情形
    "pt-a82cd13529",  # 不能按期注册须两周内请假
    "pt-b631953052",  # 助学贷款后可注册
    "pt-c4d573bb9f",  # 新生开学两周内申请保留入学资格
    "pt-c6a7e36732",  # 变更姓名出生日期需法定证明
    "pt-c9c28d2724",  # 成绩记录归档
    "pt-cc3fdb0b06",  # 对退学有异议参照处分程序
    "pt-d15977d954",  # 学业退学情形
    "pt-d1f382ede6",  # 复学时间与诊断证明
    "pt-d2b05eb22f",  # 休学累计不超过两个学期
    "pt-d889c1092d",  # 弄虚作假取得学籍取消
    "pt-d8d546c5fd",  # 证书遗失出具证明书
    "pt-daab7aedc5",  # 缓考申请材料
    "pt-dc0bcf4c1d",  # 退学后不再享受奖助与公费医疗
    "pt-ddd594cfb4",  # 可申请转专业情形
    "pt-e458500356",  # 补答辩通过换发证书
    "pt-f5fdf3ea5e",  # 不受理跨一级学科转专业
}
ef77c7fb_REASON = "适用范围、两级管理、送达方式、解释权、施行日期与内部审批程序"

# 本科生国家奖学金
eff9507a_KEEP = {
    "pt-0def01ea73",  # 国奖可与助学金兼得
    "pt-288e4a9fba",  # 每生每年 8000 元
    "pt-358ac48975",  # 奖励对象与范围
    "pt-4528cc65b6",  # 每学年等额评审
    "pt-5922b9d959",  # 以综合素质评价为主要依据
    "pt-9af9001978",  # 二年级以上可申请
    "pt-bd579e32e4",  # 成绩及格、校一等奖学金条件、博学明智前 10%
    "pt-c8310d14e0",  # 立德修为一票否决
    "pt-ca3a63e1f9",  # 弄虚作假撤销追回
    "pt-e233145fe9",  # 体测良好及以上
}
eff9507a_REASON = "宣传性表述与重复的条件描述"

# 体育课程：学分、专项、重考重修、缓考免修与游泳考核
f0b26842_KEEP = {
    "pt-08f83494bc",  # 游泳任意泳姿中途可换
    "pt-0bc9f48d78",  # 四学期至少 2 个专项，游泳限选一次
    "pt-0be1a6b96d",  # 体育缓考流程
    "pt-13b5d9d43d",  # 重考只有一次，下学期初
    "pt-19aef3d0e7",  # 游泳免测申请
    "pt-1bdb84fadd",  # 本科生须通过游泳考核
    "pt-1dd38bf65e",  # 测试不能拉水线蹬池底
    "pt-2efdaddf6d",  # 游泳合格证
    "pt-386ea61151",  # 59.9 分以下补测一次
    "pt-41c5ae2f0a",  # 选修游泳课通过结课可免测
    "pt-4e53c0b586",  # 体育课必修 144 学时 4 学分
    "pt-76dd8614c4",  # 缺课三分之一重修
    "pt-91bc9ca048",  # 游泳只计游距不计时间
    "pt-a20c5aa5a8",  # 游泳弄虚作假按违纪处理
    "pt-a67d06acc5",  # 选定项目不得更改
    "pt-b7f4d32aff",  # 游泳考核是毕业条件之一
    "pt-badddae6cd",  # 潜泳不超过 15 米
    "pt-f23ffc6521",  # 转身不能有间歇
}
f0b26842_REASON = "通知抬头、组织实施、解释条款与 2018/2019 级执行时间，体测安排与免测已由 tizhi-* 覆盖"

# 体育场馆：本人使用与位置
f1e7a343_KEEP = {
    "pt-4993f7e25b",  # 手球馆按场地预约可带同学
    "pt-a69cba1aae",  # 操场跑道 400 米
    "pt-a9e6e8b6d5",  # 无排练室舞蹈室
    "pt-b3675ef319",  # 手球馆对师生免费
    "pt-b458354049",  # 只限在校师生本人不能代约
    "pt-c8e6432dd1",  # 形体教室位置
    "pt-d2ab6a26bf",  # 形体瑜伽教室位置
    "pt-e3743ff4f5",  # 大活个人预约仅限本人入场
    "pt-ec932a6741",  # 乒乓球位置与是否预约
}
f1e7a343_REASON = "系统时间、违约黑名单与团体申请已由 tiyu-changguan-yuyue 覆盖，体育部电话已由 tiyu-jianshenfang 覆盖"

# 推免：条件、成绩构成与资格取消
f2edb8b4_KEEP = {
    "pt-028bd74ff9",  # 全面发展赋分构成
    "pt-07d3a50b1f",  # 按推免综合成绩排序推荐
    "pt-0bfd2f9799",  # 公示期内书面申诉
    "pt-19392eef90",  # 评价体系构成
    "pt-22c826c8e2",  # 综合成绩公式
    "pt-27df61842f",  # 支教团从专业前 50% 推荐
    "pt-2ac155eab3",  # 智育三年总成绩÷30，学业权重不低于 80%
    "pt-314a57e213",  # 未报备回避取消推免资格
    "pt-3412665690",  # 学生应主动报备回避关系
    "pt-434b1e4d0a",  # B 类奖励加分
    "pt-51c8df34a0",  # 取消推免资格情形
    "pt-704cb47185",  # 思想品德一票否决
    "pt-8405bd2b1c",  # 申诉处理
    "pt-851d2249aa",  # 卓越实验班须满足实验班要求
    "pt-8ee5a5698a",  # 全面发展权重不低于 10%
    "pt-91ce43c3fa",  # 学业表现得分依据
    "pt-9fac2aef0b",  # 未按时提交视为放弃
    "pt-b1bc4bc63a",  # 专项推荐名额定义
    "pt-b6314d1cc2",  # 成绩相同参考记事本与特色赋能
    "pt-b74fdb647f",  # 全面发展赋分公式
    "pt-c3a1b81ba9",  # 普通推荐名额定义
    "pt-c522d1dbb2",  # A 类五育指标
    "pt-c5718a4620",  # 免试与推荐的定义
    "pt-cde84e4b32",  # 综合成绩总分 100
    "pt-f81d86e968",  # 申请基本条件
}
f2edb8b4_REASON = "领导小组组成、名额分配过程、学院细则制定与宣传性表述"

KEEP_SOURCES = [
    ("ef0c5328", ef0c5328_KEEP, ef0c5328_REASON),
    ("ef77c7fb", ef77c7fb_KEEP, ef77c7fb_REASON),
    ("eff9507a", eff9507a_KEEP, eff9507a_REASON),
    ("f0b26842", f0b26842_KEEP, f0b26842_REASON),
    ("f1e7a343", f1e7a343_KEEP, f1e7a343_REASON),
    ("f2edb8b4", f2edb8b4_KEEP, f2edb8b4_REASON),
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
        total = kept = 0
        for pid in chunk_ids:
            src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
            if not src.startswith(prefix):
                continue
            total += 1
            if pid in keep:
                kept += 1
            elif pid not in drops:
                drops[pid] = reason
        print(f"{prefix} 本块 {total} 条，保留 {kept} 条")

    print(f"整源剔除 {len(DROP_SOURCES)} 个来源，删除 {len(drops)} 条，当前 {len(items)} 条，存留 {len(chunk_ids) - len(drops)} 条")

    for prefix, reason in DROP_SOURCES.items():
        n = sum(1 for p in chunk_ids if p in drops and drops[p] == reason)
        print(f"SOURCE {prefix}  删除 {n} 条：{reason}")
    for pid in chunk_ids:
        if pid in drops:
            text = items[pid].get("answer") or ""
            print(f"DROP  {pid}  {drops[pid]}  |  {text[:70]}")

    if dry:
        return

    BACKUP.write_text(original, encoding="utf-8")
    for pid in drops:
        items.pop(pid, None)
    data["items"] = [it for it in data["items"] if it["id"] in items]
    tmp = ITEMS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ITEMS)

    lines = [f"删除 {len(drops)} 条，存留 {len(chunk_ids) - len(drops)} 条"]
    for prefix, reason in DROP_SOURCES.items():
        lines.append(f"SOURCE {prefix}：{reason}")
    for prefix, keep, reason in KEEP_SOURCES:
        lines.append(f"KEEP {prefix} {len(keep)}：{reason}")
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已应用，备份 {BACKUP.name}")


if __name__ == "__main__":
    main()
