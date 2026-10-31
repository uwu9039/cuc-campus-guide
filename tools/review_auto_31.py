"""auto_31 人工复核：军训作息、博士预答辩、学位授予与复核、优秀毕业生、专硕考核、
博士候选人资格考试、研究生课程管理、公共外语、校史馆与赠书书库、在读证明、
学生工作规章制度汇编。

判定原则（与 auto_17…auto_30 一致）：
- 保留学生可执行的规则、期限、费用、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除已由现行服务条目完整覆盖的重复段落
- 删除残句、表格粘连、模板占位与无信息宣传语

整源判断：
- hb720eed：公费医疗享受范围与 90/80/70% 报销比例已被 xyy-gongfei / xyy-gongfei-menzhen 归纳
- hb89efe9：2022 版通识选修核心 5+拓展 6+特色 4 已被 tongshi-ke 现行核心 8+拓展 8 取代
- hb90ba79：传媒博物馆临时展厅办展程序，面向办展单位与教职工，非学生办事

保留来源：
- hb4b8c33：军训探访、伤病、考评、武器弹药与军事课学时（其余已在 auto_30 处理）
- hb679500：博士预答辩的申请条件、专家组成、程序与回避
- hb6886c4：学位答辩、匿名评阅、学术复核与学位授予条件
- hb689df5：优秀毕业生评选条件、比例、程序、申诉与撤销
- hb6cbd10：专硕专业实践能力考核的申请、程序与适用年级
- hb71540d：博士候选人资格考试考查重点、方式、时间与免考
- hb7942db：研究生个人培养计划、课程考核、补考缓考、成绩与重修
- hb7c6607：硕士预答辩程序
- hb7c8a86：学博读书报告、学术会议与科研训练学分
- hb860d51：研究生公共外语课程设置、免修免考条件与成绩记载
- hb8c1526：校史馆开放、团体参观与赠书书库阅览规则
- hb8d9e13：在读证明适用情形、线下材料与不予受理条件
- hb921f79：专博创新成果、三助、研究生奖助、荣誉称号、困难补助、基层就业代偿、
  入伍资助、贷款与勤工助学细则；本条来源在入库时被统一错标为专博创新成果规定，
  本次按学工部《学生工作规章制度汇编（2025）》更正标题并去掉错误页码
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_31.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_31.json"
LOG = ROOT / "_review_items" / "applied_auto_31.txt"

DROP_SOURCES = {
    "hb720eed": "公费医疗享受范围与报销比例已被 xyy-gongfei / xyy-gongfei-menzhen 归纳",
    "hb89efe9": "2022 版通识选修学分结构已被 tongshi-ke 现行要求取代",
    "hb90ba79": "传媒博物馆临时展厅办展程序，面向办展单位与教职工，非学生办事",
}

# 军训
hb4b8c33_KEEP = {
    "pt-70707b36aa",  # 不接待家长探访、不留宿
    "pt-7f628719b6",  # 伤病持随队医务证明并经连干部批准
    "pt-876b335e43",  # 技能考评四等级，课目 60 分养成 40 分
    "pt-948b80b945",  # 伤病离队办理交接
    "pt-b4009311ab",  # 游泳测试通过免考勤并计满分
    "pt-e626181fb6",  # 武器弹药与实弹射击安全
    "pt-ff09240ce7",  # 全日制本专科必修军事课
    "pt-abd4ff6a9e",  # 比照部队一日生活制度
    "pt-eeaa0ef538",  # 射击与战术训练 20 学时
}
hb4b8c33_REASON = "军训领导小组与带队教师职责、内务口号与重复的考核表述"

# 博士预答辩
hb679500_KEEP = {
    "pt-0dec2e7f55",  # 须责任博导与培养单位同意
    "pt-3783c3d194",  # 学博与单考核专博须预答辩
    "pt-64138d7f88",  # 责任博导出席并介绍情况
    "pt-88c7f57493",  # 预答辩程序
    "pt-cea1c0d601",  # 论文提前一周送交专家
    "pt-eb0e3f26a5",  # 博导不得任专家并须回避
}
hb679500_REASON = "制定依据、预答辩目的、材料归档与施行日期"

# 学位答辩、匿名评阅与学术复核
hb6886c4_KEEP = {
    "pt-003bade9d3",  # 学术复核决定为最终决定
    "pt-02b3dbef93",  # 书面告知并保障陈述申辩权
    "pt-03dbbb9c4e",  # 博士答辩未通过可转硕士
    "pt-07852d76bf",  # 反对票与及格段须隐名表决
    "pt-1195e5de47",  # 撤销学位后的处理
    "pt-129fa4fa2d",  # 国际研究生论文语言
    "pt-23ed978110",  # 通过匿名评阅后方可答辩
    "pt-242f9eed43",  # 学位申请条件与独立完成论文
    "pt-2f16077147",  # 学术复核专家小组组成
    "pt-307558a6c1",  # 答辩未通过三个月后重新申请
    "pt-316648cfcc",  # 博士学位授予条件
    "pt-329bcf66de",  # 三分之二同意通过答辩
    "pt-3fc3644e11",  # 一位专家不同意可申请复核
    "pt-44137be419",  # 两次答辩未通过不再具有资格
    "pt-4bcbfcac6f",  # 通过后填报学位审批呈报表
    "pt-520e75ec42",  # 硕士学位授予条件
    "pt-5864d0defb",  # 无记名投票表决
    "pt-59eee40f1e",  # 匿名评阅提交范围
    "pt-5ffe53ba51",  # 不授予或撤销学位的情形
    "pt-68c55a2ba8",  # 学位申请人政治与学术道德要求
    "pt-6e931cc457",  # 复核申请三十日内答复
    "pt-702ff39a4b",  # 校委会审核不合格的处理
    "pt-7409f941cb",  # 学术评价异议成立专家小组
    "pt-75fffe01f0",  # 评阅不合格六个月后重新申请
    "pt-79bfd48e7f",  # 答辩未通过可转毕业答辩
    "pt-7b7c209b1d",  # 评阅均同意方通过
    "pt-81a1ec440c",  # 处分未解除不受理学位申请
    "pt-8fa0bf0b48",  # 涉密论文与过程保密
    "pt-9c9667b47e",  # 复评均同意方通过
    "pt-9e69e7c7cf",  # 答辩评价异议三个工作日内申请复核
    "pt-b5c0e20d37",  # 答辩公告提前三天
    "pt-bfd73cb602",  # 单考核与双考核的答辩构成
    "pt-c329e34d0b",  # 答辩决议不得更改
    "pt-cad04501fa",  # 未通过评阅可申请毕业答辩
    "pt-cf4fca6c40",  # 学位证书颁发与生效
    "pt-e2bcfd7ce0",  # 学术复核程序
    "pt-efc16924e3",  # 匿名评阅申请与导师评阅意见
}
hb6886c4_REASON = "学位评定委员会组成与议事流程、部门职责、制定依据与施行废止条款"

# 优秀毕业生
hb689df5_KEEP = {
    "pt-05cdb4fe53",  # 撤销荣誉称号的情形
    "pt-0fcb1a4ad4",  # 5 月底、11 月底审核公示上报
    "pt-4e87eff960",  # 基本条件
    "pt-5aa9347b32",  # 成绩与证书要求
    "pt-5e4c2078e7",  # 校级以上荣誉与突出成绩
    "pt-5fe69f91c6",  # 校级 10% 与市级比例
    "pt-64bec9f79f",  # 港澳台侨与留学生另行安排
    "pt-8bf7ccab87",  # 异议七个工作日内答复
    "pt-9ad5d6fd32",  # 未受处分无不良信用记录
    "pt-a40b512387",  # 品德与学术诚信
    "pt-b3842b7b95",  # 评选对象
    "pt-f2a2a17fac",  # 素质、公益与志愿服务
    "pt-faebe7ee77",  # 德智体美劳全面发展
    "pt-fd8b61e37a",  # 就业观与基层就业优先
}
hb689df5_REASON = "部门分工与名单核算、通知性表述与施行废止条款"

# 专硕专业实践能力考核
hb6cbd10_KEEP = {
    "pt-06a81d9f18",  # 考核程序
    "pt-851a2ef4ea",  # 本人申请并经导师与单位同意
    "pt-adee05e203",  # 完成二分之一论文与作品
    "pt-d159986af0",  # 2024 级开始执行
    "pt-f81f5945af",  # 考核定义与目的
}
hb6cbd10_REASON = "组织分工、材料归档与施行条款"

# 博士候选人资格考试
hb71540d_KEEP = {
    "pt-2dff27003c",  # 笔试面试按学科类别
    "pt-38315b3295",  # 资格考试考查重点
    "pt-4f4df6fa7b",  # 双通过 60 分计 2 学分
    "pt-5eead8125f",  # 考前完成基本文献阅读
    "pt-6da064e0ad",  # 延缓考试申请
    "pt-9669cdbb63",  # 考试方式
    "pt-a454056088",  # 所有博士生含硕博连读
    "pt-c11d9d35ac",  # 责任博导不得任面试委员
    "pt-d1301517fb",  # 通过后方可进入论文工作
    "pt-eec1857f67",  # 一天半，笔试一天
    "pt-ed68354086",  # 第四、五、六学期考试
}
hb71540d_REASON = "培养单位职责、细则制定与施行条款"

# 研究生课程管理
hb7942db_KEEP = {
    "pt-04314ac252",  # 个人培养计划内容
    "pt-0934c9e268",  # 不及格可补考
    "pt-197023d21a",  # 补考成绩记 60 分并标注
    "pt-223a781e3d",  # 公共外语与政治课免修记 90 分
    "pt-2c0b1d65fb",  # 合格不得重修
    "pt-2dd146b29e",  # 查阅试卷程序
    "pt-58af167318",  # 遵守学术规范
    "pt-5bf393eafb",  # 培养计划变动
    "pt-6e3011af17",  # 考勤不合格与旷考记零分
    "pt-7263db0f72",  # 缓考参加下一次考核
    "pt-755e4d18e1",  # 入学四周内完成培养计划
    "pt-7a7373782a",  # 因病缓考申请
    "pt-a17a9729d8",  # 选修课开课人数
    "pt-b238a32309",  # 按时参加学习考核并请假
    "pt-bc17c3c82c",  # 考核通过取得学分
    "pt-c5de51ed96",  # 提分要求按作弊处理
    "pt-cb9a8a4fcc",  # 成绩由平时与期末组成
    "pt-ccd295d6fa",  # 成绩更正期限
    "pt-d0b3fb360e",  # 入学前已修课程认定
    "pt-e84394e1fa",  # 因事原则上不可缓考
    "pt-f0fa9393ab",  # 旷课超四分之一不得考核
    "pt-fc302b4291",  # 重修课程不再开设可改修
}
hb7942db_REASON = "培养目标、课程体系理念、教师授课与成绩提交要求、系统操作说明与施行条款"

# 硕士预答辩
hb7c6607_KEEP = {
    "pt-e9c232b2eb",  # 硕士预答辩程序
}
hb7c6607_REASON = ""

# 学博培养
hb7c8a86_KEEP = {
    "pt-0e307200c5",  # 读书报告或学术报告不少于 2 次
    "pt-c20816b59f",  # 国际学术会议或国际交流经历
    "pt-c9f6cd82bd",  # 科研成果包括期刊论文等
    "pt-d3038867fe",  # 科研训练学分要求
    "pt-d80b790a3d",  # 参与博导科研项目
    "pt-e1b6ffe7f2",  # 每学期至少 1 次学术汇报
    "pt-ebb112f3f3",  # 国内会议 2 次或暑期学校
}
hb7c8a86_REASON = "制定依据、培养目标、培养方案定义与施行条款"

# 研究生公共外语
hb860d51_KEEP = {
    "pt-2bbec710dc",  # 中外合作办学不能免修
    "pt-302faeb15e",  # 60 分合格
    "pt-5c0e81f783",  # 课程分类与统一选课
    "pt-776697ca76",  # 免修免考申请与 90 分
    "pt-9b199fdb60",  # 免修申请与 90 分
    "pt-b2e41f2b99",  # 学时学分与三个等级
    "pt-b8219808a7",  # 免修 32 学时条件
    "pt-d754693c35",  # 国际研究生免修记 90 分
    "pt-fe5b01f3ff",  # 免修 64 学时条件
}
hb860d51_REASON = "课程设置目的、开课单位职责、施行与解释条款"

# 校史馆与赠书书库
hb8c1526_KEEP = {
    "pt-03af185d60",  # 未经预约团体不接待
    "pt-1bb5aa523c",  # 盈利单位组织团体不接待
    "pt-22fc9d2899",  # 登记信息并听从引导
    "pt-323fba74e1",  # 学校活动可调整参观时间
    "pt-36a0c63a3e",  # 禁止攀爬喧闹
    "pt-543fedd616",  # 禁止危险物品与宠物，禁烟
    "pt-66d3fbf8e2",  # 对团体及个人免费开放
    "pt-6c90adcec7",  # 校外单位团体参观者
    "pt-6e24b7e4a4",  # 预约不符有权拒绝接待
    "pt-71d1cdf68d",  # 团队分批次入馆
    "pt-789ba0856e",  # 阅览室提前一个工作日预约
    "pt-7f0ff764c3",  # 团队有序参观并全程跟团
    "pt-866340ecea",  # 10 人以上提前 3 个工作日预约
    "pt-89d80b475d",  # 禁止私自讲解与拍摄工作人员
    "pt-90b1c36998",  # 馆内禁止用餐
    "pt-94d7d2d2ba",  # 闭馆前 15 分钟归还
    "pt-9c3ac1e4e7",  # 突发事件按指引撤离
    "pt-9e631ffc95",  # 禁止携带背包等进入阅览室
    "pt-a47af6a841",  # 开放对象
    "pt-b3925f4f05",  # 本单位团体参观者
    "pt-c8c11378e7",  # 未成年人须成年看护人陪同
    "pt-ca1aa83dd3",  # 未成年人违规造成事故由看护人担责
    "pt-db4254091a",  # 日常开放时间
    "pt-e41cc4d3cd",  # 逾时 30 分钟自动取消
    "pt-eab0dc221d",  # 团体参观不受日常开放时间限制
    "pt-eddfd44355",  # 校史馆建成时间与位置
    "pt-f57a3a8ce6",  # 闭架阅览不外借
}
hb8c1526_REASON = "校史馆与赠书书库简介、制定说明、附件表格与解释权条款"

# 在读证明
hb8d9e13_KEEP = {
    "pt-01340dc22e",  # 非京籍在学证明适用情形
    "pt-0809a34705",  # 不予受理情形
    "pt-32e8c6b097",  # 线下办理与材料
    "pt-a7230fc9eb",  # 本科生在读证明适用情形
    "pt-e7b8801615",  # 个人短期出国时间安排
}
hb8d9e13_REASON = "部门职责与系统操作说明"

# 学生工作规章制度汇编
hb921f79_ZHUANBO = {
    "pt-1379c06427",  # 创新成果累计 8 分且实践成果分不低于 5 分
    "pt-117c645575",  # 未达创新成果不得答辩
    "pt-65c3eee966",  # 成果署名单位
    "pt-7f349ccfb6",  # 攻读学位期间定义
    "pt-a395223213",  # 创新成果定义
    "pt-6bac97291e",  # 计分办法由培养单位设定
    "pt-9eaf8e693d",  # 成果须在学期间且属中传
}
hb921f79_KEEP = hb921f79_ZHUANBO | {
    # 三助
    "pt-a51d5e83dd",  # 三助定义与工时上限
    "pt-a04f6a6979",  # 三助津贴标准与 1:1 分担
    "pt-8e9eb590f2",  # 三助聘期
    "pt-84ef8b4fc1",  # 三助面向基本学制内研究生
    "pt-3f68b230c1",  # 助教岗位的学历层次
    "pt-55aa67effd",  # 助教须低于本人学历层次
    "pt-855d65580b",  # 每学期初签订岗位协议
    "pt-9f26780592",  # 津贴按月发放，最多 10 个月
    "pt-70288095a0",  # 辞职提前两周书面申请
    "pt-13e4176e54",  # 两周无答复可自行脱岗
    # 研究生奖助
    "pt-3169a49f1b",  # 成绩不及格只参评三等学业奖学金
    "pt-2855419131",  # 学业奖学金年限与直博层次
    "pt-63624a7891",  # 退学不再享受学业奖学金
    "pt-74d9f18cc0",  # 硕士新生按入学成绩评定
    "pt-6c67ba35ee",  # 二三年级考察重点
    "pt-79d1943f38",  # 二三年级评审标准
    "pt-7803529fbd",  # 学业奖学金可同时获国奖
    "pt-3a4c15812f",  # 学业奖学金 12 月 31 日前发放
    "pt-2514ce1dbd",  # 公派出国仍具国奖参评资格
    "pt-2ce76ffac4",  # 国奖可多次获得，成果不重复
    "pt-8857e5baea",  # 国奖基本申请条件
    "pt-2cddc133bf",  # 保留学籍暂停国助
    "pt-3c37b35b0b",  # 违法违纪暂停国助
    # 荣誉称号与综合素质
    "pt-563cb4951c",  # 荣誉称号种类
    "pt-28d2ffb447",  # 每学年评选一次
    "pt-048f334597",  # 三好评选比例 15%
    "pt-3fb87bf14b",  # 三好评选范围
    "pt-2f4d453bea",  # 评选名额与优秀学生干部 5%
    "pt-5f8aaa9f2c",  # 三好与五育之星不可兼得
    "pt-02d5baacb2",  # 三好与优秀学生干部可兼得
    "pt-442b935ace",  # 各维度不得为 C
    "pt-282eb3588f",  # 以综合素质评价为评定依据
    "pt-9274849314",  # A+ 申请卓越、A 申请优秀
    "pt-66785562bd",  # 奋进之星进步 20%
    "pt-181c2ace55",  # 五育之星
    "pt-172ed1d53b",  # 优秀学生干部表彰定位
    "pt-9cf44e07cf",  # 优秀学生干部评选范围
    "pt-734f8a28b3",  # 优秀学生干部公示七天
    "pt-83ef2fc2ab",  # 三好公示七天
    "pt-14f1a342fa",  # 三好弄虚作假取消称号
    "pt-9fbc333dbb",  # 优秀学生干部弄虚作假取消称号
    "pt-16e4f5d942",  # 综合素质评价不形成唯一总分
    "pt-6889b03b5d",  # 毕业班成长值累加排序
    "pt-49e014f7c6",  # 转专业成长值换算
    # 困难补助
    "pt-58c1be5e73",  # 困难补助种类
    "pt-2a1ce828bf",  # 绿色通道补助定义
    "pt-447a8bfa76",  # 绿色通道 300-500 元
    "pt-9e3822be55",  # 求职补助用途
    "pt-116bfdc7fc",  # 绿色通道与求职补助不需申请
    "pt-4f674bacbf",  # 返乡车费补助上限与比例
    "pt-53746764f6",  # 按距离分档补助
    "pt-5993368bde",  # 资助宣传大使车费 600-1000 元
    "pt-4f22e7fce5",  # 困难补助基本条件
    "pt-7ef7ee228f",  # 困难补助定义与范围
    "pt-12aea07287",  # 休学转学退学处分后不再接受申请
    "pt-73d4329b40",  # 停发追缴困难补助的情形
    "pt-7d974343d9",  # 重点关注家庭经济特别困难学生
    "pt-6c0a714d15",  # 临时困难补助具体条件
    # 校助学金与校励志
    "pt-483ef378ac",  # 校助学金 2000 元
    "pt-2bc32311e7",  # 处分收回或停发校助学金
    "pt-7eada78baf",  # 校助学金志愿服务义务
    "pt-35dc141a2a",  # 校励志不得同时获国家励志
    "pt-6f31f23642",  # 校励志各维度不得为 C
    # 基层就业与入伍
    "pt-51e00ca2a1",  # 不属于基层单位的范围
    "pt-95e379a49f",  # 基层单位定义
    "pt-480652937b",  # 提前离开基层单位
    "pt-a84a29f859",  # 提前离岗视为严重违约
    "pt-22d2953bdc",  # 取消代偿资格自行偿还
    "pt-533b7ec436",  # 补偿年限计算
    "pt-60cae05a54",  # 提前退役仍具资助资格
    "pt-44bbd8c59f",  # 退役复学学费减免申请
    "pt-a3d4c6a676",  # 入伍资助申请程序
    "pt-68e2a13a5d",  # 入伍后贷款停止发放
    # 贷款
    "pt-00643569b2",  # 贷款申请材料
    "pt-3afdd1e9ad",  # 信用贷款无需担保
    "pt-3ee0c0f750",  # 贷款停止发放的情形
    "pt-529674440b",  # 恶意拖欠贷款的限制
    "pt-6cd7b59dc7",  # 毕业前还款确认
    "pt-85c82c5608",  # 贷款学生毕业材料
    # 勤工助学
    "pt-386e879e75",  # 勤工助学申请条件
    "pt-999f62618f",  # 弄虚作假取消资格
    "pt-2a9edc02b4",  # 不得组织危险劳动
    "pt-4daaad3063",  # 校外勤工助学三方协议
    "pt-87873cd5d6",  # 校外酬金不低于最低工资
    # 其他
    "pt-a5da9c27f7",  # 不正当使用助学金停发或收回
    "pt-5d15b0aa5a",  # 发放一年内处分追回
    "pt-1d6877e993",  # 国助受助志愿服务义务
}
hb921f79_REASON = "已由现行服务与奖助条目完整归纳的重复段落、部门职责与委员会流程、残句与施行废止条款"

KEEP_SOURCES = [
    ("hb4b8c33", hb4b8c33_KEEP, hb4b8c33_REASON),
    ("hb679500", hb679500_KEEP, hb679500_REASON),
    ("hb6886c4", hb6886c4_KEEP, hb6886c4_REASON),
    ("hb689df5", hb689df5_KEEP, hb689df5_REASON),
    ("hb6cbd10", hb6cbd10_KEEP, hb6cbd10_REASON),
    ("hb71540d", hb71540d_KEEP, hb71540d_REASON),
    ("hb7942db", hb7942db_KEEP, hb7942db_REASON),
    ("hb7c6607", hb7c6607_KEEP, hb7c6607_REASON),
    ("hb7c8a86", hb7c8a86_KEEP, hb7c8a86_REASON),
    ("hb860d51", hb860d51_KEEP, hb860d51_REASON),
    ("hb8c1526", hb8c1526_KEEP, hb8c1526_REASON),
    ("hb8d9e13", hb8d9e13_KEEP, hb8d9e13_REASON),
    ("hb921f79", hb921f79_KEEP, hb921f79_REASON),
]

RETITLE = {
    "hb921f79": "中国传媒大学学生工作规章制度汇编（2025）",
}
NO_RETITLE = hb921f79_ZHUANBO


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

    retitled = 0
    for pid in chunk_ids:
        if pid in drops:
            continue
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        for prefix, title in RETITLE.items():
            if not src.startswith(prefix) or pid in NO_RETITLE:
                continue
            hit = False
            for s in items[pid].get("source") or []:
                if str(s.get("title", "")).startswith("中国传媒大学关于专业学位博士研究生"):
                    s["title"] = title
                    s.pop("page", None)
                    hit = True
            if hit:
                retitled += 1
    print(f"更正来源标题 {retitled} 条")
    if dry:
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

    lines = [f"删除 {len(drops)} 条，存留 {len(chunk_ids) - len(drops)} 条，更正来源标题 {retitled} 条"]
    for prefix, reason in DROP_SOURCES.items():
        lines.append(f"SOURCE {prefix}：{reason}")
    for prefix, keep, reason in KEEP_SOURCES:
        lines.append(f"KEEP {prefix} {len(keep)}：{reason}")
    lines.append(f"RETITLE {retitled} 条 hb921f79 为 {RETITLE['hb921f79']}，专博 7 条保留原题")
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已应用，备份 {BACKUP.name}")


if __name__ == "__main__":
    main()
