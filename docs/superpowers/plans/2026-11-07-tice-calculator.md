# 体测计算器（/tice.html）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把微信小程序「白杨口袋」的体测计算器功能原样复刻成广院通里的独立页面 `/tice.html`，功能项不增不减，UI 按钴蓝场重画。

**Architecture:** 纯前端。一个机器派生的数据文件 `tice-standard.json` 作唯一事实源；一个不碰 DOM 的纯函数算分内核；一个带失败保护的本机存储层；一个 vanilla JS 页面把三块拼起来，并在 `/field` 顶栏留一个入口。后端 `app.py` 一行不改，靠现有静态挂载伺服。

**Tech Stack:** 原生 HTML/CSS/JS（无框架、无构建）、Node v24（转录器与算分单测）、Python 3.15 `.venv`（数据不变量与静态契约测试）、git 2.56。

**Spec:** [docs/superpowers/specs/2026-11-07-tice-calculator-design.md](../specs/2026-11-07-tice-calculator-design.md)

数据源（师哥传承包解包产物，**不进仓库**）：`<本机临时解包目录>\out\app-service.js`，模块 `data/fitness-standard.js` 位于该文件第 153317–172585 字符区间。

## Global Constraints

每个任务的验收都隐含本节，逐条照抄 spec：

1. 不改 `app.py`，不接问答路由，不改 `/api/ask` 与 SSE 契约，不做服务端账号。
2. 不上传任何数据；所有记录只写本机 `localStorage`。
3. 不搬他的代码，只搬标准数据。`web-next/tice-standard.json` 是阈值唯一事实源，其余文件不得内嵌任何阈值。
4. `tice.css` 不得出现裸色值；颜色一律 `var(--…)`，token 只允许定义在 `field.css` 的 `:root` 块里。
5. 顶栏日夜开关 `themesw` 必须是 `<nav class="topacts">` 的最后一个元素（`tools/test_field_ui.py:408` 直接断言）。体测入口只能插在它左边。
6. 文案照他：四态、三种未完成、各条单位混淆提示逐条搬，不改写、不加「温馨提示」腔；引用校方规定保留原文限定词。
7. Python 一律用 `./.venv/Scripts/python.exe`，不装任何 npm 包、不装编译依赖。
8. 数值比较一律走整数刻度（一位小数 ×10、时间换算成总秒），不得用浮点直接比阈值。
9. 每任务一提交。每个任务收尾必须让 `test_field*.py` 与 `test_tice*.py` 全绿，不许为了让测试过去放宽任何现有断言。
10. **本机没有任何 git identity**（`git config user.name` 与 `user.email` 均为空，`git var GIT_COMMITTER_IDENT` 退出 128），且不允许改动 git 配置。因此**本计划里每一处 `git commit` 都必须加前缀**：

```bash
git -c user.name=campus-guide -c user.email=noreply@local commit -q -m "……"
```

把后面各任务步骤里写的 `git commit -q -m …` 一律按这条执行（包括已在计划文本里写成裸命令的那些）。基线提交 `e1de027`、`3f8e501` 就是用这个身份落的，保持后继一致。

11. 提交内容不得含本机绝对路径与账号名。`docs/superpowers/` 下的 spec 与 plan 目前带 `<仓库根目录>`、`<本机用户目录>/...`（Task 0 复核记为 Important）——本仓库不对外发布，实现阶段照旧写绝对路径以便核对；对外发布前必须按 Task 12 Step 3.5 脱敏。

12. **谁往 `web-next/` 落文件，谁就在同一个 commit 里把它加进白名单。** `tools/test_field_ui.py:1462` 的 `test_only_the_expected_files_were_added` 断言「`web-next/` 里相对备份新增的文件集合 == `expected`」，任何新建的 `web-next/tice*` 文件都会立刻让它变红，与本任务的其他断言无关。执行细则：
    - Task 1 起，凡新建 `web-next/<name>` 的任务，都要在同一次提交里把 `"<name>"` 加进 `tools/test_field_ui.py:1462` 的 `expected`，只加自己这次新建的那一个名字；不许提前加后面任务的文件（会反向红），也不许留给 Task 8 一次补齐（中间 6 个任务的门全红，门就没有意义）。
    - Task 8 Step 5 写的整份集合是**终态**：执行到那儿时集合应当已经逐项加满，那一步的职责是把写法收敛成计划里的最终形态并确认逐字相符，不是第一次补名单。
    - **并发例外：**本机另有一个会话正在同一工作树里做检索侧的活（实测 `web-next/ticket.html`、`tools/check_expect.py` 于 Task 0 基线之后出现且未纳管）。`ticket.html` 落在 `web-next/` 会让同一条断言把他也报出来。那不是本计划新增的文件，**绝对不许把它写进我们的 `expected` 来把门做绿**。判据改为：本次任务自己新建的文件都在名单里、且 `added − expected` 至多只剩 `ticket.html` 这一项外来文件；满足即视为门过，报告里如实写明「`test_only_the_expected_files_were_added` 因外来 `ticket.html` 而红，非本计划所致」。等对方把 `ticket.html` 纳管或移走，此条自动恢复。

13. **`tools/` 下有两类测试，收集方式不同，别混用。** `test_field_ui.py` 与 `test_tice*.py` 是 `unittest` 风格，可被 `discover` 收集；另有 16 个检索侧脚本风格测试（`test_sse_frames.py`、`test_assemble.py`、`test_zhuanye_tiaojian.py` 等），它们在模块末尾无条件 `sys.exit(...)`，被 `discover -p "test_*.py"` 导入时**必然**报 `ImportError: SystemExit`——与本项目改动无关，改不了也不该改。因此全量回归的门是 Task 12 Step 1 的两段式，不是单条 `test_*.py`。

---

## 命名与类型契约（所有任务共用，先读这段）

`tice-standard.json` 顶层键（Task 1 产出，Task 2 校验，Task 3 起消费）：

```
meta            {standardName, standardDocNo, schoolPolicyName, schoolPolicyDocNo,
                 policyEffectiveScope, phaseScope, verifiedDate, derivedAt,
                 sourceModule, sourceSha256, transcriber}
scoreLadder     [{score, level}] x20
limits          {maxStandardScore, maxSingleBonusScore, maxTotalBonusScore, maxTotalScore}
weights         {bmi, vitalCapacity, sprint50m, sitAndReach, standingLongJump,
                 pullUps, sitUps, run1000m, run800m}   整数百分数。这是男女并集，9 键相加 = 130；
                 真正的不变量是**按性别各 100**：男 = bmi+vc+50m+sitReach+longJump+pullUps+run1000m
                 = 15+15+20+10+10+10+20 = 100，女同构（pullUps/run1000m 换成 sitUps/run800m）。
                 断言写并集和 = 130 与各性别子集和 = 100 两条，别写「整个 weights 和为 100」——那永远不成立。
gradeGroups     {GRADE_12: grade12, GRADE_34: grade34}   枚举名→组别 id；两个 id 齐即可，无人按键取
gradeToGroup    {大一: grade12, 大二: grade12, 大三: grade34, 大四: grade34}
                 键必须是中文年级标签（下游 `STD.gradeToGroup[grade]` 传的就是 `'大一'`），
                 不是模块内部的 freshman/sophomore/junior/senior。
events          事件键 → EventDef（见下）
bmi             {unit, unitLabel, scale, weightPercent, categoriesByGender, unresolvedGapsByGender}
unresolvedRules {bmi_boundary_precision_unresolved,
                 measurement_precision_rounding_unresolved,
                 cuc_2024_policy_multi_year_scope_unresolved}
```

`EventDef`：

```
{name, tableCode, unit, unitLabel, direction, scale, decimalPlaces, unitType,
 genders, bonusEligible, bonusDeltas, thresholds}
  direction   ∈ "higher_is_better" | "lower_is_better"
  unitType    ∈ "number" | "mmss"
  genders     ["male","female"] | ["male"] | ["female"]
  bonusDeltas null | [{bonusScore, delta}] | [{bonusScore, reductionSeconds}]
  thresholds  {male: {grade12: (number|string|null)[20], grade34: …}, female: {…}}
```

实测基准（Task 1/2/5 用它自检，2026-11-07 从传承包读出）：

```
24 张表 / 480 槽 / 470 个数 / 10 个 null
null 只在 pullUps 的 male grade12 与 male grade34，槽号 5,7,9,11,13（= 78/74/70/66/62 分档）
肺活量 male grade12 = 5040 4920 4800 4550 4300 4180 4060 3940 …  末位 2300
50米   male grade12 = 6.7 6.8 6.9 7.0 7.1 7.3 7.5 …   female grade34 首位 7.4
坐位体前屈 male grade12 = 24.9 23.1 21.3 … 末位 -1.3
立定跳远 male grade12 首位 273；引体向上 male grade12 = 19 18 17 16 15 null 14 null …
1000米 male grade12 首位 3'17"（197 秒）；800米 female grade12 首位 3'18"（198 秒）
附加分阈值 = 100 分档阈值 ± delta：力量 +1..+10（C=19 → 20..29），长跑 −4..−35 秒（C=197 → 193..162）
```

`tice-calc.js` 导出（Task 3–5 逐步补齐，签名一次定死）：

```
prepareStandard(json)            → Standard    派生 levels 与 bonusTable，只做一次
gradeGroupOf(std, grade)         → "grade12" | "grade34"
eventKeysFor(std, gender)        → string[7]
parseEnduranceTime(raw)          → {ok:true, seconds} | {ok:false, code}
formatEnduranceTime(total)       → "3'17\"" | null
scaleOf(value, scale)            → number | null
scoreLevel(std, evKey, gender, group, scaled) → LevelResult
scoreEvent(std, {gender, grade, eventKey, raw, inputs}) → EventResult
computeBonus(std, evKey, gender, group, scaled) → {bonusScore, matchedTier}
gradeOf(total)                   → {gradeCode, gradeLabel}
assemble(std, {gender, grade, answers})        → TotalResult
```

`LevelResult = {status:"scored"|"unresolved"|"invalid", score, level, matchedThreshold, rawDisplay, reason}`
`EventResult = {eventKey, name, status:"complete"|"incomplete"|"invalid"|"unresolved", levelResult:LevelResult, score, weightPercent, weightedContribution, bonusEligible, bonusScore, hint}`
`TotalResult = {status, items: EventResult[], standardScore, strengthBonus, enduranceBonus, totalBonus, totalScore, gradeCode, gradeLabel, blockingReasons}`

**`EventResult` 的契约键恒在，四个 status 不得对应四种对象形状。**Task 3 的写法是四段各自字面量，`toScaled` 失败那一路漏了 `weightPercent`/`bonusEligible`——Task 3 保持原样（改动会打乱分步），**由 Task 4 重写 `scoreEvent` 时用一个 `mkResult` 工厂收口**（见 Task 4 Step 3）。`code` 与 `scaledValue` 是契约外的扩展键：`code` 在**每一路 `invalid`** 上都要有（`missing_value` / `empty_string` / `invalid_type` / `invalid_number_format` / `must_be_integer` / 三条长跑时间码 / `must_be_greater_than_zero`），`scaledValue` 只在算得出唯一刻度时存在。下游取失败原因只读 `r.code`，不许写两套取数逻辑。

**注意（回源更正，2026-11-09）：没有 `below_minimum` 这个 invalid 码。** 原程序对「低于最低档」（如肺活量 1000、1000 米 6'30"）给的是 `status:'complete'`、`score:0`、`level:'不及格'`、`matchedThreshold:null`。`invalid` 只留给**输入本身不成立**的那些情形（空串、非数值、整数项收小数等）。见 ledger「回源轮」Ruling 8。

---

## Task 0: 仓库、基线与分支

工作区不是 git 仓库。实测本目录有 **3.8 GB 未被 `.gitignore` 覆盖**的派生物（`video-remotion/node_modules` 约 460 MB、`_review_items/` 里几十份 items 快照、`sources/vector/vectors.npy` 60 MB、根 `items.json` 76 MB），所以本任务**不用 `git add -A`**，改成白名单基线：只收本功能会碰的路径。控制者已就此下过裁决并记入 ledger（见「Pre-flight」表第一行）。

**Files:**
- Create: `.git`、分支 `feat/tice-calculator`
- Modify: `.gitignore`（只追加，不重写）
- Create（基线内容）: `.gitignore` `app.py` `README.md` `release-notes.md` `docs/` `tools/` `web-next/`

- [ ] **Step 1: 建库**

Run:
```bash
cd <仓库根目录> && git init -q && git rev-parse --show-toplevel
```
Expected: 打印 `<仓库根目录>`。

- [ ] **Step 2: 补齐忽略规则**

现有 `.gitignore` 已覆盖 `.venv/` `_backups/` `_modelscope_bundle/` `*.bak` `/_release_*/` `/kb.sqlite`。在文件末尾追加（本目录 `items.json.bak-*` 这类带后缀的不被 `*.bak` 命中，必须单独挡）：

```
/items.json
/items*.json
/items_before_*.json
/_review_items/
/_api_dig/
/_attachments_*
/_studio_*/
/_exp_review_*/
/video-remotion/
/video-promotion/
/video-promo/
/sources/
/dist/
*.npy
*.tar.gz
*.json.gz
/download.devtools
__pycache__/
```

追加后逐条验证，一条不许漏：

Run:
```bash
cd <仓库根目录> && for f in items.json items.json.bak-20261030 items_before_facts_20261031.json _review_items/items.json.cleaned_accident_20261105 sources/vector/vectors.npy video-remotion/node_modules kb.sqlite .venv _backups/web-next-before-field-2026-11-02 sources-archive.tar.gz doc-report.json.gz download.devtools __pycache__; do printf '%-56s ' "$f"; git check-ignore -q "$f" && echo IGNORED || echo "NOT IGNORED"; done
```
Expected: 全部 `IGNORED`。任何 `NOT IGNORED` 先补规则再往下走。

- [ ] **Step 3: 白名单加基线，并核对没有重型文件混进来**

Run:
```bash
cd <仓库根目录> && git add .gitignore app.py README.md release-notes.md docs tools web-next && git diff --cached --name-only | wc -l && git diff --cached --name-only -z | xargs -0 -I{} du -k "{}" 2>/dev/null | sort -rn | head -5
```
Expected: 文件数在几百以内；最大的五个单项都必须远小于 5 MB（`app.py` 约 1 MB 应是量级最大的一档）。若出现几十 MB 的项，说明它没被忽略，回 Step 2 补规则后 `git reset` 重来。

- [ ] **Step 4: 跑测试基线并提交**

Run:
```bash
cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_field*.py" 2>&1 | tail -3
```
Expected: `Ran 136 tests` + `OK`。2026-11-07 实测就是这个数；不是就先停下报告，别往下走。

Run:
```bash
cd <仓库根目录> && git commit -q -m "chore: 基线快照（体测计算器开工前）" && git log --oneline -1
```

- [ ] **Step 5: 切功能分支**

基线提交只是快照，留在初始分支；本功能所有实现提交走独立分支，不在 main/master 上直接实现。

Run:
```bash
cd <仓库根目录> && git branch --show-current && git checkout -q -b feat/tice-calculator && git branch --show-current
```
Expected: 先打印仓库默认分支名（`master` 或 `main`），后打印 `feat/tice-calculator`。

- [ ] **Step 6: 确认工作树干净**

Run: `cd <仓库根目录> && git status --porcelain | grep -v "^?? " | head`
Expected: 无输出（已跟踪文件全部干净；未跟踪的 `??` 重型产物已被忽略规则挡住，不该再出现成堆未跟踪项——若仍有大量 `??`，回 Step 2 继续补）。

---

## Task 1: 转录器——执行他的数据模块派生 tice-standard.json

不手抄 470 个数。他包里的 `data/fitness-standard.js` 是 CommonJS 模块，直接在 Node 里装载并读 `module.exports`：可复现、可比对，顺带把 `unpopulatedScores`、BMI 空隙、附加分表挂法这三处最容易抄错的东西一次拿全。

**Files:**
- Create: `tools/tice_bundle.js`（模块装载器）
- Create: `tools/tice_build_json.js`（派生与自检）
- Create: `web-next/tice-standard.json`（脚本产物，不手改）

**Interfaces:**
- Consumes: `%TEMP%/wxdump/out/app-service.js`
- Produces: `web-next/tice-standard.json`

- [ ] **Step 0（仅当临时目录已空）: 重新解包**

