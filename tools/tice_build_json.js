const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { readSource, readSourceBuffer, parseDefs, makeLoader, SRC } = require('./tice_bundle.js');

const src = readSource();
// 哈希读的是字节（readSourceBuffer），不是解码后的文本，且打完整 64 位——16 位截断串对不上 sha256sum。
const sourceSha256 = crypto.createHash('sha256').update(readSourceBuffer()).digest('hex');
console.log('source %s', SRC);
console.log('sha256 %s', sourceSha256);
const { load } = makeLoader(parseDefs(src));
const S = load('data/fitness-standard.js');

// 写出路径按 __dirname 解析：换个工作目录跑，产物还在同一个地方（复核 Minor 9）。
const OUT = path.join(__dirname, '..', 'web-next', 'tice-standard.json');
// derivedAt 是本机 UTC 日期，UTC+8 上每天早上 8 点翻一次，「重跑必然字节相同」只在当天成立。
// 要跨天稳定就用 TICE_DERIVED_AT=YYYY-MM-DD 钉住；这个字段是时间戳不是数据，测试里不许断言它。
const derivedAt = process.env.TICE_DERIVED_AT || new Date().toISOString().slice(0, 10);
if (!/^\d{4}-\d{2}-\d{2}$/.test(derivedAt)) {
  throw new Error(`derivedAt 要是 YYYY-MM-DD（TICE_DERIVED_AT 给错了？），实得 ${derivedAt}`);
}

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
if (!nonBmi.length) throw new Error(`收集到 ${all.length} 个节点，其中没有一张非 bmi 表，阶梯无从反推`);
const scoreLadder = ladderOf(nonBmi[0]);
nonBmi.forEach((e) => {
  if (JSON.stringify(ladderOf(e)) !== JSON.stringify(scoreLadder)) {
    throw new Error(`${e.eventKey}/${e.gender}/${e.gradeGroup} 的分值阶梯与首表不一致`);
  }
});

const events = {};
let tableCount = 0;                       // 真正写进去的 (事件, 性别, 年级组) 表数，见复核 Minor 14
nonBmi.forEach((e) => {
  const k = e.eventKey;
  events[k] = events[k] || {
    name: e.eventName, tableCode: e.tableCode, unit: e.unit, unitLabel: e.unitLabel,
    direction: e.direction, scale: e.precision.scale, decimalPlaces: e.precision.decimalPlaces,
    // 模块的事件定义里没有 unitType 这个属性（实读 keys 见复核 Critical 1），照抄 e.unitType 会拿到
    // undefined，JSON.stringify 再把它静默丢掉——契约字段就这么没了。按已有的 unit/unitLabel 判定：
    // 分·秒 的长跑存总秒，输入是 3'17" 这种串，必须靠 unitType 走 mmss 解析。
    unitType: (e.unit === 's' && e.unitLabel === '分·秒') ? 'mmss' : 'number',
    weightPercent: e.weightPercent, bonusEligible: !!e.bonusEligible,
    // 回源轮（2026-11-09）补四个数据驱动的语义字段，代码里不内嵌 switch：
    // integerOnly —— 整数项收到小数要拒（must_be_integer）。
    // belowMinimumRuleStatus —— 低于最低档是 0 分（zero_score），不是 invalid。
    // allowZero / allowNegative —— 原程序 C() 的符号闸逐事件写死，但数据里 precision 已声明，
    //   取数据这一份：两者皆 false → sign<=0 报 must_be_greater_than_zero；
    //   只禁负数 → sign<0 报 negative_not_allowed。
    integerOnly: !!e.precision.integerOnly,
    belowMinimumRuleStatus: e.belowMinimumRuleStatus,
    allowZero: !!e.precision.allowZero,
    allowNegative: !!e.precision.allowNegative,
    bonusDeltas: e.bonusEligible ? e.bonusTable.map((t) => (
      e.direction === 'higher_is_better'
        ? { bonusScore: t.bonusScore, delta: t.deltaThreshold }
        : { bonusScore: t.bonusScore, reductionSeconds: t.reductionSeconds })) : null,
    thresholds: {},
  };
  const t = events[k];
  if (t.name !== e.eventName || t.direction !== e.direction || t.bonusEligible !== !!e.bonusEligible
      || t.integerOnly !== !!e.precision.integerOnly
      || t.belowMinimumRuleStatus !== e.belowMinimumRuleStatus
      || t.allowZero !== !!e.precision.allowZero
      || t.allowNegative !== !!e.precision.allowNegative) {
    throw new Error(`${k} 在不同 性别/年级组 下定义不一致`);
  }
  t.thresholds[e.gender] = t.thresholds[e.gender] || {};
  // 防 last-write-wins（复核 Important 6）：同一 (事件, 性别, 年级组) 出现第二张表就抛，
  // 否则静默覆盖后 flat 按格子计数仍然凑得出 24，谁也发现不了少了一张表。
  if (t.thresholds[e.gender][e.gradeGroup]) {
    throw new Error(`${k}/${e.gender}/${e.gradeGroup} 出现第二张表，拒绝静默覆盖`);
  }
  t.thresholds[e.gender][e.gradeGroup] = e.rawTableRows.map((r) => r.threshold);
  tableCount += 1;
});
Object.values(events).forEach((t) => { t.genders = Object.keys(t.thresholds).sort(); });

