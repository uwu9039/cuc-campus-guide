// 本机存储层（web-next/tice-store.js）的断言集：正常读写 / 配额超限 / JSON 损坏 /
// 版本迁移 / 存档操作 / duplicateAsNew / exportText 脱敏 / 不可用降级。
//
// 全部跑在内存假后端上，不碰真实浏览器存储：`create(backend)` 是唯一入口，
// 这正是「纯函数层」这条约束的可测形态。
//
// 跑法：node tools/test_tice_store.js
'use strict';

const assert = require('assert');
const store = require('../web-next/tice-store.js');

let pass = 0;
const failures = [];

function t(name, fn) {
  try {
    fn();
    pass += 1;
    console.log('  ok   ' + name);
  } catch (e) {
    failures.push({ name, e });
    console.log('  FAIL ' + name + ' → ' + (e && e.message));
  }
}

// ── 假后端 ────────────────────────────────────────────────────────
// failSet / failRemove 可随时改：探针通过之后再让写入失败，才能测到
// 「盘上已有数据、这次写失败、原数据必须还在」这条真正的保护路径。
function fakeBackend(opts) {
  const o = Object.assign({ failGet: false, failSet: false, failRemove: false }, opts || {});
  const map = new Map();
  return {
    _map: map,
    _o: o,
    getItem(k) {
      if (o.failGet) throw new Error('SecurityError');
      return map.has(k) ? map.get(k) : null;
    },
    setItem(k, v) {
      if (o.failSet) throw new Error('QuotaExceededError');
      map.set(k, String(v));
    },
    removeItem(k) {
      if (o.failRemove) throw new Error('remove failed');
      map.delete(k);
    }
  };
}

const K = store.KEYS;
const COPY = store.COPY;

// ── 1. 模块形状与键名 ────────────────────────────────────────────
console.log('模块形状');
t('UMD 导出 create / exportText / 常量', () => {
  assert.strictEqual(typeof store.create, 'function');
  assert.strictEqual(typeof store.exportText, 'function');
  assert.strictEqual(store.SCHEMA, 'v1');
  assert.strictEqual(store.MAX_ARCHIVES > 0 && Number.isInteger(store.MAX_ARCHIVES), true);
  assert.deepStrictEqual(store.PII_KEYS, ['name', 'college', 'major']);
  store.PROFILE_KEYS.forEach((k) => assert.ok(typeof k === 'string' && k));
  store.PII_KEYS.forEach((k) => assert.ok(store.PROFILE_KEYS.indexOf(k) >= 0, k + ' 必须是资料字段之一'));
});

t('键名照设计文档 §9：tice_draft_v1 / tice_archives_v1（带版本）', () => {
  assert.strictEqual(K.draft, 'tice_draft_v1');
  assert.strictEqual(K.archives, 'tice_archives_v1');
  assert.ok(/_v\d+$/.test(K.draft) && /_v\d+$/.test(K.archives), '键名必须带版本后缀');
});

// ── 2. 可用性探针 ────────────────────────────────────────────────
console.log('可用性探针');
t('可用后端 → available:true，探针键不留痕', () => {
  const be = fakeBackend();
  const env = store.create(be);
  assert.strictEqual(env.available, true);
  assert.strictEqual(be._map.has('__tice_probe__'), false);
});

t('写入即抛（配额满）→ available:false', () => {
  const env = store.create(fakeBackend({ failSet: true }));
  assert.strictEqual(env.available, false);
});

t('backend 为空 / 方法不全 → available:false，不抛', () => {
  assert.strictEqual(store.create().available, false);
  assert.strictEqual(store.create(null).available, false);
  assert.strictEqual(store.create({ getItem: () => null, setItem: () => {} }).available, false);
});

// ── 3. 暂存：正常读写 ────────────────────────────────────────────
console.log('暂存读写');
t('空存储读出 { ok:true, value:null }，不抛', () => {
  const env = store.create(fakeBackend());
  const r = env.draft.load();
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.value, null);
  assert.strictEqual(r.savedAt, null);
});

