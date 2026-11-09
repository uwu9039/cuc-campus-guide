// 输入体检：单位混淆（升/毫米/米/斤）、数值可疑（过小过大、极短极长）、整数项收小数、空值。
// 文案与阈值逐条搬自原程序（解包产物：
//   .superpowers/sdd/2026-11-07-tice-calculator/_extract/utils_fitness-input-view.js）：
//   · 提示 warningText —— f()（逐项）与 g()（身高/体重/BMI），只在事件 complete / unresolved 时给；
//   · 报错 errorText —— formatInvalidFieldMessage v() 与 INVALID_FORMAT_HINTS d；
//   · 汇总句 —— warningSummary { title, subtitle }。
// 纪律（原程序自己的原话）：「当前仍按填写值计算成绩，不影响评分结果。」
//   提示只用于核对，绝不参与判定；判定仍然只认 tice-calc.js 的算分路径。
// 允许面（负 / 零 / 整数）不写死事件名，统一读 std 的 allowZero / allowNegative / integerOnly
//   （身高、体重没有独立事件，读 std.bmi 的同名字段——原程序 C() 对这三者也用同一套 sign 闸）。
// 阈值 std 里没有对应字段，逐条抄原程序字面量，集中在 LIMITS；文案集中在 COPY / INVALID_COPY，
//   别散落到函数里。
// 解析器不另写一份：一律转调 tice-calc.js 的 parseDecimal / parseEnduranceTime，
//   否则体检报的 code 会和判定报的 code 分叉。
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory(require('./tice-standard.json'));
  } else {
    root.TICE_CHECKS = factory(null);
  }
}(typeof globalThis !== 'undefined' ? globalThis : this, function (stdJson) {
  'use strict';

  // ── 文案表（唯一的文案来源）─────────────────────────────────────────────
  // 提示：原程序 f()/g() 的原句；模板里的两个空档就是原程序的两次 .concat()。
  const COPY = {
    // 肺活量：疑似把升当毫升填
    vitalLitre: (litre, ml) => `疑似填写了升（L）。如实际为 ${litre} L，请填写 ${ml} mL。`,
    vitalRare: '数值较少见，请确认肺活量毫升（mL）数是否填写正确。',
    // 50 米跑
    sprintTooLarge: '数值较大，请确认是否漏填小数点，例如 7.5 秒误填为 75。',
    sprintTooShort: '用时极短，请确认实测秒数是否填写正确。',
    sprintRare: '数值较少见，请确认 50 米跑秒数是否填写正确。',
    // 坐位体前屈
    sitMm: '疑似填写了毫米（mm）或漏填小数点，请按厘米（cm）填写。',
    sitRare: '数值较少见，请确认实测厘米数是否填写正确。',
    // 立定跳远
    jumpMetre: (metre, cm) => `疑似填写了米（m）。如实际为 ${metre} m，请填写 ${cm} cm。`,
    jumpMm: (cm) => `疑似填写了毫米（mm）。如实际为 ${cm} cm，请填写 ${cm}。`,
    jumpRare: '数值较少见，请确认实测厘米数是否填写正确。',
    // 次数项（引体向上 / 仰卧起坐共用一句）
    countRare: '数值较少见，请确认次数是否填写正确。',
    // 耐力跑
    runMinutesLarge: '分钟数较大，请确认是否将总秒数填入了“分”（如 210 秒应填 3 分 30 秒）。',
    runTooShort: '用时极短，请确认分、秒是否填写正确。',
    runTooLong: '用时较长，请确认分、秒是否填写正确。',
    // 身高
    heightMetre: (metre, cm) => `疑似填写了米（m）。如实际身高为 ${metre} m，请填写 ${cm} cm。`,
    heightMm: (cm) => `疑似填写了毫米（mm）。如实际身高为 ${cm} cm，请填写 ${cm}。`,
    heightRare: '数值较少见，请确认身高厘米（cm）数是否填写正确。',
    // 体重
    weightGram: '疑似填写了克（g）或多填了数位，请按 kg 填写。',
    weightJin: '数值较大。如原始记录单位为“斤”，请换算为 kg 后填写。',
    weightRare: '数值较少见，请确认体重千克（kg）数是否填写正确。',
    // BMI 派生提示
    bmiAnomaly: 'BMI 数值明显异常，请检查身高、体重及单位。',
  };

  // 报错：原程序 d（INVALID_FORMAT_HINTS）为兜底，v() 里按 code 的覆盖写在各自名下。
  // `_` 是「没有专属 code 时的兜底句」，不是另写的文案。
  const INVALID_COPY = {
    heightCm: { must_be_greater_than_zero: '身高必须大于0', _: '请输入有效数字，例如 175' },
    weightKg: { must_be_greater_than_zero: '体重必须大于0', _: '请输入有效数字，例如 65.5' },
    vitalCapacity: {
      negative_not_allowed: '肺活量不能为负数，请输入有效数字，例如 4200',
      _: '请输入有效数字，例如 4200',
    },
    sprint50m: {
      must_be_greater_than_zero: '50米跑用时须大于 0，请输入有效数字，例如 7.5',
      _: '请输入有效数字，例如 7.5',
    },
    sitAndReach: {
      sit_and_reach_sign_conflict: '正负号与数值不一致，请输入有效数字，例如 12.5 或 -3',
      _: '请输入有效数字，例如 12.5 或 -3',
    },
    standingLongJump: {
      negative_not_allowed: '立定跳远不能为负数，请输入有效数字，例如 215',
      _: '请输入有效数字，例如 215',
    },
    pullUps: {
      negative_not_allowed: '引体向上不能为负数，请输入整数次数，例如 8',
      _: '请输入整数次数，例如 8',
    },
    sitUps: {
      negative_not_allowed: '仰卧起坐不能为负数，请输入整数次数，例如 35',
      _: '请输入整数次数，例如 35',
    },
    run1000m: {
      invalid_minutes_or_seconds_range: '请输入有效用时（秒数须为 0～59），例如 4:20',
      ambiguous_decimal_time_format: '请输入整数分、秒，不使用小数，例如 4:20',
      non_positive_time: '请输入大于 0 的有效用时，例如 4:20',
      negative_not_allowed: '请输入大于 0 的有效用时，例如 4:20',
      _: '请输入有效用时，例如 4:20',
    },
    run800m: {
      invalid_minutes_or_seconds_range: '请输入有效用时（秒数须为 0～59），例如 4:20',
      ambiguous_decimal_time_format: '请输入整数分、秒，不使用小数，例如 4:20',
      non_positive_time: '请输入大于 0 的有效用时，例如 4:20',
      negative_not_allowed: '请输入大于 0 的有效用时，例如 4:20',
      _: '请输入有效用时，例如 4:20',
    },
    bmi: { _: '请先修正身高与体重，例如 175 与 65.5' },
  };

  // ── 阈值表（std 里没有这些字段，数值抄原程序 f() / g() 的字面量）─────────
  const LIMITS = {
    // 0 < r <= 15 视为填了升；r < 800 || r > 8000 视为少见
    vitalCapacity: { litreMax: 15, rareLow: 800, rareHigh: 8000 },
    // a >= 45 漏小数点 / a < 5 极短 / a > 20 少见
    sprint50m: { tooLargeMin: 45, tooShortBelow: 5, rareAbove: 20 },
    // s < -40 || s > 50 疑似毫米；s < -25 || s > 40 少见
    sitAndReach: { mmBelow: -40, mmAbove: 50, rareBelow: -25, rareAbove: 40 },
    // 0 < u <= 4.5 疑似米；u >= 1000 疑似毫米；其余 (4.5,60) 或 >330 少见
    standingLongJump: { metreMax: 4.5, mmMin: 1000, rareLowMax: 60, rareHigh: 330 },
    pullUps: { rareCountAbove: 50 },
    sitUps: { rareCountAbove: 100 },
    // 分钟数 >= 60 疑似把总秒数填进了「分」；总秒 0<v<120 极短；v >= 600 较长
    run: { minutesLargeMin: 60, tooShortBelowSec: 120, tooLongAtSec: 600 },
    // u <= 3 疑似米；1000 <= u <= 2500 疑似毫米；u < 120 || u > 230 少见
    heightCm: { metreMax: 3, mmMin: 1000, mmMax: 2500, rareLow: 120, rareHigh: 230 },
    // o >= 25000 疑似克；110 <= o <= 220 且（BMI >= 36 或 o >= 120）疑似斤；o < 25 || o > 200 少见
    weightKg: { gramMin: 25000, jinMin: 110, jinMax: 220, jinNeedsBmi: 36,
                jinMinAlone: 120, rareLow: 25, rareHigh: 200 },
    bmi: { anomalyLow: 10, anomalyHigh: 50 },
  };

  // 身高、体重不是评分事件（原程序放在 bodyWarnings），允许面借 std.bmi 的同名开关。
  const BODY_FIELDS = {
    heightCm: { unit: 'cm', unitType: 'number', integerOnly: false },
    weightKg: { unit: 'kg', unitType: 'number', integerOnly: false },
  };

  // 这几个 code 不是「这个字段填错了」，不该贴该字段的输入文案。
  const NON_FIELD_CODES = ['invalid_gender', 'invalid_grade', 'enrollment_year_not_allowed',
    'enrollment_year_or_numeric_grade_not_allowed', 'unsupported_event_for_gender',
    'unknown_event_key'];

  let STANDARD = stdJson || null;
  let CALC = null;

  // 浏览器里没有 require：由 tice.js 调 configure(std) 注入评分表，或从全局取 TICE_CALC。
  function configure(std) {
    STANDARD = std || null;
    return api;
  }

  function calcApi() {
    if (CALC) return CALC;
    if (typeof require === 'function') {
      CALC = require('./tice-calc.js');
    } else if (typeof globalThis !== 'undefined' && globalThis.TICE_CALC) {
      CALC = globalThis.TICE_CALC;
    }
    return CALC;
  }

  // ── 显示用归一化（原程序 h()）：去前导零、去正号；时间只归一化 mm:ss 这一种形态 ──
  // 原程序只接受字符串（表单值都是字符串），这里的入参也可能是数字，先转字符串再归一化。
  function normalizeMeasuredText(raw, isTime) {
    const s = typeof raw === 'number' && Number.isFinite(raw) ? String(raw)
      : (typeof raw === 'string' ? raw.trim() : '');
    if (!s) return '';
    if (isTime) {
      const m = /^0*(\d+):(\d+)$/.exec(s);
      if (!m) return s;
      const sec = m[2].length > 2
        ? m[2].replace(/^0+(?=\d{2}$)/, '').replace(/^0+(?=\d)/, '')
        : m[2];
      return m[1] + ':' + sec;
    }
    return s.replace(/^([+-]?)0+(?=\d)/, (whole, sign) => (sign === '-' ? '-' : ''))
            .replace(/^\+(?=\d)/, '');
  }

  // 允许面：与 tice-calc.js 的 signPolicyCode 同义（那边没导出，这里按 std 字段复述一遍）。
  function signCode(allowZero, allowNegative, sign) {
    if (sign < 0 && !allowNegative) return allowZero ? 'negative_not_allowed' : 'must_be_greater_than_zero';
    if (sign === 0 && !allowZero) return 'must_be_greater_than_zero';
    return null;
  }

  function specOf(key) {
    const std = STANDARD;
    if (!std || !key) return null;
    const ev = std.events && std.events[key];
    if (ev) {
      return { unit: ev.unit, unitType: ev.unitType, integerOnly: !!ev.integerOnly,
               allowZero: !!ev.allowZero, allowNegative: !!ev.allowNegative };
    }
    const body = BODY_FIELDS[key];
    if (body && std.bmi) {
      return Object.assign({}, body, { allowZero: !!std.bmi.allowZero,
                                       allowNegative: !!std.bmi.allowNegative });
    }
    return null;
  }

  function parseValue(spec, raw) {
    const c = calcApi();
    if (spec.unitType === 'mmss') {
      const t = c.parseEnduranceTime(raw);
      return t.ok ? { ok: true, value: t.seconds } : { ok: false, code: t.code };
    }
    const d = c.parseDecimal(raw);
    if (!d.ok) return { ok: false, code: d.code };
    return { ok: true, value: d.num, sign: d.sign, decimalPlaces: d.decimalPlaces };
  }

  function numOf(raw) {
    const c = calcApi();
    if (!c) return null;
    const d = c.parseDecimal(raw);
    return d.ok ? d.num : null;
  }

  // 原程序 f() 用表单当前值算 BMI（g() 里也是），所以正在体检的那一格要用 raw 覆盖旧答案，
  // 不然「体重填了 130 但 answers 里还是 65.5」会把斤的提示漏掉。
  function bmiValue(answers, override) {
    const a = answers || {};
    const heightRaw = override && override.key === 'heightCm' ? override.raw : a.heightCm;
    const weightRaw = override && override.key === 'weightKg' ? override.raw : a.weightKg;
    const h = numOf(heightRaw);
    const w = numOf(weightRaw);
    if (!(h > 0) || !(w > 0)) return null;
    return w / Math.pow(h / 100, 2);
  }

  // ── 判定表：每条 {when(value, ctx), copy(value, ctx)}，命中第一条即止（原程序 if/else 链）──
  const CHECKS = {
    vitalCapacity: [
      { when: (v) => v > 0 && v <= LIMITS.vitalCapacity.litreMax,
        copy: (v, c) => COPY.vitalLitre(normalizeMeasuredText(c.raw, false), Math.round(1000 * v)) },
      { when: (v) => v < LIMITS.vitalCapacity.rareLow || v > LIMITS.vitalCapacity.rareHigh,
        copy: () => COPY.vitalRare },
    ],
    sprint50m: [
      { when: (v) => v >= LIMITS.sprint50m.tooLargeMin, copy: () => COPY.sprintTooLarge },
      { when: (v) => v < LIMITS.sprint50m.tooShortBelow, copy: () => COPY.sprintTooShort },
      { when: (v) => v > LIMITS.sprint50m.rareAbove, copy: () => COPY.sprintRare },
    ],
    sitAndReach: [
      { when: (v) => v < LIMITS.sitAndReach.mmBelow || v > LIMITS.sitAndReach.mmAbove,
        copy: () => COPY.sitMm },
      { when: (v) => v < LIMITS.sitAndReach.rareBelow || v > LIMITS.sitAndReach.rareAbove,
        copy: () => COPY.sitRare },
    ],
    standingLongJump: [
      { when: (v) => v > 0 && v <= LIMITS.standingLongJump.metreMax,
        copy: (v, c) => COPY.jumpMetre(normalizeMeasuredText(c.raw, false), Math.round(100 * v)) },
      { when: (v) => v >= LIMITS.standingLongJump.mmMin,
        copy: (v) => COPY.jumpMm(Math.round(v / 10)) },
      { when: (v) => (v > LIMITS.standingLongJump.metreMax && v < LIMITS.standingLongJump.rareLowMax)
                      || v > LIMITS.standingLongJump.rareHigh,
        copy: () => COPY.jumpRare },
    ],
    pullUps: [
      { when: (v) => v > LIMITS.pullUps.rareCountAbove, copy: () => COPY.countRare },
    ],
    sitUps: [
      { when: (v) => v > LIMITS.sitUps.rareCountAbove, copy: () => COPY.countRare },
    ],
    // 耐力跑按总秒数推分、秒：分钟数 >= 60 才是原程序那条「把总秒数填进分」的形态。
    run1000m: [
      { when: (sec) => Math.floor(sec / 60) >= LIMITS.run.minutesLargeMin,
        copy: () => COPY.runMinutesLarge },
      { when: (sec) => sec > 0 && sec < LIMITS.run.tooShortBelowSec, copy: () => COPY.runTooShort },
      { when: (sec) => sec >= LIMITS.run.tooLongAtSec, copy: () => COPY.runTooLong },
    ],
    heightCm: [
      { when: (v) => v > 0 && v <= LIMITS.heightCm.metreMax,
        copy: (v, c) => COPY.heightMetre(normalizeMeasuredText(c.raw, false), Math.round(100 * v)) },
      { when: (v) => v >= LIMITS.heightCm.mmMin && v <= LIMITS.heightCm.mmMax,
        copy: (v) => COPY.heightMm(Number((v / 10).toFixed(1))) },
      { when: (v) => v < LIMITS.heightCm.rareLow || v > LIMITS.heightCm.rareHigh,
        copy: () => COPY.heightRare },
    ],
    weightKg: [
      { when: (v) => v >= LIMITS.weightKg.gramMin, copy: () => COPY.weightGram },
      { when: (v, c) => v >= LIMITS.weightKg.jinMin && v <= LIMITS.weightKg.jinMax
          && (typeof c.bmi === 'number' ? c.bmi >= LIMITS.weightKg.jinNeedsBmi
                                        : v >= LIMITS.weightKg.jinMinAlone),
        copy: () => COPY.weightJin },
      { when: (v) => v < LIMITS.weightKg.rareLow || v > LIMITS.weightKg.rareHigh,
        copy: () => COPY.weightRare },
    ],
  };
  CHECKS.run800m = CHECKS.run1000m;

  function errorCopyFor(eventKey, code) {
    const key = typeof eventKey === 'string' ? eventKey.trim() : eventKey;
    if (!key || !code) return null;
    if (NON_FIELD_CODES.indexOf(code) >= 0) return null;
    const table = INVALID_COPY[key];
    if (!table) return null;
    return table[code] || table._ || null;
  }

  // 提示只在「值本身合法」时给：解析失败、符号闸、整数闸都是 invalid，原程序那时只给 errorText。
  function hintFor(eventKey, raw, answers) {
    const key = typeof eventKey === 'string' ? eventKey.trim() : eventKey;
    const std = STANDARD;
    if (!std || !key) return null;
    if (key === 'bmi') {
      const bmi = bmiValue(answers, null);
      if (typeof bmi !== 'number' || !Number.isFinite(bmi)) return null;
      return (bmi < LIMITS.bmi.anomalyLow || bmi > LIMITS.bmi.anomalyHigh)
        ? COPY.bmiAnomaly : null;
    }
    const spec = specOf(key);
    const rules = CHECKS[key];
    if (!spec || !rules) return null;
    if (raw === null || raw === undefined) return null;
    const parsed = parseValue(spec, raw);
    if (!parsed.ok) return null;
    if (spec.unitType === 'number') {
      if (signCode(spec.allowZero, spec.allowNegative, parsed.sign)) return null;
      if (spec.integerOnly && parsed.decimalPlaces > 0) return null;
    }
    const ctx = { answers: answers || {}, raw, value: parsed.value,
                  bmi: bmiValue(answers, { key, raw }) };
    for (const rule of rules) {
      if (rule.when(ctx.value, ctx)) return rule.copy(ctx.value, ctx);
    }
    return null;
  }

  // 一次体检：ok=false 只表示「这一格该判 invalid」，code 与判定路径同码；
  // hint 永远不参与判定（调用方只把它挂在结果上）。
  function validateField(eventKey, raw, answers) {
    const key = typeof eventKey === 'string' ? eventKey.trim() : eventKey;
    const ans = answers || {};
    const idle = { ok: true, code: null, errorCopy: null, hint: null, normalized: null };
    if (!STANDARD || !key || !calcApi()) return idle;
    if (key === 'bmi') {
      return Object.assign({}, idle, { hint: hintFor('bmi', null, ans) });
    }
    const spec = specOf(key);
    if (!spec) return idle;
    // null / undefined 是「未填」（原程序 isMissing → incomplete），不是填错。
    if (raw === null || raw === undefined) return idle;
    const parsed = parseValue(spec, raw);
    if (!parsed.ok) {
      return { ok: false, code: parsed.code,
               errorCopy: errorCopyFor(key, parsed.code), hint: null, normalized: null };
    }
    if (spec.unitType === 'number') {
      const sc = signCode(spec.allowZero, spec.allowNegative, parsed.sign);
      if (sc) {
        return { ok: false, code: sc, errorCopy: errorCopyFor(key, sc),
                 hint: null, normalized: null };
      }
      if (spec.integerOnly && parsed.decimalPlaces > 0) {
        return { ok: false, code: 'must_be_integer',
                 errorCopy: errorCopyFor(key, 'must_be_integer'), hint: null, normalized: null };
      }
    }
    return { ok: true, code: null, errorCopy: null, hint: hintFor(key, raw, ans),
             normalized: normalizeMeasuredText(raw, spec.unitType === 'mmss') };
  }

  // 汇总句照原程序 warningSummary：title 无句末标点，subtitle 自带句号。
  function summaryOfHints(hints) {
    if (!hints || !hints.length) return '';
    return `检测到 ${hints.length} 项疑似异常输入。当前仍按填写值计算成绩，不影响评分结果。`;
  }

  const api = { validateField, summaryOfHints, errorCopyFor, hintFor,
                normalizeMeasuredText, configure, COPY, LIMITS, CHECKS };
  return api;
}));
