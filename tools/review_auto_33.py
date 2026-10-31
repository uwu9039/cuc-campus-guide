"""auto_33 人工复核：专博培养与考核、优秀班集体、转专业接收计划、宿舍协议、体测与体育补充规定。

判定原则（与 auto_11…auto_32 一致）：
- 保留学生可执行的规则、条件、材料、考核内容、时间节点与后果
- 删除校内部门职责、委员会组织、制定目的、施行与解释条款、宣传语与表头残句
- 删除已由现行服务条目完整覆盖的重复段落
- 转专业各学院 2025 年秋季学期接收计划为现行版本，保留具体条件、材料与考核内容

整源剔除：
- hbf8ecd7：两条分别为图书馆阅览室插座残条与志愿服务口号，无可靠标题
- its-list：门户通知标题与日期拼接，非制度内容
- its-xwVP：VPN 安装与登录已由 it-vpn 完整覆盖
- loc-中传校园：支付平台使用说明仅剩第一步
- loc-迎新服务：迎新系统操作手册步骤，已由迎新流程条目与手册附件覆盖
- loc-音乐与录：全部为“参照附件计分标准”的转引，无具体分值

标题更正（原文标题与正文不符或带附件前缀）：
- hbf9b942：正文为〔2025〕6 号，标题误挂〔2024〕120 号
- hbfe67dc：正文为研究生院〔2024〕73 号，标题误挂中传研字〔2024〕120 号
- hbffbdcb：补文号（中传学教字〔2008〕121 号）
- loc-本科生院：方括号文号改为〔2026〕50 号
- loc-附件1/2/6：去掉“附件N：”前缀
- tizhi-20：去掉“PDF”后缀并补文号
- loc-中国传媒：住宿协议书与安全责任书标题本已正确，不做改动

正文修正：
- pt-a47fbb97b0：补回“以下必修课不参与预置，需自行选课等待抽签”的前提，并并入第二条“学院开设的分组课程”
- pt-623cbbc629：去掉前面的图目录，只留梆子井宿舍设施尺寸
- pt-eb846a06d1：去掉前面的图目录，只留中蓝一期宿舍设施尺寸

保留来源：
- hbf9b942：培养环节、文献、课程、资格考试、实践学分、论文工作各环节与毕业结业条件
- hbfe67dc：专业实践能力考核程序、专家小组、申请与 60 分标准
- hbffbdcb：评选范围、两级评审与答辩、1000 元经费、卫生体测奖学金硬指标
- loc-1…16：各学院接收条件、申请材料、考核内容、时间地点与年级限制
- loc-xuex：学校性质与建校年份
- loc-中传宿舍：梆子井与中蓝床铺尺寸、自习室与共享空间
- loc-中国传媒：住宿协议中的调宿、退宿、充电宝、反馈渠道与违规后果
- loc-本科生院：预选抽签、志愿次序、先选先得、必修课程与错选后果
- loc-附件1/2：特殊群体类型与 B/C 类困难情形
- loc-附件6：成果认定中的署名、排序、重复计分与学术不端规则
- tiyu-202：游泳技能测试条件、时间地点、免考勤与成绩计入
- tizhi-20：重测成绩、附加分、指标权重与满分 120
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_33.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_33.json"
LOG = ROOT / "_review_items" / "applied_auto_33.txt"

DROP_SOURCES = {
    "hbf8ecd7": "插座残条与志愿服务口号，无可靠标题",
    "its-list": "门户通知标题与日期拼接，非制度内容",
    "its-xwVP": "VPN 使用已由 it-vpn 完整覆盖",
    "loc-中传校园": "支付平台说明仅剩第一步",
    "loc-迎新服务": "迎新系统操作步骤，已由迎新流程与手册覆盖",
    "loc-音乐与录": "全部为参照附件的转引，无具体分值",
}

# 专博培养规定（中传研字〔2025〕6 号）
hbf9b942_KEEP = {
    "pt-de4a5beaeb",  # 入学四周内制定课程学习计划
    "pt-0e1c6952e7",  # 入学四周内制定专业实践计划
    "pt-f10f7d98bb",  # 个人培养计划内容
    "pt-1de34b9590",  # 跨层次补修核心课程
    "pt-20ae06f9bb",  # 原则上实践考核前完成课程
    "pt-3799020c93",  # 四个培养环节
    "pt-61156c48a0",  # 基本学制内完成可申请延长
    "pt-7986314b59",  # 普博、硕博连读、直博三类
    "pt-ad8412f156",  # 文献不少于 120 种、著作 30 种
    "pt-edcee54e4c",  # 资格考试前完成基本文献阅读
    "pt-9a9553e1bd",  # 第四学期参加资格考试
    "pt-f77a3712f5",  # 资格考试三次安排
    "pt-5c17996142",  # 笔试加面试，一天半
    "pt-c4354aecbc",  # 笔试面试均通过方为通过
    "pt-bb49d8b187",  # 延迟考试提前两周申请
    "pt-96d83e6547",  # 资格考试计 2 学分
    "pt-101bdbe074",  # 通过资格考试后进入论文环节
    "pt-997f4aace4",  # 实践考核须通过选题并完成二分之一
    "pt-7808b81b85",  # 考核须本人申请并经导师同意
    "pt-bf4da750de",  # 实践学分不少于 9，前两类不少于 4
    "pt-1cfbb3a90f",  # 专业实践学分计算办法
    "pt-5e1c1b14b4",  # 科研成果每项 1 学分
    "pt-68e6958768",  # 教学实践每项 1 学分
    "pt-f94d714165",  # 科研项目每门 1 学分
    "pt-591ea347d3",  # 社会服务每项 1 学分
    "pt-92cc37faac",  # 论文工作六个环节
    "pt-cda5abbbdb",  # 查重合格方可匿名评阅
    "pt-6816bf6c24",  # 五位校外专家匿名评阅
    "pt-64f02d3597",  # 评阅与考核间隔一学期
    "pt-2b552d8049",  # 申请终止与评阅不早于第八学期
    "pt-3190993aaf",  # 预答辩提前 30 天及小组组成
    "pt-5804784e3c",  # 答辩委员会组成
    "pt-3a555ea24e",  # 论文提前一周送交毕业答辩
    "pt-9e0f6b75d6",  # 展示与答辩百分制加权
    "pt-42b0386095",  # 双考核均通过可申请学位
    "pt-bb966bf8c8",  # 单考核可不进行展示考核
    "pt-e079dbcb28",  # 单考核须论文预答辩
    "pt-bfed68a3b5",  # 双考核展示公开进行
    "pt-ca3751ae28",  # 展示未通过可申请毕业答辩
    "pt-beb80923d6",  # 单考核评阅合格方可预答辩
    "pt-f239238e1e",  # 未达博士水平可建议授予硕士
    "pt-fe78aefe02",  # 毕业审核条件
    "pt-153ffa6eec",  # 结业审核条件
    "pt-83f07cf61f",  # 重新申请学位并收回结业证
    "pt-df48590d8a",  # 单考核毕业、学位与结业去向
    "pt-644aaf0f19",  # 自 2024 级专博生开始执行
}
hbf9b942_REASON = "培养方案与课程设置职责、培养目标、目的与解释条款、与其他环节重复的答辩条款"

# 专博专业实践能力考核工作办法（研究生院〔2024〕73 号）
hbfe67dc_KEEP = {
    "pt-49d2f24f40",  # 考核程序九步
    "pt-60ffe1e8f8",  # 专家小组五至七名
    "pt-946b0ad61c",  # 本人申请并填写申请表
    "pt-a8f8962def",  # 百分制 60 分通过
    "pt-fda77b5a27",  # 自 2024 级专博生执行
}
hbfe67dc_REASON = "考核目的与依据、组织与归档、时间与资格等与培养规定重复的条款"

# 优秀班集体评选办法（中传学教字〔2008〕121 号）
hbffbdcb_KEEP = {
    "pt-3b914f060d",  # 每学年一次，本专科研究生二学位班
    "pt-31e210f68e",  # 班级申请并填写申报表
    "pt-384873b355",  # 学校学院两级评审加答辩
    "pt-9094121de8",  # 组织答辩会
    "pt-3726bb762b",  # 答辩基础上择优审定
    "pt-15f1255d5a",  # 每班 1000 元建设经费
    "pt-9d688365ae",  # 寝室卫生合格率 90%
    "pt-9e0ceb48a9",  # 卫生值日制度每月至少两次
    "pt-e30d98754f",  # 体测合格率 90%
    "pt-e2ddb2d1a2",  # 奖学金获奖人数 30%
    "pt-6cdb0fee2f",  # 本学年无违纪处分
    "pt-83f8a6c052",  # 班委会例会每月一次
    "pt-d1166d66a8",  # 党课团课每月至少两次
    "pt-4e1dfd193e",  # 干部培训不迟到不缺勤
    "pt-b3093a777e",  # 班干部发挥桥梁作用
}
hbffbdcb_REASON = "政治口号式条件、班风学风泛述、评委会组成、施行与解释条款"

# 学校简介
loc_xuex_KEEP = {
    "pt-2189d630af",  # 教育部直属双一流
    "pt-d23b3ce15c",  # 1954 年创建，传媒人才摇篮
}
loc_xuex_REASON = "宣传性表述与愿景口号"

# 宿舍平面图
loc_sushe_KEEP = {
    "pt-46b49263f2",  # 上下铺间距 1 米，上铺到房顶 1.5 米
    "pt-623cbbc629",  # 梆子井普通床与加长床尺寸
    "pt-eb846a06d1",  # 中蓝一期床铺尺寸
    "pt-a154373a77",  # 二层两个自习室可容纳 100 人
    "pt-d04cb6ff40",  # 中蓝一期共享空间与静音仓
    "pt-e926215b8e",  # 蓝屿时光屋、放映厅、瑜伽室
}
loc_sushe_REASON = "与 sushe-jiaju 重复的家具尺寸与差异说明"

# 住宿协议（标题原挂校历）
loc_zgcm_KEEP = {
    "pt-0997274d5c",  # 学校因修缮调整宿舍须服从
    "pt-35b2cee8a8",  # 缴住宿费并签协议后入住
    "pt-7b2c5f3cc0",  # 锁门窗、3C 充电宝与异常处置
    "pt-9a4ca82449",  # 严重违规可终止协议责令退宿
    "pt-caa8b4192c",  # 反馈渠道：中传有我、码上提、65783000
    "pt-f69431efa1",  # 入住调宿退宿手续与违纪处理
    "pt-1341aa0141",  # 不擅自改装，损坏自担
    "pt-14dbe6944c",  # 身体不适就医与传染病报备
    "pt-5783fc7b0a",  # 不在宿舍做实验或经营
    "pt-b59cf8f623",  # 违反两次及以上放弃住宿资格
    "pt-c4bab5f9a2",  # 不留宿外来人员，不晚归不夜不归宿
}
loc_zgcm_REASON = "校历说明已由 xiaoli-2026-2027 覆盖，协议中的甲方职责、泛化义务与已覆盖的消防电器条款"

# 2026 级新生选课通知
loc_benke_KEEP = {
    "pt-171bda79c9",  # 所有课程须规定时间网上选
    "pt-1bd5c2a790",  # 不正当选课严肃处理
    "pt-23847cc603",  # 预选抽签
    "pt-31ec36c527",  # 统一身份认证账号密码
    "pt-32a9b504da",  # 退课名额不定时放出
    "pt-4bcecf22d7",  # 选择对应选课批次
    "pt-6f9ae67d41",  # 错选漏选影响毕业资审
    "pt-705e3ae348",  # 第一志愿优先级最高
    "pt-940bc425d2",  # 预选后统一抽签查看结果
    "pt-a47fbb97b0",  # 新生必修课程名单
    "pt-c71cc0d3ea",  # 未设志愿次序不分先后
    "pt-dd73e22cb5",  # 全面选课先选先得
}
loc_benke_REASON = "学院与任课教师工作职责、咨询电话转引、课程容量调整等管理事项"

# 困难认定申请表
loc_fj1_KEEP = {
    "pt-2a9553e0f4",  # 特殊群体类型全表
}
loc_fj1_REASON = "表单字段、签字栏与照抄式填空"

# 困难认定审批表
loc_fj2_KEEP = {
    "pt-5089b8da4e",  # B2 单亲家庭收入线
    "pt-69ec11ab71",  # B4 孤儿有固定收入亲友，B1 父母丧失劳动能力
    "pt-6c0cab3a44",  # C5 父母失业欠债，C1 长期患病
    "pt-7c4e44d212",  # C2 其他家人患重病
    "pt-f6975b5f02",  # B3 家庭遭受严重自然灾害
    "pt-081f119733",  # C3 家庭人口五人以上或在读子女
    "pt-1b9d88d48b",  # C4 父母均 60 岁以上
}
loc_fj2_REASON = "表头、A 类重复项与签字栏"

# 音录学院综合素质评价实施细则
loc_fj6_KEEP = {
    "pt-02b29a301c",  # 大创项目以结项证明为准
    "pt-0dc44046b3",  # 未结项未获奖不认定
    "pt-1aff6d14fd",  # 排序以公开出版与证书为准
    "pt-31ef8a78a5",  # 非主创不纳入
    "pt-34188cc8ff",  # 调整计分比例须全体签字审核
    "pt-3fb080e718",  # 第 6 人及以后不计分
    "pt-4b04ab2d38",  # 直系亲属合作成果不认定
    "pt-4d2f4e0c3b",  # 学术不端成果不认定
    "pt-50e3c25131",  # 单元奖与提名奖折算
    "pt-7c0bd17dc9",  # 同一成果只计最高分
    "pt-852634a010",  # 团队赋分总和不超过参考总分
    "pt-90c5e821a5",  # 挑战杯与互联网加对应 B 级
    "pt-91b217beb2",  # 作品影响力由指导教师证明
    "pt-cb168922f8",  # 团队分值按排序分配
    "pt-ddbd2cd279",  # 无证书时指导教师提交证明
    "pt-f669962edd",  # 每项成果只能一种计分比例
    "pt-f769aee8b4",  # 专业创作不与竞赛美育重复
}
loc_fj6_REASON = "认定原则、学院与专家组职责、赛事级别定义与限额纳入等管理条款"

# 体育课程补充规定（游泳）
tiyu_KEEP = {
    "pt-9d9a321cca",  # 首周开放游泳技能测试
    "pt-3e619195c5",  # 50 米蛙泳与浮板 25 米腿
    "pt-5ba09b57c9",  # 南操场集合统一测试
    "pt-1769276658",  # 通过后免考勤考勤满分
    "pt-d6e769f3fa",  # 测试成绩计入期末专项
    "pt-9dd05a55d8",  # 未通过统一编班常规教学
    "pt-1360a314b9",  # 第二周周三下午补测
    "pt-039bfed81a",  # 加入课程群并随堂体测
    "pt-f3e881280b",  # 完成阳光长跑
}
tiyu_REASON = "解释条款与自担风险表述"

# 体质健康标准实施办法
tizhi_KEEP = {
    "pt-05b3e3dcef",  # 违纪作弊按考试违纪处理
    "pt-439f720150",  # 超 100 分单项加分
    "pt-636a53fdc2",  # 指标权重与满分 120
}
tizhi_REASON = "与 tizhi-shijian、tizhi-pingyou-biye、tizhi-miance 重复的次数、时间、毕业线与免测条款"

# 转专业接收计划（2025 年秋季学期）
loc_plan_KEEP: dict[str, set[str]] = {
    "loc-1-中国": {
        "pt-0eb026fd08",  # 模拟主持不超 3 分钟
        "pt-3ee149d6dc",  # 考试内容自备且不允许化妆
        "pt-5011449149",  # 播读新闻消息不超 2 分钟
        "pt-6862c4a48e",  # 2026-03-04 下午面试
        "pt-69b352f8a7",  # 文学作品朗诵不超 1 分钟
        "pt-d951fa6fb9",  # 口齿嗓音与发音器官条件
        "pt-ed1f01f1a0",  # 携带身份证一卡通准考证
        "pt-fc600bfda4",  # 专业面试含自我介绍 1 分钟
    },
    "loc-2-中国": {
        "pt-0061847572",  # 广告学与品牌实验班笔试面试内容
        "pt-128e311a60",  # 品牌广告赛事实习证明
        "pt-1d17945315",  # 公共关系实习兼职材料
        "pt-3f7d28e757",  # 现场命题 60 分钟自备电脑
        "pt-68ca7e37e6",  # 计算广告项目经验材料
        "pt-6acd510770",  # 教务系统附件提交
        "pt-9024355fd1",  # 个人陈述内容
        "pt-b175c9cbff",  # 设计学人工智能能力证明
        "pt-b57c6d6c0a",  # 拟转入课程无不及格
        "pt-da056bfcae",  # 专业笔试作品创作
        "pt-df33fa92f2",  # 新媒体运营经验材料
        "pt-e30fc4ecd6",  # 面试携带作品集约 10 分钟
    },
    "loc-3-中国": {
        "pt-2ca0f2ae3d",  # 42 号楼 502 扫码进群
        "pt-e3d813cddc",  # 报名时附件提交
    },
    "loc-4-中国": {
        "pt-0999555eef",  # 国际新闻两件实践作品
        "pt-0efad79654",  # 后期剪辑制作能力
        "pt-12f3889170",  # 双语传播作品或英文自我介绍
        "pt-26412878e7",  # 广播电视学专业能力证明
        "pt-329a3a29fe",  # 文案写作与图片设计能力
        "pt-47fd9f4ff6",  # 英语水平证明可选
        "pt-4abe72d066",  # 短视频作品与分工证明
        "pt-668f9c72a1",  # 摄影摄像与后期能力
        "pt-6f51cc95fd",  # 外语能力与国际新闻素养
        "pt-7774231669",  # 获奖或国家级项目证明
        "pt-80ef9532bf",  # 两种以上形式作品集
        "pt-8f703b53eb",  # 个人代表作
        "pt-ab8319c6a8",  # 持续关注国际政治的习惯
        "pt-b3bda4286c",  # 摄影剪辑作品与分工证明
    },
    "loc-5-中国": {
        "pt-01bf188a54",  # 二三四年级降级转入
        "pt-1968d1198c",  # 美术设计与动画片段及录屏
        "pt-1aa9e23b07",  # 学分认定仅数学与面向对象课程
        "pt-1f8d934a90",  # 游戏创作工具与经验
        "pt-221cb6d3f2",  # 程序设计基础
        "pt-2794568e1a",  # 网媒方向交互作品与 PRD
        "pt-2882bbe0be",  # VR 视频须附普通版本
        "pt-2a8518c940",  # 现场游戏角色与环境制作
        "pt-35cc8f43b5",  # 展示命题作品与过程资料
        "pt-35d60147d0",  # 笔试范围
        "pt-38e4cb0cea",  # 网媒方向个人作品形式
        "pt-3d6a208979",  # 2 月 25 日公布命题
        "pt-3e0d80cc36",  # 数媒方向主创视频
        "pt-519df6635a",  # 动画艺术方向要求
        "pt-593d44f2d6",  # 3 月 4 日下午考试
        "pt-5a5f7b3dbc",  # 动画命题动态分镜
        "pt-6f88ced00c",  # 数媒命题视频不超 8 分钟
        "pt-7252087b2e",  # 面试携带平板或电脑
        "pt-75c43f4b3f",  # 非命题材料先过初审
        "pt-782fec9884",  # 笔试命题创作独立完成
        "pt-7bc859d1d1",  # 原创与 AIGC 注明
        "pt-7d36d27050",  # 两个方向命题发布时间
        "pt-7f18686594",  # 3 月 6 日下午考试
        "pt-7f92eeea0e",  # 艺术笔试内容
        "pt-8589f6b01e",  # 数媒方向要求
        "pt-8a1be341e2",  # 笔试 2.5 小时
        "pt-8debf125c8",  # 笔试择优进入面试
        "pt-9383d43eef",  # 必修课程无不及格
        "pt-9f7ac4a79d",  # 笔试为所有转专业同学必考
        "pt-aae0f9e73b",  # 视频格式与时长限制
        "pt-b327dad7e3",  # MP4、工程文件、截图与故事大纲
        "pt-ba46ddb64a",  # 游戏或电竞赛事策划能力
        "pt-be809dff85",  # 其他本专业课程不做认定
        "pt-be926d867f",  # 306B 扫码进复试群
        "pt-c70b3a7be9",  # 影视与三维工具能力
        "pt-c766b272db",  # 网媒方向基础要求
        "pt-df654e1905",  # 个人作品集必选
        "pt-e6d0b05ae4",  # 三维动画方向要求
        "pt-f01441e172",  # 作品文字材料内容
        "pt-f210922d9b",  # 游戏软件或互动作品展示
        "pt-f59857d243",  # 特效命题要求
        "pt-f8a45ae61e",  # 笔试考高数大一内容
    },
    "loc-6-中国": {
        "pt-b51cb2f4b4",  # 特殊才能或奖项可适当放宽
    },
    "loc-7-中国": {
        "pt-44709f3ba4",  # 限自费国际生
        "pt-52eb5fbc82",  # 汉语国际教育方向
        "pt-8f7f708ed2",  # 汉语言文学方向
        "pt-fb86bb3f89",  # 限非国际生
    },
    "loc-8-中国": {
        "pt-3af5d31795",  # 面试内容
        "pt-45338c756b",  # 数学与编程基础
        "pt-b838c929e9",  # 数学编程人工智能课程优异优先
    },
    "loc-9-中国": {
        "pt-0196ed912c",  # 英语优秀加基础西班牙语
        "pt-03baf6d9f9",  # 英语优秀加较高葡萄牙语
        "pt-061208308b",  # 葡语 Celpe-Bras 或 Caple B2 优先
        "pt-17e95c2a4c",  # 国家级英语比赛获奖优先
        "pt-1b2455dbb7",  # 德语 B2 等证书优先
        "pt-47a3ef013d",  # 德语 B1 等证书优先
        "pt-5247ce287d",  # 英语优秀加较高日语
        "pt-54f006acad",  # 德语 A1 优先
        "pt-555ffe3f2c",  # 口齿与语言感知能力
        "pt-586cd69c19",  # 日语 N2 优先
        "pt-5e9860d715",  # 中英文功底与表达能力
        "pt-5ee983cdc0",  # 认可 3+1 项目
        "pt-5f28c65755",  # 英语优秀加基础日语
        "pt-6daff9f967",  # 英语优秀加中等德语
        "pt-77c873a97c",  # 英语优秀加中等葡萄牙语
        "pt-7f36c6d353",  # 日语 N1 优先
        "pt-8976715b89",  # 英语比赛与媒体实践证明
        "pt-8ed4d10adf",  # 英语优秀加基础韩语
        "pt-a351e14982",  # 英语优秀加中等西班牙语
        "pt-c6d3f31829",  # 英语优秀加较高西班牙语
        "pt-cf41e4114d",  # 形象气质与沟通应变
        "pt-d0bd9b3d88",  # 葡语 Celpe-Bras 或 Caple A1 优先
        "pt-dd05601769",  # 英语优秀加较高德语
        "pt-de3317c22c",  # 英语优秀加基础葡萄牙语
        "pt-e0e092eac9",  # 英语优秀加基础德语
        "pt-e100e12d8b",  # 韩语四级以上优先
        "pt-f90a2cfe4b",  # 葡语 Celpe-Bras 或 Caple B1 优先
    },
    "loc-10-中": {
        "pt-3afcaf599f",  # 才能或奖项证明材料
    },
    "loc-11-中": {
        "pt-0269494485",  # 压缩包命名规则
        "pt-04ce144dca",  # 作品须本人原创或主要参与
        "pt-0b1e180a34",  # 阅读量与故事创作兴趣
        "pt-17bde17e3b",  # 舞台表现力与身体条件
        "pt-1b1bd73e12",  # 发表展出上线链接
        "pt-1b97a779b3",  # 压缩包与在线备份
        "pt-1c7d5002db",  # 表演专业面试内容
        "pt-28471c2aa0",  # 作品证明 PDF 内容
        "pt-2fa76a4fe6",  # 创作阐述单独 PDF 不超 100MB
        "pt-307cd35a86",  # 作品须主流平台播映或影展入选
        "pt-34c87a772e",  # AI 制作与影像创作材料
        "pt-357acc825f",  # 创作阐述内容建议
        "pt-39695ed313",  # 转入后从一年级开始
        "pt-3adf9ab161",  # 面试朗诵舞蹈内容
        "pt-3c5b9a0484",  # 网络小说等个人创作
        "pt-3cf9fe02e6",  # 自我介绍视频不超 3 分钟
        "pt-534847bf8c",  # 光环境设计内容建议
        "pt-567556a8b7",  # 主修选修影视课程成绩良好
        "pt-69ca4d3b67",  # 表演专业身体与语音条件
        "pt-73d3e6862d",  # 必修课程无不及格
        "pt-792de2854b",  # 音乐剧声乐舞蹈表演基础
        "pt-7a9a1d5e01",  # 光环境艺术审美与表达能力
        "pt-7ae8a4ef83",  # 影评剧评文案作品
        "pt-7d94471bca",  # 申请陈述不少于 800 字
        "pt-7e6a17ea9f",  # 作品不超过 5 件
        "pt-7f4c62c151",  # 合作作品须说明贡献
        "pt-8a65ba6118",  # 面试七个环节
        "pt-8a850e2cb8",  # 原创与诚信声明
        "pt-a4e0b2fbd0",  # 竞赛获奖证书
        "pt-a97f7b14da",  # 导演摄影剪辑特效短片
        "pt-ad55175a23",  # 光环境相关作品类型
        "pt-afb2e83c42",  # 专业能力证明选交
        "pt-bd769a8616",  # 评优评奖证书
        "pt-c62695bbfd",  # 演出视频与获奖证书
        "pt-d17ad01e4e",  # 限提交 3 部作品
        "pt-d8756e047a",  # 活动与栏目策划案
        "pt-e0b98afaa3",  # 表演创作视频不超 5 分钟
        "pt-e53b556f87",  # 数理课程基础
        "pt-f057246af6",  # 写作或策划作品不少于 1 份
        "pt-f3c3a73d76",  # AI 制作经历优先
        "pt-f521403274",  # 展演项目志愿服务证明
        "pt-fa3c74e38b",  # 创作阐述附 3 张工作照
        "pt-fb4149d711",  # 身心健康无平足
    },
    "loc-12-中": {
        "pt-aa4044f438",  # 代表作或比赛奖项材料
        "pt-dc3bf34762",  # 特殊才能或奖项优先
    },
    "loc-13-中": {
        "pt-94f5206877",  # 42 号楼 106 室
        "pt-c67b0b319b",  # 写作与口头表达能力
    },
    "loc-14-中": {
        "pt-796bcff06a",  # 报名时附件提交
        "pt-8750912993",  # 笔试高数与大学物理及面试
        "pt-b1468cdcd1",  # 数理基础
        "pt-e4e309cb4f",  # 陈述专业认识与理由
    },
    "loc-15-中": {
        "pt-06f47e08a7",  # 音乐基础与音视频制作
        "pt-07236d5c9d",  # 视频不超 10 分钟 500MB
        "pt-0c5a7f14f2",  # 音乐才艺特长
        "pt-16b83dd19d",  # 自选演唱一首
        "pt-38da707438",  # 音乐传播方向认识
        "pt-4aff5b7526",  # 视唱练耳考核
        "pt-ca08aec7d8",  # 演唱能力达到专业水平
        "pt-db1945eac8",  # 原创作品视频提交
        "pt-e94404c297",  # 数理基础
    },
    "loc-16-中": {
        "pt-2bdf1a8ce5",  # 行政管理专业知识与实践
        "pt-3b63f46544",  # 政治学专业知识与思辨
    },
}
loc_plan_REASON = "热爱专业、表现良好等泛化条件，专业简介与培养介绍，联系方式转引，重复的提交方式"

TITLE_ZHUANBO = "中国传媒大学攻读专业学位博士研究生培养工作规定（中传研字〔2025〕6号）"
TITLE_SHIJIAN = "中国传媒大学专业学位博士研究生专业实践能力考核工作办法（研究生院〔2024〕73号）"
TITLE_BANJI = "中国传媒大学优秀班集体评选办法（中传学教字〔2008〕121号）"
TITLE_BENKE = "本科生院〔2026〕50号关于开展2026—2027学年秋季学期2026级新生选课工作的通知"
TITLE_FJ1 = "中国传媒大学家庭经济困难学生认定申请表（2026年）"
TITLE_FJ2 = "中国传媒大学家庭经济困难学生认定审批表（2026年）"
TITLE_ZONGCE = "中国传媒大学音乐与录音艺术学院本科生综合素质评价办法实施细则（20250728修订）"
TITLE_TIZHI = "中国传媒大学《国家学生体质健康标准》实施办法（2024年修订）（本科生院〔2024〕115号）"

SPECIAL_DROP_REASON = {
    "pt-3424b28ba2": "内容已并入 pt-a47fbb97b0（不参与预置的必修课）",
}

ANSWER_FIX = {
    "pt-a47fbb97b0": "2026-2027学年秋季学期必修课已统一预置，其中以下必修课不参与预置，需自行选课等待抽签：1.体育（1）、计算与AI思维、理解传播、人文科学导论、设计思维、审美导论、自然科学导论。2.学院开设的分组课程。",
    "pt-623cbbc629": "梆子井宿舍内设施尺寸：普通床外尺寸200×90内长190，加长床尺寸210×90。",
    "pt-eb846a06d1": "中蓝一期宿舍内设施尺寸：普通床铺尺寸外框190×90，下铺距地面40，上下铺高度100，上铺到房顶高度135。",
}

KEEP_SOURCES = [
    ("hbf9b942", hbf9b942_KEEP, hbf9b942_REASON),
    ("hbfe67dc", hbfe67dc_KEEP, hbfe67dc_REASON),
    ("hbffbdcb", hbffbdcb_KEEP, hbffbdcb_REASON),
    ("loc-xuex", loc_xuex_KEEP, loc_xuex_REASON),
    ("loc-中传宿舍", loc_sushe_KEEP, loc_sushe_REASON),
    ("loc-中国传媒", loc_zgcm_KEEP, loc_zgcm_REASON),
    ("loc-本科生院", loc_benke_KEEP, loc_benke_REASON),
    ("loc-附件1-", loc_fj1_KEEP, loc_fj1_REASON),
    ("loc-附件2-", loc_fj2_KEEP, loc_fj2_REASON),
    ("loc-附件6-", loc_fj6_KEEP, loc_fj6_REASON),
    ("tiyu-202", tiyu_KEEP, tiyu_REASON),
    ("tizhi-20", tizhi_KEEP, tizhi_REASON),
]
for _prefix, _keep in loc_plan_KEEP.items():
    KEEP_SOURCES.append((_prefix, _keep, loc_plan_REASON))

RETITLE: dict[str, str] = {}
for _pid in hbf9b942_KEEP:
    RETITLE[_pid] = TITLE_ZHUANBO
for _pid in hbfe67dc_KEEP:
    RETITLE[_pid] = TITLE_SHIJIAN
for _pid in hbffbdcb_KEEP:
    RETITLE[_pid] = TITLE_BANJI
for _pid in loc_benke_KEEP:
    RETITLE[_pid] = TITLE_BENKE
for _pid in loc_fj1_KEEP:
    RETITLE[_pid] = TITLE_FJ1
for _pid in loc_fj2_KEEP:
    RETITLE[_pid] = TITLE_FJ2
for _pid in loc_fj6_KEEP:
    RETITLE[_pid] = TITLE_ZONGCE
for _pid in tizhi_KEEP:
    RETITLE[_pid] = TITLE_TIZHI


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
                drops[pid] = SPECIAL_DROP_REASON.get(pid, reason)
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
        old = str(it.get("answer", ""))
        quote_obj = (it.get("evidence") or {}).get("answer") or {}
        old_quote = str(quote_obj.get("quote", ""))
        if text not in old and old not in text:
            raise SystemExit(f"正文修正与答案不符：{pid}")
        if text not in old_quote and old_quote not in text:
            raise SystemExit(f"正文修正与原引文不符：{pid}")
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