t('save → load 往返，值原样回来，savedAt 是 ISO 时间', () => {
  const env = store.create(fakeBackend());
  const form = { gender: 'male', grade: '大一', vitalCapacity: '4000', runMinutes: '4', runSeconds: '20' };
  const w = env.draft.save(form);
  assert.strictEqual(w.ok, true);
  const r = env.draft.load();
  assert.strictEqual(r.ok, true);
  assert.deepStrictEqual(r.value, form);
  assert.match(String(r.savedAt), /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  assert.strictEqual(r.migratedFrom, null);
});

t('落盘结构只有 __schema / value / savedAt（不夹带任何资料字段）', () => {
  const be = fakeBackend();
  const env = store.create(be);
  env.draft.save({ vitalCapacity: '4000' });
  const keys = Object.keys(JSON.parse(be._map.get(K.draft))).sort();
  assert.deepStrictEqual(keys, ['__schema', 'savedAt', 'value']);
  assert.strictEqual(JSON.parse(be._map.get(K.draft)).__schema, 'v1');
});

t('暂存不落资料三项：误传进来的姓名/学院/专业被剥掉，其余键原样', () => {
  const be = fakeBackend();
  const env = store.create(be);
  const form = { gender: 'male', vitalCapacity: '4000', name: '测试甲', college: '电视学院', major: '新闻学' };
  env.draft.save(form);
  assert.strictEqual(be._map.get(K.draft).includes('测试甲'), false, '暂存里不许出现姓名');
  const back = env.draft.load().value;
  assert.strictEqual(back.name, undefined);
  assert.strictEqual(back.college, undefined);
  assert.strictEqual(back.major, undefined);
  assert.strictEqual(back.vitalCapacity, '4000');
  assert.strictEqual(form.name, '测试甲', '不许改调用方传进来的对象');
});

t('clear 清掉暂存；再 load 回到 null；空存储 clear 也算成功', () => {
  const env = store.create(fakeBackend());
  env.draft.save({ a: 1 });
  assert.strictEqual(env.draft.clear().ok, true);
  assert.strictEqual(env.draft.load().value, null);
  assert.strictEqual(env.draft.clear().ok, true, '本来就没有暂存时删除也要成功');
});

t('两个 create 共用一个后端 → 像刷新后一样读到上次填写', () => {
  const be = fakeBackend();
  store.create(be).draft.save({ vitalCapacity: '4300' });
  const again = store.create(be);
  assert.strictEqual(again.draft.load().value.vitalCapacity, '4300');
});

t('rawGet / rawSet 直接读写指定键', () => {
  const env = store.create(fakeBackend());
  assert.strictEqual(env.rawGet(K.draft), null);
  assert.strictEqual(env.rawSet(K.draft, '{"x":1}'), true);
  assert.strictEqual(env.rawGet(K.draft), '{"x":1}');
});

// ── 4. 配额超限（写失败）──────────────────────────────────────────
console.log('配额超限');
t('暂存写失败 → 原文「自动暂存失败…」，原暂存一个字节未变', () => {
  const be = fakeBackend();
  const env = store.create(be);
  env.draft.save({ vitalCapacity: '4000' });
  const before = be._map.get(K.draft);
  be._o.failSet = true;
  const w = env.draft.save({ vitalCapacity: '4100' });
  assert.strictEqual(w.ok, false);
  assert.strictEqual(w.copy, '自动暂存失败，当前填写仍在页面中；请勿将本机记录作为唯一凭证');
  assert.strictEqual(w.copy, COPY.draftWriteFail);
  assert.strictEqual(be._map.get(K.draft), before, '写失败时原暂存必须原样保留');
  be._o.failSet = false;
  assert.strictEqual(env.draft.load().value.vitalCapacity, '4000');
});

t('存档写失败 → 原文「保存失败，原存档未被替换…」，原存档仍在', () => {
  const be = fakeBackend();
  const env = store.create(be);
  env.archives.upsert({ id: 'a1', academicYear: '2025-2026', totalScore: 88 });
  const before = be._map.get(K.archives);
  be._o.failSet = true;
  const w = env.archives.upsert({ id: 'a1', academicYear: '2025-2026', totalScore: 99 });
  assert.strictEqual(w.ok, false);
  assert.strictEqual(w.copy, '保存失败，原存档未被替换，请稍后重试');
  assert.strictEqual(be._map.get(K.archives), before);
  be._o.failSet = false;
  assert.strictEqual(env.archives.list().length, 1);
  assert.strictEqual(env.archives.list()[0].totalScore, 88);
});

t('暂存删除失败 → 原文「暂存清除失败，原填写已保留」', () => {
  const be = fakeBackend();
  const env = store.create(be);
  env.draft.save({ a: 1 });
  be._o.failRemove = true;
  const r = env.draft.clear();
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.copy, '暂存清除失败，原填写已保留');
  assert.strictEqual(env.rawGet(K.draft) !== null, true, '原暂存不许被顺手清掉');
});

