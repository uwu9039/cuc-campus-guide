"""auto_32 人工复核：奖助补贷、大型活动、学位论文各环节、班委会、图书馆古籍与团学评优。

判定原则（与 auto_11…auto_31 一致）：
- 保留学生可执行的规则、期限、费用、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除已由现行服务条目完整覆盖的重复段落
- 删除残句、表格粘连、模板占位与无信息宣传语

整源判断：
- hbaeeeba：标题为研究生学籍管理，正文是学籍、预科与课程成绩的残段，无可执行规则
- hbbd8b17：校园治安管理规定仅剩施行日期
- hbd33955：选课管理办法仅剩适用对象与 OCR 残字

标题更正（原文标题与正文不符）：
- hb921f79：汇编来源误挂“专博创新成果规定”，非专博条目改为学生工作规章制度汇编
- hbb91b1b：误挂“课程考核及成绩管理办法”，按正文分为毕业论文办法与创新创业学分办法
- hbf7d1b9：统一挂“一卡通管理办法”，按正文分为古籍阅览室规则、一卡通办法与文献借阅规定
- hbf8ecd7：统一挂“困难认定办法”，评优条目改为团学系统评优表彰办法，困难认定条目保留原标题

正文修正：
- pt-c6ddfed1ee：引用与正文末尾是 OCR 乱码，只保留“逾期未提交学士学位申请的，不再予以受理。”

保留来源：
- hb921f79：三助、国家助学金、入伍代偿、贷款流程、勤工助学保护、荣誉称号条件与专博成果计分
- hb9461bd：大型活动人数门槛、提前申报、变更报告、申请材料、违规后果
- hb974c49：专硕答辩条件、委员会、程序、三分之二通过、未通过重申请
- hb9bc8c2：辅修学位条件、不授予情形、学士学位条件、撤销程序、逾期不受理
- hba1a222：博士选题报告小组、程序、资格考试后、变动重做
- hbaa4c08：学博中期考核时间、完成二分之一、小组与申请条件
- hbaab131：学硕中期考核时间、小组、60 分通过、程序
- hbadf714：专硕毕业作品展示考核委员会、送交、回避与审核
- hbb91b1b：毕业论文装订与存档、创新学分标准与申报、交流成绩转换
- hbc4ef87：大四春季休学与秋季复学
- hbcac8e2：班会频次、解除职务、个别调整
- hbcef538：查重范围、比例、复检、异议与规避后果
- hbd9d7bc：补发学位证书
- hbe0d10f：博士匿名评阅份数、平台、回避、通过标准与未通过处理
- hbe3f13f：学博成果分值、署名、在学期间定义与未达标后果
- hbea9aa6：思政课学时学分、免修条件与流程
- hbf17d9e：学硕科研训练学分要求、读书报告、社会服务与外语课程
- hbf7d1b9：古籍阅览室预约与复制、一卡通挂失与权限、借阅检查
- hbf8ecd7：团学评优奖项、条件、名额、程序、不重复评选与困难认定限制
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_32.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_32.json"
LOG = ROOT / "_review_items" / "applied_auto_32.txt"

DROP_SOURCES = {
    "hbaeeeba": "标题为研究生学籍管理，正文是学籍、预科与课程成绩的残段，无可执行规则",
    "hbbd8b17": "校园治安管理规定仅剩施行日期",
    "hbd33955": "选课管理办法仅剩适用对象与 OCR 残字",
}

# 奖助补贷与荣誉称号（含三助，现有服务条目未覆盖三助）
hb921f79_ZHUANBO = {
    "pt-b9a7b4b6c0",  # 学术成果第一署名单位
    "pt-c0319cec4b",  # 专博其他重大创新成果分委会认定
    "pt-d9f5202923",  # 获奖作品署名含中国传媒大学
    "pt-f8eea9cb13",  # 专业实践成果计分表
    "pt-f8ff240b0f",  # 其他参与人员定义
    "pt-f9ff71d146",  # 重要参与人员定义
    "pt-fafb8a71e7",  # 分委会报研究生院审核
    "pt-cb66032a0a",  # 学术论文须正式刊发
}
hb921f79_KEEP = hb921f79_ZHUANBO | {
    # 三助
    "pt-d034940275",  # 助管定义
    "pt-d0583b1e46",  # 三助申请条件
    "pt-e7176e2716",  # 按需设岗公开招聘择优聘用严格考核
    "pt-e6a3be940a",  # 申请面试公示并签协议
    "pt-efeaa4397f",  # 岗位全校发布
    "pt-d7393cca7d",  # 选聘名单报学生工作部
    "pt-acee4f97f6",  # 行政、学生工作、学生社区助管
    "pt-bc47c34ae0",  # 助教专业相同相近
    "pt-f89c3d1f74",  # 助教设岗人数门槛
    "pt-c969fc6d47",  # 岗位考核
    "pt-f6baeafcac",  # 聘期工作总结
    "pt-feb639cdb9",  # 三助每周 10 小时每月 40 小时
    "pt-ffb25de0cf",  # 助研津贴 1:1
    "pt-e8ebc606a9",  # 助研津贴发放方式
    # 国家助学金
    "pt-a9c94fafac",  # 档案转入后发放
    "pt-ab9f68eeda",  # 伪造档案骗助学金后果
    "pt-ae61d58fbb",  # 超学制与转学停发
    "pt-b5e95250e4",  # 直博生按层次阶段发放
    "pt-b76807e757",  # 延期、提前、退学与硕博连读转硕
    "pt-bce4a1e48b",  # 国助按学年申请可同时国奖国励
    "pt-bde16cabdc",  # 休学停学退学取消资格
    "pt-cf326a7b00",  # 硕博连读阶段身份
    "pt-e7ceb1e4d6",  # 国助基本申请条件
    "pt-f8bed2f88d",  # 国助资助对象
    "pt-f9aeb43d64",  # 转入转出与档案不符
    # 入伍资助
    "pt-d1b6cee1d9",  # 不享受国家资助的情形
    "pt-ac24d78cd5",  # 退兵取消受助资格
    "pt-e448c14268",  # 征兵报名交申请表
    "pt-fdcfd15846",  # 批准入伍盖章返还
    "pt-b679d8d0d5",  # 专升本本硕连读资助年限
    "pt-ceb25e4882",  # 资助期限一个学制期
    "pt-ec8f9052a1",  # 资助年限按基本修业年限
    "pt-f72134db64",  # 实缴低于标准按实缴
    "pt-df380276ee",  # 代偿优先偿还贷款
    "pt-df84376401",  # 学费补偿申请程序
    # 助学贷款
    "pt-aa4dc31a78",  # 贷款申请条件
    "pt-abce813478",  # 提前还贷与展期
    "pt-ad3425d418",  # 贷款发放方式
    "pt-b3ca99a584",  # 贷款审批程序
    "pt-ea99d2d36c",  # 违约后果
    # 勤工助学保护性规则
    "pt-d32a771bd5",  # 擅自离职扣发劳务费
    "pt-dc0fef104e",  # 不得占用教学时间
    "pt-dfaa8d1f53",  # 缺勤辞退
    "pt-e54da3a5e2",  # 酬金支付来源
    "pt-ee2be13f08",  # 不得代岗
    "pt-f1f4dd6b72",  # 协议纠纷协商
    "pt-f5fda66b6c",  # 寒暑假时间可延长
    # 学费减免
    "pt-ce551e668c",  # 不得申请学费减免的情形
    # 困难补助
    "pt-c632e18350",  # 可同时申请其他奖助
    "pt-bb435d7d8e",  # 春节留校补助对象
    "pt-ccd6d1870b",  # 资助宣传大使补助对象
    "pt-e5ab3d015e",  # 寒暑假返乡车费补助
    # 荣誉称号
    "pt-d3cbd71785",  # 荣誉称号申请对象
    "pt-b2687a3327",  # 优秀学生干部条件
    "pt-da68b3f566",  # 三好学生维度要求
    "pt-c3184e8e3c",  # 毕业年级参照评选
    "pt-e337535fc9",  # 奋进之星定义
    "pt-c084f4dec1",  # 校励志弄虚作假处理
    "pt-b2e293cd72",  # 校助按学年可同时国奖
    "pt-c7285bd8df",  # 校助学籍变动停发
    "pt-ef7d4f1cb6",  # 校励志二年级以上
    # 其他奖助规则
    "pt-cb45bc636a",  # 国奖不再获总台星光奖
    "pt-e90279dc28",  # 综合素质评价用于遴选
    "pt-ad824fe0e5",  # 资助标准动态调整
    "pt-ea53441ede",  # 学业奖学金申请条件
    "pt-fbad4ded0e",  # 延期不享受学业奖学金
    "pt-ef2347151d",  # 休学保留学籍奖金复学后发
    "pt-f8894e0ae7",  # 困难硕士优先评定
    "pt-e438c87901",  # 加权系数由基层单位定
    "pt-ed96648dee",  # 新生重点考察入学成绩
    "pt-d69ac34bf7",  # 国奖每学年评审一次
}
hb921f79_REASON = (
    "制定目的、废止条款、经费与预算管理、动态调整以外的部门职责、"
    "已由 yjs-jiangzhu / zxj-guojia / dk-zhuxue / xuefei-jianmian / "
    "xszz-qingong / linshi-kunnan-buzhu 覆盖的定义与金额，以及残句"
)

# 大型活动安全管理
hb9461bd_KEEP = {
    "pt-46cacf92a1",  # 室内 500 人室外 100 人
    "pt-f768acc9c8",  # 提前十五个工作日申请
    "pt-1078ff6428",  # 变更提前两个工作日报告
    "pt-69ef9850f0",  # 安全许可申报材料
    "pt-ea24cc49ea",  # 学生社团由院系或校团委申报
    "pt-07f3bda6e3",  # 外单位主办须风险预评估
    "pt-edf64c2d7c",  # 违规三到六个月不得申办
    "pt-68d8ae2cb3",  # 主办与承办签订安全协议
    "pt-47bea2c4d7",  # 承办者安全职责
    "pt-744d202ace",  # 保卫部两个工作日审查
    "pt-8a845fe248",  # 违规损失自担
    "pt-9300551382",  # 保卫部可取消或中止
    "pt-03015305ea",  # 许可异议可申请复议
    "pt-7ac98ae04b",  # 热点人物活动按大型活动管理
    "pt-e2456e8a47",  # 常规课程不在范围
}
hb9461bd_REASON = "保卫部与场所管理者职责、许可条件清单、制定与施行条款"

# 专硕学位论文答辩
hb974c49_KEEP = {
    "pt-1708f39187",  # 须导师单位与研究生院批准
    "pt-1a50091c70",  # 委员会审查并投票
    "pt-4d72b17fd8",  # 学位论文形式
    "pt-687ef687df",  # 两次未通过取消资格
    "pt-68b72cf9d7",  # 导师出席介绍
    "pt-7b8dd84b31",  # 答辩程序
    "pt-91269ea886",  # 未通过三个月后重新申请
    "pt-9bcdf61fee",  # 三分之二同意建议授予
    "pt-eca62dd3a7",  # 提前一周送交委员
    "pt-fb6ed38fd6",  # 委员会组成
}
hb974c49_REASON = "制定依据、答辩目的、归档要求与施行日期"

# 学士学位授予
hb9bc8c2_KEEP = {
    "pt-06597ed477",  # 辅修学士学位条件
    "pt-372c8941d5",  # 不授予学位的情形
    "pt-3a439c306f",  # 学士学位授予条件
    "pt-990e1c5e47",  # 撤销学位后的处理
    "pt-c6ddfed1ee",  # 逾期申请不再受理
}
hb9bc8c2_REASON = "制定依据"

# 博士选题报告
hba1a222_KEEP = {
    "pt-031206caef",  # 变动题目重新组织选题报告
    "pt-0a1d8736e7",  # 专家小组组成
    "pt-115dd46acf",  # 责任博导不可任组长
    "pt-17be9b9922",  # 审核选题依据与方案
    "pt-2648ddd792",  # 选题报告会程序
    "pt-472bd7428e",  # 资格考试后进行
    "pt-e86c6d4437",  # 填表经责任导师同意
}
hba1a222_REASON = "制定依据、归档要求、施行时间与具体要求的指引条款"

# 学博中期考核
hbaa4c08_KEEP = {
    "pt-23d3df09ca",  # 选题后下一学期且完成二分之一
    "pt-7ef487e1e4",  # 中期考核程序
    "pt-a69ae61cb8",  # 责任博导可成员不可组长
    "pt-e264ccce0c",  # 专家小组五至七名
    "pt-f1a131fb7a",  # 本人申请并经导师单位同意
}
hbaa4c08_REASON = "制定依据、归档要求、2024 级执行时间、秘书记录与定义"

# 学硕中期考核
hbaab131_KEEP = {
    "pt-8606924c5e",  # 选题后下一学期且完成二分之一
    "pt-8bc53fd8fe",  # 导师可成员不可组长
    "pt-98917ecf62",  # 本人申请并经导师单位同意
    "pt-b325cab013",  # 60 分通过
    "pt-cf50df203b",  # 专家小组三至五名
    "pt-d2b09c4605",  # 中期考核程序
}
hbaab131_REASON = "制定依据、归档要求、执行时间、秘书记录与组织分工"

# 专硕毕业作品展示考核
hbadf714_KEEP = {
    "pt-03fb588d3c",  # 导师不得任成员并报备案
    "pt-16c2228c65",  # 毕业作品水准要求
    "pt-198cc4ab0a",  # 导师出席介绍
    "pt-2b549aafab",  # 委员会组成
    "pt-3e96868263",  # 双考核须公开展映
    "pt-7d3fdde40d",  # 须导师与单位同意
    "pt-9701f13344",  # 委员会审查并提修改意见
    "pt-b17dabe930",  # 导师回避
    "pt-e372934d1b",  # 考核前一周送交
}
hbadf714_REASON = ""

# 本科毕业论文与创新创业学分
hbb91b1b_THESIS = {
    "pt-4989d0e9d8",  # 论文装订顺序
    "pt-9f3be009d8",  # 知识产权归学校
    "pt-ad782b6fe3",  # 选题须先有依据
    "pt-af9b72e27f",  # 装订成册存档四年
    "pt-e0db4996a2",  # 五级分制评分
}
hbb91b1b_INNOV = {
    "pt-328315f3c8",  # 同项目按最高级别认定
    "pt-3a0f86242c",  # 创业竞赛参照创新学分
    "pt-485b1ce86f",  # 多项只能申报一项，四月申报
    "pt-59ffaa6b14",  # 学分争议书面申请
    "pt-834e19f5e4",  # 学科竞赛学分 5/4/3/2/1
    "pt-b94a77586a",  # 创新创业学分申报流程
}
hbb91b1b_KEEP = hbb91b1b_THESIS | hbb91b1b_INNOV | {
    "pt-7c8cdb48ed",  # 境内外交流成绩等级制转换
}
hbb91b1b_REASON = "毕业论文的意义、学院职责、指导教师职责、选题泛述与施行解释"

# 本科生学籍
hbc4ef87_KEEP = {
    "pt-fdf9305724",  # 大四春季休学与秋季复学
}
hbc4ef87_REASON = "教务处解释条款"

# 班级学生委员会
hbcac8e2_KEEP = {
    "pt-158d146775",  # 不胜任或缺勤一半解除职务
    "pt-39b0ea4c77",  # 原则上每周一次班会
    "pt-caa8cabf30",  # 个别班委调整须全体选举
}
hbcac8e2_REASON = (
    "班委岗位职责清单与 banwei-roles / banwei-xuanju 重复，"
    "另有制定目的、解释与施行条款"
)

# 学位论文查重
hbcef538_KEEP = {
    "pt-0e097b182f",  # 上传后通知导师确认
    "pt-1c8cb50ea8",  # 同等学力参照执行
    "pt-391f66d9cf",  # 可聘专家鉴定
    "pt-3d0adbcee0",  # 规定时间上传电子版
    "pt-628d73511d",  # 纸质报告导师签字
    "pt-6de7580125",  # 凡申请答辩均需查重
    "pt-841e673d5b",  # 复检合格进入匿名评阅
    "pt-8d0da383a2",  # 异议审议流程
    "pt-926af9e564",  # 规避查重取消资格
    "pt-a00f12f69f",  # 十日内申请复检
    "pt-dad6536892",  # 博士 15% 硕士 20%
    "pt-dd6f955f5e",  # 查重时间由学位办确定
}
hbcef538_REASON = "制定目的、两级管理、专人负责、归档与重复的评阅衔接表述"

# 证书管理
hbd9d7bc_KEEP = {
    "pt-a24b9e4e65",  # 补发学位证书
}
hbd9d7bc_REASON = "施行与解释条款"

# 博士匿名评阅
hbe0d10f_KEEP = {
    "pt-086bcee8bc",  # 学博五位校外专家
    "pt-2c03bfb3ee",  # 专博五位含两位校外
    "pt-5671fe91f4",  # 半数以下同意可申请毕业答辩
    "pt-6863b5bbf4",  # 查重合格进入评阅
    "pt-69cc892c09",  # 学博送教育部平台
    "pt-6c9faae5b1",  # 均同意方为通过
    "pt-838fd04674",  # 最多回避三名
    "pt-854b7b6b18",  # 双向匿名
    "pt-8e53c86ae0",  # 半数或以上同意可毕业答辩
    "pt-f30aed7465",  # 专博送专业平台
}
hbe0d10f_REASON = "制定依据与归档要求"

# 学博科研成果
hbe3f13f_KEEP = {
    "pt-2299ab890f",  # 专著译著教材不折算
    "pt-79959c1f92",  # 刊物级别认定依据
    "pt-8469a27995",  # 第一署名单位
    "pt-c9cfa46150",  # 累计 8 分且 C 类一篇
    "pt-d555a628eb",  # 培养单位可提高标准
    "pt-dfb070482c",  # 在学期间定义
    "pt-e6f0b6b552",  # 未达标不得答辩
    "pt-fee327bf1c",  # 发表与成果定义
}
hbe3f13f_REASON = "制定依据、解释与 2023 级执行时间"

# 思政课
hbea9aa6_KEEP = {
    "pt-206905d30a",  # 免修申请流程与 90 分
    "pt-902497fc74",  # 硕士课程学时学分
    "pt-9f55c0e1d0",  # 博士课程学时学分
    "pt-d3de7365e6",  # 博士免修条件
    "pt-dea6e39105",  # 硕士免修条件
}
hbea9aa6_REASON = "制定依据、教学运行与教师管理、施行解释"

# 学硕培养
hbf17d9e_KEEP = {
    "pt-67616414b7",  # 论文写作训练 5 次或工作坊 1 项
    "pt-779a218902",  # 读书报告或学术报告 2 次
    "pt-8f81c4e906",  # 参加导师科研项目
    "pt-91e6f32e4a",  # 社会服务不少于 1 项
    "pt-9712a20d57",  # 外语课程范围
    "pt-a869bda5a9",  # 科研训练学分要求
    "pt-c5c7c9ac16",  # 实习实践
}
hbf17d9e_REASON = "制定依据与重复的查重表述"

# 图书馆古籍、一卡通与借阅
hbf7d1b9_GUJI = {
    "pt-022061f473",  # 铅笔抄录勿压折
    "pt-108eb001dd",  # 有复制品不提供原件
    "pt-184d7bdf0f",  # 周一三上午开放
    "pt-2e1a57044f",  # 散页破损不提供阅览
    "pt-3237c74e0f",  # 指定区域饮水
    "pt-3581ca501a",  # 禁止背包拍摄器材书刊食品
    "pt-795925db92",  # 校内师生与校外人士阅览凭证
    "pt-9889f61734",  # 复制不超过十分之一
    "pt-ad14ad2718",  # 闭架阅览不外借
    "pt-ac6b58771b",  # 提前一个工作日预约
    "pt-e55a110404",  # 每种古籍一张索书单
    "pt-f261de9ab4",  # 关闭前 15 分钟归还
}
hbf7d1b9_CARD = {
    "pt-3554e938ff",  # 双培生等开通借阅权限
    "pt-8068b3725c",  # 挂失前借还书以系统为准
    "pt-9e3b03c584",  # 遗失立即挂失补办
    "pt-ac66eb90d9",  # 卡号密码作为读者账户
    "pt-d73ab7b887",  # 硕博连读须注销硕士学段
}
hbf7d1b9_KEEP = hbf7d1b9_GUJI | hbf7d1b9_CARD | {
    "pt-8a7cf18eea",  # 阅览时检查污损当场提出
}
hbf7d1b9_REASON = (
    "与 lib-jieyue / lib-duzhe-shouze 重复的借阅、赔偿与行为规则，"
    "以及制定目的和解释条款"
)

# 团学评优与困难认定
hbf8ecd7_KUNNAN = {
    "pt-60ebe0769c",  # 特殊困难七类
    "pt-a0135423ed",  # 困难资格每学年复核
    "pt-b5658dddb8",  # 不得认定困难的六种情形
    "pt-b8301d75d4",  # 访谈小组 10-15 分钟
}
hbf8ecd7_KEEP = hbf8ecd7_KUNNAN | {
    "pt-049b3016f9",  # 优秀团员综测前 40%
    "pt-0c4b0684c7",  # 已获优干不重复
    "pt-0c5d8341e1",  # 优秀团员与优干不重复
    "pt-0d6bc77414",  # 志愿者优先条件
    "pt-111617e1ad",  # 个人奖项参评主体
    "pt-1136bb47ef",  # 优秀团员成绩条件
    "pt-1ba4fa2094",  # 志愿者 150 小时
    "pt-2fb5bb24d8",  # 团校学员优先且已获不重复
    "pt-306a91b1a6",  # 春秋两季评选
    "pt-30de9500b3",  # 志愿者条件
    "pt-3c3ea23705",  # 公开答辩公示
    "pt-5a0ff8cf10",  # 红旗团支部候选单位
    "pt-5b1acb27ef",  # 优秀志愿者评选程序
    "pt-5e612ff26d",  # 个人奖项名额
    "pt-7ce7da28e9",  # 优秀团支部评选
    "pt-84095d3e36",  # 弄虚作假处理
    "pt-88c83b118d",  # 适用对象
    "pt-893eb8a8f1",  # 干部满一年且团校优先
    "pt-899fb316ea",  # 优干推选三分之二
    "pt-9e84091545",  # 红旗团委候选单位
    "pt-9f8ff2ac13",  # 红旗团支部评选
    "pt-a4ab1f4337",  # 院内推选三分之二
    "pt-aa0cb45ad6",  # 优秀团学组织认定
    "pt-b530e9e534",  # 优秀团委评选流程
    "pt-bc7e6e047b",  # 所带组织获奖且满一年
    "pt-bf59062dae",  # 集体奖项参评主体
    "pt-c998224e51",  # 集体奖项名额
    "pt-e3f18d384d",  # 优干综测前 50%
    "pt-e7717fa875",  # 支部无处分
    "pt-ea8f0d1c46",  # 志愿者不重复评选
    "pt-ec70c2f076",  # 优秀团员评选程序
}
hbf8ecd7_REASON = (
    "图书馆行为守则重复条目、团委组织职责与口号式条件、目的与解释条款"
)

KEEP_SOURCES = [
    ("hb921f79", hb921f79_KEEP, hb921f79_REASON),
    ("hb9461bd", hb9461bd_KEEP, hb9461bd_REASON),
    ("hb974c49", hb974c49_KEEP, hb974c49_REASON),
    ("hb9bc8c2", hb9bc8c2_KEEP, hb9bc8c2_REASON),
    ("hba1a222", hba1a222_KEEP, hba1a222_REASON),
    ("hbaa4c08", hbaa4c08_KEEP, hbaa4c08_REASON),
    ("hbaab131", hbaab131_KEEP, hbaab131_REASON),
    ("hbadf714", hbadf714_KEEP, hbadf714_REASON),
    ("hbb91b1b", hbb91b1b_KEEP, hbb91b1b_REASON),
    ("hbc4ef87", hbc4ef87_KEEP, hbc4ef87_REASON),
    ("hbcac8e2", hbcac8e2_KEEP, hbcac8e2_REASON),
    ("hbcef538", hbcef538_KEEP, hbcef538_REASON),
    ("hbd9d7bc", hbd9d7bc_KEEP, hbd9d7bc_REASON),
    ("hbe0d10f", hbe0d10f_KEEP, hbe0d10f_REASON),
    ("hbe3f13f", hbe3f13f_KEEP, hbe3f13f_REASON),
    ("hbea9aa6", hbea9aa6_KEEP, hbea9aa6_REASON),
    ("hbf17d9e", hbf17d9e_KEEP, hbf17d9e_REASON),
    ("hbf7d1b9", hbf7d1b9_KEEP, hbf7d1b9_REASON),
    ("hbf8ecd7", hbf8ecd7_KEEP, hbf8ecd7_REASON),
]

TITLE_HUIBIAN = "中国传媒大学学生工作规章制度汇编（2025）"
TITLE_LUNWEN = "中国传媒大学本科生毕业论文（设计、创作）管理办法（暂行）（中传教字〔2018〕156号）"
TITLE_CHUANGXIN = "中国传媒大学本科生创新创业学分认定管理办法（试行）（中传教字〔2018〕30号）"
TITLE_GUJI = "中国传媒大学图书馆古籍阅览室（何其芳藏书阅览室）阅览规则"
TITLE_YIKATONG = "中国传媒大学图书馆校园“一卡通”管理办法"
TITLE_JIEYUE = "中国传媒大学图书馆文献借阅规定（修订）"
TITLE_PINGYOU = "中国传媒大学团学系统评优表彰办法（修订）（团字〔2023〕2号）"

RETITLE: dict[str, str] = {}
for _pid in hb921f79_KEEP - hb921f79_ZHUANBO:
    RETITLE[_pid] = TITLE_HUIBIAN
for _pid in hbb91b1b_THESIS:
    RETITLE[_pid] = TITLE_LUNWEN
for _pid in hbb91b1b_INNOV:
    RETITLE[_pid] = TITLE_CHUANGXIN
for _pid in hbf7d1b9_GUJI:
    RETITLE[_pid] = TITLE_GUJI
for _pid in hbf7d1b9_CARD:
    RETITLE[_pid] = TITLE_YIKATONG
RETITLE["pt-8a7cf18eea"] = TITLE_JIEYUE
for _pid in hbf8ecd7_KEEP - hbf8ecd7_KUNNAN:
    RETITLE[_pid] = TITLE_PINGYOU

ANSWER_FIX = {
    "pt-c6ddfed1ee": "逾期未提交学士学位申请的，不再予以受理。",
}


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

    overlap = chunk_set & set(RETITLE)
    if overlap - set().union(*(k for _, k, _ in KEEP_SOURCES)):
        raise SystemExit(f"标题更正清单含未保留条目：{sorted(overlap - set().union(*(k for _, k, _ in KEEP_SOURCES)))}")

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
        if pid in drops or pid not in RETITLE:
            continue
        title = RETITLE[pid]
        hit = False
        for s in items[pid].get("source") or []:
            if s.get("title") != title:
                s["title"] = title
                s.pop("page", None)
                hit = True
        if hit:
            retitled += 1
    print(f"更正来源标题 {retitled} 条")

    fixed = 0
    for pid, text in ANSWER_FIX.items():
        if pid not in chunk_set or pid in drops:
            raise SystemExit(f"正文修正条目不在存留范围：{pid}")
        it = items[pid]
        quote_obj = (it.get("evidence") or {}).get("answer") or {}
        if not str(it.get("answer", "")).startswith(text) or not str(quote_obj.get("quote", "")).startswith(text):
            raise SystemExit(f"正文修正与原文不符：{pid}")
        it["answer"] = text
        quote_obj["quote"] = text
        fixed += 1
    print(f"正文修正 {fixed} 条")

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

    lines = [f"删除 {len(drops)} 条，存留 {len(chunk_ids) - len(drops)} 条，更正来源标题 {retitled} 条，正文修正 {fixed} 条"]
    for prefix, reason in DROP_SOURCES.items():
        lines.append(f"SOURCE {prefix}：{reason}")
    for prefix, keep, reason in KEEP_SOURCES:
        lines.append(f"KEEP {prefix} {len(keep)}：{reason}")
    lines.append(f"RETITLE {retitled} 条")
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已应用，备份 {BACKUP.name}")


if __name__ == "__main__":
    main()
