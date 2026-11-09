// 体测计算器页面逻辑（演示版）：读 tice-standard.json + tice-calc.js，实时算分。
// 不写任何存储、不联网。文案取原程序 utils/fitness-input-view.js 的原话。
(function () {
  'use strict';

  var CALC = window.TICE_CALC;
  var STD = null;
  var state = { gender: 'male', grade: '大一', values: {} };
  var lastResult = null;
  // 填完不自动出结果：必须点「生成结果」。任何改动都会把结果收回，避免旧结果挂在屏幕上。
  var resultShown = false;

  var PLACEHOLDER = {
    heightCm: '请输入有效数字，例如 175',
    weightKg: '请输入有效数字，例如 65.5',
    vitalCapacity: '请输入有效数字，例如 4200',
    sprint50m: '例如 7.5',
    sitAndReach: '例如 12.5 或 -3',
    standingLongJump: '例如 215',
    pullUps: '请输入整数次数，例如 8',
    sitUps: '请输入整数次数，例如 35',
    run1000m: '请输入有效用时，例如 4:20',
    run800m: '请输入有效用时，例如 4:20'
  };

  var HINT = {
    empty_string: '这一项还没填内容',
    invalid_type: '请输入有效数字',
    invalid_number_format: '请输入有效数字',
    must_be_integer: '请输入整数次数，例如 8',
    must_be_greater_than_zero: '必须大于 0',
    non_positive_time: '请输入大于 0 的有效用时，例如 4:20',
    ambiguous_decimal_time_format: '请输入整数分、秒，不使用小数，例如 4:20',
    invalid_minutes_or_seconds_range: '请输入有效用时（秒数须为 0～59），例如 4:20',
    invalid_endurance_time_format: '请输入有效用时，例如 4:20',
    measurement_out_of_range: '数值超出可计算范围'
  };

  var BADGE = {
    complete: '已计算',
    incomplete: '待填写',
    invalid: '需修正',
    unresolved: '规则待确认'
  };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function byId(id) { return document.getElementById(id); }

  function valueOf(id) {
    var n = byId('f-' + id);
    return n ? n.value : '';
  }

  function inputWrap(opt) {
    var wrap = el('div', 'tice-inputwrap');
    var input = el('input');
    input.id = 'f-' + opt.id;
    input.type = 'text';
    input.inputMode = opt.integer ? 'numeric' : 'decimal';
    input.autocomplete = 'off';
    input.placeholder = PLACEHOLDER[opt.id] || '';
    input.value = state.values[opt.id] || '';
    input.setAttribute('aria-describedby', 'h-' + opt.id);
    wrap.appendChild(input);
    if (opt.unit) wrap.appendChild(el('span', 'tice-suffix', opt.unit));
    return wrap;
  }

  function statsBlock(key) {
    var dl = el('dl', 'tice-stats');
    [['单项得分', 'score', '分'], ['权重', 'weight', ''], ['加权贡献', 'contrib', '']].forEach(function (c) {
      var cell = el('div');
      cell.appendChild(el('dt', null, c[0]));
      var dd = el('dd');
      var b = el('b', null, '—');
      b.id = 's-' + key + '-' + c[1];
      dd.appendChild(b);
      if (c[2]) dd.appendChild(el('span', 'u', c[2]));
      cell.appendChild(dd);
      dl.appendChild(cell);
    });
    return dl;
  }

  function statusLine(key) {
    var line = el('div', 'tice-statusline');
    var badge = el('span', 'tice-badge', BADGE.incomplete);
    badge.id = 'st-' + key;
    line.appendChild(badge);
    var measured = el('span', null, '');
    measured.id = 'm-' + key;
    line.appendChild(measured);
    return line;
  }

  function syncSegments() {
    [['gender', state.gender], ['grade', state.grade]].forEach(function (pair) {
      var box = byId('seg-' + pair[0]);
      if (!box) return;
      var buttons = Array.prototype.slice.call(box.querySelectorAll('button'));
      buttons.forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.v === pair[1])); });
      var idx = buttons.findIndex(function (b) { return b.dataset.v === pair[1]; });
      if (idx >= 0) box.style.setProperty('--i', String(idx));
    });
  }

  function buildBmiCard() {
    var sec = el('section', 'tice-card');
    sec.id = 'card-bmi';

    var head = el('div', 'tice-card-head');
    head.appendChild(el('h2', 'tice-card-title', '身体数据'));
    head.appendChild(el('span', 'tice-card-idx', 'BMI'));
    sec.appendChild(head);

    var duo = el('div', 'tice-duo');
    [['身高', 'heightCm', 'cm'], ['体重', 'weightKg', 'kg']].forEach(function (f) {
      var box = el('div');
      var lab = el('label', 'tice-duo-label', f[0]);
      lab.setAttribute('for', 'f-' + f[1]);
      box.appendChild(lab);
      box.appendChild(inputWrap({ id: f[1], unit: f[2] }));
      var hint = el('p', 'tice-hint');
      hint.id = 'h-' + f[1];
      box.appendChild(hint);
      duo.appendChild(box);
    });
    sec.appendChild(duo);

    var bmiRow = el('div', 'tice-bmi');
    var left = el('div');
    left.appendChild(el('span', 'tice-bmi-label', 'BMI'));
    var val = el('b', 'tice-bmi-value', '—');
    val.id = 'bmi-value';
    left.appendChild(val);
    bmiRow.appendChild(left);
    var cat = el('span', 'tice-badge', '—');
    cat.id = 'bmi-cat';
    bmiRow.appendChild(cat);
    sec.appendChild(bmiRow);

    sec.appendChild(statusLine('bmi'));
    sec.appendChild(statsBlock('bmi'));

    var note = el('p', 'tice-hint', '展示保留两位，评分按原始值判断');
    sec.appendChild(note);
    return sec;
  }

  function buildEventCard(key, index, total) {
    var ev = STD.events[key];
    var sec = el('section', 'tice-card');
    sec.id = 'card-' + key;

    var head = el('div', 'tice-card-head');
    head.appendChild(el('h2', 'tice-card-title', ev.name));
    head.appendChild(el('span', 'tice-card-idx',
      String(index).padStart(2, '0') + ' / ' + String(total).padStart(2, '0')));
    sec.appendChild(head);

    sec.appendChild(inputWrap({
      id: key, unit: ev.unitLabel, integer: ev.integerOnly
    }));

    var hint = el('p', 'tice-hint');
    hint.id = 'h-' + key;
    sec.appendChild(hint);

    sec.appendChild(statusLine(key));
    sec.appendChild(statsBlock(key));
    return sec;
  }

  function buildFields() {
    var form = byId('fields');
    form.textContent = '';

    var keys = CALC.eventKeysFor(STD, state.gender);
    var events = keys.filter(function (k) { return k !== 'bmi'; });
    form.appendChild(buildBmiCard());
    events.forEach(function (key, i) {
      form.appendChild(buildEventCard(key, i + 1, events.length));
    });
  }

  function setHint(id, text, warn) {
    var h = byId('h-' + id);
    var n = byId('f-' + id);
    if (h) {
      h.textContent = text || '';
      h.className = 'tice-hint' + (warn ? ' is-warn' : '');
    }
    if (n) {
      var wrap = n.parentNode;
      if (wrap && wrap.className.indexOf('tice-inputwrap') === 0) {
        wrap.className = 'tice-inputwrap' + (warn ? ' is-bad' : '');
      }
    }
  }

  function setStats(key, r, wp) {
    var score = byId('s-' + key + '-score');
    var weight = byId('s-' + key + '-weight');
    var contrib = byId('s-' + key + '-contrib');
    if (weight) weight.textContent = wp + '%';
    if (score) score.textContent = r.status === 'complete' ? String(r.score) : '—';
    if (contrib) {
      contrib.textContent = r.status === 'complete' && r.weightedContribution != null
        ? Number(r.weightedContribution).toFixed(1) : '—';
    }
    var badge = byId('st-' + key);
    if (badge) {
      badge.textContent = BADGE[r.status] || '';
      badge.dataset.state = r.status === 'complete' ? 'ok'
        : (r.status === 'invalid' ? 'bad' : (r.status === 'unresolved' ? 'uncertain' : ''));
    }
  }

  function scoreOne(key) {
    if (key === 'bmi') {
      return CALC.scoreEvent(STD, {
        gender: state.gender, grade: state.grade, eventKey: 'bmi',
        inputs: { heightCm: valueOf('heightCm'), weightKg: valueOf('weightKg') }
      });
    }
    return CALC.scoreEvent(STD, {
      gender: state.gender, grade: state.grade, eventKey: key, raw: valueOf(key)
    });
  }

  function renderReport(agg, items) {
    var box = byId('report');
    if (!box || !agg || !items) return;
    box.textContent = '';

    var head = el('div', 'tr-head');
    head.appendChild(el('span', 'tr-kicker', '单学年成绩结果'));
    head.appendChild(el('span', 'tr-count', '已确定 ' + items.length + ' / 7 项'));
    box.appendChild(head);

    var card = el('div', 'tr-card');

    var dh = el('div', 'tr-detail-head');
    dh.appendChild(el('b', null, '七项成绩明细'));
    dh.appendChild(el('span', null, '实测 · 单项分 · 权重 · 贡献'));
    card.appendChild(dh);

    var list = el('div', 'tr-list');
    var rows = [];
    items.forEach(function (it) {
      var row = el('div', 'tr-row');

      var rh = el('div', 'tr-row-head');
      rh.appendChild(el('span', 'tr-idx', String(it.idx).padStart(2, '0')));
      rh.appendChild(el('b', null, it.name));
      var badge = el('span', 'tr-badge', BADGE[it.status] || '');
      badge.dataset.state = it.status === 'complete' ? 'ok' : (it.status === 'invalid' ? 'bad' : 'uncertain');
      rh.appendChild(badge);
      row.appendChild(rh);

      var me = el('div', 'tr-measured');
      me.appendChild(el('span', null, '实测成绩'));
      // 只有 BMI 在实测值后面带分类（如「（正常）」）；其余项的括号会与单项分重复。
      var measured = it.measured || '—';
      if (it.key === 'bmi' && it.category) measured += '（' + it.category + '）';
      me.appendChild(el('b', null, measured));
      row.appendChild(me);

      var stats = el('dl', 'tr-stats');
      var cells = [
        ['单项分', it.status === 'complete' ? String(it.score) : '—'],
        ['权重', it.weight + '%'],
        ['加权贡献', it.status === 'complete' && it.contribution != null ? Number(it.contribution).toFixed(1) : '—']
      ];
      if (it.bonusEligible) cells.push(['附加分', '+' + (it.bonus || 0)]);
      cells.forEach(function (c) {
        var d = el('div');
        d.appendChild(el('dt', null, c[0]));
        d.appendChild(el('dd', null, c[1]));
        stats.appendChild(d);
      });
      row.appendChild(stats);

      rows.push(row);
      list.appendChild(row);
    });
    card.appendChild(list);

    // 读板放在明细之后：条目一条条铺下去，滚到底才看到总分。
    var readout = el('div', 'tr-readout');

    var top = el('div', 'tr-top');
    var total = el('div', 'tr-total');
    total.appendChild(el('span', 'tr-label', '学年总分'));
    var tb = el('b', null, '0.0');
    tb.id = 'report-total';
    total.appendChild(tb);
    total.appendChild(el('span', 'tr-of', '/ 120'));
    top.appendChild(total);

    var g = el('div', 'tr-grade');
    g.appendChild(el('span', 'tr-label', '评定等级'));
    g.appendChild(el('span', 'tr-badge', agg.gradeLabel || '—'));
    top.appendChild(g);
    readout.appendChild(top);

    var split = el('div', 'tr-split');
    [['标准分', agg.standardScore, '/ 100'],
     ['附加分', agg.totalBonus == null ? '—' : '+' + agg.totalBonus, '/ 20']].forEach(function (c) {
      var d = el('div');
      d.appendChild(el('span', 'tr-label', c[0]));
      d.appendChild(el('b', null, typeof c[1] === 'number' ? c[1].toFixed(1) : String(c[1])));
      d.appendChild(el('span', 'tr-of', ' ' + c[2]));
      split.appendChild(d);
    });
    readout.appendChild(split);

    var ov = el('div', 'tr-overview');
    ov.appendChild(el('b', null, '单学年体测成绩总览'));
    ov.appendChild(el('span', null, '七项已计算 · 单学年成绩估算'));
    readout.appendChild(ov);

    card.appendChild(readout);
    box.appendChild(card);

    box.appendChild(el('p', 'tr-foot is-strong', '自动暂存与历史记录仅保存在本机'));
    box.appendChild(el('p', 'tr-foot', '正式成绩以学校体测系统为准'));
    box.appendChild(el('p', 'tr-foot', '学生个人制作 · 仅供查询参考'));

    box.hidden = false;

    // 生成时间线：一行一行往下铺，滚动跟着走；到底之后再出总分。
    // 没有 rAF 的环境（测试垫片/极老浏览器）没有时间线可言，直接一次到位。
    var instant = !window.requestAnimationFrame;
    var STEP = 320;
    rows.forEach(function (row, i) {
      if (instant) { row.className = 'tr-row is-in'; return; }
      setTimeout(function () {
        row.className = 'tr-row is-in';
        if (row.scrollIntoView) row.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }, 140 + i * STEP);
    });

    if (instant) {
      readout.className = 'tr-readout is-in';
      animateTotal(agg.totalScore, byId('report-total'));
      return;
    }

    var lastRowAt = 140 + rows.length * STEP;
    setTimeout(function () {
      if (readout.scrollIntoView) readout.scrollIntoView({ behavior: 'smooth', block: 'end' });
      setTimeout(function () {
        readout.className = 'tr-readout is-in';
        animateTotal(agg.totalScore, byId('report-total'));
      }, 420);
    }, lastRowAt);
  }

  function measuredText(key) {
    if (key === 'bmi') {
      var h = Number(valueOf('heightCm'));
      var w = Number(valueOf('weightKg'));
      if (!(h > 0 && w > 0)) return '';
      var bv = CALC.bmiOf(h, w);
      return bv ? bv.toFixed(2) + ' ' + (STD.bmi.unitLabel || '') : '';
    }
    var typed = valueOf(key);
    if (!typed) return '';
    var ev = STD.events[key];
    if (ev.unitType === 'mmss') {
      var p = CALC.parseEnduranceTime(typed);
      if (p.ok) return CALC.formatEnduranceTime(p.seconds) || typed;
      return typed;
    }
    return typed + (ev.unitLabel ? ' ' + ev.unitLabel : '');
  }

  function render() {
    var keys = CALC.eventKeysFor(STD, state.gender);
    var sum = 0, done = 0, missing = 0, bad = 0;
    var reasons = {};
    var hints = [];
    var itemMeta = [];

    keys.forEach(function (key, idx) {
      var r = scoreOne(key);
      var wp = key === 'bmi' ? STD.bmi.weightPercent : STD.events[key].weightPercent;

      if (r.status === 'complete') { sum += r.score * wp; done += 1; }
      else if (r.status === 'incomplete') missing += 1;
      else if (r.status === 'invalid') bad += 1;
      else if (r.status === 'unresolved') reasons[r.code] = true;

      setStats(key, r, wp);

      itemMeta.push({
        idx: idx + 1,
        key: key,
        name: key === 'bmi' ? '体重指数（BMI）' : STD.events[key].name,
        status: r.status,
        score: r.score,
        weight: wp,
        contribution: r.weightedContribution,
        bonus: key === 'bmi' ? null : r.bonusScore,
        bonusEligible: key === 'bmi' ? false : !!STD.events[key].bonusEligible,
        measured: measuredText(key),
        category: (r.status === 'complete' && r.levelResult) ? r.levelResult.level : ''
      });

      if (key === 'bmi') {
        var hCm = Number(valueOf('heightCm'));
        var wKg = Number(valueOf('weightKg'));
        var bv = (hCm > 0 && wKg > 0) ? CALC.bmiOf(hCm, wKg) : null;
        var valNode = byId('bmi-value');
        var catNode = byId('bmi-cat');
        if (valNode) valNode.textContent = bv ? bv.toFixed(2) : '—';
        if (catNode) {
          if (r.status === 'complete' && r.levelResult) {
            catNode.textContent = r.levelResult.level;
            catNode.dataset.state = 'ok';
          } else if (r.status === 'unresolved') {
            catNode.textContent = '待确认';
            catNode.dataset.state = 'uncertain';
          } else if (r.status === 'invalid') {
            catNode.textContent = '需修正';
            catNode.dataset.state = 'bad';
          } else {
            catNode.textContent = '—';
            catNode.dataset.state = '';
          }
        }
        var bmiMsg = r.status === 'invalid'
          ? (r.errorCopy || HINT[r.code] || '请检查这一项')
          : (r.hint || '');
        if (r.hint) hints.push(r.hint);
        // 身高、体重各自有字段级提示（如「疑似填写了毫米」），别被 BMI 的合并提示盖住。
        var hHint = '', wHint = '';
        if (window.TICE_CHECKS && window.TICE_CHECKS.validateField) {
          var hv = window.TICE_CHECKS.validateField('heightCm', valueOf('heightCm'), state.values);
          var wv = window.TICE_CHECKS.validateField('weightKg', valueOf('weightKg'), state.values);
          hHint = (hv && hv.hint) || '';
          wHint = (wv && wv.hint) || '';
          if (hHint) hints.push(hHint);
          if (wHint) hints.push(wHint);
        }
        setHint('heightCm', hHint || bmiMsg, r.status === 'invalid' && !hHint);
        setHint('weightKg', wHint || bmiMsg, r.status === 'invalid' && !wHint);
        var measured = byId('m-bmi');
        if (measured) measured.textContent = '';
      } else {
        // 两种提示分开：invalid 用错误文案（红），其余用体检提示（灰，不影响判定）。
        setHint(key,
          r.status === 'invalid' ? (r.errorCopy || HINT[r.code] || '请检查这一项') : (r.hint || ''),
          r.status === 'invalid');
        if (r.hint) hints.push(r.hint);
        // 这一行是「实测」——必须回显**用户填的值**，不是命中的档位阈值。
        // 早先接了 levelResult.rawDisplay，于是填 6327 会显示该项满分档的门槛值。
        var m = byId('m-' + key);
        if (m) {
          var typed = valueOf(key);
          var evDef = STD.events[key];
          var shown = typed;
          var unitLabel = evDef.unitLabel || '';
          if (typed && evDef.unitType === 'mmss') {
            // 长跑输入可能是 '210' / '3:30'，回显统一成分·秒字面量，别再挂「分·秒」单位。
            var parsed = CALC.parseEnduranceTime(typed);
            if (parsed.ok) { shown = CALC.formatEnduranceTime(parsed.seconds) || typed; unitLabel = ''; }
          }
          m.textContent = typed ? '实测 ' + shown + (unitLabel ? ' ' + unitLabel : '') : '';
        }
      }
    });

    var totalNode = byId('total');
    var gradeNode = byId('grade');
    var answers = Object.assign({}, state.values);
    // Task 5 的 assemble 是总分的唯一口径（含附加分与等级）；拿不到才退回本页手算。
    var agg = null;
    try {
      agg = CALC.assemble ? CALC.assemble(STD, { gender: state.gender, grade: state.grade, answers: answers }) : null;
    } catch (e) { agg = null; }

    var standard = agg && typeof agg.standardScore === 'number' ? agg.standardScore : sum / 100;
    var totalScore = agg && typeof agg.totalScore === 'number' ? agg.totalScore : standard;

    // 结果门控：没点按钮就只显示进度，不把分数摊出来。
    var allDone = done === 7 && bad === 0 && !Object.keys(reasons).length;
    var card = byId('scorecard');
    var calcBtn = byId('calcbtn');
    if (calcBtn) calcBtn.disabled = !allDone || resultShown;
    if (card) card.className = 'tice-score' + (resultShown ? ' is-in' : ' is-pending');

    if (!resultShown) {
      totalNode.textContent = '—';
      gradeNode.textContent = done === 0 ? '等待填写'
        : (bad > 0 ? '存在需修正的输入字段'
          : (allDone ? '已填完，点「生成结果」' : '已填 ' + done + '/7 项'));
    } else {
      totalNode.textContent = totalScore.toFixed(1);
      gradeNode.textContent = (agg && agg.gradeLabel) ? agg.gradeLabel : gradeOf(standard);
    }

    // 总分拆开写：标准分 + 附加分（力量/耐力各多少），别让「99.4」看不出是不是加了分。
    var bd = byId('breakdown');
    if (bd) {
      if (resultShown && agg && agg.totalBonus != null) {
        var parts = [];
        if (agg.strengthBonus != null) parts.push('力量 +' + agg.strengthBonus);
        if (agg.enduranceBonus != null) parts.push('耐力 +' + agg.enduranceBonus);
        bd.textContent = '标准分 ' + (agg.standardScore != null ? Number(agg.standardScore).toFixed(1) : '—')
          + ' · 附加分 +' + agg.totalBonus + (parts.length ? '（' + parts.join(' / ') + '）' : '');
        bd.hidden = false;
      } else {
        bd.textContent = '';
        bd.hidden = true;
      }
    }

    lastResult = {
      standardScore: standard,
      totalScore: totalScore,
      gradeLabel: agg && agg.gradeLabel ? agg.gradeLabel : gradeOf(standard),
      answers: answers,
      items: itemMeta,
      agg: agg,
      complete: done === 7 && bad === 0 && !Object.keys(reasons).length
    };

    var report = byId('report');
    if (report && !resultShown) report.hidden = true;

    var note = byId('note');
    var msgs = [];
    if (bad > 0) msgs.push('请修正下方列出的输入字段，完整成绩暂不可生成。');
    if (missing > 0) msgs.push('尚未完成全部项目，已算出的分项得分与加权贡献已保留；补齐全部七项后生成完整总分。');
    if (hints.length && window.TICE_CHECKS && window.TICE_CHECKS.summaryOfHints) {
      msgs.push(window.TICE_CHECKS.summaryOfHints(hints));
    }
    if (reasons.measurement_precision_rounding_unresolved) {
      msgs.push('原始精度高于评分表刻度，取位可能跨档，暂不能确定分数。建议按学校系统记录的实际精度填写。');
    }
    if (reasons.bmi_boundary_precision_unresolved) {
      msgs.push('BMI落在公开表格相邻区间之间，取位规则尚未明确，暂不能确定分数。');
    }
    note.textContent = msgs.join(' ');
    note.className = 'tice-note' + (msgs.length ? ' is-warn' : '');
    note.hidden = msgs.length === 0;
  }

  // 总分数字「慢慢出来」：0 → 目标值，缓动 900ms；没有 rAF 就直接落值。
  function animateTotal(to, node) {
    node = node || byId('total');
    if (!node || typeof to !== 'number' || !isFinite(to)) return;
    if (!window.requestAnimationFrame) { node.textContent = to.toFixed(1); return; }
    var dur = 900;
    var t0 = null;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      node.textContent = (to * eased).toFixed(1);
      if (p < 1) window.requestAnimationFrame(step);
      else node.textContent = to.toFixed(1);
    }
    window.requestAnimationFrame(step);
  }

  // 结果页整体「缓缓铺开」：先 0 高度，下一帧过渡到内容高度，页面因此被慢慢往下推。
  function unfoldReport() {
    var rep = byId('report');
    if (!rep) return;
    rep.hidden = false;
    if (!rep.classList || !window.requestAnimationFrame) return;
    rep.classList.add('is-unfolding');
    rep.style.maxHeight = '0px';
    window.requestAnimationFrame(function () {
      rep.style.maxHeight = (rep.scrollHeight || 720) + 'px';
      setTimeout(function () {
        rep.style.maxHeight = '';
        rep.classList.remove('is-unfolding');
      }, 760);
    });
  }

  // 演示口径：等级边界尚未进 JSON（Task 5 会搬进去），先按公开规则的 90/80/60 显示。
  function gradeOf(total) {
    if (total >= 90) return '优秀';
    if (total >= 80) return '良好';
    if (total >= 60) return '及格';
    return '不及格';
  }

  function bindSegments() {
    ['gender', 'grade'].forEach(function (name) {
      var box = byId('seg-' + name);
      box.addEventListener('click', function (e) {
        var btn = e.target.closest ? e.target.closest('button[data-v]') : null;
        if (!btn) return;
        var v = btn.dataset.v;
        if (state[name] === v) return;
        state[name] = v;
        var buttons = Array.prototype.slice.call(box.querySelectorAll('button'));
        buttons.forEach(function (b) {
          b.setAttribute('aria-pressed', String(b.dataset.v === v));
        });
        // 滑动块：整块 thumb 平移，不用逐个按钮换底色
        box.style.setProperty('--i', String(buttons.indexOf(btn)));
        resultShown = false;
        if (name === 'gender') buildFields();
        render();
      });
    });
  }

  // 顶栏：下滑收起、上滑出现（field.js 有这套，但本页不引它，得自己接）。
  function bindHeaderScroll() {
    var bar = document.querySelector ? document.querySelector('.topbar') : null;
    if (!bar || !bar.classList || !window.addEventListener) return;
    var lastY = window.pageYOffset || 0;
    window.addEventListener('scroll', function () {
      var y = window.pageYOffset || (document.documentElement && document.documentElement.scrollTop) || 0;
      if (y < 80) { bar.classList.remove('is-up'); lastY = y; return; }
      if (y > lastY + 6) bar.classList.add('is-up');
      else if (y < lastY - 6) bar.classList.remove('is-up');
      lastY = y;
    }, { passive: true });
  }

  function bindTheme() {
    var btn = byId('themesw');
    btn.addEventListener('click', function () {
      var dark = document.documentElement.dataset.theme === 'cobalt-dark';
      document.documentElement.dataset.theme = dark ? 'cobalt-field' : 'cobalt-dark';
      btn.setAttribute('aria-pressed', String(!dark));
      btn.setAttribute('aria-label', dark ? '切到夜间模式' : '切到日间模式');
    });
  }

  // ── 本机档案（Task 10）────────────────────────────────────────
  var storeApi = null;
  var draftTimer = null;

  function getStore() {
    if (storeApi) return storeApi;
    if (!window.TICE_STORE) return null;
    try { storeApi = window.TICE_STORE.create(window.localStorage); } catch (e) { storeApi = null; }
    return storeApi;
  }

  function stamp(isoStr) {
    var t = Date.parse(isoStr || '');
    if (!t) return '';
    var d = new Date(t);
    return (d.getMonth() + 1) + '月' + d.getDate() + '日';
  }

  function showNote(text) {
    var note = byId('note');
    if (!note) return;
    note.textContent = text;
    note.className = 'tice-note is-warn';
    note.hidden = false;
  }

  function loadRecord(rec) {
    state.values = Object.assign({}, rec.answers || {});
    buildFields();
    render();
  }

  function removeRecord(rec) {
    var s = getStore();
    if (!s) return;
    var r = s.archives.remove(rec.id);
    if (!r.ok) showNote(r.copy);
    renderHistory();
  }

  function duplicateRecord(rec) {
    var s = getStore();
    if (!s) return;
    var r = s.archives.duplicateAsNew(rec.id);
    if (!r.ok) showNote(r.copy);
    renderHistory();
  }

  function closePanel() {
    var mask = byId('archive-mask');
    var panel = byId('archive-panel');
    if (mask) mask.hidden = true;
    if (panel) panel.hidden = true;
  }

  function commit(rec, inputs) {
    var s = getStore();
    if (!s) { showNote('本机存储不可用，记录无法保存。'); return; }
    var base = rec || {
      standardScore: lastResult ? lastResult.standardScore : null,
      totalScore: lastResult ? lastResult.totalScore : null,
      gradeLabel: lastResult ? lastResult.gradeLabel : '',
      answers: lastResult ? lastResult.answers : {}
    };
    var payload = Object.assign({}, base, {
      academicYear: inputs.academicYear.value.trim(),
      name: inputs.name.value.trim(),
      college: inputs.college.value.trim(),
      major: inputs.major.value.trim()
    });
    var r = s.archives.upsert(payload, { requireYear: true });
    if (!r.ok) {
      var err = byId('archive-err');
      if (err) { err.textContent = r.copy; err.hidden = false; }
      return;
    }
    closePanel();
    renderHistory();
  }

  function openPanel(rec) {
    var panel = byId('archive-panel');
    var mask = byId('archive-mask');
    if (!panel || !mask) return;
    panel.textContent = '';

    var title = el('h2', null, rec ? '编辑档案' : '保存到本机');
    title.id = 'archive-title';
    panel.appendChild(title);

    var inputs = {};
    [['academicYear', '学年', '如 2026-2027 学年'],
     ['name', '姓名', '可留空'],
     ['college', '学院', '可留空'],
     ['major', '专业', '可留空']].forEach(function (f) {
      var row = el('div', 'tice-form-row');
      var lab = el('label', null, f[1]);
      lab.setAttribute('for', 'a-' + f[0]);
      row.appendChild(lab);
      var input = el('input');
      input.id = 'a-' + f[0];
      input.type = 'text';
      input.placeholder = f[2];
      input.value = (rec && rec[f[0]]) || '';
      row.appendChild(input);
      inputs[f[0]] = input;
      panel.appendChild(row);
    });

    var err = el('p', 'tice-form-err');
    err.id = 'archive-err';
    err.hidden = true;
    panel.appendChild(err);

    var actions = el('div', 'tice-form-actions');
    var cancel = el('button', 'tice-btn', '取消');
    cancel.type = 'button';
    cancel.addEventListener('click', closePanel);
    var ok = el('button', 'tice-btn is-primary', '保存');
    ok.type = 'button';
    ok.addEventListener('click', function () { commit(rec, inputs); });
    actions.appendChild(cancel);
    actions.appendChild(ok);
    panel.appendChild(actions);

    mask.hidden = false;
    panel.hidden = false;
    if (inputs.academicYear.focus) inputs.academicYear.focus();
  }

  function renderHistory() {
    var box = byId('history');
    if (!box) return;
    box.textContent = '';

    var head = el('div', 'tice-history-head');
    head.appendChild(el('h2', 'tice-card-title', '本机记录'));
    head.appendChild(el('span', 'tice-card-idx', '只存这台设备'));
    box.appendChild(head);

    var s = getStore();
    if (!s || !s.available) {
      box.appendChild(el('p', 'tice-note is-warn', '本机存储不可用，记录无法保存。'));
      return;
    }
    var list = s.archives.list();
    if (!list.ok) { box.appendChild(el('p', 'tice-note is-warn', list.copy)); return; }
    if (!list.length) {
      box.appendChild(el('p', 'tice-note', '还没有保存过成绩。填完后点「保存本次」。'));
      return;
    }

    list.forEach(function (rec) {
      var row = el('div', 'tice-hrow');
      row.appendChild(el('span', 'tice-hyear', rec.academicYear || '未填学年'));
      row.appendChild(el('span', 'tice-hscore',
        (rec.totalScore == null ? '—' : rec.totalScore) + ' · ' + (rec.gradeLabel || '—')));
      row.appendChild(el('span', 'tice-htime', stamp(rec.savedAt)));

      var acts = el('span', 'tice-hacts');
      [['载入', function () { loadRecord(rec); }],
       ['编辑', function () { openPanel(rec); }],
       ['复制', function () { duplicateRecord(rec); }],
       ['删除', function () { removeRecord(rec); }]].forEach(function (a) {
        var b = el('button', 'ghostbtn', a[0]);
        b.type = 'button';
        b.addEventListener('click', a[1]);
        acts.appendChild(b);
      });
      row.appendChild(acts);
      box.appendChild(row);
    });
  }

  function renderDeclaration() {
    // 外壳是 <details>（默认收起，点标题展开），正文只往 body 里填。
    var box = byId('declaration-body');
    if (!box) return;
    box.textContent = '';

    var meta = STD.meta || {};
    box.appendChild(el('p', null,
      '评分表：《' + String(meta.standardName || '').replace(/^《|》$/g, '') + '》（' + (meta.standardDocNo || '') + '）；'
      + '校方实施办法：' + (meta.schoolPolicyName || '') + '（' + (meta.schoolPolicyDocNo || '') + '）。'));

    if (meta.policyEffectiveScope) {
      var scope = el('p', null, meta.policyEffectiveScope);
      scope.className = 'u';
      box.appendChild(scope);
    }

    var rules = STD.unresolvedRules || {};
    var keys = Object.keys(rules);
    if (keys.length) {
      box.appendChild(el('p', null, '以下三条规则公开资料未给出唯一答案，本页按「暂不能确定」处理，不替你补规则：'));
      var ul = el('ul');
      keys.forEach(function (k) {
        ul.appendChild(el('li', null, rules[k].description));
      });
      box.appendChild(ul);
    }

    box.appendChild(el('p', null, '评分表来自公开资料，结果仅供参考；实际成绩以学校体测系统的记录为准。'));

    if (meta.sourceSha256) {
      box.appendChild(el('p', null,
        '数据快照：' + (meta.derivedAt || '') + ' 由解包产物派生，源包摘要 ' + meta.sourceSha256 + '…（只取数据，不搬代码）。'));
    }
  }

  function saveDraftSoon() {
    var s = getStore();
    if (!s || !s.available) return;
    if (draftTimer) clearTimeout(draftTimer);
    draftTimer = setTimeout(function () {
      s.draft.save({ gender: state.gender, grade: state.grade, values: state.values });
    }, 400);
  }

  function start(data) {
    STD = CALC.prepareStandard(data);
    // 体检模块要先拿到同一份标准（阈值/允许面都在数据里，不在代码里）。
    if (window.TICE_CHECKS && window.TICE_CHECKS.configure) window.TICE_CHECKS.configure(data);

    // 先读本机暂存：刷新/关页后回来，填过的值还在（只在这一台设备上）。
    var s = getStore();
    if (s && s.available) {
      var draft = s.draft.load();
      if (draft && draft.ok && draft.value && typeof draft.value === 'object') {
        var dv = draft.value;
        state.values = Object.assign({}, dv.values || dv);
        if (dv.gender === 'female' || dv.gender === 'male') state.gender = dv.gender;
        if (dv.grade && STD.gradeToGroup[dv.grade]) state.grade = dv.grade;
      }
    }

    buildFields();
    syncSegments();

    var form = byId('fields');
    form.addEventListener('input', function (e) {
      var t = e && e.target;
      if (t && t.id && t.id.indexOf('f-') === 0) state.values[t.id.slice(2)] = t.value;
      resultShown = false;          // 改一个数就把结果收回，避免旧分数挂在屏幕上
      render();
      saveDraftSoon();
    });

    bindSegments();
    bindTheme();
    bindHeaderScroll();
    render();
    renderHistory();
    renderDeclaration();

    var saveBtn = byId('savebtn');
    if (saveBtn) {
      saveBtn.addEventListener('click', function () {
        if (!lastResult || lastResult.totalScore == null) { showNote('先把成绩填上再保存。'); return; }
        openPanel(null);
      });
    }

    var calcBtn = byId('calcbtn');
    if (calcBtn) {
      calcBtn.addEventListener('click', function () {
        if (!lastResult) return;
        resultShown = true;
        render();
        animateTotal(lastResult.totalScore);
        renderReport(lastResult.agg, lastResult.items);
        unfoldReport();
        var report = byId('report');
        if (report && report.scrollIntoView) report.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }
  }

  function fail(msg) {
    var note = byId('note');
    note.textContent = msg;
    note.className = 'tice-note is-warn';
    note.hidden = false;
  }

  if (!CALC) { fail('算分内核没加载成功（tice-calc.js）。'); return; }
  fetch('tice-standard.json', { cache: 'no-store' })
    .then(function (res) {
      if (!res.ok) throw new Error(String(res.status));
      return res.json();
    })
    .then(start)
    .catch(function (e) { fail('评分标准没读到：' + e.message + '。请确认 tice-standard.json 与页面同目录。'); });
}());



