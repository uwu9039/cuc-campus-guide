from pathlib import Path
from string import Template


ROOT = Path(__file__).resolve().parent

BASE_CSS = r"""
:root {
  --bg: #f4f4f0;
  --surface: #ffffff;
  --ink: #171918;
  --muted: #626762;
  --accent: #175c4c;
  --accent-ink: #ffffff;
  --line: #d9ddd7;
  --radius: 18px;
  --shadow: 0 16px 45px rgba(20, 30, 24, .08);
  --display: inherit;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  min-width: 320px;
  overflow-x: hidden;
  background: var(--bg);
  color: var(--ink);
  font-family: Inter, "Segoe UI", "Microsoft YaHei", sans-serif;
  line-height: 1.6;
}
button, input { font: inherit; }
button, a, input, summary { -webkit-tap-highlight-color: transparent; }
a { color: inherit; }
button { cursor: pointer; }
.skip-link {
  position: fixed;
  left: 16px;
  top: -80px;
  z-index: 100;
  padding: 10px 16px;
  background: var(--ink);
  color: var(--bg);
}
.skip-link:focus { top: 16px; }
.ambient { position: fixed; inset: 0; pointer-events: none; overflow: hidden; }
.topbar {
  position: relative;
  z-index: 5;
  width: min(1240px, calc(100% - 64px));
  margin: 0 auto;
  padding: 26px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.brand { display: flex; align-items: center; gap: 12px; font-weight: 750; text-decoration: none; }
.brand-mark { width: 28px; height: 28px; display: grid; place-items: center; background: var(--accent); color: var(--accent-ink); border-radius: 50%; }
.back-link { font-size: 14px; text-decoration: none; border-bottom: 1px solid currentColor; }
.page {
  position: relative;
  z-index: 2;
  width: min(1180px, calc(100% - 64px));
  margin: 0 auto;
  padding: 58px 0 76px;
}
.intro { max-width: 790px; margin-bottom: 48px; }
.kicker, .answer-kicker {
  margin: 0 0 14px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .16em;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  max-width: 850px;
  font-family: var(--display);
  font-size: clamp(48px, 7vw, 94px);
  line-height: 1.02;
  letter-spacing: -.055em;
}
h1 em { color: var(--accent); font-style: normal; }
.lede { max-width: 620px; margin: 26px 0 0; color: var(--muted); font-size: 17px; }
.style-tag { display: inline-flex; margin-top: 24px; padding: 7px 12px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); font-size: 12px; letter-spacing: .08em; }
.demo { display: grid; gap: 24px; }
.query-panel, .answer { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); }
.query-panel { padding: 26px; }
.query-panel > label { display: block; margin-bottom: 12px; font-size: 14px; font-weight: 750; }
.field-row { display: grid; grid-template-columns: 1fr auto; gap: 12px; }
.field-row input {
  width: 100%;
  min-width: 0;
  padding: 15px 18px;
  border: 1px solid var(--line);
  border-radius: calc(var(--radius) * .65);
  background: var(--bg);
  color: var(--ink);
  outline: none;
}
.primary-button {
  min-height: 52px;
  padding: 0 24px;
  border: 1px solid var(--accent);
  border-radius: calc(var(--radius) * .65);
  background: var(--accent);
  color: var(--accent-ink);
  font-weight: 750;
}
.sample-row { display: flex; flex-wrap: wrap; align-items: center; gap: 9px; margin-top: 14px; color: var(--muted); font-size: 12px; }
.sample-row button { padding: 5px 10px; border: 1px solid var(--line); border-radius: 999px; background: transparent; color: inherit; }
.answer { padding: clamp(24px, 4vw, 44px); }
.answer-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; }
.answer h2 { margin: 0; font-family: var(--display); font-size: clamp(30px, 4vw, 48px); line-height: 1.15; letter-spacing: -.035em; }
.status { flex: 0 0 auto; padding: 6px 11px; border-radius: 999px; background: var(--accent); color: var(--accent-ink); font-size: 12px; font-weight: 800; }
.answer-summary { max-width: 760px; margin: 20px 0 28px; color: var(--muted); }
.answer-grid { display: grid; grid-template-columns: repeat(3, 1fr); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.answer-grid section { padding: 24px 22px; }
.answer-grid section + section { border-left: 1px solid var(--line); }
.answer-grid span { display: block; margin-bottom: 9px; color: var(--accent); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
.answer-grid strong { display: block; font-size: 16px; }
.answer-grid p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
.details-grid { display: grid; grid-template-columns: 1.2fr .8fr; gap: 36px; margin-top: 30px; }
.details-grid h3 { margin: 0 0 14px; font-size: 14px; }
.steps ol { margin: 0; padding-left: 22px; color: var(--muted); }
.steps li + li { margin-top: 9px; }
.material-list { display: grid; gap: 10px; }
.material-list label { display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 14px; }
.material-list input { width: 17px; height: 17px; accent-color: var(--accent); }
.source { margin-top: 28px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }
.source summary { color: var(--ink); cursor: pointer; font-weight: 700; }
.source p { margin-bottom: 0; }
.page-footer { position: relative; z-index: 2; width: min(1180px, calc(100% - 64px)); margin: 0 auto; padding: 22px 0 30px; display: flex; justify-content: space-between; gap: 16px; border-top: 1px solid var(--line); color: var(--muted); font-size: 12px; }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; }
@media (max-width: 720px) {
  .topbar, .page, .page-footer { width: min(100% - 32px, 1180px); }
  .topbar { padding: 18px 0; }
  .brand { font-size: 14px; }
  .page { padding: 34px 0 48px; }
  .intro { margin-bottom: 30px; }
  h1 { font-size: clamp(42px, 14vw, 62px); }
  .lede { font-size: 15px; }
  .query-panel, .answer { padding: 20px; }
  .field-row { grid-template-columns: 1fr; }
  .primary-button { width: 100%; }
  .answer-head { gap: 12px; }
  .answer-grid { grid-template-columns: 1fr; }
  .answer-grid section { padding: 18px 0; }
  .answer-grid section + section { border-left: 0; border-top: 1px solid var(--line); }
  .details-grid { grid-template-columns: 1fr; gap: 24px; }
  .page-footer { flex-direction: column; gap: 4px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; animation: none !important; transition: none !important; }
}
"""

PAGE_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="data:,">
<title>$number $name · 校园办事向导</title>
<style>
$base_css
$theme_css
$apple_css
$field_css
</style>
</head>
<body class="$body_class">
<a class="skip-link" href="#content">跳到主要内容</a>
<div class="ambient" aria-hidden="true"><i></i><b></b><span></span></div>$field_extra
<header class="topbar">
  <a class="brand" href="index.html"><span class="brand-mark">$short</span><span>校园办事向导</span></a>
  <a class="back-link" href="index.html">$total_cn种风格目录</a>
</header>
<main class="page" id="content">
  <section class="intro">
    <p class="kicker">STYLE $number / $english</p>
    <h1>把校园办事，<br><em>说得清楚。</em></h1>
$display_strip
    <p class="lede">同一组办事内容，换一种界面气质。本页用<strong>$name</strong>组织信息，$description。</p>
    <span class="style-tag">$name · $english</span>
  </section>
  <section class="demo" aria-label="校园卡补卡示例">
    <form class="query-panel" id="question-form">
      <label for="question">今天想办什么？</label>
      <div class="field-row">
        <input id="question" name="question" value="校园卡丢了怎么办" autocomplete="off">
        <button class="primary-button" type="submit">查看指引</button>
      </div>
      <div class="sample-row"><span>示例</span><button type="button" data-question="校园卡丢了怎么办">校园卡丢了怎么办</button><button type="button" data-question="校园网怎么报修">校园网怎么报修</button></div>
    </form>
    <article class="answer" id="answer" tabindex="-1">
      <div class="answer-head">
        <div><p class="answer-kicker">推荐办理方式</p><h2>校园卡补卡</h2></div>
        <span class="status">已核验</span>
      </div>
      <p class="answer-summary">到校园生活服务大厅的自助补卡机现场办理，按设备提示操作并支付工本费。</p>
      <div class="answer-grid">
        <section><span>01 / 地点</span><strong>艺术与传播大楼 1 层</strong><p>校园生活服务大厅</p></section>
        <section><span>02 / 费用</span><strong>20 元</strong><p>微信支付</p></section>
        <section><span>03 / 方式</span><strong>自助补卡机</strong><p>本人到场办理</p></section>
      </div>
      <div class="details-grid">
        <section class="steps"><h3>办理步骤</h3><ol><li>到校园生活服务大厅找到自助补卡机。</li><li>按设备提示确认个人信息。</li><li>微信支付工本费，等待补卡机出卡。</li></ol></section>
        <section class="materials"><h3>现场确认</h3><div class="material-list"><label><input type="checkbox">本人到场</label><label><input type="checkbox">在自助补卡机办理</label><label><input type="checkbox">准备微信支付</label></div></section>
      </div>
      <details class="source"><summary>查看官方依据</summary><p>校园卡补卡 · 信息化处　｜　核验日期：2026-10-20</p></details>
    </article>
  </section>