Run: `cd <本机临时解包目录> && node decrypt.js 2>&1 | tail -3`
Expected: `extracted 60 files`。若整个目录不在了，按 spec 记录的 V1MMWX 规则重建：`key = PBKDF2-SHA1(appid, "saltiest", 1000, 32)`，剥 6 字节 `V1MMWX` 后 1024 字节走 AES-256-CBC（iv `"the iv: 16 bytes"`），**只取前 1023 字节**，其余逐字节 XOR `0x61`；明文头 14 字节后 u32BE 是 fileCount，记录为 `(nameLen, name, off, size)` 全大端。

- [ ] **Step 1: 装载器**

Create `tools/tice_bundle.js`：

```js
// 只为取数据：从解包产物里把 define("name", function(...){...}) 的函数体切出来，
// 用最小 CommonJS 注册表执行。不跑页面逻辑，不联网。
const fs = require('fs');

const SRC = sourcePath();   // argv[2] 或 TICE_SOURCE，二者皆无则抛出并提示 Step 0；
                           // 不写死本机绝对路径：提交内容不得带账号名（Global Constraint 11）

function readSource() { return fs.readFileSync(SRC, 'utf8'); }

function parseDefs(src) {
  const defs = new Map();
  const OPEN = /define\("([^"]+)", function\([^)]*\)\{/g;
  let m;
  while ((m = OPEN.exec(src))) {
    const start = m.index + m[0].length;
    let depth = 1, i = start, q = null, esc = false;
    for (; i < src.length && depth > 0; i += 1) {
      const c = src[i];
      if (q) {
        if (esc) esc = false;
        else if (c === '\\') esc = true;
        else if (c === q) q = null;
        continue;
      }
      if (c === '"' || c === "'") q = c;
      else if (c === '{') depth += 1;
      else if (c === '}') depth -= 1;
    }
    defs.set(m[1], src.slice(start, i - 1));
  }
  return defs;
}

function makeLoader(defs) {
  const cache = new Map();
  const shortName = (spec) => spec.replace(/^(\.\.\/)+/, '').replace(/\.js$/, '');
  function resolve(spec) {
    if (defs.has(spec)) return spec;
    const want = shortName(spec);
    const hit = [...defs.keys()].find((k) => shortName(k) === want)
      || [...defs.keys()].find((k) => k.endsWith('/' + want) || k.endsWith(want));
    if (!hit) throw new Error('bundle 里找不到模块: ' + spec);
    return hit;
  }
  function load(spec) {
    const key = resolve(spec);
    if (cache.has(key)) return cache.get(key);
    const module = { exports: {} };
    cache.set(key, module.exports);                       // 先登记，防循环 require
    new Function('require', 'module', 'exports',
      'window', 'document', 'navigator', 'localStorage',   // 空壳，数据模块不碰
      defs.get(key))(load, module, module.exports, undefined, undefined, undefined, undefined);
    cache.set(key, module.exports);
    return module.exports;
  }
  return { load, resolve };
}

module.exports = { readSource, parseDefs, makeLoader, SRC };
```

- [ ] **Step 2: 冒烟——先看真实 exports**

Create `tools/tice_build_json.js`，本步只打印形状：

```js
const { readSource, parseDefs, makeLoader } = require('./tice_bundle.js');
const { load } = makeLoader(parseDefs(readSource()));

function shape(v, d) {
  if (d > 2 || v === null || typeof v !== 'object') return Array.isArray(v) ? `[${v.length}]` : typeof v;
  const ks = Object.keys(v).slice(0, 12);
  return '{' + ks.map((k) => `${k}:${shape(v[k], d + 1)}`).join(' ') + '}';
}

const S = load('data/fitness-standard.js');
console.log('exports :', Object.keys(S).sort().join(' '));
console.log('STANDARD_VERSION :', JSON.stringify(S.STANDARD_VERSION));
console.log('SCORE_LIMITS     :', JSON.stringify(S.SCORE_LIMITS));
console.log('GRADE_GROUPS     :', JSON.stringify(S.GRADE_GROUPS));
console.log('GRADE_TO_GROUP_MAP:', JSON.stringify(S.GRADE_TO_GROUP_MAP));
console.log('FITNESS_STANDARDS:', shape(S.FITNESS_STANDARDS, 0));
console.log('BMI male         :', shape(S.BMI_CATEGORIES_BY_GENDER.male, 0));
console.log('UNRESOLVED       :', Object.keys(S.UNRESOLVED_POLICY_RULES).join(' '));
```

Run: `cd <仓库根目录> && node tools/tice_build_json.js`
Expected: 打出全部 exports 键。已实测含 `STANDARD_VERSION DATA_SOURCES GENDERS GRADES GRADE_GROUPS GRADE_TO_GROUP_MAP GRADE_LABELS GRADE_GROUP_LABELS TOTAL_SCORE_GRADE_RULES SCORE_LIMITS BMI_CATEGORIES_BY_GENDER RAW_THRESHOLDS FITNESS_STANDARDS UNRESOLVED_POLICY_RULES parseMmSsLiteralToSeconds formatSecondsToMmSsLiteral`。
注意三点：他**确实导出了 20 档阶梯**——`STANDARD_SCORE_TIERS`（共 17 个导出，此处早先记成 16 个是漏数），Step 3 的内容闸要用它交叉验证，而不是只让 24 张表互相对齐（24 张表一起错也是错）；`scoreLadder` 仍从 `rawTableRows` 反推，反推结果必须与那份导出逐档相等；`FITNESS_STANDARDS` 的嵌套层次以本步打印为准。

- [ ] **Step 3: 派生 + 自检**

把 `tice_build_json.js` 换成完整版。关键：不猜 `FITNESS_STANDARDS` 的嵌套，递归收集所有带 `eventKey`+`gender`+`gradeGroup` 的对象，形状怎么变都吃得下。

```js
const crypto = require('crypto');
const fs = require('fs');
const { readSource, parseDefs, makeLoader } = require('./tice_bundle.js');

const src = readSource();
const { load } = makeLoader(parseDefs(src));
const S = load('data/fitness-standard.js');

const WALK_MAX_DEPTH = 5;
function collectStandards(node, depth, out) {
  if (!node || typeof node !== 'object' || depth > WALK_MAX_DEPTH) return out;
  if (Array.isArray(node)) { node.forEach((v) => collectStandards(v, depth + 1, out)); return out; }
  if (typeof node.eventKey === 'string' && node.gender && node.gradeGroup) out.push(node);
  Object.values(node).forEach((v) => collectStandards(v, depth + 1, out));
  return out;
}

const all = collectStandards(S.FITNESS_STANDARDS, 0, []);
if (!all.length) throw new Error('FITNESS_STANDARDS 里没找到事件定义，检查 Step 2 打印的形状');

// 20 档 ladder 从任意一张满表的 rawTableRows 反推，全表必须一致
const ladderOf = (ev) => ev.rawTableRows.map((r) => ({ score: r.score, level: r.level }));
const nonBmi = all.filter((e) => e.direction !== 'bmi_category');
const scoreLadder = ladderOf(nonBmi[0]);
nonBmi.forEach((e) => {
  if (JSON.stringify(ladderOf(e)) !== JSON.stringify(scoreLadder)) {
    throw new Error(`${e.eventKey}/${e.gender}/${e.gradeGroup} 的分值阶梯与首表不一致`);
  }
});

const events = {};
nonBmi.forEach((e) => {
  const k = e.eventKey;
  events[k] = events[k] || {
    name: e.eventName, tableCode: e.tableCode, unit: e.unit, unitLabel: e.unitLabel,
    direction: e.direction, scale: e.precision.scale, decimalPlaces: e.precision.decimalPlaces,
    unitType: (e.unit === 's' && e.unitLabel === '分·秒') ? 'mmss' : 'number', weightPercent: e.weightPercent, bonusEligible: !!e.bonusEligible,
    bonusDeltas: e.bonusEligible ? e.bonusTable.map((t) => (
      e.direction === 'higher_is_better'
        ? { bonusScore: t.bonusScore, delta: t.deltaThreshold }
        : { bonusScore: t.bonusScore, reductionSeconds: t.reductionSeconds })) : null,
    thresholds: {},
  };
  const t = events[k];
  if (t.name !== e.eventName || t.direction !== e.direction || t.bonusEligible !== !!e.bonusEligible) {
    throw new Error(`${k} 在不同 性别/年级组 下定义不一致`);
  }
  t.thresholds[e.gender] = t.thresholds[e.gender] || {};
  t.thresholds[e.gender][e.gradeGroup] = e.rawTableRows.map((r) => r.threshold);
});
Object.values(events).forEach((t) => { t.genders = Object.keys(t.thresholds).sort(); });

const bmi = S.BMI_CATEGORIES_BY_GENDER;
const out = {
  meta: {
    standardName: S.STANDARD_VERSION.nationalStandardName,
    standardDocNo: S.STANDARD_VERSION.nationalStandardDocNo,
    schoolPolicyName: S.STANDARD_VERSION.schoolPolicyName,
    schoolPolicyDocNo: S.STANDARD_VERSION.schoolPolicyDocNo,
    policyEffectiveScope: S.STANDARD_VERSION.schoolPolicyEffectiveScope,
    phaseScope: S.STANDARD_VERSION.phaseScope,
    verifiedDate: S.STANDARD_VERSION.verifiedDate,
    derivedAt: new Date().toISOString().slice(0, 10),
    sourceModule: 'data/fitness-standard.js',
    sourceSha256: crypto.createHash('sha256').update(src).digest('hex').slice(0, 16),
    transcriber: 'tools/tice_build_json.js',
  },
  scoreLadder,
  limits: S.SCORE_LIMITS,
  weights: Object.assign(
    { bmi: bmi.male.weightPercent },
    Object.fromEntries(Object.keys(events).map((k) => [k, events[k].weightPercent]))),
  gradeGroups: S.GRADE_GROUPS,
  gradeToGroup: Object.fromEntries(Object.entries(S.GRADE_TO_GROUP_MAP)
    .map(([k, v]) => [S.GRADE_LABELS[k] || k, v])),
  events,
  bmi: {
    unit: bmi.male.unit, unitLabel: bmi.male.unitLabel, scale: bmi.male.scale,
    weightPercent: bmi.male.weightPercent,
    categoriesByGender: { male: bmi.male.categories, female: bmi.female.categories },
    unresolvedGapsByGender: { male: bmi.male.unresolvedGaps || [], female: bmi.female.unresolvedGaps || [] },
  },
  unresolvedRules: S.UNRESOLVED_POLICY_RULES,
};

const flat = Object.values(events).flatMap((e) => Object.values(e.thresholds)
  .flatMap((g) => Object.values(g)));
const slots = flat.reduce((a, x) => a + x.length, 0);
const nulls = flat.reduce((a, x) => a + x.filter((v) => v === null).length, 0);
console.log('arrays %d  slots %d  nulls %d  numbers %d  events %d',
            flat.length, slots, nulls, slots - nulls, Object.keys(events).length);

// 计数只证明「形状像」，不证明「内容对」。下面四道内容闸才是这份数据能当唯一数据源的理由。
const REQUIRED_EVENT_KEYS = ['name', 'tableCode', 'unit', 'unitLabel', 'direction', 'scale',
  'decimalPlaces', 'unitType', 'genders', 'bonusEligible', 'bonusDeltas', 'thresholds', 'weightPercent'];
Object.entries(events).forEach(([k, e]) => {
  const missing = REQUIRED_EVENT_KEYS.filter((f) => e[f] === undefined);
  if (missing.length) throw new Error(`${k} 缺契约字段 ${missing.join(',')}——JSON.stringify 会静默丢掉 undefined，别让它混过去`);
});
if (tableCount !== 24) {   // tableCount 在每次真正写入 thresholds 格子时 +1，不是 collectStandards 的节点数
  throw new Error(`写入 ${tableCount} 张表，应为 24（4 项男女共有 × 2 性别 × 2 年级组 = 16，加 4 项单性别项目 × 1 性别 × 2 年级组 = 8）——有表没落到格子里`);
}
// 阶梯必须与模块自己的权威导出一致，不能只跟第一张表对齐：24 张表一起错也是错。
const tiers = S.STANDARD_SCORE_TIERS;
if (!tiers) throw new Error('模块未导出 STANDARD_SCORE_TIERS，无法交叉验证阶梯');
if (JSON.stringify(scoreLadder.map((t) => t.score)) !== JSON.stringify(tiers.map((t) => t.score ?? t))) {
  throw new Error('反推的分值阶梯与模块导出的 STANDARD_SCORE_TIERS 不一致');
}
flat.forEach((arr, i) => { if (arr.length !== 20) throw new Error(`第 ${i} 张表 ${arr.length} 档，应为 20`); });
const nullIdx = (ev, gender, group) =>
  (events[ev].thresholds[gender][group] || []).map((v, i) => (v === null ? i : -1)).filter((i) => i >= 0);
const nullSpec = { 'pullUps/male/grade12': [5, 7, 9, 11, 13], 'pullUps/male/grade34': [5, 7, 9, 11, 13] };
const nullSeen = {};
Object.entries(events).forEach(([ev, e]) => Object.entries(e.thresholds)
  .forEach(([g, gs]) => Object.entries(gs).forEach(([gr, arr]) => {
    const idx = arr.map((v, i) => (v === null ? i : -1)).filter((i) => i >= 0);
    if (idx.length) nullSeen[`${ev}/${g}/${gr}`] = idx;
  })));
if (JSON.stringify(Object.keys(nullSeen).sort()) !== JSON.stringify(Object.keys(nullSpec).sort())
 || Object.entries(nullSpec).some(([k, v]) => JSON.stringify(nullSeen[k]) !== JSON.stringify(v))) {
  throw new Error(`null 位置与 spec 不符：实得 ${JSON.stringify(nullSeen)}`);
}

if (flat.length !== 24 || slots !== 480 || nulls !== 10) {
  throw new Error('派生结果与 spec 实测不符（应为 24 表 / 480 槽 / 10 null），拒绝写出');
}
fs.writeFileSync('web-next/tice-standard.json', JSON.stringify(out, null, 1) + '\n');
console.log('wrote web-next/tice-standard.json');
```

防 last-write-wins：`tableCount` 只在赋值那一下 +1，所以赋值处必须先查重，否则覆盖掉一张表后格子总数仍然凑得出 24。在 `events[k].thresholds[e.gender][e.gradeGroup]` 赋值前判一句，重复即抛：

```js
  if (t.thresholds[e.gender][e.gradeGroup]) {
    throw new Error(`${k}/${e.gender}/${e.gradeGroup} 出现第二张表，拒绝静默覆盖`);
  }
```

- [ ] **Step 4: 跑派生**

装载器不得把本机账号路径写死进提交的源码（Global Constraint 11 说的是「提交内容」，`tools/*.js` 也算）。源包路径由参数或环境变量给，缺了就报错并提示 Step 0：

Run: `cd <仓库根目录> && node tools/tice_build_json.js "<本机临时解包目录>/out/app-service.js"`（或 `TICE_SOURCE=… node tools/tice_build_json.js`）
Expected: `arrays 24  slots 480  nulls 10  numbers 470  events 8` + 一行完整 SHA-256 + `wrote …`。对不上就停在装载器上查形状，**不许手改 JSON 里的阈值**。写出路径按 `__dirname` 解析，换个工作目录跑不该把文件写到别处。
`derivedAt` 用 UTC 日期，本机 UTC+8 会在早上 8 点翻转，因此「重跑必然字节相同」只在同一天内成立；要跨天稳定就 `TICE_DERIVED_AT=2026-11-07` 给定，测试里不许断言这个字段。

- [ ] **Step 5: 抽查四个已知值**

Run:
```bash
cd <仓库根目录> && "./.venv/Scripts/python.exe" -c "
import json;S=json.load(open('web-next/tice-standard.json',encoding='utf-8'))
print(S['events']['vitalCapacity']['thresholds']['male']['grade12'][:5])
print(S['events']['standingLongJump']['thresholds']['male']['grade12'][0])
print(S['events']['pullUps']['thresholds']['male']['grade12'][:6])
print(S['events']['run1000m']['thresholds']['male']['grade12'][0])
print(S['limits'])"
```
Expected 逐行：`[5040, 4920, 4800, 4550, 4300]` / `273` / `[19, 18, 17, 16, 15, None]` / `197` / `{'maxStandardScore': 100, 'maxSingleBonusScore': 10, 'maxTotalBonusScore': 20, 'maxTotalScore': 120}`。第三行的 `None` 就是引体向上 78 分档在原表无阈值那件事；第四行 `197` 是分秒按总秒落盘（3'17"）。

