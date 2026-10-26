// 直连 Chrome DevTools Protocol：给「问道中传」输入框发真实键盘输入并发送。
// 代理只暴露 eval/click，模拟不出 Quill 需要的 beforeinput，所以这里直连调试端口。
// 用法：node tools/cdp_type.mjs "成绩单密封章几点能办？"

const PORT = 9222;

async function listTargets() {
  const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
  return r.json();
}

function connect(url) {
  const ws = new WebSocket(url);
  let id = 0;
  const pending = new Map();
  ws.addEventListener("message", (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  });
  const ready = new Promise((res) => ws.addEventListener("open", () => res()));
  const send = (method, params = {}) =>
    new Promise((resolve) => {
      const mid = ++id;
      pending.set(mid, resolve);
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
  return { ready, send, close: () => ws.close() };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const question = process.argv[2] || "成绩单密封章几点能办？";
  const targets = await listTargets();
  const t = targets.find((x) => x.type === "page" && x.url.includes("aihub.cuc.edu.cn"));
  if (!t) {
    console.error("没找到问道中传标签页");
    process.exit(2);
  }
  console.log("目标：", t.url.slice(0, 80));

  const cdp = connect(t.webSocketDebuggerUrl);
  await cdp.ready;

  const evalJs = async (expr) => {
    const r = await cdp.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    return r.result?.result?.value;
  };

  // 1. 聚焦输入框并清空
  await evalJs(`(()=>{const ed=document.querySelector('.ql-editor');ed.focus();ed.innerHTML='<p><br></p>';return 'ok'})()`);
  await sleep(300);

  // 2. 真实键入（Input.insertText 会触发 beforeinput/input，Quill 才认）
  await cdp.send("Input.insertText", { text: question });
  await sleep(600);
  const state = await evalJs(
    `(()=>{const ed=document.querySelector('.ql-editor');const b=document.querySelector('.send-btn');return (ed?ed.innerText.trim():'')+' || '+ (b?b.className:'no-btn')})()`
  );
  console.log("输入后状态：", state);

  // 3. 点发送
  await evalJs(`(()=>{const b=document.querySelector('.send-btn');if(b)b.click();return 'clicked'})()`);

  // 4. 等回答：正文不再增长或出现关键词就收
  let last = 0;
  for (let i = 0; i < 60; i++) {
    await sleep(1000);
    const len = await evalJs(`document.body.innerText.length`);
    if (len === last && i > 8) break;
    last = len;
  }
  const text = await evalJs(`document.body.innerText`);
  console.log("---- 回答区 ----");
  console.log((text || "").slice(-1500));
  cdp.close();
})();