</main>
<footer class="page-footer"><span>校园办事向导 · 风格试验 $number / $total</span><span>仅用于视觉选型</span></footer>
$page_script
</body>
</html>
""")

BASE_SCRIPT = r"""<script>
(function () {
  const form = document.getElementById("question-form");
  const question = document.getElementById("question");
  const answer = document.getElementById("answer");
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    answer.focus();
  });
  document.querySelectorAll("[data-question]").forEach(function (button) {
    button.addEventListener("click", function () {
      question.value = button.dataset.question;
      question.focus();
    });
  });
})();
</script>
"""

APPLE_BASE_CSS = r"""
.apple { --pointer-x: 50%; --pointer-y: 18%; --scroll-shift: 0px; --scroll-progress: 0; }
.apple .ambient::after { content: ""; position: absolute; inset: 0; background: radial-gradient(44vw 44vw at var(--pointer-x) var(--pointer-y), var(--pointer-glow), transparent 62%); }
.apple::before { translate: 0 calc(var(--scroll-shift) * .3); }
.apple .ambient i { translate: 0 calc(var(--scroll-shift) * -.55); rotate: calc(var(--scroll-progress) * -7deg); }
.apple .ambient b { translate: 0 calc(var(--scroll-shift) * 1); rotate: calc(var(--scroll-progress) * 9deg); }
.apple .ambient span { translate: 0 calc(var(--scroll-shift) * 1.7); }
.apple .query-panel, .apple .answer {
  backdrop-filter: blur(28px) saturate(155%);
  -webkit-backdrop-filter: blur(28px) saturate(155%);
  transition: transform .45s cubic-bezier(.2,.8,.2,1), border-color .3s ease, box-shadow .45s ease;
}
.apple .query-panel:focus-within { transform: translateY(-3px); }
.apple .field-row input, .apple .primary-button, .apple .sample-row button { transition: border-color .25s ease, box-shadow .25s ease, transform .25s ease, background .25s ease; }
.apple .primary-button:hover { transform: translateY(-2px); }
.apple .primary-button:active { transform: translateY(0) scale(.985); }
.apple .sample-row button:hover { transform: translateY(-1px); }
.apple .answer.is-revealed { animation: apple-answer-in .72s cubic-bezier(.16,1,.3,1) both; }
.apple .answer.is-revealed .answer-grid section { animation: apple-card-in .64s cubic-bezier(.16,1,.3,1) both; }
.apple .answer.is-revealed .answer-grid section:nth-child(2) { animation-delay: .07s; }
.apple .answer.is-revealed .answer-grid section:nth-child(3) { animation-delay: .14s; }
@keyframes apple-answer-in { from { opacity: .35; transform: translateY(18px) scale(.99); } to { opacity: 1; transform: none; } }
@keyframes apple-card-in { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
@media (max-width: 900px) {
  .apple .demo { grid-template-columns: 1fr; }
  .apple .query-panel { position: static; }
}
@media (max-width: 720px) {
  .apple .query-panel:focus-within { transform: none; }
  .apple .answer-grid section { padding: 20px 4px; }
}
"""

APPLE_SCRIPT = r"""
<script>
(function () {
  const form = document.getElementById("question-form");
  const question = document.getElementById("question");
  const answer = document.getElementById("answer");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let ticking = false;
  let pointerX = window.innerWidth / 2;
  let pointerY = window.innerHeight * 0.18;
  let scrollProgress = 0;

  function update() {
    document.body.style.setProperty("--pointer-x", pointerX + "px");
    document.body.style.setProperty("--pointer-y", pointerY + "px");
    document.body.style.setProperty("--scroll-shift", (scrollProgress * 100).toFixed(2) + "px");
    document.body.style.setProperty("--scroll-progress", scrollProgress.toFixed(4));
    ticking = false;
  }

  function schedule() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(update);
    }
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    answer.classList.remove("is-revealed");
    void answer.offsetWidth;
    answer.classList.add("is-revealed");
    answer.focus({ preventScroll: true });
  });

  document.querySelectorAll("[data-question]").forEach(function (button) {
    button.addEventListener("click", function () {
      question.value = button.dataset.question;
      question.focus();
    });
  });

  window.addEventListener("pointermove", function (event) {
    if (reducedMotion.matches) return;
    pointerX = event.clientX;
    pointerY = event.clientY;
    schedule();
  }, { passive: true });

  window.addEventListener("scroll", function () {
    if (reducedMotion.matches) return;
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    scrollProgress = scrollable > 0 ? Math.min(window.scrollY / scrollable, 1) : 0;
    schedule();
  }, { passive: true });
})();
</script>
"""

FIELD_BASE_CSS = r"""
.field { --scroll-shift: 0px; --scroll-progress: 0; }
.field .ambient { opacity: .26; }
.field .ambient i { translate: 0 calc(var(--scroll-shift) * -.45); rotate: calc(var(--scroll-progress) * 7deg); background: var(--accent); border-radius: 50%; }
.field .ambient i::before { content: ""; position: absolute; left: 58%; top: 62%; width: 46%; height: 46%; background: var(--accent); border-radius: 50%; }
.field .ambient b { translate: 0 calc(var(--scroll-shift) * .95); rotate: calc(var(--scroll-progress) * -9deg); background: var(--accent); border-radius: 50%; }
.field .ambient b::after { content: ""; position: absolute; left: -34%; top: 52%; width: 58%; height: 58%; background: var(--accent); border-radius: 50%; }
.field .ambient span { translate: 0 calc(var(--scroll-shift) * 1.2); background: var(--accent); border-radius: 50%; }
.field .fx { translate: 0 calc(var(--scroll-shift) * 1.55); }
.field .page { padding-top: 108px; }
.field .page-footer { padding-bottom: 96px; }
.field .topbar { position: fixed; left: 22px; top: 22px; width: auto; margin: 0; z-index: 6; padding: 12px 20px; background: #111111; color: #ffffff; border-radius: 999px; }
.field .back-link { border: 0; }
.field .query-panel, .field .answer { border: 0; box-shadow: none; }
.field h1 { max-width: none; margin-left: clamp(-46px, -3.4vw, -10px); font-size: clamp(58px, 11.5vw, 152px); line-height: 1.05; font-weight: 800; text-transform: uppercase; }
.field h1 em { display: inline-block; line-height: 1; padding: 0 .06em .05em; background: var(--accent); color: var(--accent-ink); }
.field .rotate { overflow: hidden; height: clamp(56px, 8.6vw, 124px); margin: 4px 0 0 clamp(-46px, -3.4vw, -10px); }
.field .rotate-inner { display: grid; animation: field-reel @REEL_DURATION@s cubic-bezier(.76,0,.24,1) infinite; }
.field .rotate span { display: grid; align-items: center; height: clamp(56px, 8.6vw, 124px); font-family: var(--display); font-size: clamp(46px, 7.2vw, 106px); font-weight: 800; line-height: 1; letter-spacing: -.02em; text-transform: uppercase; white-space: nowrap; color: var(--ink); }
.field .rotate span:nth-child(even) { color: transparent; -webkit-text-stroke: 2px var(--ink); }
.field .kicker, .field .answer-kicker { color: var(--ink); letter-spacing: .26em; }
.field .style-tag { background: var(--accent); color: var(--accent-ink); border: 0; font-weight: 700; }
.field .field-row input { background: #ffffff; border-color: #e3e3de; }
.field .primary-button { border: 0; background: var(--accent); color: var(--accent-ink); border-radius: 999px; padding: 0 32px; font-weight: 800; }
.field .sample-row button { border: 0; background: #efefec; color: var(--ink); }
.field .status { background: var(--accent); color: var(--accent-ink); }
.field .answer-grid { border: 0; gap: 14px; }
.field .answer-grid section { border-radius: 18px; background: #ffffff; }
.field .answer-grid section + section { border-left: 0; }
.field .answer-grid span { color: var(--ink); letter-spacing: .18em; }
.field .source, .field .page-footer { border-color: #e3e3de; }
.field .answer.is-revealed { animation: field-land .48s cubic-bezier(.2,.8,.2,1) both; }
@REEL_KEYFRAMES@
@keyframes field-land { from { opacity: .3; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@media (max-width: 900px) {
  .field .demo { grid-template-columns: 1fr; }
  .field .query-panel { position: static; }
}
@media (max-width: 720px) {
  .field h1 { margin-left: 0; font-size: clamp(40px, 13vw, 64px); }
  .field .rotate { margin-left: 0; height: 44px; }
  .field .rotate span { height: 44px; font-size: 38px; }
  .field .page { padding-top: 88px; }
  .field .topbar { left: 14px; top: 14px; padding: 10px 16px; }
}
"""

REEL_SECONDS_PER_ROW = 2.5
FIELD_WORDS = [
    "CUC", "CARD REISSUE", "ONE ASK", "CUC", "LOCATION",
    "CARD KIOSK", "CUC", "ONE VISIT", "WECHAT PAY", "VERIFIED",
]


def field_reel_rows():
    return FIELD_WORDS + FIELD_WORDS[:1]


def field_reel_shift(percent):
    return "transform: translateY(0)" if not percent else f"transform: translateY(-{percent:.2f}%)"


def field_reel_keyframes():
    rows = field_reel_rows()
    slots = len(rows) - 1
    step = 100 / slots
    lines = []
    for index in range(slots):
        start = index * step
        end = start + step * .64
        lines.append(f"  {start:.2f}%, {end:.2f}% {{ {field_reel_shift(index * 100 / len(rows))} }}")
    lines.append(f"  100% {{ {field_reel_shift(slots * 100 / len(rows))} }}")
    return "@keyframes field-reel {\n" + "\n".join(lines) + "\n}"


FIELD_STRIP = (
    '<div class="rotate" aria-hidden="true"><div class="rotate-inner">'
    + "".join(f"<span>{word}</span>" for word in field_reel_rows())
    + "</div></div>"
)

FIELD_BASE_CSS = (FIELD_BASE_CSS
                  .replace("@REEL_DURATION@", f"{REEL_SECONDS_PER_ROW * len(FIELD_WORDS):g}")
                  .replace("@REEL_KEYFRAMES@", field_reel_keyframes()))

FIELD_EXTRA = (
    '<div class="fx" aria-hidden="true">'
    '<i style="--h: 26%; --d: 0s"></i><i style="--h: 48%; --d: -.14s"></i>'
    '<i style="--h: 34%; --d: -.28s"></i><i style="--h: 62%; --d: -.42s"></i>'
    '<i style="--h: 40%; --d: -.56s"></i><i style="--h: 72%; --d: -.7s"></i>'
    '<i style="--h: 52%; --d: -.84s"></i><i style="--h: 86%; --d: -.98s"></i>'
    '<i style="--h: 44%; --d: -1.12s"></i><i style="--h: 66%; --d: -1.26s"></i>'
    '<i style="--h: 30%; --d: -1.4s"></i><i style="--h: 58%; --d: -1.54s"></i>'
    '<i style="--h: 38%; --d: -1.68s"></i><i style="--h: 74%; --d: -1.82s"></i>'
    "</div>"
)

FIELD_CSS_BODY = r"""
body { background: #ffffff; }
.ambient { z-index: 1; }
.ambient i { position: absolute; left: -4%; top: 3%; width: clamp(240px, 33vw, 520px); aspect-ratio: 1; animation: field-drift-a 19s ease-in-out infinite alternate; }
.ambient b { position: absolute; right: -7%; top: 29%; width: clamp(200px, 25vw, 400px); aspect-ratio: 1; animation: field-drift-b 15s ease-in-out infinite alternate-reverse; }
.ambient span { position: absolute; left: 27%; bottom: -9%; width: clamp(150px, 17vw, 280px); aspect-ratio: 1; animation: field-drift-a 23s ease-in-out infinite alternate-reverse; }
.fx { position: fixed; left: 0; right: 0; bottom: 0; z-index: 1; height: min(30vh, 300px); display: flex; align-items: flex-end; gap: 1.4%; padding: 0 3%; opacity: .5; }
.fx i { flex: 1 1 0; height: var(--h); transform-origin: bottom; border-radius: 999px 999px 0 0; background: var(--accent); animation: field-eq 1.7s ease-in-out infinite alternate; animation-delay: var(--d); }
.page { width: min(1240px, calc(100% - 56px)); }
.intro { max-width: none; margin-bottom: 42px; }
.kicker { font-size: 11px; }
.lede { max-width: 540px; font-size: 18px; }
.demo { grid-template-columns: .92fr 1.08fr; align-items: start; gap: 26px; }
.query-panel { position: sticky; top: 96px; padding: 30px; }
.query-panel > label { font-size: 13px; letter-spacing: .1em; text-transform: uppercase; }
.field-row input { border-radius: 999px; padding: 16px 22px; font-size: 17px; }
.answer { padding: clamp(26px, 3.4vw, 46px); }
.answer h2 { font-size: clamp(34px, 4.6vw, 62px); }
.answer-grid { margin: 0 -7px; }
.answer-grid section { padding: 26px 22px; }
.answer-grid span { font-size: 10px; }
.details-grid { gap: 42px; }
.status { letter-spacing: .1em; font-size: 11px; }
@keyframes field-drift-a { from { transform: scale(.9) translate3d(-3%,-2%,0); } to { transform: scale(1.14) translate3d(6%,7%,0); } }
@keyframes field-drift-b { from { transform: scale(1.08) translate3d(4%,-5%,0); } to { transform: scale(.86) translate3d(-7%,6%,0); } }
@keyframes field-eq { from { transform: scaleY(.26); } to { transform: scaleY(1.55); } }
"""


def field_theme(number, slug, name, english, description, accent, accent_ink, muted):
    return {
        "slug": slug, "name": name, "english": english, "number": number, "field": True,
        "description": description,
        "colors": ["#ffffff", accent, "#111111"],
        "accent": accent, "accent_ink": accent_ink, "muted": muted,
        "display_strip": FIELD_STRIP,
        "field_extra": FIELD_EXTRA,
        "css": (
            ':root { --bg: #ffffff; --surface: #f9f9f9; --ink: #111111; --muted: ' + muted
            + "; --accent: " + accent + "; --accent-ink: " + accent_ink
            + '; --line: #e3e3de; --radius: 24px; --shadow: none; --display: "Arial Narrow", "Helvetica Neue", Impact, "Microsoft YaHei", sans-serif; }'
            + FIELD_CSS_BODY
        ),
    }


FIELD_VARIANTS = [
    ("26", "acid-field", "酸黄场", "ACID FIELD", "用同色实心圆、均衡器与巨型字标搭一版扁平、无玻璃的能量场", "#ffde00", "#111111", "#6d6d6d"),
    ("27", "signal-orange", "信号橙场", "SIGNAL FIELD", "同一套能量场换成信号橙，看强调色在字标和按钮上的分量", "#ff6a00", "#111111", "#5f5f5f"),
    ("28", "alarm-red", "正红场", "RED FIELD", "同一套能量场换成正红，红块压黑字最像告示", "#ff3b30", "#111111", "#5a5a5a"),
    ("29", "volt-lime", "荧光绿场", "LIME FIELD", "同一套能量场换成荧光绿，整页最亮但字还是读得出", "#b6ff2e", "#111111", "#6d6d6d"),
    ("30", "electric-cyan", "电光青场", "CYAN FIELD", "同一套能量场换成电光青，冷色版更靠近数码产品官网", "#00d5ff", "#111111", "#5f5f5f"),
    ("31", "cobalt-blue", "钴蓝场", "COBALT FIELD", "同一套能量场换成钴蓝，深色强调只能配白字", "#2b5bff", "#ffffff", "#5a5a5a"),
    ("32", "hot-magenta", "品红场", "MAGENTA FIELD", "同一套能量场换成品红，最跳的一版，适合活动页", "#ff2e93", "#111111", "#5a5a5a"),
]

THEMES = [
    {
        "slug": "swiss-grid", "name": "瑞士网格", "english": "SWISS GRID", "number": "04",
        "description": "强调严格分栏、非对称留白和高效率阅读",
        "colors": ["#f5f5f2", "#e32b20", "#111111"],
        "css": r"""
:root { --bg: #f5f5f2; --surface: #ffffff; --ink: #111111; --muted: #555555; --accent: #e32b20; --accent-ink: #ffffff; --line: #111111; --radius: 0; --shadow: none; --display: Arial, "Microsoft YaHei", sans-serif; }
body { font-family: Arial, "Microsoft YaHei", sans-serif; background-image: linear-gradient(90deg, transparent calc(100% - 1px), rgba(0,0,0,.06) 1px); background-size: calc(100% / 12) 100%; }
.topbar { border-bottom: 3px solid var(--ink); }
.brand-mark { border-radius: 0; }
.page { display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; }
.intro { grid-column: 1 / 9; margin-bottom: 42px; }
.demo { grid-column: 3 / 13; }
h1 { font-size: clamp(52px, 8vw, 112px); text-transform: uppercase; }
h1 em { display: inline-block; margin-left: 12%; }
.kicker { padding-left: 8px; border-left: 28px solid var(--accent); }
.style-tag { border-radius: 0; border-width: 2px; }
.query-panel { border-width: 3px; }
.field-row input, .primary-button { border-radius: 0; }
.primary-button { text-transform: uppercase; }
.answer { border: 0; border-top: 12px solid var(--ink); }
.status { border-radius: 0; }
.answer-grid { border-width: 2px; }
.source, .page-footer { border-color: var(--ink); }
@media (max-width: 720px) { .page { display: block; } h1 em { margin-left: 0; } }
"""
    },
    {
        "slug": "minimal-mono", "name": "极简黑白", "english": "QUIET MONO", "number": "05",
        "description": "用大量留白、细线和黑白灰建立安静秩序",
        "colors": ["#fafafa", "#111111", "#d8d8d8"],
        "css": r"""
:root { --bg: #fafafa; --surface: #fafafa; --ink: #111111; --muted: #777777; --accent: #111111; --accent-ink: #ffffff; --line: #dedede; --radius: 0; --shadow: none; --display: Georgia, "Songti SC", serif; }
body { font-weight: 400; }
.topbar { padding-top: 36px; }
.brand { font-weight: 500; letter-spacing: .08em; }
.brand-mark { background: transparent; color: var(--ink); border: 1px solid var(--ink); font-size: 11px; }
.page { width: min(980px, calc(100% - 64px)); padding-top: 88px; }
.intro { margin-bottom: 76px; }
h1 { font-weight: 400; letter-spacing: -.065em; }
h1 em { color: var(--ink); -webkit-text-stroke: 1px var(--ink); -webkit-text-fill-color: transparent; }
.lede { max-width: 480px; font-size: 14px; }
.style-tag { border: 0; padding-left: 0; border-radius: 0; }
.query-panel, .answer { border-left: 0; border-right: 0; }
.query-panel { padding: 30px 0; }
.field-row input { background: transparent; border: 0; border-bottom: 1px solid var(--ink); padding-left: 0; }
.primary-button { background: transparent; color: var(--ink); border-color: var(--ink); }
.primary-button:hover { background: var(--ink); color: white; }
.answer { padding: 54px 0; }
.status { background: transparent; color: var(--ink); border: 1px solid var(--ink); font-weight: 400; }
.answer-kicker, .answer-grid span { color: var(--muted); }
.answer-summary { font-size: 14px; }
.source { border-top-style: dashed; }
"""
    },
    {
        "slug": "brutalist", "name": "粗野主义", "english": "NEO BRUTALISM", "number": "06",
        "description": "用粗边框、硬阴影和高饱和色直接撞击视线",
        "colors": ["#fff200", "#ff5c8a", "#111111"],
        "css": r"""
:root { --bg: #fff200; --surface: #ffffff; --ink: #111111; --muted: #333333; --accent: #ff5c8a; --accent-ink: #111111; --line: #111111; --radius: 0; --shadow: 8px 8px 0 #111111; --display: Impact, Arial Black, "Microsoft YaHei", sans-serif; }
body { font-family: Arial Black, "Microsoft YaHei", sans-serif; }
.ambient i { position: absolute; width: 180px; height: 180px; right: 5%; top: 12%; background: #6c63ff; border: 5px solid #111; transform: rotate(18deg); }
.ambient b { position: absolute; width: 110px; height: 110px; left: -20px; bottom: 12%; background: #00d9b5; border: 5px solid #111; border-radius: 50%; }
.topbar { background: #fff; border: 4px solid #111; padding: 16px 20px; margin-top: 20px; box-shadow: 6px 6px 0 #111; }
.brand-mark { border-radius: 0; border: 3px solid #111; }
.back-link { background: #6c63ff; color: white; padding: 6px 10px; border: 3px solid #111; }
h1 { text-transform: uppercase; transform: rotate(-1deg); text-shadow: 4px 4px 0 #fff; }
h1 em { color: #6c63ff; -webkit-text-stroke: 2px #111; }
.style-tag { background: #00d9b5; color: #111; border: 3px solid #111; border-radius: 0; box-shadow: 4px 4px 0 #111; font-weight: 900; }
.query-panel, .answer { border: 4px solid #111; }
.field-row input { border: 3px solid #111; background: #fff; border-radius: 0; }
.primary-button { border: 3px solid #111; box-shadow: 4px 4px 0 #111; text-transform: uppercase; }
.primary-button:active { transform: translate(4px, 4px); box-shadow: none; }
.sample-row button { border: 2px solid #111; background: #fff; color: #111; border-radius: 0; }
.answer { transform: rotate(.35deg); }
.status { border: 3px solid #111; border-radius: 0; background: #00d9b5; color: #111; }
.answer-grid, .answer-grid section + section, .source { border-color: #111; border-width: 2px; }
.material-list input { appearance: none; border: 3px solid #111; background: white; }
.material-list input:checked { background: #ff5c8a; box-shadow: inset 0 0 0 3px white; }
@media (max-width: 720px) { .ambient { display: none; } }
"""
    },
    {
        "slug": "bauhaus", "name": "包豪斯", "english": "BAUHAUS", "number": "07",
        "description": "把圆形、三角和原色转化为明确的功能分区",
        "colors": ["#f1e7d0", "#dc3828", "#2058a8"],
        "css": r"""
:root { --bg: #f1e7d0; --surface: #f8f1e3; --ink: #191919; --muted: #514b42; --accent: #dc3828; --accent-ink: #ffffff; --line: #191919; --radius: 0; --shadow: none; --display: Futura, Century Gothic, "Microsoft YaHei", sans-serif; }
.ambient i { position: absolute; right: -70px; top: 90px; width: 330px; height: 330px; border-radius: 50%; background: #2058a8; }
.ambient b { position: absolute; right: 220px; top: 400px; width: 0; height: 0; border-left: 85px solid transparent; border-right: 85px solid transparent; border-bottom: 150px solid #e6b800; transform: rotate(-16deg); }
.ambient span { position: absolute; left: -60px; bottom: 10%; width: 190px; height: 190px; border-radius: 50% 50% 0 0; background: #dc3828; }
.topbar { border-bottom: 2px solid #191919; }
.brand-mark { border-radius: 50% 50% 0 0; background: #e6b800; color: #191919; }
.page { max-width: 1080px; }
.intro { position: relative; padding-left: 8%; }
h1 { font-weight: 900; text-transform: uppercase; }
h1 em { color: #2058a8; }
.kicker { display: inline-flex; align-items: center; gap: 10px; }
.kicker::before { content: ""; width: 18px; height: 18px; border-radius: 50%; background: #dc3828; }
.style-tag { border: 2px solid #191919; border-radius: 50%; padding: 16px 24px; background: #e6b800; color: #191919; }
.demo { grid-template-columns: .72fr 1.28fr; align-items: start; }
.query-panel { border: 3px solid #191919; background: #2058a8; color: white; }
.query-panel > label { font-size: 20px; }
.field-row { grid-template-columns: 1fr; }
.field-row input { background: #f8f1e3; border: 2px solid #191919; border-radius: 50px; }
.primary-button { background: #e6b800; color: #191919; border: 2px solid #191919; border-radius: 50%; min-height: 92px; }
.sample-row { color: white; }
.sample-row button { border-color: white; color: white; }
.answer { border: 3px solid #191919; }
.status { border-radius: 50%; width: 62px; height: 62px; display: grid; place-items: center; }
.answer-grid section:first-child { border-left: 10px solid #dc3828; }
.answer-grid section:nth-child(2) { border-left: 10px solid #e6b800; }
.answer-grid section:nth-child(3) { border-left: 10px solid #2058a8; }
@media (max-width: 800px) { .demo { grid-template-columns: 1fr; } .primary-button { border-radius: 50px; min-height: 52px; } .ambient { display: none; } }
"""
    },
    {
        "slug": "memphis", "name": "孟菲斯", "english": "MEMPHIS POP", "number": "08",
        "description": "用波浪、彩点和 playful 几何制造轻快节奏",
        "colors": ["#dcd4ff", "#ff6b9d", "#26c6b8"],
        "css": r"""
:root { --bg: #dcd4ff; --surface: #fffdf7; --ink: #29243a; --muted: #625a75; --accent: #ff5f96; --accent-ink: #251e35; --line: #29243a; --radius: 22px; --shadow: 7px 7px 0 #29243a; --display: Trebuchet MS, "Microsoft YaHei", sans-serif; }
body { background-image: radial-gradient(#29243a 1.2px, transparent 1.2px); background-size: 24px 24px; }
.ambient i { position: absolute; top: 130px; right: 4%; width: 150px; height: 48px; border: 9px solid #26c6b8; border-color: #26c6b8 transparent #26c6b8 transparent; border-radius: 50%; transform: rotate(25deg); }
.ambient b { position: absolute; left: 4%; bottom: 12%; width: 90px; height: 90px; background: #ffd84d; clip-path: polygon(50% 0, 62% 35%, 100% 35%, 70% 57%, 82% 100%, 50% 74%, 18% 100%, 30% 57%, 0 35%, 38% 35%); }
.topbar { background: #fffdf7; border: 3px solid #29243a; border-radius: 18px; padding: 14px 20px; margin-top: 18px; }
.brand-mark { background: #26c6b8; color: #29243a; border: 2px solid #29243a; }
h1 { font-weight: 900; letter-spacing: -.04em; }
h1 em { color: #ff5f96; text-shadow: 3px 3px 0 #fffdf7; }
.style-tag { background: #ffd84d; color: #29243a; border: 2px solid #29243a; border-radius: 8px 18px 8px 18px; font-weight: 800; }
.query-panel { background: #26c6b8; border: 3px solid #29243a; }
.field-row input { background: #fffdf7; border: 3px solid #29243a; border-radius: 14px; }
.primary-button { border: 3px solid #29243a; border-radius: 14px; box-shadow: 4px 4px 0 #29243a; }
.sample-row { color: #29243a; }
.sample-row button { border: 2px solid #29243a; background: #fffdf7; color: #29243a; }
.answer { border: 3px solid #29243a; }
.answer-head { align-items: center; }
.status { border: 2px solid #29243a; background: #ffd84d; color: #29243a; border-radius: 8px; transform: rotate(4deg); }
.answer-grid section:nth-child(2) { background: #ffe1ec; }
.answer-grid span { color: #29243a; }
.details-grid h3 { display: inline-block; background: #ffd84d; padding: 3px 9px; transform: rotate(-2deg); }
"""
    },
    {
        "slug": "art-deco", "name": "装饰艺术", "english": "ART DECO", "number": "09",
        "description": "以金色细线、对称框架和华丽比例营造仪式感",
        "colors": ["#111714", "#c7a65a", "#ece1c5"],
        "css": r"""
:root { --bg: #111714; --surface: #17201b; --ink: #ece1c5; --muted: #b8ad94; --accent: #c7a65a; --accent-ink: #111714; --line: #71633e; --radius: 0; --shadow: 0 0 0 5px #17201b, 0 0 0 6px #c7a65a; --display: Didot, Bodoni MT, Georgia, serif; }
body { background-image: repeating-linear-gradient(45deg, transparent 0 34px, rgba(199,166,90,.045) 34px 35px); }
.ambient i, .ambient b { position: absolute; top: 100px; width: 210px; height: 420px; border: 1px solid #71633e; border-radius: 50% 50% 0 0; opacity: .45; }
.ambient i { left: -110px; }
.ambient b { right: -110px; }
.topbar { border-bottom: 1px solid var(--accent); }
.brand { letter-spacing: .16em; text-transform: uppercase; }
.brand-mark { border-radius: 50%; border: 1px solid var(--accent); background: transparent; color: var(--accent); }
.page { max-width: 1000px; }
.intro { text-align: center; margin-left: auto; margin-right: auto; }
.intro::before, .intro::after { content: "◆"; display: inline-block; color: var(--accent); margin: 0 18px 24px; }
h1 { font-weight: 400; letter-spacing: .01em; }
h1 em { color: var(--accent); }
.lede { margin-left: auto; margin-right: auto; }
.style-tag { border-radius: 0; border-left: 0; border-right: 0; letter-spacing: .2em; }
.query-panel, .answer { position: relative; }
.query-panel::before, .answer::before { content: ""; position: absolute; inset: 9px; border: 1px solid var(--line); pointer-events: none; }
.query-panel > label, .field-row, .sample-row { position: relative; }
.query-panel > label { text-align: center; letter-spacing: .16em; }
.field-row input { background: #111714; border-color: var(--accent); border-radius: 0; color: var(--ink); text-align: center; }
.primary-button { border-radius: 0; letter-spacing: .12em; }
.answer-head { text-align: center; flex-direction: column; align-items: center; }
.answer-kicker { letter-spacing: .25em; }
.answer h2 { font-weight: 400; }
.answer h2::after { content: ""; display: block; width: 100px; height: 1px; background: var(--accent); margin: 18px auto; }
.status { border-radius: 0; order: -1; }
.answer-summary { text-align: center; margin-left: auto; margin-right: auto; }
.answer-grid { border-color: var(--accent); }
.details-grid h3 { color: var(--accent); letter-spacing: .12em; }
.source, .page-footer { border-color: var(--accent); }
"""
    },
    {
        "slug": "glassmorphism", "name": "玻璃拟态", "english": "GLASSMORPHISM", "number": "10",
        "description": "让半透明层级漂浮在柔光和渐变背景之上",
        "colors": ["#8b7cf6", "#e7e4ff", "#62d8ff"],
        "css": r"""
:root { --bg: #7771dc; --surface: rgba(255,255,255,.16); --ink: #ffffff; --muted: #e6e4ff; --accent: #a9efff; --accent-ink: #26345f; --line: rgba(255,255,255,.28); --radius: 28px; --shadow: 0 24px 70px rgba(35,24,90,.25); --display: "Segoe UI", "Microsoft YaHei", sans-serif; }
body { background: radial-gradient(circle at 18% 12%, #f29ad4 0, transparent 35%), radial-gradient(circle at 82% 18%, #6ee7f5 0, transparent 32%), linear-gradient(145deg, #6758c8, #8a75df 55%, #4b74c9); min-height: 100vh; }
.ambient i { position: absolute; width: 330px; height: 330px; left: 4%; bottom: 2%; border-radius: 50%; background: linear-gradient(135deg, rgba(255,255,255,.4), rgba(255,255,255,0)); filter: blur(2px); }
.ambient b { position: absolute; width: 210px; height: 210px; right: 7%; top: 18%; background: linear-gradient(145deg, #ffb3d9, #8d7bff); transform: rotate(28deg); border-radius: 48px; opacity: .6; }
.query-panel, .answer { background: var(--surface); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,.38); }
.brand-mark { background: rgba(255,255,255,.25); color: white; border: 1px solid rgba(255,255,255,.4); }
.back-link { border: 1px solid rgba(255,255,255,.45); border-radius: 999px; padding: 6px 13px; }
h1 { text-shadow: 0 4px 25px rgba(41,27,94,.2); }
h1 em { color: #c8f7ff; }
.style-tag { background: rgba(255,255,255,.14); color: white; border-color: rgba(255,255,255,.35); backdrop-filter: blur(12px); }
.field-row input { background: rgba(255,255,255,.16); color: white; border-color: rgba(255,255,255,.4); }
.field-row input::placeholder { color: #eee; }
.primary-button { background: rgba(213,250,255,.85); color: #304071; border-color: rgba(255,255,255,.6); }
.sample-row { color: #f1efff; }
.sample-row button { color: white; border-color: rgba(255,255,255,.35); background: rgba(255,255,255,.1); }
.status { background: rgba(197,255,223,.8); color: #205442; }
.answer-grid section { background: rgba(255,255,255,.06); }
.answer-grid span, .answer-kicker { color: #c8f7ff; }
"""
    },
    {
        "slug": "neumorphism", "name": "新拟态", "english": "SOFT UI", "number": "11",
        "description": "用同色系凹凸和柔软阴影模拟可触摸控件",
        "colors": ["#e3e9f0", "#7b8da6", "#f8fbff"],
        "css": r"""
:root { --bg: #e3e9f0; --surface: #e3e9f0; --ink: #39485d; --muted: #718096; --accent: #667f9f; --accent-ink: #ffffff; --line: transparent; --radius: 28px; --shadow: 12px 12px 26px #b8c2cf, -12px -12px 26px #ffffff; --display: "Segoe UI", "Microsoft YaHei", sans-serif; }
.topbar { padding: 30px 0; }
.brand-mark { background: #e3e9f0; color: #667f9f; box-shadow: inset 3px 3px 6px #c1cbd6, inset -3px -3px 6px #fff; }
.back-link { border: 0; padding: 9px 16px; border-radius: 999px; box-shadow: 5px 5px 12px #c0cad5, -5px -5px 12px #fff; }
.page { max-width: 1020px; }
h1 { font-weight: 750; }
h1 em { color: #667f9f; }
.style-tag { border: 0; background: #e3e9f0; color: #667f9f; box-shadow: inset 4px 4px 9px #c4ced9, inset -4px -4px 9px #fff; }
.query-panel, .answer { border: 0; }
.field-row input { background: #e3e9f0; border: 0; box-shadow: inset 6px 6px 12px #bdc7d2, inset -6px -6px 12px #fff; }
.primary-button { border: 0; background: #e3e9f0; color: #526b8b; box-shadow: 6px 6px 14px #b8c2cf, -6px -6px 14px #fff; }
.primary-button:active { box-shadow: inset 5px 5px 10px #bdc7d2, inset -5px -5px 10px #fff; }
.sample-row button { border: 0; box-shadow: 3px 3px 8px #c0cad5, -3px -3px 8px #fff; color: #667f9f; }
.status { background: #e3e9f0; color: #667f9f; box-shadow: inset 3px 3px 7px #c1cbd6, inset -3px -3px 7px #fff; }
.answer-grid, .answer-grid section + section, .source, .page-footer { border-color: #cbd4de; }
.answer-grid section { margin: 12px; border-radius: 18px; box-shadow: inset 4px 4px 9px #c4ced9, inset -4px -4px 9px #fff; }
.answer-grid section + section { border-left: 0; }
.answer-grid span, .answer-kicker { color: #667f9f; }
.material-list input { appearance: none; border-radius: 6px; background: #e3e9f0; box-shadow: inset 2px 2px 5px #bdc7d2, inset -2px -2px 5px #fff; }
.material-list input:checked { background: #7b8da6; }
@media (max-width: 720px) { .answer-grid section + section { border-top: 0; } }
"""
    },
    {
        "slug": "retro-terminal", "name": "复古终端", "english": "RETRO TERMINAL", "number": "12",
        "description": "模拟 CRT 屏幕、命令行和绿色磷光字符",
        "colors": ["#07110b", "#6cff8f", "#1c4128"],
        "css": r"""
:root { --bg: #07110b; --surface: rgba(5,20,11,.88); --ink: #b8ffc9; --muted: #70b982; --accent: #6cff8f; --accent-ink: #07110b; --line: #1c5a2d; --radius: 3px; --shadow: 0 0 24px rgba(75,255,126,.08); --display: Consolas, Courier New, monospace; }
body { font-family: Consolas, Courier New, monospace; background-image: linear-gradient(rgba(108,255,143,.025) 50%, rgba(0,0,0,.12) 50%); background-size: 100% 4px; }
body::after { content: ""; position: fixed; inset: 0; pointer-events: none; background: radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.55)); z-index: 10; }
.topbar, .page, .page-footer { z-index: 11; }
.brand-mark { border-radius: 0; }
.brand::after { content: "_"; color: var(--accent); animation: blink 1s steps(1) infinite; }
@keyframes blink { 50% { opacity: 0; } }
.page { max-width: 1040px; }
.kicker::before { content: "> "; }
h1 { font-size: clamp(38px, 6vw, 76px); font-weight: 400; letter-spacing: -.06em; text-shadow: 0 0 12px rgba(108,255,143,.5); }
h1 em { color: var(--accent); }
h1 em::before { content: "[ "; color: var(--muted); }
h1 em::after { content: " ]"; color: var(--muted); }
.style-tag { border-radius: 0; }
.query-panel::before { content: "C:\\CAMPUS\\ASK.EXE"; display: block; margin: -26px -26px 24px; padding: 7px 12px; background: #6cff8f; color: #07110b; font-size: 12px; }
.query-panel > label::before { content: "INPUT > "; color: var(--accent); }
.field-row input { background: #020905; border-radius: 0; color: #6cff8f; font-family: inherit; }
.primary-button { border-radius: 0; }
.primary-button::before { content: "[RUN] "; }
.sample-row button { border-radius: 0; }
.answer { position: relative; }
.answer::before { content: "RESPONSE // VERIFIED"; display: block; margin-bottom: 20px; color: #6cff8f; font-size: 11px; }
.status { border-radius: 0; }
.answer-grid span::before { content: ":: "; }
.steps ol { list-style: none; padding: 0; counter-reset: terminal; }
.steps li { counter-increment: terminal; }
.steps li::before { content: "0" counter(terminal) " > "; color: #6cff8f; }
.source summary::before { content: "+ "; color: #6cff8f; }
"""
    },
    {
        "slug": "pixel-arcade", "name": "像素游戏", "english": "PIXEL ARCADE", "number": "13",
        "description": "把办理流程变成带血条、像素按钮的关卡界面",
        "colors": ["#24245a", "#ffcf3f", "#4de68a"],
        "css": r"""
:root { --bg: #24245a; --surface: #fff4cf; --ink: #25213c; --muted: #62566b; --accent: #ffcf3f; --accent-ink: #25213c; --line: #25213c; --radius: 0; --shadow: 0 8px 0 #151537; --display: "Courier New", "Microsoft YaHei", monospace; }
body { font-family: "Courier New", "Microsoft YaHei", monospace; background-image: linear-gradient(45deg, rgba(255,255,255,.035) 25%, transparent 25%, transparent 75%, rgba(255,255,255,.035) 75%), linear-gradient(45deg, rgba(255,255,255,.035) 25%, transparent 25%, transparent 75%, rgba(255,255,255,.035) 75%); background-position: 0 0, 8px 8px; background-size: 16px 16px; }
.ambient i { position: absolute; top: 120px; right: 8%; width: 72px; height: 72px; background: #4de68a; clip-path: polygon(25% 0,75% 0,75% 12%,88% 12%,88% 25%,100% 25%,100% 75%,88% 75%,88% 88%,75% 88%,75% 100%,25% 100%,25% 88%,12% 88%,12% 75%,0 75%,0 25%,12% 25%,12% 12%,25% 12%); box-shadow: 12px 12px 0 #151537; }
.topbar { background: #ff6b6b; color: #25213c; border: 4px solid #25213c; padding: 14px 18px; margin-top: 18px; box-shadow: 0 6px 0 #151537; }
.brand-mark { border-radius: 0; border: 3px solid #25213c; }
.page { max-width: 1040px; }
.intro { color: #fff4cf; }
.kicker { color: #ffcf3f; }
h1 { font-weight: 900; letter-spacing: -.04em; text-shadow: 5px 5px 0 #151537; }
h1 em { color: #4de68a; }
.lede { color: #d9d5ff; }
.style-tag { background: #ffcf3f; color: #25213c; border: 3px solid #25213c; border-radius: 0; box-shadow: 4px 4px 0 #151537; }
.query-panel, .answer { border: 4px solid #25213c; }
.query-panel { background: #fff4cf; }
.field-row input { border: 3px solid #25213c; border-radius: 0; background: white; }
.primary-button { border: 3px solid #25213c; border-radius: 0; box-shadow: 4px 4px 0 #25213c; }
.primary-button:active { transform: translateY(4px); box-shadow: none; }
.sample-row button { border: 2px solid #25213c; border-radius: 0; background: #ff9ecf; color: #25213c; }
.status { border: 3px solid #25213c; border-radius: 0; background: #4de68a; color: #25213c; }
.answer-grid section:nth-child(1) { background: #ffcf3f; }
.answer-grid section:nth-child(2) { background: #ff9ecf; }
.answer-grid section:nth-child(3) { background: #4de68a; }
.answer-grid span, .answer-grid p { color: #25213c; }
.material-list input { appearance: none; border: 3px solid #25213c; background: white; }
.material-list input:checked { background: #4de68a; box-shadow: inset 0 0 0 3px white; }
.page-footer { color: #d9d5ff; border-color: #6b68a5; }
"""
    },
    {
        "slug": "y2k-chrome", "name": "Y2K 金属", "english": "Y2K CHROME", "number": "14",
        "description": "混合银色渐变、泡泡形状和千禧年数字光泽",
        "colors": ["#dce5ff", "#6c78ff", "#ffffff"],
        "css": r"""
:root { --bg: #dce5ff; --surface: rgba(255,255,255,.72); --ink: #263273; --muted: #6471a1; --accent: #6c78ff; --accent-ink: #ffffff; --line: #ffffff; --radius: 28px; --shadow: inset 1px 1px 0 #fff, 0 14px 35px rgba(83,98,190,.22); --display: Arial Rounded MT Bold, Trebuchet MS, "Microsoft YaHei", sans-serif; }
body { background: radial-gradient(circle at 15% 20%, #fff 0 2%, transparent 18%), radial-gradient(circle at 85% 5%, #f8bfff 0, transparent 26%), linear-gradient(155deg, #e9f7ff, #cfd6ff 55%, #e6d6ff); }
.ambient i { position: absolute; top: 100px; right: 8%; width: 190px; height: 190px; border-radius: 50%; background: linear-gradient(145deg, #fff 0, #9ca9c9 25%, #fff 48%, #7788b5 70%, #eaf4ff); box-shadow: inset -12px -12px 25px rgba(68,77,140,.3), 0 20px 40px rgba(90,100,170,.2); }
.ambient b { position: absolute; left: 5%; bottom: 12%; width: 90px; height: 90px; background: linear-gradient(145deg, white, #9aabff); clip-path: polygon(50% 0,61% 36%,100% 50%,61% 62%,50% 100%,38% 62%,0 50%,38% 36%); }
.topbar { background: linear-gradient(#ffffff, #c2cde5 48%, #f4f8ff 52%, #d5def0); border: 2px solid white; border-radius: 999px; padding: 12px 22px; margin-top: 18px; box-shadow: 0 8px 24px rgba(84,98,160,.2); }
.brand-mark { background: linear-gradient(145deg, #fff, #6c78ff); border: 2px solid white; }
h1 { font-weight: 900; }
h1 em { background: linear-gradient(180deg, #ffffff 0, #899aff 35%, #ffffff 50%, #5365d9 70%, #d9e2ff); -webkit-background-clip: text; background-clip: text; color: transparent; -webkit-text-stroke: 1px #5365b5; filter: drop-shadow(2px 3px 0 white); }
.style-tag { background: linear-gradient(145deg, white, #c6d1ff); border: 2px solid white; color: #5365b5; }
.query-panel { background: linear-gradient(145deg, rgba(255,255,255,.85), rgba(201,213,255,.6)); border: 2px solid white; }
.field-row input { background: rgba(255,255,255,.75); border: 2px solid white; border-radius: 999px; box-shadow: inset 3px 3px 8px rgba(91,106,165,.18); }
.primary-button { border: 2px solid white; border-radius: 999px; background: linear-gradient(#aab4ff, #6372ef 50%, #98a7ff 52%, #6c78ff); text-shadow: 0 1px 2px #38468f; }
.sample-row button { background: linear-gradient(#fff, #d7def7); border: 2px solid white; color: #6471a1; }
.answer { border: 2px solid white; background: rgba(255,255,255,.68); backdrop-filter: blur(14px); }
.status { border: 2px solid white; background: linear-gradient(145deg, #c8fff1, #58d5c1); color: #236557; }
.answer-grid section { margin: 12px; border: 2px solid white; border-radius: 22px; background: linear-gradient(145deg, rgba(255,255,255,.9), rgba(211,220,255,.6)); }
.answer-grid section + section { border-left: 2px solid white; }
@media (max-width: 720px) { .answer-grid section + section { border-top: 2px solid white; } }
"""
    },
    {
        "slug": "cyber-neon", "name": "赛博霓虹", "english": "CYBER NEON", "number": "15",
        "description": "用暗色城市感、青紫辉光和切角组件强化未来感",
        "colors": ["#0a0920", "#00f0ff", "#ff2ca8"],
        "css": r"""
:root { --bg: #0a0920; --surface: rgba(15,15,43,.94); --ink: #edfaff; --muted: #94a5c7; --accent: #00f0ff; --accent-ink: #07121c; --line: #28345c; --radius: 0; --shadow: 0 0 32px rgba(0,240,255,.09); --display: Orbitron, Segoe UI, "Microsoft YaHei", sans-serif; }
body { background-image: linear-gradient(rgba(0,240,255,.045) 1px, transparent 1px), linear-gradient(90deg, rgba(0,240,255,.045) 1px, transparent 1px); background-size: 46px 46px; }
.ambient i { position: absolute; top: -20%; right: -10%; width: 60%; height: 70%; background: radial-gradient(circle, rgba(255,44,168,.2), transparent 65%); }
.ambient b { position: absolute; left: -10%; bottom: -20%; width: 60%; height: 70%; background: radial-gradient(circle, rgba(0,240,255,.14), transparent 65%); }
.topbar { border-bottom: 1px solid #00f0ff; }
.brand { letter-spacing: .12em; }
.brand-mark { border-radius: 0; clip-path: polygon(20% 0,100% 0,100% 80%,80% 100%,0 100%,0 20%); }
.back-link { color: #ff2ca8; }
h1 { text-transform: uppercase; text-shadow: 3px 0 0 rgba(255,44,168,.55), -3px 0 0 rgba(0,240,255,.45); }
h1 em { color: #00f0ff; }
.kicker { color: #ff2ca8; }
.style-tag { border-radius: 0; border-color: #ff2ca8; color: #ff8dcd; clip-path: polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px); }
.query-panel, .answer { clip-path: polygon(18px 0,100% 0,100% calc(100% - 18px),calc(100% - 18px) 100%,0 100%,0 18px); border-color: #00f0ff; }
.query-panel { border-left: 4px solid #ff2ca8; }
.field-row input { background: #070817; border-radius: 0; color: #00f0ff; border-color: #28345c; }
.primary-button { border-radius: 0; clip-path: polygon(10px 0,100% 0,100% calc(100% - 10px),calc(100% - 10px) 100%,0 100%,0 10px); box-shadow: 0 0 18px rgba(0,240,255,.35); }
.sample-row button { border-radius: 0; border-color: #3a4770; }
.status { border-radius: 0; background: #ff2ca8; color: white; box-shadow: 0 0 18px rgba(255,44,168,.35); }
.answer-kicker, .answer-grid span { color: #00f0ff; }
.answer-grid section:nth-child(2) { border-top: 2px solid #ff2ca8; }
.answer-grid section:nth-child(3) { border-top: 2px solid #00f0ff; }
.source summary { color: #00f0ff; }
"""
    },
    {
        "slug": "blueprint", "name": "工程蓝图", "english": "BLUEPRINT", "number": "16",
        "description": "把内容绘制成带坐标、标注和技术网格的图纸",
        "colors": ["#14538c", "#ecf7ff", "#81c8ef"],
        "css": r"""
:root { --bg: #14538c; --surface: rgba(10,63,111,.72); --ink: #ecf7ff; --muted: #b5d9ee; --accent: #ecf7ff; --accent-ink: #14538c; --line: #5d9fc6; --radius: 0; --shadow: none; --display: Consolas, "Microsoft YaHei", monospace; }
body { font-family: Consolas, "Microsoft YaHei", monospace; background-image: linear-gradient(rgba(236,247,255,.12) 1px, transparent 1px), linear-gradient(90deg, rgba(236,247,255,.12) 1px, transparent 1px), linear-gradient(rgba(236,247,255,.05) 1px, transparent 1px), linear-gradient(90deg, rgba(236,247,255,.05) 1px, transparent 1px); background-size: 100px 100px, 100px 100px, 20px 20px, 20px 20px; }
.topbar { border: 1px solid var(--line); margin-top: 20px; padding: 16px 20px; }
.brand-mark { border-radius: 0; border: 1px solid var(--accent); background: transparent; color: var(--accent); }
.page { max-width: 1100px; }
.intro { position: relative; border: 1px solid var(--line); padding: 36px; max-width: none; }
.intro::before { content: "A-01"; position: absolute; top: -12px; left: 20px; padding: 0 10px; background: #14538c; color: #ecf7ff; }
h1 { font-weight: 400; }
h1 em { color: #ecf7ff; text-decoration: underline; text-decoration-style: dashed; text-underline-offset: 12px; }
.style-tag { border-radius: 0; }
.demo { position: relative; }
.demo::before { content: "SCALE 1:100"; position: absolute; right: 0; top: -28px; font-size: 11px; color: #b5d9ee; }
.query-panel, .answer { border: 1px solid var(--accent); }
.query-panel { border-style: dashed; }
.field-row input { background: rgba(5,45,80,.5); border-radius: 0; color: white; }
.primary-button { border-radius: 0; background: transparent; color: #ecf7ff; border-color: #ecf7ff; }
.primary-button:hover { background: #ecf7ff; color: #14538c; }
.sample-row button { border-radius: 0; }
.status { border-radius: 0; border: 1px solid #ecf7ff; background: transparent; color: #ecf7ff; }
.answer h2::after { content: "  [FIG. 02]"; font-size: 12px; font-weight: 400; color: #b5d9ee; }
.answer-kicker, .answer-grid span { color: #ecf7ff; }
.answer-grid section { position: relative; }
.answer-grid section::after { content: "+"; position: absolute; right: 5px; bottom: 2px; color: #81c8ef; }
.source summary::before { content: "NOTE: "; color: #ecf7ff; }
"""
    },
    {
        "slug": "handwritten", "name": "手绘笔记", "english": "DOODLE NOTES", "number": "17",
        "description": "用横线纸、手写感和随手圈画降低办事距离感",
        "colors": ["#fffdf2", "#e96767", "#5279b9"],
        "css": r"""
:root { --bg: #fffdf2; --surface: #fffdf2; --ink: #33425c; --muted: #69748a; --accent: #e96767; --accent-ink: #fffdf2; --line: #9db7d7; --radius: 3px; --shadow: 3px 5px 0 rgba(82,121,185,.12); --display: "Comic Sans MS", "KaiTi", cursive; }
body { font-family: "Comic Sans MS", "KaiTi", cursive; background-image: repeating-linear-gradient(transparent 0 31px, #c9def0 31px 32px); }
body::before { content: ""; position: fixed; left: 54px; top: 0; bottom: 0; width: 2px; background: rgba(233,103,103,.45); }
.ambient i { position: absolute; right: 5%; top: 110px; width: 140px; height: 70px; border: 4px solid #e96767; border-color: #e96767 transparent transparent; border-radius: 50%; transform: rotate(14deg); }
.topbar { transform: rotate(-.4deg); }
.brand-mark { border-radius: 45% 55% 50% 40%; }
.page { max-width: 1040px; }
h1 { font-weight: 700; letter-spacing: -.035em; }
h1 em { position: relative; color: #5279b9; }
h1 em::after { content: ""; position: absolute; left: -2%; right: -2%; bottom: -5px; height: 10px; border: 3px solid #e96767; border-color: #e96767 transparent transparent; border-radius: 50%; }
.lede strong { background: linear-gradient(transparent 45%, #fff09c 45%); }
.style-tag { border: 2px solid #5279b9; color: #5279b9; border-radius: 48% 52% 45% 55%; transform: rotate(-2deg); }
.query-panel { transform: rotate(.35deg); border: 2px solid #5279b9; }
.field-row input { background: rgba(255,255,255,.6); border: 2px dashed #5279b9; border-radius: 8px 13px 7px 11px; }
.primary-button { border-radius: 45% 55% 48% 52%; transform: rotate(-1deg); }
.sample-row button { background: #fff09c; border: 1px solid #9c8c47; color: #5a533c; }
.answer { border: 2px solid #5279b9; transform: rotate(-.25deg); }
.status { border-radius: 50%; transform: rotate(8deg); background: transparent; color: #e96767; border: 3px solid #e96767; }
.answer-grid { border-style: dashed; }
.answer-grid section + section { border-left-style: dashed; }
.answer-grid span { color: #e96767; }
.details-grid h3 { text-decoration: underline wavy #e96767; text-underline-offset: 6px; }
.material-list input { accent-color: #e96767; }
.source { border-top-style: dashed; }
"""
    },
    {
        "slug": "collage", "name": "杂志拼贴", "english": "CUT & PASTE", "number": "18",
        "description": "把错位纸片、撕边和混合字体拼成编辑式版面",
        "colors": ["#e9e2d5", "#ef5a3c", "#272727"],
        "css": r"""
:root { --bg: #e9e2d5; --surface: #fffaf0; --ink: #272727; --muted: #635d55; --accent: #ef5a3c; --accent-ink: #fffaf0; --line: #272727; --radius: 0; --shadow: 8px 12px 20px rgba(50,43,32,.16); --display: Georgia, "Songti SC", serif; }
body { background-image: radial-gradient(rgba(50,40,30,.09) .6px, transparent .6px); background-size: 5px 5px; }
.ambient i { position: absolute; top: 150px; right: 4%; width: 180px; height: 230px; background: #537d72; transform: rotate(12deg); clip-path: polygon(0 3%,8% 0,17% 3%,28% 0,38% 2%,49% 0,60% 3%,73% 0,85% 3%,100% 0,98% 100%,0 98%); }
.topbar { background: #272727; color: #fffaf0; padding: 16px 22px; margin-top: 20px; transform: rotate(-.5deg); }
.brand-mark { background: #ef5a3c; border-radius: 0; }
.page { max-width: 1080px; }
.intro { position: relative; }
h1 { position: relative; z-index: 1; font-weight: 900; }
h1 em { display: inline-block; background: #ef5a3c; color: #fffaf0; padding: 0 18px 8px; transform: rotate(-2deg); clip-path: polygon(1% 4%,99% 0,97% 96%,0 100%); }
.kicker { display: inline-block; background: #fff09c; color: #272727; padding: 3px 12px; transform: rotate(2deg); }
.style-tag { background: #537d72; color: white; border: 0; border-radius: 0; transform: rotate(-1deg); }
.query-panel { transform: rotate(-.6deg); clip-path: polygon(0 2%,7% 0,15% 2%,24% 0,33% 1%,42% 0,54% 2%,67% 0,79% 2%,90% 0,100% 2%,99% 100%,0 98%); }
.field-row input { background: white; border: 2px solid #272727; border-radius: 0; }
.primary-button { border-radius: 0; transform: rotate(1deg); }
.sample-row button { background: #fff09c; color: #272727; border-color: #272727; border-radius: 0; }
.answer { transform: rotate(.4deg); border: 0; }
.answer-head { border-bottom: 8px solid #272727; padding-bottom: 18px; }
.answer h2 { font-style: italic; }
.status { border-radius: 0; transform: rotate(5deg); }
.answer-grid { border: 0; gap: 12px; }
.answer-grid section { background: #e9e2d5; border: 1px solid #272727 !important; }
.answer-grid section:nth-child(2) { background: #fff09c; transform: rotate(-1deg); }
.answer-grid section:nth-child(3) { background: #d4e1db; transform: rotate(1deg); }
.details-grid h3 { font-family: Arial Black, sans-serif; text-transform: uppercase; }
.source { border-top: 2px dashed #272727; }
"""
    },
    {
        "slug": "soft-clay", "name": "柔彩黏土", "english": "SOFT CLAY", "number": "19",
        "description": "用奶油色、膨胀圆角和柔软立体阴影模拟手作质感",
        "colors": ["#f9e8dd", "#e8977d", "#a6c8b5"],
        "css": r"""
:root { --bg: #f9e8dd; --surface: #fff8f1; --ink: #604b47; --muted: #947873; --accent: #e8977d; --accent-ink: #fff8f1; --line: rgba(255,255,255,.8); --radius: 34px; --shadow: 0 18px 30px rgba(164,112,94,.16), inset 2px 2px 2px rgba(255,255,255,.8), inset -3px -3px 5px rgba(164,112,94,.08); --display: Arial Rounded MT Bold, "Segoe UI", "Microsoft YaHei", sans-serif; }
body { background: radial-gradient(circle at 10% 15%, #fff6e9 0, transparent 28%), radial-gradient(circle at 85% 15%, #dcebe2 0, transparent 25%), #f9e8dd; }
.ambient i { position: absolute; width: 190px; height: 190px; right: 5%; top: 130px; border-radius: 45% 55% 60% 40%; background: #a6c8b5; box-shadow: inset 8px 8px 15px rgba(255,255,255,.45), inset -8px -8px 15px rgba(70,120,95,.12), 0 22px 35px rgba(100,140,115,.18); transform: rotate(18deg); }
.ambient b { position: absolute; width: 120px; height: 120px; left: 4%; bottom: 10%; border-radius: 40% 60% 45% 55%; background: #f4c86c; box-shadow: inset 6px 6px 12px rgba(255,255,255,.45), 0 18px 30px rgba(160,120,60,.15); }
.brand-mark { border-radius: 40% 60% 50% 50%; box-shadow: inset 2px 2px 2px rgba(255,255,255,.4); }
.back-link { border: 0; background: #fff8f1; padding: 8px 15px; border-radius: 999px; box-shadow: 0 6px 14px rgba(164,112,94,.12); }
.page { max-width: 1060px; }
h1 { font-weight: 800; letter-spacing: -.045em; }
h1 em { color: #e8977d; }
.style-tag { border: 0; background: #dcebe2; color: #557464; border-radius: 999px; box-shadow: inset 2px 2px 3px rgba(255,255,255,.6); }
.query-panel, .answer { border: 2px solid rgba(255,255,255,.75); }
.field-row input { background: #f5e9e0; border: 0; border-radius: 999px; box-shadow: inset 4px 4px 9px rgba(140,100,85,.12), inset -3px -3px 8px white; }
.primary-button { border: 0; border-radius: 999px; box-shadow: 0 8px 15px rgba(170,100,80,.2), inset 2px 2px 2px rgba(255,255,255,.35); }
.sample-row button { border: 0; background: #eee5f5; color: #806f8e; }
.status { background: #a6c8b5; color: #365848; box-shadow: inset 2px 2px 2px rgba(255,255,255,.4); }
.answer-grid { border: 0; gap: 14px; }
.answer-grid section { border-radius: 24px; background: #f9eee6; box-shadow: inset 2px 2px 4px white, inset -2px -2px 4px rgba(150,110,90,.08); }
.answer-grid section + section { border: 0; }
.answer-grid section:nth-child(2) { background: #f3e8f6; }
.answer-grid section:nth-child(3) { background: #e5f0e9; }
.answer-grid span { color: #b66f5c; }
.material-list label { background: #f7ede6; padding: 9px 12px; border-radius: 16px; }
.source, .page-footer { border-color: rgba(170,120,100,.22); }
"""
    },
    {
        "slug": "organic", "name": "自然有机", "english": "ORGANIC EARTH", "number": "20",
        "description": "用植物色、流动曲线和自然纸张感形成舒缓体验",
        "colors": ["#eef0e4", "#496b54", "#c9b894"],
        "css": r"""
:root { --bg: #eef0e4; --surface: #f8f6ed; --ink: #2f4435; --muted: #6d7967; --accent: #496b54; --accent-ink: #f8f6ed; --line: #c7cbb7; --radius: 30px 12px 34px 16px; --shadow: 0 18px 45px rgba(61,82,56,.09); --display: Georgia, "Songti SC", serif; }
body { background: radial-gradient(ellipse at 0 0, #dce5d1 0, transparent 35%), radial-gradient(ellipse at 100% 20%, #e5d9bd 0, transparent 30%), #eef0e4; }
.ambient i { position: absolute; right: -40px; top: 90px; width: 300px; height: 440px; border-radius: 100% 0 100% 0; background: #b7c7a8; transform: rotate(28deg); opacity: .6; }
.ambient b { position: absolute; left: -60px; bottom: 8%; width: 240px; height: 240px; border-radius: 60% 40% 70% 30%; border: 1px solid #9faf91; }
.topbar { border-bottom: 1px solid #aeb9a1; }
.brand-mark { border-radius: 70% 30% 65% 35%; }
.back-link { border-bottom-style: dotted; }
.page { max-width: 1080px; }
.intro { padding-left: 5%; }
h1 { font-weight: 400; letter-spacing: -.05em; }
h1 em { color: #496b54; font-style: italic; }
.kicker { letter-spacing: .22em; }
.style-tag { border-radius: 50% 20% 50% 20%; padding: 12px 20px; background: rgba(248,246,237,.5); }
.demo { gap: 30px; }
.query-panel { border: 1px solid #bcc6ae; }
.field-row input { background: #f1f0e5; border-color: #b8c1ab; border-radius: 24px 10px 24px 10px; }
.primary-button { border-radius: 50% 20% 50% 20%; }
.sample-row button { border-color: #b8c1ab; background: #f8f6ed; }
.answer { border: 1px solid #c1c8b4; }
.answer-kicker { color: #6b815d; }
.status { border-radius: 50% 20% 50% 20%; background: #dce6d4; color: #3e5d43; }
.answer-grid { border-color: #c7cbb7; }
.answer-grid section:first-child { background: #edf0e4; border-radius: 24px 0 0 0; }
.answer-grid section:nth-child(2) { background: #f0eadc; }
.answer-grid section:nth-child(3) { background: #e4eadc; border-radius: 0 0 24px 0; }
.answer-grid span { color: #6b815d; }
.details-grid h3 { font-family: Georgia, serif; font-size: 18px; font-weight: 400; }
.material-list input { accent-color: #496b54; }
.source { border-top-style: dotted; }
"""
    },
    {
        "slug": "aurora-glass", "name": "极光玻璃", "english": "AURORA GLASS", "number": "21", "apple": True,
        "description": "用缓慢极光、透亮玻璃与分层浮现营造轻盈智能感",
        "colors": ["#eef4ff", "#8ea7ff", "#d9f4ef"],
        "css": r"""
:root { --bg: #f4f7fc; --surface: rgba(255,255,255,.54); --ink: #11151d; --muted: #454e5c; --accent: #1e459f; --accent-ink: #ffffff; --line: rgba(255,255,255,.7); --radius: 30px; --shadow: 0 24px 70px rgba(61,80,125,.13); --display: "Segoe UI", "Microsoft YaHei", sans-serif; --pointer-glow: rgba(101,132,255,.14); }
body { background: #f4f7fc; }
body::before { content: ""; position: fixed; inset: -25%; z-index: 0; pointer-events: none; background: radial-gradient(ellipse at 20% 25%, rgba(157,194,255,.72), transparent 35%), radial-gradient(ellipse at 76% 18%, rgba(239,177,218,.55), transparent 30%), radial-gradient(ellipse at 55% 78%, rgba(164,231,214,.6), transparent 33%); animation: aurora-flow 18s ease-in-out infinite alternate; }
.ambient { z-index: 1; }
.ambient i { position: absolute; right: -8vw; top: -12vw; width: 46vw; height: 46vw; border-radius: 50%; background: radial-gradient(circle at 35% 35%, rgba(255,255,255,.85), rgba(110,139,255,.22) 45%, transparent 70%); filter: blur(18px); animation: aurora-breathe 14s ease-in-out infinite alternate; }
.ambient b { position: absolute; left: -10vw; bottom: -12vw; width: 38vw; height: 38vw; border-radius: 50%; background: rgba(127,221,200,.2); filter: blur(46px); animation: aurora-breathe 17s ease-in-out infinite alternate-reverse; }
.ambient span { position: absolute; left: 0; right: 0; top: 38%; height: 1px; background: linear-gradient(90deg, transparent, rgba(88,116,180,.26), transparent); }
.topbar { margin-top: 18px; padding: 12px 18px; border: 1px solid rgba(255,255,255,.75); border-radius: 999px; background: rgba(255,255,255,.38); backdrop-filter: blur(22px); }
.brand-mark { background: rgba(255,255,255,.72); color: #1e459f; box-shadow: 0 5px 18px rgba(55,111,232,.18); }
.back-link { border: 0; color: #3d4753; }
.page { max-width: 1160px; }
.intro { max-width: 850px; }
h1 { font-weight: 680; letter-spacing: -.065em; }
h1 em { background: linear-gradient(110deg, #1e459f, #4a3f9e 48%, #1f6b58); -webkit-background-clip: text; background-clip: text; color: transparent; }
.style-tag { background: rgba(255,255,255,.42); color: #454e5c; border-color: rgba(255,255,255,.7); backdrop-filter: blur(14px); }
.demo { grid-template-columns: .78fr 1.22fr; align-items: start; gap: 28px; }
.query-panel { position: sticky; top: 24px; }
.field-row { grid-template-columns: 1fr; }
.field-row input { background: rgba(255,255,255,.62); border-color: rgba(117,135,170,.2); border-radius: 18px; }
.field-row input:focus { border-color: rgba(55,111,232,.55); box-shadow: 0 0 0 5px rgba(55,111,232,.09); }
.primary-button { border: 0; border-radius: 18px; background: #2a5bc4; box-shadow: 0 10px 25px rgba(42,91,196,.25); }
.sample-row button { background: rgba(255,255,255,.38); border-color: rgba(105,124,155,.18); }
.answer { border-color: rgba(255,255,255,.8); }
.answer-grid { gap: 12px; border: 0; }
.answer-grid section { border: 1px solid rgba(255,255,255,.64) !important; border-radius: 20px; background: rgba(255,255,255,.35); }
.answer-grid span, .answer-kicker { color: #1e459f; }
.status { background: rgba(220,246,236,.82); color: #23624e; border: 1px solid rgba(255,255,255,.7); }
.source, .page-footer { border-color: rgba(85,103,135,.18); }
@keyframes aurora-flow { from { transform: translate3d(-4%,-3%,0) rotate(-6deg) scale(.97); } to { transform: translate3d(6%,5%,0) rotate(7deg) scale(1.15); } }
@keyframes aurora-breathe { from { transform: scale(.86) translate3d(0,0,0); opacity: .55; } to { transform: scale(1.16) translate3d(-7%,10%,0); opacity: 1; } }
"""
    },
    {
        "slug": "graphite-halo", "name": "石墨光晕", "english": "GRAPHITE HALO", "number": "22", "apple": True,
        "description": "以石墨玻璃、金属轮廓和跟随指针的柔光建立空间感",
        "colors": ["#080a0e", "#c4d2ff", "#303542"],
        "css": r"""
:root { --bg: #07080b; --surface: rgba(20,23,30,.62); --ink: #f3f5f9; --muted: #a1a8b5; --accent: #c4d2ff; --accent-ink: #11141b; --line: rgba(255,255,255,.12); --radius: 26px; --shadow: 0 30px 90px rgba(0,0,0,.42); --display: "Segoe UI", "Microsoft YaHei", sans-serif; --pointer-glow: rgba(150,175,255,.26); }
body { background: linear-gradient(145deg, #07080b, #0b0d12 55%, #07080b); }
.ambient i { position: absolute; right: -13vw; top: -18vw; width: 52vw; height: 52vw; border-radius: 50%; border: 1px solid rgba(190,205,255,.13); box-shadow: inset 0 0 90px rgba(150,170,240,.05), 0 0 100px rgba(100,120,200,.04); animation: halo-turn 26s ease-in-out infinite alternate; }
.ambient i::after { content: ""; position: absolute; inset: 13%; border-radius: inherit; border: 1px solid rgba(255,255,255,.06); }
.ambient b { position: absolute; left: 4%; bottom: 2%; width: 320px; height: 320px; border-radius: 50%; background: rgba(99,116,180,.09); filter: blur(60px); animation: halo-pulse 12s ease-in-out infinite alternate; }
.ambient span { position: absolute; left: 8%; right: 8%; top: 47%; height: 1px; background: linear-gradient(90deg, transparent, rgba(196,210,255,.11), transparent); }
.topbar { border-bottom: 1px solid rgba(255,255,255,.1); }
.brand-mark { background: linear-gradient(145deg, #f5f7fb, #8994aa); color: #11141b; box-shadow: inset 0 1px 1px white; }
.back-link { border-bottom-color: rgba(255,255,255,.25); color: #c4c9d3; }
.page { max-width: 1160px; }
h1 { font-weight: 620; }
h1 em { background: linear-gradient(110deg, #ffffff, #9daecb 55%, #e8ecf5); -webkit-background-clip: text; background-clip: text; color: transparent; }
.kicker, .answer-kicker, .answer-grid span { color: #b7c8f4; }
.style-tag { background: rgba(255,255,255,.035); color: #aab2c1; }
.demo { grid-template-columns: .76fr 1.24fr; align-items: start; gap: 28px; }
.query-panel { position: sticky; top: 24px; background: linear-gradient(rgba(20,23,30,.72),rgba(20,23,30,.72)) padding-box, linear-gradient(145deg,rgba(255,255,255,.22),rgba(255,255,255,.035)) border-box; border: 1px solid transparent; }
.answer { background: linear-gradient(rgba(17,20,27,.72),rgba(17,20,27,.72)) padding-box, linear-gradient(145deg,rgba(255,255,255,.2),rgba(255,255,255,.035)) border-box; border: 1px solid transparent; }
.field-row { grid-template-columns: 1fr; }
.field-row input { background: rgba(0,0,0,.25); color: #f3f5f9; border-color: rgba(255,255,255,.12); border-radius: 16px; }
.field-row input:focus { border-color: rgba(196,210,255,.48); box-shadow: 0 0 0 5px rgba(160,180,240,.07); }
.primary-button { background: #edf1f8; color: #11141b; border: 0; border-radius: 16px; box-shadow: 0 10px 30px rgba(200,215,255,.1); }
.sample-row button { background: rgba(255,255,255,.035); border-color: rgba(255,255,255,.1); color: #b7bdc9; }
.status { background: rgba(196,210,255,.12); color: #d9e3ff; border: 1px solid rgba(196,210,255,.18); }
.answer-grid section { background: rgba(255,255,255,.022); }
.source, .page-footer { border-color: rgba(255,255,255,.1); }
.source summary { color: #e3e7ef; }
@keyframes halo-turn { from { transform: rotate(-7deg) translate3d(-3%,-2%,0); } to { transform: rotate(11deg) translate3d(4%,5%,0); } }
@keyframes halo-pulse { to { transform: scale(1.34) translate3d(-9%,-13%,0); opacity: .5; } }
"""
    },
    {
        "slug": "silver-studio", "name": "银白序章", "english": "SILVER STUDIO", "number": "23", "apple": True,
        "description": "借银灰材质、巨幅排版和轻微视差接近产品发布现场",
        "colors": ["#edf0f4", "#1d1d1f", "#b9c8e2"],
        "css": r"""
:root { --bg: #eef0f3; --surface: rgba(255,255,255,.58); --ink: #1d1d1f; --muted: #5c6068; --accent: #1d1d1f; --accent-ink: #ffffff; --line: rgba(255,255,255,.78); --radius: 34px; --shadow: 0 34px 90px rgba(62,70,84,.12); --display: "Segoe UI", "Microsoft YaHei", sans-serif; --pointer-glow: rgba(255,255,255,.75); }
body { background: linear-gradient(145deg, #f8f9fb 0%, #e7eaef 48%, #f4f5f7 100%); }
.ambient i { position: absolute; right: -7vw; top: 5vh; width: 36vw; height: 36vw; border-radius: 50%; background: radial-gradient(circle at 32% 28%, #ffffff 0%, #dfe4eb 25%, #aab4c3 52%, #f2f4f7 72%, #c6cdd7 100%); box-shadow: inset -22px -26px 50px rgba(66,77,96,.16), 0 45px 90px rgba(70,80,100,.15); opacity: .68; animation: silver-float 14s ease-in-out infinite alternate; }
.ambient b { position: absolute; left: -12vw; bottom: 4%; width: 42vw; height: 24vw; border-radius: 50%; background: linear-gradient(120deg, rgba(255,255,255,.8), rgba(171,190,220,.3), rgba(255,255,255,.5)); filter: blur(4px); transform: rotate(24deg); opacity: .7; animation: silver-drift 18s ease-in-out infinite alternate; }
.ambient span { position: absolute; left: 6%; right: 6%; top: 52%; height: 1px; background: linear-gradient(90deg, transparent, rgba(112,128,155,.3), transparent); }
.topbar { margin-top: 18px; padding: 12px 18px; border-radius: 999px; border: 1px solid rgba(255,255,255,.8); background: rgba(255,255,255,.42); backdrop-filter: blur(24px); box-shadow: 0 8px 30px rgba(70,80,100,.06); }
.brand-mark { background: #1d1d1f; color: white; }
.back-link { border: 0; }
.page { max-width: 1160px; padding-top: 76px; }
.intro { max-width: 970px; margin: 0 auto 64px; text-align: center; }
h1 { font-size: clamp(54px,7.5vw,104px); font-weight: 650; }
h1 em { background: linear-gradient(100deg, #1d1d1f 5%, #778399 48%, #1d1d1f 90%); -webkit-background-clip: text; background-clip: text; color: transparent; }
.lede { margin-left: auto; margin-right: auto; }
.kicker { color: #586274; }
.style-tag { background: rgba(255,255,255,.48); border-color: rgba(255,255,255,.85); color: #575d68; }
.demo { display: block; }
.query-panel { max-width: 920px; margin: 0 auto 30px; padding: 18px; border-radius: 28px; }
.query-panel > label { padding: 4px 8px 0; }
.field-row input { background: rgba(255,255,255,.68); border-color: rgba(85,95,115,.12); border-radius: 18px; }
.field-row input:focus { border-color: rgba(60,110,220,.38); box-shadow: 0 0 0 5px rgba(60,110,220,.07); }
.primary-button { border: 0; border-radius: 18px; background: #1d1d1f; }
.sample-row { padding: 0 8px; }
.sample-row button { background: rgba(255,255,255,.45); border-color: rgba(90,100,120,.12); }
.answer { border-color: rgba(255,255,255,.9); box-shadow: 0 40px 110px rgba(55,65,85,.14), inset 0 1px 0 white; }
.answer-grid { gap: 14px; border: 0; }
.answer-grid section { border: 1px solid rgba(255,255,255,.8) !important; border-radius: 22px; background: linear-gradient(145deg, rgba(255,255,255,.58), rgba(226,232,241,.38)); }
.answer-grid span, .answer-kicker { color: #4f5c73; }
.status { background: #1d1d1f; color: white; }
.source, .page-footer { border-color: rgba(70,80,100,.14); }
@keyframes silver-float { from { transform: translate3d(2%,-4%,0) rotate(-7deg); } to { transform: translate3d(-6%,7%,0) rotate(9deg); } }
@keyframes silver-drift { to { transform: rotate(35deg) translateX(12%); } }
"""
    },
    {
        "slug": "deep-blue-focus", "name": "深海聚焦", "english": "DEEP BLUE FOCUS", "number": "24", "apple": True,
        "description": "用深海蓝光和输入聚焦时的环境降噪突出人机对话",
        "colors": ["#030b16", "#7dd3fc", "#102c46"],
        "css": r"""
:root { --bg: #030b16; --surface: rgba(8,25,43,.58); --ink: #eef7ff; --muted: #9cafc2; --accent: #7dd3fc; --accent-ink: #062033; --line: rgba(148,205,241,.14); --radius: 28px; --shadow: 0 30px 100px rgba(0,0,0,.38); --display: "Segoe UI", "Microsoft YaHei", sans-serif; --pointer-glow: rgba(70,170,230,.22); }
body { background: linear-gradient(160deg, #020810, #061526 58%, #020a13); }
.ambient i { position: absolute; left: 18%; top: -38%; width: 65%; height: 95%; background: conic-gradient(from 170deg at 50% 0%, transparent, rgba(75,176,235,.13), transparent 30%); filter: blur(22px); transform-origin: 50% 0; animation: deep-sway 16s ease-in-out infinite alternate; }
.ambient b { position: absolute; right: -12%; bottom: -20%; width: 55vw; height: 55vw; border-radius: 50%; background: rgba(20,108,165,.12); filter: blur(70px); animation: deep-glow 13s ease-in-out infinite alternate; }
.ambient span { position: absolute; left: 0; right: 0; bottom: 16%; height: 1px; background: linear-gradient(90deg, transparent, rgba(125,211,252,.14), transparent); }
.topbar { border-bottom: 1px solid rgba(148,205,241,.12); }
.brand-mark { background: rgba(125,211,252,.14); color: #a8e4ff; border: 1px solid rgba(125,211,252,.2); }
.back-link { color: #b4c8d9; border-bottom-color: rgba(125,211,252,.25); }
.page { max-width: 1100px; padding-top: 72px; }
.intro { max-width: 900px; margin: 0 auto 58px; text-align: center; transition: opacity .5s ease, transform .5s ease, filter .5s ease; }
.page:has(.query-panel:focus-within) .intro { opacity: .5; transform: scale(.99); filter: blur(.6px); }
h1 { font-weight: 620; }
h1 em { color: #8bdcff; text-shadow: 0 0 40px rgba(125,211,252,.15); }
.lede { margin-left: auto; margin-right: auto; }
.kicker, .answer-kicker, .answer-grid span { color: #7dd3fc; }
.style-tag { background: rgba(125,211,252,.05); color: #9fb9cc; border-color: rgba(125,211,252,.14); }
.demo { display: block; }
.query-panel { max-width: 900px; margin: 0 auto 30px; border-color: rgba(125,211,252,.17); }
.query-panel:focus-within { border-color: rgba(125,211,252,.42); box-shadow: 0 30px 100px rgba(0,0,0,.4), 0 0 60px rgba(58,160,220,.08); }
.field-row input { background: rgba(0,8,17,.45); color: #eef7ff; border-color: rgba(125,211,252,.15); border-radius: 17px; }
.field-row input:focus { border-color: rgba(125,211,252,.5); box-shadow: 0 0 0 5px rgba(125,211,252,.06); }
.primary-button { background: #a5e3ff; color: #062033; border: 0; border-radius: 17px; box-shadow: 0 10px 30px rgba(80,190,240,.12); }
.sample-row button { background: rgba(125,211,252,.04); color: #a9bfd1; border-color: rgba(125,211,252,.12); }
.answer { border-color: rgba(125,211,252,.15); }
.answer-grid section { background: rgba(125,211,252,.025); }
.status { background: rgba(114,239,203,.12); color: #9af0d6; border: 1px solid rgba(114,239,203,.18); }
.source, .page-footer { border-color: rgba(125,211,252,.12); }
@keyframes deep-sway { from { transform: rotate(-10deg) translateY(-3%); opacity: .45; } to { transform: rotate(14deg) translateY(5%); opacity: 1; } }
@keyframes deep-glow { to { transform: scale(1.28) translate3d(-12%,6%,0); opacity: .6; } }
"""
    },
    {
        "slug": "spectrum-prism", "name": "光谱折射", "english": "SPECTRUM PRISM", "number": "25", "apple": True,
        "description": "让透明棱镜与局部光谱随操作错位呈现克制的智能感",
        "colors": ["#f2f1f3", "#7266df", "#e6b9d2"],
        "css": r"""
:root { --bg: #f2f1f3; --surface: rgba(255,255,255,.5); --ink: #17161b; --muted: #5a5561; --accent: #5a4ac9; --accent-ink: #ffffff; --line: rgba(255,255,255,.72); --radius: 30px; --shadow: 0 28px 80px rgba(65,55,90,.13); --display: "Segoe UI", "Microsoft YaHei", sans-serif; --pointer-glow: rgba(238,232,255,.62); }
body { background: #f2f1f3; }
body::before { content: ""; position: fixed; inset: -35%; z-index: 0; pointer-events: none; background: conic-gradient(from 210deg at 68% 32%, transparent 0deg, rgba(125,211,252,.3) 35deg, rgba(196,181,253,.34) 72deg, rgba(249,168,212,.25) 105deg, transparent 145deg); filter: blur(34px); animation: prism-turn 24s ease-in-out infinite alternate; }
.ambient { z-index: 1; }
.ambient i { position: absolute; right: 2%; top: 8%; width: 280px; height: 330px; clip-path: polygon(50% 0,100% 100%,0 100%); background: linear-gradient(135deg, rgba(255,255,255,.68), rgba(147,129,230,.18) 45%, rgba(244,174,205,.24)); filter: drop-shadow(0 25px 35px rgba(80,65,120,.12)); animation: prism-float 15s ease-in-out infinite alternate; }
.ambient b { position: absolute; left: -8%; bottom: -8%; width: 360px; height: 360px; border-radius: 50%; background: linear-gradient(145deg, rgba(130,215,240,.2), rgba(232,167,205,.18)); filter: blur(32px); animation: prism-float 18s ease-in-out infinite alternate-reverse; }
.ambient span { position: absolute; left: 0; right: 0; top: 44%; height: 1px; background: linear-gradient(90deg, transparent, rgba(126,104,196,.34), transparent); }
.topbar { margin-top: 18px; padding: 12px 18px; border: 1px solid rgba(255,255,255,.7); border-radius: 999px; background: rgba(255,255,255,.34); backdrop-filter: blur(22px); }
.brand-mark { background: linear-gradient(145deg, #6d5fd8, #4b3fa7); color: white; box-shadow: 0 7px 20px rgba(103,87,217,.2); }
.back-link { border: 0; }
.page { max-width: 1160px; }
h1 { font-weight: 660; }
h1 em { background: linear-gradient(100deg, #5143b7, #8260a0 52%, #417f9b); -webkit-background-clip: text; background-clip: text; color: transparent; }
.style-tag { background: rgba(255,255,255,.4); color: #5a5561; border-color: rgba(255,255,255,.74); }
.demo { grid-template-columns: .86fr 1.14fr; align-items: start; gap: 28px; }
.query-panel { position: sticky; top: 24px; }
.field-row { grid-template-columns: 1fr; }
.field-row input { background: rgba(255,255,255,.54); border-color: rgba(103,87,217,.12); border-radius: 18px; }
.field-row input:focus { border-color: rgba(103,87,217,.42); box-shadow: 0 0 0 5px rgba(103,87,217,.07); }
.primary-button { border: 0; border-radius: 18px; background: linear-gradient(135deg, #7565e3, #5545bd); box-shadow: 0 12px 28px rgba(103,87,217,.22); }
.sample-row button { background: rgba(255,255,255,.36); border-color: rgba(103,87,217,.12); }
.answer { border-color: rgba(255,255,255,.82); }
.answer-grid { gap: 12px; border: 0; }
.answer-grid section { border: 1px solid rgba(255,255,255,.65) !important; border-radius: 20px; background: rgba(255,255,255,.32); }
.answer-grid section:nth-child(1) { background: linear-gradient(145deg, rgba(255,255,255,.42), rgba(191,225,245,.2)); }
.answer-grid section:nth-child(2) { background: linear-gradient(145deg, rgba(255,255,255,.42), rgba(211,194,239,.22)); }
.answer-grid section:nth-child(3) { background: linear-gradient(145deg, rgba(255,255,255,.42), rgba(241,197,219,.2)); }
.answer-grid span, .answer-kicker { color: #5a4ac9; }
.status { background: rgba(233,227,255,.7); color: #5143a8; border: 1px solid rgba(255,255,255,.72); }
.source, .page-footer { border-color: rgba(80,65,110,.14); }
@keyframes prism-turn { from { transform: rotate(-9deg) translate3d(-5%,-3%,0); } to { transform: rotate(15deg) translate3d(7%,6%,0); } }
@keyframes prism-float { from { transform: translate3d(2%,-5%,0) rotate(-5deg); } to { transform: translate3d(-7%,9%,0) rotate(8deg); } }
"""
    },
    *[field_theme(*variant) for variant in FIELD_VARIANTS],
]

EXISTING = [
    {"filename": "clear-campus.html", "number": "01", "name": "清透校园", "english": "CLEAR CAMPUS", "description": "暖白、墨绿与清晰卡片", "colors": ["#f4f6ef", "#175c4c", "#d5e7dc"]},
    {"filename": "paper-archive.html", "number": "02", "name": "纸张档案", "english": "PAPER ARCHIVE", "description": "米白纸张、黑红编辑网格", "colors": ["#f2ebdc", "#a43228", "#26221d"]},
    {"filename": "dark-command.html", "number": "03", "name": "深色智能中枢", "english": "DARK COMMAND", "description": "炭黑界面与荧光状态", "colors": ["#151a17", "#b8f35a", "#34443a"]},
]

TOTAL = len(EXISTING) + len(THEMES)
_CN_DIGITS = "零一二三四五六七八九"


def chinese_count(value):
    tens, ones = divmod(value, 10)
    head = "" if not tens else ("十" if tens == 1 else _CN_DIGITS[tens] + "十")
    return head + (_CN_DIGITS[ones] if ones else "")


TOTAL_CN = chinese_count(TOTAL)

INDEX_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="data:,">
<title>校园办事向导 · $total_cn种视觉风格</title>
<style>
:root { --ink: #18231d; --muted: #68736b; --paper: #f3f1e9; --accent: #df5b3f; }
* { box-sizing: border-box; }
body { margin: 0; min-width: 320px; background: var(--paper); color: var(--ink); font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
a { color: inherit; }
header { width: min(1240px, calc(100% - 48px)); margin: 0 auto; padding: 72px 0 48px; display: grid; grid-template-columns: 1.3fr .7fr; gap: 48px; align-items: end; border-bottom: 2px solid var(--ink); }
.eyebrow { margin: 0 0 18px; color: var(--accent); font-size: 12px; font-weight: 800; letter-spacing: .18em; }
h1 { margin: 0; max-width: 800px; font-family: Georgia, "Songti SC", serif; font-size: clamp(48px, 7vw, 92px); line-height: .98; letter-spacing: -.055em; font-weight: 500; }
.header-note { margin: 0; color: var(--muted); font-size: 15px; }
.header-note strong { display: block; margin-bottom: 12px; color: var(--ink); font-size: 32px; font-weight: 500; }
main { width: min(1240px, calc(100% - 48px)); margin: 0 auto; padding: 42px 0 70px; }
.gallery { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.style-card { position: relative; min-width: 0; display: flex; flex-direction: column; min-height: 300px; padding: 18px; border: 1px solid #c9c7bc; background: rgba(255,255,255,.38); text-decoration: none; transition: transform .18s ease, box-shadow .18s ease; }
.style-card:hover { transform: translateY(-5px); box-shadow: 0 14px 30px rgba(30,40,30,.1); }
.style-card:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
.card-top { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.card-number { font-family: Georgia, serif; font-size: 14px; }
.card-arrow { font-size: 20px; }
.preview { position: relative; height: 120px; margin: 18px 0 22px; overflow: hidden; background: var(--c1); border: 1px solid rgba(0,0,0,.1); }
.preview::before { content: ""; position: absolute; width: 58%; height: 58%; left: 10%; top: 20%; background: var(--c2); border-radius: var(--shape, 0); transform: rotate(var(--turn, -5deg)); }
.preview::after { content: ""; position: absolute; width: 42%; height: 28%; right: 7%; bottom: 12%; background: var(--c3); border-radius: var(--shape2, 50%); }
.style-card h2 { margin: 0; font-size: 21px; line-height: 1.2; }
.style-card p { margin: 8px 0 0; color: var(--muted); font-size: 13px; }
.card-english { margin-top: auto; padding-top: 18px; color: var(--muted); font-size: 10px; letter-spacing: .14em; }
footer { width: min(1240px, calc(100% - 48px)); margin: 0 auto; padding: 24px 0 34px; border-top: 1px solid #c9c7bc; color: var(--muted); font-size: 12px; }
@media (max-width: 1000px) { .gallery { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 720px) { header { grid-template-columns: 1fr; gap: 24px; padding-top: 46px; } .gallery { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px) { header, main, footer { width: calc(100% - 28px); } .gallery { grid-template-columns: 1fr; } .style-card { min-height: 260px; } }
@media (prefers-reduced-motion: reduce) { .style-card { transition: none; } .style-card:hover { transform: none; } }
</style>
</head>
<body>
<header>
  <div><p class="eyebrow">CAMPUS GUIDE / VISUAL STUDIES</p><h1>同一内容，<br>$total_cn种表情。</h1></div>
  <p class="header-note"><strong>$total 个方向</strong>不做功能堆叠，只比较色彩、字体、布局、质感与信息节奏。点击任意卡片打开完整示例。</p>
</header>
<main><div class="gallery">$cards</div></main>
<footer>校园办事向导 · 独立视觉稿 · 正式前端未改动</footer>
</body>
</html>
""")


def render_cards():
    cards = []
    all_themes = EXISTING + [{**theme, "filename": theme["slug"] + ".html"} for theme in THEMES]
    for index, theme in enumerate(all_themes):
        shape = ["0", "50%", "12px", "50% 0 50% 0"][index % 4]
        shape2 = ["50%", "0", "18px", "50% 50% 0 0"][index % 4]
        turn = ["-5deg", "8deg", "-12deg", "0deg"][index % 4]
        colors = theme["colors"]
        cards.append(
            f'<a class="style-card" href="{theme["filename"]}" style="--c1:{colors[0]};--c2:{colors[1]};--c3:{colors[2]};--shape:{shape};--shape2:{shape2};--turn:{turn}">'
            f'<div class="card-top"><span class="card-number">{theme["number"]} / {TOTAL}</span><span class="card-arrow">↗</span></div>'
            '<div class="preview" aria-hidden="true"></div>'
            f'<h2>{theme["name"]}</h2><p>{theme["description"]}</p>'
            f'<span class="card-english">{theme["english"]}</span></a>'
        )
    return "\n".join(cards)


def main():
    for theme in THEMES:
        is_apple = bool(theme.get("apple"))
        is_field = bool(theme.get("field"))
        values = {"field_extra": "", "display_strip": ""}
        values.update(theme)
        html = PAGE_TEMPLATE.substitute(
            **values,
            short=theme["number"],
            body_class=theme["slug"] + (" apple" if is_apple else "") + (" field" if is_field else ""),
            base_css=BASE_CSS,
            theme_css=theme["css"],
            apple_css=APPLE_BASE_CSS if is_apple else "",
            field_css=FIELD_BASE_CSS if is_field else "",
            page_script=(APPLE_SCRIPT if (is_apple or is_field) else BASE_SCRIPT),
            total=TOTAL,
            total_cn=TOTAL_CN,
        )
        (ROOT / f'{theme["slug"]}.html').write_text(html, encoding="utf-8")
    (ROOT / "index.html").write_text(
        INDEX_TEMPLATE.substitute(cards=render_cards(), total=TOTAL, total_cn=TOTAL_CN), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