- [ ] **Step 6: 白名单加本次新建的文件（Global Constraint 12）**

`tools/test_field_ui.py:1462` 的 `expected` 加上 `"tice-standard.json"`：

```python
        expected = {f"field.{ext}" for ext in ("html", "css", "js")} | {EMBLEM} | {"tice-standard.json"}
```

Run: `cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_field*.py" 2>&1 | tail -8`
Expected: `Ran 136 tests`。`test_only_the_expected_files_were_added` 这一条在 `added − expected` 只剩外来的 `ticket.html` 时仍会红——按 Global Constraint 12 的并发例外处置：如实记录，不要把 `ticket.html` 加进名单。其余 135 条必须绿。

- [ ] **Step 7: 提交**

```bash
cd <仓库根目录> && git add tools/tice_bundle.js tools/tice_build_json.js web-next/tice-standard.json tools/test_field_ui.py && git commit -q -m "feat(tice): 从传承数据模块派生 tice-standard.json"
```

---

## Task 2: 数据不变量测试 tools/test_tice.py

先把「这份 JSON 是不是自洽」钉成测试，再动算分。探针必须能真的让检查变红。

**Files:**
- Create: `tools/test_tice.py`

**Interfaces:**
- Consumes: `web-next/tice-standard.json`
- Produces: `check_slot_count(events)` / `check_monotonic(events)` / `check_null_layout(events)` 三个可传参函数，正式测试与探针共用

- [ ] **Step 1: 写测试**

Create `tools/test_tice.py`：

```python
"""体测评分表 JSON 的数据不变量与文件契约。见 spec §12。"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web-next" / "tice-standard.json"
STD = json.loads(DATA.read_text(encoding="utf-8"))
GROUPS = ("grade12", "grade34")
WANT_LADDER = [100, 95, 90, 85, 80, 78, 76, 74, 72, 70, 68, 66, 64, 62, 60, 50, 40, 30, 20, 10]
WANT_NULLS = {("pullUps", "male", "grade12"): [5, 7, 9, 11, 13],
              ("pullUps", "male", "grade34"): [5, 7, 9, 11, 13]}


def tables(events):
    for ev, d in events.items():
        for g in d["genders"]:
            for grp in GROUPS:
                yield ev, g, grp, d["thresholds"][g][grp]


def check_slot_count(events):
    bad = [(e, g, gr, len(t)) for e, g, gr, t in tables(events) if len(t) != 20]
    assert not bad, f"槽位数不是 20：{bad}"


def check_null_layout(events):
    found, total = {}, 0
    for e, g, gr, t in tables(events):
        ix = [i for i, v in enumerate(t) if v is None]
        total += len(t)
        if ix:
            found[(e, g, gr)] = ix
    assert found == WANT_NULLS, f"null 位置不符：{found}"
    assert total == 480, f"总槽位 {total} != 480"
    nums = sum(1 for _, _, _, t in tables(events) for v in t if v is not None)
    assert nums == 470, f"非空阈值 {nums} != 470"


def _as_number(x):
    if isinstance(x, str) and "'" in x:
        m = re.match(r"(\d+)'(\d+)\"", x)
        return int(m.group(1)) * 60 + int(m.group(2))
    return float(x)


def check_monotonic(events):
    for ev, d in events.items():
        assert d["direction"] in ("higher_is_better", "lower_is_better"), \
            f"{ev} 的 direction 是 {d['direction']!r}，不在契约两值内"
        asc = d["direction"] == "lower_is_better"
        for e, g, gr, t in tables(events):
            if e != ev:
                continue
            v = [_as_number(x) for x in t if x is not None]
            got = sorted(v) if asc else sorted(v, reverse=True)
            assert v == got, f"{ev}/{g}/{gr} 阈值不单调：{v}"


class LadderTest(unittest.TestCase):
    def test_score_ladder_is_the_20_official_steps(self):
        self.assertEqual([x["score"] for x in STD["scoreLadder"]], WANT_LADDER)

    def test_levels_map_to_the_four_bands(self):
        by = {x["score"]: x["level"] for x in STD["scoreLadder"]}
        for s, want in [(100, "优秀"), (95, "优秀"), (90, "优秀"), (85, "良好"), (80, "良好"),
                        (78, "及格"), (60, "及格"), (50, "不及格"), (10, "不及格")]:
            self.assertEqual(by[s], want, f"{s} 分档等级错")

    def test_limits_are_the_official_four(self):
        self.assertEqual(STD["limits"], {"maxStandardScore": 100, "maxSingleBonusScore": 10,
                                        "maxTotalBonusScore": 20, "maxTotalScore": 120})

    def test_weights_sum_to_hundred_per_gender(self):
        w = STD["weights"]
        self.assertEqual(sum(w.values()), 130, "男女并集 9 键：15+15+20+10+10+10+20 两遍")
        male = ["bmi", "vitalCapacity", "sprint50m", "sitAndReach", "standingLongJump",
                "pullUps", "run1000m"]
        female = ["bmi", "vitalCapacity", "sprint50m", "sitAndReach", "standingLongJump",
                  "sitUps", "run800m"]
        self.assertEqual(sum(w[k] for k in male), 100)
        self.assertEqual(sum(w[k] for k in female), 100)
        self.assertEqual(w, {"bmi": 15, "vitalCapacity": 15, "sprint50m": 20,
                             "sitAndReach": 10, "standingLongJump": 10, "pullUps": 10,
                             "sitUps": 10, "run800m": 20, "run1000m": 20})


class ThresholdTest(unittest.TestCase):
    def test_slot_count(self):
        check_slot_count(STD["events"])

    def test_null_layout_and_totals(self):
        check_null_layout(STD["events"])

    def test_monotonic(self):
        check_monotonic(STD["events"])

    def test_gender_specific_events_have_one_gender_only(self):
        self.assertEqual(STD["events"]["pullUps"]["genders"], ["male"])
        self.assertEqual(STD["events"]["run1000m"]["genders"], ["male"])
        self.assertEqual(STD["events"]["sitUps"]["genders"], ["female"])
        self.assertEqual(STD["events"]["run800m"]["genders"], ["female"])

    def test_unit_type_and_grade_map_are_the_contract_keys(self):
        # 这两键是 Task 1 复核补回来的（unitType 曾被 JSON.stringify 静默丢掉、
        # gradeToGroup 曾是 freshman/… 英文键）。下游按它们解单位与年级，必须钉住。
        self.assertEqual({k: v["unitType"] for k, v in STD["events"].items()},
                         {"vitalCapacity": "number", "sprint50m": "number", "sitAndReach": "number",
                          "standingLongJump": "number", "pullUps": "number", "sitUps": "number",
                          "run1000m": "mmss", "run800m": "mmss"})
        self.assertEqual(STD["gradeToGroup"],
                         {"大一": "grade12", "大二": "grade12", "大三": "grade34", "大四": "grade34"})

    def test_bonus_is_only_strength_and_endurance(self):
        self.assertEqual(sorted(k for k, v in STD["events"].items() if v["bonusEligible"]),
                         ["pullUps", "run1000m", "run800m", "sitUps"])

    def test_bonus_tables_descend_ten_to_one(self):
        for k, v in STD["events"].items():
            if v["bonusDeltas"]:
                self.assertEqual([t["bonusScore"] for t in v["bonusDeltas"]], list(range(10, 0, -1)), k)

    def test_strength_and_endurance_delta_ranges(self):
        self.assertEqual([t["delta"] for t in STD["events"]["pullUps"]["bonusDeltas"]],
                         list(range(10, 0, -1)))
        self.assertEqual([t["delta"] for t in STD["events"]["sitUps"]["bonusDeltas"]],
                         [13, 12, 11, 10, 9, 8, 7, 6, 4, 2])
        self.assertEqual([t["reductionSeconds"] for t in STD["events"]["run1000m"]["bonusDeltas"]],
                         [35, 32, 29, 26, 23, 20, 16, 12, 8, 4])
        self.assertEqual([t["reductionSeconds"] for t in STD["events"]["run800m"]["bonusDeltas"]],
                         [50, 45, 40, 35, 30, 25, 20, 15, 10, 5])


class BmiTest(unittest.TestCase):
    def test_four_categories_both_genders(self):
        for g in ("male", "female"):
            self.assertEqual(len(STD["bmi"]["categoriesByGender"][g]), 4, g)

    def test_categories_do_not_leave_gaps_on_scaled_scale(self):
        # 低体重下界与肥胖上界是开区间，落盘为 None；直接 sorted(…, reverse=True) 会
        # TypeError: '<' not supported between NoneType and int，所以按升序 + None 占位排序。
        for g in ("male", "female"):
            segs = sorted([(c["scaledMinInclusive"], c["scaledMaxInclusive"])
                           for c in STD["bmi"]["categoriesByGender"][g]],
                          key=lambda s: float("-inf") if s[0] is None else s[0])
            for lo, hi in zip(segs, segs[1:]):
                self.assertIsNotNone(lo[1], f"{g} 非最高档区间缺上界：{lo} {hi}")
                self.assertEqual(hi[0], lo[1] + 1, f"{g} 相邻 BMI 区间没接上：{lo} {hi}")
            # 三条内缝接上不等于整把刻度被铺满：两端必须是开区间，否则最低端/最高端留了洞
            self.assertIsNone(segs[0][0], f"{g} 低体重下界不是开区间：{segs[0]}")
            self.assertIsNone(segs[-1][1], f"{g} 肥胖上界不是开区间：{segs[-1]}")

    def test_bmi_scores_are_the_official_four(self):
        for g in ("male", "female"):
            self.assertEqual({c["category"]: c["score"] for c in STD["bmi"]["categoriesByGender"][g]},
                             {"normal": 100, "underweight": 80, "overweight": 80, "obese": 60})


class MetaTest(unittest.TestCase):
    def test_provenance_fields_are_present_and_verbatim(self):
        m = STD["meta"]
        for k in ("standardName", "standardDocNo", "schoolPolicyName", "schoolPolicyDocNo",
                  "policyEffectiveScope", "verifiedDate", "sourceSha256"):
            self.assertTrue(m.get(k), f"meta 缺 {k}")
        self.assertEqual(m["standardDocNo"], "教体艺〔2014〕5号")
        self.assertIn("2024级本科生起施行", m["policyEffectiveScope"])

    def test_three_unresolved_rules_are_kept(self):
        self.assertEqual(sorted(STD["unresolvedRules"]),
                         ["bmi_boundary_precision_unresolved",
                          "cuc_2024_policy_multi_year_scope_unresolved",
                          "measurement_precision_rounding_unresolved"])


class FileContractTest(unittest.TestCase):
    def test_css_has_no_raw_colors(self):
        css_path = ROOT / "web-next" / "tice.css"
        if not css_path.exists():
            # 本任务先于页面存在。让整套门保持绿：任何一条红都是真消息，
            # 而不是「反正有一条是预置的红」被顺手放过。Task 8 建出文件后这条自动生效。
            self.skipTest("web-next/tice.css 由 Task 8 创建")
        css = css_path.read_text(encoding="utf-8")
        bad = re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", css)
        self.assertFalse(bad, f"tice.css 出现裸色值：{bad[:5]}")

    def test_no_other_file_embeds_thresholds(self):
        # 不外调 grep：硬门不该依赖 PATH 上有哪个二进制，且 grep 无命中时 rc=1、
        # stdout 为空，原写法会把「没查到」报成「内嵌在 []」这种看不懂的失败信息。
        for probe in ("5040", "4920", "4550", "2300", "3030"):
            hits = [p.name for p in sorted((ROOT / "web-next").rglob("*"))
                    if p.is_file() and probe in p.read_text(encoding="utf-8", errors="ignore")]
            self.assertEqual(hits, ["tice-standard.json"],
                             f"特征值 {probe} 应只出现在 tice-standard.json，实得 {hits}")


class ProbeTest(unittest.TestCase):
    """假阳性检查：三项检查必须真的能红。用被改坏的副本喂同一个函数，不许比文件差异冒充。"""

    def setUp(self):
        self.ev = json.loads(json.dumps(STD["events"]))

    def test_disorder_injection_is_caught(self):
        self.ev["vitalCapacity"]["thresholds"]["male"]["grade12"][3] = 9999
        with self.assertRaises(AssertionError) as ctx:
            check_monotonic(self.ev)
        self.assertIn("vitalCapacity", str(ctx.exception))

    def test_missing_slot_is_caught(self):
        self.ev["sitAndReach"]["thresholds"]["female"]["grade12"].pop()
        with self.assertRaises(AssertionError):
            check_slot_count(self.ev)

    def test_extra_null_in_wrong_place_is_caught(self):
        self.ev["standingLongJump"]["thresholds"]["male"]["grade12"][6] = None
        with self.assertRaises(AssertionError):
            check_null_layout(self.ev)

    def test_untouched_copy_passes_all_three(self):
        check_slot_count(STD["events"])
        check_null_layout(STD["events"])
        check_monotonic(STD["events"])
```

- [ ] **Step 2: 跑测试，确认只因缺 CSS 而失败**

Run: `cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_tice*.py" -v 2>&1 | tail -6`
Expected: `FileContractTest.test_css_has_no_raw_colors` 因 `web-next/tice.css` 尚不存在而 **SKIP**（`skipTest("web-next/tice.css 由 Task 8 创建")`），整套门仍是绿；其余全 PASS——包括 `test_no_other_file_embeds_thresholds`，因为此时 web-next 里除了 `tice-standard.json` 没有别的新文件。Task 8 建出 `tice.css` 后那条 skip 自动变成真断言。**不许把这条门做成「预置的一条红」**：套件退出码分不清「预置的那条红」和「预置红＋新坏的一条不变量」，一旦养成放过红的习惯，后面 10 个任务就没人看得住真损坏了。

- [ ] **Step 3: 确认探针不是空过**

Run: `cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest tools.test_tice.ProbeTest -v 2>&1 | tail -6`
Expected: 4 项全 PASS。若前三项有任何一条 FAIL，说明检查函数写得松，先修检查而不是删探针。

- [ ] **Step 4: 提交**

```bash
cd <仓库根目录> && git add tools/test_tice.py && git commit -q -m "test(tice): 评分表数据不变量、来源字段与假阳性探针"
```

---

## Task 3: 算分内核——单项得分（含空档跳过与分秒解析）

**Files:**
- Create: `web-next/tice-calc.js`
- Test: `tools/test_tice_calc.js`

**Interfaces:**
- Consumes: `web-next/tice-standard.json`
- Produces: `prepareStandard`, `gradeGroupOf`, `eventKeysFor`, `parseEnduranceTime`, `formatEnduranceTime`, `scaleOf`, `scoreLevel`, `scoreEvent`（本任务先只支持非 BMI 事件，Task 4 扩 BMI 与 unresolved）

- [ ] **Step 1: 写失败测试**

Create `tools/test_tice_calc.js`。每条期望值都由「实测基准」推出来，不是拍的：

