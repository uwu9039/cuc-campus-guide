# 广院通宣传片 · 设计 spec（video-shotcraft 自主自由创作）

流水线：`dsh-skills:video-shotcraft/references/pipeline.md` 阶段 0–7。
本文是阶段 0–3 的执行记录（自主自由创作：Agent 定案并留理由，不逐阶段等确认）。
工程：`video-remotion/`（复用已装好的 remotion 4.0.537 + react 19，新合成注册为 `CucPromo`）。

## 阶段 0 · 产品简报

- 产品：广院通 · 校园办事向导（中国传媒大学，2026 首届智能体节 管理类 参赛）。
- 一句话：学生问一句「校园卡丢了怎么补」，它不只回答，而是给出一张能打印带走的单子——时间线、材料清单、文书草稿。
- 核心主张（设计文档原话）：**答案的每一句事实，都必须能点回官方原文**。每条事实带 `quote`，且 `quote` 必须是官方原文的逐字子串，`tools/check_quotes.py` 不一致就退出码 1。
- 必须展示的功能（阶段 2 逐条对镜头）：提问输入与预设胶囊 / 答案卡只答被问的那一面 / 条目档案四页签 概览·材料·流程·原文 / 逐字原文引文与检索标字 / 材料清单核对与拍照核对 / 复制清单与打印 / 真底图校园地图 / 规模数字 39222 事项 · 42237 引文 · 0 条缺证 / 答不上来就直说 / 日夜两套主题。
- 受众与用途：评委与校内学生，比赛提交 + 社媒传播。
- 规格：1920×1080 / 30fps / 简体中文 + 产品自带的英文大写词表 / 目标 48–56s。
- 用户硬约束：「越炫酷越好，不用管 token 开销」→ 能量取全片高档、允许卡拍强节奏；成本不设限。

### 需求到执行决策表

| 需求 | 决策 | 依据与代价 |
|---|---|---|
| 无 npm/npx/pnpm | 复用 `video-remotion/` 依赖，不新建工程 | 装不了包；`three`/`@react-three/fiber`/`@remotion/three`/`@remotion/motion-blur` 全部不可用 → 排除依赖它们的镜头卡，2.5D 运镜走 PageCam 的 CSS 路径 |
| capture 模板要 puppeteer | 自写采集：Edge headless `--force-device-scale-factor=2` 出全页 2x 纹理 + browser-use `evaluate_script` 出 layout.json + ffmpeg 按 bbox×2 裁元素切片 | 无 puppeteer；等效产出三件套，代价是透明底抠图改为从整页裁切（切片自带页面底色，回贴同底色无接缝） |
| Freesound 无 API token | SFX 全部本地合成（numpy 确定性生成 air/whoosh/impact/sub 四类），并记录为偏离项 | 与阶段 6「从 Freesound 选材」不符，属必要偏离；质感靠 BGM + 混响空间补偿。用户若给 token，SFX 可整批重做 |
| 强节奏诉求 | 用库内 BGM `bgm-tech-house.mp3`（Mixkit 免署名可商用，标注 BPM ~124），开工即做节奏网格 | 需自写 numpy 网格拟合（无 librosa），瞬态覆盖率验收后才分镜；交付带 BGM / 无 BGM 两版 |
| 页面数据口径 | 公开官方事实与官方公开电话邮箱保留不打码；不出现任何学生个人信息；`faculty.json` 无路由不入镜 | README 第 229 行既有发布政策 |
| 旧片资产 | `dist/demo-guangyuantong.mp4` 的深色舞台 + 朱红 `#e0483a` 视觉不沿用 | 与现行钴蓝界面不一致；旧截图按新界面重拍 |

## 阶段 1 · 视觉方向

### 三个候选方向（文字）

A. **钴蓝场（亮场主导）**：白底 + 产品自带的三颗同色实心圆融成的场，大字从蓝块破出。优点是还原主界面，缺点是亮场做不出「炫酷」的光感层次。
B. **核验高亮（本片选定）**：把产品自己的检索标字色——浅底金 `#ffe9a3` / 暗底金 `#4a3f14`+`#ffdf7e`——提成全片主角：一束金底从左到右扫过文字，扫过的字就变成可点开的官方原文。日夜两套主题（`cobalt-field` / `cobalt-dark`，产品真实存在的开关）当作能量落差工具：暗场开场→高亮扫进亮场办事→压回暗场砸字标。
C. **印刷单据**：纸面、清单勾选、盖章收尾。叙事最贴「能打印带走的单子」，但能量偏低，与「越炫酷越好」冲突。

