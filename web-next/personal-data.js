/* ============================================================
   校园办事向导 / web-next/personal-data.js
   个人数据查询：默认关闭，显式授权，只读本人数据。
   页面本身不请求任何校园系统；页内模式由本机浏览器组件完成读取。
   ============================================================ */
(function () {
  "use strict";

  const EXT_ID = "gonnbphpnoobkjgcancajjjkgldilocm";
  const EXT_ORIGIN = "chrome-extension://" + EXT_ID;
  const EXT_PANEL = EXT_ORIGIN + "/panel.html";
  const READY_TIMEOUT = 2600;

  const CARD_URL = "https://pcard.cuc.edu.cn/servicehall/ykt/query?code=5";
  const COURSES_URL = "https://courses.cuc.edu.cn/user/index";

  const state = {
    enabled: false,
    mode: null,
    panelOpen: false,
    iframe: null,
    ready: false,
    readyTimer: 0,
    flashTimer: 0,
    lastMode: null,
  };

  let bar = null;
  let panel = null;
  let panelBody = null;
  let dialog = null;
  let confirmBtn = null;
  let cancelBtn = null;
  let openBtn = null;

  function node(html) {
    const tpl = document.createElement("template");
    tpl.innerHTML = html.trim();
    return tpl.content.firstElementChild;
  }

  function flash(text) {
    if (!bar) return;
    const box = bar.querySelector('[data-pd="flash"]');
    if (!box) return;
    box.textContent = text;
    box.dataset.show = "true";
    clearTimeout(state.flashTimer);
    state.flashTimer = setTimeout(() => { box.dataset.show = "false"; }, 2400);
  }

  function buildBar() {
    const rail = document.querySelector(".rail");
    const topbar = rail && rail.querySelector(".topbar");
    if (!rail || !topbar) return;

    bar = node(`
      <div class="pd-bar" data-on="false" role="region" aria-label="个人数据查询">
        <div class="pd-id">
          <span class="pd-lamp" aria-hidden="true"></span>
          <b class="pd-title">个人数据查询（默认关闭）</b>
          <span class="pd-sub">只查本人 · 数据不离开本机</span>
          <span class="pd-flash" data-pd="flash" role="status" aria-live="polite"></span>
        </div>
        <div class="pd-acts" data-pd="acts"></div>
      </div>
    `);
    topbar.insertAdjacentElement("afterend", bar);

    panel = node(`
      <section class="pd-panel" hidden aria-label="个人数据查询面板">
        <div class="pd-panelhead">
          <span class="pd-paneltitle" data-pd="panel-title"></span>
          <button type="button" class="pd-mini" data-pd="collapse">收起</button>
        </div>
        <div class="pd-panelbody" data-pd="panel-body"></div>
      </section>
    `);
    bar.insertAdjacentElement("afterend", panel);
    panelBody = panel.querySelector('[data-pd="panel-body"]');

    bar.addEventListener("click", onBarClick);
    panel.querySelector('[data-pd="collapse"]').addEventListener("click", () => setPanel(false));
  }

  function onBarClick(event) {
    const act = event.target.closest("[data-pd]");
    if (!act || !bar.contains(act)) return;
    const name = act.dataset.pd;
    if (name === "open") openDialog();
    else if (name === "toggle") setPanel(!state.panelOpen);
    else if (name === "clear") clearData();
    else if (name === "close") turnOff();
  }

  function render() {
    if (!bar) return;
    bar.dataset.on = String(state.enabled);
    bar.querySelector(".pd-title").textContent =
      state.enabled ? "个人数据查询（已开启）" : "个人数据查询（默认关闭）";
    bar.querySelector(".pd-sub").textContent =
      !state.enabled ? "只查本人 · 数据不离开本机"
      : state.mode === "official" ? "官方页面查询 · 页内不显示明细"
      : "页内查询 · 关闭即清空";

    const acts = bar.querySelector('[data-pd="acts"]');
    acts.innerHTML = state.enabled
      ? `<button type="button" class="pd-btn" data-pd="toggle">${state.panelOpen ? "收起" : "展开"}</button>
         <button type="button" class="pd-btn" data-pd="clear">清除本次数据</button>
         <button type="button" class="pd-btn pd-strong" data-pd="close">关闭</button>`
      : `<button type="button" class="pd-btn pd-strong" data-pd="open">了解并开启</button>`;
    openBtn = bar.querySelector('[data-pd="open"]');
  }

  function buildDialog() {
    dialog = node(`
      <dialog class="pd-dialog" aria-labelledby="pd-dtitle" aria-describedby="pd-ddesc">
        <div class="pd-dlg">
          <p class="pd-kicker">个人数据查询 · 默认关闭</p>
          <h2 id="pd-dtitle">开启前，请先看这五条</h2>
          <p class="pd-desc" id="pd-ddesc">开启后不会自动查询。每次都要你自己点「查询」，只读取你本人的数据。</p>

          <ul class="pd-facts">
            <li>只读取你本人校园卡的余额、有效期、近 7 天流水，以及畅课里你自己的课程、课表、待办、学期。</li>
            <li>数据只在当前页面的内存里显示，不上传、不写日志、不发给第三方。</li>
            <li>不读取服务大厅里的个人信息。该账户未开通，登录会提示账号不存在。</li>
            <li>使用你自己的登录状态。向导不保存账号、密码、Cookie 或会话参数。</li>
            <li>随时可以关闭。关闭后立即停止查询，并清空已经加载的数据。</li>
          </ul>

          <fieldset class="pd-modes">
            <legend>选择一种查询方式</legend>
            <label class="pd-mode">
              <input type="radio" name="pd-mode" value="embed">
              <span class="pd-modebody">
                <b>页内查询</b>
                <span>需要先在本机浏览器安装一次组件。组件在你的浏览器里读取，再把结果嵌到本页，向导服务器不接触数据。换部署地址、换设备，只要装了同一组件就能用。</span>
              </span>
            </label>
            <label class="pd-mode">
              <input type="radio" name="pd-mode" value="official">
              <span class="pd-modebody">
                <b>官方页面查询</b>
                <span>不装任何东西。点开后到官方系统里自己查，向导页内不显示明细。手机、公共电脑，或不能装组件时用这个。</span>
              </span>
            </label>
          </fieldset>

          <p class="pd-risk">页内查询会在本机读取你本人的校园卡和课程数据。请在私人设备上使用，用完点「关闭」。</p>

          <div class="pd-dlgbtns">
            <button type="button" class="pd-btn pd-cancel" data-pd="dialog-cancel">取消</button>
            <button type="button" class="pd-btn pd-strong" data-pd="dialog-ok" disabled>我已了解，开启</button>
          </div>
        </div>
      </dialog>
    `);
    document.body.append(dialog);
    confirmBtn = dialog.querySelector('[data-pd="dialog-ok"]');
    cancelBtn = dialog.querySelector('[data-pd="dialog-cancel"]');

    dialog.querySelectorAll('input[name="pd-mode"]').forEach((input) => {
      input.addEventListener("change", () => { confirmBtn.disabled = false; });
    });
    cancelBtn.addEventListener("click", closeDialog);
    confirmBtn.addEventListener("click", confirmDialog);
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeDialog();
    });
    dialog.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      closeDialog();
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) closeDialog();
    });
  }

  function openDialog() {
    if (state.enabled) return;
    if (!dialog) buildDialog();
    dialog.querySelectorAll('input[name="pd-mode"]').forEach((input) => {
      input.checked = state.lastMode ? input.value === state.lastMode : false;
    });
    confirmBtn.disabled = !state.lastMode;
    dialog.showModal();
    cancelBtn.focus({ preventScroll: true });
    dialog.scrollTop = 0;
  }

  function closeDialog() {
    if (!dialog || !dialog.open) return;
    dialog.close();
    if (openBtn) openBtn.focus();
  }

  function confirmDialog() {
    const picked = dialog.querySelector('input[name="pd-mode"]:checked');
    if (!picked) return;
    state.enabled = true;
    state.mode = picked.value;
    state.lastMode = picked.value;
    dialog.close();

    setPanel(true);
    if (state.mode === "embed") mountFrame();
    else renderOfficial();
    render();
    flash("已开启，查询由你手动发起");
    const first = panel.querySelector(".pd-mini");
    if (first) first.focus();
  }

  function setPanel(open) {
    if (!state.enabled) open = false;
    state.panelOpen = open;
    if (panel) panel.hidden = !open;
    if (panel) {
      const title = panel.querySelector('[data-pd="panel-title"]');
      if (title) {
        title.textContent = state.mode === "official"
          ? "校园卡与畅课 · 官方入口"
          : "校园卡与畅课 · 本机组件读取";
      }
    }
    if (bar) {
      bar.querySelectorAll('[data-pd="toggle"]').forEach((btn) => {
        btn.textContent = open ? "收起" : "展开";
      });
    }
  }

  function removeFrame() {
    clearTimeout(state.readyTimer);
    if (state.iframe) {
      state.iframe.remove();
      state.iframe = null;
    }
    state.ready = false;
  }

  function mountFrame() {
    if (!panelBody) return;
    panelBody.innerHTML = "";
    removeFrame();
    state.ready = false;

    const wait = node(`<p class="pd-wait">正在连接本机组件…</p>`);
    const frame = document.createElement("iframe");
    frame.className = "pd-frame";
    frame.title = "个人数据查询面板";
    frame.src = EXT_PANEL;
    frame.setAttribute("referrerpolicy", "no-referrer");
    state.iframe = frame;

    panelBody.append(wait, frame);
    state.readyTimer = setTimeout(() => {
      if (!state.ready) showInstall();
    }, READY_TIMEOUT);
  }

  function officialLinksHtml(compact) {
    return `
      <div class="pd-links${compact ? " pd-links-mini" : ""}">
        <a href="${CARD_URL}" target="_blank" rel="noreferrer">
          <b>校园卡</b><span>余额、有效期、流水</span><i>打开官方页面 ↗</i>
        </a>
        <a href="${COURSES_URL}" target="_blank" rel="noreferrer">
          <b>畅课</b><span>课程、待办、学期、课表</span><i>打开官方页面 ↗</i>
        </a>
      </div>`;
  }

  function showInstall() {
    if (!panelBody) return;
    removeFrame();
    panelBody.innerHTML = `
      <div class="pd-install">
        <p><b>没有检测到本机组件。</b>页内查询需要在你自己的浏览器里装一次组件，向导服务器不参与读取。</p>
        <ol>
          <li><a href="campus-guide-personal-data.zip" download>下载组件包</a>，解压后得到一个 extension 文件夹。也可以直接用项目源码里的 extension 文件夹。</li>
          <li>打开 Edge 扩展页 <code>edge://extensions</code>（Chrome 用 <code>chrome://extensions</code>），打开「开发人员模式」。</li>
          <li>点「加载解压缩的扩展」，选择解压出来的 extension 文件夹。</li>
          <li>回到本页刷新，重新开启个人数据查询，就能页内查询。</li>
        </ol>
        <p class="pd-installfoot">换设备或换部署地址，装同一个组件包即可，向导地址不固定。已经装过还是连不上，先确认组件处于启用状态，或改用官方页面查询。</p>
        ${officialLinksHtml(true)}
      </div>`;
  }

  function renderOfficial() {
    if (!panelBody) return;
    removeFrame();
    panelBody.innerHTML = `
      <div class="pd-official">
        <p class="pd-officialnote">向导页内不读取、不显示明细。点下面任一入口，用你自己的账号在官方系统里查。</p>
        ${officialLinksHtml(false)}
        <p class="pd-officialnote">这两个入口只是跳转。换设备、换部署地址都能用。</p>
      </div>`;
  }

  function clearData() {
    if (!state.enabled) return;
    if (state.iframe && state.ready) {
      try {
        state.iframe.contentWindow.postMessage({ type: "pd-clear" }, EXT_ORIGIN);
      } catch (e) { /* 组件已卸载时没有可清的数据 */ }
    }
    flash("本次数据已清除");
  }

  function resetAll() {
    removeFrame();
    if (panelBody) panelBody.innerHTML = "";
    if (panel) panel.hidden = true;
    state.enabled = false;
    state.mode = null;
    state.panelOpen = false;
    render();
  }

  function turnOff() {
    resetAll();
    flash("已关闭，本次数据已丢弃");
    if (openBtn) openBtn.focus();
  }

  window.addEventListener("message", (event) => {
    if (!state.iframe || event.source !== state.iframe.contentWindow) return;
    const data = event.data;
    if (!data || data.type !== "pd-embed-ready") return;
    state.ready = true;
    clearTimeout(state.readyTimer);
    const wait = panelBody && panelBody.querySelector(".pd-wait");
    if (wait) wait.remove();
  });

  window.addEventListener("pagehide", resetAll);

  function boot() {
    buildBar();
    render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
