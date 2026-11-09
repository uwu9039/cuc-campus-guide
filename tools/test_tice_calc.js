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
// 210 的两种形态都是「整数总秒数」：数字 210 与字符串 '210' 走同一分支。原程序
// parseEnduranceTime 实测 '210' → totalSeconds=210 / displayValue=3'30"，'210秒' / '197s'
// 同样接受；只有小数时间（'4.20' / '3.17'）才是 ambiguous_decimal_time_format。
assert.deepStrictEqual(calc.parseEnduranceTime('4:20'), { ok: true, seconds: 260 });
assert.deepStrictEqual(calc.parseEnduranceTime('4:7'),  { ok: true, seconds: 247 });
assert.deepStrictEqual(calc.parseEnduranceTime('4:60'), { ok: false, code: 'invalid_minutes_or_seconds_range' });
assert.deepStrictEqual(calc.parseEnduranceTime('0:00'), { ok: false, code: 'non_positive_time' });
assert.deepStrictEqual(calc.parseEnduranceTime('4.20'), { ok: false, code: 'ambiguous_decimal_time_format' });
assert.deepStrictEqual(calc.parseEnduranceTime('3.17'), { ok: false, code: 'ambiguous_decimal_time_format' });
assert.deepStrictEqual(calc.parseEnduranceTime(210),    { ok: true, seconds: 210 });
assert.deepStrictEqual(calc.parseEnduranceTime('210'),  { ok: true, seconds: 210 });
assert.deepStrictEqual(calc.parseEnduranceTime('210秒'), { ok: true, seconds: 210 });
assert.deepStrictEqual(calc.parseEnduranceTime('197s'), { ok: true, seconds: 197 });
assert.deepStrictEqual(calc.parseEnduranceTime('3:7'),  { ok: true, seconds: 187 });
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

// 三条空值分支各有自己的下游依赖，压成一支就丢语义：
// (1) null / undefined 是「未填」→ incomplete——Task 5 的 assemble 靠它数 filled.length，
//     删掉 isBlank 分支会退化成「0 → invalid」；
// (2) '' / 纯空格是「填错了」→ invalid/empty_string（原程序 validateEventInput 实测）；
// (3) false / [] / {} 是类型错 → invalid/invalid_type。
// 旧断言把 '' 也当 incomplete，等于把三种语义折成一种。
assert.strictEqual(calc.scoreEvent(std, {
  gender: 'male', grade: '大一', eventKey: 'vitalCapacity', raw: null,
}).status, 'incomplete');
assert.strictEqual(calc.scoreEvent(std, {
  gender: 'male', grade: '大一', eventKey: 'vitalCapacity', raw: undefined,
}).status, 'incomplete');
// incomplete 也要带 code 与权重：原程序 error.code='missing_value'、weightPercent 照常给。
// Task 5 的 assemble 数 filled.length 靠 status，Task 9 的「还差哪几项」靠 code 与 name。
for (const raw of [null, undefined]) {
  const r = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'vitalCapacity', raw });
  assert.strictEqual(r.code, 'missing_value', `incomplete 缺 code：${JSON.stringify(raw)}`);
  assert.strictEqual(r.weightPercent, 15);
  assert.strictEqual(r.name, '肺活量');
}
const emptyStr = calc.scoreEvent(std, {
  gender: 'male', grade: '大一', eventKey: 'vitalCapacity', raw: '',
});
assert.strictEqual(emptyStr.status, 'invalid');
assert.strictEqual(emptyStr.code, 'empty_string');
const badType = calc.scoreEvent(std, {
  gender: 'male', grade: '大一', eventKey: 'vitalCapacity', raw: false,
});
assert.strictEqual(badType.status, 'invalid');
assert.strictEqual(badType.code, 'invalid_type');
// 性别不匹配不许静默回退——回退到 byGroup 里第一个性别，就是拿男表给女生算引体向上，
// 这类计算器最常见的错分。原程序 scoreSingleEvent 返回 invalid + code（不抛异常）：
// 抛异常会跳出 spec 的四态，页面还得额外 try/catch。
const wrongGender = calc.scoreEvent(std, {
  gender: 'female', grade: '大一', eventKey: 'pullUps', raw: 8,
});
assert.strictEqual(wrongGender.status, 'invalid');
assert.strictEqual(wrongGender.code, 'unsupported_event_for_gender');
assert.strictEqual(wrongGender.score, null);
// 反向也要拒：男生没有 800 米表
const wrongGender2 = calc.scoreEvent(std, {
  gender: 'male', grade: '大一', eventKey: 'run800m', raw: 200,
});
assert.strictEqual(wrongGender2.status, 'invalid');
assert.strictEqual(wrongGender2.code, 'unsupported_event_for_gender');
// 未知项目名同样走 invalid，且 name/weightPercent 落 null——不许回退成 BMI 的名字与权重，
// 那会把「项目名打错了」显示成「体重指数 15%」。原程序 eventName undefined / weightPercent null。
const unknownEv = calc.scoreEvent(std, {
  gender: 'male', grade: '大一', eventKey: 'noSuchEvent', raw: 1,
});
assert.strictEqual(unknownEv.status, 'invalid');
assert.strictEqual(unknownEv.code, 'unsupported_event_for_gender');
assert.strictEqual(unknownEv.name, null);
assert.strictEqual(unknownEv.weightPercent, null);
// 直接调 scoreLevel / gradeGroupOf 仍抛可读错误：那是给编程错误用的，不是给输入用的。
assert.throws(() => calc.scoreLevel(std, 'pullUps', 'female', 'grade12', 8), /性别不匹配/);
assert.throws(() => calc.gradeGroupOf(std, 'noSuchGrade'), /未知年级/);