**选定 B，理由**：唯一从产品自身生长、且产品里已存在、 yet 没被任何一版旧片用过的视觉资产是那个金底标字（`field.css:23` `--hit-bg`）。它同时就是本片的叙事主张——逐字核验。日夜翻转是产品顶栏那个真实开关，当转场不算另造皮肤。
**取舍（写进 spec 的偏离理由）**：全片放弃粒子/泛光群发（技能硬规则），冲击力改由 大字动效 + 2.5D 页面运镜 + 卡拍转场 承担；暗场光效只允许单点高质量（主角卡边缘那一束），不群发。

### 设计 tokens（全部来自产品，见 `web-next/field.css`）

- 色：`#2b5bff` 钴蓝（日间强调）/ `#6e8bff`（夜间强调）/ `#ffffff` 底 / `#f7f7f4` 表面 / `#111111` 墨 / `#5a5a5a` 弱文 / `#e3e3de` 线 / `#0e0f12` 夜底 / `#16181d` 夜表面 / `#ffe9a3`+`#211a05` 金底标字（浅档）/ `#4a3f14`+`#ffdf7e` 金底标字（暗档）/ `#a8452f` 警示。
- 字：展示 `Arial Narrow, Helvetica Neue, Impact, Microsoft YaHei`（大写、字距 −.05em、字重 800，hero 上限 132px）；正文 `Inter, Segoe UI, Microsoft YaHei`，行高 1.62。
- 形：面板圆角 24px / 胶囊 999px / 面板内边距 `clamp(20px,3vw,40px)` / 顶栏保留 84px。
- 缓动（产品自带两条）：`--reel-ease cubic-bezier(.76,0,.24,1)`（词表滚动＝快速进出）/ `--land-ease cubic-bezier(.2,.8,.2,1)`（落位）。

### 品牌→动效参数

能量轴偏高（大字、快切、强节奏）× 调性轴中性偏严肃（官方办事、可信）→ 取「活力大胆」与「专业信赖」之间：

- 主时长 18–21f@30fps；破出场/字标砸落用 `bezier(0.16,1,0.3,1)`（y1>1，落地必弹，判例赢）；淡入推移用 `bezier(0,0,0.2,1)` 不弹。
- squash 0.2 只给收尾字标；高亮扫过用产品的 `--land-ease`。
- hold/rest 帧预算：字标落定 ≥30f；批量动效收尾 15f 静止；开场主体动作 ≥3s。全片留 ≥1 段近静音静止。
- 自检：三个词描述成片=「锐利 / 逐字 / 强拍」，与品牌词「有求必应 + 条条能查」对得上；入场·转场·hold 三处共用同一套 tokens。

### styleframe

`styleframe/f1-open.html`（暗场开场）、`f2-verified.html`（亮场办事 + 金底高亮主角）、`f3-end.html`（暗场砸字标），各 1920×1080，Edge headless 截图验字体/色板/材质/构图/信息密度。缓动与运镜速度不在此阶段验（仍以 tokens 与 Gallery 样片判断）。

## 阶段 2 · 功能到镜头映射

扫描来源：`references/shots/` 全部卡 frontmatter + `gallery/api/library.json` 索引校验 + `demos/` 源码依赖逐张核对（由 shot-scout 只读调研，20 个卡名全部命中索引）。

| 能力 | 首选卡 | style-key | demo TSX | 备选 |
|---|---|---|---|---|
| 开场字标+主张 | lead-word-zoom-assemble | 同名 | `demos/typography/lead-word-zoom-assemble/LeadWordZoomAssemble.tsx` | outline-word-fill |
| 主张重锤（金底填充） | outline-word-fill | 同名 | `demos/typography/outline-word-fill/` | — |
| 提问打字+胶囊点击 | type-and-filter | 同名 | `demos/interaction/type-and-filter/TypeAndFilter.tsx` | glass-pill-dictation-typing |
| 答案聚焦急推 | crash-zoom-punch | 同名 | `demos/camera/crash-zoom-punch/CrashImpactReal.tsx`（撞停款，全片 ≤2 次） | jump-cut-punch-in |
| 四页签+行嵌入 | row-embed | 同名 | `demos/ui-entrance/row-embed/RowEmbed.tsx` | pill-chip-slot-cycle-handled |
| 逐字原文（本片签名） | document-typewriter-reveal | 同名 | `demos/ui-entrance/document-typewriter-reveal/DocumentTypewriterReveal.tsx` | scan-bracket-sweep |
| 材料清单/缺件 | product-card-progressive-assemble | 同名 | `demos/ui-entrance/product-card-progressive-assemble/ProductCardProgressiveAssemble.tsx` | chip-grid-single-select-blackout |
| 拍照核对 | scan-bracket-sweep | 同名 | `demos/ui-entrance/scan-bracket-sweep/` | — |
| 校园地图 | integration-hub-map | 同名 | `demos/ui-entrance/integration-hub-map/IntegrationHubMap.tsx` | circle-match-iris |
| 拒答（查不到就直说） | jump-cut-punch-in | jump-cut-punch-in | `demos/camera/.../`（三级跳切） | — |
| 规模数字 | gauge-readout-moves（B 式） | tape-scroll-fixed-pointer | `demos/data/gauge-readout-moves/TapeScrollFixedPointer.tsx` + `assets/lib/DigitRoll.tsx` | A 式 needle-sweep-selftest |
| 交付物打印 | riso-print-hits | misregistration-hit | `demos/effects/riso-print-hits/` | ink-bleed-reveal |
| 日夜翻转（倒数第二转场） | palette-theme-ripple | palette-theme-ripple | `demos/.../theme-switch-moves/` | theme-sweep-toggle |
| 收尾合影+字标砸落 | outro-group-photo-launch | 同名 | `demos/outro/outro-group-photo-launch/OutroGroupPhotoLaunch.tsx` | logo-shrink-wordmark-lockup |