// ── 5. JSON 损坏 / 版本不认识 ────────────────────────────────────
console.log('JSON 损坏与版本闸');
t('暂存 JSON 损坏 → 读失败原文；save / clear 都不许覆盖原数据', () => {
  const be = fakeBackend();
  const env = store.create(be);
  be._map.set(K.draft, '{ not json');
  const r = env.draft.load();
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.value, null);
  assert.strictEqual(r.copy, '本地暂存读取失败或版本暂不支持，原数据已保留；当前填写暂不能覆盖它');
  assert.strictEqual(env.draft.save({ a: 1 }).ok, false);
  assert.strictEqual(env.draft.save({ a: 1 }).copy, COPY.draftReadFail);
  assert.strictEqual(env.draft.clear().copy, COPY.draftClearFail);
  assert.strictEqual(be._map.get(K.draft), '{ not json');
});

t('未知版本 v9 暂存 → 不覆盖、不删除，原字节保留', () => {
  const be = fakeBackend();
  const env = store.create(be);
  const raw = JSON.stringify({ __schema: 'v9', x: 1 });
  env.rawSet(K.draft, raw);
  const r = env.draft.load();
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.copy, COPY.draftReadFail);
  assert.strictEqual(env.draft.save({ a: 1 }).ok, false);
  assert.strictEqual(env.draft.clear().ok, false);
  assert.strictEqual(be._map.get(K.draft), raw, '未知版本的原数据不许被覆盖');
});

t('v1 但结构缺 value → 按版本不支持处理', () => {
  const be = fakeBackend();
  const env = store.create(be);
  be._map.set(K.draft, JSON.stringify({ __schema: 'v1', savedAt: null }));
  assert.strictEqual(env.draft.load().ok, false);
});

t('存档 JSON 损坏 → 列表空 + historyFail 原文，写入被拒且原存储保留', () => {
  const be = fakeBackend();
  const env = store.create(be);
  be._map.set(K.archives, '[{"id":');
  const list = env.archives.list();
  assert.strictEqual(list.length, 0);
  assert.strictEqual(list.ok, false);
  assert.strictEqual(list.copy, '历史读取失败或版本暂不支持，原存储已保留');
  const w = env.archives.upsert({ academicYear: '2025-2026' });
  assert.strictEqual(w.ok, false);
  assert.strictEqual(w.copy, COPY.historyFail);
  assert.strictEqual(be._map.get(K.archives), '[{"id":');
});