// 取位模式本身要钉住：Math.round 换成 floor/trunc 时上面所有用例仍全绿
// （6.72 与 6.75 的 67/68 之差正是 Task 4 判跨档的支点）。
assert.strictEqual(calc.scaleOf(6.75, 10), 68);
assert.strictEqual(calc.scaleOf(6.72, 10), 67);
console.log('边界断言全部通过');

// Task 3 复核 Important 1 的收口：EventResult 必须四路同键，不许再各自拼字面量。
// 这里钉的是「形状」本身——把任何一路改回裸返回、或删掉工厂里的默认键，都会红。
// mmss 路用 '4.20'（小数时间，原程序判 ambiguous_decimal_time_format）；数值路用 'abc'。
// 旧用例的 '210' 已不是 invalid（见上面 parseEnduranceTime），不能拿来测 invalid 形状。
for (const bad of [{ eventKey: 'run1000m', raw: '4.20' }, { eventKey: 'sprint50m', raw: 'abc' }]) {
  const r = calc.scoreEvent(std, { gender: 'male', grade: '大一', ...bad });
  assert.strictEqual(r.status, 'invalid');
  assert.ok(typeof r.code === 'string' && r.code.length, `${bad.eventKey}/${bad.raw} 缺顶层 code`);
  ['weightPercent', 'bonusEligible', 'hint', 'name', 'levelResult'].forEach((k) =>
    assert.ok(k in r, `${bad.eventKey}/${bad.raw} 的 invalid 缺契约键 ${k}`));
}
// 低于最低档不是 invalid：原程序 scoreSingleEvent(sprint50m, 11.1) 实测
// status:'complete' / score:0 / level:'不及格' / matchedThreshold:null（belowMinimum 只是内部标记）。
const bm = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'sprint50m', raw: '11.1' });
assert.strictEqual(bm.status, 'complete');
assert.strictEqual(bm.code, null);
assert.strictEqual(bm.score, 0);
assert.strictEqual(bm.levelResult.status, 'scored');
assert.strictEqual(bm.levelResult.level, '不及格');
assert.strictEqual(bm.levelResult.matchedThreshold, null);

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
// 6.72 同样落在 67 与 68 之间：floor 6.7→100、ceil 6.8→95，两档分数不同 → unresolved。
// 旧断言写「两位取位后同为 67 档 → 放行 100」，那是旧语义（Math.round 取位）。
// 原程序实测 sprint50m 6.72 → unresolved / measurement_precision_rounding_unresolved。
const cross672 = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'sprint50m',
                                        raw: '6.72' });
assert.strictEqual(cross672.status, 'unresolved', '6.72 跨档未被拦：' + cross672.status);
assert.strictEqual(cross672.levelResult.reason, 'measurement_precision_rounding_unresolved');

// ── 金标准对照块（2026-11-09 回源轮）：数值全部抄自 oracle.js 的原程序实测 ──
// (1) 低于最低档 = 0 分，不是 invalid：vitalCapacity 1000
//     oracle: status=complete score=0 level=不及格 matchedThreshold=null
const belowMin = calc.scoreEvent(std, { gender: 'male', grade: '大一',
                                        eventKey: 'vitalCapacity', raw: 1000 });
assert.strictEqual(belowMin.status, 'complete');
assert.strictEqual(belowMin.score, 0);
assert.strictEqual(belowMin.levelResult.level, '不及格');
assert.strictEqual(belowMin.levelResult.matchedThreshold, null);

// (2) 精度闸没有 scale<=1 例外：standingLongJump 272.5 跨 272(95)/273(100) 两档
//     oracle: status=unresolved reason=measurement_precision_rounding_unresolved
const jump2725 = calc.scoreEvent(std, { gender: 'male', grade: '大二',
                                        eventKey: 'standingLongJump', raw: 272.5 });
assert.strictEqual(jump2725.status, 'unresolved');
assert.strictEqual(jump2725.levelResult.reason, 'measurement_precision_rounding_unresolved');

// (3) 同一条精度闸的同档放行对照组（6.72 的跨档已在 cross672 钉住）：
//     vitalCapacity 3500.5 的 floor 3500 / ceil 3501 同为 66 分 → 照常给分。
//     oracle: status=complete score=66
const vc35005 = calc.scoreEvent(std, { gender: 'male', grade: '大一',
                                       eventKey: 'vitalCapacity', raw: 3500.5 });
assert.strictEqual(vc35005.status, 'complete');
assert.strictEqual(vc35005.score, 66);

// (4) 整数项收到小数 → invalid/must_be_integer；'14.0'/'14.00' 余数为 0，正常给分
//     oracle: pullUps 14.5 / '14.5' → invalid(must_be_integer)；'14.0'/'14.00' → complete 76
const pu145 = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'pullUps', raw: 14.5 });
assert.strictEqual(pu145.status, 'invalid');
assert.strictEqual(pu145.code, 'must_be_integer');
for (const raw of ['14.0', '14.00']) {
  const r = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'pullUps', raw });
  assert.strictEqual(r.status, 'complete', `pullUps ${raw} 应 complete，实际 ${r.status}`);
  assert.strictEqual(r.score, 76);
}

// (5) '210' 是整数总秒数，不是非法格式：parseEnduranceTime('210') 已在上方断言；
//     走完整评分链路 run1000m '210' 也要给分。oracle: complete / score=85
const run210 = calc.scoreEvent(std, { gender: 'male', grade: '大一',
                                      eventKey: 'run1000m', raw: '210' });
assert.strictEqual(run210.status, 'complete');
assert.strictEqual(run210.score, 85);

// (6) BMI 不取位，真值与一位小数门槛精确比较；scoreBmi 签名是 (std, gender, heightCm, weightKg)
//     oracle: 100/20.05 → complete 100 正常；100/17.86 → unresolved；100/17.8 → complete 80 低体重；
//             175/95 → complete 60 肥胖
const bmi2005 = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'bmi',
                                       inputs: { heightCm: 100, weightKg: 20.05 } });
