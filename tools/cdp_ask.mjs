import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { connect } from './cdp.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const QFILE = `${ROOT}/aia-runs/questions-expanded.txt`;
const AFILE = `${ROOT}/aia-runs/answers-20261028.jsonl`;
const LIMIT = Number(process.argv[2] || 0);
const START_AT = Number(process.argv[3] || 0);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (...a) => console.log(`[${new Date().toLocaleTimeString('zh-CN', { hour12: false })}]`, ...a);

const questions = fs.readFileSync(QFILE, 'utf8').split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
const answered = new Set();
for (const line of fs.readFileSync(AFILE, 'utf8').split(/\r?\n/)) {
  if (!line.trim()) continue;
  try { answered.add(JSON.parse(line).q); } catch {}
}
let todo = questions.filter((q) => !answered.has(q)).slice(START_AT);
if (LIMIT > 0) todo = todo.slice(0, LIMIT);
log(`remaining ${todo.length}`);

const c = await connect();
const target = c.pages.find((p) => p.url.includes('aihub.cuc.edu.cn') && p.url.includes('zcDialogue'))
  || c.pages.find((p) => p.url.includes('aihub.cuc.edu.cn'));
if (!target) { log('NO_AIHUB_TAB'); process.exit(1); }
const s = await c.attach(target.targetId);
log('attached', target.title.slice(0, 30));

const js = {
  focus: `(() => { const e = document.querySelector('#debotInput .ql-editor'); if (!e) return 'noeditor'; e.focus(); return 'ok'; })()`,
  editorText: `(() => { const e = document.querySelector('#debotInput .ql-editor'); return e ? e.innerText.trim() : null; })()`,
  count: `document.querySelectorAll('.chat-item-response').length`,
  sendState: `(() => { const b = document.querySelector('.send-btns.send-btn'); if (!b) return 'nosend'; return { cls: b.className, disabled: /disabled|forbid/i.test(b.className) || b.getAttribute('aria-disabled') === 'true' }; })()`,
  clickSend: `(() => { const b = document.querySelector('.send-btns.send-btn'); if (!b) return 'nosend'; b.click(); return 'clicked'; })()`,
  last: `(() => {
    const rs = document.querySelectorAll('.chat-item-response');
    if (!rs.length) return null;
    const r = rs[rs.length - 1];
    const links = [...r.querySelectorAll('a[href]')].map(a => ({ t: a.innerText.trim().slice(0, 80), h: a.href })).filter(x => /fileview|fileId/.test(x.h));
    const copy = !!r.querySelector('[class*=copy]');
    const txt = r.innerText.trim();
    return { txt, links, copy, len: txt.length };
  })()`,
  scrollBottom: `(() => { const b = document.querySelector('.chat-list, .chat-container, .chat-content'); if (b) b.scrollTop = b.scrollHeight; window.scrollTo(0, document.body.scrollHeight); return 'ok'; })()`,
};

async function ask(q) {
  const t0 = Date.now();
  const n0 = await s.evaluate(js.count);

  await s.evaluate(js.focus);
  await s.cdp('Input.dispatchKeyEvent', { type: 'keyDown', modifiers: 2, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65 });
  await s.cdp('Input.dispatchKeyEvent', { type: 'keyUp', modifiers: 2, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65 });
  await s.cdp('Input.dispatchKeyEvent', { type: 'keyDown', modifiers: 0, key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8, nativeVirtualKeyCode: 8 });
  await s.cdp('Input.dispatchKeyEvent', { type: 'keyUp', modifiers: 0, key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8, nativeVirtualKeyCode: 8 });
  await s.cdp('Input.insertText', { text: q });
  await sleep(400);

  let typed = await s.evaluate(js.editorText);
  if (typed !== q) {
    await sleep(500);
    typed = await s.evaluate(js.editorText);
  }
  if (!typed || !typed.includes(q.slice(0, 6))) return { ok: false, note: `typed_mismatch:${String(typed).slice(0, 30)}`, secs: 0 };
  if (typed !== q) {
    // 清空重来一次
    await s.evaluate(`(() => { const e = document.querySelector('#debotInput .ql-editor'); if (e) { e.focus(); document.execCommand('selectAll'); document.execCommand('delete'); } return 'ok'; })()`);
    await s.cdp('Input.insertText', { text: q });
    await sleep(400);
    typed = await s.evaluate(js.editorText);
    if (typed !== q) return { ok: false, note: `typed_retry:${String(typed).slice(0, 30)}`, secs: 0 };
  }

  for (let i = 0; i < 10; i++) {
    const st = await s.evaluate(js.sendState);
    if (st === 'nosend') return { ok: false, note: 'no_send_button', secs: 0 };
    if (!st.disabled) break;
    await sleep(500);
  }
  const clicked = await s.evaluate(js.clickSend);
  if (clicked !== 'clicked') return { ok: false, note: 'click_failed', secs: 0 };

  let last = null;
  let stableAt = 0;
  let prevLen = -1;
  const deadline = Date.now() + 300000;
  while (Date.now() < deadline) {
    await sleep(3000);
    const n1 = await s.evaluate(js.count).catch(() => -1);
    if (n1 <= n0) continue;
    last = await s.evaluate(js.last).catch(() => null);
    if (!last) continue;
    if (last.copy && last.len > 20) break;
    if (last.len === prevLen) { if (Date.now() - stableAt > 12000) break; }
    else { prevLen = last.len; stableAt = Date.now(); }
  }
  await s.evaluate(js.scrollBottom).catch(() => {});
  if (!last) return { ok: false, note: 'no_answer_timeout', secs: Math.round((Date.now() - t0) / 1000) };
  return {
    ok: last.len > 10,
    secs: Math.round((Date.now() - t0) / 1000),
    chars: last.len,
    a: last.txt,
    links: last.links,
  };
}

let ok = 0, fail = 0;
for (let i = 0; i < todo.length; i++) {
  const q = todo[i];
  let rec;
  try {
    rec = await ask(q);
  } catch (e) {
    rec = { ok: false, note: `error:${e.message}`.slice(0, 120), secs: 0 };
  }
  const out = { q, t: new Date().toISOString(), done: !!rec.ok, secs: rec.secs || 0, note: rec.note || '', chars: rec.chars || 0, a: rec.a || '', links: rec.links || [] };
  fs.appendFileSync(AFILE, JSON.stringify(out) + '\n');
  if (out.done) { ok++; log(`OK  ${i + 1}/${todo.length} ${out.secs}s ${out.chars}c ${out.links.length}L  ${q.slice(0, 28)}`); }
  else { fail++; log(`FAIL ${i + 1}/${todo.length} ${out.note}  ${q.slice(0, 28)}`); }
  await sleep(1500);
}
log(`batch done ok=${ok} fail=${fail}`);
process.exit(0);