// ── 6. 版本迁移 ─────────────────────────────────────────────────
console.log('版本迁移 v0 → v1');
t('无版本标记的暂存（v0 形态）在内存里补成 v1，读得出，但不回写', () => {
  const be = fakeBackend();
  const env = store.create(be);
  const raw = JSON.stringify({ value: { gender: 'female' }, savedAt: '2026-01-01T00:00:00.000Z' });
  be._map.set(K.draft, raw);
  const r = env.draft.load();
  assert.strictEqual(r.ok, true);
  assert.deepStrictEqual(r.value, { gender: 'female' });
  assert.strictEqual(r.savedAt, '2026-01-01T00:00:00.000Z');
  assert.strictEqual(r.migratedFrom, 'v0');
  assert.strictEqual(be._map.get(K.draft), raw, '读操作不许顺手改盘');
});

t('v0 暂存下一次 save 落成 v1 信封', () => {
  const be = fakeBackend();
  const env = store.create(be);
  be._map.set(K.draft, JSON.stringify({ value: { gender: 'female' } }));
  assert.strictEqual(env.draft.load().ok, true);
  assert.strictEqual(env.draft.save({ gender: 'male' }).ok, true);
  const stored = JSON.parse(be._map.get(K.draft));
  assert.strictEqual(stored.__schema, 'v1');
  assert.deepStrictEqual(stored.value, { gender: 'male' });
});

t('v0 存档是裸数组 → 列表读得出，下一次写入包成 v1 信封', () => {
  const be = fakeBackend();
  const env = store.create(be);
  const legacy = [{ id: 'old', academicYear: '2024-2025', totalScore: 80 }];
  be._map.set(K.archives, JSON.stringify(legacy));
  const list = env.archives.list();
  assert.strictEqual(list.length, 1);
  assert.strictEqual(list[0].totalScore, 80);
  assert.strictEqual(be._map.get(K.archives), JSON.stringify(legacy), '读操作不许回写');
  assert.strictEqual(env.archives.upsert({ academicYear: '2025-2026' }).ok, true);
  const stored = JSON.parse(be._map.get(K.archives));
  assert.strictEqual(stored.__schema, 'v1');
  assert.strictEqual(stored.records.length, 2);
  assert.strictEqual(stored.records[0].id, 'old');
});

t('未知版本 v9 存档 → 列表空、写入被拒、原存储保留', () => {
  const be = fakeBackend();
  const env = store.create(be);
  const raw = JSON.stringify({ __schema: 'v9', records: [{ id: 'z', academicYear: '2024-2025' }] });
  env.rawSet(K.archives, raw);
  const list = env.archives.list();
  assert.strictEqual(list.length, 0);
  assert.strictEqual(list.copy, COPY.historyFail);
  assert.strictEqual(env.archives.upsert({ academicYear: '2025-2026' }).ok, false);
  assert.strictEqual(env.archives.remove('z').ok, false);
  assert.strictEqual(be._map.get(K.archives), raw);
});

// ── 7. 存档：学年必填 / upsert / 上限 / remove ────────────────────
console.log('存档');
t('学年必填：空串 / 纯空格 / 缺失 → 「请填写学年」，且不写盘', () => {
  const be = fakeBackend();
  const env = store.create(be);
  assert.strictEqual(env.archives.upsert({ id: 'x1' }).copy, '请填写学年');
  assert.strictEqual(env.archives.upsert({ id: 'x1', academicYear: '' }).copy, '请填写学年');
  assert.strictEqual(env.archives.upsert({ id: 'x1', academicYear: '   ' }).copy, '请填写学年');
  assert.strictEqual(be._map.has(K.archives), false, '校验失败不该留下任何键');
  assert.strictEqual(env.archives.list().length, 0);
});