assert.strictEqual(bmi2005.status, 'complete');
assert.strictEqual(bmi2005.score, 100);
assert.strictEqual(bmi2005.levelResult.level, '正常');
const bmi1786 = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'bmi',
                                       inputs: { heightCm: 100, weightKg: 17.86 } });
assert.strictEqual(bmi1786.status, 'unresolved');
assert.strictEqual(bmi1786.levelResult.reason, 'bmi_boundary_precision_unresolved');
const bmi178 = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'bmi',
                                      inputs: { heightCm: 100, weightKg: 17.8 } });
assert.strictEqual(bmi178.status, 'complete');
assert.strictEqual(bmi178.score, 80);
assert.strictEqual(bmi178.levelResult.level, '低体重');
assert.strictEqual(calc.scoreBmi.length, 4, 'scoreBmi 签名应为 (std, gender, heightCm, weightKg)');
assert.strictEqual(calc.scoreBmi(std, 'male', 100, 20.05).score, 100);
// (7) 符号闸由数据 allowZero/allowNegative 驱动，不是按项目名内嵌 switch。
//     oracle 实测：50米 0/-1 → must_be_greater_than_zero（两者皆禁）；
//     肺活量/立定跳远/引体向上/仰卧起坐 -1 → negative_not_allowed（禁负不禁零）；
//     坐位体前屈 -5 → complete 0（负值合法，低于最低档给 0 分）。
//     把 allowZero 一律当 false，肺活量 0 会从 complete/0 变成 invalid；
//     把 allowNegative 一律当 false，坐位体前屈 -5 会从 0 分变成需修正。
const signCases = [
  ['sprint50m',        'male',   '0',    'invalid',  'must_be_greater_than_zero', null],
  ['sprint50m',        'male',   '-1',   'invalid',  'must_be_greater_than_zero', null],
  ['vitalCapacity',    'male',   '0',    'complete', null,                        0],
  ['vitalCapacity',    'male',   '-1',   'invalid',  'negative_not_allowed',      null],
  ['standingLongJump', 'male',   '0',    'complete', null,                        0],
  ['standingLongJump', 'male',   '-1',   'invalid',  'negative_not_allowed',      null],
  ['sitAndReach',      'male',   '-5',   'complete', null,                        0],
  ['pullUps',          'male',   '0',    'complete', null,                        0],
  ['pullUps',          'male',   '-1',   'invalid',  'negative_not_allowed',      null],
  ['sitUps',           'female', '0',    'complete', null,                        0],
  ['sitUps',           'female', '-1',   'invalid',  'negative_not_allowed',      null],
];
for (const [ev, g, raw, wantStatus, wantCode, wantScore] of signCases) {
  const r = calc.scoreEvent(std, { gender: g, grade: '大一', eventKey: ev, raw });
  assert.strictEqual(r.status, wantStatus, `${ev} ${raw} status=${r.status} 期望 ${wantStatus}`);
  assert.strictEqual(r.code, wantCode, `${ev} ${raw} code=${r.code} 期望 ${wantCode}`);
  assert.strictEqual(r.score, wantScore, `${ev} ${raw} score=${r.score} 期望 ${wantScore}`);
}
// 符号闸在整数闸之前：原程序 pullUps 先判 sign<0 再判 decimalPlaces>0，
// 所以 '-0.5' 报 negative_not_allowed 而不是 must_be_integer。两道闸调序就会红。
const negFrac = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'pullUps', raw: '-0.5' });
assert.strictEqual(negFrac.code, 'negative_not_allowed');
assert.strictEqual(calc.scoreEvent(std, {
  gender: 'female', grade: '大一', eventKey: 'sitUps', raw: '8.5',
}).code, 'must_be_integer');

// (8) 年级解析的三个错误码各有文案（Task 6 要映射），不能都塞进 invalid_grade。
//     oracle 实测：'2023' → enrollment_year_not_allowed；数字 2023 / 5 →
//     enrollment_year_or_numeric_grade_not_allowed；其余 → invalid_grade。
const gradeCases = [
  ['2023',        'enrollment_year_not_allowed'],
  ['2023级',      'enrollment_year_not_allowed'],
  [2023,          'enrollment_year_or_numeric_grade_not_allowed'],
  [5,             'enrollment_year_or_numeric_grade_not_allowed'],
  ['noSuchGrade', 'invalid_grade'],
  ['',            'invalid_grade'],
  [null,          'invalid_grade'],
];
for (const [grade, wantCode] of gradeCases) {
  const r = calc.scoreEvent(std, { gender: 'male', grade, eventKey: 'vitalCapacity', raw: 4000 });
  assert.strictEqual(r.status, 'invalid', `grade=${JSON.stringify(grade)} status=${r.status}`);
  assert.strictEqual(r.code, wantCode, `grade=${JSON.stringify(grade)} code=${r.code} 期望 ${wantCode}`);
}
// 校验顺序照原程序：性别 → 年级 → 项目。性别与年级同时非法时报 invalid_gender，
// 且 raw 为空也不该被 incomplete 盖过去。
const bothBad = calc.scoreEvent(std, { gender: 'alien', grade: 'noSuchGrade', eventKey: 'vitalCapacity', raw: null });
assert.strictEqual(bothBad.code, 'invalid_gender');
// 性别两端空白要 trim：原程序 ' male ' → complete 74。不 trim 就变 invalid_gender。
const trimmed = calc.scoreEvent(std, { gender: ' male ', grade: '大一', eventKey: 'vitalCapacity', raw: 4000 });
assert.strictEqual(trimmed.status, 'complete');
assert.strictEqual(trimmed.score, 74);
// 组别名直传也接（本项目契约用 grade12/grade34，源包内部用 freshman 等英文枚举——
// 这是唯一一处有意偏离，年级标签本身两边都是中文 UI）。
for (const [group, topRaw] of [['grade12', 5040], ['grade34', 5140]]) {
  const r = calc.scoreEvent(std, { gender: 'male', grade: group, eventKey: 'vitalCapacity', raw: topRaw });
  assert.strictEqual(r.status, 'complete', `组别名 ${group} 应被接受，实际 ${r.status}/${r.code}`);
  assert.strictEqual(r.score, 100);
}

