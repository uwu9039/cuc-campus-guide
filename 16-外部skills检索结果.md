# 16 · 外部 skills 检索结果（三个方向）

> 2026-10-27 检索。**只收录能在 GitHub / 技能目录上找到实物、能 `npx skills add` 或 git clone 的**，
> 不写"应该有这样一个 skill"。评分只写与《校园办事向导》的贴合度，不写通用优劣。
>
> 本机已装：`~/.dsh/skills/` 7 个（docx / pdf / pptx / xlsx / frontend-design / web-access / github-credential）。

**检索入口**（以后自己加）：
[skills.rest](https://skills.rest/)（75 万条索引，带安装命令）· [SkillsMP](https://skillsmp.com/) ·
[vivy-yi/awesome-skills](https://github.com/vivy-yi/awesome-skills)（341 个仓库的目录）·
[anthropics/skills](https://github.com/anthropics/skills)（官方 17 个）· `npx skills add <repo>`

---

## 方向一 · 智能体能力强化

| skill | 来源 | 干什么 | 用在这份作品哪里 |
|---|---|---|---|
| **`evaluation`** / **`advanced-evaluation`** | [muratcankoylan/Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering)（19 个 skill） | 确定性检查、rubric、回归套件；LLM-as-judge 的直接打分 / 两两比较 / 偏差校准 | 直接接 `eval.py`：现在只报准确率，它给的是**可复现的评分口径 + 判官偏差处理** |
| **`tool-design`** | 同上 | 定义 agent-tool 契约、收敛工具面、让工具报错可执行 | 你的两个外部调用（视觉核对、LLM 裁决）各是一把"工具"，现在报错只返回 null |
| **`harness-engineering`** | 同上 | 锁死指标、耐用日志、新鲜度门、回滚、人工审批边界 | 对应 `tools/pipeline.py` 的四步必跑，缺"锁定指标 + 异常时回滚" |
| **`Skill_Seekers`** | [yusufkaraaslan/Skill_Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) ⭐8.2k | 把文档站 / GitHub 仓库 / PDF 转成 skill，带冲突检测 | 你手上 **619 份语料**，现在是 items.json 里的条目；它能把某一专题（如学籍流转）压成独立 skill |
| **`planning-with-files`** | [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) ⭐11.6k | Manus 式「Markdown 持久计划」，跨长任务不丢线 | 你的 `09-进度快照` 已经是这个模式的手工版，可换成它的机制 |
| **`superpowers`** | [obra/superpowers](https://github.com/obra/superpowers) ⭐38k | 14 个工程方法论 skill（含完成前自验证） | 想给"改代码前先验证"这类纪律上约束时用；对作品本体不直接加分 |
| **`Claudeception`** | [blader/Claudeception](https://github.com/blader/Claudeception) ⭐1.5k | 从实际工作中自动抽取新 skill、持续学习 | 你每次修 badcase 都是一次"该沉淀成 skill"的动作，它把这个自动化 |

> 读法提醒：「智能体能力强化」有两种读法 —— **把 agent 跑得更好**（上表 evaluation / tool-design / harness），
> 和**帮你造 agent**（SkillForge、[alirezarezvani/claude-code-skill-factory](https://github.com/alirezarezvani/claude-code-skill-factory)）。
> 后者对参赛作品不加分，除非你要把"我怎么造出这个 bot"本身当卖点。

---

## 方向二 · 数据处理能力强化

| skill | 来源 | 干什么 | 用在这份作品哪里 |
|---|---|---|---|
| **`data-cleaning-skill`** | [yangqiong/claude-skills](https://github.com/yangqiong/claude-skills/tree/main/data-analysis/data-cleaning)（[条目](https://skills.rest/skill/data-cleaning-skill)） | 缺失值 / 重复 / 类型转换 / Z-score·IQR 异常值 / 字符串归一 / 数据质量报告 | `items.json` 现在 0 缺证靠自写脚本；它给的是**标准清洗管线 + 质量报告** |
| **`Data Transformation & ETL`** | [simkeyur](https://skills.rest/skill/data-transformation-etl) | 端到端 ETL，带校验与审计留痕 | 对应 `fetch → 抽取 → 入库` 那条链，"审计留痕"正是你要的 sha256 + 抓取时间 |
| **`csv-data-summarizer`** | [coffeefuelbump](https://github.com/coffeefuelbump/csv-data-summarizer-claude-skill) ⭐196 | 上传 CSV 自动出统计摘要、缺数据检测、快速可视化 | 语料台账 `corpus-index.json` 的体检（未被引用 141 份这类统计）现在是你手写的 |
| **`pivot-table-cross-analysis`** | [OpenSenseNova](https://skills.rest/skill/pivot-table-cross-analysis)（官方） | Excel 分类数据交叉表 + 热力图 | 覆盖对照表（清单 124 份 × 我们语料）适合做成交叉表 |
| **`md_exporter`** | [bowenliang123/md_exporter](https://github.com/bowenliang123/md_exporter) ⭐174 | Markdown → DOCX / PPTX / XLSX，兼 Dify 插件 | 交付物（1000 字设计文档、评测表）一条命令出多格式 |
| **本机已有** `xlsx` `docx` `pdf` | anthropics 官方 | 读写 Excel / Word / PDF | 已装，别重找；做评测表和设计文档直接用 |

> 缺的一类：**"证据/引文校验"没有现成 skill**。你要的「子串必须命中原文」这件事在公共技能库里没对上，
> 最接近的是 `data-cleaning-skill` 的 validation 段和 `ETL` 的 audit trail 段 —— 也就是说
> `tools/check_quotes.py` 这块**确实是原创**，可以放心当记忆点讲。

---

## 方向三 · 说话有人味

这一方向是三个里**公共供给最丰富**的，而且质量比想象中高：

| skill | 来源 | 干什么 | 贴合度 |
|---|---|---|---|
| **`Humanizer-zh`** | [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) ⭐1.7k | 中文润色：**31 个检查点**分 A–F 六类（铺垫代替陈述 / 公式化节奏 / 拔高借权威 / 公式化排版 / 聊天残留 / 中文补充：长定语、"进行＋动词"、被字句堆叠、四字词排比、套话收尾） | ★★★★★ **首选**。它的铁律跟你的数据层同构：不编造功能/数据/来源，保留否定·条件·归因·范围·时间和完成状态，"可能"不改"确定" |
| **`humanizer`** | [blader/humanizer](https://github.com/blader/humanizer) ⭐3.3k | 英文原版，26 个模式；支持"给 2–3 段我自己的文字做 voice matching" | ★★★★ 模式表可直接翻译成中文规则；voice matching 可用来学"窗口老师的口吻" |
| **`stop-slop`** | [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | 五个维度打分（直给 / 节奏 / 尊重读者 / 像人 / 密度），<35/50 就重写 | ★★★★ 你缺的正是**可打分的验收口径**，这个可以直接当 `eval.py` 的第五个维度 |
| **`copywriting-tone-of-voice-creator`** | [samber/cc-skills](https://github.com/samber/cc-skills) | 产出 `TONE.md`：3–5 条声纹属性（每条带 do/don't/例句/反面例）、语气调制矩阵（情境 × 渠道）、**禁用词表**、称呼与句长规范 | ★★★★ 你要的「人设 + 三条语气规则」它有成套模板，缺点是 B2B 品牌视角、偏英文 |
| **`brand-voice-guidelines`** | [thatrebeccarae/claude-marketing](https://github.com/thatrebeccarae/claude-marketing) | 品牌语调指南，marketing 技能包里的一个 | ★★★ 轻量，可当 TONE.md 的简化版 |
| **宝鱼技能** | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) ⭐2.9k | 中文 AI agent 技能合集（写作/表达向） | ★★★ 中文语境补充，需自己挑 |

**共同的关键约束**（三个都写明，可当你的护栏依据）：只改措辞，不改事实与确定程度；
缺细节就问，不补；文件模式下不动代码、数据、路径、锚点。

---

## 判断

1. **先装 `Humanizer-zh`** —— 它是唯一一个中文、且规则与你"不许编"原则同构的成品，装完能把 `index.html` + `app.py` 的散文腔一次压掉。`npx skills add https://github.com/op7418/Humanizer-zh.git`
2. **再装 `stop-slop` 的打分表**（不必全装，抄它的五维 rubric 进 `eval.py`），让"有人味"变成可报数字的第五项。
3. 数据处理侧，**只有 `Data Transformation & ETL` 的审计留痕段值得抄**；其余能力你本地脚本已经覆盖，装全套反而多一层依赖。
4. 智能体侧，**`evaluation` 与 `tool-design` 是最对味的两个**（都直接对应你已有的 eval.py 和两个外部调用），
   其余（superpowers / Claudeception / planning-with-files）属于"顺手变强"，不加分。

> 结论：**12 个候选里真正能提升这份作品的只有 3 个**（Humanizer-zh、stop-slop 的 rubric、evaluation/tool-design）。
> 其余是工具链的通用收益，不是评委能看见的差异。