组件 copy 清单（依赖已逐张核对为纯 remotion/react）：`assets/lib/PageCam.tsx`、`ClipCard.tsx`、`DigitRoll.tsx`、`FlashCut.tsx`、`Caption.tsx`、`VerticalTicker.tsx`、`helpers/{motion,rand,shake}.ts`，外加 `demos/_fixtures/PageCam2D.tsx`（row-embed / type-and-filter / outro 依赖它）。
**不可用**：`assets/lib/FlatPanel.tsx`（import three）、`helpers/camera.tsx`（@react-three/fiber）、以及所有 `import '@remotion/motion-blur'` 的 demo（crane-rise-reveal、fracture、magician-card-flourish、drone-dive-landing、speed-ramp-freeze、`_legacy/SpeedRampReal`、`_legacy/WhipPanReal`）。急推/鞭甩的快门模糊改走库内已验证的 CSS 单向拖影写法（`cursor-flyover` 的 SpeedBlur amount 0.09、上限 8px）。
**风险记录**：`gallery/media/` 本地 0 个 mp4（仅 54 张 poster），故本片不得声称已对照动态样片；实现依据是配方卡全文 + 准确 demo TSX，动态样片对照列为未验证项。

## 阶段 3 · 分镜与帧级时间轴

### 音乐先行结论（先于分镜，已做完）

`analysis/beat_analysis.py` 用 numpy STFT 频谱通量 + 最小二乘网格拟合 + 打击成分瞬态覆盖率，对库内 5 首 BGM 各测 0.5x/1x/2x 候选网格：

| 曲子 | 获胜 BPM | match | mean_abs | drift | 判定 |
|---|---|---|---|---|---|
| bgm-tech-house | 61.52 | 52.2% | 14.66ms | 3.19ms | FAIL |
| cat-walk | 73.81 | 54.6% | 15.41ms | 5.08ms | FAIL |
| g-eazy-nba-type | 172.34 | 52.0% | 15.89ms | 0.42ms | FAIL |
| house-vibez | 123.09 | 55.3% | 15.46ms | 4.13ms | FAIL |
| tonight-hiphop | 69.86 | 58.0% | 15.83ms | 17.46ms | FAIL |

门槛是 match ≥98% / mean <10ms / drift <5ms（`music-beat-sync.md` §3），最好的一首也只有 58%。lift 中位数 5.5 说明拍位上确实有强瞬态，但瞬态定位精度与反拍基线估计达不到审计要求——根因是本机 Python 3.15 无 librosa/scipy 轮子，自写的 onset 检测与 median 基线替代不了 `beat_track + hpss`。
**决定**：本片不做卡拍。按流水线「未指定 BGM」分支走内容节奏，音轨用 SFX-only（已验收模板片 Ink Press 就是 SFX-only），时间线用帧号而非 `beatF()`。若日后要卡拍版，需先在有 librosa 的环境里把网格测到验收通过。

### 分镜表（30fps，1920×1080，总 1612f = 53.7s）

