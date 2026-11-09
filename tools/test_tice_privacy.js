// 隐私契约（设计文档 §9.1 末段 + §11 声明区，spec §12 第 6 条的自动化版）：
//   1) 存储层不碰 DOM、不碰全局存储对象、不发网络请求——源码层静态断言；
//   2) 资料三项（姓名/学院/专业）只落本机，导出文本与复制路径一律不带；
//   3) 期末不给「学号 / 身份证」一类字段留位置（这批数据本来就不该出现在本页）。
//
// 跑法：node tools/test_tice_privacy.js
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const STORE_PATH = path.join(__dirname, '..', 'web-next', 'tice-store.js');
const SOURCE = fs.readFileSync(STORE_PATH, 'utf8');
const store = require(STORE_PATH);

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

function memBackend() {
  const map = new Map();
  return {
    _map: map,
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => { map.set(k, String(v)); },
    removeItem: (k) => { map.delete(k); }
  };
}

// ── 1. 源码层：不碰设备、不发请求 ─────────────────────────────────
console.log('源码静态断言');
t('存储层源码不出现任何浏览器全局对象（只认注入的 backend）', () => {
  ['localStorage', 'sessionStorage', 'indexedDB', 'window', 'document', 'navigator']
    .forEach((token) => {
      assert.strictEqual(SOURCE.includes(token), false,
        '源码里出现了 ' + token + '——存储层必须只走注入的 backend');
    });
});

t('存储层源码不发起任何网络请求', () => {
  ['fetch(', 'XMLHttpRequest', 'WebSocket', 'sendBeacon', 'importScripts', 'http://', 'https://']
    .forEach((token) => {
      assert.strictEqual(SOURCE.includes(token), false, '源码里出现了 ' + token);
    });
});