// (9) BMI 逐字段校验，顺序是 height → weight，且「已填但坏」压过「另一项未填」。
//     oracle 实测：(0,'') → must_be_greater_than_zero；('',0) → empty_string；
//     (null,-1) → must_be_greater_than_zero；(null,null) → incomplete/missing_value。
//     先扫一遍 missing 再扫一遍 bad 的写法会把 (0,'') 判成 empty_string。
const bmiOrder = [
  [0,      '',    'invalid',    'must_be_greater_than_zero'],
  ['',     0,     'invalid',    'empty_string'],
  [-1,     null,  'invalid',    'must_be_greater_than_zero'],
  [null,   -1,    'invalid',    'must_be_greater_than_zero'],
  ['abc',  '',    'invalid',    'invalid_number_format'],
  ['',     'abc', 'invalid',    'empty_string'],
  [175,    0,     'invalid',    'must_be_greater_than_zero'],
  [175,    -1,    'invalid',    'must_be_greater_than_zero'],
  [null,   null,  'incomplete', 'missing_value'],
];
for (const [h, w, wantStatus, wantCode] of bmiOrder) {
  const r = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'bmi',
                                   inputs: { heightCm: h, weightKg: w } });
  assert.strictEqual(r.status, wantStatus, `BMI(${JSON.stringify(h)},${JSON.stringify(w)}) status=${r.status} 期望 ${wantStatus}`);
  assert.strictEqual(r.code, wantCode, `BMI(${JSON.stringify(h)},${JSON.stringify(w)}) code=${r.code} 期望 ${wantCode}`);
}
// BMI 的性别也要 trim，且字符串身高体重要能算（输入框给的就是字符串）。
const bmiTrim = calc.scoreEvent(std, { gender: ' male ', grade: '大一', eventKey: 'bmi',
                                       inputs: { heightCm: '175', weightKg: '65.5' } });
assert.strictEqual(bmiTrim.status, 'complete');
assert.strictEqual(bmiTrim.score, 100);
// BMI 权重 15%（Task 4 复核 Mi5）：加权贡献 = round(100*15)/100 = 15。
assert.strictEqual(bmiTrim.weightPercent, 15);
assert.strictEqual(bmiTrim.weightedContribution, 15);
assert.strictEqual(bmiTrim.name, '体重指数（BMI）');
// 肥胖档上界是开区间（null）：BMI 46.88 仍要落肥胖，不能因为 null 比较而漏判。
// JS 里 `46.88 <= null` 是 false、`46.88 >= null` 是 true，用 ±Infinity 或裸比较都会错。
const obese = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'bmi',
                                     inputs: { heightCm: 100, weightKg: 46.88 } });
assert.strictEqual(obese.status, 'complete');
assert.strictEqual(obese.score, 60);
assert.strictEqual(obese.levelResult.level, '肥胖');
// 低体重档下界同样是开区间：13.06 要落低体重 80 分。
const under = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'bmi',
                                     inputs: { heightCm: 100, weightKg: 13.06 } });
assert.strictEqual(under.status, 'complete');
assert.strictEqual(under.score, 80);
assert.strictEqual(under.levelResult.level, '低体重');

console.log(bf ? `bmi ${bf} 条失败` : `bmi ${bmiCases.length} pass + 空隙2 + 跨档2`);

// ── Task 5：加权标准分 / 附加分 / 总分等级 ──
// 期望值全部抄自原程序 calculateFitnessResult / calculateBonus / getTotalScoreGrade 的实测
// （2026-11-09，探针 _extract/probe-task5*.js），**不是抄计划原文**——计划在这一节的期望值
// 与语义共 5 处错（见 task-5-report.md §5），下面每条注释里都标出 oracle 原值。
// 满分基准：男大一 175cm/65.5kg（BMI 21.4→100）/ 肺活量 5040→100 / 50米 6.7→100 /
// 坐位体前屈 24.9→100 / 立定跳远 273→100 / 引体向上 19 次起 100 分 / 1000米 3'17" 起 100 分。
const MALE_FULL = {
  heightCm: 175, weightKg: 65.5, vitalCapacity: 5040, sprint50m: '6.7',
  sitAndReach: '24.9', standingLongJump: 273, pullUps: 21, run1000m: '2\'40"',
};