| # | from | dur | 镜头卡 | 画面 | 主动效（每镜只一个） | 转场 carry |
|---|---|---|---|---|---|---|
| S0 | 0 | 84 | lead-word-zoom-assemble | 暗场 `#0e0f12`，「校园事务」首词 2.3× 占屏收束成整句 | 字距收束 + 末 12f crash 交棒 | 首词蓝块 morphRect 成 S1 底 |
| S1 | 84 | 66 | outline-word-fill | 「有求必应」描边字按帧硬切填充为产品金底 | 按帧硬切 `frame>=POP`（不可渐变） | 金面撑满→zoomThrough 进页面 |
| S2 | 150 | 108 | type-and-filter | 真实 `/field` hero（PageCam 2.5D），输入框打「校园卡丢了怎么补」，点预设胶囊 | 3f/字符打字 + 双圈 ripple 点击 | 输入行上移接 S3 |
| S3 | 258 | 90 | crash-zoom-punch 撞停 | 一拍按到答案卡「校园卡补卡」大标题（4x 高清纹理槽位） | 撞停（全画面级冲击 1/3） | 撞停落位即 S4 面板上沿 |
| S4 | 348 | 78 | row-embed | 条目档案 概览 页签，地点/费用/时长/渠道四行 rotateX 收平嵌入真实槽位 | 行逐条嵌入 + 底边强调色缝裁进圆角 | 最后一行落地接 S5 首行 |
| S5 | 426 | 150 | document-typewriter-reveal | 「原文 4」页签，逐块揭示引文，单一 caret，底块 multiply 金底 | 逐字核验高亮扫过（本片签名） | caret 停在末字→S6 静止 |
| S6 | 576 | 60 | 字卡（呼吸位） | 近静音：白底一行「周二 14:30–16:30 · 艺术与传播大楼 1 层」 | 无动效，仅 15f 静止 hold | 纸面翻成 S7 |
| S7 | 636 | 120 | product-card-progressive-assemble | 材料清单逐字段抓取，缺件位灰色骨架条 | 光标逐字段填 + 缺件一眼可见 | 清单卡缩成 S8 取景框 |
| S8 | 756 | 90 | scan-bracket-sweep | 拍照核对：取景括号收拢 + 扫描线过 | 括号收拢 + 扫描核对 | 扫描线擦出 S9 地图 |
| S9 | 846 | 120 | integration-hub-map | 真底图翻开，POI 图标同帧 → +10f 光管连线同帧（两拍制） | 两拍制点亮 | 地图缩为 S10 的卡片 |
| S10 | 966 | 45 | jump-cut-punch-in | 三级跳切到灰卡「官方没写这条 · 我不编」（`--warn-ink #a8452f`） | 三连跳切（bare cut 只在此处） | 跳切末帧黑闪接数字 |
| S11 | 1011 | 150 | tape-scroll-fixed-pointer + DigitRoll | 39222 / 42237 慢爬→断上限→冲刺→spring 刹车过冲；0 条缺证错峰自检 | 世界动针不动（全画面级冲击 2/3 在断上限） | 数字行归位成 S12 纸面抬头 |
| S12 | 1161 | 120 | riso-print-hits (misregistration-hit) | 双版油墨套准，「啪」印出一张能带走的单子 | 套准单发（全画面级冲击 3/3） | 纸被抽出→元素合影散开 |
| S13 | 1281 | 156 | palette-theme-ripple | 顶栏日夜开关按下，亮场整页 ripple 翻成 cobalt-dark | 主题翻作为倒数第二转场 | 暗场即 S14 舞台 |
| S14 | 1437 | 175 | outro-group-photo-launch | 9 个元素四方飞入围住字标，「广院通」letterpress 逐字砸落 + 30f hold | 合影组装 + 字标砸落 | 落定后静止收黑 |

帧预算核对：字标落定 hold 30f（S14 尾）+ S1 前 12f crash + S3 前 30f 后 45f + S6 整段 60f 近静 + 每段批量动效收尾 15f。全画面级冲击 3 处（S3 撞停、S11 断上限、S12 套准），相邻间隔 ≥16 拍等效（≥250f），符合审美准则 R4。

### 每镜验收帧号（阶段 5 逐条跑 `remotion still`）

S0 f30/f70 · S1 f100/f145 · S2 f210/f250 · S3 f290/f340 · S4 f380/f420 · S5 f480/f560 · S6 f600 · S7 f680/f750 · S8 f790/f840 · S9 f880/f960 · S10 f985/f1005 · S11 f1080/f1150 · S12 f1200/f1275 · S13 f1330/f1430 · S14 f1500/f1600

## 阶段 4 · 采集清单（分镜放行后才跑）

页面状态：`/field` hero 空态、输入中、`?q=校园卡丢了怎么补` 答后态、原文页签展开、材料清单、拍照核对、地图面板、拒答态（用一条官方没写的问题）、打印预览。每态出全页 2x 纹理 + 元素切片 + layout.json；关键特写（S3 答案卡标题）另出 4x。

