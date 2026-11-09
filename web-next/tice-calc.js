// 体测算分内核：纯函数，不碰 DOM，不碰存储，不用浮点比阈值。
// 规则以解包产物 utils/fitness-calculator.js 为金标准（2026-11-09 回源轮）：
//   1) 全程 BigInt 十进制定标（scaledBigInt + decimalPlaces），阈值比较在整数域；
//   2) 不擅自取位：精度高于表格刻度时，向下取位与向上取位落不同档 → 无法定分；
//   3) BMI 不取位：真值与一位小数门槛直接精确比较，落开缝才 unresolved；
//   4) 低于最低档是 0 分（complete），不是 invalid；
//   5) 整数项收到小数 → must_be_integer；符号闸由数据 allowZero/allowNegative 驱动；
//   6) 空值面分三类：null/undefined → incomplete，空串 → empty_string，异类型 → invalid_type；
//   7) 性别/年级/项目非法一律 invalid + code，不抛异常（抛异常会跳出 spec 的四态）。
// 与源包的两处有意差异：年级键用中文标签（源包内部是 freshman 等英文枚举，UI 同样是中文）；
// BMI 只接 heightCm/weightKg，不接源包那条「直接给 rawBMI」的旁路（本项目页面没有这个入口）。
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    // 体检模块（tice-checks.js）只借 std 的 allowZero/allowNegative/integerOnly 与文案，
    // 算分语义仍全在本文件；它反过来借本文件的 parseDecimal / parseEnduranceTime（延迟 require，
    // 所以这里的循环依赖在加载期不会取到空 exports）。
    module.exports = factory(require('./tice-checks.js'));
  } else {
    root.TICE_CALC = factory(root.TICE_CHECKS || null);
  }
}(typeof globalThis !== 'undefined' ? globalThis : this, function (checksInjected) {
  const DECIMAL_RE = /^([+-]?)(\d+)(?:\.(\d+))?$/;
  const MAX_SAFE_BIG = 900719925474099n;
  const MAX_INPUT_CHARS = 4096;

  // 浏览器里 tice-checks.js 与 tice-calc.js 的加载顺序不保证（tice.html 不归本任务改），
  // 所以注入优先、其次在调用时读全局；两边都没有就退化成「只算分、不提示」。
  function checksApi() {
    if (checksInjected) return checksInjected;
    if (typeof globalThis !== 'undefined' && globalThis.TICE_CHECKS) return globalThis.TICE_CHECKS;
    return null;
  }

  function pow10Big(n) {
    let r = 1n;
    for (let i = 0; i < n; i += 1) r *= 10n;
    return r;
  }

  // ── 输入形态：null/undefined 是「未填」，空串是「填错了」 ──
  // 原程序实测：null/undefined → incomplete/missing_value；''/空格 → invalid/empty_string；
  // false/[]/{} → invalid/invalid_type。三者不能混成同一个分支。
  function classifyRaw(raw) {
    if (raw === null || raw === undefined) return { kind: 'missing', code: 'missing_value' };
    if (typeof raw === 'number') {
      return Number.isFinite(raw) ? { kind: 'ok' } : { kind: 'bad', code: 'non_finite_number' };
    }
    if (typeof raw !== 'string') return { kind: 'bad', code: 'invalid_type' };
    if (raw.trim() === '') return { kind: 'bad', code: 'empty_string' };
    return { kind: 'ok' };
  }

  // 解析成 {num, sign, scaledBigInt(绝对值), decimalPlaces}；失败带 code。
  // 尾随零先剥掉再数小数位（原程序 M 的 `.replace(/0+$/,"")`）：`8.0` 与 `8` 同形，
  // 否则整数项会把 `8.0` 误判成小数。sign 为 0 表示值就是零，符号闸靠它区分「零」与「负」。
  function parseDecimal(raw) {
    const cls = classifyRaw(raw);
    if (cls.kind === 'missing') return { ok: false, code: 'missing_value' };
    if (cls.kind === 'bad') return { ok: false, code: cls.code };
    if (typeof raw === 'string' && raw.length > MAX_INPUT_CHARS) {
      return { ok: false, code: 'decimal_input_too_long' };
    }
    const s = String(raw).trim();
    const m = DECIMAL_RE.exec(s);
    if (!m) return { ok: false, code: 'invalid_number_format' };
    const frac = (m[3] || '').replace(/0+$/, '');
    const num = Number(s);
    if (!Number.isFinite(num)) return { ok: false, code: 'non_finite_number' };
    const sign = /^0+$/.test(m[2]) && frac.length === 0 ? 0 : (m[1] === '-' ? -1 : 1);
    const scaledBigInt = BigInt(m[2] + frac);
    // 与原程序同一条边界：数值本身要落在安全整数范围内；`0.000…1` 这类下溢成 0 的也拒。
    if (scaledBigInt > MAX_SAFE_BIG * pow10Big(frac.length) || (sign !== 0 && num === 0)) {
      return { ok: false, code: 'measurement_out_of_range' };
    }
    return { ok: true, num, sign, scaledBigInt, decimalPlaces: frac.length };
  }

  // 符号闸由数据驱动（源 precision.allowZero / allowNegative），代码里不写事件名 switch。
  // 两者皆禁时负数与零同报 must_be_greater_than_zero（原程序 sprint50m/BMI 就是 `sign<=0` 一条）。
  function signPolicyCode(allowZero, allowNegative, sign) {
    if (sign < 0 && !allowNegative) return allowZero ? 'negative_not_allowed' : 'must_be_greater_than_zero';
    if (sign === 0 && !allowZero) return 'must_be_greater_than_zero';
    return null;
  }

  // 把十进制按表格刻度定标。余数为 0 即「本就落在刻度上」；否则给 floor / ceil 两个整数刻度。
  // 负值按数学意义向下取整：-3.5 → floor -4 / ceil -3（BigInt 除法是向零截断，所以负号要另判）。
  function toStep(dec, stepDecimalPlaces) {
    const dp = dec.decimalPlaces;
    const signed = dec.sign < 0 ? -dec.scaledBigInt : dec.scaledBigInt;
    if (dp <= stepDecimalPlaces) {
      const v = Number(signed * pow10Big(stepDecimalPlaces - dp));
      return { isExactScale: true, floorScaled: v, ceilScaled: v, scaledValue: v };
    }
    const unit = pow10Big(dp - stepDecimalPlaces);
    const q = signed / unit;
    const r = signed % unit;
    if (r === 0n) {
      const v = Number(q);
      return { isExactScale: true, floorScaled: v, ceilScaled: v, scaledValue: v };
    }
    const lo = signed >= 0n ? q : q - 1n;
    const hi = signed >= 0n ? q + 1n : q;
    return { isExactScale: false, floorScaled: Number(lo), ceilScaled: Number(hi), scaledValue: null };
  }

  // ── 耐力跑时间 ──
  // 接受面照原程序 R()：3'17" / 3′17″ / 3'17 / 3:17 / 3:7 / 3分17秒 / 3分 /
  //   210 / 210秒 / 197s / 数字总秒 / {minutes,seconds}。
  // 小数时间一律拒成 ambiguous_decimal_time_format（模块原话：「严禁将 3.17 等小数误认为分秒」），
  // 且这条在分秒正则之前——`3.17` 不许被当成 3 分 17 秒。
  function timeFromParts(min, sec) {
    if (!Number.isSafeInteger(min) || !Number.isSafeInteger(sec)) {
      return { ok: false, code: 'unsafe_time_integer' };
    }
    if (min < 0 || sec < 0 || sec >= 60) return { ok: false, code: 'invalid_minutes_or_seconds_range' };
    const total = 60n * BigInt(min) + BigInt(sec);
    if (total <= 0n) return { ok: false, code: 'non_positive_time' };
    if (total > BigInt(Number.MAX_SAFE_INTEGER)) return { ok: false, code: 'unsafe_time_integer' };
    return { ok: true, seconds: Number(total) };
  }

  function parseEnduranceTime(raw) {
    if (raw === null || raw === undefined) return { ok: false, code: 'missing_value' };
    if (typeof raw === 'object' && !Array.isArray(raw)) return timeFromParts(raw.minutes, raw.seconds);
    if (typeof raw === 'number') {
      if (!Number.isFinite(raw)) return { ok: false, code: 'non_finite_number' };
      if (raw <= 0) return { ok: false, code: 'non_positive_time' };
      if (!Number.isInteger(raw)) return { ok: false, code: 'ambiguous_decimal_time_format' };
      if (!Number.isSafeInteger(raw)) return { ok: false, code: 'unsafe_time_integer' };
      return timeFromParts(Math.floor(raw / 60), raw % 60);
    }
    if (typeof raw !== 'string') return { ok: false, code: 'invalid_type' };
    if (raw.length > MAX_INPUT_CHARS) return { ok: false, code: 'time_input_too_long' };
    const s = raw.trim();
    if (s === '') return { ok: false, code: 'empty_string' };
    if (s.includes('.')) return { ok: false, code: 'ambiguous_decimal_time_format' };
    if (s.startsWith('-')) return { ok: false, code: 'negative_not_allowed' };
    const m = /^(\d+):(\d+)$/.exec(s)
           || /^(\d+)['′](\d+)(?:["″])?$/.exec(s)
           || /^(\d+)分(?:(\d+)秒?)?$/.exec(s);
    if (m) return timeFromParts(Number(m[1]), Number(m[2] === undefined ? '0' : m[2]));
    const s2 = /^(\d+)(?:s|秒)?$/i.exec(s);
    if (s2) {
      const sec = Number(s2[1]);
      if (!Number.isSafeInteger(sec)) return { ok: false, code: 'unsafe_time_integer' };
      return timeFromParts(Math.floor(sec / 60), sec % 60);
    }
    return { ok: false, code: 'invalid_endurance_time_format' };
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

  // 年级解析照原程序：标签 → 组别，也接组别名直传；标签两端空白要 trim。
  // 入学年份与数字年级各有专属错误码（Task 6 的文案映射要用），不能都塞进 invalid_grade。
  function resolveGrade(std, grade) {
    if (typeof grade === 'string') {
      const g = grade.trim();
      if (std.gradeToGroup[g]) return { ok: true, group: std.gradeToGroup[g] };
      if (Object.values(std.gradeGroups).indexOf(g) >= 0) return { ok: true, group: g };
      if (/^20\d{2}/.test(g)) return { ok: false, code: 'enrollment_year_not_allowed' };
    } else if (typeof grade === 'number' && Number.isFinite(grade)) {
      return { ok: false, code: 'enrollment_year_or_numeric_grade_not_allowed' };
    }
    return { ok: false, code: 'invalid_grade' };
  }

  function gradeGroupOf(std, grade) {
    const r = resolveGrade(std, grade);
    if (!r.ok) throw new Error('未知年级: ' + grade);
    return r.group;
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

  // 最低分档的 level（本数据恒为「不及格」）。低于最低档给 0 分时用它，不写死字面量。
  function failLevelOf(levels) {
    return levels.reduce((a, b) => (b.score < a.score ? b : a)).level;
  }

  // 低于最低档 = 0 分（原程序 status:'complete'/score:0/level:'不及格'/matchedThreshold:null）
  function scoreAt(levels, direction, scaled) {
    const hit = matchLevel(levels, direction, scaled);
    if (hit) {
      return { score: hit.score, level: hit.level,
               matchedThreshold: hit.threshold, rawDisplay: hit.rawDisplay };
    }
    return { score: 0, level: failLevelOf(levels), matchedThreshold: null, rawDisplay: null };
  }

  function scoreLevel(std, evKey, gender, group, scaled) {
    const ev = std.events[evKey];
    if (!ev || ev.genders.indexOf(gender) < 0) {
      throw new Error(`性别不匹配: ${evKey} 只存 ${ev ? ev.genders.join('/') : '?'}`);
    }
    const built = ev.byGroup[gender][group];
    const hit = scoreAt(built.levels, ev.direction, scaled);
    return { status: 'scored', score: hit.score, level: hit.level,
             matchedThreshold: hit.matchedThreshold, rawDisplay: hit.rawDisplay, reason: null };
  }

  // ── BMI：不取位，真值与一位小数门槛做精确整数比较 ──
  // bmi ⋚ T/10 ⟺ 10·10000·W ⋚ T·H²，H=sh/10^dh、W=sw/10^dw 通分后全部是整数乘法。
  function bmiCompareTenths(h, w, tenths) {
    const L = 100000n * w.scaledBigInt * pow10Big(2 * h.decimalPlaces);
    const R = BigInt(tenths) * h.scaledBigInt * h.scaledBigInt * pow10Big(w.decimalPlaces);
    return L < R ? -1 : (L > R ? 1 : 0);
  }

  function bmiOf(heightCm, weightKg) {
    if (!(heightCm > 0) || !(weightKg > 0)) return null;
    return weightKg / Math.pow(heightCm / 100, 2);      // 只给显示用，判定不读它
  }

  // 四类里两端是开区间（低体重的 min、肥胖的 max 落盘为 null）：用「该端不存在」表达，
  // 不做 ±Infinity 数值兜底——判定走整数比较，不会有 `310 <= null` 那类静默失效。
  // 字段顺序照原程序 G()：先身高后体重，任一「填了但填错」立即报码、盖过另一头的「未填」
  // （实测 h=0 / w='' 报 must_be_greater_than_zero，不是 empty_string）；两头都没填才 incomplete。
  function scoreBmi(std, gender, heightCm, weightKg) {
    const blank = (status, code) => ({ status, score: null, level: null,
                                       matchedThreshold: null, rawDisplay: null, reason: code });
    const g = typeof gender === 'string' ? gender.trim() : null;
    const cats = g ? std.bmi.categoriesByGender[g] : null;
    if (!cats) return blank('invalid', 'invalid_gender');
    const parts = [];
    for (const raw of [heightCm, weightKg]) {
      const d = parseDecimal(raw);
      if (!d.ok) {
        if (d.code === 'missing_value') { parts.push(null); continue; }
        return blank('invalid', d.code);
      }
      const sc = signPolicyCode(std.bmi.allowZero, std.bmi.allowNegative, d.sign);
      if (sc) return blank('invalid', sc);
      parts.push(d);
    }
    if (parts.indexOf(null) >= 0) return blank('incomplete', 'missing_value');
    const h = parts[0], w = parts[1];
    const hit = cats.find((c) =>
      (c.scaledMinInclusive === null || bmiCompareTenths(h, w, c.scaledMinInclusive) >= 0)
      && (c.scaledMaxInclusive === null || bmiCompareTenths(h, w, c.scaledMaxInclusive) <= 0));
    if (hit) {
      return { status: 'scored', score: hit.score, level: hit.categoryLabel,
               matchedThreshold: hit.rawDisplay, rawDisplay: hit.rawDisplay, reason: null };
    }
    return blank('unresolved', 'bmi_boundary_precision_unresolved');
  }

  // 精度对照：输入精度高于表格刻度时，向下取位与向上取位落不同档 → 无法定分；
  // 同档用向下取位那一档。**没有 scale<=1 的前置闸**：肺活量、立定跳远同样要查。
  function precisionCrossCheck(ev, levels, step) {
    if (step.isExactScale) return null;
    const lo = scoreAt(levels, ev.direction, step.floorScaled);
    const hi = scoreAt(levels, ev.direction, step.ceilScaled);
    if (lo.score !== hi.score) {
      return { status: 'unresolved', score: null, level: null, matchedThreshold: null,
               rawDisplay: null, reason: 'measurement_precision_rounding_unresolved' };
    }
    return null;
  }

  // EventResult 的唯一出口：四个 status 共用同一份键集合。
  // 未知项目时 name/weightPercent 落 null（照原程序：eventName undefined、weightPercent null），
  // 不许回退成 BMI 的名字——那会把「项目名打错了」显示成「体重指数」。
  function mkResult(evKey, std, patch) {
    const isBmi = evKey === 'bmi';
    const ev = isBmi ? null : std.events[evKey];
    const lr = patch.levelResult || null;
    return Object.assign({
      eventKey: evKey, name: ev ? ev.name : (isBmi ? '体重指数（BMI）' : null),
      status: 'incomplete', levelResult: lr, score: null,
      weightPercent: ev ? ev.weightPercent : (isBmi ? std.bmi.weightPercent : null),
      weightedContribution: null,
      bonusEligible: ev ? ev.bonusEligible : false, bonusScore: 0, hint: null,
      code: null, errorCopy: null,
    }, patch);
  }

  // 提示只挂在「已算出」与「规则待确认」两态：原程序 f() 的门就是 status complete / unresolved，
  // invalid 给 errorText、incomplete 什么都不给。提示不参与判定，分数照常算。
  function attachHint(result, hint) {
    if (hint && (result.status === 'complete' || result.status === 'unresolved')) {
      result.hint = hint;
    }
    return result;
  }

  function invalidResult(evKey, std, code) {
    const checks = checksApi();
    const errorCopy = checks && typeof checks.errorCopyFor === 'function'
      ? checks.errorCopyFor(evKey, code) : null;
    return mkResult(evKey, std, {
      status: 'invalid', code, errorCopy,
      levelResult: { status: 'invalid', score: null, level: null,
                     matchedThreshold: null, rawDisplay: null, reason: code },
    });
  }

  function unresolvedResult(evKey, std, lr) {
    return mkResult(evKey, std, { status: 'unresolved', code: lr.reason, levelResult: lr });
  }

  function completeResult(evKey, std, lr, weighted, extra) {
    return mkResult(evKey, std, Object.assign({
      status: 'complete', levelResult: lr, score: lr.score, code: null,
      weightedContribution: weighted(lr.score),
    }, extra || {}));
  }

  function scoreEvent(std, input) {
    const evKey = input.eventKey;
    // 校验顺序照原程序：性别 → 年级 → 项目，三者都返回 invalid + code，不抛异常。
    // 抛异常会跳出 spec 的四态（已计算/待填写/需修正/规则待确认），页面还得额外 try/catch。
    // 直接调 scoreLevel / gradeGroupOf 仍抛可读错误——那是给编程错误用的，不是给输入用的。
    const gender = typeof input.gender === 'string' ? input.gender.trim() : input.gender;
    if (Object.keys(std.bmi.categoriesByGender).indexOf(gender) < 0) {
      return invalidResult(evKey, std, 'invalid_gender');
    }
    const resolved = resolveGrade(std, input.grade);
    if (!resolved.ok) return invalidResult(evKey, std, resolved.code);
    const group = resolved.group;

    if (evKey === 'bmi') {
      const inputs = input.inputs || {};
      // BMI 这一格的体检用身高/体重两项派生（原程序 g() 同形：bodyWarnings 分开列，
      // bmi 自己的 warningText 只有「BMI 数值明显异常…」）。
      const checks = checksApi();
      const check = checks ? checks.validateField('bmi', null, inputs) : null;
      const lr = scoreBmi(std, gender, inputs.heightCm, inputs.weightKg);
      if (lr.status === 'incomplete') return mkResult(evKey, std, { code: lr.reason });
      if (lr.status === 'invalid') return invalidResult(evKey, std, lr.reason);
      if (lr.status === 'unresolved') {
        return attachHint(unresolvedResult(evKey, std, lr), check && check.hint);
      }
      return attachHint(completeResult(evKey, std, lr,
        (s) => Math.round(s * std.bmi.weightPercent) / 100), check && check.hint);
    }

    const ev = std.events[evKey];
    const built = ev && ev.byGroup[gender] && ev.byGroup[gender][group];
    if (!ev || ev.genders.indexOf(gender) < 0 || !built) {
      return invalidResult(evKey, std, 'unsupported_event_for_gender');
    }

    // 体检在算分之前，但排在性别/年级/项目三闸之后：报错码与文案由体检给，
    // 它转调的就是下面这两个解析器，所以码不会分叉；hint 只随后续结果带出，不参与判定。
    let hint = null;
    const checks = checksApi();
    if (checks) {
      const check = checks.validateField(evKey, input.raw, input.inputs || {});
      if (!check.ok) return invalidResult(evKey, std, check.code);
      hint = check.hint;
    }

    const cls = classifyRaw(input.raw);
    if (cls.kind === 'missing') return mkResult(evKey, std, { code: cls.code });
    // 其余坏形态交给各自的解析器报码：长跑去 parseEnduranceTime（它接受 {minutes,seconds}，
    // 在这里先按 invalid_type 拦掉就把这条接受面砍了），数值去 parseDecimal。

    if (ev.unitType === 'mmss') {
      const t = parseEnduranceTime(input.raw);
      if (!t.ok) return invalidResult(evKey, std, t.code);
      const lr = scoreLevel(std, evKey, gender, group, t.seconds);
      // 附加分按同一刻度值判：门槛来自 std 的 bonusTable，不在代码里写秒数。
      const bonus = computeBonus(std, evKey, gender, group, t.seconds);
      return attachHint(completeResult(evKey, std, lr,
        (s) => Math.round(s * ev.weightPercent) / 100,
        { scaledValue: t.seconds, bonusScore: bonus.bonusScore }), hint);
    }

    const dec = parseDecimal(input.raw);
    if (!dec.ok) return invalidResult(evKey, std, dec.code);
    // 符号闸在整数闸之前：原程序 pullUps 先判 `sign<0` 再判 `decimalPlaces>0`，
    // 所以 `-0.5` 报 negative_not_allowed 而不是 must_be_integer。
    const signCode = signPolicyCode(ev.allowZero, ev.allowNegative, dec.sign);
    if (signCode) return invalidResult(evKey, std, signCode);
    if (ev.integerOnly && dec.decimalPlaces > 0) {
      return invalidResult(evKey, std, 'must_be_integer');
    }
    const step = toStep(dec, ev.decimalPlaces);
    const levels = built.levels;
    const cross = precisionCrossCheck(ev, levels, step);
    if (cross) return attachHint(unresolvedResult(evKey, std, cross), hint);
    const lr = scoreLevel(std, evKey, gender, group, step.floorScaled);
    const bonus = computeBonus(std, evKey, gender, group, step.floorScaled);
    return attachHint(completeResult(evKey, std, lr,
      (s) => Math.round(s * ev.weightPercent) / 100,
      { scaledValue: step.floorScaled, bonusScore: bonus.bonusScore }), hint);
  }

  // ── 附加分 ──
  // 原程序 scoreSingleEvent 里对 bonusEligible 的项逐档比 bonusTable：方向 higher_is_better
  // 用 `scaled >= 门槛`、lower_is_better 用 `scaled <= 门槛`，命中第一档即返回，单项封顶
  // 取 std.limits.maxSingleBonusScore（数据是 10，代码里不写字面量）。
  // 门槛本身由 100 分档 ± delta 派生（prepareStandard 的 buildBonusTable），所以「命中附加分」
  // 必然已经单项满分——原程序没有另写一条 score===100 的前置判断，这里也不加。
  function computeBonus(std, evKey, gender, group, scaled) {
    const ev = std.events[evKey];
    if (!ev || !ev.bonusEligible || typeof scaled !== 'number' || !Number.isFinite(scaled)) {
      return { bonusScore: 0, matchedTier: null };
    }
    const built = ev.byGroup[gender] && ev.byGroup[gender][group];
    if (!built) return { bonusScore: 0, matchedTier: null };
    for (const t of built.bonusTable) {
      const hit = ev.direction === 'higher_is_better'
        ? scaled >= t.scaledAbsoluteThreshold
        : scaled <= t.scaledAbsoluteThreshold;
      if (hit) {
        return { bonusScore: Math.min(std.limits.maxSingleBonusScore, t.bonusScore),
                 matchedTier: t };
      }
    }
    return { bonusScore: 0, matchedTier: null };
  }

  // ── 总分等级 ──
  // 原程序 getTotalScoreGrade：非数值 / NaN / Infinity / 负数一律返回 null（不是
  // {gradeCode:null}），调用方自己判空。边界闭合在「≥」侧：90 / 80 / 60 本身属于高一档。
  // 90/80/60 在数据包里没有对应表（std 只有权重、上限与 BMI 分类），只能落在代码常量上。
  function gradeOf(total) {
    if (typeof total !== 'number' || !Number.isFinite(total) || total < 0) return null;
    if (total >= 90) return { gradeCode: 'excellent', gradeLabel: '优秀' };
    if (total >= 80) return { gradeCode: 'good', gradeLabel: '良好' };
    if (total >= 60) return { gradeCode: 'pass', gradeLabel: '及格' };
    return { gradeCode: 'fail', gradeLabel: '不及格' };
  }

  const STRENGTH_KEYS = ['pullUps', 'sitUps'];
  const ENDURANCE_KEYS = ['run1000m', 'run800m'];
  // 事件键 → 页面输入字段名；BMI 不在表里，它由 heightCm/weightKg 两项派生。
  const ANSWER_KEY = { vitalCapacity: 'vitalCapacity', sprint50m: 'sprint50m',
                       sitAndReach: 'sitAndReach', standingLongJump: 'standingLongJump',
                       pullUps: 'pullUps', sitUps: 'sitUps',
                       run1000m: 'run1000m', run800m: 'run800m' };

  // ── 汇总 ──
  // 语义照原程序 calculateFitnessResult，不照计划原文（计划把 status 优先级、未完成时的
  // 附加分、以及若干期望值写错了，见 task-5-report.md）：
  //   1) 标准分 = Σ(单项分 × weightPercent) / 100；单项都在全部 7 项 complete 后才给，
  //      未完成时 standardScore/totalScore/gradeCode 全 null，只有 partialStandardScore 有值；
  //   2) 附加分按「力量项 / 耐力项各自是否 complete」给（那一项没算 → null，不是 0）；
  //      totalBonus 只在整体 complete 时求和，否则 null；
  //   3) status 优先级 invalid > incomplete > unresolved（原程序依次判 inputErrors /
  //      missingFields / unresolvedRules，计划写成了 unresolved 优先）；
  //   4) totalScore 用整数分位 (cent + 100×bonus)/100 算，与原程序同式，再另给
  //      displayTotalScore 做 toFixed(1)。原程序不静默截断，越界直接抛不变量错误。
  function assemble(std, input) {
    const opts = input || {};
    // 性别要 trim：原程序 calculateFitnessResult 先 trim 再取 FITNESS_STANDARDS；
    // scoreEvent 也 trim，这里不 trim 会让 eventKeysFor 走进女表而逐项按男表判。
    const gender = typeof opts.gender === 'string' ? opts.gender.trim() : opts.gender;
    const grade = opts.grade;
    const answers = opts.answers || {};
    const keys = eventKeysFor(std, gender);
    const items = keys.map((k) => scoreEvent(std, {
      gender, grade, eventKey: k,
      raw: ANSWER_KEY[k] ? answers[ANSWER_KEY[k]] : undefined,
      inputs: answers,
    }));

    const count = { complete: 0, incomplete: 0, invalid: 0, unresolved: 0 };
    items.forEach((r) => { count[r.status] = (count[r.status] || 0) + 1; });
    const complete = count.complete === keys.length;
    const status = count.invalid ? 'invalid'
      : count.incomplete ? 'incomplete'
      : count.unresolved ? 'unresolved' : 'complete';

    // 整数分位累加避开 0.1 级浮点尾巴；∑权重 = 100，所以不会顶到 maxStandardScore。
    const cent = items.reduce((a, r) => a + (typeof r.weightedContribution === 'number'
      ? Math.round(r.weightedContribution * 100) : 0), 0);
    const partialStandardScore = cent / 100;

    const pick = (list) => items.find((r) => list.indexOf(r.eventKey) >= 0) || null;
    const bonusOf = (r) => (r && r.status === 'complete'
      ? (typeof r.bonusScore === 'number' ? r.bonusScore : 0) : null);
    const strengthBonus = bonusOf(pick(STRENGTH_KEYS));
    const enduranceBonus = bonusOf(pick(ENDURANCE_KEYS));
    const totalBonus = complete ? (strengthBonus || 0) + (enduranceBonus || 0) : null;

    let standardScore = null, totalScore = null, displayTotalScore = null;
    let gradeCode = null, gradeLabel = null;
    if (complete) {
      standardScore = partialStandardScore;
      totalScore = (cent + 100 * totalBonus) / 100;
      if (standardScore > std.limits.maxStandardScore
          || totalBonus > std.limits.maxTotalBonusScore
          || totalScore > std.limits.maxTotalScore) {
        // 原程序在这里 throw 而不是静默截断：越界只可能是数据包的上限/权重被改坏。
        throw new Error('Score limit invariant violated: standardScore=' + standardScore
          + ', bonusScore=' + totalBonus + ', totalScore=' + totalScore);
      }
      const g = gradeOf(totalScore);
      gradeCode = g ? g.gradeCode : null;
      gradeLabel = g ? g.gradeLabel : null;
      displayTotalScore = totalScore.toFixed(1);
    }

    const blockingReasons = ['invalid', 'incomplete', 'unresolved'].filter((s) => count[s] > 0);

    return { status, items, standardScore, strengthBonus, enduranceBonus, totalBonus,
             totalScore, gradeCode, gradeLabel, blockingReasons,
             partialStandardScore, displayTotalScore };
  }

  return { prepareStandard, gradeGroupOf, eventKeysFor, parseEnduranceTime, formatEnduranceTime,
           scaleOf, scoreLevel, scoreEvent, matchLevel, scoreAt, buildLevels, buildBonusTable,
           bmiOf, scoreBmi, parseDecimal, toStep, classifyRaw, pow10Big,
           computeBonus, gradeOf, assemble };
}));