t('upsert 新记录 → ok:true 带 id；同 id 再写是替换，不新增也不改顺序', () => {
  const env = store.create(fakeBackend());
  const w1 = env.archives.upsert({ id: 'b', academicYear: '2024-2025', totalScore: 70 });
  assert.strictEqual(w1.ok, true);
  assert.strictEqual(w1.id, 'b');
  assert.ok(w1.record.savedAt);
  env.archives.upsert({ id: 'a', academicYear: '2023-2024', totalScore: 60 });
  env.archives.upsert({ id: 'c', academicYear: '2022-2023', totalScore: 50 });
  assert.deepStrictEqual(env.archives.list().map((x) => x.id), ['b', 'a', 'c']);
  env.archives.upsert({ id: 'a', academicYear: '2023-2024', totalScore: 65 });
  assert.strictEqual(env.archives.list().length, 3);
  assert.deepStrictEqual(env.archives.list().map((x) => x.id), ['b', 'a', 'c']);
  assert.strictEqual(env.archives.list()[1].totalScore, 65);
});

t('不给 id 时自动生成，两次生成不撞', () => {
  const env = store.create(fakeBackend());
  const a = env.archives.upsert({ academicYear: '2025-2026' });
  const b = env.archives.upsert({ academicYear: '2025-2026' });
  assert.ok(a.id && b.id && a.id !== b.id);
  assert.strictEqual(env.archives.list().length, 2);
});

t('存档条数上限：超一条就淘汰最旧的，并回报 dropped', () => {
  const env = store.create(fakeBackend());
  const ids = [];
  for (let i = 0; i <= store.MAX_ARCHIVES; i += 1) {
    const w = env.archives.upsert({ academicYear: '2025-2026', totalScore: i });
    ids.push(w.id);
    if (i === store.MAX_ARCHIVES) {
      assert.deepStrictEqual(w.dropped, [ids[0]], '超限时被淘汰的应是第一条');
    }
  }
  const list = env.archives.list();
  assert.strictEqual(list.length, store.MAX_ARCHIVES);
  assert.strictEqual(list.some((x) => x.id === ids[0]), false);
  assert.strictEqual(list.some((x) => x.id === ids[ids.length - 1]), true);
});

t('remove：删掉指定那条，其他记录不动', () => {
  const be = fakeBackend();
  const env = store.create(be);
  env.archives.upsert({ id: 'keep', academicYear: '2024-2025' });
  env.archives.upsert({ id: 'drop', academicYear: '2023-2024' });
  const r = env.archives.remove('drop');
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.removed, true);
  assert.deepStrictEqual(env.archives.list().map((x) => x.id), ['keep']);
  assert.strictEqual(env.archives.remove('nope').removed, false, '删不存在的 id 不该报错');
});

t('remove 写失败 → 「删除失败，原记录已保留」，两条都还在', () => {
  const be = fakeBackend();
  const env = store.create(be);
  env.archives.upsert({ id: 'keep', academicYear: '2024-2025' });
  env.archives.upsert({ id: 'drop', academicYear: '2023-2024' });
  be._o.failSet = true;
  const r = env.archives.remove('drop');
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.copy, '删除失败，原记录已保留');
  be._o.failSet = false;
  assert.strictEqual(env.archives.list().length, 2);
});

t('remove 最后一条 → 删键腾地方；删键失败报「删除失败，原记录已保留」且记录还在', () => {
  const be = fakeBackend();
  const env = store.create(be);
  env.archives.upsert({ id: 'only', academicYear: '2025-2026' });
  be._o.failRemove = true;
  const bad = env.archives.remove('only');
  assert.strictEqual(bad.ok, false);
  assert.strictEqual(bad.copy, '删除失败，原记录已保留');
  assert.strictEqual(env.archives.list().length, 1);
  be._o.failRemove = false;
  assert.strictEqual(env.archives.remove('only').ok, true);
  assert.strictEqual(be._map.has(K.archives), false, '空存档不留空壳键');
});

