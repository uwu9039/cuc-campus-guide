import fs from 'node:fs';
import path from 'node:path';

function readPort() {
  const p = path.join(process.env.LOCALAPPDATA, 'Microsoft', 'Edge', 'User Data', 'DevToolsActivePort');
  const [port, wsPath] = fs.readFileSync(p, 'utf8').trim().split(/\r?\n/);
  return { port, wsPath };
}

export async function connect() {
  const { port, wsPath } = readPort();
  const ws = new WebSocket(`ws://127.0.0.1:${port}${wsPath}`);
  await new Promise((res, rej) => {
    ws.addEventListener('open', res, { once: true });
    ws.addEventListener('error', () => rej(new Error('CDP websocket error')), { once: true });
  });

  let seq = 0;
  const pending = new Map();
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? reject(new Error(m.error.message)) : resolve(m.result);
    }
  });

  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params, sessionId }));
    setTimeout(() => {
      if (pending.has(id)) { pending.delete(id); reject(new Error(`timeout ${method}`)); }
    }, 30000);
  });

  const targets = await send('Target.getTargets');
  const pages = targets.targetInfos.filter((t) => t.type === 'page');

  const attach = async (targetId) => {
    const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
    const evaluate = async (expression) => {
      const r = await send('Runtime.evaluate', {
        expression,
        awaitPromise: true,
        returnByValue: true,
      }, sessionId);
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception?.description || ''));
      return r.result.value;
    };
    const cdp = (method, params) => send(method, params, sessionId);
    return { sessionId, evaluate, cdp, detach: () => send('Target.detachFromTarget', { sessionId }) };
  };

  return { send, pages, attach, close: () => ws.close() };
}
