/* ============================================================
   广院通 / web-next/field.js —— 钴蓝场前端（并行入口 /field）
   依赖只有仓库内的本地 Leaflet（vendor/leaflet），不引 CDN、不加框架。
   所有事实来自 /api/health、/api/campus、/api/ask、/api/deliver、
   /api/search、/api/contacts，界面只做呈现与组织，不生成内容。
   与 app.js 之间的少量重复是有意的：主链路已经验收，不为 DRY 去重构它。
   ============================================================ */
(function () {
  "use strict";

  /* ---------- 字幕词表与节奏：改词只动这一个数组 ---------- */
  const FIELD_WORDS = [
    "CUC", "CARD REISSUE", "ONE ASK", "CUC", "LOCATION",
    "CARD KIOSK", "CUC", "ONE VISIT", "WECHAT PAY", "VERIFIED",
  ];
  const REEL_SECONDS_PER_ROW = 2.5;
  const REEL_DWELL = 0.64;          // 每格里的停留比例，剩余时间用于换行
  const PRESETS = [
    "48教在哪", "校医院在哪", "校卡怎么补办", "转专业",
    "出国用的成绩单怎么开", "奖学金", "保研", "宿舍购电",
  ];

  function reelRows() {
    // 末行复制首行，循环回到开头时不会有空帧
    return FIELD_WORDS.concat(FIELD_WORDS[0]);
  }

  function reelKeyframes(rows) {
    const slots = rows.length - 1;
    const step = 100 / slots;
    const lines = [];
    for (let index = 0; index < slots; index += 1) {
      const start = index * step;
      const hold = start + step * REEL_DWELL;
      lines.push(`  ${start.toFixed(2)}%, ${hold.toFixed(2)}% { transform: translateY(-${(index * 100 / rows.length).toFixed(2)}%) }`);
    }
    lines.push(`  100% { transform: translateY(-${(slots * 100 / rows.length).toFixed(2)}%) }`);
    return "@keyframes field-reel {\n" + lines.join("\n") + "\n}";
  }

  function installReel() {
    const rows = reelRows();
    const strip = document.getElementById("rotate");
    if (!strip) return;
    strip.innerHTML = '<div class="rotate-inner">' + rows.map((word) => `<span>${word}</span>`).join("") + "</div>";
    const style = document.createElement("style");
    style.id = "field-reel-keys";
    style.textContent = reelKeyframes(rows)
      + `\n:root { --reel-duration: ${(FIELD_WORDS.length * REEL_SECONDS_PER_ROW).toFixed(2)}s }`;
    document.head.appendChild(style);
  }

  /* ---------- 基础工具 ---------- */
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  const esc = (value) => String(value == null ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  // 反问菜单的选项带条目 id：点下去按 id 打开那一条，别再拿标题重新路由一遍
  const pickAttr = (choice) => (choice && choice.id
    ? ` data-pick="${esc(choice.id)}"` : "");
  const num = (value) => Number(value || 0).toLocaleString("zh-CN");
  const pct = (value) => Math.round((Number(value) || 0) * 100) + "%";

  /* 原文检索走语义近似，输入的整句常常在原文里一个字都不重样（实测八句整串命中为零）。
     所以标的不是整句，而是「你打的这串字里真正落在那段原文上的那几个字」：
     疑问词先摘掉，剩下的按最长公共片段逐段找，找到的词把每一处都标出来。 */
  const MARK_STOP = ["什么时候", "多少时间", "多长时间", "需不需要", "有没有", "是不是", "可不可以",
                     "能不能", "为什么", "怎么样", "怎样", "如何", "哪里", "哪儿", "哪些", "什么",
                     "怎么", "多少", "几个", "请问", "需要", "要", "吗", "呢", "的", "了", "啊", "是"];

  function markHits(text, query) {
    const s = String(text == null ? "" : text);
    const low = s.toLowerCase();
    let cleaned = String(query == null ? "" : query).toLowerCase();
    for (const word of MARK_STOP) cleaned = cleaned.split(word).join("");
    const terms = [];
    const one = (ch) => {
      // 单字退让只对汉字开：一个拉丁字母能在满屏里到处撞上车
      if (!/[\u4e00-\u9fff]/.test(ch) || low.indexOf(ch) < 0) return;
      if (!terms.includes(ch)) terms.push(ch);
    };
    const dig = (seg) => {
      // 纯拉丁词最短要到三个字母，否则 "excel" 会退化成满屏的 "el"；两字母缩写（ps）本身就该整词认
      const floor = /^[a-z0-9]+$/.test(seg) && seg.length > 2 ? 3 : 2;
      for (let size = seg.length; size >= floor; size--) {
        for (let at = 0; at + size <= seg.length; at++) {
          const piece = seg.slice(at, at + size);
          if (!/[a-z0-9\u4e00-\u9fff]/.test(piece) || low.indexOf(piece) < 0) continue;
          if (!terms.includes(piece)) terms.push(piece);
          dig(seg.slice(0, at));
          dig(seg.slice(at + size));
          return;
        }
      }
      // 这一段连两个字都凑不上，退一步把单个字标出来
      if (seg.length >= 2) Array.from(seg).forEach(one); else one(seg);
    };
    cleaned.split(/\s+/).forEach(dig);
    const marks = [];
    terms.sort((a, b) => b.length - a.length).forEach((term) => {
      // 拉丁词卡词界：ps 不许从 wps 里被认出来（和条目定位器同一口径）
      const tight = /^[a-z0-9]+$/.test(term);
      let at = -1;
      while ((at = low.indexOf(term, at + 1)) >= 0) {
        const end = at + term.length;
        if (tight && (/[a-z0-9]/.test(low.charAt(at - 1)) || /[a-z0-9]/.test(low.charAt(end)))) continue;
        if (!marks.some(([m, n]) => at < n && m < end)) marks.push([at, end]);
        at = end - 1;
      }
    });
    if (!marks.length) return esc(s);
    let html = "", cut = 0;
    marks.sort((a, b) => a[0] - b[0]).forEach(([from, to]) => {
      html += esc(s.slice(cut, from)) + '<mark class="hit">' + esc(s.slice(from, to)) + "</mark>";
      cut = to;
    });
    return html + esc(s.slice(cut));
  }
  // 「· 图书馆手册.docx」这种来源后缀是给条目自己用的，不该出现在给用户看的话里。
  // 只处理显示：data-ask 仍然原样发出去，免得动到路由。
  const docName = (value) => String(value == null ? "" : value)
    .replace(/\.(docx|xlsx|pptx|pdf|doc|xls|ppt|txt|md|wps)\b/gi, "");
  const statusText = (item) => !item ? ""
    : item.status === "verified" ? "原文已核验"
    : item.status === "partial" ? "官方无正文"
    : "待核验";

  const PLACE_SKIP = new Set(["快递", "大集", "教务", "国重", "活动中心"]);
  const PLACE_TWO = new Set(["主楼", "南门", "北门", "西门", "1教", "一教", "艺传", "南操", "大活", "北苑"]);
  let PLACE_RE = null;

  function buildPlaces(pois) {
    const seen = new Set();
    const names = [];
    for (const p of pois || []) {
      for (const raw of [p.name].concat(p.aliases || [])) {
        const value = String(raw || "").trim();
        if (value.length < 2 || /^\d+$/.test(value) || PLACE_SKIP.has(value)) continue;
        if (value.length === 2 && !PLACE_TWO.has(value)) continue;
        if (seen.has(value)) continue;
        seen.add(value);
        names.push(value);
      }
    }
    names.sort((a, b) => b.length - a.length);
    if (!names.length) { PLACE_RE = null; return; }
    const body = names.map((value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
    PLACE_RE = new RegExp(`(?<!第)(?:${body})`, "g");
  }

  // 只对已转义的纯文本调用，不会碰标签属性
  function linkify(html) {
    if (!PLACE_RE || !html) return html;
    PLACE_RE.lastIndex = 0;
    return html.replace(PLACE_RE, (match) =>
      `<a class="plink" href="#" data-ask="${esc(match + "在哪")}" title="问：${esc(match)}在哪">${match}</a>`);
  }

  // 原文里常直接写网址（正版软件平台、办事系统入口、报到页面），得点开。
  // 先按 URL 把原文切开：网址段自己转义成链接，其余段照旧走 esc＋地点词，
  // 这样不会出现 a 套 a。中文句号、顿号、全角括号不能算进网址。
  const URL_RE = /https?:\/\/[^\s，。；、！？〈《》「」『』【】（）"'<>]+|www\.[^\s，。；、！？〈《》「」『』【】（）"'<>]+/g;
  function richText(value) {
    const raw = String(value == null ? "" : value);
    if (!raw) return "";
    const out = [];
    let cut = 0;
    let m;
    URL_RE.lastIndex = 0;
    while ((m = URL_RE.exec(raw))) {
      if (m.index > cut) out.push(linkify(esc(raw.slice(cut, m.index))));
      const url = m[0];
      const href = /^www\./i.test(url) ? `https://${url}` : url;
      out.push(`<a class="ulink" href="${esc(href)}" target="_blank" rel="noreferrer">${esc(url)}</a>`);
      cut = m.index + url.length;
    }
    if (cut < raw.length) out.push(linkify(esc(raw.slice(cut))));
    return out.join("");
  }

  const stepNote = (step, index) => {
    if (typeof step === "string") return "";
    return step.where || (step.when && step.when !== `第 ${index + 1} 步` ? step.when : "");
  };

  const state = {
    item: null,
    last: null,
    deliver: null,
    slots: {},
    checked: new Set(),
    history: [],
    tab: "overview",
    busy: false,
    count: 0,
    pushed: false,
    campus: null,
    contacts: null,
    contactPurpose: "",
    searchQuery: "",
    searchHits: null,
    searchTotal: 0,
    mapQuery: "",
    mapPick: null,
    mapPlace: null,
  };

  const el = {
    body: document.body,
    statline: $("#statline"),
    topline: $("#topline"),
    back: $("#backbtn"),
    thread: $("#thread"),
    composer: $("#composer"),
    q: $("#q"),
    send: $("#send"),
    presets: $("#presets"),
    llm: $("#llmsw"),
    llmwrap: $("#llmwrap"),
    llmrisk: $("#llmrisk"),
    clear: $("#clearbtn"),
    inspector: $("#inspector"),
    title: $("#institle"),
    sub: $("#insub"),
    tabs: $("#tabs"),
    body2: $("#insbody"),
    qcount: $("#qcount"),
    stamp: $("#stamp"),
    copy: $("#copybtn"),
    print: $("#printbtn"),
    toast: $("#toast"),
    panel: $("#panel"),
    pantitle: $("#pantitle"),
    panelbody: $("#panelbody"),
    panclose: $("#panclose"),
    scrim: $("#scrim"),
    bar: $(".topbar"),
  };

  let toastTimer = 0;
  function toast(message) {
    el.toast.textContent = message;
    el.toast.dataset.show = "true";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.toast.dataset.show = "false"; }, 2500);
  }

  async function api(path, body) {
    let res;
    try {
      res = await fetch(path, body
        ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
        : {});
    } catch (error) {
      throw new Error("连不上本地服务，请确认 app.py 已在当前端口运行");
    }
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      // 后端两种形状都要读：HTTPException 走 {"error": ...}，业务错误走 detail / message
      const text = data && (data.error || data.detail || data.message);
      throw new Error(text || `请求失败（${res.status}）`);
    }
    return data;
  }

  async function copyText(text, okMessage) {
    try {
      await navigator.clipboard.writeText(text);
      toast(okMessage || "已复制");
      return true;
    } catch (error) {
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      let done = false;
      try { done = document.execCommand("copy"); } catch (inner) { done = false; }
      area.remove();
      toast(done ? (okMessage || "已复制") : "复制失败，请手动选择文字");
      return done;
    }
  }

  function setMode(mode) {
    const prev = el.body.dataset.mode;
    el.body.dataset.mode = mode;
    // 只在「满屏 → 工作区」这一次压一条历史，返回键因此能回到刚进 /field 的样子；
    // 后续反复提问不再堆栈，否则要按很多次返回才出得去。
    if (mode === "work" && prev !== "work" && !state.pushed) {
      state.pushed = true;
      history.pushState({ field: "work" }, "", window.location.pathname + window.location.search);
    }
  }

  // 「返回」与「重新问」共用这一套复位：清掉问答痕迹，只留满屏场域态。
  function resetToHero() {
    closePanel();
    state.item = null;
    state.last = null;
    state.deliver = null;
    state.pushed = false;
    state.slots = {};
    state.history = [];
    state.count = 0;
    el.thread.innerHTML = "";
    el.topline.hidden = true;
    setMode("hero");
    renderIns();
    updateStamp();
    el.q.focus({ preventScroll: true });
  }

  /* ============================================================
     结果呈现。分支顺序与经典版 renderAnswer 一致：
     计划 → 未命中 → 多义澄清 → 先确认/追问 → 普通答案。
     ============================================================ */
  function renderResult(data) {
    if (data.plan) return planCard(data);
    if (!data.matched) return missCard(data);
    if (Array.isArray(data.disambiguate) && data.disambiguate.length && data.clarify) return clarifyCard(data);
    if (data.hold || (data.followups || []).length) return holdCard(data);
    return answerCard(data);
  }

  function modelStat(data) {
    // 模型这一层到底有没有参与：没问、问了、报错，用户要能一眼分开看
    const m = data.model_route;
    if (!m) return "";
    const bits = [];
    let bad = false;
    if (m.error) {
      const err = String(m.error);
      if (err.includes("限流")) bits.push("模型接口被限流，这条只按规则答");
      else if (err.includes("连不通")) bits.push("模型接口连不通，这条只按规则答");
      else if (err.includes("Key")) bits.push("模型 Key 可能失效，这条只按规则答");
      else bits.push("模型接口失败，这条只按规则答");
      bad = true;
    }
    else if (m.gate === "no_key") { bits.push("没配模型 Key，这条只按规则答"); bad = true; }
    else if (m.gate === "router_off") { bits.push("模型裁决没开，这条只按规则答"); bad = true; }
    else if (m.gate === "user_pick") { bits.push("按你点的那一条答"); }
    else if (m.gate === "menu_default") { bits.push("这个词先答主项，其余问法在下面"); }
    else if (m.gate === "menu_declined") {
      bits.push(`模型看过 ${m.pool} 个选项，认不出你要哪一件，先列给你挑`);
    }
    else if (m.gate === "menu_low") {
      bits.push(`模型对选项最高只有 ${m.score}% 把握，还是列给你挑`); bad = true;
    }
    else if (m.rescue === "menu_pick") {
      bits.push("模型从选项里选定这一条");
      if (data.soft_match) { bits.push(`只有 ${m.score}% 把握`); bad = true; }
    }
    else if (m.rescue === "rewrite_pool") {
      bits.push("模型换了说法重新检索后指定");
      if (data.soft_match) { bits.push(`只有 ${m.score}% 把握`); bad = true; }
    }
    else if (m.rescue === "keyword_fallback") {
      bits.push("模型接口不可用，这条按改写关键词命中"); bad = true;
    }
    else if (m.gate === "llm_declined") {
      bits.push(m.pool2
        ? `模型换过 ${m.rewrites ? m.rewrites.length : 0} 种说法重新检索，也没认出来`
        : `模型看过 ${m.pool} 条候选，认为都没答上`);
    }
    else {
      if (data.soft_match) { bits.push(`模型只有 ${m.score}% 把握`); bad = true; }
      if (m.changed) bits.push("模型改判");
      if (data.focus_by_llm) bits.push("问的是哪一面由模型判断");
    }
    if (!bits.length) return "";
    const why = m.why || m.error || "";
    return `<span class="mstat${bad ? " bad" : ""}"${why ? ` title="${esc(why)}"` : ""}>${esc(bits.join(" · "))}</span>`;
  }

  function cardHead(data, title) {
    const item = data.item || {};
    const verified = item.status === "verified";
    return `<div class="cardhead">
      <span class="tag${verified ? "" : " warn"}">${esc(statusText(item) || "未匹配到事项")}</span>
      ${modelStat(data)}
      <span class="norm" title="${esc(data.normalized || "")}">理解成 ${esc(docName(data.normalized || data.query || ""))}</span>
      <span class="conf" title="系统和这句话的匹配程度">${pct(data.confidence)}</span>
      ${title ? `<h2>${esc(docName(title))}</h2>` : ""}
    </div>`;
  }

  function planCard(data) {
    const plan = data.plan || {};
    const focus = plan.focus || {};
    // 与经典版 planCard 同源：先展开 answers 各面，再列计划覆盖的专业，最后给 PDF 原文与备注。
    const parts = (data.answers || []).map(partHtml).join("");
    const majors = (plan.majors || []).slice(0, 10).map((row) => {
      const name = typeof row === "string" ? row : (row.name || row.major || "");
      if (!name) return "";
      return `<button class="opt" type="button" data-ask="${esc(`转专业到${plan.college_label || plan.college || ""}${name}`)}">${esc(name)}</button>`;
    }).join("");
    const scope = [];
    if (focus.major) scope.push(`按 ${focus.major} 单列`);
    else if (plan.college_label) scope.push(`按 ${plan.college_label} 整体列出`);
    return `<div class="card">${cardHead(data, plan.college ? `${plan.college} 接收计划` : "转专业接收计划")}
      ${scope.length ? `<p class="aval">${esc(scope.join("；"))}，以下按接收计划原表逐条保留</p>` : ""}
      ${parts || '<p class="aval none">这份接收计划没有可展开的条目</p>'}
      ${majors ? `<div class="sec"><h3>这份计划覆盖的专业</h3><div class="opts">${majors}</div></div>` : ""}
      ${data.plan_file ? `<div class="opts"><a class="opt" href="${esc(data.plan_file)}" target="_blank" rel="noreferrer">打开学院接收计划 PDF ↗</a></div>` : ""}
      ${noteBlock(data)}${relatedBlock(data.related)}
      <div class="cardfoot">
        <button class="plainbtn" type="button" data-act="quotes">核对原文 <span>${(data.quotes || []).length}</span></button>
        <button class="plainbtn" type="button" data-act="copy">复制答案</button>
        <span class="stampnote">${data.plan_no_file ? "学院未公开 PDF · " : ""}NO.${String(state.count).padStart(3, "0")} · 转专业接收计划</span>
      </div></div>`;
  }

  function missCard(data) {
    // 与经典版 notFoundCard 同源：开场句 + 模型生成（若有）+ 原文线索 + 候选事项 + 归口线索 + 公开联系方式 + 下一步
    const lead = `${data.topic ? `你问的是 ${esc(data.topic)}，` : ""}${esc(data.search_note
      || "下面是我从原文里找到的线索。你可以换个更具体的说法再问。")}`;
    const gen = data.llm_answer ? `<div class="genbox">
      <div class="alab">模型生成 · 没有官方条目，这段回答由模型直接生成</div>
      <p class="aval">${richText(data.llm_answer.text || "")}</p>
      <p class="qmore">${esc(data.llm_answer.disclaimer || "这段内容由模型生成，可能不准确")}${data.llm_answer.caveat ? ` ${esc(data.llm_answer.caveat)}` : ""}</p>
    </div>` : "";
    const clues = (data.original_search || []).map((h) => `<div class="hitrow">
      <div class="ht">${esc(docName(h.title) || "原文段落")}</div>
      <p class="norm">${[h.kind || "原文", h.score != null ? `相关度 ${pct(h.score)}` : "", h.page ? `p.${esc(h.page)}` : ""].filter(Boolean).join(" · ")}</p>
      <p class="aval">${esc(h.snippet || "")}</p>
      ${h.url ? `<a class="opt" href="${esc(h.url)}" target="_blank" rel="noreferrer">打开原文 ↗</a>` : ""}
    </div>`).join("");
    const choices = (data.disambiguate || []).map((b) =>
      `<button class="opt" type="button" data-ask="${esc(b.title)}"${pickAttr(b)}>${esc(docName(b.title))}${b.dept ? `<span class="odept">${esc(b.dept)}</span>` : ""}</button>`).join("");
    const related = (data.related_items || []).map((a) =>
      `<button class="opt" type="button" data-ask="${esc(a.title)}">${esc(docName(a.label || a.title))}</button>`).join("");
    const alts = (data.alternatives || []).map((a) =>
      `<button class="opt" type="button" data-ask="${esc(a.title)}">${esc(docName(a.title))}</button>`).join("");
    const hints = (data.hints || []).map((h) => `<div class="hitrow">
      <div class="ht"><b>${esc(h.name)}</b> 可能管这件事${h.basis ? `<span class="norm">依据 ${esc(h.basis)}</span>` : ""}</div>
      ${(h.matched || []).length ? `<p class="norm">${(h.matched || []).map((m) => esc(m)).join(" · ")}</p>` : ""}
      ${h.url ? `<a class="opt" href="${esc(h.url)}" target="_blank" rel="noreferrer">打开部门网站 ↗</a>` : ""}
    </div>`).join("");
    const kindLabel = { phone: "电话", email: "邮箱", wechat: "公众号", web: "网址", url: "网址", link: "网址" };
    const contacts = (data.contacts || []).map((c) => {
      const value = c.value || "";
      const href = c.kind === "phone" ? `tel:${value.replace(/\s/g, "")}`
        : c.kind === "email" ? `mailto:${value}` : "";
      return `<div class="hitrow">
        <div class="ht"><span class="norm">${esc(kindLabel[c.kind] || c.kind || "联系")}</span>${href
          ? `<a class="opt" href="${esc(href)}">${esc(value)}</a>` : esc(value)}</div>
        <p class="norm">${esc([c.dept, c.purpose].filter(Boolean).join(" / "))}</p>
        ${c.source_url ? `<a class="opt" href="${esc(c.source_url)}" target="_blank" rel="noreferrer">来源原文 ↗</a>` : ""}
      </div>`;
    }).join("");
    const next = (data.next_actions || []).map((s) => `<li>${esc(s)}</li>`).join("");
    return `<div class="card">${cardHead(data, "没找到对应的事项")}
      <p class="aval">${lead}</p>
      ${gen}
      ${clues ? `<div class="sec"><h3>原文线索</h3>${clues}</div>` : ""}
      ${choices ? `<p class="aval">${esc(data.clarify || "你要办的是下面哪一类？")}</p><div class="opts">${choices}</div>` : ""}
      ${related ? `<p class="aval">这些事项可能是你要的</p><div class="opts">${related}</div>` : ""}
      ${alts ? `<p class="aval">相近的事项</p><div class="opts">${alts}</div>` : ""}
      ${hints ? `<div class="sec"><h3>归口线索（非官方流程）</h3>${hints}</div>` : ""}
      ${contacts ? `<div class="sec"><h3>公开联系方式（按你问的事匹配，非办事流程）</h3>${contacts}</div>` : ""}
      ${next ? `<div class="sec"><h3>接下来可以这样办</h3><ul class="alines">${next}</ul></div>` : ""}
      ${data.suggestion ? `<p class="plannote">${esc(data.suggestion)}</p>` : ""}
      <div class="opts">
        <button class="opt" type="button" data-panel="contacts">看公开联系方式</button>
        <button class="opt" type="button" data-panel="search">在原文里找这句话</button>
      </div>
    </div>`;
  }

  function clarifyCard(data) {
    const n = (data.disambiguate || []).length;
    const reason = data.reason || (n === 2
      ? "这两件事不在同一个地方办。选一个，我按那件事的原文回答。"
      : "选一个，我按那件事的原文回答。");
    const opts = (data.disambiguate || []).map((choice) =>
      `<button class="opt" type="button" data-ask="${esc(choice.title || choice.label || choice)}"${pickAttr(choice)}>${esc(docName(choice.label || choice.title || choice))}
        ${choice.dept ? `<span class="odept">${esc(choice.dept)}</span>` : ""}</button>`).join("");
    return `<div class="card">${cardHead(data, "想问哪一个")}
      <p class="aval">${esc(data.clarify || "没太确定你问的是哪一件")}</p>
      <p class="norm">${esc(reason)}</p>
      <div class="opts">${opts}</div></div>`;
  }

  function holdCard(data) {
    // 与经典版 followupCard 同源：先确认 N 件事 + 已知条件 + 每问的备选 + 能确定的部分
    const known = Object.entries(data.known || {});
    const knownHtml = known.length
      ? `<div class="known">已记下 ${known.map(([, value]) => `<span class="norm">${esc(value)}</span>`).join(" ")}</div>` : "";
    const questions = (data.followups || []).map((f, i) => `<div class="fq">
      <p class="aval">${String(i + 1).padStart(2, "0")}　${esc(f.question)}</p>
      <div class="opts">${(f.options || []).map((o) =>
        `<button class="opt" type="button" data-key="${esc(f.key)}" data-opt="${esc(o)}">${esc(o)}</button>`).join("")}</div>
    </div>`).join("");
    const base = (data.answers || []).filter((a) => a.found).map(partHtml).join("");
    return `<div class="card" data-orig="${esc(data.query || "")}">${cardHead(data, (data.item || {}).title || "先确认一件事")}
      <p class="aval">这件事分几种情况，答之前先确认 ${(data.followups || []).length} 件事</p>
      ${knownHtml}${questions}
      ${relatedBlock(data.related)}
      ${base ? `<div class="sec"><h3>先给你能确定的部分</h3>${base}</div>` : ""}
    </div>`;
  }

  function answerCard(data) {
    const item = data.item || {};
    const quotes = data.quotes || [];
    const body = (data.answers || []).map(partHtml).join("");
    return `<div class="card">${cardHead(data, data.headline || item.title || "")}
      ${item.summary ? `<p class="aval">${richText(item.summary)}</p>` : ""}
      ${body}${noteBlock(data)}${attachBlock(item)}${relatedBlock(data.related)}${tableBlock(data)}
      ${sourceBlock(item)}
      <div class="cardfoot">
        <button class="plainbtn" type="button" data-act="quotes">核对原文 <span>${quotes.length}</span></button>
        <button class="plainbtn" type="button" data-act="material">清单与流程</button>
        <button class="plainbtn" type="button" data-act="copy">复制答案</button>
        <span class="stampnote">NO.${String(state.count).padStart(3, "0")} · ${esc(docName(item.title || ""))}</span>
      </div></div>`;
  }

  // 条目登记的官方网址：回答卡底部给前两条，点开就是学校页面上的原文。
  // 一条网址都没有就整块不出现，不留一个空标题。
  // 语料里少数来源记的是系统接口（点开是一段 JSON，人看不了），这类不当官方来源展示。
  const isReadableSource = (url) => !/\/engine2\/|api-v2|\.json(\?|#|$)/i.test(String(url || ""));
  function sourceLinks(item) {
    return (item.source || []).filter((s) => s && s.url && isReadableSource(s.url)).slice(0, 2);
  }
  function sourceBlock(item) {
    const list = sourceLinks(item);
    if (!list.length) return "";
    return `<div class="srcs"><h3>官方来源</h3>${list.map((s) => `<a class="srclink" href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(s.title || s.url)}</a>`).join("")}</div>`;
  }

  function partHtml(a) {
    const quotes = a.quotes || [];
    let value;
    if (!a.found) {
      value = `<p class="aval none">官方页面没有写这一项</p>`;
    } else if (Array.isArray(a.steps) && a.steps.length) {
      value = `<ol class="asteps">${a.steps.map((step, index) => {
        const what = typeof step === "string" ? step : (step.what || "");
        const where = stepNote(step, index);
        return `<li><span>${richText(what)}${where ? ` <span class="norm">${esc(where)}</span>` : ""}</span></li>`;
      }).join("")}</ol>`;
    } else if (Array.isArray(a.lines) && a.lines.length) {
      value = `<ul class="alines">${a.lines.map((line) => `<li>${richText(line)}</li>`).join("")}</ul>`;
    } else {
      const text = a.text == null ? "" : String(a.text);
      value = `<p class="aval">${richText(text || "官方页面没有写这一项")}</p>`;
    }
    const first = quotes[0] ? quoteLine(quotes[0]) : (a.focus === "contact" && a.found
      ? `<div class="qmore">联系人取自这条事项的归属部门，官方页面里没有单列这一句。</div>` : "");
    // 引文一条都不藏（两版内容必须一致），只把视觉权重让回答案正文：
    // 每条面下内联第一段原文，其余原文在档案栏「原文」标签里全量列出。
    return `<div class="aone"><div class="alab">${esc(a.label || "答复")}</div>${value}${
      first ? `<div class="qsrc">${first}</div>` : ""}</div>`;
  }

  function quoteLine(q, opts = {}) {
    if (!q) return "";
    const meta = [q.kind, q.date].filter(Boolean).join(" / ") || "原文";
    const who = q.label || q.src || "";
    const whoHtml = who
      ? `<span class="who">${q.url ? `<a href="${esc(q.url)}" target="_blank" rel="noreferrer">${esc(who)}</a>` : esc(who)}</span>`
      : "";
    const text = opts.short && q.quote && q.quote.length > 120 ? q.quote.slice(0, 120) + "…" : q.quote;
    return `<div class="qline"><span class="qmeta">${esc(meta)}</span>
      <div class="qtxt">${richText(text)}${whoHtml}</div></div>`;
  }

  function noteBlock(data) {
    if (data.note) return `<p class="plannote">${richText(data.note)}</p>`;
    if (data.missing && data.missing.length) {
      return `<p class="plannote">官方页面没有写 ${esc(data.missing.join("、"))}，我不能替学校补。</p>`;
    }
    return "";
  }

  function attachBlock(item) {
    const pdfs = Array.isArray(item.pdf) ? item.pdf : [];
    if (!pdfs.length) return "";
    return `<div class="sec"><h3>官方附件</h3><div class="opts">${pdfs.map((p) =>
      `<a class="opt" href="${esc(p.url)}" target="_blank" rel="noreferrer">${esc(p.title || "文件")}</a>`).join("")}</div></div>`;
  }

  function relatedBlock(list) {
    if (!Array.isArray(list) || !list.length) return "";
    return `<div class="sec"><h3>相关事项（点一下直接问）</h3><div class="opts">${list.slice(0, 8).map((b) =>
      `<button class="opt" type="button" data-ask="${esc(b.title || b.hint)}"${pickAttr(b)}>${esc(docName(b.label || b.title))}
        ${b.dept ? `<span class="odept">${esc(b.dept)}</span>` : ""}</button>`).join("")}</div></div>`;
  }

  // 数据表的行不进答案正文：一行表格数字没有办理上下文，顶在答案里等于拿它当结论。
  // 后端只递一个条数，点开了到原文检索面板里看那几行原文。
  function tableBlock(data) {
    const t = data.table_link;
    if (!t || !t.count || !t.q) return "";
    return `<div class="sec"><h3>数据表（表格里的原文，不是办理结论）</h3><div class="opts">
      <button class="opt" type="button" data-panel="search" data-query="${esc(t.q)}">有 ${num(t.count)} 行和这句话字面相近，点开看</button>
    </div></div>`;
  }

  function extractText(d) {
    if (d.llm_answer && d.llm_answer.text) return d.llm_answer.text.slice(0, 500);
    const bits = [];
    for (const part of d.answers || []) {
      if (part.text) bits.push(part.text);
      else if (part.steps && part.steps.length) bits.push(part.steps.map((s) => typeof s === "string" ? s : (s.what || "")).join("；"));
      else if (part.lines && part.lines.length) bits.push(part.lines.join("；"));
    }
    if (bits.join("\n")) return bits.join("\n").slice(0, 500);
    return d.normalized || d.search_note || "（未匹配到事项）";
  }

  /* ---------- 对话流 ---------- */
  function addExchange(text) {
    const wrap = document.createElement("div");
    wrap.innerHTML = `<div class="ask">${esc(text)}</div><div data-slot></div>`;
    // 先把答案槽取出来：下面的循环会把子节点全部搬进 #thread，搬完后 wrap 自己是空的
    const slot = wrap.lastElementChild;
    while (wrap.firstChild) el.thread.appendChild(wrap.firstChild);
    el.thread.scrollTop = el.thread.scrollHeight;
    return slot;
  }

  function jumpToStart(anchor) {
    // 答案是从槽往下长的，视口却停在旧位置：把这一轮的开头顶到顶栏下沿。
    // 滚动的一直是文档（.thread 没有 overflow）；卡片入场动画会让它的
    // scrollHeight 短暂大于 clientHeight，所以不能拿「谁可滚滚谁」当判据。
    const shift = window.scrollY || document.documentElement.scrollTop || 0;
    const style = getComputedStyle(document.documentElement);
    // --panel-top 是实测顶栏底边后下发的真值：窄屏顶栏绕成两三行时它比 84 大得多，
    // 只看 --topbar-keep 会把刚点亮的加载点顶到顶栏底下。后者只是 JS 没跑起来时的兜底。
    const keep = parseFloat(style.getPropertyValue("--panel-top") || style.getPropertyValue("--topbar-keep"));
    const offset = (Number.isFinite(keep) ? keep : 0) + 12;
    const top = Math.max(0, anchor.getBoundingClientRect().top + shift - offset);
    // 不用 smooth：占位比答案高，答案到达时文档会突然矮一大截，而没跑完的平滑滚动
    // 不理会这次收缩，继续往一个已经不存在的位置夹，实测把答案顶到顶栏上面
    // （卡片 -64 ~ -10px，大标题压在透明顶栏底下）。瞬时落位没有这个窗口。
    window.scrollTo({ top, behavior: "instant" });
  }

  /* /api/ask 有两种回法：一次性 JSON（后端还没上 SSE 就是这样），和 event-stream
     一步步把模型调用报出来。这里只负责读，不猜进度：一条都不报就退回一次性 JSON，
     槽里那一个呼吸框原样留着，前端不编阶段。 */
  async function askStream(body, onStep) {
    let res;
    try {
      res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify(body),
      });
    } catch (error) {
      throw new Error("连不上本地服务，请确认 app.py 已在当前端口运行");
    }
    const type = res.headers.get("content-type") || "";
    if (!type.includes("event-stream")) {
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error((data && (data.error || data.detail || data.message)) || `请求失败（${res.status}）`);
      }
      return { json: data, streamed: false };
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let payload = null;
    let failure = null;
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      let cut = buffer.indexOf("\n\n");
      while (cut >= 0) {
        const frame = buffer.slice(0, cut);
        buffer = buffer.slice(cut + 2);
        const name = (frame.match(/^event:\s*(.+)$/m) || [])[1];
        const raw = (frame.match(/^data:\s*(.+)$/m) || [])[1];
        if (name && raw) {
          let data = null;
          try {
            data = JSON.parse(raw);
          } catch (error) {
            if (name !== "step") failure = new Error(`思考流第 ${name} 步的数据读不出来`);
          }
          if (data) {
            if (name === "step") onStep(data);
            if (name === "done") payload = data;
            if (name === "err") failure = new Error(data.error || data.detail || data.message || "模型这一趟没走完");
          }
        }
        cut = buffer.indexOf("\n\n");
      }
    }
    if (failure) throw failure;
    if (!payload) throw new Error("思考流断了：没等到 done 那一步");
    return { json: payload, streamed: true };
  }

  // 后端报的字段名 → 界面上的说法。只有名字是前端给的，值一律原样来自后端。
  const THINK_KEYS = {
    gate: "门", pool: "候选", pool2: "候选2", score: "复核分", facets: "面",
    rewrites: "改写", rescue: "救场", changed: "改判", confirmed: "复核",
    asked: "裁决", why: "理由", faces: "拼面", plan: "拼装", error: "报错",
  };

  function thinkValue(value) {
    // 后端字段可能是数组或嵌套字典（如 assembly:{faces:[…]}），不递归就会打成 [object Object]
    if (Array.isArray(value)) return value.map(thinkValue).filter(Boolean).join("、");
    if (value && typeof value === "object") {
      return Object.keys(value)
        .map((key) => `${THINK_KEYS[key] || key}=${thinkValue(value[key])}`)
        .filter((text) => !text.endsWith("="))
        .join(" · ");
    }
    return String(value);
  }

  function thinkLine(evt) {
    const src = (evt && (evt.fields || evt.route)) || {};
    const bits = [];
    Object.keys(src).forEach((key) => {
      const value = src[key];
      const name = THINK_KEYS[key] || key;
      if (value === true) { bits.push(name); return; }          // 布尔只报「有这回事」
      if (value === null || value === undefined || value === false || value === "") return;
      const text = thinkValue(value);
      if (text) bits.push(`${name}=${text}`);
    });
    return bits.join(" · ");
  }

  function typeInto(node, text) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      node.textContent = text;
      return null;
    }
    let shown = 0;
    const timer = setInterval(() => {
      shown += 3;                    // 每拍三个字：一框两行大约三拍打完
      node.textContent = text.slice(0, shown);
      if (shown >= text.length) clearInterval(timer);
    }, 40);
    return timer;
  }

  /* 思考流：后端每报一次模型调用就开一个框，下一框开始打字时上面那些折到三行。
     答案到达时整串折成一行摘要，点开恢复全文。 */
  function thinkFlow(slot) {
    const timers = [];
    const boxes = [];
    let wrap = null;
    let dots = null;
    let seconds = 0;

    function open() {
      if (wrap) return;
      // 第一条 step 到了才换掉等待时那一个框；三点不消失，改成常驻在最后一条
      slot.innerHTML = '<div class="thinking" role="status" aria-label="正在等模型回话">'
        + '<div class="thinksteps"><div class="thinkbox dots"><i></i><i></i><i></i></div></div></div>';
      wrap = slot.querySelector(".thinksteps");
      dots = slot.querySelector(".thinkbox.dots");
    }

    return {
      step(evt) {
        open();
        // 上一行折到三行、竖线退回灰；新到的这条才是「正在想」的
        boxes.forEach((box) => {
          box.node.classList.add("folded");
          box.node.classList.remove("now");
        });
        if (evt && typeof evt.t === "number") seconds += evt.t;
        const node = document.createElement("div");
        node.className = "thinkbox now";
        const label = (evt && (evt.label || evt.id)) || "模型调用";
        const text = thinkLine(evt);
        node.innerHTML = `<h4 class="thinklab">${esc(label)}</h4><p class="thinktxt"></p>`;
        // 插在三点前面：每来一步就多一行，三点顺延到最下面，一直表示「还在想」
        wrap.insertBefore(node, dots);
        boxes.push({ node, text });
        const timer = typeInto(node.querySelector(".thinktxt"), text);
        if (timer) timers.push(timer);
      },
      stop() {
        timers.forEach((timer) => clearInterval(timer));
        timers.length = 0;
      },
      collapsed() {
        if (!boxes.length) return "";
        this.stop();
        // 摘要里每个框都给全文：折叠只是等待过程中的临时形态，三点也不再带上
        const html = boxes.map((box) => `<div class="thinkbox"><h4 class="thinklab">${box.node.querySelector(".thinklab").innerHTML}</h4><p class="thinktxt">${esc(box.text)}</p></div>`).join("");
        return `<div class="thinking" data-done="1"><button class="thinksum" type="button" aria-expanded="false">已思考 ${boxes.length} 步 · ${seconds.toFixed(1)}s</button><div class="thinksteps" hidden>${html}</div></div>`;
      },
    };
  }

  async function ask(text, pick) {
    text = String(text || "").trim();
    if (text.length < 2) { toast("问得太短了，把要办的事说全一点"); return; }
    if (state.busy) return;
    state.busy = true;
    el.send.disabled = true;
    const slot = addExchange(text);
    // 思考框也写进这个槽：答案（或错误卡）随后覆盖 slot.innerHTML，框就随之消失。
    // 顺序不能反——先请求再点亮，等于答完了才亮。后端报出第一步之前，框里不放任何阶段文字。
    slot.innerHTML = `<div class="thinking" role="status" aria-label="正在等模型回话"><div class="thinkbox dots"><i></i><i></i><i></i></div></div>`;
    jumpToStart(slot);
    const flow = thinkFlow(slot);
    try {
      const { json: response } = await askStream({
        text,
        slots: state.slots,
        router_llm: el.llm.checked,
        context_item: state.item ? state.item.id : null,
        context_slots: (state.last && state.last.known) || {},
        messages: state.history.slice(-12),
        // 点选项时必须带上条目 id：只按标题重新问，同一句词会再摊出同一份菜单
        pick_item: pick || null,
      }, (evt) => flow.step(evt));
      state.last = response;
      state.count += 1;
      slot.innerHTML = flow.collapsed() + renderResult(response);
      afterResult(response);
      // 落位要排在 afterResult 之后：这一问定位到条目时它会 setMode("work")，
      // .hero 整块 display:none，文档当场矮掉一大截。在那之前量到的位置不作数。
      jumpToStart(slot);
      state.history.push({ role: "user", content: text });
      state.history.push({ role: "assistant", content: extractText(response) });
      if (state.history.length > 24) state.history = state.history.slice(-24);
    } catch (error) {
      flow.stop();
      slot.innerHTML = `${flow.collapsed()}<div class="errcard"><h2>这次没答上来</h2><p class="aval">${esc(error.message)}</p></div>`;
      jumpToStart(slot);
    } finally {
      state.busy = false;
      el.send.disabled = false;
    }
  }

  function afterResult(response) {
    const matched = response.matched && response.item
      && !(response.disambiguate && response.disambiguate.length);
    if (matched) {
      state.item = response.item;
      loadDeliver();
    }
    // 这一问没答上、或正在反问，不等于用户换了话题：上一件事留着，
    // 下一句「几天能办好」才有得接续。一没答上就清空，就是「问两句就失忆」的根因。
    if (state.item) {
      el.topline.textContent = `当前事项 · ${docName(state.item.title) || ""}`;
    } else {
      el.topline.textContent = "还没定位到具体事项";
      state.deliver = null;
    }
    el.topline.hidden = false;
    setMode("work");
    renderIns();
    updateStamp();
    // 后端在回答里给 data.map（问句点到校内地点），经典版靠它开地图抽屉。
    // 这里漏接就是「问了地点却不拉地图」的根因；自动拉起不抢答案的焦点，
    // 也没有地点时不抢关用户自己开着的面板。
    if (response.map && response.map.name) {
      state.mapPlace = response.map;
      state.mapPick = response.map.name;
      state.mapQuery = "";
      openPanel("map", true);
    }
  }

  /* ---------- 条目档案 ---------- */
  async function loadDeliver() {
    if (!state.item) return;
    try {
      state.deliver = await api("/api/deliver", { item_id: state.item.id, slots: state.slots });
      if (state.tab === "material") renderIns();
    } catch (error) {
      state.deliver = null;
    }
    updateStamp();
  }

  function updateStamp() {
    el.stamp.textContent = `NO.${String(state.count).padStart(3, "0")} · ${state.item ? state.item.id : "—"}`;
  }

  // 概览、材料、流程三节各按自己的字段判有没有内容；一节空着就连标签一起收起来，
  // 不再让人点进去只看到一句「官方页面没有写」。原文标签是核对出处用的，始终留着。
  const OVERVIEW_KEYS = ["location", "fee", "hours", "duration", "window", "channel"];
  const MATERIAL_KEYS = ["materials", "draft"];
  const STEPS_KEYS = ["steps"];

  function hasContent(item, kind) {
    if (!item) return false;
    const keys = kind === "overview" ? OVERVIEW_KEYS : kind === "material" ? MATERIAL_KEYS : STEPS_KEYS;
    return keys.some((key) => {
      const value = item[key];
      return Array.isArray(value) ? value.length > 0 : String(value == null ? "" : value).trim().length > 0;
    });
  }

  function visibleTabs(item) {
    $$("[data-tab]", el.tabs).forEach((btn) => {
      btn.hidden = item ? !hasContent(item, btn.dataset.tab) && btn.dataset.tab !== "quotes" : false;
    });
    if (item && !hasContent(item, state.tab) && state.tab !== "quotes") {
      const first = $$("[data-tab]", el.tabs).find((btn) => !btn.hidden);
      if (first) state.tab = first.dataset.tab;
    }
    syncTabs();
  }

  function renderIns() {
    const item = state.item;
    el.title.textContent = item ? docName(item.title) : "条目档案";
    el.sub.textContent = item
      ? [item.dept, statusText(item), item.confidence === "high" ? "核对程度高" : item.confidence === "low" ? "核对程度低" : "核对程度中"].filter(Boolean).join(" / ")
      : "问一件事，这里出现它的官方依据、材料与流程。";
    if (!item) {
      visibleTabs(null);
      el.qcount.textContent = "0";
      el.body2.innerHTML = `<div class="insempty"><p>这一栏放的是答案的出处。问一句，这里固定显示四项：办理信息、要带的材料、可执行步骤、原文引文。每条结论都注明出自哪一段原文。</p>
        <ul><li>原文没写的字段，显示「官方页面没有写这一项」，不替学校补。</li><li>勾选只存在当前页面，不上传。</li></ul></div>`;
      return;
    }
    visibleTabs(item);
    if (state.tab === "material") return renderMaterial(item);
    if (state.tab === "steps") return renderSteps(item);
    if (state.tab === "quotes") return renderQuotes(item);
    renderOverview(item);
  }

  function renderOverview(item) {
    const rows = [
      ["地点", item.location],
      ["费用", item.fee],
      ["时间", item.hours],
      ["办理时长", item.duration],
      ["受理窗口", item.window],
      ["渠道", Array.isArray(item.channel) ? item.channel.join(" / ") : item.channel],
    ];
    // 官方没登记的项整行不显示：连着几行「这一项没有」的灰字会盖掉真正有用的信息。
    // 缺失这件事仍由后端给的 note / missing 在答案卡上说明一次，档案栏不重复刷屏。
    const shown = rows.filter(([, value]) => String(value == null ? "" : value).trim().length > 0);
    el.qcount.textContent = String(((state.last && state.last.quotes) || []).length);
    el.body2.innerHTML = (shown.length
      ? `<dl class="field-list">${shown.map(([label, value]) =>
        `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`).join("")}</dl>`
      : "")
      + (item.pitfalls && item.pitfalls.length
        ? `<div class="sec"><h3>容易出错</h3><ul class="alines">${item.pitfalls.map((p) => `<li>${esc(p)}</li>`).join("")}</ul></div>`
        : "");
  }

  function renderMaterial(item) {
    const source = state.deliver || item;
    const mats = ((source && source.materials) || []).map((m) => (typeof m === "string" ? { name: m } : m));
    const checkedCount = mats.filter((_, index) => state.checked.has(`${item.id}:${index}`)).length;
    const list = mats.length
      ? `<div class="sec"><h3>要带的东西 · 已备 ${checkedCount}/${mats.length}</h3><ul class="checks">${mats.map((m, index) => `
          <li role="checkbox" tabindex="0" aria-checked="${state.checked.has(`${item.id}:${index}`)}" data-mat="${index}">
            <span class="cbox" aria-hidden="true"></span>
            <span class="mname">${esc(m.name)}${m.note ? `<span class="mnote">${esc(m.note)}</span>` : ""}</span>
          </li>`).join("")}</ul></div>`
      : "";
    const draft = source && source.draft ? `<div class="sec"><h3>${esc(source.draft.title || "文书草稿")}</h3>
      <pre class="qtxt">${esc(source.draft.text)}</pre></div>` : "";
    el.body2.innerHTML = list + draft
      + (mats.length ? `<p class="insempty" style="margin-top:14px">勾选只存在当前页面，不上传。带材料以官方原文与窗口要求为准。</p>` : "");
  }

  function renderSteps(item) {
    const steps = item.steps || [];
    el.body2.innerHTML = steps.length
      ? `<ol class="asteps">${steps.map((step, index) => {
          const what = typeof step === "string" ? step : (step.what || "");
          const where = stepNote(step, index);
          return `<li><span>${esc(what)}${where ? ` <span class="norm">${esc(where)}</span>` : ""}</span></li>`;
        }).join("")}</ol>`
      : "";
  }

  function renderQuotes(item) {
    const raw = (state.last && state.last.quotes) || [];
    const seen = new Set();
    const uniq = raw.filter((q) => q && q.quote && (seen.has(q.quote) ? false : (seen.add(q.quote), true)));
    el.qcount.textContent = String(uniq.length);
    const list = uniq.length
      ? `<div class="quotelist">${uniq.map((q) => `<div class="qline">
          <span class="qmeta">${esc(q.kind || "原文")}${q.date ? " / " + esc(q.date) : ""}</span>
          <div class="qtxt">${richText(q.quote)}<span class="who">${q.url ? `<a href="${esc(q.url)}" target="_blank" rel="noreferrer">${esc(q.label || q.src || "")}</a>` : esc(q.label || q.src || "")}</span></div>
        </div>`).join("")}</div>`
      : `<p class="insempty">这次回答没有引用到原文段落。下面是条目登记的官方来源，可直接打开核对。</p>`;
    const src = (item.source || []).map((s) => `<div class="qline">
        <div class="qtxt">${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(s.title || s.url)}</a>` : esc(s.title || "")}</div>
        ${s.checked ? `<span class="qmeta">核验 ${esc(s.checked)}</span>` : ""}</div>`).join("");
    el.body2.innerHTML = list + src;
  }

  /* ============================================================
     二期面板：原文检索 / 公开联系方式 / 位置示意 / 个人数据入口。
     前三块只读后端既有接口；「个人数据」按 2026-11-02 的口径只做一件事——
     把两个官方系统的入口给出来，查余额、流水、课表都在官方页面里由本人登录完成，
     向导页不代查、不嵌入官方页面、也不保存任何东西。
     面板是附加层，都不碰问答主链路。
     ============================================================ */
  // 两个地址与经典版组件 personal-data.js 里的同名常量必须逐字一致（有测试比对），
  // 免得两版各写一份、点进去其实不是同一个系统。
  const CARD_URL = "https://pcard.cuc.edu.cn/servicehall/ykt/query?code=5";
  const COURSES_URL = "https://courses.cuc.edu.cn/user/index";

  const PANELS = {
    search: { title: "原文检索", render: searchPanel },
    contacts: { title: "公开联系方式", render: contactPanel },
    map: { title: "校园位置", render: mapPanel },
    personal: { title: "个人数据 · 官方入口", render: personalPanel },
  };

  let panelReturn = null;

  function openPanel(kind, keepFocus) {
    const panel = PANELS[kind];
    if (!panel) return;
    // 换一个面板就重画外壳；同一个面板再打开时保留上次的结果与输入
    if (el.panel.dataset.kind !== kind) {
      // 地图实例绑死在容器节点上：清空 panelbody 之前不先 remove，
      // 再开一次地图就会撞 Leaflet 的 "Map container is already initialized"。
      resetBasemap();
      el.panel.dataset.kind = kind;
      el.panelbody.innerHTML = "";
      panelReturn = document.activeElement;
    }
    el.pantitle.textContent = panel.title;
    // 顶栏若正收着，先无动画拉回来再量底边：面板要落在顶栏下面，那一排入口才点得到
    if (el.bar && el.bar.classList.contains("is-up")) {
      el.bar.classList.add("no-anim");
      el.bar.classList.remove("is-up");
      void el.bar.offsetHeight;
      el.bar.classList.remove("no-anim");
      barUp = false;
    }
    syncPanelTop();
    // 每次打开都回到默认半屏：上一次拉出来的高度不带进下一次
    el.panel.style.removeProperty("--sheet-h");
    el.scrim.hidden = false;
    el.panel.hidden = false;
    el.body.dataset.panelOpen = kind;
    panel.render();
    // keepFocus：回答里带地点时自动拉起地图，不能把焦点从答案上抢走
    if (!keepFocus) {
      const first = $(".paninput, .purposes button, .poirow button, .pdlink", el.panelbody);
      (first || el.panclose).focus({ preventScroll: true });
    }
  }

  let barBottom = 0;
  function syncPanelTop() {
    // 顶栏答完题会多出「当前事项」一行，窄屏还会换行——高度是动态的，写死的档位必然压住顶栏。
    // 实测底边下发成 --panel-top，面板和遮罩都从这条线下面开始，右侧三个入口才一直点得到。
    // 顶栏收起中量到的是位移里的中间值，不作数：沿用上一次没收起时量到的底边。
    const bottom = el.bar ? Math.round(el.bar.getBoundingClientRect().bottom) : 0;
    const collapsed = el.bar && el.bar.classList.contains("is-up");
    if (bottom > 0 && !collapsed) barBottom = bottom;
    const keep = bottom > 0 && !collapsed ? bottom : barBottom;
    if (keep > 0) document.documentElement.style.setProperty("--panel-top", `${keep}px`);
  }

  // 顶栏高度变化（换面板标题、窗口缩放、字体重排）都会重新对齐一次
  if (window.ResizeObserver && el.bar) new ResizeObserver(syncPanelTop).observe(el.bar);

  function closePanel() {
    if (el.panel.hidden) return;
    el.panel.hidden = true;
    el.scrim.hidden = true;
    delete el.body.dataset.panelOpen;
    if (panelReturn && document.contains(panelReturn)) panelReturn.focus({ preventScroll: true });
    panelReturn = null;
  }

  // 手机端抽屉的拉手：按住标题行向上提，高度从半屏长到 2/3 屏。
  // 上下限都写在 field.css 的 clamp 里，这里只报一个 --sheet-h；报多了被夹住的那一段
  // 不扔掉，接着拿去滚内容——一次手势从「拉高抽屉」直接接到「滚列表」，不用松手重按。
  const sheetMedia = window.matchMedia("(max-width: 720px)");

  function initSheetDrag() {
    const head = $(".panelhead", el.panel);
    if (!head) return;
    let drag = null;
    head.addEventListener("pointerdown", (event) => {
      if (!sheetMedia.matches || event.target.closest("button")) return;
      drag = { y: event.clientY, h: el.panel.getBoundingClientRect().height, top: el.panelbody.scrollTop };
      head.setPointerCapture(event.pointerId);
    });
    head.addEventListener("pointermove", (event) => {
      if (!drag) return;
      const want = drag.h + (drag.y - event.clientY);
      el.panel.style.setProperty("--sheet-h", `${want}px`);
      const got = el.panel.getBoundingClientRect().height;
      if (want > got) el.panelbody.scrollTop = drag.top + (want - got);
    });
    const stop = () => { drag = null; };
    head.addEventListener("pointerup", stop);
    head.addEventListener("pointercancel", stop);
  }

  /* ---------- 原文检索：GET /api/search?q=&k=，只给原文段落 ---------- */
  async function searchPanel() {
    const q = String(state.searchQuery || "").trim();
    if (!$(".panbar", el.panelbody)) el.panelbody.innerHTML = `<form class="panbar" data-panel-form="search" role="search"><input class="paninput" type="search" placeholder="要在那段原文里找哪句话" value="${esc(q)}" aria-label="在官方原文里检索"><button class="send" type="submit">搜索</button></form><p class="pansub">只给原文、不生成答案：下面是官方原文里与你这句话最接近的段落，内容以原文为准。</p><div class="panout"></div>`;
    const out = $(".panout", el.panelbody);
    if (q.length < 2) { out.innerHTML = `<p class="insempty">说具体一点再搜，至少两个字。</p>`; return; }
    const data = await api("/api/search?q=" + encodeURIComponent(q) + "&k=12").catch((error) => ({ fail: error.message }));
    if (data.fail) { out.innerHTML = `<p class="insempty">${esc(data.fail)}</p>`; return; }
    const hits = data.hits || [];
    const rows = hits.map((h) => `<div class="hitrow"><div class="ht">${esc(docName(h.title) || "原文段落")}</div><p class="norm">${[h.kind || "原文", h.page ? "第 " + esc(String(h.page)) + " 页" : "", h.score != null ? "相关度 " + pct(h.score) : ""].filter(Boolean).join(" · ")}</p><p class="aval">${markHits(h.snippet || "", q)}</p>${h.url ? `<a class="opt" href="${esc(h.url)}" target="_blank" rel="noreferrer">打开原文 ↗</a>` : ""}</div>`).join("");
    const tableRows = (data.rows || []).map((r) => {
      const who = docName(r.label || r.title) || "数据表";
      const meta = [(r.kind && r.kind !== "未知" ? r.kind : "表格行"),
        r.row_no ? "第 " + esc(String(r.row_no)) + " 行" : "",
        r.shared ? "字面重合 " + num(r.shared) + " 处" : ""].filter(Boolean).join(" · ");
      return `<div class="hitrow"><div class="ht">${esc(who)}</div><p class="norm">${meta}</p>
        <p class="aval">${markHits(r.text || "", q)}</p>${
        r.url && isReadableSource(r.url) ? `<a class="opt" href="${esc(r.url)}" target="_blank" rel="noreferrer">打开原文 ↗</a>` : ""}</div>`;
    }).join("");
    out.innerHTML = `<p class="norm">原文里共命中 ${num(data.total)} 段，下面是最接近的 ${hits.length} 段。</p>`
      + (rows || `<p class="insempty">原文里没有相近的段落，换一个更具体的说法再试。</p>`)
      + (tableRows ? `<p class="pansub">数据表里最接近的 ${(data.rows || []).length} 行，逐格原文照搬，不是办理结论。</p>${tableRows}` : "");
  }

  /* ---------- 联系方式：GET /api/contacts[?purpose=]，全部来自公开原文 ---------- */
  async function contactPanel() {
    const purpose = state.contactPurpose || "";
    const cached = state.contacts && state.contacts.key === purpose;
    const data = cached ? null : await api("/api/contacts" + (purpose ? "?purpose=" + encodeURIComponent(purpose) : "")).catch((error) => ({ fail: error.message }));
    if (data && data.fail) { el.panelbody.innerHTML = `<p class="insempty">${esc(data.fail)}</p>`; return; }
    if (data) state.contacts = { key: purpose, purposes: data.purposes || [], items: data.items || [], total: data.total || 0 };
    const store = state.contacts || { purposes: [], items: [], total: 0 };
    const HREF = { phone: "tel:", email: "mailto:" };
    const chips = [{ key: "", label: "全部" }].concat(store.purposes.map((p) => ({ key: p, label: p })))
      .map((o) => `<button type="button" data-purpose="${esc(o.key)}" aria-pressed="${o.key === purpose}">${esc(o.label)}</button>`).join("");
    const rows = store.items.map((c) => `<div class="ctrow"><span class="ctv">${
      HREF[c.kind] ? `<a href="${esc(HREF[c.kind] + String(c.value || "").replace(/\s/g, ""))}">${esc(c.value)}</a>`
        : c.source_url ? `<a href="${esc(c.source_url)}" target="_blank" rel="noreferrer">${esc(c.value)}</a>` : esc(c.value)}</span>${
      c.source_url ? `<a class="ctsrc" href="${esc(c.source_url)}" target="_blank" rel="noreferrer">来源原文 ↗</a>` : `<span class="ctsrc">见原文</span>`}<span class="ctmeta">${
        [c.dept, c.purpose, c.context].filter(Boolean).join(" · ")}</span></div>`).join("");
    el.panelbody.innerHTML = `<p class="pansub">这些是公开渠道上登记的联系方式，共 ${num(store.total)} 条；按用途先挑一类。号码和邮箱会随部门调整，办事前点「来源原文」核对那一条。</p><div class="purposes" role="group" aria-label="按用途筛选">${chips}</div><div class="panout">${rows || `<p class="insempty">这一类下没有公开的联系方式。</p>`}</div>`;
  }

  /* ---------- 位置：本地 Leaflet 接高德底图，点位只用官方给过的坐标 ---------- */
  function poiHaystack(p) {
    return [p.name, p.place, p.kind].concat(p.aliases || []).join(" ");
  }

  // 瓦片地址与经典版 app.js 一字不差：同一栋楼在两版页面上必须落在同一张底图的同一个位置。
  const MAP_TILE = "https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}";
  // 兜底视角，和 /api/campus 的 center 一致。campus-map.json 里的坐标是 GCJ-02，与高德底图同基准，不用换算。
  const MAP_HOME = [39.9137, 116.5536];
  const CONF = { high: "高", medium: "中", low: "低" };
  const mapView = { view: null, layer: null };

  function token(name) {
    return String(getComputedStyle(el.body).getPropertyValue(name)).trim();
  }

  function mapHome() {
    const center = (state.campus && state.campus.center) || {};
    return center.lat != null && center.lng != null ? [Number(center.lat), Number(center.lng)] : MAP_HOME;
  }

  function markerCoords(url) {
    const hit = /position=([\d.]+),([\d.]+)/.exec(String(url || ""));
    return hit ? [Number(hit[2]), Number(hit[1])] : null;
  }

  function ensureBasemap(node) {
    if (mapView.view) return mapView.view;
    if (!node || !window.L) return null;
    // 滚轮缩放关掉：面板是能滚的，地图把滚轮吃掉会让人以为页面卡住
    const view = L.map(node, { zoomControl: true, attributionControl: true, scrollWheelZoom: false }).setView(mapHome(), 16);
    L.tileLayer(MAP_TILE, { subdomains: "1234", maxZoom: 19, attribution: "底图来自高德地图" }).addTo(view);
    mapView.view = view;
    return view;
  }

  function resetBasemap() {
    mapView.layer = null;
    if (!mapView.view) return;
    mapView.view.remove();
    mapView.view = null;
  }

  function plotSpots(view, points, target) {
    if (mapView.layer) mapView.layer.clearLayers(); else mapView.layer = L.layerGroup().addTo(view);
    const accent = token("--accent");
    points.forEach((p) => {
      const on = !!target && p.name === target.name;
      const dot = L.circleMarker([Number(p.lat), Number(p.lng)], {
        radius: on ? 9 : 5, color: accent, weight: on ? 3 : 1.4, opacity: 1,
        fillColor: accent, fillOpacity: on ? 1 : 0.3,
      }).addTo(mapView.layer);
      dot.bindTooltip(esc(p.name) + (p.place ? ` · ${esc(p.place)}` : ""), { direction: "top", offset: [0, -8] });
      if (on) dot.openTooltip();
    });
  }

  function aimAt(view, target) {
    view.invalidateSize();
    if (target && target.lat != null && target.lng != null) { view.setView([Number(target.lat), Number(target.lng)], 17); return; }
    view.setView(mapHome(), 16);
  }

  function pickTarget(all) {
    const name = String(state.mapPick || "");
    if (!name) return null;
    const listed = all.filter((p) => p.name === name)[0];
    if (listed) return listed;
    // 回答里点到的地点不一定在校内清单里（例如只出现在原文中的叫法），这时用后端给的那一条兜，
    // 坐标从 amap 深链里解；解不出来就如实说没有坐标，不拿校园中心假造一个点。
    const answer = state.mapPlace || {};
    if (answer.name !== name) return null;
    const spot = markerCoords(answer.marker);
    return { name: name, place: answer.place || "", kind: "回答里提到的地点", aliases: [], lat: spot ? spot[0] : null, lng: spot ? spot[1] : null, coord_confidence: "", amap_marker: answer.marker || "", amap: answer.url || "" };
  }

  function pickCard(p) {
    const hasCoords = p.lat != null && p.lng != null;
    const deep = p.amap_marker || p.amap || "";
    return `<div class="mappick"><h4>${esc(p.name)}</h4><p>${[p.place, p.kind].filter(Boolean).join(" · ") || "官方未写具体位置"}</p><p>${hasCoords ? `坐标 ${esc(String(p.lat))}, ${esc(String(p.lng))} · 可信度 ${esc(CONF[p.coord_confidence] || p.coord_confidence || "未标注")}` : "官方没有给出这一处的坐标，图上不标点，只把范围放到校园这一片。"}</p>${deep ? `<div class="opts"><a class="opt" href="${esc(deep)}" target="_blank" rel="noreferrer">在高德里打开 ↗</a></div>` : ""}</div>`;
  }

  function poiRows(pool, q) {
    if (!pool.length) return `<p class="insempty">没有名字里带「${esc(q)}」的地点，换一个说法试试。</p>`;
    const rows = pool.slice(0, 16).map((p) => `<div class="poirow"><button class="pname" type="button" data-poi="${esc(p.name)}">${esc(p.name)}</button><span class="pplace">${[p.place, p.kind].filter(Boolean).join(" · ") || "官方未写具体位置"}</span>${p.lat != null ? `<span class="pcoord">图上有这个点</span>` : ""}${(p.amap_marker || p.amap) ? `<a class="opt" href="${esc(p.amap_marker || p.amap)}" target="_blank" rel="noreferrer">在高德里打开 ↗</a>` : ""}</div>`).join("");
    return `<div class="sec"><h3>${q ? `与「${esc(q)}」相近的地点` : "校内地点"}</h3>${rows}${pool.length > 16 ? `<p class="mapnote">这里只列前 16 个，搜索框里换个更具体的名字可以看全。</p>` : ""}</div>`;
  }

  function mapPanel() {
    const campus = state.campus || { pois: [] };
    const all = campus.pois || [];
    const q = String(state.mapQuery || "").trim();
    const pool = q ? all.filter((p) => poiHaystack(p).indexOf(q) >= 0) : all;
    const fixed = pool.filter((p) => p.lat != null && p.lng != null);
    if (!$(".panbar", el.panelbody)) el.panelbody.innerHTML = `<form class="panbar" data-panel-form="map" role="search"><input class="paninput" type="search" placeholder="找一栋楼、一个校门或一个学院" value="${esc(q)}" aria-label="在校内地点里找"><button class="send" type="submit">定位</button></form><p class="pansub">底图来自高德地图，图上只标官方给过坐标的地点：${all.length} 个校内地点里有坐标的是 ${fixed.length} 个；楼里在哪一层仍以原文为准。</p><div class="mapwrap"><div class="mapcanvas" id="mapcanvas" role="region" aria-label="校园地图，蓝点是官方给出坐标的地点"></div><p class="mapnote">坐标与高德底图同一基准，落点和导航能对上。底图要联网取，取不到时标记仍在原位；要直接导航点「在高德里打开 ↗」。</p></div><div class="mapdetail"></div><div class="panout"></div>`;
    const out = $(".panout", el.panelbody);
    const detail = $(".mapdetail", el.panelbody);
    if (!all.length) { out.innerHTML = `<p class="insempty">地点数据没取到，先确认本地服务在运行。</p>`; return; }
    const target = pickTarget(all);
    const view = ensureBasemap($("#mapcanvas"));
    if (!view) { detail.innerHTML = `<p class="insempty">地图组件没加载到（本地 vendor/leaflet 缺失），下面的地点列表和高德深链照常用。</p>`; out.innerHTML = poiRows(pool, q); return; }
    plotSpots(view, fixed, target);
    aimAt(view, target);
    detail.innerHTML = target ? pickCard(target) : `<p class="mapnote">在下面的列表里点一个地点，图上会把它标出来。</p>`;
    out.innerHTML = poiRows(pool, q);
  }

  function personalPanel() {
    // 微信内置浏览器打不开校内系统，这句提示只在微信里出现，别的浏览器不占版面。
    const inWeChat = /MicroMessenger/i.test(navigator.userAgent || "");
    el.panelbody.innerHTML = `
      <p class="pansub">这里不读取任何个人数据。校园卡的余额、流水和畅课的课程、课表都在学校官方系统里，要点开下面的页面、由本人登录查询，向导页不代查、不嵌入官方页面，也不保存任何东西。</p>
      <a class="pdlink" href="${CARD_URL}" target="_blank" rel="noreferrer"><b>校园卡</b><span>余额、有效期、流水</span><i>打开官方页面 ↗</i></a>
      <a class="pdlink" href="${COURSES_URL}" target="_blank" rel="noreferrer"><b>畅课</b><span>课程、待办、学期、课表</span><i>打开官方页面 ↗</i></a>
      ${inWeChat ? `<p class="pdwarn">微信里点开可能提示打不开，请在菜单里选「在浏览器打开」，或复制链接到浏览器地址栏。</p>` : ""}
      <p class="mapnote">两个入口是学校官方的 pcard.cuc.edu.cn 与 courses.cuc.edu.cn，地址沿用经典版组件里记录的页面，没有另写一份。</p>`;
  }

  /* ---------- 场域动效：背景随滚动上下变化，减弱动效时全停 ---------- */
  let ticking = false;
  function paintMotion() {
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const progress = scrollable > 0 ? Math.min(window.scrollY / scrollable, 1) : 0;
    el.body.style.setProperty("--scroll-shift", (progress * 100).toFixed(2) + "px");
    el.body.style.setProperty("--scroll-progress", progress.toFixed(4));
    ticking = false;
  }
  function scheduleMotion() {
    if (reduced.matches) return;
    if (!ticking) { ticking = true; requestAnimationFrame(paintMotion); }
  }

  /* ---------- 顶栏：下滑收起、上划拉出 ---------- */
  const BAR_KEEP = 160;   // 首屏这一段里永不收起，否则刚进页面手一抖顶栏就没了
  const BAR_DELTA = 12;   // 位移小于它不当作方向变化，避免来回开关
  let lastY = window.scrollY;
  let barUp = false;
  function syncBarHide() {
    const y = window.scrollY;
    if (!el.panel.hidden) {
      // 面板开着时不收：顶栏一位移，面板顶边跟着跳一整栏
      lastY = y;
      if (barUp) { barUp = false; el.bar.classList.toggle("is-up", barUp); }
      return;
    }
    const delta = y - lastY;
    if (Math.abs(delta) < BAR_DELTA) return;
    const wantUp = delta > 0 && y > BAR_KEEP;
    if (wantUp !== barUp) {
      barUp = wantUp;
      el.bar.classList.toggle("is-up", barUp);
    }
    lastY = y;
  }

  /* ---------- 事件 ---------- */
  /* 日夜开关：只翻 <html> 的 data-theme，别的东西一律不动。
     不写 storage 也不写 cookie——刷新就回到日间，默认状态随时能拿回去。
     状态挂在 aria-pressed 上：样式表靠它挑皮肤，读屏也能报出现在是白天还是夜里。 */
  function initThemeSwitch() {
    const btn = $("#themesw");
    if (!btn) return;
    btn.addEventListener("click", () => {
      const dark = document.documentElement.dataset.theme !== "cobalt-dark";
      document.documentElement.dataset.theme = dark ? "cobalt-dark" : "cobalt-field";
      btn.setAttribute("aria-pressed", String(dark));
      btn.setAttribute("aria-label", dark ? "切回日间模式" : "切到夜间模式");
    });
  }

  function bind() {
    el.presets.innerHTML = PRESETS.map((text) => `<button type="button" data-ask="${esc(text)}">${esc(text)}</button>`).join("");

    el.composer.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = el.q.value;
      el.q.value = "";
      ask(text);
    });

    document.addEventListener("click", (event) => {
      const askBtn = event.target.closest("[data-ask]");
      if (askBtn) {
        event.preventDefault();
        // 点选项不把选项文字留在输入框：这一问已经回声在对话流里了
        el.q.value = "";
        ask(askBtn.dataset.ask, askBtn.dataset.pick);
        return;
      }
      const slotBtn = event.target.closest("[data-key]");
      if (slotBtn) {
        // 「先确认」卡里的选项：记下这个条件，用原话再问一次，和经典版 data-key 流程一致
        state.slots[slotBtn.dataset.key] = slotBtn.dataset.opt;
        const host = slotBtn.closest("[data-orig]");
        const text = (host && host.dataset.orig) || (state.last && state.last.query) || el.q.value;
        el.q.value = text;
        ask(text);
        return;
      }
      const sum = event.target.closest(".thinksum");
      if (sum) {
        const expanded = sum.getAttribute("aria-expanded") !== "true";
        sum.setAttribute("aria-expanded", String(expanded));
        const steps = sum.nextElementSibling;
        if (steps) steps.hidden = !expanded;
        return;
      }
      const act = event.target.closest("[data-act]");
      if (act) handleAction(act.dataset.act);
      const mat = event.target.closest("[data-mat]");
      if (mat && state.item) {
        const key = `${state.item.id}:${mat.dataset.mat}`;
        if (state.checked.has(key)) state.checked.delete(key); else state.checked.add(key);
        mat.setAttribute("aria-checked", String(state.checked.has(key)));
        const count = $$(".checks li[aria-checked='true']", el.body2).length;
        const total = $$(".checks li", el.body2).length;
        const heading = $(".sec h3", el.body2);
        if (heading) heading.textContent = `要带的东西 · 已备 ${count}/${total}`;
      }
      const tab = event.target.closest("[data-tab]");
      if (tab) {
        state.tab = tab.dataset.tab;
        $$("[data-tab]", el.tabs).forEach((b) => b.setAttribute("aria-selected", String(b === tab)));
        renderIns();
      }
    });

    el.clear.addEventListener("click", () => resetToHero());

    el.back.addEventListener("click", () => {
      // 优先走浏览器历史，返回后地址栏也回到进入时的样子；没有历史就直接复位
      if (state.pushed) { state.pushed = false; history.back(); return; }
      resetToHero();
    });
    window.addEventListener("popstate", () => { state.pushed = false; resetToHero(); });

    el.copy.addEventListener("click", () => handleAction("copy"));
    el.print.addEventListener("click", () => window.print());

    // 二期面板：入口按钮、用途筛选、地点选点（面板内的表单在下面的 submit 里）
    // 入口按标签限定成 button/a：曾经写成 closest("[data-panel]")，于是面板里点「地点名」「用途」
    // 时先命中 body 上的同名属性，被当成重新打开口令，选点和筛选一次都没生效。
    document.addEventListener("click", (event) => {
      const entry = event.target.closest("button[data-panel], a[data-panel]");
      if (entry) {
        // 答案卡上的数据表链接自带那句话：不换掉旧输入，打开的还是上一次检索的词。
        // 面板外壳里写着旧词，得逼 openPanel 重画一次，搜索框才对得上。
        const preset = entry.dataset.query;
        if (preset != null && preset !== state.searchQuery) {
          state.searchQuery = preset;
          delete el.panel.dataset.kind;
        }
        openPanel(entry.dataset.panel);
        return;
      }
      const chip = event.target.closest("[data-purpose]");
      if (chip) { state.contactPurpose = chip.dataset.purpose; contactPanel(); return; }
      const pin = event.target.closest("[data-poi]");
      if (pin) { state.mapPick = pin.dataset.poi; mapPanel(); }
    });
    el.panclose.addEventListener("click", closePanel);
    el.scrim.addEventListener("click", closePanel);
    el.panel.addEventListener("submit", (event) => {
      event.preventDefault();
      const kind = event.target.dataset.panelForm;
      const input = event.target.querySelector("input");
      const value = input ? input.value : "";
      if (kind === "search") { state.searchQuery = value; searchPanel(); }
      if (kind === "map") { state.mapQuery = value; state.mapPick = null; mapPanel(); }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== " " && event.key !== "Enter") return;
      // 输入框里的 Enter 归提交管，不能让下面的清单勾选抢走
      if (event.target === el.q) return;
      const mat = event.target.closest("[data-mat]");
      if (!mat) return;
      event.preventDefault();
      mat.click();
    });

    // 面板打开时：Esc 关闭，Tab 圈在面板里，不要把焦点跑到背后的问答上
    document.addEventListener("keydown", (event) => {
      if (el.panel.hidden) return;
      if (event.key === "Escape") { closePanel(); return; }
      if (event.key !== "Tab") return;
      const stops = $$('button:not([disabled]), input:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])', el.panel);
      if (!stops.length) return;
      const first = stops[0];
      const last = stops[stops.length - 1];
      const inside = el.panel.contains(document.activeElement);
      if (event.shiftKey && (document.activeElement === first || !inside)) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !inside)) { event.preventDefault(); first.focus(); }
    });

    // 与经典版一致：Enter 提交、Shift+Enter 换行；提交走表单那条路，保证清空输入框的逻辑只有一份
    el.q.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.shiftKey) return;
      event.preventDefault();
      if (el.composer.requestSubmit) el.composer.requestSubmit();
      else el.composer.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    });

    el.q.addEventListener("input", () => {
      el.q.style.height = "auto";
      el.q.style.height = Math.min(el.q.scrollHeight, window.innerHeight * 0.22) + "px";
    });

    window.addEventListener("scroll", scheduleMotion, { passive: true });
    window.addEventListener("scroll", () => syncBarHide(), { passive: true });
    window.addEventListener("resize", scheduleMotion);
    initSheetDrag();
    initThemeSwitch();
  }

  function handleAction(act) {
    if (act === "quotes") { state.tab = "quotes"; syncTabs(); renderIns(); }
    if (act === "material") { state.tab = "material"; syncTabs(); renderIns(); }
    if (act === "copy") copyAnswer();
  }

  function syncTabs() {
    $$("[data-tab]", el.tabs).forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === state.tab)));
  }

  function plainAnswer() {
    const d = state.last || {};
    const item = d.item || {};
    const lines = [];
    lines.push(`校园办事向导 · ${docName(item.title) || d.normalized || ""}`);
    if (item.location) lines.push(`地点：${item.location}`);
    if (item.fee) lines.push(`费用：${item.fee}`);
    for (const part of d.answers || []) {
      lines.push("", `【${part.label || "答复"}】`);
      if (part.found === false) lines.push("官方页面没有写这一项");
      else if (part.text) lines.push(part.text);
      for (const step of part.steps || []) lines.push("- " + (typeof step === "string" ? step : step.what || ""));
      for (const line of part.lines || []) lines.push("- " + line);
    }
    const mats = ((state.deliver || item).materials || []).map((m) => (typeof m === "string" ? m : m.name));
    if (mats.length) lines.push("", "要带的材料：", ...mats.map((m) => "- " + m));
    if (d.note) lines.push("", `说明：${d.note}`);
    const quotes = (d.quotes || []).filter((q) => q && q.quote).slice(0, 5);
    if (quotes.length) lines.push("", "官方原文：", ...quotes.map((q) => `- ${q.quote}（${q.label || q.src || "原文"}）`));
    const srcs = sourceLinks(item);
    if (srcs.length) lines.push("", "官方来源：", ...srcs.map((s) => `- ${s.title || s.url}：${s.url}`));
    return lines.join("\n");
  }

  function copyAnswer() {
    if (!state.last) { toast("先问一件事，再复制"); return; }
    copyText(plainAnswer(), "答案已复制，可带走");
  }

  /* ---------- 启动 ---------- */
  async function loadMeta() {
    try {
      const health = await api("/api/health");
      el.statline.textContent = `${num(health.items)} 事项 / ${num(health.verified)} 已核验 / ${num(health.sources)} 份原文`;
      el.statline.title = `事项库更新于 ${health.data_updated || "未知"}；原文库 ${num(health.vector_chunks)} 段`;
      if (!health.key_configured) {
        el.llm.disabled = true;
        el.llm.checked = false;
        el.llmwrap.classList.add("is-off");
        el.llmwrap.title = "未配置模型密钥，模型裁决不可用";
        el.llmrisk.textContent = "不可用";
      } else {
        el.llmrisk.textContent = "含模型生成";
      }
    } catch (error) {
      el.statline.textContent = "本地服务未连接";
    }
    try {
      const data = await api("/api/campus?limit=500");
      state.campus = data;
      buildPlaces(data.pois);
    } catch (error) { /* 地点表失败只影响链接化与地图面板，不影响问答 */ }
  }

  installReel();
  bind();
  renderIns();
  updateStamp();
  loadMeta();

  const presetQuery = new URLSearchParams(window.location.search).get("q");
  if (presetQuery) ask(presetQuery);
})();