// (1) 全满分 + 两项附加分：引体 21 次（19 次 100 分，+2）＋ 1000米 2'40"=160 秒（门槛 162，+10）
//     oracle: complete / standardScore=100 / strengthBonus=2 / enduranceBonus=10 /
//             totalBonus=12 / totalScore=112 / gradeCode=excellent / gradeLabel=优秀
const full = calc.assemble(std, { gender: 'male', grade: '大一', answers: MALE_FULL });
assert.strictEqual(full.status, 'complete');
assert.strictEqual(full.standardScore, 100);
assert.strictEqual(full.strengthBonus, 2);
assert.strictEqual(full.enduranceBonus, 10);
assert.strictEqual(full.totalBonus, 12);
assert.strictEqual(full.totalScore, 112);
assert.strictEqual(full.displayTotalScore, '112.0');
assert.strictEqual(full.gradeCode, 'excellent');
assert.strictEqual(full.gradeLabel, '优秀');
assert.deepStrictEqual(full.blockingReasons, []);
assert.strictEqual(full.items.length, 7, '七项都要在场（BMI + 六项）');
assert.ok(full.items.every((r) => r.status === 'complete'));
assert.strictEqual(full.items[0].eventKey, 'bmi');
// 性别两端空白：原程序 calculateFitnessResult 顶层就 trim 了 gender，这里也必须
// 先 trim 再选项目表（不 trim 会拿到女生的 sitUps/run800m 表去套男生的成绩）。
const fullTrimmed = calc.assemble(std, { gender: ' male ', grade: '大一', answers: MALE_FULL });
assert.strictEqual(fullTrimmed.status, 'complete');
assert.strictEqual(fullTrimmed.totalScore, 112);
assert.strictEqual(fullTrimmed.items[5].eventKey, 'pullUps');

// (2) 无附加分：正好压在 100 分档（引体 19 次 / 1000米 3'17"=197 秒）→ 附加分是 0，不是 null
//     oracle: complete / standardScore=100 / bonusScore=0 / totalScore=100
const noBonus = calc.assemble(std, { gender: 'male', grade: '大一',
  answers: Object.assign({}, MALE_FULL, { pullUps: 19, run1000m: '3\'17"' }) });
assert.strictEqual(noBonus.status, 'complete');
assert.strictEqual(noBonus.strengthBonus, 0);
assert.strictEqual(noBonus.enduranceBonus, 0);
assert.strictEqual(noBonus.totalBonus, 0);
assert.strictEqual(noBonus.totalScore, 100);

// (3) 计划原文「只快 10 秒 → +4」是错的：197−10=187 秒只够 189 秒那一档（+2）。
//     附加分档是 −4/−8/−12/−16/−20/−22/−25/−28/−31/−35 秒，不是每 4 秒一档。
//     oracle: scoreSingleEvent(run1000m,187) → bonusScore=2；
//             assemble → enduranceBonus=2 / totalBonus=2 / totalScore=102
assert.strictEqual(calc.parseEnduranceTime('3\'07"').seconds, 187);
assert.strictEqual(calc.computeBonus(std, 'run1000m', 'male', 'grade12', 187).bonusScore, 2);
assert.strictEqual(calc.computeBonus(std, 'run1000m', 'male', 'grade12', 187)
  .matchedTier.scaledAbsoluteThreshold, 189);
const smallRun = calc.assemble(std, { gender: 'male', grade: '大一',
  answers: Object.assign({}, MALE_FULL, { pullUps: 19, run1000m: '3\'07"' }) });
assert.strictEqual(smallRun.enduranceBonus, 2);
assert.strictEqual(smallRun.totalBonus, 2);
assert.strictEqual(smallRun.totalScore, 102);

// (4) 附加分档位与封顶都从 std 读：单项 10（29 次；30 次也只有 10）、总 20
//     oracle: pullUps 21→2 / 29→10 / 30→10；run1000m 193→1、162→10、197→0；
//             29 次 + 2'40" → totalBonus=20 / totalScore=120
assert.strictEqual(calc.computeBonus(std, 'pullUps', 'male', 'grade12', 21).bonusScore, 2);
assert.strictEqual(calc.computeBonus(std, 'pullUps', 'male', 'grade12', 19).bonusScore, 0);
assert.strictEqual(calc.computeBonus(std, 'pullUps', 'male', 'grade12', 29).bonusScore, 10);
assert.strictEqual(calc.computeBonus(std, 'pullUps', 'male', 'grade12', 30).bonusScore, 10);
assert.strictEqual(calc.computeBonus(std, 'run1000m', 'male', 'grade12', 193).bonusScore, 1);
assert.strictEqual(calc.computeBonus(std, 'run1000m', 'male', 'grade12', 162).bonusScore, 10);
assert.strictEqual(calc.computeBonus(std, 'run1000m', 'male', 'grade12', 197).bonusScore, 0);
// 非附加分项恒 0（肺活量满分也没有附加分，原程序 bonusEligible:false）
assert.strictEqual(calc.computeBonus(std, 'vitalCapacity', 'male', 'grade12', 5040).bonusScore, 0);
assert.strictEqual(calc.computeBonus(std, 'bmi', 'male', 'grade12', 21).bonusScore, 0);
const capped = calc.assemble(std, { gender: 'male', grade: '大一',
  answers: Object.assign({}, MALE_FULL, { pullUps: 29, run1000m: 160 }) });
assert.strictEqual(capped.strengthBonus, 10);
assert.strictEqual(capped.enduranceBonus, 10);
assert.strictEqual(capped.totalBonus, 20);
assert.strictEqual(capped.totalScore, 120);

// 上限本身也必须从 std 读：把 maxSingleBonusScore 改成 8，同一个 29 次只给 8。
// （写死字面量 10 的实现会在这里红。）
const stdJson = JSON.parse(fs.readFileSync('web-next/tice-standard.json', 'utf8'));
const looseStd = calc.prepareStandard(Object.assign({}, stdJson, {
  limits: Object.assign({}, stdJson.limits, { maxSingleBonusScore: 8 }) }));
assert.strictEqual(calc.computeBonus(looseStd, 'pullUps', 'male', 'grade12', 29).bonusScore, 8,
  '单项附加分封顶必须读 std.limits.maxSingleBonusScore');

// (5) 单项低于最低档 = 0 分，仍算 complete、仍参与加权（不是 invalid、不是缺项）
//     oracle: vitalCapacity 1000 → singleScore 0；standardScore=85 / totalScore=97
const lowVc = calc.assemble(std, { gender: 'male', grade: '大一',
  answers: Object.assign({}, MALE_FULL, { vitalCapacity: 1000 }) });