```js
const assert = require('assert');
const fs = require('fs');
const calc = require('../web-next/tice-calc.js');
const std = calc.prepareStandard(
  JSON.parse(fs.readFileSync('web-next/tice-standard.json', 'utf8')));

// 男 grade12 阈值：肺活量 5040..2300 / 50米 6.7.. / 坐位体前屈 24.9..-1.3 /
// 立定跳远 273.. / 引体向上 19 18 17 16 15 null 14 null 13 null 12 … / 1000米 3'17"…
const cases = [
  ['vitalCapacity',  'male',   '大一', 5040,      'scored', 100],
  ['vitalCapacity',  'male',   '大一', 2300,      'scored', 10],
  ['vitalCapacity',  'male',   '大一', 4000,      'scored', 74],   // 4060(76) 与 3940(74) 取低档
  ['sprint50m',      'male',   '大一', '6.9',     'scored', 90],
  ['sprint50m',      'male',   '大一', '7.0',     'scored', 85],
  ['sprint50m',      'female', '大三', '7.4',     'scored', 100],
  ['sitAndReach',    'male',   '大一', '-1.3',    'scored', 10],
  ['standingLongJump','male',  '大二', 273,       'scored', 100],
  ['standingLongJump','male',  '大二', 250,       'scored', 80],   // 256(85) 与 248(80) 取低
  ['pullUps',        'male',   '大一', 14,        'scored', 76],   // 78 档为 null，跳过
  ['pullUps',        'male',   '大一', 12,        'scored', 68],   // 74/70/66 档 null，跳到 68
  ['run1000m',       'male',   '大一', "3'17\"",  'scored', 100],
  ['run800m',        'female', '大二', "3'18\"",  'scored', 100],
  // 降序方向也要有「落两档之间取低档」的用例：上面 5 条 50米/长跑全部精确压档，
  // 有人只在下侧分支加插值或把取档方向搞反，13 条会全绿。
  ['sprint50m',      'male',   '大一', '7.2',     'scored', 78],   // 7.1(80) 与 7.3(78) 之间取低
  ['run1000m',       'male',   '大一', "3'40\"",  'scored', 80],   // 214"（85）与 222"（80）之间取低
];

let fail = 0;
for (const [ev, g, grade, raw, wantStatus, wantScore] of cases) {
  const r = calc.scoreEvent(std, { gender: g, grade, eventKey: ev, raw });
  try {
    assert.strictEqual(r.status, 'complete', `status=${r.status}`);
    assert.strictEqual(r.levelResult.status, wantStatus);
    assert.strictEqual(r.score, wantScore, `score=${r.score} 期望 ${wantScore}`);
  } catch (e) { console.log('FAIL', ev, g, grade, raw, e.message); fail += 1; }
}
console.log(fail ? `${fail}/${cases.length} 失败` : `all ${cases.length} pass`);

// spec §12 点名要的边界，钉成断言而不是只 print 一遍。
// 回源更正（2026-11-09）：`'210'` 是**接受**的，等于 210 总秒。原程序 parseEnduranceTime
// 实测接受 '210' / '210秒' / '197s' / '3:7' 这些形态，并把小数时间单独拒成
// ambiguous_decimal_time_format（它的模块注释就是「严禁将 3.17 等小数误认为分秒」）。
// 早先那条「拒绝裸秒串」是凭提示文案反推的，与实测不符，已撤销。
assert.deepStrictEqual(calc.parseEnduranceTime('4:20'), { ok: true, seconds: 260 });
assert.deepStrictEqual(calc.parseEnduranceTime('4:7'),  { ok: true, seconds: 247 });
assert.deepStrictEqual(calc.parseEnduranceTime('4:60'), { ok: false, code: 'invalid_minutes_or_seconds_range' });
assert.deepStrictEqual(calc.parseEnduranceTime('0:00'), { ok: false, code: 'non_positive_time' });
assert.deepStrictEqual(calc.parseEnduranceTime('4.20'), { ok: false, code: 'ambiguous_decimal_time_format' });
assert.deepStrictEqual(calc.parseEnduranceTime(210),    { ok: true, seconds: 210 });
assert.deepStrictEqual(calc.parseEnduranceTime('210'),  { ok: true, seconds: 210 });
assert.deepStrictEqual(calc.parseEnduranceTime('210秒'), { ok: true, seconds: 210 });
assert.deepStrictEqual(calc.parseEnduranceTime('197s'), { ok: true, seconds: 197 });
assert.deepStrictEqual(calc.parseEnduranceTime('3\'17"'), { ok: true, seconds: 197 });
// `3'99"` 是输入框能打出来的东西，正则只锁位数不锁值域；不补这一句，
// 它会安静地算成 279 秒（4'39"），而 `99:99` 那条路是拒的——两路宽严必须一致。
assert.deepStrictEqual(calc.parseEnduranceTime('3\'99"'), { ok: false, code: 'invalid_minutes_or_seconds_range' });
assert.strictEqual(calc.formatEnduranceTime(197), '3\'17"');
assert.strictEqual(calc.formatEnduranceTime(247), '4\'07"');
assert.strictEqual(calc.formatEnduranceTime(0), null);

// -0.0 与 0 必须同档：Math.round(-0) 是 -0，比较不应出现分叉。
// 只比判定结果，别 deepStrictEqual 整个返回体——里面的 scaledValue 是 -0 vs 0，
// deepStrictEqual 按 Object.is 判，会把这对本来相等的值判成不等。
const negZero = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'sitAndReach', raw: '-0.0' });
const zero    = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'sitAndReach', raw: '0' });
assert.strictEqual(negZero.status, zero.status);
assert.strictEqual(negZero.score, zero.score);
assert.strictEqual(negZero.levelResult.level, zero.levelResult.level);

// 长跑档位的 rawDisplay 必须是分秒字面量。结果卡与历史文本直接渲染它，
// 落成总秒数 197 就会在页面上显示「197 → 100 分」。
assert.strictEqual(calc.scoreEvent(std, {
  gender: 'male', grade: '大一', eventKey: 'run1000m', raw: "3'17\"",
}).levelResult.rawDisplay, '3\'17"');

// 两条硬约束各有自己的下游依赖，不钉就等于没写：
// (1) 空输入必须是 incomplete——Task 5 的 assemble 靠它数 filled.length，
//     删掉 isBlank 分支会退化成「0 → invalid」，13 条用例一条不红。
// (2) 性别不匹配必须抛错、不许静默回退——把 throw 换成「回退到 byGroup 里第一个性别」，
//     就是拿男表给女生算引体向上，这类计算器最常见的错分。
assert.strictEqual(calc.scoreEvent(std, {
  gender: 'male', grade: '大一', eventKey: 'vitalCapacity', raw: '',
}).status, 'incomplete');
assert.throws(() => calc.scoreEvent(std, {
  gender: 'female', grade: '大一', eventKey: 'pullUps', raw: 8,
}), /性别不匹配/);
// 未知项目名要给可读的错误，不是裸 TypeError
assert.throws(() => calc.scoreEvent(std, {
  gender: 'male', grade: '大一', eventKey: 'noSuchEvent', raw: 1,
}), /未知项目/);

// 取位模式本身要钉住：Math.round 换成 floor/trunc 时上面所有用例仍全绿
// （6.72 与 6.75 的 67/68 之差正是 Task 4 判跨档的支点）。
assert.strictEqual(calc.scaleOf(6.75, 10), 68);
assert.strictEqual(calc.scaleOf(6.72, 10), 67);
console.log('边界断言全部通过');
process.exit(fail ? 1 : 0);
```

- [ ] **Step 2: 跑到失败**

Run: `cd <仓库根目录> && node tools/test_tice_calc.js`
Expected: `Cannot find module '../web-next/tice-calc.js'`。

- [ ] **Step 3: 写实现**

Create `web-next/tice-calc.js`：

```js
// 体测算分内核：纯函数，不碰 DOM，不碰存储，不用浮点比阈值。
// 规则与传承实现一致：20 档离散匹配，无插值；空档跳过，拿不准就不给分。
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.TICE_CALC = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const MMSS = /^(\d+)'(\d{2})"$/;

  function parseEnduranceTime(raw) {
    if (typeof raw === 'number' && Number.isSafeInteger(raw) && raw > 0) return { ok: true, seconds: raw };
    const s = String(raw == null ? '' : raw).trim();
    const m = /^(\d+):(\d{1,2})$/.exec(s);              // 页面输入形如 4:20
    if (m) {
      const min = Number(m[1]), sec = Number(m[2]);
      if (sec > 59) return { ok: false, code: 'invalid_minutes_or_seconds_range' };
      if (min * 60 + sec <= 0) return { ok: false, code: 'non_positive_time' };
      return { ok: true, seconds: min * 60 + sec };
    }
    if (MMSS.test(s)) {                                  // 表内字面量 3'17"
      const r = MMSS.exec(s);
      if (Number(r[2]) > 59) return { ok: false, code: 'invalid_minutes_or_seconds_range' };
      return { ok: true, seconds: Number(r[1]) * 60 + Number(r[2]) };
    }
    if (/^\d+[.,]\d+$/.test(s)) return { ok: false, code: 'ambiguous_decimal_time_format' };
    return { ok: false, code: 'invalid_minutes_or_seconds_range' };
  }

  function formatEnduranceTime(total) {
    if (typeof total !== 'number' || !Number.isSafeInteger(total) || total <= 0) return null;
    return `${Math.floor(total / 60)}'${String(total % 60).padStart(2, '0')}"`;
  }

  function scaleOf(value, scale) {
    if (typeof value !== 'number' || !Number.isFinite(value)) return null;
    return Math.round(value * (scale || 1));
  }

  function buildLevels(scoreLadder, rawRow, unitType, scale) {
    const all = scoreLadder.map((row, i) => {
      const t = rawRow[i];
      if (t === null || t === undefined) {
        return { score: row.score, level: row.level, threshold: null,
                 scaledThreshold: null, rawDisplay: null };
      }
      if (unitType === 'mmss') {
        const sec = parseEnduranceTime(t).seconds;
        return { score: row.score, level: row.level, threshold: sec,
                 scaledThreshold: sec, rawDisplay: formatEnduranceTime(sec) };
      }
      const num = Number(t);
      return { score: row.score, level: row.level, threshold: num,
               scaledThreshold: scaleOf(num, scale), rawDisplay: String(t) };
    });
    return { levels: all.filter((r) => r.threshold !== null),
             unpopulatedScores: all.filter((r) => r.threshold === null).map((r) => r.score),
             rawTableRows: all };
  }

  function buildBonusTable(e, levels) {
    const top = levels.find((l) => l.score === 100);
    if (!top) return [];
    return e.bonusDeltas.map((d) => {
      const abs = e.direction === 'higher_is_better'
        ? top.scaledThreshold + d.delta
        : top.scaledThreshold - d.reductionSeconds;
      return { bonusScore: d.bonusScore,
               scaledAbsoluteThreshold: abs,
               rawAbsoluteDisplay: e.unitType === 'mmss' ? formatEnduranceTime(abs) : String(abs) };
    });
  }

  function prepareStandard(json) {
    const events = {};
    Object.keys(json.events).forEach((key) => {
      const e = json.events[key];
      const byGroup = {};
      Object.keys(e.thresholds).forEach((gender) => {
        byGroup[gender] = {};
        Object.keys(e.thresholds[gender]).forEach((group) => {
          const built = buildLevels(json.scoreLadder, e.thresholds[gender][group],
                                   e.unitType, e.scale);
          built.bonusTable = e.bonusEligible ? buildBonusTable(e, built.levels) : [];
          byGroup[gender][group] = built;
        });
      });
      events[key] = Object.assign({}, e, { byGroup });
    });
    return { limits: json.limits, weights: json.weights, gradeToGroup: json.gradeToGroup,
             gradeGroups: json.gradeGroups, events, bmi: json.bmi,
             unresolvedRules: json.unresolvedRules, meta: json.meta };
  }

  function gradeGroupOf(std, grade) {
    const g = std.gradeToGroup[grade];
    if (!g) throw new Error('未知年级: ' + grade);
    return g;
  }

  function eventKeysFor(std, gender) {
    const base = ['bmi', 'vitalCapacity', 'sprint50m', 'sitAndReach', 'standingLongJump'];
    return base.concat(gender === 'male' ? ['pullUps', 'run1000m'] : ['sitUps', 'run800m']);
  }

  function matchLevel(levels, direction, scaled) {
    for (const l of levels) {
      if (direction === 'higher_is_better' ? scaled >= l.scaledThreshold
                                           : scaled <= l.scaledThreshold) return l;
    }
    return null;
  }

  function scoreLevel(std, evKey, gender, group, scaled) {
    const ev = std.events[evKey];
    if (!ev || ev.genders.indexOf(gender) < 0) {
      throw new Error(`性别不匹配: ${evKey} 只存 ${ev ? ev.genders.join('/') : '?'}`);
    }
    const built = ev.byGroup[gender][group];
    const hit = matchLevel(built.levels, ev.direction, scaled);
    if (!hit) {
      // 回源更正：低于最低档不是 invalid，是 0 分。原程序 status:'complete'/score:0/level:'不及格'。
      return { status: 'scored', score: 0, level: failLevel(std),
               matchedThreshold: null, rawDisplay: null, reason: null };
    }
    return { status: 'scored', score: hit.score, level: hit.level,
             matchedThreshold: hit.threshold, rawDisplay: hit.rawDisplay, reason: null };
  }

  function toScaled(std, evKey, gender, group, raw) {
    const ev = std.events[evKey];
    if (ev.unitType === 'mmss') {
      const t = parseEnduranceTime(raw);
      return t.ok ? { scaled: t.seconds } : { error: t.code };
    }
    const num = typeof raw === 'number' ? raw : Number(String(raw == null ? '' : raw).trim());
    const scaled = scaleOf(num, ev.scale);
    return scaled === null ? { error: 'not_a_number' } : { scaled };
  }

  function isBlank(v) {
    return v === undefined || v === null || String(v).trim() === '';
  }

  // 本任务只算非 BMI 五项 + 力量 + 长跑；BMI 在 Task 4 接进来
  function scoreEvent(std, input) {
    const group = gradeGroupOf(std, input.grade);
    const evKey = input.eventKey;
    const ev = std.events[evKey];
    if (evKey === 'bmi') {
      const blank = isBlank(input.inputs.heightCm) || isBlank(input.inputs.weightKg);
      return { eventKey: evKey, name: '体重指数（BMI）', status: blank ? 'incomplete' : 'unresolved',
               levelResult: null, score: null, weightedContribution: null, bonusScore: 0 };
    }
    // 守卫必须在 BMI 之后：BMI 不在 std.events 里（它在顶层 std.bmi），
    // 放在前面会让 BMI 分支先撞成「未知项目」。放在这里是让 ev 之后所有
    // `ev.name` / `ev.unitType` 取值都不用再判空。
    if (!ev) throw new Error('未知项目: ' + evKey);
    if (isBlank(input.raw)) {
      return { eventKey: evKey, name: ev.name, status: 'incomplete',
               levelResult: null, score: null, weightPercent: ev.weightPercent,
               weightedContribution: null, bonusEligible: ev.bonusEligible, bonusScore: 0, hint: null };
    }
    const conv = toScaled(std, evKey, input.gender, group, input.raw);
    if (conv.error) {
      return { eventKey: evKey, name: std.events[evKey].name, status: 'invalid',
               levelResult: { status: 'invalid', score: null, level: null,
                              matchedThreshold: null, rawDisplay: null, reason: conv.error },
               score: null, weightedContribution: null, bonusScore: 0, hint: null, code: conv.error };
    }
    const lr = scoreLevel(std, evKey, input.gender, group, conv.scaled);
    const complete = lr.status === 'scored';
    return {
      eventKey: evKey, name: std.events[evKey].name,
      status: complete ? 'complete' : (lr.status === 'unresolved' ? 'unresolved' : 'invalid'),
      levelResult: lr, score: lr.score,
      weightPercent: std.events[evKey].weightPercent,
      weightedContribution: complete ? Math.round(lr.score * std.events[evKey].weightPercent) / 100 : null,
      bonusEligible: std.events[evKey].bonusEligible, bonusScore: 0, hint: null,
      scaledValue: conv.scaled,
    };
  }

  return { prepareStandard, gradeGroupOf, eventKeysFor, parseEnduranceTime, formatEnduranceTime,
           scaleOf, scoreLevel, scoreEvent, matchLevel, buildLevels, buildBonusTable, toScaled };
}));
```

- [ ] **Step 4: 跑到通过**

Run: `cd <仓库根目录> && node tools/test_tice_calc.js`
Expected: `all 15 pass` + `边界断言全部通过`，退出码 0。第 3、9、10、11 条是本任务的意义：不插值、空档跳过、不编分。若第 10 条得 78，说明 `levels` 没把 null 槽剔掉。第 14、15 条钉住降序侧的取低档。

再跑 Global Constraint 9 的两段 Python 门（Constraint 13：只用了两个窄 pattern，别用 `test_*.py`）：

```bash
cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_tice*.py" 2>&1 | tail -4
cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_field*.py" 2>&1 | tail -4
```

Expected: `Ran 23 tests` / `OK (skipped=1)` 与 `Ran 136 tests` / `OK`。第一条的 skip 是 css 裸色值门，Task 8 才自退休。若 `test_field*.py` 报 `test_only_the_expected_files_were_added` 红，是 Step 5 的白名单还没加——按 Constraint 12 加自己这一个名字，不许加别人的文件。

- [ ] **Step 5: 白名单与提交**

本任务新建了 `web-next/tice-calc.js`，按 Global Constraint 12 必须在**同一次提交**里把它加进 `tools/test_field_ui.py:1462` 的 `expected`，只加这一个名字：

```python
        expected = {f"field.{ext}" for ext in ("html", "css", "js")} | {EMBLEM} | {"tice-standard.json", "tice-calc.js"}
