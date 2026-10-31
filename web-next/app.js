/* ============================================================
   校园办事向导 / web-next/app.js
   零依赖。所有事实来自 /api/*，界面只做呈现与组织，不生成内容。
   ============================================================ */
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  const isMobile = () => window.matchMedia("(max-width: 900px)").matches;

  // 首页精选问法：七条先反问再作答，三条直接查地点并打开地图。
  // 改词后要逐条打 /api/ask 验证，确认仍命中同一条目、反问能走到答案、地点带 map。
  const FEATURED_PRESETS = [
    "出国用的成绩单怎么开",
    "转专业要满足什么条件",
    "一教在哪",
    "助学贷款怎么申请",
    "校医院在哪",
    "想补选一门课怎么办",
    "宿舍没电了怎么买电",
    "图书馆在哪",
    "考试去不了怎么缓考",
    "奖学金怎么评",
  ];

  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const num = (n) => Number(n || 0).toLocaleString("zh-CN");
  const pct = (v) => Math.round((Number(v) || 0) * 100) + "%";

  // 校园地点链接化：答案里出现的地点名点一下，就等于问「X 在哪」。
  // 只收有辨识度的名字：纯数字、太泛的两字词不进链接表。
  let PLACE_RE = null;
  const PLACE_SKIP = new Set(["快递", "大集", "教务", "国重", "活动中心"]);
  const PLACE_TWO = new Set(["主楼", "南门", "北门", "西门", "1教", "一教", "艺传", "南操", "大活", "北苑"]);

  function buildPlaces(pois) {
    const seen = new Set();
    const names = [];
    for (const p of pois || []) {
      for (const raw of [p.name, ...(p.aliases || [])]) {
        const s = String(raw || "").trim();
        if (s.length < 2 || /^\d+$/.test(s) || PLACE_SKIP.has(s)) continue;
        if (s.length === 2 && !PLACE_TWO.has(s)) continue;
        if (seen.has(s)) continue;
        seen.add(s);
        names.push(s);
      }
    }
    names.sort((a, b) => b.length - a.length);
    if (!names.length) { PLACE_RE = null; return; }
    const body = names.map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
    PLACE_RE = new RegExp(`(?<!第)(?:${body})`, "g");
  }

  // 只对已转义的纯文本调用；不会碰标签属性。
  function linkify(html) {
    if (!PLACE_RE || !html) return html;
    PLACE_RE.lastIndex = 0;
    return html.replace(PLACE_RE, (m) =>
      `<a class="plink" href="#" data-ask="${esc(m + "在哪")}" title="问：${esc(m)}在哪">${m}</a>`);
  }

  // 序号已由列表渲染，泛化的「第 N 步」不再重复出现在后缀里
  const stepNote = (s, i) => {
    if (typeof s === "string") return "";
    return s.where || (s.when && s.when !== `第 ${i + 1} 步` ? s.when : "");
  };

  const state = {
    slots: {},
    item: null,
    last: null,
    lastQuery: "",
    tab: "overview",
    deliver: null,
    checked: new Set(),
    contacts: null,
    contactsPurpose: "",
    contactsQ: "",
    exCount: 0,
    busy: false,
    drawerOpen: false,
    sheetOpen: false,
    presets: [],
    history: [],
  };

  const el = {
    thread: $("#thread"),
    scroller: $("#scroller"),
    q: $("#q"),
    composer: $("#composer"),
    send: $("#send"),
    presetRow: $("#presets"),
    statline: $("#statline"),
    llm: $("#llmsw"),
    llmhint: $("#llmhint"),
    title: $("#institle"),
    sub: $("#jnsub"),
    insbody: $("#insbody"),
    tabs: $("#tabs"),
    qcount: $("#qcount"),
    stamp: $("#insstamp"),
    inspector: $("#inspector"),
    scrim: $("#scrim"),
    drawer: $("#drawer"),
    drawertitle: $("#drawertitle"),
    drawerbody: $("#drawerbody"),
    toast: $("#toast"),
    map: $("#map-drawer"),
    maptarget: $("#maptarget"),
    mapopen: $("#mapopen"),
    mapclose: $("#mapclose"),
    mapcanvas: $("#mapcanvas"),
    mapfoot: $("#mapfoot"),
    printsheet: $("#printsheet"),
  };

  /* ---------------- 基础 ---------------- */
  async function api(path, body) {
    let res;
    try {
      res = await fetch(path, body
        ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
        : {});
    } catch (e) {
      throw new Error("连不上本地服务，请确认 app.py 已在当前端口运行");
    }
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new Error((data && (data.detail || data.message)) || `请求失败（${res.status}）`);
    return data;
  }

  let toastTimer = 0;
  function toast(msg) {
    el.toast.textContent = msg;
    el.toast.dataset.show = "true";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.toast.dataset.show = "false"; }, 2500);
  }

  async function copyText(text, okMsg) {
    try {
      await navigator.clipboard.writeText(text);
      toast(okMsg || "已复制");
      return true;
    } catch (e) {
      try {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
        toast(okMsg || "已复制");
        return true;
      } catch (e2) {
        toast("复制失败，请手动选择文字");
        return false;
      }
    }
  }

  const statusText = (item) => !item ? ""
    : item.status === "verified" ? "原文已核验"
    : item.status === "partial" ? "官方无正文"
    : "待核验";

  /* ---------------- 启动 ---------------- */
  function boot() {
    bind();
    renderEmpty();
    loadMeta();
    const params = new URLSearchParams(location.search);
    const q = (params.get("q") || "").trim();
    const ct = params.get("ct");
    const tab = params.get("tab");
    if (["overview", "material", "steps", "quotes"].includes(tab)) openTab(tab);
    if (q) {
      el.q.value = q;
      ask(q);
    }
    if (ct) openContacts(ct);
  }

  async function loadMeta() {
    try {
      const h = await api("/api/health");
      const bits = [`${num(h.items)} 事项`, `${num(h.verified)} 已核验`, `${num(h.sources)} 份原文`];
      el.statline.innerHTML = bits.map(esc).join(" / ");
      el.statline.title = `事项库更新于 ${h.data_updated || "未知"}；原文库 ${num(h.vector_chunks)} 段`;
      if (!h.key_configured) {
        el.llm.disabled = true;
        el.llm.closest(".llm").title = "未配置模型密钥，模型裁决不可用";
        el.llm.closest(".llm").style.opacity = ".5";
      }
    } catch (e) {
      el.statline.textContent = "本地服务未连接";
    }
    state.presets = FEATURED_PRESETS;
    renderPresets();
    try {
      const c = await api("/api/campus?limit=500");
      buildPlaces(c.pois);
    } catch (e) { /* 地点表失败只影响链接化 */ }
  }

  function renderPresets() {
    if (!state.presets.length) return;
    el.presetRow.innerHTML = state.presets
      .map((s) => `<button type="button" data-ask="${esc(s)}">${esc(s)}</button>`).join("");
    syncPresetEdge();
  }

  function syncPresetEdge() {
    const row = el.presetRow;
    const max = row.scrollWidth - row.clientWidth;
    if (max <= 1) {
      row.dataset.overflow = "false";
      row.dataset.edge = "none";
      return;
    }
    row.dataset.overflow = "true";
    const left = row.scrollLeft > 1;
    const right = row.scrollLeft < max - 1;
    row.dataset.edge = left && right ? "middle" : left ? "end" : right ? "start" : "none";
  }

  function wheelPresets(e) {
    const row = el.presetRow;
    const max = row.scrollWidth - row.clientWidth;
    if (max <= 1 || e.ctrlKey || e.metaKey) return;
    if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
    const delta = e.deltaMode === 1 ? e.deltaY * 16
      : e.deltaMode === 2 ? e.deltaY * row.clientWidth : e.deltaY;
    if (delta > 0 ? row.scrollLeft >= max - 1 : row.scrollLeft <= 1) return;
    e.preventDefault();
    row.scrollLeft += delta;
  }

  let presetDrag = null;
  let presetSuppress = false;

  function bindPresets() {
    const row = el.presetRow;
    row.addEventListener("wheel", wheelPresets, { passive: false });
    row.addEventListener("scroll", syncPresetEdge, { passive: true });
    row.addEventListener("pointerdown", (e) => {
      if (e.pointerType === "touch" || e.button !== 0) return;
      if (row.scrollWidth - row.clientWidth <= 1) return;
      presetDrag = { id: e.pointerId, x: e.clientX, left: row.scrollLeft, moved: false };
    });
    row.addEventListener("pointermove", (e) => {
      if (!presetDrag || e.pointerId !== presetDrag.id) return;
      const dx = e.clientX - presetDrag.x;
      if (!presetDrag.moved && Math.abs(dx) < 4) return;
      if (!presetDrag.moved) {
        presetDrag.moved = true;
        row.setPointerCapture(e.pointerId);
        row.dataset.dragging = "true";
      }
      row.scrollLeft = presetDrag.left - dx;
      e.preventDefault();
    });
    const endDrag = (e) => {
      if (!presetDrag || e.pointerId !== presetDrag.id) return;
      const moved = presetDrag.moved;
      presetDrag = null;
      row.dataset.dragging = "false";
      if (row.hasPointerCapture(e.pointerId)) row.releasePointerCapture(e.pointerId);
      if (moved) {
        presetSuppress = true;
        setTimeout(() => { presetSuppress = false; }, 300);
      }
    };
    row.addEventListener("pointerup", endDrag);
    row.addEventListener("pointercancel", endDrag);
    row.addEventListener("click", (e) => {
      if (!presetSuppress) return;
      e.preventDefault();
      e.stopPropagation();
    }, true);
    window.addEventListener("resize", syncPresetEdge);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(syncPresetEdge);
  }

  function renderEmpty() {
    const samples = ["校园卡丢了怎么办", "开成绩单要带什么", "转专业到新闻学院要什么条件"];
    el.thread.innerHTML = `<div class="empty" id="empty">
      <p class="ek">校园办事向导</p>
      <h1>说得清，<em>带得对</em>。</h1>
      <p>每句结论旁边都压着原文。查得到，抄得走，错了知道该找谁。问一句，右边同时打开这件事的档案。</p>
      <div class="chips">${samples.map((s) => `<button type="button" data-ask="${esc(s)}">${esc(s)}</button>`).join("")}</div>
      <p class="eexit"><b>全库 8,500 多条原文事项</b>来自学校官网、公众号与制度汇编，逐条对过原文。<br>原文没写的字段，它说“没写”，不替学校补。</p>
    </div>`;
  }

  /* ---------------- 提问 ---------------- */
  function addExchange(text) {
    const empty = $("#empty");
    if (empty) empty.remove();
    const ex = document.createElement("article");
    ex.className = "ex";
    ex.dataset.q = text;
    state.exCount += 1;
    ex.innerHTML = `<div class="ask"><p class="bubble">${esc(text)}</p></div>
      <div class="ans" data-ans>
        <div class="loading"><span class="dots"><i></i><i></i><i></i></span>在本地事项库里找这一件事，并核对原文…</div>
        <div class="skel w60"></div><div class="skel"></div>
      </div>`;
    el.thread.appendChild(ex);
    scrollToEx(ex);
    return ex;
  }

  function scrollToEx(ex) {
    requestAnimationFrame(() => {
      const top = ex.offsetTop - 18;
      el.scroller.scrollTo({ top, behavior: reduced.matches ? "auto" : "smooth" });
    });
  }

  function extractAnswerText(d) {
    if (d.llm_answer && d.llm_answer.text) return d.llm_answer.text.slice(0, 500);
    const parts = d.answers || [];
    const bits = [];
    for (const p of parts) {
      if (p.text) bits.push(p.text);
      else if (p.steps && p.steps.length) bits.push(p.steps.map(s => typeof s === "string" ? s : (s.what || "")).join("；"));
      else if (p.lines && p.lines.length) bits.push(p.lines.join("；"));
    }
    const joined = bits.join("\n").slice(0, 500);
    if (joined) return joined;
    if (d.normalized) return d.normalized;
    return d.search_note || "（未匹配到事项）";
  }

  async function ask(text, opts = {}) {
    text = (text || "").trim();
    if (text.length < 2 && !/^\s*\d{1,3}\s*(?:号楼|号|楼|教)?\s*[。.、,，!！?？]*\s*$/.test(text)) { toast("请再说得具体一点"); return; }
    if (state.busy) return;
    if (!opts.keepSlots) state.slots = {};
    state.busy = true;
    el.send.disabled = true;
    const ex = addExchange(text);
    const ans = $("[data-ans]", ex);
    try {
      const d = await api("/api/ask", {
        text,
        slots: state.slots,
        router_llm: el.llm.checked,
        context_item: state.item ? state.item.id : null,
        context_slots: (state.last && state.last.known) || {},
        messages: state.history.slice(-12),
      });
      state.last = d;
      state.lastQuery = text;
      ex.__data = d;
      ans.innerHTML = renderAnswer(d, ex);
      afterAnswer(d);
      const assistantText = extractAnswerText(d);
      state.history.push({ role: "user", content: text });
      state.history.push({ role: "assistant", content: assistantText });
      if (state.history.length > 24) state.history = state.history.slice(-24);
    } catch (e) {
      ans.innerHTML = renderError(e.message, text);
    } finally {
      state.busy = false;
      el.send.disabled = false;
      if (!isMobile()) el.q.focus({ preventScroll: true });
    }
  }

  function afterAnswer(d) {
    if (d.matched && d.item && !(d.disambiguate && d.disambiguate.length)) {
      setItem(d.item);
      loadDeliver();
    }
    if (d.map) showMap(d.map); else hideMap();
    updateSensitiveHint(d);
    updateStamp();
  }

  function renderAnswer(d, ex) {
    if (d.plan) return planCard(d, ex);
    if (!d.matched) return notFoundCard(d);
    if (Array.isArray(d.disambiguate) && d.disambiguate.length && d.clarify) return ambiguousCard(d);
    if (d.hold) return followupCard(d, ex);
    return answerCard(d, ex);
  }

  /* 一面答复的渲染：普通答案卡和「先确认」卡共用 */
  function partHtml(a) {
    const qs = a.quotes || [];
    let val;
    if (!a.found) {
      val = `<p class="aval none">官方页面没有写这一项</p>`;
    } else if (Array.isArray(a.steps) && a.steps.length) {
      val = `<ol class="asteps">${a.steps.map((s, i) => {
        const what = typeof s === "string" ? s : (s.what || "");
        const where = stepNote(s, i);
        return `<li><span class="n">${String(i + 1).padStart(2, "0")}</span><span>${linkify(esc(what))}${where ? `<span class="w">${linkify(esc(where))}</span>` : ""}</span></li>`;
      }).join("")}</ol>`;
    } else if (Array.isArray(a.lines) && a.lines.length) {
      val = `<ul class="alines">${a.lines.map((s) => `<li>${linkify(esc(s))}</li>`).join("")}</ul>`;
    } else {
      const t = a.text == null ? "" : String(a.text);
      val = `<p class="aval${t.length > 40 ? " long" : ""}">${linkify(esc(t || "官方页面没有写这一项"))}</p>`;
    }
    const q = qs[0] ? quoteLine(qs[0]) : (a.focus === "contact" && a.found
      ? `<div class="qmore">联系人取自条目归属部门，官方页面没有单列这句话</div>` : "");
    const more = qs.length > 1 ? `<div class="qmore">这一面另有 ${qs.length - 1} 条原文，点核对原文查看</div>` : "";
    return `<div class="aone"><div class="alab">${esc(a.label || "答复")}</div>${val}${q}${more}</div>`;
  }

  /* 二维码与官方附件 */
  function attachBlock(item) {
    const qr = Array.isArray(item.qr) ? item.qr : [];
    const pdfs = Array.isArray(item.pdf) ? item.pdf : [];
    if (!qr.length && !pdfs.length) return "";
    const codes = qr.map((q) => `<figure class="qrcode"><img src="${esc(q.src)}" alt="${esc(q.label || "二维码")}" loading="lazy"><figcaption>${esc(q.label || "")}</figcaption></figure>`).join("");
    const files = pdfs.length
      ? `<div class="pdflist"><div class="pdflab">官方简章 PDF · ${pdfs.length} 份</div>${pdfs.map((p) => `<a href="${esc(p.url)}" target="_blank" rel="noreferrer"><span>${esc(p.title)}</span><span class="go">↗</span></a>`).join("")}</div>`
      : "";
    return `<div class="attach">${codes ? `<div class="qrwrap">${codes}</div>` : ""}${files}</div>`;
  }

  /* 相关事项：同一个词还能问什么 */
  function relatedBlock(list) {
    if (!Array.isArray(list) || !list.length) return "";
    const opts = list.map((b) =>
      `<button class="opt" type="button" data-ask="${esc(b.title)}">${esc(b.label || b.title)}<span class="odept">${esc(b.dept || "")}</span></button>`).join("");
    return `<div class="sec related"><h3>相关事项（点一下直接问）</h3><div class="opts">${opts}</div></div>`;
  }

  /* 普通答案 */
  function answerCard(d, ex) {
    const item = d.item || {};
    const quotes = d.quotes || [];
    const body = (d.answers || []).map(partHtml).join("");

    const noteBits = [];
    if (d.note) noteBits.push(linkify(esc(d.note)));
    else if (d.missing && d.missing.length) noteBits.push(`官方页面没有写 ${esc(d.missing.join("、"))}，不替它补`);

    return `<div class="card">
      <div class="cardhead">
        <span class="tag${item.status === "verified" ? "" : " warn"}">${esc(statusText(item))}</span>
        <span class="norm" title="${esc(d.normalized || "")}">理解成 ${esc(d.normalized || "")}</span>
        <span class="conf" title="规则匹配分数">${pct(d.confidence)}</span>
      </div>
      <div class="cardbody">${body}${noteBits.length ? `<p class="plannote">${noteBits.join("<br>")}</p>` : ""}${attachBlock(item)}${relatedBlock(d.related)}</div>
      <div class="cardfoot">
        <button class="cf key" type="button" data-act="ev">核对原文<span class="n">${quotes.length}</span></button>
        <button class="cf" type="button" data-act="mat">清单与流程</button>
        <button class="cf" type="button" data-act="copy">复制答案</button>
        <button class="cf" type="button" data-act="loc">位置</button>
        <span class="cfstamp">NO.${String(state.exCount).padStart(3, "0")} / 条目 ${esc(item.title || "")}</span>
      </div>
    </div>`;
  }

  function quoteLine(q, opts = {}) {
    if (!q) return "";
    const meta = [q.kind, q.date].filter(Boolean).join(" / ") || "原文";
    const who = q.label || q.src || "";
    const whoHtml = who
      ? `<span class="who">${q.url ? `<a href="${esc(q.url)}" target="_blank" rel="noreferrer">${esc(who)}</a>` : esc(who)}</span>`
      : "";
    const short = opts.short && q.quote && q.quote.length > 120 ? q.quote.slice(0, 120) + "…" : q.quote;
    return `<div class="qline">
      <span class="qmeta">${esc(meta)}</span>
      <div class="qtxt">${linkify(esc(short))}${whoHtml}</div>
    </div>`;
  }

  /* 歧义：让用户在候选里选 */
  function ambiguousCard(d) {
    const n = (d.disambiguate || []).length;
    const reason = d.reason || (n === 2
      ? "这两件事办起来不是一处，选一个，我按那件事的原文回答，不猜"
      : "选一个，我按那件事的原文回答，不猜");
    const opts = (d.disambiguate || []).map((b) =>
      `<button class="opt" type="button" data-ask="${esc(b.title)}">${esc(b.label || b.title)}<span class="odept">${esc(b.dept || "")}</span></button>`).join("");
    return `<div class="notice">
      <h3>${esc(d.clarify || "没太确定你问的是哪一件")}</h3>
      <p>${esc(reason)}</p>
      <div class="opts">${opts}</div>
    </div>`;
  }

  /* 未命中 */
  function notFoundCard(d) {
    const hitRows = (d.original_search || []).map((h) => `
      <div class="hitrow">
        <div class="ht">${esc(h.title || "原文段落")}</div>
        <div class="hm"><span>${esc(h.kind || "原文")}</span><span>相关度 ${pct(h.score)}</span>${h.page ? `<span>p.${esc(h.page)}</span>` : ""}</div>
        <div class="hs">${esc(h.snippet || "")}</div>
        ${h.url ? `<a class="lnk" href="${esc(h.url)}" target="_blank" rel="noreferrer">打开原文 ↗</a>` : ""}
      </div>`).join("");

    const alts = (d.alternatives || []).map((a) =>
      `<button class="opt" type="button" data-ask="${esc(a.title)}">${esc(a.title)}</button>`).join("");

    const dis = (d.disambiguate || []).map((b) =>
      `<button class="opt" type="button" data-ask="${esc(b.title)}">${esc(b.title)}<span class="odept">${esc(b.dept || "")}</span></button>`).join("");

    const related = (d.related_items || []).map((a) =>
      `<button class="opt" type="button" data-ask="${esc(a.title)}">${esc(a.title)}</button>`).join("");

    const hints = (d.hints || []).map((h) => `
      <div class="hintrow">
        <div class="hintdept"><b>${esc(h.name)}</b> 可能管这件事
          ${h.basis ? `<span class="why">依据 ${esc(h.basis)}</span>` : ""}</div>
        <div class="hm">${(h.matched || []).map((m) => `<span class="ktag">${esc(m)}</span>`).join("")}</div>
        ${h.url ? `<a class="lnk" href="${esc(h.url)}" target="_blank" rel="noreferrer">打开部门网站 ↗</a>` : ""}
      </div>`).join("");

    const contacts = (d.contacts || []).map((c) => {
      const val = c.value || "";
      const href = c.kind === "phone" ? `tel:${val.replace(/\s/g, "")}`
        : c.kind === "email" ? `mailto:${val}` : "";
      const kindLabel = { phone: "电话", email: "邮箱", wechat: "公众号", web: "网址", url: "网址", link: "网址" };
      return `<div class="ctrow">
        <div class="cttop"><span class="ctkind">${esc(kindLabel[c.kind] || c.kind || "联系")}</span>
          <span class="ctval">${href ? `<a href="${esc(href)}" style="border:0;color:inherit">${esc(val)}</a>` : esc(val)}</span></div>
        <div class="ctdept">${esc(c.dept || "")}${c.purpose ? ` / ${esc(c.purpose)}` : ""}</div>
        <div class="ctacts">${c.source_url ? `<a href="${esc(c.source_url)}" target="_blank" rel="noreferrer">来源原文 ↗</a>` : ""}</div>
      </div>`;
    }).join("");

    const next = (d.next_actions || []).map((s) => `<li>${esc(s)}</li>`).join("");

    const gen = d.llm_answer ? `<div class="genbox">
      <div class="genhead"><span class="gentag">模型生成</span><span>没有官方条目，以下由大模型直接回答</span></div>
      <p class="gentext">${esc(d.llm_answer.text || "")}</p>
      <p class="gencaveat">${esc(d.llm_answer.disclaimer || "内容由大模型生成，可能不准确")}${d.llm_answer.caveat ? ` ${esc(d.llm_answer.caveat)}` : ""}</p>
    </div>` : "";

    return `<div class="notice">
      <h3>没对上事项，我不硬猜</h3>
      <p>${d.topic ? `你问的是 ${esc(d.topic)}，` : ""}${esc(d.search_note || "换个更具体的说法，比如 校园卡补卡 或 开成绩单，下面是我能从原文里找到的线索")}</p>
      ${gen}
      ${hitRows ? `<div class="hintlist">${hitRows}</div>` : ""}
      ${dis ? `<p style="margin-top:14px">${esc(d.clarify || "也许你要办的是下面某一类")}</p><div class="opts">${dis}</div>` : ""}
      ${related ? `<p style="margin-top:14px">这些事项可能是你要的</p><div class="opts">${related}</div>` : ""}
      ${alts ? `<p style="margin-top:14px">相近的事项</p><div class="opts">${alts}</div>` : ""}
      ${hints ? `<div class="sec"><h3>归口线索（非官方流程）</h3>${hints}</div>` : ""}
      ${contacts ? `<div class="sec"><h3>公开联系方式（按你问的事匹配，非办事流程）</h3>${contacts}</div>` : ""}
      ${next ? `<div class="sec"><h3>接下来可以这样办</h3><ul class="alines">${next}</ul></div>` : ""}
      ${d.suggestion ? `<p style="margin-top:14px;color:var(--ink-3)">${esc(d.suggestion)}</p>` : ""}
      <div class="opts" style="margin-top:14px">
        <button class="opt" type="button" data-searching="${esc(d.query || "")}">拿这句话去原文库搜</button>
        <button class="opt" type="button" data-contacts="1">找归口部门电话</button>
      </div>
    </div>`;
  }

  /* 追问 */
  function followupCard(d, ex) {
    const known = Object.entries(d.known || {});
    const knownHtml = known.length
      ? `<div class="known">已记下 ${known.map(([, v]) => `<span class="ktag">${esc(v)}</span>`).join("")}</div>`
      : "";
    const fqs = (d.followups || []).map((f, i) => `
      <div class="fq">
        <p class="fqq">${String(i + 1).padStart(2, "0")}　${esc(f.question)}</p>
        <p class="fqw">为什么问 ${esc(f.why || "这一项会改变答案")}</p>
        <div class="opts">${(f.options || []).map((o) =>
          `<button class="opt" type="button" data-key="${esc(f.key)}" data-opt="${esc(o)}">${esc(o)}</button>`).join("")}</div>
      </div>`).join("");
    const base = (d.answers || []).filter((a) => a.found).map(partHtml).join("");
    return `<div class="fu" data-orig="${esc(d.query || "")}">
      <div class="fuhead"><h3>这件事分几种情况，答之前先确认 ${d.followups.length} 件事</h3>
        <span>${esc(d.normalized || "")}</span></div>
      ${knownHtml}${fqs}
      ${relatedBlock(d.related)}
      ${base ? `<div class="fubase"><h3>先给你能确定的部分</h3>${base}</div>` : ""}
    </div>`;
  }

  /* 转专业计划 */
  function planCard(d, ex) {
    const item = d.item || {};
    const parts = (d.answers || []).map((p) => {
      const lines = Array.isArray(p.lines) && p.lines.length ? p.lines : [p.text].filter(Boolean);
      return `<div class="plansec"><h4>${esc(p.label || "")}</h4>
        <ul class="alines">${lines.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div>`;
    }).join("");
    const focus = (d.plan && d.plan.focus) || {};
    const majors = ((d.plan && d.plan.majors) || []).slice(0, 10).map((m) =>
      `<button class="major" type="button" data-ask="${esc("转专业到" + ((d.plan && d.plan.college_label) || "") + m.name)}">${esc(m.name)}</button>`).join("");
    const scope = [];
    if (focus.major) scope.push(`按 ${focus.major} 单列`);
    else if (d.plan && d.plan.college_label) scope.push(`按 ${d.plan.college_label} 整体列出`);

    return `<div class="card">
      <div class="cardhead">
        <span class="tag${d.plan_no_file ? " warn" : ""}">${d.plan_no_file ? "学院未公开 PDF" : "接收计划原文"}</span>
        <span class="norm">${esc(d.normalized || "")}</span>
        <span class="conf">${pct(d.confidence)}</span>
      </div>
      <div class="cardbody">
        ${scope.length ? `<p class="insempty2">${esc(scope.join("；"))}，以下按接收计划原表逐条保留</p>` : ""}
        ${parts || `<p class="aval none">这份接收计划没有可展开的条目</p>`}
        ${majors ? `<div class="sec"><h3>这份计划覆盖的专业</h3><div class="majors">${majors}</div></div>` : ""}
        ${d.plan_file ? `<a class="planfile" href="${esc(d.plan_file)}" target="_blank" rel="noreferrer">打开学院接收计划 PDF ↗</a>` : ""}
        ${d.note ? `<p class="plannote">${esc(d.note)}</p>` : ""}
      </div>
      <div class="cardfoot">
        <button class="cf key" type="button" data-act="ev">核对原文<span class="n">${(d.quotes || []).length}</span></button>
        <button class="cf" type="button" data-act="copy">复制答案</button>
        ${d.plan_file ? `<a class="cf" href="${esc(d.plan_file)}" target="_blank" rel="noreferrer">下载 PDF</a>` : ""}
        <span class="cfstamp">NO.${String(state.exCount).padStart(3, "0")} / 转专业接收计划</span>
      </div>
    </div>`;
  }

  function renderError(msg, retryText) {
    return `<div class="notice">
      <h3>这一步没走通</h3>
      <p>${esc(msg)}</p>
      <div class="opts"><button class="opt" type="button" data-retry="${esc(retryText)}">再试一次</button></div>
    </div>`;
  }

  function updateSensitiveHint(d) {
    const on = el.llm.checked;
    if (d && d.sensitive) {
      el.llmhint.className = "llmhint warn";
      el.llmhint.innerHTML = `这类问题（${esc((d.hits || []).join("、"))}）答错代价大，建议开启模型裁决`
        + (on ? "（已开启）" : `<button type="button" data-llmfix="1">开启并重答</button>`);
    } else if (d && d.rule_unsure && !on) {
      el.llmhint.className = "llmhint";
      el.llmhint.textContent = "规则对这句话没把握，开启模型裁决后，先把问题翻译成多种校园说法重新检索，再在候选条目里挑；一条都没收录时由模型直接生成，内容仅供参考";
    } else {
      el.llmhint.className = "llmhint";
      el.llmhint.textContent = "";
    }
  }

  function updateStamp() {
    const n = state.last && state.last.item ? String(state.exCount).padStart(3, "0") : "—";
    el.stamp.textContent = `NO.${n}`;
    el.qcount.textContent = (state.last && state.last.quotes ? state.last.quotes.length : 0);
  }

  /* ---------------- 档案 ---------------- */
  function setItem(item) {
    state.item = item;
    el.title.textContent = item.title;
    const band = item.confidence === "high" ? "核对程度高" : item.confidence === "low" ? "核对程度低" : "核对程度中";
    el.sub.textContent = [item.dept, statusText(item), band].filter(Boolean).join(" / ");
    renderIns();
  }

  async function loadDeliver() {
    if (!state.item) return;
    try {
      state.deliver = await api("/api/deliver", { item_id: state.item.id, slots: state.slots });
      if (state.tab === "material") renderIns();
    } catch (e) {
      state.deliver = null;
    }
    updateStamp();
  }

  function openTab(tab) {
    state.tab = tab;
    $$("#tabs [data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
    el.insbody.setAttribute("aria-labelledby", "tab-" + tab);
    renderIns();
  }

  function renderIns() {
    const item = state.item;
    if (!item) { renderInsEmpty(); return; }
    if (state.tab === "material") return renderMaterial(item);
    if (state.tab === "steps") return renderSteps(item);
    if (state.tab === "quotes") return renderQuotes(item);
    renderOverview(item);
  }

  function renderInsEmpty() {
    el.title.textContent = "条目档案";
    el.sub.textContent = "问一个问题，这里会出现它的官方依据、材料与流程。";
    el.qcount.textContent = "0";
    el.insbody.innerHTML = `<div class="insempty">
      <p class="ek">条目档案</p>
      <h3>右边不是附件，是答案的出处</h3>
      <p>问一句，这里固定显示四项：办理信息、要带的材料、可执行步骤、原文引文。任何一条结论都能落到原文上。</p>
      <ul>
        <li>原文没写的字段，显示“官方页面没有写”，不补全。</li>
        <li>转专业会直接展开学院接收计划，按专业列出条件与考核。</li>
        <li>清单可以打印，也可以复制成纯文本带走。</li>
      </ul>
    </div>`;
  }

  function renderOverview(item) {
    const rows = [
      ["办理部门", item.dept],
      ["办理渠道", (item.channel || []).join(" / ")],
      ["费用", item.fee],
      ["用时", item.duration],
      ["受理时间", item.window || item.hours],
      ["地点", item.location, true],
    ].filter(([, v]) => v && String(v).trim());

    const meta = rows.length
      ? `<dl class="metagrid">${rows.map(([k, v, wide]) =>
          `<div${wide ? ' class="wide"' : ""}><dt>${esc(k)}</dt><dd>${linkify(esc(v))}</dd></div>`).join("")}</dl>`
      : `<p class="insempty2">官方页面没有写办理部门、地点与费用。可以看原文或直接问联系人。</p>`;

    const pitfalls = (item.pitfalls || []).length
      ? `<div class="sec"><h3>这几种情况会白跑</h3><div class="warnbox">${item.pitfalls.map((p) => `<p>${linkify(esc(p))}</p>`).join("")}</div></div>`
      : "";

    const advisory = (item.advisory || []).length
      ? `<div class="sec"><h3>办理提示</h3><div class="srcbox">${item.advisory.map((a) => `<p class="insempty2">${linkify(esc(a))}</p>`).join("")}</div></div>`
      : "";

    const sources = (item.source || []).map((s) => `
      <div class="srcline"><span class="k">${esc(s.checked ? `核验 ${s.checked}` : "来源")}</span>
        ${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(s.title || s.url)} ↗</a>` : esc(s.title || "")}
      </div>`).join("");

    const note = item.note ? `<div class="sec"><h3>条目说明</h3><p class="insempty2">${esc(item.note)}</p></div>` : "";

    el.insbody.innerHTML = `${meta}${pitfalls}${advisory}${note}
      <div class="sec"><h3>官方来源</h3><div class="srcbox">${sources || `<p class="insempty2">这一条还没有可用来源。</p>`}</div></div>`;
  }

  function renderMaterial(item) {
    const d = state.deliver || item;
    const mats = ((d && d.materials) || []).map((m) => (typeof m === "string" ? { name: m } : m));
    const key = item.id;
    const checked = (i) => state.checked.has(key + ":" + i);
    const count = mats.filter((_, i) => checked(i)).length;

    const list = mats.length
      ? `<div class="matbar"><b>${count}/${mats.length}</b> 已备
          <button class="mini" type="button" data-act="matcopy">复制清单</button></div>
        <ul class="checks">${mats.map((m, i) => `
          <li role="checkbox" tabindex="0" aria-checked="${checked(i)}" data-mat="${i}">
            <span class="cbox" aria-hidden="true"></span>
            <span class="mname">${esc(m.name)}${m.note ? `<span class="mnote">${esc(m.note)}</span>` : ""}</span>
          </li>`).join("")}</ul>`
      : `<p class="insempty2">官方页面没有列出材料清单。这不等于不用带，原文里可能写在步骤中。</p>`;

    const draft = d && d.draft ? `
      <div class="draftbox">
        <h4>${esc(d.draft.title || "文书草稿")}
          <span>${d.draft.complete ? "已按条件填好" : "原因待你补充"}</span></h4>
        <pre class="draft">${esc(d.draft.text)}</pre>
        <div class="draftacts"><button class="ghostbtn" type="button" data-act="draftcopy">复制草稿</button></div>
      </div>` : "";

    el.insbody.innerHTML = `${list}${draft}
      <div class="sec"><h3>清单说明</h3><p class="insempty2">勾选只存在当前页面，不上传。带材料以官方原文与窗口要求为准。</p></div>`;
  }

  function renderSteps(item) {
    const steps = item.steps || [];
    const list = steps.length
      ? `<ol class="steps2">${steps.map((s, i) => {
          const what = typeof s === "string" ? s : s.what;
          const where = stepNote(s, i);
          return `<li><span class="n">${String(i + 1).padStart(2, "0")}</span>
            <span>${linkify(esc(what))}${where ? `<span class="w">${linkify(esc(where))}</span>` : ""}</span></li>`;
        }).join("")}</ol>`
      : `<p class="insempty2">官方页面没有给出可执行步骤。</p>`;
    el.insbody.innerHTML = `${list}
      <div class="sec"><h3>流程提示</h3><p class="insempty2">步骤来自官方页面的原文，没有排序加工。条件不同时会走的分支，会在提问时先问你。</p></div>`;
  }

  function renderQuotes(item) {
    const quotes = ((state.last && state.last.quotes) || []).filter((q) => q && q.quote);
    const seen = new Set();
    const uniq = quotes.filter((q) => (seen.has(q.quote) ? false : (seen.add(q.quote), true)));
    const list = uniq.length
      ? `<div class="quotelist">${uniq.map((q) => `
          <div class="q">
            <p class="t">${linkify(esc(q.quote))}</p>
            <div class="m"><span class="k">${esc(q.kind || "原文")}</span>
              <span>${esc(q.label || q.src || "")}</span>
              ${q.date ? `<span>${esc(q.date)}</span>` : ""}
              ${q.url ? `<a href="${esc(q.url)}" target="_blank" rel="noreferrer">打开 ↗</a>` : ""}
            </div>
          </div>`).join("")}</div>`
      : `<p class="insempty2">这次回答没有引用到原文段落。下面是条目登记的官方来源，可直接打开核对。</p>`;

    const src = (item.source || []).map((s) => `
      <div class="srcline" style="margin-top:10px">
        ${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(s.title || s.url)} ↗</a>` : esc(s.title || "")}
        ${s.checked ? `<span class="k">核验 ${esc(s.checked)}</span>` : ""}
      </div>`).join("");

    el.insbody.innerHTML = `${list}
      <div class="sec"><h3>官方来源</h3><div class="srcbox">${src || `<p class="insempty2">这一条还没有可用来源。</p>`}</div></div>`;
  }

  /* ---------------- 清单 / 打印 ---------------- */
  function checklistText() {
    const item = state.item;
    if (!item) return "";
    const d = state.deliver || item;
    const mats = ((d.materials) || []).map((m) => (typeof m === "string" ? m : m.name)).filter(Boolean);
    const steps = (item.steps || []).map((s, i) => `${i + 1}. ${typeof s === "string" ? s : s.what}`).filter(Boolean);
    const quotes = ((state.last && state.last.quotes) || []).slice(0, 3);
    return [
      `${item.title}（${item.dept || ""}）`,
      item.location ? `地点\n${item.location}` : "",
      item.fee ? `费用\n${item.fee}` : "",
      mats.length ? `要带\n${mats.map((m) => `□ ${m}`).join("\n")}` : "",
      steps.length ? `步骤\n${steps.join("\n")}` : "",
      `原文\n${quotes.map((q) => `- ${q.quote}\n  ${q.label || q.src || ""}${q.url ? " " + q.url : ""}`).join("\n")}`,
      `来源\n${(item.source || []).map((s) => s.url).filter(Boolean).join("\n")}`,
      "以上事实来自官方原文，由校园办事向导整理；原文没写的未补写。",
    ].filter(Boolean).join("\n\n");
  }

  function printSheet() {
    const item = state.item;
    if (!item) { toast("先问一件事，再打印"); return; }
    const d = state.deliver || item;
    const mats = ((d.materials) || []).map((m) => (typeof m === "string" ? m : m.name)).filter(Boolean);
    const steps = (item.steps || []).map((s) => (typeof s === "string" ? s : s.what)).filter(Boolean);
    const quotes = ((state.last && state.last.quotes) || []).slice(0, 4);
    el.printsheet.innerHTML = `<h1>${esc(item.title)}</h1>
      <p class="pmeta">${esc([item.dept, item.location, item.fee].filter(Boolean).join(" / "))}</p>
      <h2>要带的材料</h2>
      <ul>${mats.length ? mats.map((m) => `<li>□ ${esc(m)}</li>`).join("") : "<li>官方页面没有列出材料清单</li>"}</ul>
      <h2>办理步骤</h2>
      <ol>${steps.length ? steps.map((s) => `<li>${esc(s)}</li>`).join("") : "<li>官方页面没有给出步骤</li>"}</ol>
      <h2>原文依据</h2>
      ${quotes.length ? quotes.map((q) => `<p>${esc(q.quote)}</p><p class="psrc">${esc([q.label || q.src, q.date, q.url].filter(Boolean).join(" / "))}</p>`).join("") : "<p>本次回答未引用原文段落。</p>"}
      <p class="psrc">打印时间 ${new Date().toLocaleString("zh-CN")}。事实以官方原文为准。</p>`;
    window.print();
  }

  /* ---------------- 抽屉 ---------------- */
  function openOverlay(kind) {
    if (kind === "drawer") state.drawerOpen = true;
    if (kind === "sheet") state.sheetOpen = true;
    el.inspector.dataset.open = String(state.sheetOpen);
    el.drawer.dataset.open = String(state.drawerOpen);
    el.drawer.hidden = !state.drawerOpen;
    el.scrim.hidden = !(state.drawerOpen || state.sheetOpen);
    requestAnimationFrame(() => { el.scrim.dataset.open = "true"; });
  }

  function closeOverlays(which) {
    if (!which || which === "drawer") state.drawerOpen = false;
    if (!which || which === "sheet") state.sheetOpen = false;
    el.inspector.dataset.open = String(state.sheetOpen);
    el.drawer.dataset.open = String(state.drawerOpen);
    const any = state.drawerOpen || state.sheetOpen;
    el.scrim.dataset.open = "false";
    if (!any) setTimeout(() => {
      if (!state.drawerOpen && !state.sheetOpen) {
        el.scrim.hidden = true;
        el.drawer.hidden = true;
      }
    }, 320);
  }

  async function openContacts(purpose) {
    state.contactsPurpose = purpose || "";
    el.drawertitle.textContent = "联系方式";
    el.drawerbody.innerHTML = `<div class="searchform"><input id="ctsearch" type="search" placeholder="按部门、号码或用途搜" value="${esc(state.contactsQ)}"></div>
      <div class="ctctrl"><select id="ctpurpose" aria-label="按用途筛选"><option value="">全部用途</option></select></div>
      <p class="ctcount" id="ctcount">正在读取公开联系方式…</p>
      <div id="ctlist"></div>`;
    openOverlay("drawer");
    try {
      const d = await api("/api/contacts");
      state.contacts = d;
      const sel = $("#ctpurpose");
      (d.purposes || []).forEach((p) => {
        const o = document.createElement("option");
        o.value = p; o.textContent = p;
        sel.appendChild(o);
      });
      sel.value = state.contactsPurpose || "";
      sel.onchange = () => { state.contactsPurpose = sel.value; renderContacts(); };
      const search = $("#ctsearch");
      search.oninput = () => { state.contactsQ = search.value.trim(); renderContacts(); };
      renderContacts();
    } catch (e) {
      $("#ctcount").textContent = "联系方式没读出来：" + e.message;
    }
  }

  function renderContacts() {
    const d = state.contacts;
    if (!d) return;
    const q = state.contactsQ;
    const items = (d.items || []).filter((i) => {
      if (state.contactsPurpose && i.purpose !== state.contactsPurpose) return false;
      if (!q) return true;
      return (i.value + i.dept + i.context + i.purpose).includes(q);
    });
    $("#ctcount").textContent = `${items.length} 条公开联系方式` + (state.contactsPurpose ? ` / ${state.contactsPurpose}` : "");
    const kindLabel = { phone: "电话", email: "邮箱", wechat: "公众号", web: "网址", url: "网址", link: "网址" };
    $("#ctlist").innerHTML = items.length ? items.map((i) => {
      const val = i.value || "";
      const href = i.kind === "phone" ? `tel:${val.replace(/\s/g, "")}`
        : i.kind === "email" ? `mailto:${val}`
        : /^https?:/.test(val) ? val : "";
      return `<div class="ctrow">
        <div class="cttop"><span class="ctkind">${esc(kindLabel[i.kind] || i.kind || "联系")}</span>
          <span class="ctval">${href ? `<a href="${esc(href)}" style="border:0;color:inherit">${esc(val)}</a>` : esc(val)}</span></div>
        <div class="ctdept">${esc(/^[0-9a-f]{8,}$/i.test(i.dept || "") ? "来源未标注部门" : (i.dept || ""))}${i.purpose ? ` / ${esc(i.purpose)}` : ""}</div>
        ${i.context ? `<p class="ctctx">${esc(i.context)}</p>` : ""}
        <div class="ctacts"><button type="button" data-copy="${esc(val)}">复制</button>
          ${i.source_url ? `<a href="${esc(i.source_url)}" target="_blank" rel="noreferrer">来源原文 ↗</a>` : ""}</div>
      </div>`;
    }).join("") : `<p class="insempty2">这个筛选下没有收录到公开联系方式。换个用途，或直接问我。</p>`;
  }

  async function openSearch(q) {
    q = (q || "").trim();
    el.drawertitle.textContent = "原文检索";
    el.drawerbody.innerHTML = `<form class="searchform" id="sform">
        <input id="sq" type="search" placeholder="输入一句话，直接去原文库找段落" value="${esc(q)}">
        <button type="submit">检索</button>
      </form>
      <p class="searchmeta" id="smeta">只返回原文与出处，不生成答案。</p>
      <div id="slist"></div>`;
    openOverlay("drawer");
    const form = $("#sform");
    form.onsubmit = (e) => { e.preventDefault(); runSearch($("#sq").value.trim()); };
    $("#sq").focus();
    if (q) runSearch(q);
  }

  async function runSearch(q) {
    if (q.length < 2) { toast("请再说得具体一点"); return; }
    $("#smeta").textContent = "在官方原文里检索…";
    $("#slist").innerHTML = "";
    try {
      const d = await api(`/api/search?q=${encodeURIComponent(q)}&k=8`);
      const hits = d.hits || [];
      $("#smeta").textContent = `「${q}」命中 ${hits.length} 段 / 库内 ${num(d.vector_sources)} 份、${num(d.vector_chunks)} 段原文`;
      $("#slist").innerHTML = hits.length ? hits.map((h) => `
        <div class="shit">
          <h3>${esc(h.title || "原文段落")}</h3>
          <div class="sm"><span>${esc(h.kind || "原文")}</span><span>相关度 ${pct(h.score)}</span>${h.page ? `<span>p.${esc(h.page)}</span>` : ""}</div>
          <p>${esc(h.snippet || "")}</p>
          ${h.url ? `<a class="lnk" href="${esc(h.url)}" target="_blank" rel="noreferrer">打开原文 ↗</a>` : ""}
        </div>`).join("") : `<p class="insempty2">原文库里没有相近段落。换个说法，或者回到对话直接问事项。</p>`;
    } catch (e) {
      $("#smeta").textContent = "检索失败：" + e.message;
    }
  }

  /* ---------------- 高德地图抽屉 ---------------- */
  const CAMPUS_CENTER = [39.9131, 116.5555];
  const map = { last: null, leaflet: null, marker: null };

  function amapSearch(query) {
    return `https://www.amap.com/search?query=${encodeURIComponent(query || "中国传媒大学")}&city=北京`;
  }

  function coordsOf(place) {
    const m = /position=([\d.]+),([\d.]+)/.exec((place && place.marker) || "");
    return m ? [parseFloat(m[2]), parseFloat(m[1])] : null;
  }

  function ensureMap() {
    if (map.leaflet) return map.leaflet;
    const m = L.map(el.mapcanvas, { zoomControl: true, attributionControl: true })
      .setView(CAMPUS_CENTER, 16);
    L.tileLayer("https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}", {
      subdomains: "1234", maxZoom: 19, attribution: "底图 © 高德地图",
    }).addTo(m);
    map.leaflet = m;
    return m;
  }

  function popupFor(place) {
    const box = document.createElement("div");
    box.className = "mappop";
    const b = document.createElement("b");
    b.textContent = place.name || place.label || place.query;
    box.append(b);
    const line = place.line || place.label;
    if (line && line !== place.name) {
      const p = document.createElement("p");
      p.textContent = line;
      box.append(p);
    }
    return box;
  }

  function drawMarker(place) {
    if (typeof L === "undefined") return;
    const m = ensureMap();
    m.invalidateSize();
    const c = coordsOf(place);
    if (map.marker) { map.marker.remove(); map.marker = null; }
    if (!c) { m.setView(CAMPUS_CENTER, 16); return; }
    m.setView(c, 17);
    map.marker = L.marker(c).addTo(m).bindPopup(popupFor(place), { closeButton: false, autoPan: false });
    map.marker.openPopup();
  }

  function showMap(place) {
    if (!place || !place.query) return;
    map.last = place;
    el.maptarget.textContent = place.label || place.name || place.query;
    const url = place.url || amapSearch(place.query);
    el.mapopen.href = url;
    el.mapopen.textContent = `在高德搜「${place.query}」↗`;
    const where = place.line || place.place;
    const exact = !!coordsOf(place);
    el.mapfoot.textContent = [
      where ? `官方位置：${where.replace(/。$/, "")}。` : "",
      exact
        ? `地图底图是高德，标记落在「${place.query}」。`
        : `这条没有精确坐标，地图只到校园范围；到「${place.query}」的搜索结果里看具体门牌。`,
    ].join("");
    el.map.dataset.open = "true";
    el.map.setAttribute("aria-hidden", "false");
    requestAnimationFrame(() => drawMarker(place));
    setTimeout(() => { if (el.map.dataset.open === "true") drawMarker(place); }, 320);
  }

  function hideMap() {
    if (el.map.dataset.open !== "true") return;
    if (el.map.contains(document.activeElement)) document.activeElement.blur();
    el.map.dataset.open = "false";
    el.map.setAttribute("aria-hidden", "true");
  }

  function bindMapDrawer() {
    el.mapclose.addEventListener("click", hideMap);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && el.map.dataset.open === "true") hideMap();
    });
  }

  /* ---------------- 事件 ---------------- */
  function bind() {
    bindPresets();
    el.composer.addEventListener("submit", (e) => {
      e.preventDefault();
      ask(el.q.value);
    });
    el.q.addEventListener("keydown", (e) => {
      if ((e.key === "Enter" && !e.shiftKey) || (e.key === "Enter" && (e.metaKey || e.ctrlKey))) {
        e.preventDefault();
        ask(el.q.value);
      }
    });
    el.q.addEventListener("input", () => {
      el.q.style.height = "auto";
      el.q.style.height = Math.min(el.q.scrollHeight, 150) + "px";
    });
    $("#clearbtn").addEventListener("click", () => {
      state.slots = {};
      el.q.value = "";
      el.q.style.height = "auto";
      el.q.focus();
      toast("条件已清空，可以重新问");
    });
    el.llm.addEventListener("change", () => {
      if (state.lastQuery) ask(state.lastQuery, { keepSlots: true });
    });

    el.thread.addEventListener("click", async (e) => {
      const t = e.target.closest("[data-ask],[data-key],[data-retry],[data-act]");
      if (!t) return;
      if (t.dataset.ask) { e.preventDefault(); el.q.value = t.dataset.ask; ask(t.dataset.ask); return; }
      if (t.dataset.retry) { el.q.value = t.dataset.retry; ask(t.dataset.retry); return; }
      if (t.dataset.key) {
        state.slots[t.dataset.key] = t.dataset.opt;
        const fu = t.closest(".fu");
        const orig = (fu && fu.dataset.orig) || state.lastQuery;
        el.q.value = orig;
        ask(orig, { keepSlots: true });
        return;
      }
      if (t.dataset.act) {
        const exEl = t.closest(".ex");
        const d = (exEl && exEl.__data) || state.last;
        if (!d) return;
        if (t.dataset.act === "ev") {
          openTab("quotes");
          if (isMobile()) openOverlay("sheet");
        } else if (t.dataset.act === "mat") {
          openTab("material");
          if (isMobile()) openOverlay("sheet");
        } else if (t.dataset.act === "copy") {
          copyAnswer(d);
        } else if (t.dataset.act === "loc") {
          if (d.map) showMap(d.map);
          else if (map.last) showMap(map.last);
          else toast("这条没写具体位置");
        }
      }
    });

    document.addEventListener("click", (e) => {
      const askBtn = e.target.closest("[data-ask]");
      if (askBtn && !el.thread.contains(askBtn)) {
        e.preventDefault();
        el.q.value = askBtn.dataset.ask;
        ask(askBtn.dataset.ask);
        if (state.drawerOpen) closeOverlays("drawer");
        return;
      }
      const llmFix = e.target.closest("[data-llmfix]");
      if (llmFix) {
        el.llm.checked = true;
        if (state.lastQuery) ask(state.lastQuery, { keepSlots: true });
        return;
      }
      const copyBtn = e.target.closest("[data-copy]");
      if (copyBtn) {
        copyText(copyBtn.dataset.copy, "已复制");
        return;
      }
      const searchGo = e.target.closest("[data-searching]");
      if (searchGo) {
        const q = searchGo.dataset.searching || "";
        openSearch(q);
        if (q) setTimeout(() => runSearch(q), 60);
        return;
      }
      const contactsGo = e.target.closest("[data-contacts]");
      if (contactsGo) { openContacts(); return; }
      const matCopy = e.target.closest('[data-act="matcopy"]');
      if (matCopy) {
        const item = state.item;
        if (!item) return;
        const mats = ((state.deliver || item).materials || []).map((m) => (typeof m === "string" ? m : m.name));
        copyText(`${item.title}\n${mats.map((m) => "□ " + m).join("\n")}`, "材料清单已复制");
        return;
      }
      const draftCopy = e.target.closest('[data-act="draftcopy"]');
      if (draftCopy) {
        const draft = state.deliver && state.deliver.draft;
        if (draft) copyText(draft.text, "草稿已复制");
        return;
      }
    });

    el.insbody.addEventListener("click", (e) => {
      const li = e.target.closest("[data-mat]");
      if (!li || !state.item) return;
      const key = state.item.id + ":" + li.dataset.mat;
      if (state.checked.has(key)) state.checked.delete(key); else state.checked.add(key);
      li.setAttribute("aria-checked", String(state.checked.has(key)));
      const mats = ((state.deliver || state.item).materials || []);
      const bar = $(".matbar b");
      if (bar) bar.textContent = `${mats.filter((_, i) => state.checked.has(state.item.id + ":" + i)).length}/${mats.length}`;
    });
    el.insbody.addEventListener("keydown", (e) => {
      if ((e.key === " " || e.key === "Enter") && e.target.matches("[data-mat]")) {
        e.preventDefault();
        e.target.click();
      }
    });

    el.tabs.addEventListener("click", (e) => {
      const b = e.target.closest("[data-tab]");
      if (b) openTab(b.dataset.tab);
    });

    $("#insclose").addEventListener("click", () => closeOverlays("sheet"));
    $("#ctbtn").addEventListener("click", () => openContacts());
    $("#searchbtn").addEventListener("click", () => openSearch(el.q.value.trim()));
    $("#drawerclose").addEventListener("click", () => closeOverlays("drawer"));
    el.scrim.addEventListener("click", () => closeOverlays());
    $("#printbtn").addEventListener("click", printSheet);
    $("#copyallbtn").addEventListener("click", () => {
      const text = checklistText();
      if (!text) { toast("先问一件事，再复制清单"); return; }
      copyText(text, "清单已复制，可直接粘贴进备忘录");
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (state.drawerOpen || state.sheetOpen) closeOverlays();
      }
    });

    const sheetbar = $("#sheetbar");
    let sy = null;
    sheetbar.addEventListener("pointerdown", (e) => {
      sy = e.clientY;
      sheetbar.setPointerCapture(e.pointerId);
    });
    sheetbar.addEventListener("pointermove", (e) => {
      if (sy == null) return;
      const dy = e.clientY - sy;
      if (dy > 70) { sy = null; closeOverlays("sheet"); }
    });
    sheetbar.addEventListener("pointerup", () => { sy = null; });

    window.addEventListener("resize", () => {
      if (!isMobile() && state.sheetOpen) closeOverlays("sheet");
    });

    bindMapDrawer();
  }

  function copyAnswer(d) {
    const item = d.item || {};
    if (d.plan) {
      const parts = (d.answers || []).map((p) => `【${p.label}】\n${(p.lines || [p.text]).filter(Boolean).join("\n")}`);
      copyText([`转专业：${d.normalized}`, ...parts, d.note, d.plan_file ? `接收计划 PDF：${location.origin}${d.plan_file}` : ""]
        .filter(Boolean).join("\n\n"), "答案已复制");
      return;
    }
    const parts = (d.answers || []).map((a) => {
      const steps = (a.steps || []).map((s, i) => {
        if (typeof s === "string") return s;
        const note = stepNote(s, i);
        return s.what + (note ? `（${note}）` : "");
      });
      return `【${a.label}】${a.text || steps.join("；")}`;
    });
    const quotes = (d.quotes || []).slice(0, 5).map((q) => `- ${q.quote}（${[q.label, q.date].filter(Boolean).join(" / ")}${q.url ? " " + q.url : ""}）`);
    const src = (item.source || []).map((s) => s.url).filter(Boolean);
    copyText([
      `问\n${d.query}`,
      `理解成\n${d.normalized}`,
      ...parts,
      d.note ? `说明\n${d.note}` : "",
      quotes.length ? `原文\n${quotes.join("\n")}` : "",
      src.length ? `来源\n${src.join("\n")}` : "",
      "由校园办事向导整理，事实以官方原文为准。",
    ].filter(Boolean).join("\n\n"), "答案已复制");
  }

  boot();
})();