assert.strictEqual(lowVc.status, 'complete');
assert.strictEqual(lowVc.items[1].score, 0);
assert.strictEqual(lowVc.items[1].status, 'complete');
assert.strictEqual(lowVc.standardScore, 85);
assert.strictEqual(lowVc.totalScore, 97);
assert.strictEqual(lowVc.gradeCode, 'excellent');

// (6) 缺项：七项都在场，四项有分三项待填；总分/标准分/等级/总附加分全 null，
//     只有 partialStandardScore（已算项的加权和）有值。
//     oracle: status=incomplete / partialStandardScore=48.3 / strength, endurance, totalBonus=null
const part = calc.assemble(std, { gender: 'male', grade: '大一', answers: {
  heightCm: 175, weightKg: 65.5, vitalCapacity: 4000, sprint50m: '7.5', sitAndReach: '12' } });
assert.strictEqual(part.status, 'incomplete');
assert.strictEqual(part.totalScore, null);
assert.strictEqual(part.standardScore, null);
assert.strictEqual(part.gradeCode, null);
assert.strictEqual(part.gradeLabel, null);
assert.strictEqual(part.totalBonus, null);
assert.strictEqual(part.strengthBonus, null);
assert.strictEqual(part.enduranceBonus, null);
assert.strictEqual(part.partialStandardScore, 48.3);
assert.strictEqual(part.items.length, 7, '七项都要在场，空的显示待填写');
assert.strictEqual(part.items.filter((r) => r.status === 'complete').length, 4);
assert.strictEqual(part.items.filter((r) => r.status === 'incomplete').length, 3);
assert.strictEqual(part.items[1].score, 74);   // 肺活量 4000 的分项仍要留着
assert.deepStrictEqual(part.blockingReasons, ['incomplete']);

// (7) status 优先级照原程序 invalid > incomplete > unresolved（计划写成 unresolved 优先）
//     oracle: 空串(肺活量) + 缺(引体) → invalid；单独 50米 '6.75' → unresolved
const badAndMissing = calc.assemble(std, { gender: 'male', grade: '大一',
  answers: Object.assign({}, MALE_FULL, { vitalCapacity: '', pullUps: null }) });
assert.strictEqual(badAndMissing.status, 'invalid', 'invalid 必须压过 incomplete');
assert.strictEqual(badAndMissing.totalScore, null);
assert.strictEqual(badAndMissing.partialStandardScore, 75);
assert.deepStrictEqual(badAndMissing.blockingReasons, ['invalid', 'incomplete']);
const unres = calc.assemble(std, { gender: 'male', grade: '大一',
  answers: Object.assign({}, MALE_FULL, { sprint50m: '6.75' }) });
assert.strictEqual(unres.status, 'unresolved');
assert.strictEqual(unres.totalScore, null);
assert.strictEqual(unres.partialStandardScore, 80);
// unresolved + 缺项 → incomplete（原程序先判 missingFields 再判 unresolvedRules；
// 计划把它写成 unresolved 优先，这一条就是那个错的钉子）
// oracle: sprint50m 6.75 + pullUps null → status=incomplete / partialStandardScore=70
const unresAndMissing = calc.assemble(std, { gender: 'male', grade: '大一',
  answers: Object.assign({}, MALE_FULL, { sprint50m: '6.75', pullUps: null }) });
assert.strictEqual(unresAndMissing.status, 'incomplete');
assert.strictEqual(unresAndMissing.partialStandardScore, 70);
assert.strictEqual(unresAndMissing.totalBonus, null);
// 整体未完成时，单项附加分照原程序分别给值（那一项 complete 就有），总量仍 null
// oracle: unresolved 单项 → bonusBreakdown.strengthBonus=2 / enduranceBonus=10 / totalBonus=null
assert.strictEqual(unres.strengthBonus, 2);
assert.strictEqual(unres.enduranceBonus, 10);
assert.strictEqual(unres.totalBonus, null);
// invalid + 已完成的长跑：耐力附加分仍是 10（原程序同形）
assert.strictEqual(badAndMissing.enduranceBonus, 10);
assert.strictEqual(badAndMissing.strengthBonus, null);

// (8) 等级四个边界：边界值本身属于高一档（≥90 / ≥80 / ≥60）；0 分是不及格；
//     非数值 / NaN / Infinity / 负数 → null（原程序 getTotalScoreGrade 返回 null，
//     不是 {gradeCode:null}，计划把这一条写成了对象）
assert.deepStrictEqual(calc.gradeOf(90), { gradeCode: 'excellent', gradeLabel: '优秀' });
assert.deepStrictEqual(calc.gradeOf(89.9), { gradeCode: 'good', gradeLabel: '良好' });
assert.deepStrictEqual(calc.gradeOf(80), { gradeCode: 'good', gradeLabel: '良好' });
assert.deepStrictEqual(calc.gradeOf(79.9), { gradeCode: 'pass', gradeLabel: '及格' });
assert.deepStrictEqual(calc.gradeOf(60), { gradeCode: 'pass', gradeLabel: '及格' });
assert.deepStrictEqual(calc.gradeOf(59.9), { gradeCode: 'fail', gradeLabel: '不及格' });
assert.deepStrictEqual(calc.gradeOf(0), { gradeCode: 'fail', gradeLabel: '不及格' });
assert.strictEqual(calc.gradeOf(-0.1), null);
assert.strictEqual(calc.gradeOf(NaN), null);
assert.strictEqual(calc.gradeOf(Infinity), null);
assert.strictEqual(calc.gradeOf('90'), null);
// 经 assemble 的等级也要对：109.5 仍是优秀（小数分不取整）
const femalePartial = calc.assemble(std, { gender: 'female', grade: '大二', answers: {
  heightCm: 165, weightKg: 55, vitalCapacity: 3400, sprint50m: '7.5', sitAndReach: '25.8',
  standingLongJump: 201, sitUps: 56, run800m: '2\'28"' } });