```

（该行现有内容以文件实况为准，只在集合末尾追加 `"tice-calc.js"`，不要重写整行的其余部分。）

```bash
cd <仓库根目录> && git add web-next/tice-calc.js tools/test_tice_calc.js tools/test_field_ui.py && git -c user.name=campus-guide -c user.email=noreply@local commit -q -m "feat(tice): 单项离散档算分，空档跳过与分秒解析"
```

---

## Task 4: BMI 分类与两类 unresolved

**Files:**
- Modify: `web-next/tice-calc.js`（`bmiOf`、`scoreBmi`、`scoreEvent` 接 BMI 与精度跨档）
- Test: `tools/test_tice_calc.js`

**Interfaces:**
- Consumes: `std.bmi.categoriesByGender`、`std.bmi.unresolvedGapsByGender`、`std.unresolvedRules`
- Produces: `bmiOf(heightCm, weightKg)`、`scoreBmi(std, gender, scaled)`，并让 `scoreEvent` 支持 `eventKey:'bmi'` 与 `inputs`

- [ ] **Step 1: 先把空隙数据的真实形状读出来**

Run:
```bash
cd <仓库根目录> && "./.venv/Scripts/python.exe" -c "
import json;S=json.load(open('web-next/tice-standard.json',encoding='utf-8'))
print('gaps male  ', S['bmi']['unresolvedGapsByGender']['male'])
print('gaps female', S['bmi']['unresolvedGapsByGender']['female'])
print('cats male  ', [(c['category'],c['scaledMinInclusive'],c['scaledMaxInclusive']) for c in S['bmi']['categoriesByGender']['male']])"
```
Expected: 男生四类区间的 scaled 边界是 `正常179–239 / 超重240–279 / 肥胖≥280 / 低体重≤178`——整数刻度上首尾相接，**没有缝**。缝在第三位小数：真实 BMI 常常不是 0.1 的整数倍，例如 23.95、17.85、27.95 既不属于本档也不属于邻档，他包把这类值记成空隙。

所以本任务的判定规则定死为（实现照此写，不留待观察）：

1. **不取位。** 把 `bmi = weightKg / (heightCm/100)²` 与 17.8 / 17.9 / 24.0 / 27.9 / 28.0 这些**一位小数门槛**做精确整数比较（见下面 `bmiCompareTenths`），全程不经浮点、不四舍五入、不截断。
2. 落在四类区间内的正常给分；**落进相邻区间之间的开缝**（男 (17.8,17.9) / (23.9,24.0) / (27.9,28.0)，女 (17.1,17.2) / (23.9,24.0) / (27.9,28.0)）**返回 unresolved**，理由 `bmi_boundary_precision_unresolved`。
3. 于是 `20.05` 落在 17.9~23.9 之内 → 正常 100；`17.86` 落在 (17.8,17.9) 之内 → unresolved。**这两个方向都必须成立**——既不许把档内无歧义的值拒掉，也不许替用户挑一种取位方式硬给分。

> 回源更正（2026-11-09）：本节早先写的是「`hundredths % 10 === 5` 才 unresolved、否则 `Math.floor` 取位」，对照解包产物 `utils/fitness-calculator.js` 的实测是**双向失真**——它把 20.05、22.95 这类档内值误拒（每人 260 个，约 1/10 的 BMI 输入拿不到分），又把 17.86、23.96 这类真歧义值按截断硬给成错档（每人 24 个）。原程序是拿真值与门槛直接比的，代码见下。用户已裁定按原程序对齐。

用例固定用 `heightCm = 100`，此时 `BMI = weightKg`，能精确落到位上，不引入额外舍入噪声。男生空隙输入即 `weightKg = 23.95`、`17.85`、`27.95`；贴边的 `17.8` / `17.9` 属于闭区间端点，必须给分。Step 1 打印的 `unresolvedGaps` 用来验证规则覆盖的值与他记录的一致——两者本应是同一组缝，不一致就是数据或判据有一边错了。

- [ ] **Step 2: 追加失败测试**

在 `tools/test_tice_calc.js` 的 `process.exit` 之前插入：

```js
const bmiCases = [
  ['male',   175, 65.5, 'scored', 100, '正常'],
  ['male',   175, 50.0, 'scored', 80,  '低体重'],
  ['male',   175, 85.0, 'scored', 80,  '超重'],
  ['male',   175, 95.0, 'scored', 60,  '肥胖'],
  ['female', 160, 47.0, 'scored', 100, '正常'],
];
let bf = 0;
for (const [g, h, w, wantStatus, wantScore, wantLevel] of bmiCases) {
  const r = calc.scoreEvent(std, { gender: g, grade: '大一', eventKey: 'bmi',
                                   inputs: { heightCm: h, weightKg: w } });
  if (r.levelResult.status !== wantStatus || r.score !== wantScore
      || r.levelResult.level !== wantLevel) {
    console.log('FAIL bmi', g, h, w, JSON.stringify(r.levelResult), r.score); bf += 1;
  }
}

// 空隙：BMI 恰为 23.95，落在正常(≤23.9)与超重(≥24.0)之间的 0.05 处
const gapM = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'bmi',
                                    inputs: { heightCm: 100, weightKg: 23.95 } });
assert.strictEqual(gapM.status, 'unresolved', '男生空隙应 unresolved，实际 ' + gapM.status);
assert.strictEqual(gapM.levelResult.reason, 'bmi_boundary_precision_unresolved');
const gapF = calc.scoreEvent(std, { gender: 'female', grade: '大二', eventKey: 'bmi',
                                    inputs: { heightCm: 100, weightKg: 17.15 } });
assert.strictEqual(gapF.status, 'unresolved', '女生空隙应 unresolved，实际 ' + gapF.status);

// 取位跨档：50米 male grade12 前四档 6.7(100) / 6.8(95) / 6.9(90) / 7.0(85)
// 6.75 的两位小数码在 67 与 68 之间，向下取位 100、向上取位 95 → 无法唯一确定
const cross = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'sprint50m',
                                     raw: '6.75' });
assert.strictEqual(cross.status, 'unresolved', '取位跨档应 unresolved，实际 ' + cross.status);
assert.strictEqual(cross.levelResult.reason, 'measurement_precision_rounding_unresolved');
// 6.72 两位取位后同为 67 档（6.7），不跨档 → 照常给分，证明上面那条不是滥判
const same = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'sprint50m',
                                    raw: '6.72' });
assert.strictEqual(same.status, 'complete', '不跨档却被拦了：' + same.status);
assert.strictEqual(same.score, 100);
console.log(bf ? `bmi ${bf} 条失败` : `bmi ${bmiCases.length} pass + 空隙2 + 跨档2`);
if (bf) process.exit(1);
```

`17.15` 来自女生低体重上界 `≤17.1`、正常下界 `17.2`（Task 1 Step 5 打印的 `cats` 若与他数据不符，按他的实际邻界中点替换这两条的输入值，规则不变）。

- [ ] **Step 3: 写实现**

在 `tice-calc.js` 工厂内加，并把 `scoreEvent` 的 BMI 分支替掉 Task 3 那个占位返回：

```js
  // ── 精确十进制（回源更正 2026-11-09）：输入与门槛都在整数域比，绝不经过浮点 ──
  // 原程序的做法：parseDecimal → {scaledBigInt, decimalPlaces}，阈值比较全在 BigInt 上，
  // toFixed(1) 只用于显示。我们照这个纪律来，不引入任何「先取位再比」的中间态。
  function pow10Big(n) { let r = 1n; for (let i = 0; i < n; i += 1) r *= 10n; return r; }

  function bmiOf(heightCm, weightKg) {
    if (!(heightCm > 0) || !(weightKg > 0)) return null;
    return weightKg / Math.pow(heightCm / 100, 2);   // 只给显示用，判定不读它
  }

  // BMI 不取位：bmi ⋚ T/10 ⟺ 100000·W ⋚ T·H²（H、W 都是定标整数）
  // 推导：bmi = W·10000/H²，与 T/10 比 ⟺ 10·10000·W ⋚ T·H²；H=sh/10^dh、W=sw/10^dw 通分即得。
  function bmiCompareTenths(h, w, tenths) {
    const L = 100000n * w.scaledBigInt * pow10Big(2 * h.decimalPlaces);
    const R = BigInt(tenths) * h.scaledBigInt * h.scaledBigInt * pow10Big(w.decimalPlaces);
    return L < R ? -1 : (L > R ? 1 : 0);
  }

  // 四类里有两端是开区间，落盘为 null：低体重的 scaledMinInclusive、肥胖的 scaledMaxInclusive。
  // 用「该端不存在」表达开区间，不做 ±Infinity 数值兜底——判定本来就走整数比较，
  // 不再有 `310 <= null` 把 null 转成 0 那类静默失效。175/95（肥胖 60）是这条的探测器。
  function scoreBmi(std, gender, heightCm, weightKg) {
    const h = parseDecimal(heightCm);
    const w = parseDecimal(weightKg);
    if (!h.ok) return { status: 'invalid', score: null, level: null, matchedThreshold: null,
                        rawDisplay: null, reason: h.code };
    if (!w.ok) return { status: 'invalid', score: null, level: null, matchedThreshold: null,
                        rawDisplay: null, reason: w.code };
    const cats = std.bmi.categoriesByGender[gender];
    const hit = cats.find((c) =>
      (c.scaledMinInclusive === null || bmiCompareTenths(h, w, c.scaledMinInclusive) >= 0)
      && (c.scaledMaxInclusive === null || bmiCompareTenths(h, w, c.scaledMaxInclusive) <= 0));
    if (hit) {
      return { status: 'scored', score: hit.score, level: hit.categoryLabel,
               matchedThreshold: hit.rawDisplay, rawDisplay: hit.rawDisplay, reason: null };
    }
    return { status: 'unresolved', score: null, level: null, matchedThreshold: null,
             rawDisplay: null, reason: 'bmi_boundary_precision_unresolved' };
  }

  // 精度对照：输入精度高于表格刻度时，向下取位与向上取位落不同档 → 无法定分；
  // 同档就用向下取位那一档（与原程序一致）。
  // **没有 scale<=1 的前置闸**：肺活量、立定跳远（scale=1）同样要查——
  // 272.5 → 272(95) vs 273(100) → unresolved，这是标准里点名要求防的「擅自取位」。
  function precisionCrossCheck(ev, levels, step) {
    if (step.isExactScale) return null;
    const lo = scoreAt(levels, ev.direction, step.floorScaled);
    const hi = scoreAt(levels, ev.direction, step.ceilScaled);
    if (!lo || !hi) return null;
    if (lo.score !== hi.score) {
      return { status: 'unresolved', score: null, level: null, matchedThreshold: null,
               rawDisplay: null, reason: 'measurement_precision_rounding_unresolved' };
    }
    return null;
  }
```

低于最低档由 `scoreAt` 给 `{score:0, level:'不及格'}`（`'不及格'` 取自分值阶梯末档的 level，不写死字面量），不再返回 `invalid/below_minimum`——原程序对「低于最低档」是给 0 分并照常计入总分。

`toScaled` 本任务改成 `parseEventValue(ev, raw)`：先 `parseDecimal`，再 `toStep(dec, ev.decimalPlaces)` 拿到 `{isExactScale, floorScaled, ceilScaled}`，**不做任何取位**。整数型输入本来余数为 0，`isExactScale` 为真，直接走匹配。

`scoreEvent` 重排成：先做输入形态判定（`null`/`undefined` → `incomplete`；`''`/纯空格 → `invalid/empty_string`；非 string/number → `invalid/invalid_type`），再 `parseEventValue`；带 `code` 返回 `invalid`；`integerOnly` 项（`std.events[k].integerOnly`）余数非 0 → `invalid/must_be_integer`；然后跑 `precisionCrossCheck(ev, levels, step)`，有返回就用它，否则用 `step.floorScaled` 走 Task 3 的 `scoreLevel`。BMI 分支走 `scoreBmi(std, gender, heightCm, weightKg)`：`invalid` 带 `code`、`unresolved` 带理由、`scored` 直接给分——**BMI 没有 scaledValue**（它从不产生唯一刻度）。`status` 映射：`scored→complete`、`unresolved→unresolved`、`invalid→invalid`。BMI 结果同样带 `weightedContribution = score * 15 / 100`。

> 判据顺序也有讲究：**精度对照必须排在算分之前**。`10.15` 秒若先落到「低于最低档」就会被判 0 分，而原程序看到的是 `10.1`（10 分）与 `10.2`（0 分）跨档 → `unresolved`。顺序反了会给出一个"看起来合理"的错答案。

**本任务必须同时收口 Task 3 复核记下的 `EventResult` 形状不一致**（Task 3 复核 Important 1，主控裁定由本任务落笔）：Task 3 的四段各自字面量的返回里，`toScaled` 失败那一路缺 `weightPercent`/`bonusEligible`。改成经一个工厂返回，四个 status 共用一份键集合：

```js
  function mkResult(evKey, std, patch) {
    const ev = evKey === 'bmi' ? null : std.events[evKey];
    const lr = patch.levelResult || null;
    return Object.assign({
      eventKey: evKey, name: ev ? ev.name : '体重指数（BMI）',
      status: 'incomplete', levelResult: lr, score: null,
      weightPercent: ev ? ev.weightPercent : std.bmi.weightPercent,
      weightedContribution: null,
      bonusEligible: ev ? ev.bonusEligible : false, bonusScore: 0, hint: null, code: null,
    }, patch);
  }
```

四条硬要求：(1) 每一路 `invalid` 都带顶层 `code`，`below_minimum` 的 `code` 就等于它的 `levelResult.reason`；(2) `code`/`scaledValue` 是契约外的扩展键，`scaledValue` 只在算得出刻度时存在；(3) BMI 的 `weightPercent` 取 `std.bmi.weightPercent`——JSON 顶层 `bmi` 里**本来就有这个键且实测为 15**，`prepareStandard` 已把 `bmi` 整体透传，**不要新造 `maleWeightPercent`、也不要改 `prepareStandard` 的返回形状**；(4) `scoreEvent` 的四个返回全部改成 `return mkResult(evKey, std, {...})`，函数里不许再出现第五个字面量返回体。

追加两条断言到 `tools/test_tice_calc.js`（钉住收口本身，不是钉住实现细节）：

```js
for (const bad of [{ eventKey: 'run1000m', raw: '210' }, { eventKey: 'sprint50m', raw: 'abc' }]) {
  const r = calc.scoreEvent(std, { gender: 'male', grade: '大一', ...bad });
  assert.strictEqual(r.status, 'invalid');
  assert.ok(typeof r.code === 'string' && r.code.length, `${bad.eventKey}/${bad.raw} 缺顶层 code`);
  ['weightPercent', 'bonusEligible', 'hint', 'name', 'levelResult'].forEach((k) =>
    assert.ok(k in r, `${bad.eventKey}/${bad.raw} 的 invalid 缺契约键 ${k}`));
}
const bm = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'sprint50m', raw: '11.1' });
assert.strictEqual(bm.status, 'invalid');
assert.strictEqual(bm.code, 'below_minimum');
```

> 上面第三条断言用 `11.1` 秒压 `below_minimum`（男 grade12 最差档 10.1 秒），实跑得先按实测阈值确认；若该输入落到别的分支，换一个确实低于最差档的值，别改断言的形状。

- [ ] **Step 4: 跑到通过**

Run: `cd <仓库根目录> && node tools/test_tice_calc.js`
Expected: `all 15 pass` + `bmi ${bmiCases.length} pass + 空隙2 + 跨档2`（即 `bmi 5 pass + 空隙2 + 跨档2`），退出码 0。

再跑 Global Constraint 9 的两段 Python 门（Constraint 13：只用这两个窄 pattern）：

```bash
cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_tice*.py" 2>&1 | tail -4
cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_field*.py" 2>&1 | tail -4
```

Expected: `Ran 23 tests` / `OK (skipped=1)` 与 `Ran 136 tests` / `OK`。本任务不新建 `web-next/` 文件，白名单不用动（Constraint 12 只管新建）。

- [ ] **Step 5: 提交**

```bash
cd <仓库根目录> && git add web-next/tice-calc.js tools/test_tice_calc.js && git -c user.name=campus-guide -c user.email=noreply@local commit -q -m "feat(tice): BMI 分类与边界/取位两类无法定分"
```

---

## Task 5: 加权标准分、附加分与总分等级

**Files:**
- Modify: `web-next/tice-calc.js`（`computeBonus`、`gradeOf`、`assemble`）
- Test: `tools/test_tice_calc.js`

**Interfaces:**
- Consumes: Task 3/4 的 `scoreEvent`、`std.events[].byGroup[][].bonusTable`
- Produces: `computeBonus(std, evKey, gender, group, scaled)`, `gradeOf(total)`, `assemble(std, {gender, grade, answers})`

- [ ] **Step 1: 写失败测试**

样例是精挑的「全 100 分档 + 两项附加分」组合，每个数都能由 Task 1 Step 5 的实测阈值手算复核：

```js
// 男 大一：BMI 21.4→正常100 / 肺活量5040→100 / 50米6.7→100 / 坐位体前屈24.9→100 /
// 立定跳远273→100 / 引体向上 21 次（100 档 19 次，+2 次 → +2 分）/ 1000米 2'40"（160 秒，
// 100 档 197 秒，快 37 秒 ≥ +10 档门槛 162 秒 → +10 分）
const full = calc.assemble(std, { gender: 'male', grade: '大一', answers: {
  heightCm: 175, weightKg: 65.5, vitalCapacity: 5040, sprint50m: '6.7',
  sitAndReach: '24.9', standingLongJump: 273, pullUps: 21, run1000m: "2'40\"" } });