t('存储层源码不 require 任何模块（零依赖，node 里可直接跑）', () => {
  assert.strictEqual(/require\s*\(/.test(SOURCE), false);
});

t('存储层源码不收集学号 / 身份证 / 手机号 / 邮箱一类资料', () => {
  ['学号', '身份证', 'studentId', 'idCard', 'idNumber', 'phone', 'email', 'address']
    .forEach((token) => {
      assert.strictEqual(SOURCE.includes(token), false, '源码里出现了 ' + token);
    });
});

t('UMD 两侧都可用：node 里 module.exports 有 create / exportText', () => {
  assert.strictEqual(typeof store.create, 'function');
  assert.strictEqual(typeof store.exportText, 'function');
  assert.ok(SOURCE.includes('root.TICE_STORE'), '浏览器侧必须挂 TICE_STORE');
});

// ── 2. 运行期：真跑一遍 CRUD，网络调用计数必须为 0 ─────────────────
console.log('运行期网络计数');
t('整轮存取 + 导出 + 复制期间没有任何网络请求', () => {
  let netCalls = 0;
  const realFetch = globalThis.fetch;
  globalThis.fetch = function () { netCalls += 1; throw new Error('不许联网'); };
  try {
    const env = store.create(memBackend());
    env.draft.save({ gender: 'male', grade: '大一', vitalCapacity: '5040' });
    env.draft.load();
    env.archives.upsert({
      id: 'p1', academicYear: '2025-2026', grade: '大一',
      name: '测试甲', college: '电视学院', major: '新闻学', enrollGrade: '2025级', note: '备注乙',
      items: [{ name: '肺活量', rawDisplay: '5040', score: 100 }],
      standardScore: 100, totalBonus: 12, totalScore: 112, gradeLabel: '优秀'
    });
    env.archives.list();
    const dup = env.archives.duplicateAsNew('p1');
    store.exportText(env.archives.list()[0]);
    env.archives.remove(dup.id);
    env.draft.clear();
  } finally {
    if (realFetch) globalThis.fetch = realFetch;
    else delete globalThis.fetch;
  }
  assert.strictEqual(netCalls, 0, '存储层发起了 ' + netCalls + ' 次网络请求');
});

// ── 3. 资料字段只落本机 ──────────────────────────────────────────
console.log('资料字段只落本机');
t('存档里确实留着姓名（只落本机），不是被静默丢掉', () => {
  const be = memBackend();
  const env = store.create(be);
  env.archives.upsert({
    id: 'p1', academicYear: '2025-2026',
    name: '测试甲', college: '电视学院', major: '新闻学', enrollGrade: '2025级', note: '备注乙'
  });
  const stored = be._map.get(store.KEYS.archives);
  assert.ok(stored.includes('测试甲'), '姓名应当只存在本机存储里');
  assert.strictEqual(env.archives.list()[0].name, '测试甲');
});

t('暂存层不额外收集资料字段：落盘只有 __schema / value / savedAt', () => {
  const be = memBackend();
  const env = store.create(be);
  env.draft.save({ gender: 'male', grade: '大一' });
  const keys = Object.keys(JSON.parse(be._map.get(store.KEYS.draft))).sort();
  assert.deepStrictEqual(keys, ['__schema', 'savedAt', 'value']);
  store.PROFILE_KEYS.forEach((k) => assert.strictEqual(keys.includes(k), false, k + ' 不该进暂存信封'));
});

t('暂存层即使被误传资料三项也不落盘（只进存档对象）', () => {
  const be = memBackend();
  const env = store.create(be);
  env.draft.save({ gender: 'male', vitalCapacity: '4000', name: '测试甲', college: '电视学院', major: '新闻学' });
  const raw = be._map.get(store.KEYS.draft);
  store.PII_KEYS.forEach((k) => assert.strictEqual(raw.includes('"' + k + '":'), false, k + ' 被写进了暂存'));
  assert.strictEqual(raw.includes('测试甲'), false);
  const back = env.draft.load().value;
  assert.strictEqual(back.vitalCapacity, '4000', '剥资料不能把填写内容一起剥掉');
});

// ── 4. 出门的两条路都不带资料三项 ────────────────────────────────
console.log('导出与复制脱敏');
const RECORD = {
  id: 'p1', academicYear: '2025-2026', grade: '大一',
  name: '测试甲', college: '电视学院', major: '新闻学', enrollGrade: '2025级', note: '备注乙',
  items: [{ name: '肺活量', rawDisplay: '5040', score: 100 }],
  standardScore: 100, strengthBonus: 6, enduranceBonus: 6, totalBonus: 12,
  totalScore: 112, gradeLabel: '优秀', status: 'complete'
};
const PII_VALUES = ['测试甲', '电视学院', '新闻学', '2025级', '备注乙'];

t('exportText 不含资料三项的任何值', () => {
  const text = store.exportText(RECORD);
  PII_VALUES.forEach((v) => assert.strictEqual(text.includes(v), false, '导出泄漏 ' + v));
});

t('exportText 不含资料字段的标签（姓名/学院/专业/入学年级/备注）', () => {
  const text = store.exportText(RECORD);
  ['姓名', '学院', '专业', '入学年级', '备注'].forEach((label) => {
    assert.strictEqual(text.includes(label), false, '导出出现了资料字段标签 ' + label + '：\n' + text);
  });
});

t('exportText 仍是可用的成绩清单（脱敏不能变阉割）', () => {
  const text = store.exportText(RECORD);
  ['肺活量：5040 → 100 分', '标准分：100', '附加分：12', '总分：112 / 120', '等级：优秀',
    '仅供参考，实际成绩以学校体测系统记录为准。'].forEach((line) => {
    assert.ok(text.includes(line), '导出缺 ' + line + '：\n' + text);
  });
});

t('复制为新计算不带资料三项，只带成绩', () => {
  const env = store.create(memBackend());
  env.archives.upsert(RECORD);
  const dup = env.archives.duplicateAsNew('p1');
  assert.strictEqual(dup.ok, true);
  const copy = env.archives.list().find((x) => x.id === dup.id);
  store.PII_KEYS.forEach((k) => assert.strictEqual(copy[k], undefined, '复制带走了 ' + k));
  assert.strictEqual(copy.totalScore, 112, '成绩要跟着复制');
  assert.strictEqual(copy.academicYear, '');
  // 旧档仍在，且资料只在本机这份里
  assert.strictEqual(env.archives.list().find((x) => x.id === 'p1').name, '测试甲');
});

t('PII_KEYS 与 PROFILE_KEYS 的关系被钉住：三项 ⊂ 五个资料字段', () => {
  assert.deepStrictEqual(store.PII_KEYS.slice().sort(), ['college', 'major', 'name']);
  store.PII_KEYS.forEach((k) => assert.ok(store.PROFILE_KEYS.includes(k), k + ' 不在资料字段里'));
  assert.strictEqual(store.PROFILE_KEYS.includes('academicYear'), false, '学年是键，不是资料字段');
});

// ── 5. 防止无限增长的基础约束 ────────────────────────────────────
console.log('容量与版本约束');
t('键名带版本、存档有上限（防止无限增长）', () => {
  ['draft', 'archives'].forEach((k) => {
    assert.match(store.KEYS[k], /_v\d+$/, k + ' 键名必须带版本后缀');
  });
  assert.ok(Number.isInteger(store.MAX_ARCHIVES) && store.MAX_ARCHIVES > 0);
});

t('上限真的生效：写满 MAX_ARCHIVES + 3 条后条数不再增长', () => {
  const env = store.create(memBackend());
  for (let i = 0; i < store.MAX_ARCHIVES + 3; i += 1) {
    env.archives.upsert({ academicYear: '2025-2026', totalScore: i });
  }
  assert.strictEqual(env.archives.list().length, store.MAX_ARCHIVES);
});

console.log('');
if (failures.length) {
  failures.forEach((f) => console.log('FAILED: ' + f.name + '\n' + (f.e && f.e.stack)));
  console.log('privacy 断言 ' + (pass + failures.length) + ' 条，失败 ' + failures.length + ' 条');
  process.exit(1);
}
console.log('privacy 断言全过（' + pass + ' 条）');