assert.strictEqual(femalePartial.status, 'complete');
assert.strictEqual(femalePartial.standardScore, 99.5);
assert.strictEqual(femalePartial.totalScore, 109.5);
assert.strictEqual(femalePartial.displayTotalScore, '109.5');
assert.strictEqual(femalePartial.gradeCode, 'excellent');

// (9) 女生口径：立定跳远 grade12 的 100 分档是 207，不是 201（计划原文的 201 只有 95 分，
//     会把女生「全满分」那组算成 standardScore=99.5——Step 2 要求改输入值本身）。
//     oracle: 跳 207 + 坐位体前屈 25.8 + 肺活量 3400 + 50米 7.5 + 坐 56 次 + 800米 2'28"=148 秒
//             → complete / standardScore=100 / strengthBonus=0 / enduranceBonus=10 /
//               totalBonus=10 / totalScore=110 / 优秀
const female = calc.assemble(std, { gender: 'female', grade: '大二', answers: {
  heightCm: 165, weightKg: 55, vitalCapacity: 3400, sprint50m: '7.5', sitAndReach: '25.8',
  standingLongJump: 207, sitUps: 56, run800m: '2\'28"' } });
assert.strictEqual(female.status, 'complete');
assert.strictEqual(female.standardScore, 100);
assert.strictEqual(female.strengthBonus, 0);
assert.strictEqual(female.enduranceBonus, 10);
assert.strictEqual(female.totalBonus, 10);
assert.strictEqual(female.totalScore, 110);
assert.strictEqual(female.gradeLabel, '优秀');
assert.strictEqual(female.items.length, 7);
assert.strictEqual(female.items[6].eventKey, 'run800m');
// 仰卧起坐 58 次才进 +1 档（56/57 次都是 0）；800米 148 秒是 +10 档
// oracle: sitUps 56→0 / 58→1 / 69→10；run800m 198→0 / 148→10
assert.strictEqual(calc.computeBonus(std, 'sitUps', 'female', 'grade12', 56).bonusScore, 0);
assert.strictEqual(calc.computeBonus(std, 'sitUps', 'female', 'grade12', 58).bonusScore, 1);
assert.strictEqual(calc.computeBonus(std, 'sitUps', 'female', 'grade12', 69).bonusScore, 10);
assert.strictEqual(calc.computeBonus(std, 'run800m', 'female', 'grade12', 198).bonusScore, 0);
assert.strictEqual(calc.computeBonus(std, 'run800m', 'female', 'grade12', 148).bonusScore, 10);
const female58 = calc.assemble(std, { gender: 'female', grade: '大二', answers: {
  heightCm: 165, weightKg: 55, vitalCapacity: 3400, sprint50m: '7.5', sitAndReach: '25.8',
  standingLongJump: 207, sitUps: 58, run800m: '2\'28"' } });
assert.strictEqual(female58.strengthBonus, 1);
assert.strictEqual(female58.totalBonus, 11);
assert.strictEqual(female58.totalScore, 111);

console.log('Task 5 断言全部通过（标准分/附加分/等级/四态汇总）');

// ── Task 6：输入体检与单位混淆提示 ────────────────────────────────────────────
// 体检模块与 tice-calc.js 同为 UMD：node 里 require，浏览器挂 TICE_CHECKS（由 calc 注入）。
const checks = require('../web-next/tice-checks.js');
const ANSWERS = { heightCm: 175, weightKg: 65.5 };

// 真阳性：文案逐字抄解包产物 utils_fitness-input-view.js（f() / g() 的原句）。
// 与计划 Step 1 的三处差异都是回源后的结果，逐条见 task-6-report.md：
//   · vitalCapacity 900 → 原程序阈值 `r<800||r>8000`，900 在区间内不提示，真阳性用 700；
//   · heightCm 1750 → 原句就是「如实际身高为 175 cm，请填写 175。」（第二处不带单位，原程序如此）；
//   · pullUps 3.5 → 原程序报 must_be_integer，v() 无专属文案，落 d.pullUps。
const wantHint = [
  ['vitalCapacity', 4,        '疑似填写了升（L）。如实际为 4 L，请填写 4000 mL。'],
  ['vitalCapacity', 700,      '数值较少见，请确认肺活量毫升（mL）数是否填写正确。'],
  ['standingLongJump', 2.15,  '疑似填写了米（m）。如实际为 2.15 m，请填写 215 cm。'],
  ['sitAndReach', 248,        '疑似填写了毫米（mm）或漏填小数点，请按厘米（cm）填写。'],
  ['sprint50m', 75,           '数值较大，请确认是否漏填小数点，例如 7.5 秒误填为 75。'],
  ['weightKg', 130,           '数值较大。如原始记录单位为“斤”，请换算为 kg 后填写。'],
  ['heightCm', 1750,          '疑似填写了毫米（mm）。如实际身高为 175 cm，请填写 175。'],
  ['run1000m', '210:30',      '分钟数较大，请确认是否将总秒数填入了“分”（如 210 秒应填 3 分 30 秒）。'],
];
// 该判 invalid 的三类：负数、整数项收小数、空值（空串是「填错了」，null 才是「没填」）
const wantError = [
  ['vitalCapacity', -1,  'negative_not_allowed', '肺活量不能为负数，请输入有效数字，例如 4200'],
  ['pullUps',       3.5, 'must_be_integer',      '请输入整数次数，例如 8'],
  ['vitalCapacity', '',  'empty_string',         '请输入有效数字，例如 4200'],
];
let cf = 0;
for (const [ev, raw, copy] of wantHint) {
  const r = checks.validateField(ev, raw, ANSWERS);
  if (!r.ok || r.hint !== copy) {
    console.log('FAIL hint', ev, raw, JSON.stringify(r.hint)); cf += 1;
  }
}
for (const [ev, raw, code, copy] of wantError) {
  const r = checks.validateField(ev, raw, ANSWERS);
  if (r.ok || r.code !== code || r.errorCopy !== copy) {
    console.log('FAIL err', ev, raw, JSON.stringify(r.code), JSON.stringify(r.errorCopy)); cf += 1;
  }
}
// 假阳性：正常值一条提示都不许有（含 900：它只是偏低，没到原程序的 800 阈值）
const cleanHint = [
  ['vitalCapacity', 4200], ['vitalCapacity', 900], ['vitalCapacity', 3500],
  ['sprint50m', '7.5'], ['sprint50m', '6.9'], ['sitAndReach', 12.5], ['sitAndReach', -3],
  ['standingLongJump', 215], ['standingLongJump', 273],
  ['pullUps', 12], ['sitUps', 35], ['run1000m', "3'17\""], ['run1000m', '197'],
  ['heightCm', 175], ['weightKg', 65.5],
];
for (const [ev, raw] of cleanHint) {
  const r = checks.validateField(ev, raw, ANSWERS);
  if (!r.ok || r.hint !== null) {
    console.log('FAIL false-positive', ev, raw, JSON.stringify(r.hint)); cf += 1;
  }
}
assert.strictEqual(checks.summaryOfHints([]), '');
assert.strictEqual(checks.summaryOfHints(['a', 'b']),
  '检测到 2 项疑似异常输入。当前仍按填写值计算成绩，不影响评分结果。');