// ── 8. duplicateAsNew ───────────────────────────────────────────
console.log('duplicateAsNew');
t('复制为新计算：生成新 id、学年置空、旧存档一字不动', () => {
  const env = store.create(fakeBackend());
  env.archives.upsert({
    id: 'x1', academicYear: '2025-2026', grade: '大一', totalScore: 88,
    name: '测试甲', college: '电视学院', major: '新闻学', enrollGrade: '2025级', note: '备注乙'
  });
  const dup = env.archives.duplicateAsNew('x1');
  assert.strictEqual(dup.ok, true);
  assert.ok(dup.id && dup.id !== 'x1', '复制必须生成新 id');
  assert.strictEqual(dup.record.academicYear, '');
  assert.strictEqual(env.archives.list().length, 2);
  const old = env.archives.list().find((x) => x.id === 'x1');
  assert.strictEqual(old.academicYear, '2025-2026', '旧存档不许被动');
  assert.strictEqual(old.totalScore, 88);
  assert.strictEqual(old.name, '测试甲', '复制不该改旧档的姓名');
});

t('复制出的记录不带资料三项，成绩字段照抄', () => {
  const env = store.create(fakeBackend());
  env.archives.upsert({
    id: 'p1', academicYear: '2025-2026', totalScore: 90,
    name: '测试甲', college: '电视学院', major: '新闻学'
  });
  const dup = env.archives.duplicateAsNew('p1');
  const copy = env.archives.list().find((x) => x.id === dup.id);
  store.PII_KEYS.forEach((k) => assert.strictEqual(copy[k], undefined, k + ' 不许跟着复制'));
  assert.strictEqual(copy.totalScore, 90);
});

t('复制后填上学年再 upsert → 落成一条正常存档', () => {
  const env = store.create(fakeBackend());
  env.archives.upsert({ id: 'p1', academicYear: '2025-2026', totalScore: 90 });
  const dup = env.archives.duplicateAsNew('p1');
  const w = env.archives.upsert(Object.assign({}, dup.record, { academicYear: '2024-2025' }));
  assert.strictEqual(w.ok, true);
  assert.strictEqual(env.archives.list().length, 2);
  assert.strictEqual(env.archives.list().find((x) => x.id === dup.id).academicYear, '2024-2025');
});

t('复制不存在的 id → 「复制失败，原暂存与存档已保留」，列表不变', () => {
  const env = store.create(fakeBackend());
  env.archives.upsert({ id: 'p1', academicYear: '2025-2026' });
  const r = env.archives.duplicateAsNew('nope');
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.copy, '复制失败，原暂存与存档已保留');
  assert.strictEqual(env.archives.list().length, 1);
});

// ── 9. exportText ───────────────────────────────────────────────
console.log('exportText');
t('导出文本含成绩四件套与参考小字', () => {
  const rec = {
    id: 'e1', academicYear: '2025-2026', grade: '大一', gender: 'male',
    items: [
      { name: '肺活量', rawDisplay: '5040', score: 100 },
      { name: '引体向上', rawDisplay: '19', score: 100 }
    ],
    standardScore: 100, strengthBonus: 6, enduranceBonus: 6, totalBonus: 12,
    totalScore: 112, gradeLabel: '优秀', status: 'complete'
  };
  const text = store.exportText(rec);
  assert.ok(text.includes('学年：2025-2026'));
  assert.ok(text.includes('年级：大一'));
  assert.ok(text.includes('肺活量：5040 → 100 分'));
  assert.ok(text.includes('引体向上：19 → 100 分'));
  assert.ok(text.includes('标准分：100'));
  assert.ok(text.includes('附加分：12'));
  assert.ok(text.includes('总分：112 / 120'));
  assert.ok(text.includes('等级：优秀'));
  assert.ok(text.includes('仅供参考，实际成绩以学校体测系统记录为准。'));
});