const bmi = S.BMI_CATEGORIES_BY_GENDER;
// BMI 的输入符号策略不在 BMI_CATEGORIES_BY_GENDER 里，在它自己那张事件节点的 precision 上。
const bmiNode = all.find((e) => e.direction === 'bmi_category');
if (!bmiNode) throw new Error('收集到的节点里没有 bmi_category 表，BMI 的 precision 策略无从取');
// gradeToGroup 的键必须是中文年级标签：下游一律按 STD.gradeToGroup['大一'] 取组别
// （tice-calc.js 取不到就抛 未知年级），而模块内部的 GRADE_TO_GROUP_MAP 键是 freshman/sophomore/…，
// 原样抄过去等于把契约写坏。用同一个包里的 GRADE_LABELS 映射，映射不上就抛，不许静默退回英文键。
const gradeToGroup = Object.fromEntries(Object.entries(S.GRADE_TO_GROUP_MAP).map(([k, v]) => {
  const label = S.GRADE_LABELS && S.GRADE_LABELS[k];
  if (!label) {
    throw new Error(`GRADE_LABELS 里没有 ${k}，gradeToGroup 会退回内部枚举名，下游 '大一' 这类调用直接 未知年级`);
  }
  return [label, v];
}));
const out = {
  meta: {
    standardName: S.STANDARD_VERSION.nationalStandardName,
    standardDocNo: S.STANDARD_VERSION.nationalStandardDocNo,
    schoolPolicyName: S.STANDARD_VERSION.schoolPolicyName,
    schoolPolicyDocNo: S.STANDARD_VERSION.schoolPolicyDocNo,
    policyEffectiveScope: S.STANDARD_VERSION.schoolPolicyEffectiveScope,
    phaseScope: S.STANDARD_VERSION.phaseScope,
    verifiedDate: S.STANDARD_VERSION.verifiedDate,
    derivedAt,
    sourceModule: 'data/fitness-standard.js',
    sourceSha256: sourceSha256.slice(0, 16),
    transcriber: 'tools/tice_build_json.js',
  },
  scoreLadder,
  limits: S.SCORE_LIMITS,
  weights: Object.assign(
    { bmi: bmi.male.weightPercent },
    Object.fromEntries(Object.keys(events).map((k) => [k, events[k].weightPercent]))),
  gradeGroups: S.GRADE_GROUPS,
  gradeToGroup,
  events,
  bmi: {
    unit: bmi.male.unit, unitLabel: bmi.male.unitLabel, scale: bmi.male.scale,
    weightPercent: bmi.male.weightPercent,
    allowZero: !!bmiNode.precision.allowZero, allowNegative: !!bmiNode.precision.allowNegative,
    categoriesByGender: { male: bmi.male.categories, female: bmi.female.categories },
    unresolvedGapsByGender: { male: bmi.male.unresolvedGaps || [], female: bmi.female.unresolvedGaps || [] },
  },
  unresolvedRules: S.UNRESOLVED_POLICY_RULES,
};

const cells = Object.entries(events).flatMap(([ev, e]) => Object.entries(e.thresholds)
  .flatMap(([g, gs]) => Object.entries(gs).map(([gr, arr]) => ({ key: `${ev}/${g}/${gr}`, arr }))));
const flat = cells.map((c) => c.arr);
const slots = flat.reduce((a, x) => a + x.length, 0);
const nulls = flat.reduce((a, x) => a + x.filter((v) => v === null).length, 0);
console.log('arrays %d  slots %d  nulls %d  numbers %d  events %d',
            flat.length, slots, nulls, slots - nulls, Object.keys(events).length);

// 计数只证明「形状像」，不证明「内容对」：下面这几道内容闸才是这份数据能当唯一数据源的理由。
const REQUIRED_EVENT_KEYS = ['name', 'tableCode', 'unit', 'unitLabel', 'direction', 'scale',
  'decimalPlaces', 'unitType', 'genders', 'bonusEligible', 'bonusDeltas', 'thresholds', 'weightPercent',
  'integerOnly', 'belowMinimumRuleStatus', 'allowZero', 'allowNegative'];