assert.strictEqual(full.status, 'complete');
assert.strictEqual(full.standardScore, 100);
assert.strictEqual(full.strengthBonus, 2);
assert.strictEqual(full.enduranceBonus, 10);
assert.strictEqual(full.totalBonus, 12);
assert.strictEqual(full.totalScore, 112);
assert.strictEqual(full.gradeCode, 'excellent');
assert.strictEqual(full.gradeLabel, '优秀');
assert.strictEqual(full.items.length, 7);

// 只快 10 秒：197-10=187 秒 → 187 ≤ 193（+4 档）→ 附加分 4
const minusRun = { heightCm: 175, weightKg: 65.5, vitalCapacity: 5040, sprint50m: '6.7',
                   sitAndReach: '24.9', standingLongJump: 273, pullUps: 21 };
const small = calc.assemble(std, { gender: 'male', grade: '大一',
                                   answers: Object.assign({}, minusRun, { run1000m: "3'07\"" }) });
assert.strictEqual(calc.parseEnduranceTime("3'07\"").seconds, 187);
assert.strictEqual(small.enduranceBonus, 4);

// 只填四项半（BMI 两项 + 三项）：分项留着，但不造总分
const part = calc.assemble(std, { gender: 'male', grade: '大一', answers: {
  heightCm: 175, weightKg: 65.5, vitalCapacity: 4000, sprint50m: '7.5', sitAndReach: '12' } });
assert.strictEqual(part.status, 'incomplete');
assert.strictEqual(part.totalScore, null);
assert.strictEqual(part.gradeCode, null);
assert.strictEqual(part.items.length, 7, '七项都要在场，空的显示待填写');
assert.strictEqual(part.items.filter((r) => r.status === 'complete').length, 4);
assert.strictEqual(part.items.filter((r) => r.status === 'incomplete').length, 3);
assert.strictEqual(part.items[1].score, 74);   // 肺活量 4000 的分项仍要留着

// 附加分总封顶 20：引体向上 29（+10）与 1000米 2'40"（+10）→ 20，不超
// 女生换算：BMI 正常、800米 grade12 首位 3'18"=198 秒，+10 档 = 198-50=148 秒 = 2'28"
const female = calc.assemble(std, { gender: 'female', grade: '大二', answers: {
  heightCm: 165, weightKg: 55, vitalCapacity: 3400, sprint50m: '7.5', sitAndReach: '25.8',
  standingLongJump: 201, sitUps: 56, run800m: "2'28\"" } });
assert.strictEqual(female.status, 'complete');
assert.strictEqual(female.enduranceBonus, 10);
assert.strictEqual(female.totalBonus, 10);
```

`assemble` 返回的 `items` 恒为七项（`eventKeysFor` 给全），未填的项 `status:'incomplete'`、`score:null`——这样界面能把「待填写」摆出来，同时 `filled.length < keys.length` 保证不生成总分。

- [ ] **Step 2: 先实测复核两组期望值，再实现**

Run:
```bash
cd <仓库根目录> && "./.venv/Scripts/python.exe" -c "
import json;S=json.load(open('web-next/tice-standard.json',encoding='utf-8'))
for k,gen in [('run1000m','male'),('run800m','female'),('sitUps','female'),('standingLongJump','female')]:
    print(k, S['events'][k]['thresholds'][gen]['grade12'][:3],
          S['events'][k]['bonusDeltas'][:3] if S['events'][k]['bonusDeltas'] else '')
print('jump female g12 head', S['events']['standingLongJump']['thresholds']['female']['grade12'][:2])
print('sitReach female g12 head', S['events']['sitAndReach']['thresholds']['female']['grade12'][:2])
print('vc female g12 head', S['events']['vitalCapacity']['thresholds']['female']['grade12'][:2])
print('50m female g12 head', S['events']['sprint50m']['thresholds']['female']['grade12'][:2])"
```
Expected: 打印出女生各项的 100 分档阈值与附加分档。用这些数字逐条复核 Step 1 里 `female` 那组的 `sitUps: 56`、`run800m: "2'28\""`、`standingLongJump: 201`、`sitAndReach: '25.8'`、`vitalCapacity: 3400`、`sprint50m: '7.5'` 是否真的都命中 100 分档；**任何一项对不上就改测试输入值本身**（改成一个确实命中 100 档的成绩），不许改断言期望、更不许把 `totalBonus` 调成碰巧能过的数。

- [ ] **Step 3: 写实现**

```js
  const STRENGTH_KEYS = ['pullUps', 'sitUps'];
  const ENDURANCE_KEYS = ['run1000m', 'run800m'];
  // 事件键 → 页面上的输入字段名；BMI 由身高体重两项派生
  const ANSWER_KEY = { vitalCapacity: 'vitalCapacity', sprint50m: 'sprint50m',
                       sitAndReach: 'sitAndReach', standingLongJump: 'standingLongJump',
                       pullUps: 'pullUps', sitUps: 'sitUps',
                       run1000m: 'run1000m', run800m: 'run800m' };

  function computeBonus(std, evKey, gender, group, scaled) {
    const ev = std.events[evKey];
    if (!ev.bonusEligible || typeof scaled !== 'number') return { bonusScore: 0, matchedTier: null };
    for (const t of ev.byGroup[gender][group].bonusTable) {
      if (ev.direction === 'higher_is_better' ? scaled >= t.scaledAbsoluteThreshold
                                              : scaled <= t.scaledAbsoluteThreshold) {
        return { bonusScore: Math.min(std.limits.maxSingleBonusScore, t.bonusScore), matchedTier: t };
      }
    }
    return { bonusScore: 0, matchedTier: null };
  }

  function gradeOf(total) {
    if (typeof total !== 'number' || !Number.isFinite(total) || total < 0) {
      return { gradeCode: null, gradeLabel: null };
    }
    if (total >= 90) return { gradeCode: 'excellent', gradeLabel: '优秀' };
    if (total >= 80) return { gradeCode: 'good', gradeLabel: '良好' };
    if (total >= 60) return { gradeCode: 'pass', gradeLabel: '及格' };
    return { gradeCode: 'fail', gradeLabel: '不及格' };
  }

  function assemble(std, input) {
    const keys = eventKeysFor(std, input.gender);
    const items = keys.map((k) => scoreEvent(std, {
      gender: input.gender, grade: input.grade, eventKey: k,
      raw: input.answers[ANSWER_KEY[k]], inputs: input.answers }));

    const filled = items.filter((r) => r.status !== 'incomplete');
    const blocking = Array.from(new Set(
      filled.filter((r) => r.status !== 'complete').map((r) => r.status)));
    const complete = blocking.length === 0 && filled.length === keys.length;

    // 加权分用整数刻度累加再除回，避免 0.1 级别的浮点尾巴
    const cent = filled.filter((r) => typeof r.weightedContribution === 'number')
                       .reduce((a, r) => a + Math.round(r.weightedContribution * 100), 0);
    const standard = Math.min(std.limits.maxStandardScore, cent / 100);
    const strength = filled.filter((r) => STRENGTH_KEYS.indexOf(r.eventKey) >= 0)
      .reduce((a, r) => a + (complete ? r.bonusScore : 0), 0);
    const endurance = filled.filter((r) => ENDURANCE_KEYS.indexOf(r.eventKey) >= 0)
      .reduce((a, r) => a + (complete ? r.bonusScore : 0), 0);
    const totalBonus = complete
      ? Math.min(std.limits.maxTotalBonusScore, strength + endurance) : 0;
    const totalScore = complete ? Math.round((standard + totalBonus) * 10) / 10 : null;
    const g = complete ? gradeOf(totalScore) : { gradeCode: null, gradeLabel: null };

    return { status: complete ? 'complete'
             : blocking.indexOf('unresolved') >= 0 ? 'unresolved'
             : blocking.indexOf('invalid') >= 0 ? 'invalid' : 'incomplete',
             items, standardScore: complete ? standard : null,
             strengthBonus: strength, enduranceBonus: endurance, totalBonus,
             totalScore, gradeCode: g.gradeCode, gradeLabel: g.gradeLabel,
             blockingReasons: blocking };
  }
```

`scoreEvent` 里补一行真附加分（Task 3/4 先给 0，本任务接上）：非 BMI 且 `bonusEligible` 时，`bonusScore = computeBonus(std, evKey, gender, group, scaled).bonusScore`；BMI 恒 0。`incomplete` 项不参与累加，保证 Task 5 里只填五项那条用例的 `items.length === 5` 与「分项留着」同时成立。

- [ ] **Step 4: 跑到通过**

Run: `cd <仓库根目录> && node tools/test_tice_calc.js`
Expected: Task 3/4 的用例仍全过，本组断言全过，退出码 0。

- [ ] **Step 5: 提交**

```bash
cd <仓库根目录> && git add web-next/tice-calc.js tools/test_tice_calc.js && git commit -q -m "feat(tice): 加权标准分、附加分与总分等级"
```

---

## Task 6: 输入体检与单位混淆提示

spec §3 第 3 行那一整块。算法风险低、文案量大，逐条照他搬。

**Files:**
- Create: `web-next/tice-checks.js`
- Modify: `web-next/tice-calc.js`（`scoreEvent` 前挂 `validateField`，`hint` 随结果带出）
- Test: `tools/test_tice_calc.js`

**Interfaces:**
- Produces: `validateField(eventKey, raw, answers)` → `{ok, code, errorCopy, hint, normalized}`；`summaryOfHints(hints)`

- [ ] **Step 1: 写失败测试**

追加到 `tools/test_tice_calc.js`：

```js
const checks = require('../web-next/tice-checks.js');
const want = [
  ['vitalCapacity', 4,    'hint',  '疑似填写了升（L）。如实际为 4 L，请填写 4000 mL。'],
  ['vitalCapacity', 900,  'hint',  '数值较少见，请确认肺活量毫升（mL）数是否填写正确。'],
  ['standingLongJump', 2.15, 'hint', '疑似填写了米（m）。如实际为 2.15 m，请填写 215 cm。'],
  ['sitAndReach', 248,    'hint',  '疑似填写了毫米（mm）或漏填小数点，请按厘米（cm）填写。'],
  ['sprint50m', 75,       'hint',  '数值较大，请确认是否漏填小数点，例如 7.5 秒误填为 75。'],
  ['weightKg', 130,       'hint',  '数值较大。如原始记录单位为“斤”，请换算为 kg 后填写。'],
  ['heightCm', 1750,      'hint',  '疑似填写了毫米（mm）。如实际身高为 1750 mm，请填写 175 cm。'],
  ['run1000m', '210:30',  'hint',  '分钟数较大，请确认是否将总秒数填入了“分”（如 210 秒应填 3 分 30 秒）。'],
  ['vitalCapacity', -1,   'error', '肺活量不能为负数，请输入有效数字，例如 4200'],
  ['pullUps', 3.5,        'error', '引体向上不能为负数，请输入整数次数，例如 8'],
];
let cf = 0;
for (const [ev, raw, kind, copy] of want) {
  const r = checks.validateField(ev, raw, { heightCm: 175, weightKg: 65.5 });
  if (kind === 'error') {
    if (r.ok || r.errorCopy !== copy) { console.log('FAIL err', ev, raw, JSON.stringify(r.errorCopy)); cf += 1; }
  } else if (r.hint !== copy) { console.log('FAIL hint', ev, raw, JSON.stringify(r.hint)); cf += 1; }
}
assert.strictEqual(checks.summaryOfHints([]), '');
assert.strictEqual(checks.summaryOfHints(['a', 'b']),
  '检测到 2 项疑似异常输入。当前仍按填写值计算成绩，不影响评分结果。');