// 提示不改变判定：4 mL 照常算分（0 分），只多一条提示；4200 mL 照常 100 分且无提示
const vcHint = calc.scoreEvent(std, { gender: 'male', grade: '大一',
                                      eventKey: 'vitalCapacity', raw: 4 });
assert.strictEqual(vcHint.status, 'complete');
assert.strictEqual(vcHint.score, 0);
assert.strictEqual(vcHint.hint, '疑似填写了升（L）。如实际为 4 L，请填写 4000 mL。');
const vcPlain = calc.scoreEvent(std, { gender: 'male', grade: '大一',
                                       eventKey: 'vitalCapacity', raw: 4200 });
assert.strictEqual(vcPlain.status, 'complete');
assert.strictEqual(vcPlain.score, 78);   // 4200 落在 4300(78) 档，分数照表算，不受提示影响
assert.strictEqual(vcPlain.hint, null);
// 报错码与文案由体检给、与判定同源，且 invalid 不带提示
const vcNeg = calc.scoreEvent(std, { gender: 'male', grade: '大一',
                                     eventKey: 'vitalCapacity', raw: -1 });
assert.strictEqual(vcNeg.status, 'invalid');
assert.strictEqual(vcNeg.code, 'negative_not_allowed');
assert.strictEqual(vcNeg.errorCopy, '肺活量不能为负数，请输入有效数字，例如 4200');
assert.strictEqual(vcNeg.hint, null);
// 整数项与空值同样带文案
assert.strictEqual(calc.scoreEvent(std, { gender: 'male', grade: '大一',
  eventKey: 'pullUps', raw: 3.5 }).errorCopy, '请输入整数次数，例如 8');
assert.strictEqual(calc.scoreEvent(std, { gender: 'male', grade: '大一',
  eventKey: 'vitalCapacity', raw: '' }).errorCopy, '请输入有效数字，例如 4200');
// BMI 派生提示：身高按「米」填（1.75）时 BMI 明显异常；正常 175 无提示
const bmiUnit = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'bmi',
  inputs: { heightCm: 1.75, weightKg: 65.5 } });
assert.strictEqual(bmiUnit.status, 'complete');
assert.strictEqual(bmiUnit.hint, 'BMI 数值明显异常，请检查身高、体重及单位。');
const bmiNormal = calc.scoreEvent(std, { gender: 'male', grade: '大一', eventKey: 'bmi',
  inputs: { heightCm: 175, weightKg: 65.5 } });
assert.strictEqual(bmiNormal.hint, null);
// 满分样例一条提示都没有：体检不许在正常值上噪声化，也不许改动分数
const hintFree = calc.assemble(std, { gender: 'male', grade: '大一', answers: MALE_FULL });
assert.strictEqual(hintFree.standardScore, 100);
assert.strictEqual(hintFree.totalScore, 112);
assert.strictEqual(hintFree.items.filter((r) => r.hint).length, 0);
// 提示进了 assemble 的单项：肺活量 4 → complete / 0 分 / 带升毫升提示；汇总句按条数
const hintOn = calc.assemble(std, { gender: 'male', grade: '大一',
  answers: Object.assign({}, MALE_FULL, { vitalCapacity: 4 }) });
const vcItem = hintOn.items.find((r) => r.eventKey === 'vitalCapacity');
assert.strictEqual(vcItem.status, 'complete');
assert.strictEqual(vcItem.score, 0);
assert.strictEqual(vcItem.hint.indexOf('疑似填写了升（L）'), 0);
assert.strictEqual(hintOn.status, 'complete');
assert.strictEqual(checks.summaryOfHints(
  hintOn.items.map((r) => r.hint).filter(Boolean)).indexOf('检测到 1 项'), 0);

console.log(cf ? `体检 ${cf} 条失败`
               : `体检 ${wantHint.length + wantError.length} 条通过（假阳性 ${cleanHint.length} 条无一误报）`);
if (cf) process.exit(1);
if (bf) process.exit(1);
process.exit(fail ? 1 : 0);