Object.entries(events).forEach(([k, e]) => {
  const missing = REQUIRED_EVENT_KEYS.filter((f) => e[f] === undefined);
  if (missing.length) throw new Error(`${k} 缺契约字段 ${missing.join(',')}——JSON.stringify 会静默丢掉 undefined，别让它混过去`);
});
// 回源轮的四个语义字段是**内容**断言，不是形状断言：这几个集合错了，算分会静默变成另一种规则。
const expectIntegerOnly = ['pullUps', 'run1000m', 'run800m', 'sitUps'];
const actualIntegerOnly = Object.keys(events).filter((k) => events[k].integerOnly).sort();
if (JSON.stringify(actualIntegerOnly) !== JSON.stringify(expectIntegerOnly.slice().sort())) {
  throw new Error(`integerOnly 集合不符：实得 ${actualIntegerOnly.join(',')}，应为 ${expectIntegerOnly.join(',')}`);
}
// 符号策略逐事件钉死：原程序 C() 的 switch 与数据 precision 一致，两边任何一处漂移都要在这里红。
const expectAllowZero = ['pullUps', 'sitAndReach', 'sitUps', 'standingLongJump', 'vitalCapacity'];
const expectAllowNegative = ['sitAndReach'];
for (const [field, expect] of [['allowZero', expectAllowZero], ['allowNegative', expectAllowNegative]]) {
  const actual = Object.keys(events).filter((k) => events[k][field]).sort();
  if (JSON.stringify(actual) !== JSON.stringify(expect.slice().sort())) {
    throw new Error(`${field} 集合不符：实得 ${actual.join(',')}，应为 ${expect.join(',')}`);
  }
}
if (out.bmi.allowZero !== false || out.bmi.allowNegative !== false) {
  throw new Error('BMI 的身高体重必须都大于 0（allowZero/allowNegative 皆 false）');
}
Object.entries(events).forEach(([k, e]) => {
  if (e.belowMinimumRuleStatus !== 'zero_score') {
    throw new Error(`${k} 的 belowMinimumRuleStatus 是 ${e.belowMinimumRuleStatus}，低于最低档必须给 0 分（zero_score）`);
  }
});
// all 是递归收集到的节点数（含 4 张 bmi_category 表），从来不是表数；查重后的写入计数才是。
if (tableCount !== 24) {
  throw new Error(`收到 ${tableCount} 张 事件×性别×年级组 表，应为 24（4 项男女共有 × 2 性别 × 2 年级组 = 16，加 4 项单性别项目 × 1 性别 × 2 年级组 = 8）——有表被 last-write-wins 吞了`);
}
// 阶梯必须与模块自己的权威导出一致，不能只跟第一张表对齐：24 张表一起错也是错。
// （计划 Step 2 那句「他没有单独导出 20 档 ladder」不实：模块导出 17 个键，含 STANDARD_SCORE_TIERS。）
const tiers = S.STANDARD_SCORE_TIERS;
if (!Array.isArray(tiers) || tiers.length !== 20) {
  throw new Error(`模块导出的 STANDARD_SCORE_TIERS 不是 20 档（实得 ${tiers && tiers.length}），无法交叉验证阶梯`);
}
if (JSON.stringify(scoreLadder.map((t) => t.score))
  !== JSON.stringify(tiers.map((t) => (t && typeof t === 'object' ? t.score : t)))) {
  throw new Error('反推的分值阶梯与模块导出的 STANDARD_SCORE_TIERS 不一致');
}
if (tiers.every((t) => t && typeof t === 'object' && t.level !== undefined)
  && JSON.stringify(scoreLadder.map((t) => t.level)) !== JSON.stringify(tiers.map((t) => t.level))) {
  throw new Error('反推的等级名（优秀/良好/及格/不及格）与模块导出的 STANDARD_SCORE_TIERS 不一致');
}
cells.forEach(({ key, arr }) => { if (arr.length !== 20) throw new Error(`${key} 表 ${arr.length} 档，应为 20`); });
const nullIdx = (ev, gender, group) => {
  const cell = ((events[ev] || {}).thresholds || {})[gender] || {};
  if (!(group in cell)) throw new Error(`${ev}/${gender}/${group} 这张表根本不存在，null 位置无从校验`);
  return cell[group].map((v, i) => (v === null ? i : -1)).filter((i) => i >= 0);
};
const nullSpec = { 'pullUps/male/grade12': [5, 7, 9, 11, 13], 'pullUps/male/grade34': [5, 7, 9, 11, 13] };
const nullSeen = {};
Object.entries(events).forEach(([ev, e]) => Object.entries(e.thresholds)
  .forEach(([g, gs]) => Object.entries(gs).forEach(([gr, arr]) => {
    const idx = arr.map((v, i) => (v === null ? i : -1)).filter((i) => i >= 0);
    if (idx.length) nullSeen[`${ev}/${g}/${gr}`] = idx;
  })));
if (JSON.stringify(Object.keys(nullSeen).sort()) !== JSON.stringify(Object.keys(nullSpec).sort())
  || Object.entries(nullSpec).some(([k, v]) => JSON.stringify(nullIdx(...k.split('/'))) !== JSON.stringify(v))) {
  throw new Error(`null 位置与 spec 不符：实得 ${JSON.stringify(nullSeen)}，应为 ${JSON.stringify(nullSpec)}`);
}

if (flat.length !== 24 || slots !== 480 || nulls !== 10) {
  throw new Error('派生结果与 spec 实测不符（应为 24 表 / 480 槽 / 10 null），拒绝写出');
}
fs.writeFileSync(OUT, JSON.stringify(out, null, 1) + '\n');
console.log('wrote %s', OUT);
