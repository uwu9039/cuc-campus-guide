// 只为取数据：从解包产物里把 define("name", function(...){...}) 的函数体切出来，
// 用最小 CommonJS 注册表执行。不跑页面逻辑，不联网。
const fs = require('fs');

// 源包路径只从参数或环境变量来（Global Constraint 11：提交的源码里不写死本机账号目录）。
// 缺路径、缺文件都带 Step 0 的解包提示抛出去，别让人对着 ENOENT 猜。
const STEP0_HINT = '路径从参数或环境变量给：node tools/tice_build_json.js "<…/wxdump/out/app-service.js>" 或 '
  + 'TICE_SOURCE="<…/wxdump/out/app-service.js>" node tools/tice_build_json.js。'
  + '临时目录已空就按 brief Step 0 重新解包：cd %TEMP%/wxdump && node decrypt.js（期望 extracted 60 files）；'
  + '整个目录不在了就按 spec 记录的 V1MMWX 规则重建。';

function sourcePath() {
  const p = process.argv[2] || process.env.TICE_SOURCE || '';
  if (!p) throw new Error(`没给解包产物路径。${STEP0_HINT}`);
  if (!fs.existsSync(p)) throw new Error(`解包产物不存在：${p}。${STEP0_HINT}`);
  return p;
}

const SRC = sourcePath();

function readSource() { return fs.readFileSync(SRC, 'utf8'); }
// 校验和按字节算，不按解码后的文本算：包一旦带上 BOM 或非法字节，文本哈希和 sha256sum 就对不上了。
function readSourceBuffer() { return fs.readFileSync(SRC); }

// 花括号配对时的词法跳壳：字符串、模板串、行注释、块注释、正则字面量都要整段跳过，
// 否则像 data/fitness-standard.js 里 parseMmSsLiteralToSeconds 的 /^(\d+)'(\d{2})"$/
// 会把单引号当成串起点，深度错位、函数体切短、new Function 语法错。
// 仅补强 parseDefs 的这段扫描，其余标识符、接口、产物结构保持不变。
const REGEX_OK = new Set(['(', ',', '=', ':', '[', '!', '&', '|', '?', '{', '}', ';', '+', '-', '*', '/', '%', '~', '^', '<', '>']);

function parseDefs(src) {
  const defs = new Map();
  const OPEN = /define\("([^"]+)", function\([^)]*\)\{/g;
  let m;
  while ((m = OPEN.exec(src))) {
    const start = m.index + m[0].length;
    let depth = 1, i = start, q = null, esc = false, prev = '{';
    for (; i < src.length && depth > 0; i += 1) {
      const c = src[i];
      if (q) {
        if (esc) esc = false;
        else if (c === '\\') esc = true;
        else if (c === q) q = null;
        continue;
      }
      if (c === '/' && src[i + 1] === '/') { const nl = src.indexOf('\n', i); i = nl < 0 ? src.length : nl; continue; }
      if (c === '/' && src[i + 1] === '*') { const e = src.indexOf('*/', i + 2); i = e < 0 ? src.length : e + 1; prev = '/'; continue; }
      if (c === '"' || c === "'" || c === '`') { q = c; prev = c; continue; }
      if (c === '/' && REGEX_OK.has(prev)) {                 // 正则字面量：整段跳到闭合 /
        let rEsc = false, cls = false;
        for (i += 1; i < src.length; i += 1) {
          const r = src[i];
          if (rEsc) { rEsc = false; continue; }
          if (r === '\\') { rEsc = true; continue; }
          if (r === '\n') break;                              // 未闭合兜底
          if (cls) { if (r === ']') cls = false; continue; }
          if (r === '[') cls = true;
          else if (r === '/') break;
        }
        prev = '/';
        continue;
      }
      if (c === '{') depth += 1;
      else if (c === '}') depth -= 1;
      if (!/\s/.test(c)) prev = c;
    }
    defs.set(m[1], src.slice(start, i - 1));
  }
  return defs;
}

function makeLoader(defs) {
  const cache = new Map();
  // 剥前导相对点时同时吃 "./" 与 "../"：@swc/runtime 兄弟模块用 "./_x.js" 引，
  // 而 define 名是 "@swc/runtime/_x.js"，原短名只剥 "../" 会解析不到。
  const shortName = (spec) => spec.replace(/^(\.\.?\/)+/, '').replace(/\.js$/, '');
  function resolve(spec) {
    if (defs.has(spec)) return spec;
    const want = shortName(spec);
    const hit = [...defs.keys()].find((k) => shortName(k) === want)
      || [...defs.keys()].find((k) => { const b = k.replace(/\.js$/, ''); return b.endsWith('/' + want) || b.endsWith(want); });
    if (!hit) throw new Error('bundle 里找不到模块: ' + spec);
    return hit;
  }
  function load(spec) {
    const key = resolve(spec);
    if (cache.has(key)) return cache.get(key);
    const module = { exports: {} };
    cache.set(key, module.exports);                       // 先登记，防循环 require
    // 下面四个名字绑成 undefined，只是让「碰 DOM」的写法立刻抛，不等于沙箱：
    // new Function 的函数体照样够得着 globalThis、process 和 fs。执行解包产物是 brief 授权的取数据
    // 手段，前提是所读的包是自己从官方小程序解出来的；来路不明的包不要往这儿喂。
    new Function('require', 'module', 'exports',
      'window', 'document', 'navigator', 'localStorage',
      defs.get(key))(load, module, module.exports, undefined, undefined, undefined, undefined);
    cache.set(key, module.exports);
    return module.exports;
  }
  return { load, resolve };
}

module.exports = { readSource, readSourceBuffer, parseDefs, makeLoader, SRC };
