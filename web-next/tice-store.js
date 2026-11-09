// 体测本机存储层：自动暂存 + 按学年存档 + 四种失败保护 + 导出脱敏。
//
// 这一层是纯函数层：所有读写只走 create(backend) 注入进来的那个后端对象
// （页面传浏览器的本机存储对象，测试传内存假后端）。本文件不碰 DOM、不碰任何
// 全局存储对象、不发任何网络请求，也不 require 别的模块，所以能直接在 node 里
// require 跑断言。四个失败分支各自返回 { ok: false, copy }，copy 全部是设计文档
// §9 或原程序里的原话（见 COPY 表里的出处注释），页面只负责照原样显示。
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.TICE_STORE = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // 键名照设计文档 §9 原文。版本号已经写在键名里（后缀 _v1），再加前缀就等于
  // 写了两套版本标记，改名时必然漏一个，所以按原样用。
  const SCHEMA = 'v1';
  const LEGACY_SCHEMA = 'v0';
  const KEYS = {
    draft: 'tice_draft_v1',      // 当前填写 + 时间戳
    archives: 'tice_archives_v1' // 按学年的存档数组
  };

  // 存档条数上限。设计文档没给具体条数（只要求「防止无限增长」），这里按容量倒算：
  // 单存档约 1–2 KB，50 条 ≈ 100 KB，远低于本机存储常见的 5 MB 配额，同时够覆盖
  // 本科四年每学年多份记录的用法。超出时淘汰 savedAt 最旧的，写盘仍然成功，但把
  // 被淘汰的 id 放在返回值 dropped 里，页面若想提示用户可以直接用。
  const MAX_ARCHIVES = 50;

  // 资料三项：只落本机，永不进任何导出/复制/分享文本（设计文档 §9.1 末段）。
  // 注意区分：items[].name 是项目名（肺活量/50米…），record.name 才是姓名。
  const PII_KEYS = ['name', 'college', 'major'];
  // 档案编辑浮层的六个字段里除学年之外的五项（学年是存档的键，单独校验）。
  const PROFILE_KEYS = ['name', 'college', 'major', 'enrollGrade', 'note'];

  const PROBE_KEY = '__tice_probe__';

  // 总分卡下方小字（设计文档 §10 原文）。
  const REFERENCE_NOTE = '仅供参考，实际成绩以学校体测系统记录为准。';

  const COPY = {
    // §9 保护 1 原文（spec 里没有句末句号，这里也不加，测试按原文比对）
    draftReadFail: '本地暂存读取失败或版本暂不支持，原数据已保留；当前填写暂不能覆盖它',
    // §9 保护 2 原文
    draftWriteFail: '自动暂存失败，当前填写仍在页面中；请勿将本机记录作为唯一凭证',
    // §9 保护 3 原文
    deleteFail: '删除失败，原记录已保留',
    // §9 保护 4 原文
    saveFail: '保存失败，原存档未被替换，请稍后重试',
    // §3 要求「暂存读、写、清三种失败各有文案」，§9 只给了读与写两句；
    // 清暂存的文案取原程序 pages/fitness/index 的 onRestart 原文，不另造措辞。
    draftClearFail: '暂存清除失败，原填写已保留',
    // 历史读取失败：§9 保护 1 只讲了暂存；历史这一支取原程序
    // pages/fitness-history/index 的 refresh 原文（同构，且已在原程序里用过）。
    historyFail: '历史读取失败或版本暂不支持，原存储已保留',
    // §9.1 原文
    yearRequired: '请填写学年',
    // 原程序 pages/fitness-history/index 的 onCopy 原文（Task 10 用它）
    copyFail: '复制失败，原暂存与存档已保留',
    // §11 空态原文，页面在 available === false 时显示
    unavailable: '本机存储不可用'
  };

  function isPlainObject(v) {
    return !!v && typeof v === 'object' && !Array.isArray(v);
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function dash(v) {
    if (v === null || v === undefined) return '—';
    if (typeof v === 'string' && v.trim() === '') return '—';
    return String(v);
  }

  function numText(v) {
    return v === null || v === undefined || v === '' ? '—' : String(v);
  }

  function hasAcademicYear(v) {
    if (typeof v === 'string') return v.trim() !== '';
    return typeof v === 'number' && Number.isFinite(v);
  }

  function create(backend) {
    const usable = !!backend
      && typeof backend.getItem === 'function'
      && typeof backend.setItem === 'function'
      && typeof backend.removeItem === 'function';

    // 可用性探针：写得进、读得回才算可用。整块存储不可用（隐私模式一类）时
    // 页面只留算分，暂存与历史一起降级，并显示 COPY.unavailable。
    let available = false;
    if (usable) {
      try {
        backend.setItem(PROBE_KEY, '1');
        available = backend.getItem(PROBE_KEY) === '1';
      } catch (e) {
        available = false;
      }
      try {
        backend.removeItem(PROBE_KEY);
      } catch (e) {
        // 探针键残留一个不影响读写，不算不可用
      }
    }

    // 读一条原始文本：区分「读失败」与「本来就没有」——两者绝不能混成一个分支，
    // 否则读失败会被当成空存储，接着写入就把原数据覆盖了。
    function readRaw(key) {
      if (!usable) return { ok: false, text: null };
      try {
        const v = backend.getItem(key);
        if (v === null || v === undefined) return { ok: true, text: null };
        return { ok: true, text: String(v) };
      } catch (e) {
        return { ok: false, text: null };
      }
    }

    function rawGet(key) {
      const r = readRaw(key);
      return r.ok ? r.text : null;
    }

    function rawSet(key, text) {
      if (!usable) return false;
      try {
        backend.setItem(key, String(text));
        return true;
      } catch (e) {
        return false;
      }
    }

    function rawDel(key) {
      if (!usable) return false;
      try {
        backend.removeItem(key);
        return true;
      } catch (e) {
        return false;
      }
    }

    // 先序列化到局部变量，成功之后才写；中途抛错时盘上的旧值一个字节都没动过。
    function serialize(payload) {
      try {
        const body = Object.assign({ __schema: SCHEMA }, payload);
        return { ok: true, text: JSON.stringify(body) };
      } catch (e) {
        return { ok: false, text: null };
      }
    }

    // ── 暂存 ──────────────────────────────────────────────────────
    // 版本迁移：载荷带 __schema:'v0'（或干脆没带标记的旧形态）时，只在内存里补成
    // v1 读出来，不主动回写——读操作不该顺手改盘。真正的升级发生在下一次 save。
    function readDraftPayload() {
      // 整块存储不可用时读也不可信（§9：暂存与历史一起降级），不装作「没有数据」
      if (!available) return { ok: false, copy: COPY.draftReadFail };
      const r = readRaw(KEYS.draft);
      if (!r.ok) return { ok: false, copy: COPY.draftReadFail };
      if (r.text === null) return { ok: true, payload: null };
      let parsed;
      try {
        parsed = JSON.parse(r.text);
      } catch (e) {
        return { ok: false, copy: COPY.draftReadFail };
      }
      if (!isPlainObject(parsed)) return { ok: false, copy: COPY.draftReadFail };
      const version = parsed.__schema;
      const recognised = version === SCHEMA || version === LEGACY_SCHEMA;
      const untouched = version === undefined || version === null;
      if (!recognised && !untouched) return { ok: false, copy: COPY.draftReadFail };
      if (!('value' in parsed)) return { ok: false, copy: COPY.draftReadFail };
      return {
        ok: true,
        payload: {
          value: parsed.value === undefined ? null : parsed.value,
          savedAt: typeof parsed.savedAt === 'string' ? parsed.savedAt : null
        },
        migratedFrom: recognised && version === LEGACY_SCHEMA ? LEGACY_SCHEMA
          : (untouched ? LEGACY_SCHEMA : null)
      };
    }

    // 资料三项只进存档对象（Task 10 的纪律）：暂存层即使被误传了这三个键，也不落盘。
    function sanitizeDraft(value) {
      if (!isPlainObject(value)) return value;
      let touched = false;
      const out = {};
      Object.keys(value).forEach((k) => {
        if (PII_KEYS.indexOf(k) >= 0) { touched = true; return; }
        out[k] = value[k];
      });
      return touched ? out : value;
    }

    const draft = {
      // { ok, value, savedAt, migratedFrom }：空存储读出 value === null，不抛
      load() {
        const r = readDraftPayload();
        if (!r.ok) return { ok: false, copy: r.copy, value: null, savedAt: null };
        if (!r.payload) return { ok: true, value: null, savedAt: null, migratedFrom: null };
        return {
          ok: true,
          value: r.payload.value,
          savedAt: r.payload.savedAt,
          migratedFrom: r.migratedFrom || null
        };
      },
      save(value) {
        if (!available) return { ok: false, copy: COPY.draftWriteFail };
        const cur = readDraftPayload();
        // 盘上有数据但读不出来 → 不许覆盖它，报「原数据已保留」那句（§9 保护 1）
        if (!cur.ok) return { ok: false, copy: COPY.draftReadFail };
        const savedAt = nowIso();
        const safe = value === undefined ? null : sanitizeDraft(value);
        const wrapped = serialize({ value: safe, savedAt });
        if (!wrapped.ok) return { ok: false, copy: COPY.draftWriteFail };
        if (!rawSet(KEYS.draft, wrapped.text)) return { ok: false, copy: COPY.draftWriteFail };
        return { ok: true, savedAt };
      },
      clear() {
        if (!available) return { ok: false, copy: COPY.draftClearFail };
        const cur = readDraftPayload();
        // 版本不认识的暂存不删：宁可清不掉，也不销毁看不懂的原数据
        if (!cur.ok) return { ok: false, copy: COPY.draftClearFail };
        if (!rawDel(KEYS.draft)) return { ok: false, copy: COPY.draftClearFail };
        return { ok: true };
      }
    };

    // ── 存档 ──────────────────────────────────────────────────────
    // 只保留普通对象条目：数组里混进来的 null/字符串/数组既渲染不了，也不该被
    // 当成一条记录继续存下去。
    function sanitizeRecords(list) {
      return list
        .filter((x) => isPlainObject(x))
        .map((x) => Object.assign({}, x));
    }

    function readArchivesPayload() {
      if (!available) return { ok: false, copy: COPY.historyFail };
      const r = readRaw(KEYS.archives);
      if (!r.ok) return { ok: false, copy: COPY.historyFail };
      if (r.text === null) return { ok: true, payload: { records: [] } };
      let parsed;
      try {
        parsed = JSON.parse(r.text);
      } catch (e) {
        return { ok: false, copy: COPY.historyFail };
      }
      // v0 旧形态：整条就是一个裸数组，没有版本信封
      if (Array.isArray(parsed)) {
        return { ok: true, payload: { records: sanitizeRecords(parsed) }, migratedFrom: LEGACY_SCHEMA };
      }
      if (!isPlainObject(parsed)) return { ok: false, copy: COPY.historyFail };
      const version = parsed.__schema;
      if (version !== SCHEMA && version !== LEGACY_SCHEMA) return { ok: false, copy: COPY.historyFail };
      if (!Array.isArray(parsed.records)) return { ok: false, copy: COPY.historyFail };
      return {
        ok: true,
        payload: { records: sanitizeRecords(parsed.records) },
        migratedFrom: version === LEGACY_SCHEMA ? LEGACY_SCHEMA : null
      };
    }

    function savedAtOf(rec) {
      const t = Date.parse(rec && rec.savedAt);
      return Number.isFinite(t) ? t : -Infinity;
    }

    // 超出上限时保留 savedAt 最新的 MAX_ARCHIVES 条；同一毫秒按「后写入的优先」
    // （数组靠后即后写）。被淘汰的单独返回，避免悄悄丢数据时调用方一无所知。
    function capRecords(records) {
      if (records.length <= MAX_ARCHIVES) return { kept: records, dropped: [] };
      const rank = records.map((rec, i) => ({ i, t: savedAtOf(rec) }))
        .sort((a, b) => (b.t - a.t) || (b.i - a.i));
      const keep = new Set(rank.slice(0, MAX_ARCHIVES).map((x) => x.i));
      const kept = [];
      const dropped = [];
      records.forEach((rec, i) => { (keep.has(i) ? kept : dropped).push(rec); });
      return { kept, dropped };
    }

    function nextId(records) {
      const used = new Set(records.map((x) => x.id));
      for (let n = 0; n < 64; n += 1) {
        const id = 't' + Date.now().toString(36) + Math.floor(Math.random() * 1296).toString(36);
        if (!used.has(id)) return id;
      }
      return 't' + Date.now().toString(36) + '-' + records.length;
    }

    const archives = {
      // 返回数组（Task 10 直接 map/find）。数组上另挂 ok/copy：读取失败时页面
      // 显示 copy 原文，而不是把「历史读取失败」错报成「还没有本机存档」。
      list() {
        const r = readArchivesPayload();
        const records = r.ok ? r.payload.records : [];
        records.ok = r.ok;
        records.copy = r.ok ? '' : r.copy;
        return records;
      },
      // 同一次读的完整结果，给需要区分失败原因的调用方
      read() {
        const r = readArchivesPayload();
        return r.ok
          ? { ok: true, value: r.payload.records.slice() }
          : { ok: false, copy: r.copy, value: [] };
      },
      // options.requireYear === false 只给 duplicateAsNew 用：复制出来的记录学年
      // 先置空，由用户在档案浮层里填，填完再 upsert 一次（此时才校验学年）。
      upsert(record, options) {
        const requireYear = !(options && options.requireYear === false);
        if (!isPlainObject(record)) return { ok: false, copy: COPY.saveFail };
        if (requireYear && !hasAcademicYear(record.academicYear)) {
          return { ok: false, copy: COPY.yearRequired };
        }
        if (!available) return { ok: false, copy: COPY.saveFail };
        const cur = readArchivesPayload();
        // 读不出来就别写：任何写入都等于把看不懂的原存储整块替换掉
        if (!cur.ok) return { ok: false, copy: cur.copy };
        const records = cur.payload.records.slice();
        const stored = Object.assign({}, record);
        const hasId = typeof stored.id === 'string' && stored.id.trim() !== '';
        let id = hasId ? stored.id.trim() : '';
        let at = hasId ? records.findIndex((x) => x.id === id) : -1;
        if (!hasId) id = nextId(records);
        stored.id = id;
        stored.savedAt = nowIso();
        if (at >= 0) records[at] = stored;
        else records.push(stored);
        const capped = capRecords(records);
        const wrapped = serialize({ records: capped.kept });
        if (!wrapped.ok) return { ok: false, copy: COPY.saveFail };
        if (!rawSet(KEYS.archives, wrapped.text)) return { ok: false, copy: COPY.saveFail };
        return {
          ok: true,
          id,
          record: stored,
          dropped: capped.dropped.map((x) => x.id).filter(Boolean)
        };
      },
      remove(id) {
        if (!available) return { ok: false, copy: COPY.deleteFail };
        const cur = readArchivesPayload();
        if (!cur.ok) return { ok: false, copy: cur.copy };
        const before = cur.payload.records;
        const next = before.filter((x) => x.id !== id);
        if (next.length === before.length) return { ok: true, removed: false };
        // 最后一条删掉后不留空壳键；此时删除动作退化为「删键」，失败同样报原文
        if (next.length === 0) {
          return rawDel(KEYS.archives)
            ? { ok: true, removed: true }
            : { ok: false, copy: COPY.deleteFail };
        }
        const wrapped = serialize({ records: next });
        if (!wrapped.ok) return { ok: false, copy: COPY.deleteFail };
        return rawSet(KEYS.archives, wrapped.text)
          ? { ok: true, removed: true }
          : { ok: false, copy: COPY.deleteFail };
      },
      duplicateAsNew(id) {
        if (!available) return { ok: false, copy: COPY.copyFail };
        const cur = readArchivesPayload();
        if (!cur.ok) return { ok: false, copy: cur.copy };
        const src = cur.payload.records.find((x) => x.id === id);
        if (!src) return { ok: false, copy: COPY.copyFail };
        const copy = Object.assign({}, src);
        delete copy.id;
        delete copy.savedAt;
        copy.academicYear = '';
        // 复制也是一条会离开本页的路径（Task 10 的「复制为新计算」）：资料三项
        // 一律不带（§9.1 末段）。旧存档原对象不动。
        PII_KEYS.forEach((k) => { delete copy[k]; });
        const w = archives.upsert(copy, { requireYear: false });
        if (!w.ok) return { ok: false, copy: COPY.copyFail };
        return { ok: true, id: w.id, record: w.record };
      }
    };

    return {
      available,
      draft,
      archives,
      rawGet,
      rawSet,
      COPY,
      KEYS,
      SCHEMA,
      MAX_ARCHIVES,
      PII_KEYS,
      PROFILE_KEYS,
      REFERENCE_NOTE
    };
  }

  // 导出文本：只按白名单拼行，绝不 JSON.stringify 整条记录——那样姓名/学院/专业/
  // 入学年级/备注会跟着跑出去（§9.1 末段 + §12 第 6 条）。
  function exportText(record) {
    const rec = isPlainObject(record) ? record : {};
    const lines = [];
    lines.push('学年：' + dash(rec.academicYear));
    lines.push('年级：' + dash(rec.grade));
    const items = Array.isArray(rec.items) ? rec.items : [];
    items.forEach((it) => {
      if (!isPlainObject(it)) return;
      const label = dash(it.label || it.name || it.eventName || it.eventKey);
      const raw = dash(it.rawDisplay);
      const score = it.score === null || it.score === undefined || it.score === ''
        ? '—' : it.score + ' 分';
      lines.push(label + '：' + raw + ' → ' + score);
    });
    const standardScore = rec.standardScore;
    const totalBonus = rec.totalBonus !== undefined ? rec.totalBonus : null;
    const totalScore = rec.totalScore;
    const gradeLabel = rec.gradeLabel || (typeof rec.level === 'string' ? rec.level : '');
    lines.push('标准分：' + numText(standardScore));
    lines.push('附加分：' + numText(totalBonus));
    // 120 是设计文档 §6 limits.maxTotalScore，只在这里当单位用
    lines.push('总分：' + (totalScore === null || totalScore === undefined ? '—' : totalScore + ' / 120'));
    lines.push('等级：' + dash(gradeLabel));
    lines.push(REFERENCE_NOTE);
    return lines.join('\n');
  }

  return {
    create,
    exportText,
    COPY,
    KEYS,
    SCHEMA,
    LEGACY_SCHEMA,
    MAX_ARCHIVES,
    PII_KEYS,
    PROFILE_KEYS,
    REFERENCE_NOTE
  };
}));