console.log(cf ? `体检 ${cf} 条失败` : `体检 ${want.length} 条通过`);
if (cf) process.exit(1);
```

- [ ] **Step 2: 先确认时间格式的真实宽容度**

Run:
```bash
cd <仓库根目录> && node -e "
const c=require('./web-next/tice-calc.js');
for (const v of ['4:20','4:7','4:60','4.20','210', \"3'17\\\"\"]) console.log(v, JSON.stringify(c.parseEnduranceTime(v)));"
```
Expected: `4:20`→`{ok:true,seconds:260}`；`4:7`→`{ok:true,seconds:247}`；`4:60`→`{ok:false,code:"invalid_minutes_or_seconds_range"}`；`4.20`→`{ok:false,code:"ambiguous_decimal_time_format"}`；**`'210'`（字符串）→`{ok:true,seconds:210}`**；`3'17"`→`{ok:true,seconds:197}`。这六条 Task 3 Step 1 已钉成 `deepStrictEqual` 断言，本步只是再打印一遍确认没被后续任务改坏。

> 回源更正（2026-11-09）：本节早先要求 `'210'` 被拒，理由是"输入框里的 210 语义不明"。对照解包产物实测**这是错的**——原程序接受 `'210'` / `'210秒'` / `'197s'` / `'3:7'`（都等于总秒数），只把小数时间单独拒成 `ambiguous_decimal_time_format`。已按原程序改：判据服从它，提示文案照它的说法。

- [ ] **Step 3: 写 `web-next/tice-checks.js`**

一张 `CHECKS` 表，每事件 `{scale, unit, hints: [{test(raw, answers), copy}], errors: [{test(raw), code, copy}]}`，按他包里的原文逐条录入：升↔毫升（`0 < r <= 15`）、米↔厘米（`0 < r <= 4.5`）、毫米或漏小数点（`r >= 1000`）、50米过大（`r >= 45`）/过小（`r < 5`）/少见（`r > 20`）、坐位体前屈超 ±40 与 ±25、体重 ≥100（斤）与 ≥1000（克）、身高 mm 与 cm 混淆、长跑分钟 > 20 的总秒数误填、次数非整数、负数。返回 `{ok, code, errorCopy, hint, normalized}`。

本文件必须和 `tice-calc.js` 一样包成 UMD（`module.exports` 或挂 `window.TICE_CHECKS`），否则 Task 6 Step 1 的 `require` 在 Node 里直接失败：

```js
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.TICE_CHECKS = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  /* CHECKS 表 + validateField + summaryOfHints，三个都 return 出去 */
}));
```

汇总句固定：

```js
function summaryOfHints(hints) {
  if (!hints.length) return '';
  return `检测到 ${hints.length} 项疑似异常输入。当前仍按填写值计算成绩，不影响评分结果。`;
}
```

- [ ] **Step 4: 接到 `scoreEvent` 并跑通**

`scoreEvent` 开头插入：先 `checks.validateField(evKey, raw, answers)`，`ok === false` 时直接返回 `{status:'invalid', code, errorCopy}`；`hint` 只挂在返回值上、不参与任何判定——分数照常算，这是他的行为（提示不影响评分）。BMI 分支用 `answers.heightCm / answers.weightKg` 作输入做同样的体检。

Run: `cd <仓库根目录> && node tools/test_tice_calc.js`
Expected: 全绿，含 `体检 10 条通过`。

- [ ] **Step 5: 提交**

```bash
cd <仓库根目录> && git add web-next/tice-checks.js web-next/tice-calc.js tools/test_tice_calc.js && git commit -q -m "feat(tice): 输入体检与单位混淆提示"
```

---

## Task 7: 本机存储层

**Files:**
- Create: `web-next/tice-store.js`
- Test: `tools/test_tice_store.js`, `tools/test_tice_privacy.js`

**Interfaces:**
- Produces: `create(backend)` → `{available, draft:{load,save,clear}, archives:{list,upsert,remove,duplicateAsNew}, rawGet, rawSet}`；`exportText(record)` → 纯文本清单（**不含资料三项**）；每个失败分支返回 `{ok:false, copy}`，`copy` 用 spec §9 原文

- [ ] **Step 1: 写失败测试**

Create `tools/test_tice_store.js`：

```js
const assert = require('assert');
const store = require('../web-next/tice-store.js');

function mkStore(broken) {
  const map = new Map();
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => { if (broken === 'write' || broken === 'all') throw new Error('QuotaExceeded'); map.set(k, String(v)); },
    removeItem: (k) => { if (broken === 'remove' || broken === 'all') throw new Error('fail'); map.delete(k); },
    _map: map,
  };
}

const env = store.create(mkStore());
assert.strictEqual(env.available, true);
assert.strictEqual(env.draft.load().ok, true);
assert.strictEqual(env.draft.load().value, null, '空存储读出 null，不抛');
env.draft.save({ vitalCapacity: 4000 });
assert.strictEqual(env.draft.load().value.vitalCapacity, 4000);

env.rawSet('tice_draft_v1', JSON.stringify({ __schema: 'v9', x: 1 }));
const guarded = env.draft.load();
assert.strictEqual(guarded.ok, false);
assert.strictEqual(guarded.copy, '本地暂存读取失败或版本暂不支持，原数据已保留；当前填写暂不能覆盖它');
assert.ok(env.rawGet('tice_draft_v1').includes('v9'), '未知版本不许被覆盖');

const badWrite = store.create(mkStore('write'));
assert.strictEqual(badWrite.draft.save({ a: 1 }).ok, false);
assert.strictEqual(badWrite.draft.save({ a: 1 }).copy,
  '自动暂存失败，当前填写仍在页面中；请勿将本机记录作为唯一凭证');

const a = env.archives;
assert.strictEqual(a.upsert({ id: 'x1', academicYear: '', totalScore: 88 }).copy, '请填写学年');
assert.strictEqual(a.upsert({ id: 'x1', academicYear: '2025-2026', totalScore: 88 }).ok, true);
assert.strictEqual(a.list().length, 1);

const brokenRemove = store.create(mkStore('remove'));
brokenRemove.rawSet('tice_archives_v1', JSON.stringify([{ id: 'y', academicYear: '2024-2025' }]));
assert.strictEqual(brokenRemove.archives.remove('y').copy, '删除失败，原记录已保留');
assert.strictEqual(brokenRemove.archives.list().length, 1);

const dup = a.duplicateAsNew('x1');
assert.strictEqual(dup.ok, true);
assert.strictEqual(a.list().length, 2);
assert.strictEqual(a.list().find((x) => x.id === 'x1').academicYear, '2025-2026', '旧存档不许被动');

const dead = store.create(mkStore('all'));
assert.strictEqual(dead.available, false);
assert.strictEqual(dead.draft.load().ok, false);
assert.strictEqual(dead.archives.list().length, 0);
console.log('store 断言全过');
```

- [ ] **Step 2: 跑到失败**

Run: `cd <仓库根目录> && node tools/test_tice_store.js`
Expected: `Cannot find module '../web-next/tice-store.js'`。

- [ ] **Step 3: 写实现**

`web-next/tice-store.js`：

```js
// UMD：浏览器挂 window.TICE_STORE，Node 侧测试可 require
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.TICE_STORE = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const SCHEMA = 'v1';
  const KEYS = { draft: 'tice_draft_v1', archives: 'tice_archives_v1' };
  const COPY = {
    draftReadFail: '本地暂存读取失败或版本暂不支持，原数据已保留；当前填写暂不能覆盖它',
    draftWriteFail: '自动暂存失败，当前填写仍在页面中；请勿将本机记录作为唯一凭证',
    draftClearFail: '暂存清除失败，原填写已保留',
    saveFail: '保存失败，原存档未被替换，请稍后重试',
    removeFail: '删除失败，原记录已保留',
    historyFail: '历史读取失败或版本暂不支持，原存储已保留',
    yearRequired: '请填写学年',
    copyFail: '复制失败，原暂存与存档已保留',
  };
  const PROFILE_KEYS = ['name', 'college', 'major', 'enrollGrade', 'note'];
  const EXPORT_FORBIDDEN = ['name', 'college', 'major'];

  function create(backend) {
    let available = true;
    try { backend.setItem('__tice_probe__', '1'); backend.removeItem('__tice_probe__'); }
    catch (e) { available = false; }

    const rawGet = (k) => { try { return backend.getItem(k); } catch (e) { return null; } };
    const rawSet = (k, v) => { try { backend.setItem(k, v); return true; } catch (e) { return false; } };
    const rawDel = (k) => { try { backend.removeItem(k); return true; } catch (e) { return false; } };

    function readKey(key, fallback) {
      if (!available) return { ok: false, copy: COPY.draftReadFail, value: fallback };
      const s = rawGet(key);
      if (s === null) return { ok: true, value: fallback };
      let parsed;
      try { parsed = JSON.parse(s); } catch (e) { return { ok: false, copy: COPY.historyFail, value: fallback }; }
      if (!parsed || parsed.__schema !== SCHEMA) return { ok: false, copy: COPY.draftReadFail, value: fallback };
      return { ok: true, value: parsed };
    }
    // 先序列化到局部变量，成功后才 setItem —— 中途抛错时磁盘上的旧值没动过
    function writeKey(key, payload) {
      let text;
      try { text = JSON.stringify(Object.assign({ __schema: SCHEMA }, payload)); }
      catch (e) { return { ok: false, copy: COPY.saveFail }; }
      return rawSet(key, text) ? { ok: true } : { ok: false, copy: COPY.saveFail };
    }

    const draft = {
      load() { return readKey(KEYS.draft, null); },
      save(value) { return writeKey(KEYS.draft, { value }) },
      clear() { return rawDel(KEYS.draft) ? { ok: true } : { ok: false, copy: COPY.draftClearFail }; },
    };

    const archives = {
      list() {
        const r = readKey(KEYS.archives, { records: [] });
        if (!r.ok) return [];
        return (r.value && r.value.records) || [];
      },
      upsert(rec) {
        if (!rec || String(rec.academicYear || '').trim() === '') {
          return { ok: false, copy: COPY.yearRequired };
        }
        const cur = archives.list();
        const id = rec.id || `a${Date.now().toString(36)}`;
        const hit = cur.findIndex((x) => x.id === id);
        const next = cur.slice();
        const stored = Object.assign({}, rec, { id, savedAt: new Date().toISOString() });
        if (hit >= 0) next[hit] = stored; else next.push(stored);
        const w = writeKey(KEYS.archives, { records: next });
        return w.ok ? { ok: true, id } : { ok: false, copy: COPY.saveFail };
      },
      remove(id) {
        const cur = archives.list();
        const next = cur.filter((x) => x.id !== id);
        let text;
        try { text = JSON.stringify({ __schema: SCHEMA, records: next }); }
        catch (e) { return { ok: false, copy: COPY.removeFail }; }
        return rawSet(KEYS.archives, text)
          ? { ok: true } : { ok: false, copy: COPY.removeFail };
      },
      duplicateAsNew(id) {
        const src = archives.list().find((x) => x.id === id);
        if (!src) return { ok: false, copy: COPY.copyFail };
        const copy = Object.assign({}, src, { id: null, academicYear: '', savedAt: null });
        delete copy.id;
        return archives.upsert(copy).ok
          ? { ok: true, record: copy } : { ok: false, copy: COPY.copyFail };
      },
    };

    return { available, draft, archives, rawGet, rawSet, COPY };
  }

  // 导出文本只带成绩与输入，资料三项（姓名/学院/专业）永不进文本层
  function exportText(rec) {
    const lines = [`学年：${rec.academicYear || '—'}`, `年级：${rec.grade || '—'}`];
    (rec.items || []).forEach((it) => {
      lines.push(`${it.name}：${it.rawDisplay || '—'} → ${it.score === null ? '—' : it.score} 分`);
    });
    lines.push(`标准分：${rec.standardScore === null ? '—' : rec.standardScore}`);
    lines.push(`附加分：${rec.totalBonus}`);
    lines.push(`总分：${rec.totalScore === null ? '—' : `${rec.totalScore} / 120`}`);
    lines.push(`等级：${rec.gradeLabel || '—'}`);
    lines.push('仅供参考，实际成绩以学校体测系统记录为准。');
    return lines.join('\n');
  }

  return { create, exportText, COPY, KEYS, SCHEMA, PROFILE_KEYS, EXPORT_FORBIDDEN };
}));
```

顺序上有一条必须守住：`archives.duplicateAsNew` 复制完必须先把 `academicYear` 置空、由用户在浮层里填学年再落盘，因此它会先撞上 `yearRequired`——所以本函数内部走的是「带新 id 直接 upsert 到空学年会被拒」之外的路径：先 `list()` 复制对象、生成新 id、写入前不校验学年，只在用户保存时校验。实现时给 `upsert` 加第二参 `{ requireYear = true }`，`duplicateAsNew` 传 `false`，测试里断言复制出的记录 `academicYear === ''` 且能被列表读出。

存档记录字段：`id`、`academicYear`、`gender`、`grade`、七项原始输入、`items` 快照、`standardScore`、`strengthBonus`、`enduranceBonus`、`totalBonus`、`totalScore`、`gradeCode`、`gradeLabel`、`status`、`savedAt`，加档案资料六个字段（`name`/`college`/`major`/`enrollGrade`/`note`，均可空）。

- [ ] **Step 4: 跑到通过**

Run: `cd <仓库根目录> && node tools/test_tice_store.js`
Expected: 只打印 `store 断言全过`，退出码 0。

- [ ] **Step 5: 写隐私契约测试**

Create `tools/test_tice_privacy.js`（对应 spec §12 第 6 条，做成自动断言而不是靠手工看）：

```js
const assert = require('assert');
const store = require('../web-next/tice-store.js');

function mkMap() {
  const map = new Map();
  return { getItem: (k) => (map.has(k) ? map.get(k) : null),
           setItem: (k, v) => map.set(k, String(v)),
           removeItem: (k) => map.delete(k) };
}
const env = store.create(mkMap());
const rec = {
  id: 'p1', academicYear: '2025-2026', grade: '大一',
  name: '测试甲', college: '电视学院', major: '新闻学', enrollGrade: '2025级', note: '备注乙',
  items: [{ name: '肺活量', rawDisplay: '5040', score: 100 }],
  standardScore: 100, totalBonus: 12, totalScore: 112, gradeLabel: '优秀',
};
env.archives.upsert(rec);
const text = store.exportText(env.archives.list()[0]);
for (const pii of ['测试甲', '电视学院', '新闻学', '2025级', '备注乙']) {
  assert.strictEqual(text.includes(pii), false, `导出文本泄漏了 ${pii}：${text}`);
}
assert.ok(text.includes('肺活量'), '导出必须带成绩');
assert.ok(text.includes('仅供参考'), '导出必须带小字');
console.log('privacy 断言全过');
```

Run: `cd <仓库根目录> && node tools/test_tice_privacy.js`
Expected: `privacy 断言全过`。若前四个断言之一红，说明 `exportText` 直接序列化了整条记录——改成只按字段白名单拼行，不要图省事 `JSON.stringify(rec)`。

- [ ] **Step 6: 提交**

```bash
cd <仓库根目录> && git add web-next/tice-store.js tools/test_tice_store.js tools/test_tice_privacy.js && git commit -q -m "feat(tice): 本机暂存与存档层，含四类失败保护与导出脱敏"
```

---

## Task 8: 页面骨架、样式基线与顶栏入口

**Files:**
- Create: `web-next/tice.html`
- Create: `web-next/tice.css`
- Modify: `web-next/field.html`（顶栏）
- Modify: `tools/test_field_ui.py:1462`

**Interfaces:**
- Produces: DOM id `#gender` `#grade` `#inputs` `#total` `#history` `#declaration` `#archive-mask` `#archive-panel`

- [ ] **Step 1: `tice.html`**

```html
<!doctype html>
<html lang="zh-CN" data-theme="cobalt-field">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>体测成绩估算 · 广院通</title>
<link rel="stylesheet" href="field.css">
<link rel="stylesheet" href="tice.css">
</head>
<body class="tice">
<a class="skip" href="#gender">跳到填写</a>
<header class="ticebar">
  <a class="back" href="/field">返回广院通</a>
  <b>体测成绩估算</b>
</header>
<main>
  <section id="inputs" aria-label="填写成绩"></section>
  <section id="total" aria-live="polite" aria-label="估算结果"></section>
  <section id="history" aria-label="本机记录"></section>
  <section id="declaration" aria-label="来源与说明"></section>
</main>
<div id="archive-mask" hidden></div>
<aside id="archive-panel" hidden role="dialog" aria-modal="true" aria-labelledby="archive-title"></aside>
<script src="tice-calc.js" defer></script>
<script src="tice-checks.js" defer></script>
<script src="tice-store.js" defer></script>
<script src="tice.js" defer></script>
</body>
</html>
```

三个内核文件都是 UMD（Task 3/6/7 已按 `module.exports` 或挂全局写），浏览器里依次落成 `window.TICE_CALC` `window.TICE_CHECKS` `window.TICE_STORE`，`tice.js` 用这三个全局名取用。顺序不能调：`tice.js` 必须排最后。数据一律由 `tice.js` 里 `fetch('tice-standard.json')` 取；取不到就渲染「评分表未加载，本页无法算分」，界面上不得出现任何分数或 0 分。

- [ ] **Step 2: `tice.css`**

只写本页规则，色值全部 `var(--…)`，token 用 `field.css` `:root` 里已有的；缺一个就复用现有语义最接近的那个，不在本页定义新颜色。需要落的最小集：`.tice` 主体与 `main` 竖距、`.ticebar`、`#inputs` 每行（label + input + 单位 + 提示位）、四态标签 `.st-scored` `.st-todo` `.st-fix` `.st-rule`、`#total` 结果卡、`#note` 小字 `font-size:12px;color:var(--muted)`、`#archive-mask/#archive-panel` 浮层、`@media (max-width:520px)` 单列。

- [ ] **Step 3: 跑 CSS 契约**

Run: `cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest tools.test_tice.FileContractTest -v 2>&1 | tail -4`
Expected: 两项都 PASS——Task 2 里那条 ERROR 到此转绿。若裸色值那条红，把报错里列出的字面量换成 `var(--…)`，不许往 `field.css` 的 `:root` 里加新色值来绕过。

- [ ] **Step 4: 顶栏入口**

`web-next/field.html` 里，`<button class="ghostbtn" type="button" id="databtn" …>个人数据</button>` 那一行之后、`<button class="themesw"` 之前插入：

```html
    <a class="ghostbtn" href="/tice.html" title="体测成绩估算：本机填写、本机估算，不上传">体测</a>
```

- [ ] **Step 5: 更新新增文件白名单**

`tools/test_field_ui.py:1462` 的 `expected` 改成：

```python
        expected = {f"field.{ext}" for ext in ("html", "css", "js")} | {EMBLEM} | {
            "tice.html", "tice.css", "tice.js", "tice-calc.js", "tice-checks.js",
            "tice-store.js", "tice-standard.json"}
```

- [ ] **Step 6: 跑全量 field 套件**

Run: `cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_field*.py" 2>&1 | tail -3`
Expected: `Ran 136 tests` + `OK`。若 408 行那条断言红，说明入口插到开关右边去了，回 Step 4 改位置——**不许改断言**。

- [ ] **Step 7: 提交**

```bash
cd <仓库根目录> && git add web-next/tice.html web-next/tice.css web-next/field.html tools/test_field_ui.py && git commit -q -m "feat(tice): 页面骨架、token 化样式与顶栏入口"
```

---

## Task 9: 计算区与结果卡渲染

**Files:**
- Create: `web-next/tice.js`
- Test: `tools/test_tice_render.py`

**Interfaces:**
- Consumes: `TICE_CALC`（`prepareStandard/scoreEvent/assemble/eventKeysFor/gradeGroupOf`）、`tice-checks.validateField/summaryOfHints`、`tice-store.create`
- Produces: `renderInputs` `renderResult` `renderTotal` `state()`

- [ ] **Step 1: 写渲染契约测试**

Create `tools/test_tice_render.py`：

```python
"""计算区与结果卡的静态契约：四态文案、小字、未完成三分支必须都在。"""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "web-next" / "tice.js").read_text(encoding="utf-8")


def test_four_states_are_named_verbatim():
    for s in ("已计算", "待填写", "需修正", "规则待确认"):
        assert s in JS, f"缺状态文案 {s}"


def test_reference_note_is_present():
    assert "仅供参考，实际成绩以学校体测系统记录为准" in JS


def test_three_incomplete_branches_are_distinct():
    for c in ("尚未完成全部项目", "存在需修正的输入字段", "当前公开标准无法唯一确定该项分数"):
        assert c in JS, f"缺未完成话术 {c}"


def test_no_fabricated_total_when_incomplete():
    assert re.search(r"totalScore\s*===\s*null|totalScore\s*==\s*null", JS), "未完成时总分位必须走 null 分支"


def test_standard_load_failure_blocks_any_score():
    assert "评分表未加载，本页无法算分" in JS


def test_grade_label_comes_from_calc():
    head = JS.split("function renderTotal")[1][:600]
    assert "优秀" not in head and "良好" not in head, "结果卡不许自己写等级文案"


def test_entry_uses_fetch_not_script_tag():
    html = (ROOT / "web-next" / "tice.html").read_text(encoding="utf-8")
    assert ".json" not in html, "数据只能由 fetch 取，不能当 script 引"
```

Run: `cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest tools.test_tice_render -v`
Expected: 全部 FAIL（`tice.js` 还不存在，读文件就抛）。

- [ ] **Step 2: 写 `tice.js`**

逐条实现，都是硬要求：

1. 启动 `fetch('tice-standard.json')` → `prepareStandard`；失败渲染「评分表未加载，本页无法算分」并 return，不出现任何分数。
2. 性别与年级用 `<fieldset>` + radio 分段单选；年级四项 `大一/大二/大三/大四`，切换后只重渲跑动项与力量项的标签（引体向上↔一分钟仰卧起坐、1000米↔800米）和性别专属字段的显隐。
3. 七项输入布局：BMI 行（身高 cm + 体重 kg，回显算出的 BMI 与分类）、肺活量 mL、50米 s（一位小数）、坐位体前屈 cm（允许负数，占位 `12.5 或 -3`）、立定跳远 cm、引体向上/仰卧起坐 次（整数）、1000/800米 分+秒两格。每个 `<input>` 用 `aria-describedby` 指向自己的错误/提示节点。
4. 输入去抖 300ms：`validateField` → `assemble` → 渲染；`draft.save` 落暂存；`draft.load().ok === false` 时不覆盖并显示它给的原文那句。首屏若恢复到暂存，提示「已恢复上次填写内容」。
5. 结果表每行：项目名、实测值（按 `rawDisplay` 档位回显）、得分、`加权贡献`、附加分（`+N`，仅两项 eligible 显示）、状态标签四选一。
6. 结果卡：标准分、力量附加分、长跑附加分、总附加分、总分（`xx / 120`）、等级。`status !== 'complete'` 时总分与等级位显示对应那句未完成话术，不显示数字：
   - `incomplete` → 「尚未完成全部项目」+「尚未完成全部项目，已算出的分项得分与加权贡献已保留；补齐全部七项后生成完整总分。」
   - `invalid` → 「存在需修正的输入字段」+「请修正下方列出的输入字段，完整成绩暂不可生成。」
   - `unresolved` → 「规则待确认」+「当前公开标准无法唯一确定该项分数，因此暂不生成完整成绩。」
7. 小字固定一句，`id="note"`：`仅供参考，实际成绩以学校体测系统记录为准。`
8. 「重新开始」：二次确认文案「将清空当前填写和自动暂存，已保存的历史记录不受影响。」，确认后 `draft.clear()`，成功提示「已重新开始」，失败显示「暂存清除失败，原填写已保留」。
9. 「保存本次记录」打开 Task 10 的档案浮层。
10. 汇总提示：`summaryOfHints(hints)` 有内容时挂在结果卡下方，不参与任何判定。

- [ ] **Step 3: 跑到通过 + 浏览器实测**

Run:
```bash
cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest tools.test_tice_render tools.test_tice -v 2>&1 | tail -4 && node tools/test_tice_calc.js && node tools/test_tice_store.js
```
Expected: Python 侧全绿（含 Task 2 那两条 Task 8 时还 ERROR 的契约），Node 两个脚本全绿。

浏览器实测（自起独立端口，不撞在跑的后端）：
```bash
cd <仓库根目录>/web-next && "./.venv/Scripts/python.exe" -m http.server 8137
```
打开 `http://127.0.0.1:8137/tice.html`，逐条走：Task 5 那组满分样例 → 标准分 100、附加分 12、总分 112、优秀；只填五项 → 未完成话术且分项仍显示；肺活量填 `4` → 升/毫升提示且分数照算；男→女 → 第六七项标签跟着换；刷新 → 「已恢复上次填写内容」；把 `tice-standard.json` 改名再刷 → 只出现「评分表未加载」且无任何数字。测完把文件名改回来。

- [ ] **Step 4: 提交**

```bash
cd <仓库根目录> && git add web-next/tice.js tools/test_tice_render.py && git commit -q -m "feat(tice): 计算区与总分卡渲染"
```

---

## Task 10: 历史区与档案编辑浮层

**Files:**
- Modify: `web-next/tice.js`, `web-next/tice.css`
- Test: `tools/test_tice_render.py`（追加）

**Interfaces:**
- Consumes: `archives.list/upsert/remove/duplicateAsNew`
- Produces: `renderHistory` `renderArchive`

- [ ] **Step 1: 追加失败测试**

```python
def test_archive_fields_are_the_six_from_spec():
    for label in ("姓名（可选）", "学院（可选）", "专业（可选）",
                  "入学年级（可选，如2025级）", "学年（必填）", "备注（可选）"):
        assert label in JS, f"缺档案字段 {label}"


def test_two_confirmations_exist():
    assert "仅删除这条体测存档，删除后无法恢复。是否继续？" in JS
    assert "当前填写内容将被替换，是否继续？旧存档不会改变。" in JS


def test_one_shot_profile_switch_copy_exists():
    assert "一次性资料 · 仅保存本条记录，不更新常用资料" in JS


def test_privacy_line_exists():
    assert "仅保存在本机 · 不主动上传服务器" in JS


def test_history_status_labels_are_four():
    for s in ("完整", "未完成", "输入待修正", "规则待确认"):
        assert s in JS


def test_three_archive_actions_exist():
    for s in ("编辑档案信息", "复制为新计算", "删除记录"):
        assert s in JS
```

- [ ] **Step 2: 写实现**

1. 历史列表按 `academicYear` 倒序，每行：学年、年级、总分（`status !== 'complete'` 显示 `—`）、等级、状态标签四选一、三个操作按钮。
2. 删除：`confirm` 用上面原文 → `archives.remove(id)`；`ok:false` 显示它给的「删除失败，原记录已保留」。
3. 复制为新计算：`confirm` 用上面原文 → `duplicateAsNew(id)` → 打开档案浮层要求填学年；失败显示「复制失败，原暂存与存档已保留」。
4. 编辑档案信息：只动资料字段，不动成绩；标题用「编辑档案信息」，从计算页保存进来时标题是「保存本次记录」。
5. 浮层六个资料字段按 §契约 命名，学年必填，空则显示「请填写学年」并停在浮层不写盘。
6. 「一次性资料 · 仅保存本条记录，不更新常用资料」勾选时只写 `archives`，不写常用资料；「清空本次资料」清六个字段但不动已算成绩；取消丢弃本次改动。
7. 姓名/学院/专业只进存档对象：任何复制文本、打印、URL、分享文案里不得出现这三项。

- [ ] **Step 3: 跑到通过 + 浏览器实测**

Run: `cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest tools.test_tice_render -v 2>&1 | tail -3`
Expected: 全绿。

浏览器：存两条同学年，确认是按他的规则替换还是并列——照他行为，若替换需在浮层里说明；姓名填「测试甲」，保存后用页面复制出口取文本，粘贴内容里搜不到「测试甲」；删一条走二次确认；刷新后历史仍在；学年留空点保存，浮层不关且提示「请填写学年」。

- [ ] **Step 4: 提交**

```bash
cd <仓库根目录> && git add web-next/tice.js web-next/tice.css tools/test_tice_render.py && git commit -q -m "feat(tice): 历史区与档案编辑浮层"
```

---

## Task 11: 声明区、两种空态与存储降级

**Files:**
- Modify: `web-next/tice.js`, `web-next/tice.css`
- Test: `tools/test_tice_render.py`（追加）

- [ ] **Step 1: 追加失败测试**

```python
def test_declaration_has_three_blocks():
    for t in ("不会主动上传至服务器", "请勿作为唯一成绩凭证", "教体艺〔2014〕5号"):
        assert t in JS, f"声明区缺 {t}"


def test_two_empty_states_are_distinct():
    assert "还没有本机存档，算完一次可保存" in JS
    assert "本机存储不可用" in JS


def test_policy_scope_qualifier_is_kept():
    assert "2024级本科生起施行" in JS


def test_provenance_sha_is_rendered_from_meta():
    assert "sourceSha256" in JS and "verifiedDate" in JS
```

- [ ] **Step 2: 写实现**

声明区三段，全部从 `meta`/数据取，不硬编码数字：

1. 来源与核验：`standardName` + `standardDocNo`、`schoolPolicyName` + `schoolPolicyDocNo`、`policyEffectiveScope`（保留「自2024级本科生起施行」原话）、`verifiedDate`、`sourceSha256` 前 8 位、加一句「评分表由传承核对人逐项核对」。
2. 本机存储：逐字搬他那句「本次记录仅写入当前设备的本地存储，本项目不会主动上传至服务器。」
3. 失效风险：同一句的后半「清除微信/小程序数据、更换设备或重新安装微信等情况下，记录可能丢失，请勿作为唯一成绩凭证。」——**把「微信/小程序」改成本页对应说法**（清除浏览器数据、更换设备或重装浏览器），因为承载介质不同；其余限定词一字不动。

空态两支：无存档 → 「还没有本机存档，算完一次可保存」；`available === false` → 「本机存储不可用」+ 一句原因，并隐藏保存/历史入口，只留算分与小字。两文案不得复用同一句。

- [ ] **Step 3: 跑到通过 + 手工核窄屏、夜间、键盘**

Run: `cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_tice*.py" 2>&1 | tail -3`
Expected: 全绿。

手工：375px 窄屏走完七项 + 保存 + 历史；`data-theme="cobalt-dark"` 下结果卡与小字能读；只用 Tab + 空格完成填表、保存与两个二次确认；长跑只填分不填秒时的错误落在那一格；隐私模式（或把 localStorage 屏蔽）下页面仍能算分且历史区显示「本机存储不可用」。

- [ ] **Step 4: 提交**

```bash
cd <仓库根目录> && git add web-next/tice.js web-next/tice.css tools/test_tice_render.py && git commit -q -m "feat(tice): 声明区、两种空态与存储不可用降级"
```

---

## Task 12: 全量回归与发布记录

**Files:**
- Modify: `release-notes.md`, `README.md`

- [ ] **Step 1: 全量回归（两段式，见 Global Constraint 13）**

甲、可被 `discover` 收集的 unittest 风格：

```bash
cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_field*.py" 2>&1 | tail -3
cd <仓库根目录> && "./.venv/Scripts/python.exe" -m unittest discover -s tools -p "test_tice*.py" 2>&1 | tail -3
```
Expected: `test_field*.py` 相对 Task 0 的 136 项只多不减；`test_tice*.py` 全绿。若 `test_only_the_expected_files_were_added` 因外来的 `ticket.html` 仍红，照 Global Constraint 12 记为「非本计划所致」并单独列出，不许为凑绿把它加进名单。

乙、脚本风格（末尾无条件 `sys.exit`，`discover` 收不了，只能逐个直跑）：

```bash
cd <仓库根目录> && for f in tools/test_*.py; do case "$f" in *test_field*|*test_tice*) continue;; esac; "./.venv/Scripts/python.exe" "$f" >/dev/null 2>&1; rc=$?; echo "$(basename "$f") exit=$rc"; done
```
Expected: 逐行 `exit=0`。**必须写 `rc=$?` 再打印**：`echo "$(basename $f) exit=$?"` 里的命令替换会先把 `$?` 重新绑成 `basename` 的退出码（实测 `false` 之后仍打出 `exit=0`），那样这半扇门永远报绿。已知的 `test_routing_transfer.py` 2 项待裁决期望若仍红，照实记录为既有噪声，不算回归，也不许顺手修。绝不使用 `-p "test_*.py"` 的单条命令当门——那 16 个脚本风格文件被 `discover` 导入时必然 `ImportError: SystemExit`，与本项目无关。

- [ ] **Step 2: Node 侧两个脚本再跑一次**

Run: `cd <仓库根目录> && node tools/test_tice_calc.js && node tools/test_tice_store.js; echo "exit=$?"`
Expected: 两个脚本各自打印通过行，`exit=0`。

- [ ] **Step 3: 复核数字并写 release-notes**

同句给等式，不裸报数：

1. 阈值 `24 张 × 20 槽 = 480 槽 − 10 null = 470 个数`，null 全在引体向上两个年级组的第 5/7/9/11/13 槽。
2. `tice-standard.json` 的 `derivedAt` 与 `meta.sourceSha256`（记 Task 1 打印的 16 位前缀），并写明评分表由传承核对人逐项核对。
3. 文件变化按实际清点写，用命令取数而不是照抄本段：
```bash
cd <仓库根目录> && git diff --name-status $(git rev-list --max-parents=0 HEAD) HEAD | sort | awk '{print $1, $2}'
```
预期落点是 `A 14`（web-next 7 个：`tice.html` `tice.css` `tice.js` `tice-calc.js` `tice-checks.js` `tice-store.js` `tice-standard.json`；tools 7 个：`tice_bundle.js` `tice_build_json.js` `test_tice.py` `test_tice_render.py` `test_tice_calc.js` `test_tice_store.js` `test_tice_privacy.js`）与 `M` 若干（`field.html`、`tools/test_field_ui.py`、`.gitignore`、`release-notes.md`、`README.md`）。命令输出与预期不符时，以命令输出为准写进 release-notes，并把差异原因记在同一段里，不要为了对上数字去补文件。

- [ ] **Step 3.5: 对外发布前的脱敏门**

仅当本次交付要推到本机以外的公开位置（远端仓库、创空间、任何他人可读的地方）时执行；只在本地提交则记录结果后跳过。

先取数，不猜：

```bash
cd <仓库根目录> && git ls-files -z docs/superpowers web-next tools release-notes.md README.md \
| xargs -0 -I{} sh -c 'grep -c -E "<盘符绝对路径>|<本机账号名>|智能体节" "{}" 2>/dev/null | { read n; [ "$n" -gt 0 ] && echo "$n {}"; }' \
| sort -rn
```

Expected: 打印「命中行数 文件」清单。清单非空即未过门，逐文件处理：

1. `docs/superpowers/**` 里的绝对路径改成仓库相对（`web-next/tice-calc.js:12` 这种形式），临时解包目录（`<本机临时解包目录>`）改成「本机临时目录下的解包工作区」这类不带账号名的说法；实测数字、SHA、结论一律原样保留，只改路径写法。
2. `web-next/**`、`tools/**` 里若命中本机账号名或盘符路径，说明代码里硬编了本机位置，改成相对路径或环境变量；不许用注释遮掩。
3. 处理完重跑同一条命令，Expected: 无输出（退出码非 0 是 `grep` 的正常「查无此物」，不是错误）。
4. 另跑一次 `git log -p --all | grep -c -E "<本机用户目录>|<仓库根目录>"`：历史里仍命中就说明只改了工作树，公开前必须改用全新分支/仓库 squash 导出，或向本人请示后重写历史——不许自作主张 `filter-branch`。

账号名与主机名还出现在 `.git/config`、commit 作者字段里：作者字段按 Global Constraint 10 的 `-c` 前缀走 `noreply@local`，发布前用 `git log --format='%an <%ae>' | sort -u` 核一遍只有那一个身份。

- [ ] **Step 4: 从 `/field` 走完整入口链**

打开 `/field`，确认顶栏「体测」在日夜开关左边、点击进 `/tice.html`、页内「返回广院通」能回来、日夜开关仍在顶栏最末。

- [ ] **Step 5: 提交**

```bash
cd <仓库根目录> && git add release-notes.md README.md && git commit -q -m "docs(tice): 发布说明与功能清单"
```
