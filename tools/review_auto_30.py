"""auto_30 人工复核：学博/专硕/专博培养、硕士选题与匿名评阅、博物馆、社团、户口与军训。

判定原则（与 auto_17…auto_29 一致）：
- 保留学生可执行的规则、期限、费用、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除已由现行服务条目完整覆盖的重复段落
- 删除残句、表格粘连、模板占位与无信息宣传语

整源判断：
- f685575d：行政单位国有资产管理暂行办法，非校园办事
- f694bb0e：2025 年 5 月平台培训通知，平台入口已由中传智算云条目覆盖
- f6e9cd2f：门急诊时间与医事服务费已被 xyy-menzhen-shijian 完整覆盖
- f722505e：大屏阅览区已由 lib-daping-yuelan 覆盖，其余为设备参数与宣传语
- f917f291：公费医疗问答已被 xyy-gongfei 完整归纳
- fa42d232：违纪条款碎片，缺处分档次与处理程序
- fb5663fe：事业单位国有资产管理暂行办法，非校园办事
- fb6cf13c：教务员手册内部参考资料，学籍案例与经办流程已有对应条目
- fbe97680：OCR 残缺的申请表模板，无可读规则

保留来源：
- fb1675e0：学博培养环节、文献、资格考试、选题、中期、评阅、预答辩与答辩规则
- fb45dc5b：学博答辩三分之二通过、未通过转毕业答辩、两次未通过取消资格
- ffb0eed1：账号申诉后的生效时间与手持证件照上传
- hb0277ac：学硕基本文献考试方式、次数、成绩与时间
- hb0807a6：专博答辩主要环节不少于 2 小时
- hb1a4f11：传媒博物馆开放时间、团体与新生绿色通道预约
- hb1c44b2：硕士选题报告专家小组、成绩、流程与变动重做
- hb1de9b9：专博毕业作品展示考核的委员会、表决与时间要求
- hb1f31e1：专硕培养环节、文献、实践学分、选题、预答辩与答辩规则
- hb2138ae：研究生境外课程认定与学分转换条件、比例与材料
- hb33c2d1：硕士匿名评阅送审、回避、复核与未通过处理
- hb42a3ca：社团活动与大型活动审批流程、材料与人数门槛
- hb49833f：集体户口借卡与迁出规则，以及退役士兵优待政策
- hb4b8c33：军事课学分、免训缓训、请假、考核与军训纪律
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_30.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_30.json"
LOG = ROOT / "_review_items" / "applied_auto_30.txt"

DROP_SOURCES = {
    "f685575d": "行政单位国有资产管理暂行办法，非校园办事",
    "f694bb0e": "2025 年 5 月培训通知，平台入口已由中传智算云条目覆盖",
    "f6e9cd2f": "门急诊时间与医事服务费已被 xyy-menzhen-shijian 完整覆盖",
    "f722505e": "大屏阅览区已由 lib-daping-yuelan 覆盖，其余为设备参数与宣传语",
    "f917f291": "公费医疗问答已被 xyy-gongfei 完整归纳",
    "fa42d232": "违纪条款碎片，缺处分档次与处理程序",
    "fb5663fe": "事业单位国有资产管理暂行办法，非校园办事",
    "fb6cf13c": "教务员手册内部参考资料，学籍案例与经办流程已有对应条目",
    "fbe97680": "OCR 残缺的申请表模板，无可读规则",
}

# 学术学位博士培养
fb1675e0_KEEP = {
    "pt-043b7a81ba",  # 社会服务不少于 1 项
    "pt-0673305186",  # 文献 120 种，文学艺术 50，工学 30
    "pt-06f65b4293",  # 答辩主要环节 3 小时 / 2 小时
    "pt-10756ad913",  # 入学四周内制定课程学习计划
    "pt-22c4a6faf6",  # 答辩委员会可建议授予硕士学位
    "pt-28eb13d876",  # 答辩委员会五至七名，含两至三名校外
    "pt-2ccff7e68a",  # 入学四周内制定科研训练计划
    "pt-2f94b49528",  # 国内会议 2 次或暑期学校 1 次
    "pt-43272e0e22",  # 硕博连读与直博适用本规定
    "pt-47051999e0",  # 第四学期参加资格考试
    "pt-48bc77af48",  # 中期考核须完成二分之一论文
    "pt-4cfcda3f1f",  # 预答辩在答辩 30 天前
    "pt-5447462562",  # 文学艺术类学分要求
    "pt-556f3b8b5b",  # 中期考核前完成课程
    "pt-5672557738",  # 培养环节四项
    "pt-59654bbae9",  # 考核须本人申请
    "pt-59fc337ddd",  # 资格考试三次安排
    "pt-66b3db5ace",  # 匿名评阅不早于第八学期
    "pt-6d8f69f8b0",  # 结业审核
    "pt-6f0a9fec89",  # 毕业审核
    "pt-6f794b34dd",  # 通过资格考试方可进入学位论文
    "pt-8456b89806",  # 学位论文答辩计 2 学分
    "pt-8b1afe6d85",  # 培养方案以二级学科为单位
    "pt-8bf0565ed1",  # 博导组联合指导
    "pt-8c6452b77c",  # 资格考试延迟申请
    "pt-8d18f2f5f4",  # 读书报告不少于 2 次
    "pt-8e7f145c3a",  # 中期考核目的
    "pt-93461ff285",  # 基础文献按一级学科
    "pt-94b9fa201b",  # 五位校外专家匿名评阅
    "pt-9c8022f16d",  # 学位授予流程
    "pt-9fa4cb0339",  # 全日制培养方式
    "pt-a10831fec9",  # 文献包括基础与专业
    "pt-a181139af3",  # 选题报告内容
    "pt-a1d41b770b",  # 工学类学分要求
    "pt-a352e5d8eb",  # 答辩前一周送交委员
    "pt-a3e87c0262",  # 结业后重新申请学位
    "pt-a533397eda",  # 资格考试前完成文献阅读
    "pt-a8d6cf86fc",  # 补修核心课程
    "pt-aae8e4d818",  # 独立完成国家级项目申报书
    "pt-abb011ed9c",  # 延期与最长有效修业年限
    "pt-b5dfb22f31",  # 科研训练学分要求（教学实践）
    "pt-b982f7a7a1",  # 中期考核时间
    "pt-bc1ac3f7d4",  # 笔试加面试
    "pt-ce6cefe506",  # 资格考试目的
    "pt-d8bfae1d94",  # 学位论文工作环节
    "pt-da350c1540",  # 学位论文本人独立完成
    "pt-da8596b67a",  # 答辩未通过三个月后重新申请
    "pt-dbcbd3e263",  # 国际会议 1 次或境外交流
    "pt-e171852502",  # 选题报告在资格考试后进行
    "pt-e6b45cb083",  # 申请答辩条件
    "pt-e79af6e8f6",  # 普博、硕博连读、直博
    "pt-ebd4f74913",  # 每学期至少 1 次学术汇报
    "pt-ec0eeefdf0",  # 答辩前查重
    "pt-f1c30fafcd",  # 选题报告目的
    "pt-fbeb9e9ab8",  # 匿名评阅与中期间隔一学期
    "pt-fc68f52182",  # 答辩前须预答辩
}
fb1675e0_REASON = "制定依据、培养目标、培养方案定义、责任博导职责、施行与废止条款及重复的委员会表述"

# 学术学位博士答辩工作办法
fb45dc5b_KEEP = {
    "pt-0efb0973ca",  # 责任博导不得担任答辩委员
    "pt-266b94b81c",  # 未通过三个月后重新申请一次
    "pt-292d37c63f",  # 三分之二以上同意方为通过
    "pt-33e3ea0ae0",  # 答辩须经研究生院批准
    "pt-3646295953",  # 未通过可转毕业答辩
    "pt-52eabb5f80",  # 答辩程序
    "pt-9051a9528d",  # 答辩时长与后续程序
    "pt-ae9b938988",  # 答辩委员会组成
    "pt-bf2ff3fd83",  # 决议书与记录表归档
    "pt-f13938db27",  # 未通过可建议授予硕士学位
    "pt-fc8e9ca88d",  # 两次未通过取消资格
    "pt-ff3f98b526",  # 答辩前一周送交委员
}
fb45dc5b_REASON = "制定依据、答辩目的、责任博导出席说明与旧规定废止"

# 统一身份认证账号申诉
ffb0eed1_KEEP = {
    "pt-0d85d0c9d9",  # 申诉后一个工作日可用新手机号登录
    "pt-60adb4e7fd",  # 上传本人出镜手持证件照
}
ffb0eed1_REASON = "申诉入口与适用情形已由 it-shensu 覆盖，步骤碎片不保留"

# 学术学位硕士基本文献考试
hb0277ac_KEEP = {
    "pt-0cd3cd79d8",  # 所有学硕笔试，文科面试
    "pt-11d0f997eb",  # 延缓考试两周前申请
    "pt-1cb5cd15f6",  # 三次考试机会
    "pt-1ccd14aecd",  # 笔试闭卷加面试
    "pt-200264ac11",  # 导师不得担任面试委员
    "pt-465b4ab94a",  # 考试一天，笔试半天
    "pt-48122dedfb",  # 考试前完成阅读
    "pt-685404d30b",  # 双通过 60 分计 2 学分
    "pt-789f7e03a4",  # 考试小组不少于五人
    "pt-a5c2bb445a",  # 考试目的
    "pt-aa90cc22d9",  # 面试委员会三至五名
    "pt-bb741a9b10",  # 面试由培养单位组织
    "pt-d599d46c5c",  # 第三、四、五学期考试
}
hb0277ac_REASON = "可适当提高标准、笔试组织、小组制定细则与旧文件废止"

# 专业学位博士答辩
hb0807a6_KEEP = {
    "pt-6c627e9cdc",  # 专博答辩主要环节不少于 2 小时
}
hb0807a6_REASON = ""

# 传媒博物馆
hb1a4f11_KEEP = {
    "pt-0b5f881de2",  # 校外团体预约
    "pt-1cadb7737c",  # 开放时间
    "pt-25cd7445d4",  # 新生绿色通道
    "pt-98b093d550",  # 团体预约一周前电话并交表
    "pt-b9edd2fa46",  # 10 人以上团体，只接受电话预约
    "pt-d21eee37d7",  # 预约表与开馆时间
    "pt-df4dd55c85",  # 新生绿色通道表与分组
}
hb1a4f11_REASON = "博物馆简介、荣誉、合作项目与馆方内部确认表述"

# 硕士选题报告
hb1c44b2_KEEP = {
    "pt-06ef3a3107",  # 选题报告目的
    "pt-0d836e9881",  # 专家小组组成
    "pt-1d9a5aa3c3",  # 60 分通过
    "pt-6518f1cb3e",  # 选题依据内容
    "pt-747f25e2e3",  # 文献考试后进行
    "pt-7742192ec6",  # 题目变动重新组织
    "pt-774938aef1",  # 选题报告会程序
    "pt-964d47363f",  # 不通过重新申请
    "pt-b56e5814fd",  # 责任导师可任成员不可任组长
    "pt-ddaaf01fd4",  # 申请表与导师同意
    "pt-e42824633d",  # 审核选题依据与方案
}
hb1c44b2_REASON = "归档要求、预审机制、制定依据与 2024 级执行时间"

# 专博毕业作品展示考核
hb1de9b9_KEEP = {
    "pt-125a18fe68",  # 须经责任博导与单位同意
    "pt-1d957c4298",  # 三分之二以上同意通过
    "pt-2015a707c0",  # 责任博导不得任成员
    "pt-3db102d2d6",  # 考核方案报备案
    "pt-438005df56",  # 委员会审查并提修改意见
    "pt-534a80e4ea",  # 作品考核前一周送交
    "pt-59ae669bdf",  # 责任博导回避
    "pt-5be2ecbd14",  # 毕业作品形式
    "pt-67b9eb5fd9",  # 委员会组成
    "pt-7ec40dccb8",  # 双考核须公开展映
    "pt-b9d517f11e",  # 责任博导出席并介绍
    "pt-c95befeb53",  # 匿名评阅通过后考核
    "pt-d926028b7d",  # 委员会名单备案
    "pt-d989173a5c",  # 毕业作品水准要求
    "pt-e7c28226f5",  # 考核表归档
}
hb1de9b9_REASON = "施行日期、单位负责人职责与重复的答辩时长表述"

# 专业学位硕士培养
hb1f31e1_KEEP = {
    "pt-0010087421",  # 选题报告在文献考核后
    "pt-00b160c287",  # 实践能力考核在选题后
    "pt-0350e241ad",  # 文献 40 种，著作 10 种
    "pt-0eef384eae",  # 全日制与非全日制培养
    "pt-104e9f6e73",  # 延迟考核两周前申请
    "pt-120dc8f894",  # 个人培养计划
    "pt-13455f789b",  # 文献考核小组
    "pt-1473af1ff8",  # 考核前完成阅读
    "pt-14f30f7949",  # 学位评定委员会投票
    "pt-1585f96a4b",  # 毕业答辩 2 学分
    "pt-168c3a634f",  # 通过文献考核进入作品与论文
    "pt-18a7636604",  # 基本学制两年
    "pt-1f86d36f05",  # 文献考核 2 学分
    "pt-1fdab54aa4",  # 延期两年最长四年
    "pt-203d874ab4",  # 未通过三个月后重新申请
    "pt-250c64973e",  # 选题报告内容
    "pt-2538a0ee9b",  # 培养环节四项
    "pt-2adbf20e27",  # 答辩委员会三至五名含校外
    "pt-2b5d030e46",  # 申请答辩条件
    "pt-2ce23adf7c",  # 创作实践等专业实践形式
    "pt-34a892c7ee",  # 培养方案按类别制定
    "pt-3eed678316",  # 专业实践不少于 6 学分
    "pt-4054084463",  # 结业审核
    "pt-42f6848243",  # 每项成果 1 学分
    "pt-43fb23ca1f",  # 选题预审
    "pt-4714b2708f",  # 选题报告内容要求
    "pt-4cec0ed814",  # 单考核须预答辩
    "pt-50e405738a",  # 答辩前一周送交
    "pt-5481f321cd",  # 实践能力考核目的
    "pt-633e22f3a8",  # 两次答辩未通过无资格
    "pt-6f8caa6daf",  # 第二次考核未通过终止培养
    "pt-70ecf899ec",  # 单考核可不做作品展示
    "pt-718d618a2f",  # 毕业、学位与结业条件
    "pt-7313476b88",  # 社会服务 1 学分
    "pt-7317f197d6",  # 双考核须公开展映
    "pt-7c279c2e98",  # 考核须本人书面申请
    "pt-900678b212",  # 作品考核未通过可参加答辩
    "pt-90f048bb64",  # 作品考核在答辩前或同时
    "pt-92dae8dbd6",  # 均通过可申请硕士学位
    "pt-9655bc2d04",  # 课程学分要求
    "pt-99be644a09",  # 文献考核第二、三学期
    "pt-9b4edb379c",  # 毕业审核
    "pt-9e18fad79b",  # 预答辩 30 天前，三至五名
    "pt-a71d2046a4",  # 学位论文答辩 2 学分
    "pt-aa15a40b1a",  # 未达学位标准可申请毕业答辩
    "pt-ab4f84bceb",  # 实践能力考核资格
    "pt-acf55c80b2",  # 基础文献与方向文献
    "pt-adb48609e9",  # 匿名评阅通过后进入答辩
    "pt-ae8682dff3",  # 单考核毕业条件
    "pt-b178eeac33",  # 第二学期参加文献考核
    "pt-b4d92e6874",  # 成绩加权计算
    "pt-b695abf2bd",  # 学位授予流程
    "pt-b6b9e1d308",  # 全日制与非全日制分别制定方案
    "pt-bb09ff574a",  # 文献包括基础与方向
    "pt-bb37ed89f6",  # 答辩前查重
    "pt-beba763d91",  # 学术交流 1 学分
    "pt-c79d3096f1",  # 文献类型
    "pt-caf965993a",  # 入学四周内课程计划
    "pt-d71aa54633",  # 同一专家委员会评议
    "pt-db502e887a",  # 未达学位要求重新申请
    "pt-dc3013dc16",  # 缺考 0 分，考核形式
    "pt-dd4796692f",  # 实践能力考核 2 学分
    "pt-de76a0538d",  # 导师组联合指导
    "pt-e90636e59c",  # 选题报告目的
    "pt-eaad026ef9",  # 毕业答辩委员会组成
    "pt-f2deccbd35",  # 补修核心课程
    "pt-f8d1461c9f",  # 文献考核目的
    "pt-fbb3a4069c",  # 毕业作品与论文工作环节
    "pt-fdae1cb39c",  # 入学四周内专业实践计划
}
hb1f31e1_REASON = "制定依据、培养目标、课程体系理念、培养方案内容、责任导师职责、2024 级执行时间与重复的匿名评阅表述"

# 研究生境外课程认定
hb2138ae_KEEP = {
    "pt-024fcd5a0f",  # 回国 3 个月内申请
    "pt-42e4ff0a29",  # 认定学分不超过 50%
    "pt-4705804d63",  # 认定原则
    "pt-4e2694aae9",  # 因私赴境外不予认定
    "pt-8e2562fd92",  # 因公按协议转换
    "pt-a2b241dd93",  # 申请表与材料
    "pt-e9abca4333",  # 成绩单标注转换
    "pt-ed2cfa4d6c",  # 成绩换算
}
hb2138ae_REASON = "制定目的与废止条款"

# 硕士匿名评阅
hb33c2d1_KEEP = {
    "pt-0bc1d4a389",  # 回避申请材料
    "pt-1ca83d036d",  # 培养单位检查材料
    "pt-1e1828dec4",  # 学术复核为最终结果
    "pt-22304ddf24",  # 专硕两位专家含校外
    "pt-27e2fd2c71",  # 半数以上同意答辩可毕业答辩
    "pt-29683663c6",  # 增聘两名复评
    "pt-317f9430c2",  # 可申请其他平台送审
    "pt-323db98629",  # 学硕送教育部平台
    "pt-53a3d4c016",  # 半数以下同意答辩再次送审
    "pt-58a7a66829",  # 不适用同等学力
    "pt-67bf80fbcc",  # 无专家接审须告知
    "pt-79e6634c13",  # 2025 年起执行
    "pt-7fcca9b994",  # 均同意方为通过
    "pt-a0b3ffefd4",  # 最早最后学期评阅
    "pt-a114d93cf0",  # 一位不同意可学术复核
    "pt-abd3cdb1f7",  # 同等学力至少三位校外
    "pt-bd31d15274",  # 复评均同意视为通过
    "pt-cb88d41874",  # 查重后进入评阅
    "pt-dd6d15a651",  # 学硕两位校外
    "pt-ed48ed2823",  # 双向匿名
    "pt-ef4c620fbe",  # 最多回避三名专家
    "pt-f2ecc0d241",  # 专硕送专业平台
}
hb33c2d1_REASON = "总体安排、材料归档、制定依据与两级管理"

# 社团活动
hb42a3ca_KEEP = {
    "pt-05a4720b62",  # 日常活动审批流程
    "pt-0a9930e234",  # 少于 50 人预约
    "pt-24e3d97916",  # 审批材料
    "pt-313ef07a92",  # 提前一周与外出活动材料
    "pt-606ac07242",  # 值班地点时间与填表要求
    "pt-71d6ab8b77",  # 审批通过后再准备
    "pt-b07d349c23",  # 提交校外人员信息
    "pt-cc7598ec3b",  # 经费填写与代签规则
    "pt-f253d7addc",  # 大型活动 100 人与四周
    "pt-fe2f63a2bd",  # 校外人员超过 50 人交名单
}
hb42a3ca_REASON = ""

# 集体户口与退役士兵优待
hb49833f_KEEP = {
    "pt-02dd68369a",  # 退役复学可转专业
    "pt-043da34fe5",  # 学费补偿标准 12000 / 16000
    "pt-0eb4f38744",  # 免修军事技能
    "pt-1bb7810efc",  # 服役期视为工作经历
    "pt-1ec285fac2",  # 退役一年内视同应届
    "pt-394c3c4cfe",  # 义务兵优待金
    "pt-4f1f91d4b3",  # 复学课程成绩与学分认定
    "pt-6537eef6c4",  # 义务兵父母医疗补充保险
    "pt-7bce8410ce",  # 考研加 10 分或免试
    "pt-89708528b2",  # 定向招聘
    "pt-914561779a",  # 5 月 31 日后户口卡不再外借
    "pt-bc0ee215d2",  # 迁入集体户须更换身份证
    "pt-bd55e16177",  # 自主就业一次性补助 10 万元
    "pt-cb2cccd747",  # 满 12 年安排工作
    "pt-cdcd2fb275",  # 开除退学须先迁户口
    "pt-cdf178e213",  # 退役士兵专项硕士计划
    "pt-eb4a76f3de",  # 休学不办理户口迁出
    "pt-eea6742e7d",  # 复学提高奖学金等级
    "pt-f7ff3d32cf",  # 退役后两年内允许复学或入学
}
hb49833f_REASON = "非计划招生与教职工入户、死亡销户，以及已由户籍、征兵与保留学籍条目覆盖的重复条款"

# 军事课与军训
hb4b8c33_KEEP = {
    "pt-068424b609",  # 防卫技能 30 学时
    "pt-0b34b5c4f1",  # 不准染发戴饰物
    "pt-0c4021269e",  # 军事理论内容
    "pt-10d53b1d2a",  # 严禁吸烟饮酒
    "pt-1cac144d79",  # 违纪降一个等次
    "pt-234dcb0757",  # 统一着装
    "pt-25f9cd383a",  # 体测指标与 120 分
    "pt-2a562857f4",  # 请假半天与一日审批
    "pt-2cf825b3bb",  # 游泳首周技能测试
    "pt-3c7872fdd1",  # 军事理论考核方式
    "pt-46248079ed",  # 军事技能内容
    "pt-4db3fe0c1a",  # 战备基础 20 学时
    "pt-575853bf4e",  # 免训缓训手续
    "pt-59f75de4a4",  # 不得私自离开营区
    "pt-5beec38322",  # 原则上不得请假
    "pt-5c2e764605",  # 笔试 60% 在线 40%，技能四等级
    "pt-5c893b20a9",  # 退伍免训获标兵成绩
    "pt-5d603fd64e",  # 违纪给予处分
    "pt-619201c2c5",  # 一项不及格须重考重修
    "pt-6554f6886c",  # 2 学分，免训仍须学理论
    "pt-6a2fa3d6ac",  # 2022 年 9 月施行
}
hb4b8c33_REASON = "军训领导小组职责、安全口号、乘车与行为准则"

KEEP_SOURCES = [
    ("fb1675e0", fb1675e0_KEEP, fb1675e0_REASON),
    ("fb45dc5b", fb45dc5b_KEEP, fb45dc5b_REASON),
    ("ffb0eed1", ffb0eed1_KEEP, ffb0eed1_REASON),
    ("hb0277ac", hb0277ac_KEEP, hb0277ac_REASON),
    ("hb0807a6", hb0807a6_KEEP, hb0807a6_REASON),
    ("hb1a4f11", hb1a4f11_KEEP, hb1a4f11_REASON),
    ("hb1c44b2", hb1c44b2_KEEP, hb1c44b2_REASON),
    ("hb1de9b9", hb1de9b9_KEEP, hb1de9b9_REASON),
    ("hb1f31e1", hb1f31e1_KEEP, hb1f31e1_REASON),
    ("hb2138ae", hb2138ae_KEEP, hb2138ae_REASON),
    ("hb33c2d1", hb33c2d1_KEEP, hb33c2d1_REASON),
    ("hb42a3ca", hb42a3ca_KEEP, hb42a3ca_REASON),
    ("hb49833f", hb49833f_KEEP, hb49833f_REASON),
    ("hb4b8c33", hb4b8c33_KEEP, hb4b8c33_REASON),
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
