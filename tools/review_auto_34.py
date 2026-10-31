"""auto_34 人工复核：体测补充、选课管理、学籍管理、转专业、国家资助、图书馆各馆规章。

判定原则（与 auto_11…auto_33 一致）：
- 保留学生可执行的规则、条件、材料、时间节点与后果
- 删除校内部门职责、委员会组织、制定目的、施行与解释条款、宣传语与表头残句
- 删除已由现行服务条目完整覆盖的重复段落

整源剔除：
- xsc-list：门户导航与通知标题日期拼接，非制度内容
- zz-wenda：问答页标题与页头导航，政策内容已由 zz-jiaoy 与 zxj-* 覆盖
- 中图分类法-0e：分类法科普，无学生可执行事项
- 借阅规则-72c：六层库本阅览与制定目的，已由 lib-jieyue / lib-duzhe-shouze 覆盖
- 文献借阅规定-0：单条赔款标准已由 lib-jieyue 覆盖
- 校园_一卡通_管：教工开通借阅权限与制定目的，非学生事项
- 自助打印_扫描-：与 lib-zizhu-dayin 重复
- 读者留言-d3c：服务承诺与部门转引，无具体渠道
- 读者行为守则-a：仅制定目的
- 通识课教育-8f：课程介绍已由 lib-jiangzuo 覆盖

保留来源：
- tizhi-20：补测一次、入伍免测 95 分、加分上限 10、标准分 100、补测随新生
- xuanke-2：未选视为放弃、扰乱公平取消结果、退课时限、特殊情况、12 学分下限、注册前置、重修范围、先选先得/预选抽签
- xueji-20：退学六情形、结业换毕业、保留入学资格、休学退课、重修补考规则、转学限制、辅修证书
- zhuanzhu：不得申请情形、中外合作限制、单独考核情形、申请表流程、编入年级、学费、学号、异议与造假
- zz-jiaoy：国奖/励志/助学贷款/基层就业/服兵役金额、研究生奖助、勤工助学与三助
- 一卡通寄存柜使用：他人柜内存物、盗刷自负
- 中传学者文库章程：征集范围、到馆与上门捐赠、捐赠证书、所有权、损坏赔偿、终止使用
- 座位预约-72d：续座、未按时返回回收座位
- 校友入馆阅览管理：免费、违规警告与终止、携带文献离馆、离馆检查与清物、不提供科研支持服务
- 研讨间使用守则-：3 人以上团体、非学习活动禁止、违约 1 次禁用 30 天
- 空间预约-3b1：实际使用人信息与严禁虚假预约
- 芸悦读使用规则-：复本 2 册、10 天自动确认收货
- 资源荐购-7c1：芸台购平台
- 馆长信箱-dfa：反映问题需详细描述并留真实联系方式
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_34.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_34.json"
LOG = ROOT / "_review_items" / "applied_auto_34.txt"

DROP_SOURCES = {
    "xsc-list": "门户导航与通知标题日期拼接，非制度内容",
    "zz-wenda": "问答页标题与页头导航，政策内容已由 zz-jiaoy 与 zxj-* 覆盖",
    "中图分类法-0e": "分类法科普，无学生可执行事项",
    "借阅规则-72c": "六层库本阅览与制定目的，已由 lib-jieyue / lib-duzhe-shouze 覆盖",
    "文献借阅规定-0": "单条赔款标准已由 lib-jieyue 覆盖",
    "校园_一卡通_管": "教工开通借阅权限与制定目的，非学生事项",
    "自助打印_扫描-": "与 lib-zizhu-dayin 重复",
    "读者留言-d3c": "服务承诺与部门转引，无具体渠道",
    "读者行为守则-a": "仅制定目的",
    "通识课教育-8f": "课程介绍已由 lib-jiangzuo 覆盖",
}

tizhi_KEEP = {
    "pt-7c708e0101",  # 每年补测一次
    "pt-86c2634aed",  # 入伍退役两年内免测，成绩 95
    "pt-b32362ff8f",  # 四项加分指标，单项上限 10
    "pt-c1ba42099f",  # 补测秋季随新生进行
    "pt-f15f69c244",  # 标准分满分 100
}
tizhi_REASON = "组织实施、双培生范围、解释条款与 tizhi-shijian/tizhi-pingyou-biye 已覆盖的补测评优条款"

xuanke_KEEP = {
    "pt-05b8e09331",  # 未选或错过视为放弃
    "pt-0610924d81",  # 扰乱公平取消选课结果
    "pt-0d4fe50ed6",  # 第二周及以后开课退课时限
    "pt-137eecd295",  # 特殊情况处理四项
    "pt-24d7ff2839",  # 新生入学教育周、在校生学期末集中选课
    "pt-2633a11241",  # 不得代选或盗用账号
    "pt-31fefa829e",  # 仅已选课程获成绩学分
    "pt-4e707e5e66",  # 每学期原则上高于 12 学分
    "pt-53c26c5e65",  # 选课限制三条件
    "pt-6a646d7dcb",  # 自修审核后生效
    "pt-8358905912",  # 注册前置
    "pt-9643ef1cc1",  # 重修仅限不及格必修与无对应重修
    "pt-a3d3a901f2",  # 补退选操作与停开改选
    "pt-c3b3aac4dc",  # 第一周集中补退选
    "pt-ead6de3ab6",  # 先选先得与预选抽签
    "pt-f93f98171a",  # 核查选课结果
}
xuanke_REASON = "本科生院与培养单位职责、课程分类定义、学业指导性表述与施行解释"

xueji_KEEP = {
    "pt-03fdb16637",  # 退学六情形
    "pt-09cb1f0d7c",  # 学期末休学须退未结课课程
    "pt-0ebbf5d0a0",  # 结业证换毕业证
    "pt-10dd48241e",  # 保留入学资格五种情形
    "pt-1a8b767e7d",  # 入伍保留学籍至退役后两年
    "pt-24de173c1f",  # 未选课无考试资格，缺考零分
    "pt-25dfb1e7b5",  # 休学期间四项规定
    "pt-2df7e6cee2",  # 创新创业成果认定学分
    "pt-3304ac8b00",  # 休学时长计入最长年限
    "pt-376e01e3a4",  # 入学请假不超两周
    "pt-3ab07a1dff",  # 保留入学资格时长
    "pt-3b88e4e363",  # 困难学生贷款后注册
    "pt-3f0d2ddd4e",  # 考试纪律与诚信记录
    "pt-53b3c65935",  # 未缴费不予注册
    "pt-552ecc27db",  # 逾期不报到视为放弃
    "pt-582e0ed8cc",  # 保留入学资格只可一次
    "pt-59263413c8",  # 违反招生规定取消学籍
    "pt-5c3131e022",  # 超最长年限不予注册
    "pt-5f2b89336a",  # 退学后学分保留两年
    "pt-85689a5418",  # 必修可重修重考，选修不可
    "pt-87b5744410",  # 转专业四规则含退役优先
    "pt-8b07aaeda8",  # 学制与最长有效年限
    "pt-a32de574ac",  # 重修重考五项规则
    "pt-a606f2a946",  # 创业休学延长年限
    "pt-a86a909f94",  # 交流成绩学分认定
    "pt-aa83cee575",  # 保留入学资格期满申请入学
    "pt-cbc9e3da63",  # 学业留级五种情形
    "pt-d503905c48",  # 重考仍不及格须重修，按 60 分计入
    "pt-d555c08478",  # 辅修证书
    "pt-ee3a0c10e2",  # 违纪作弊课程零分
    "pt-eed9168b1c",  # 注册与暂缓注册
    "pt-f39652a09a",  # 交流项目须备案
    "pt-f4a8bb5308",  # 复查弄虚作假取消学籍
    "pt-f9ba6a7bfb",  # 未备案交流不认定
    "pt-faaf33a73b",  # 不得转学五种情形
}
xueji_REASON = "制定目的、施行解释、申诉与送达程序、部门职责，以及与 xueji-* 现有条目重复的休学/退学/请假/缓考流程"

zhuanzhu_KEEP = {
    "pt-46c3565701",  # 国家规定或录取前约定不得转专业
    "pt-52f72067c2",  # 中外合作仅限同一外方专业间
    "pt-2b1a569a7d",  # 退役复学可单独考核
    "pt-07d7fc1f16",  # 复学无对应年级可单独考核
    "pt-a35e0835f8",  # 人才实验班可单独考核
    "pt-cfe394abdb",  # 特殊情形申请表流程
    "pt-60d655aa33",  # 综合评估后编入年级
    "pt-bb261c9a5e",  # 逾期未确认视为放弃
    "pt-179a1518ee",  # 按转入专业标准缴学费
    "pt-93b6d3844e",  # 学号不变，学生证校园卡更换
    "pt-f51b3108dc",  # 异议 3 个工作日内答复
    "pt-3e50198241",  # 材料造假取消资格
    "pt-ec0181c2af",  # 在籍在校且符合接收条件
    "pt-ae2aef5301",  # 党团组织关系转移
}
zhuanzhu_REASON = "学院与本科生院职责、制定目的、施行解释、工作人员纪律，以及与 zhuanzhuanye 条目重复的流程与条件"

zz_KEEP = {
    "pt-1cafb5ca2f",  # 本专科国奖 12 万名，10000 元
    "pt-3bb0a3ca10",  # 励志奖学金 6000 元
    "pt-e74f42b190",  # 助学贷款每年最高 25000，利息国家承担
    "pt-7222b0b03a",  # 学费补偿代偿减免每年最高 25000
    "pt-e5e207bc68",  # 基层就业补偿每年不超 25000
    "pt-fd950f6623",  # 中西部地区省份名单
    "pt-3c282d5f84",  # 研究生国奖每年 9 万名
    "pt-9d54a77b6a",  # 硕士 7 万×20000，博士 2 万×30000
    "pt-2beab1ea78",  # 研究生国家助学金 6000/15000
    "pt-95a2bd6aef",  # 研究生学业奖学金由高校确定
    "pt-423090c40a",  # 研究生三助岗位津贴
    "pt-f277de5792",  # 勤工助学
}
zz_REASON = "师范生与地方政策、校内资助泛述、绿色通道与困难认定，以及 zxj-*/dk-zhuxue/zb-zizhu 已覆盖的内容"

yikatong_KEEP = {
    "pt-0ada59335b",  # 勿在他人已开箱内存物
    "pt-94ec185e55",  # 一卡通盗刷后果由卡主自负
}
yikatong_REASON = "操作提示与爱护公物，已由 lib-jicungui 覆盖"

wenku_KEEP = {
    "pt-5a390f50c0",  # 著作与讲义手稿等征集范围
    "pt-8b5d9deca7",  # 通信笔记题词等实物范围
    "pt-ca4fc8dfd7",  # 到馆捐赠 115 室
    "pt-25342e590c",  # 200 册以上可上门提取
    "pt-01ca5a878e",  # 颁发捐赠证书
    "pt-d1d5e13b71",  # 接收后拥有所有权与处置权
    "pt-f9221f9628",  # 损坏设备家具照价赔偿
    "pt-13e0fd73bd",  # 劝阻无效终止使用
    "pt-7c776edb4a",  # 禁食品饮料并关电源
}
wenku_REASON = "宗旨、部门职责、解释权、开放对象与阅览规则（已由 lib-xuezhe-wenku 覆盖）、重复的征集范围表述"

zuowei_KEEP = {
    "pt-926a440130",  # 未结束时可续座
    "pt-dbc62365c8",  # 未按时返回自动结束并回收座位
}
zuowei_REASON = "触屏机操作步骤与提示语，已由 lib-zuowei-yuyue 覆盖"

xiaoyou_KEEP = {
    "pt-1d2ffc033c",  # 校友入馆阅览免费，收费服务另付
    "pt-646f84e489",  # 不文明行为口头或书面警告
    "pt-f38cd33075",  # 严重违规暂停或永久终止入馆资格
    "pt-724fcdf5d9",  # 未办外借携带文献离馆视为违规
    "pt-f6b7623f3b",  # 出口离馆检查须配合
    "pt-4f1a5af2c3",  # 离馆带走个人物品
    "pt-763f94cf9a",  # 不提供科研支持服务明细
}
xiaoyou_REASON = "身份认证、服务清单、行为规范、人数限制与解释修订条款，已由 lib-xiaoyou-rg 覆盖"

yantao_KEEP = {
    "pt-b60df90f7c",  # 仅 3 人以上团体使用
    "pt-9c6a57baa6",  # 违约 1 次禁用研讨间 30 天
    "pt-dc5e71c465",  # 不得从事非学习研究活动
}
yantao_REASON = "清洁整理等日常提示，已由 lib-fangjian-yuyue 覆盖"

kongjian_KEEP = {
    "pt-53a7a17ca5",  # 填写实际使用人，严禁虚假或替人预约
}
kongjian_REASON = "预约路径、签到提示与违约记录，已由 lib-fangjian-yuyue 覆盖"

yunyuedu_KEEP = {
    "pt-8078696708",  # 复本 2 册
    "pt-d6447a8727",  # 10 天未确认自动收货
}
yunyuedu_REASON = "使用提示与借购规则，已由 lib-jiangou 覆盖"

jiangou_KEEP = {
    "pt-5ec881852e",  # 芸台购荐购平台
}
jiangou_REASON = "荐购方式与联系方式，已由 lib-jiangou 覆盖"

guanzhang_KEEP = {
    "pt-23766c1db8",  # 详细描述并留真实联系方式
}
guanzhang_REASON = "设立目的与服务承诺"

ANSWER_FIX = {
    "pt-5c3131e022": "超过最长有效学习年限者，不予注册。",
}

KEEP_SOURCES = [
    ("tizhi-20", tizhi_KEEP, tizhi_REASON),
    ("xuanke-2", xuanke_KEEP, xuanke_REASON),
    ("xueji-20", xueji_KEEP, xueji_REASON),
    ("zhuanzhu", zhuanzhu_KEEP, zhuanzhu_REASON),
    ("zz-jiaoy", zz_KEEP, zz_REASON),
    ("一卡通寄存柜使用", yikatong_KEEP, yikatong_REASON),
    ("中传学者文库章程", wenku_KEEP, wenku_REASON),
    ("座位预约-72d", zuowei_KEEP, zuowei_REASON),
    ("校友入馆阅览管理", xiaoyou_KEEP, xiaoyou_REASON),
    ("研讨间使用守则-", yantao_KEEP, yantao_REASON),
    ("空间预约-3b1", kongjian_KEEP, kongjian_REASON),
    ("芸悦读使用规则-", yunyuedu_KEEP, yunyuedu_REASON),
    ("资源荐购-7c1", jiangou_KEEP, jiangou_REASON),
    ("馆长信箱-dfa", guanzhang_KEEP, guanzhang_REASON),
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

    all_keeps: set[str] = set()
    for prefix, keep, reason in KEEP_SOURCES:
        missing = keep - chunk_set
        if missing:
            raise SystemExit(f"{prefix} 保留清单有误，条目不在分块内：{sorted(missing)}")
        all_keeps |= keep
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

    dup = [pid for pid in all_keeps if pid in drops]
    if dup:
        raise SystemExit(f"同一编号既保留又删除：{sorted(dup)}")
    copied = [pid for pid in chunk_ids if pid in all_keeps]
    if len(copied) != len(all_keeps):
        raise SystemExit("保留清单中有条目不属于本分块")

    print(f"整源剔除 {len(DROP_SOURCES)} 个来源，删除 {len(drops)} 条，当前 {len(items)} 条，存留 {len(chunk_ids) - len(drops)} 条")

    for prefix, reason in DROP_SOURCES.items():
        n = sum(1 for p in chunk_ids if p in drops and drops[p] == reason)
        print(f"SOURCE {prefix}  删除 {n} 条：{reason}")

    fixed = 0
    for pid, text in ANSWER_FIX.items():
        if pid not in chunk_set or pid in drops:
            raise SystemExit(f"正文修正条目不在存留范围：{pid}")
        it = items[pid]
        old = str(it.get("answer", ""))
        quote_obj = (it.get("evidence") or {}).get("answer") or {}
        old_quote = str(quote_obj.get("quote", ""))
        if text not in old or text not in old_quote:
            raise SystemExit(f"正文修正与原答案或引文不符：{pid}")
        it["answer"] = text
        quote_obj["quote"] = text
        fixed += 1
    print(f"正文修正 {fixed} 条")

    if dry:
        for pid in chunk_ids:
            if pid in drops:
                text = items[pid].get("answer") or ""
                print(f"DROP  {pid}  {drops[pid]}  |  {text[:70]}")
        for pid in chunk_ids:
            if pid not in drops:
                text = items[pid].get("answer") or ""
                print(f"KEEP  {pid}  |  {text[:70]}")
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