t('导出文本不含资料三项（逐值查不到）', () => {
  const rec = {
    id: 'e2', academicYear: '2025-2026', grade: '大一',
    name: '测试甲', college: '电视学院', major: '新闻学', enrollGrade: '2025级', note: '备注乙',
    items: [{ name: '肺活量', rawDisplay: '5040', score: 100 }],
    standardScore: 100, totalBonus: 0, totalScore: 100, gradeLabel: '优秀'
  };
  const text = store.exportText(rec);
  ['测试甲', '电视学院', '新闻学', '2025级', '备注乙'].forEach((v) => {
    assert.strictEqual(text.includes(v), false, '导出文本泄漏了 ' + v + '：\n' + text);
  });
  assert.ok(text.includes('肺活量'), '脱敏不能把成绩一起删掉');
});

t('未填字段 / 缺项 / null 分数都退化成破折号，不出现 null', () => {
  const text = store.exportText({
    academicYear: '', items: [{ name: '50米', rawDisplay: '', score: null }],
    standardScore: null, totalBonus: null, totalScore: null, gradeLabel: ''
  });
  assert.ok(text.includes('学年：—'));
  assert.ok(text.includes('50米：— → —'));
  assert.ok(text.includes('标准分：—'));
  assert.ok(text.includes('总分：—'));
  assert.ok(text.includes('等级：—'));
  assert.strictEqual(text.includes('null'), false);
});

t('exportText 不挑输入：空对象 / null 都不抛', () => {
  [null, undefined, {}, { items: 'not-an-array' }].forEach((rec) => {
    const text = store.exportText(rec);
    assert.ok(text.includes('仅供参考'), '任何输入都要带小字');
  });
});

// ── 10. 整块存储不可用时的降级 ─────────────────────────────────
console.log('存储不可用降级');
t('available:false 时每个分支都给 ok:false + 原文，读不出数据也不假装空', () => {
  const env = store.create(fakeBackend({ failGet: true, failSet: true, failRemove: true }));
  assert.strictEqual(env.available, false);
  const load = env.draft.load();
  assert.strictEqual(load.ok, false);
  assert.strictEqual(load.value, null);
  assert.strictEqual(load.copy, COPY.draftReadFail);
  assert.strictEqual(env.draft.save({ a: 1 }).copy, COPY.draftWriteFail);
  assert.strictEqual(env.draft.clear().copy, COPY.draftClearFail);
  const list = env.archives.list();
  assert.strictEqual(list.length, 0);
  assert.strictEqual(list.ok, false);
  assert.strictEqual(list.copy, COPY.historyFail);
  assert.strictEqual(env.archives.upsert({ academicYear: '2025-2026' }).copy, COPY.saveFail);
  assert.strictEqual(env.archives.remove('x').copy, COPY.deleteFail);
  assert.strictEqual(env.archives.duplicateAsNew('x').copy, COPY.copyFail);
  assert.strictEqual(env.rawGet(K.draft), null);
  assert.strictEqual(env.rawSet(K.draft, 'x'), false);
});

t('恢复可用后（同一环境新建）数据仍在，不被降级态写坏', () => {
  const be = fakeBackend();
  const ok = store.create(be);
  ok.draft.save({ vitalCapacity: '4000' });
  ok.archives.upsert({ id: 'a1', academicYear: '2025-2026' });
  be._o.failGet = true;
  be._o.failSet = true;
  const dead = store.create(be);
  assert.strictEqual(dead.available, false);
  assert.strictEqual(dead.draft.save({ vitalCapacity: '1' }).ok, false);
  be._o.failGet = false;
  be._o.failSet = false;
  const back = store.create(be);
  assert.strictEqual(back.available, true);
  assert.strictEqual(back.draft.load().value.vitalCapacity, '4000');
  assert.strictEqual(back.archives.list().length, 1);
});

// ── 小结 ───────────────────────────────────────────────────────
console.log('');
if (failures.length) {
  failures.forEach((f) => console.log('FAILED: ' + f.name + '\n' + (f.e && f.e.stack)));
  console.log('store 断言 ' + (pass + failures.length) + ' 条，失败 ' + failures.length + ' 条');
  process.exit(1);
}
console.log('store 断言全过（' + pass + ' 条）');
