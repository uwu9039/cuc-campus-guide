# Campus Guide Frontend Visual Directions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build three standalone, interactive HTML visual directions for the campus guide while preserving the current frontend and a complete rollback copy.

**Architecture:** Keep the production frontend untouched. Create three self-contained HTML documents under one design directory, each with inline CSS and the same small native-JavaScript interaction contract. Validate structure with Python standard-library tests, then verify real rendering and interactions in a browser.

**Tech Stack:** HTML5, inline CSS, native JavaScript, Python 3 unittest, Qoder Browser Agent.

**Spec:** `docs/superpowers/specs/2026-11-01-frontend-visual-directions-design.md`

## Global Constraints

- Do not modify `web-next/index.html`, `web-next/styles.css`, `web-next/app.js`, `web-next/classic.html`, `app.py`, or any data file.
- Create only the three requested visual HTML pages plus their standard-library test file and this planning material.
- Each HTML file contains its own CSS and JavaScript; no frameworks, build tools, CDN, web fonts, network requests, or localStorage.
- All three pages use the same “校园卡丢了怎么办” sample and do not create new campus facts.
- Demo submission only reveals the same sample answer; it must not pretend to call the real backend.
- Support empty and answer views, sample-question filling, material progress, quote disclosure, cross-page navigation, narrow screens, keyboard focus, and reduced motion.
- Preserve a complete local copy of `web-next` at `_backups/web-next-before-visual-directions-2026-11-01/`.
- The project has no Git metadata. Do not run Git commands or create commits; use test output and directory diffs as checkpoints.

## File Structure

- Create `design/frontend-visual-directions-2026-11-01/clear-campus.html`: light modern campus direction.
- Create `design/frontend-visual-directions-2026-11-01/paper-archive.html`: editorial paper direction.
- Create `design/frontend-visual-directions-2026-11-01/dark-command.html`: dark command-center direction.
- Create `design/frontend-visual-directions-2026-11-01/test_pages.py`: dependency-free structural and safety checks.
- Create `_backups/web-next-before-visual-directions-2026-11-01/`: exact rollback copy; no files inside are edited.

## Shared Interaction Contract

Every page uses these exact element IDs and function names so the same tests and review script apply to all three designs:

- `#view-empty`, `#view-answer`: the two mutually exclusive views.
- `#question`: the sample-question input.
- `#material-progress`: text showing checked and total material counts.
- `#quotes`: the official-quote region controlled by `aria-expanded` on `#quotes-toggle`.
- `setView(view: "empty" | "answer"): void`
- `fillQuestion(text: string): void`
- `submitDemo(event: Event): void`
- `toggleMaterial(input: HTMLInputElement): void`
- `toggleQuotes(): void`

Each page includes this behavior, adapting only class names used for layout:

```html
<script>
(function () {
  const empty = document.getElementById("view-empty");
  const answer = document.getElementById("view-answer");
  const question = document.getElementById("question");
  const progress = document.getElementById("material-progress");
  const quotes = document.getElementById("quotes");
  const quoteToggle = document.getElementById("quotes-toggle");

  window.setView = function (view) {
    const showAnswer = view === "answer";
    empty.hidden = showAnswer;
    answer.hidden = !showAnswer;
    document.querySelectorAll("[data-set-view]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.setView === view));
    });
  };

  window.fillQuestion = function (text) {
    question.value = text;
    question.focus();
  };

  window.submitDemo = function (event) {
    event.preventDefault();
    if (!question.value.trim()) question.value = "校园卡丢了怎么办";
    setView("answer");
    document.getElementById("answer-title").focus();
  };

  window.toggleMaterial = function () {
    const materials = Array.from(document.querySelectorAll("[data-material]"));
    const checked = materials.filter((input) => input.checked).length;
    progress.textContent = checked + " / " + materials.length + " 已备齐";
  };

  window.toggleQuotes = function () {
    const expanded = quoteToggle.getAttribute("aria-expanded") === "true";
    quoteToggle.setAttribute("aria-expanded", String(!expanded));
    quotes.hidden = expanded;
  };

  document.querySelectorAll("[data-material]").forEach((input) => {
    input.addEventListener("change", () => toggleMaterial(input));
  });
  quoteToggle.addEventListener("click", toggleQuotes);
  setView("empty");
  toggleMaterial();
})();
</script>
```

The answer view contains a focusable heading with `id="answer-title"` and `tabindex="-1"`. The empty and answer views are in the same document, so no network request or storage is needed.

---

### Task 1: Backup and Failing Structural Tests

**Files:**
- Create: `_backups/web-next-before-visual-directions-2026-11-01/`
- Create: `design/frontend-visual-directions-2026-11-01/test_pages.py`

**Interfaces:**
- Consumes: the existing `web-next` directory and the shared interaction contract.
- Produces: repeatable tests named `test_clear_campus`, `test_paper_archive`, and `test_dark_command`; an unchanged rollback copy.

- [ ] **Step 1: Create and verify the rollback copy**

Run from the project root:

```bash
mkdir -p _backups/web-next-before-visual-directions-2026-11-01 design/frontend-visual-directions-2026-11-01
cp -a web-next/. _backups/web-next-before-visual-directions-2026-11-01/
diff -qr web-next _backups/web-next-before-visual-directions-2026-11-01
```

Expected: `diff -qr` exits 0 with no output. Stop if the source or backup differs.

- [ ] **Step 2: Write the failing tests**

Create `test_pages.py` with:

```python
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
PAGES = {
    "clear-campus.html": ("clear", "--accent: #175c4c"),
    "paper-archive.html": ("paper", "--accent: #a43228"),
    "dark-command.html": ("dark", "--accent: #b8f35a"),
}
REQUIRED_IDS = (
    "view-empty", "view-answer", "question", "material-progress",
    "quotes", "quotes-toggle", "answer-title",
)


class VisualPagesTest(unittest.TestCase):
    def assert_page(self, filename, page_name, accent):
        path = ROOT / filename
        self.assertTrue(path.is_file(), f"missing {filename}")
        text = path.read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", text.lower())
        self.assertIn('<html lang="zh-CN">', text)
        self.assertIn('name="viewport"', text)
        self.assertIn(f'data-page="{page_name}"', text)
        self.assertIn("<style>", text)
        self.assertIn("<script>", text)
        self.assertIn("@media (max-width: 760px)", text)
        self.assertIn("prefers-reduced-motion", text)
        self.assertIn(accent, text)
        for element_id in REQUIRED_IDS:
            self.assertIn(f'id="{element_id}"', text, f"{filename}: {element_id}")
        for function_name in ("setView", "fillQuestion", "submitDemo", "toggleMaterial", "toggleQuotes"):
            self.assertIn(function_name, text)
        self.assertGreaterEqual(len(re.findall(r'data-material\b', text)), 3)
        self.assertIn('aria-live="polite"', text)
        self.assertIn(":focus-visible", text)
        for linked_page in PAGES:
            self.assertIn(f'href="{linked_page}"', text)
        for forbidden in ("fetch(", "localStorage", "@import", 'src="http', 'href="http'):
            self.assertNotIn(forbidden, text)
        self.assertIn("校园卡丢了怎么办", text)
        self.assertIn("成绩单", text)
        self.assertIn("转专业", text)

    def test_clear_campus(self):
        self.assert_page("clear-campus.html", *PAGES["clear-campus.html"])

    def test_paper_archive(self):
        self.assert_page("paper-archive.html", *PAGES["paper-archive.html"])

    def test_dark_command(self):
        self.assert_page("dark-command.html", *PAGES["dark-command.html"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 3: Run the tests and confirm the expected failure**

Run:

```bash
.venv/Scripts/python.exe design/frontend-visual-directions-2026-11-01/test_pages.py
```

Expected: three failures reporting the three missing HTML files. No production file has changed.

---

### Task 2: Clear Campus Page

**Files:**
- Create: `design/frontend-visual-directions-2026-11-01/clear-campus.html`
- Test: `design/frontend-visual-directions-2026-11-01/test_pages.py`

**Interfaces:**
- Consumes: the shared interaction contract.
- Produces: a responsive page with `data-page="clear"` and `--accent: #175c4c`.

- [ ] **Step 1: Implement the complete standalone page**

Use a `<header>` with the product name, a three-page local navigation, and a compact evidence-status label. Use `<main>` with a view switcher, a question form, `#view-empty`, and hidden-by-default `#view-answer`. The empty view shows the headline “今天要办什么事？” and three sample buttons. The answer view shows the campus-card conclusion, three steps, three material checkboxes, and the quotes disclosure.

Start the inline CSS with these exact design tokens and include the required accessibility and responsive rules:

```css
:root {
  --bg: #f4f6f1;
  --surface: #ffffff;
  --ink: #17231f;
  --muted: #66736d;
  --line: #dce3dd;
  --accent: #175c4c;
  --accent-soft: #e2efe9;
  --warm: #a84b3c;
  color-scheme: light;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }
button, input { font: inherit; }
button, a, input { -webkit-tap-highlight-color: transparent; }
:focus-visible { outline: 3px solid color-mix(in srgb, var(--accent) 55%, transparent); outline-offset: 3px; }
[hidden] { display: none !important; }
.demo-nav a[aria-current="page"] { color: var(--accent); font-weight: 700; }
.answer-grid { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(280px, .8fr); gap: 20px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 20px; }
@media (max-width: 760px) {
  .answer-grid { grid-template-columns: 1fr; }
  .demo-nav { overflow-x: auto; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; animation: none !important; }
}
```

Complete the visual system with generous whitespace, a large rounded question panel, clear card hierarchy, green primary buttons, and restrained brick-red accents. Add the shared script verbatim. Set `aria-live="polite"` on `#material-progress`, `aria-expanded="false"` on `#quotes-toggle`, and `hidden` on `#quotes`.

- [ ] **Step 2: Run this page's structural test**

Run:

```bash
.venv/Scripts/python.exe design/frontend-visual-directions-2026-11-01/test_pages.py VisualPagesTest.test_clear_campus
```

Expected: `OK`. The other two pages are intentionally still absent.

---

### Task 3: Paper Archive Page

**Files:**
- Create: `design/frontend-visual-directions-2026-11-01/paper-archive.html`
- Test: `design/frontend-visual-directions-2026-11-01/test_pages.py`

**Interfaces:**
- Consumes: the same content, element IDs, functions, and local navigation as Task 2.
- Produces: a responsive page with `data-page="paper"` and `--accent: #a43228`.

- [ ] **Step 1: Implement the complete standalone page**

Use the same semantic content and shared script as the clear page, but express the editorial direction rather than recoloring rounded cards. Put a masthead above a ruled two-column answer sheet. Use section numbers `01`, `02`, and `03`, serif display headings, bracketed source labels, and a small “已核验” seal. Keep the question form and all controls fully functional.

Use these exact tokens and required rules:

```css
:root {
  --bg: #eee9df;
  --surface: #fbf8f0;
  --ink: #211f1a;
  --muted: #746d60;
  --line: #cfc5b4;
  --accent: #a43228;
  --accent-soft: #f1dfd7;
  --warm: #a43228;
  color-scheme: light;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }
h1, h2, blockquote { font-family: Georgia, "Songti SC", "SimSun", serif; }
button, input { font: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; }
[hidden] { display: none !important; }
.demo-nav a[aria-current="page"] { color: var(--accent); text-decoration: underline; text-underline-offset: 5px; }
.answer-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(280px, .85fr); border-top: 3px solid var(--ink); }
.sheet-section { border-bottom: 1px solid var(--line); padding: 22px 0; }
@media (max-width: 760px) {
  .answer-grid { grid-template-columns: 1fr; }
  .demo-nav { overflow-x: auto; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; animation: none !important; }
}
```

Use squared controls and thin rules instead of floating cards. Add the same three material inputs, `#material-progress` with `aria-live="polite"`, the quotes disclosure, all local page links, and the shared script verbatim.

- [ ] **Step 2: Run this page's structural test**

Run:

```bash
.venv/Scripts/python.exe design/frontend-visual-directions-2026-11-01/test_pages.py VisualPagesTest.test_paper_archive
```

Expected: `OK`.

---

### Task 4: Dark Command Page

**Files:**
- Create: `design/frontend-visual-directions-2026-11-01/dark-command.html`
- Test: `design/frontend-visual-directions-2026-11-01/test_pages.py`

**Interfaces:**
- Consumes: the same content, element IDs, functions, and local navigation as Tasks 2 and 3.
- Produces: a responsive page with `data-page="dark"` and `--accent: #b8f35a`.

- [ ] **Step 1: Implement the complete standalone page**

Use a compact system-status header, a high-contrast question console, and an answer dashboard. The main conclusion occupies the widest panel; material progress and official evidence form secondary panels. Use borders and tonal surfaces rather than glow-heavy effects. Include text labels alongside every status color.

Use these exact tokens and required rules:

```css
:root {
  --bg: #0c1210;
  --surface: #131d19;
  --ink: #eef5ef;
  --muted: #9baba3;
  --line: #2b3a33;
  --accent: #b8f35a;
  --accent-soft: #223522;
  --warm: #ff9c83;
  color-scheme: dark;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }
button, input { font: inherit; }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
[hidden] { display: none !important; }
.demo-nav a[aria-current="page"] { color: var(--accent); border-color: var(--accent); }
.answer-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(280px, .75fr); gap: 16px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; }
@media (max-width: 760px) {
  .answer-grid { grid-template-columns: 1fr; }
  .demo-nav { overflow-x: auto; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; animation: none !important; }
}
```

Add the same sample content, material behavior, quotes disclosure, local navigation, ARIA attributes, and shared script verbatim. Keep body text at least 14px on narrow screens and do not add continuous animation.

- [ ] **Step 2: Run this page's structural test**

Run:

```bash
.venv/Scripts/python.exe design/frontend-visual-directions-2026-11-01/test_pages.py VisualPagesTest.test_dark_command
```

Expected: `OK`.

---

### Task 5: Full Static and Browser Verification

**Files:**
- Test: all three HTML files and `test_pages.py`
- Verify unchanged: `web-next/`, `app.py`, `/`, `/classic`

**Interfaces:**
- Consumes: all completed pages and the backup from Task 1.
- Produces: three user-openable previews, actual desktop and narrow-screen render checks, and evidence that rollback assets remain intact.

- [ ] **Step 1: Run all structural tests**

Run:

```bash
.venv/Scripts/python.exe design/frontend-visual-directions-2026-11-01/test_pages.py
```

Expected: three tests pass and the final line is `OK`.

- [ ] **Step 2: Verify the production frontend still equals the backup**

Run:

```bash
diff -qr web-next _backups/web-next-before-visual-directions-2026-11-01
```

Expected: exit 0 with no output. If any difference appears, stop and report it rather than overwriting either copy.

- [ ] **Step 3: Serve only the design directory**

Run in the background:

```bash
.venv/Scripts/python.exe -m http.server 8094 --bind 127.0.0.1 --directory design/frontend-visual-directions-2026-11-01
```

Open `http://127.0.0.1:8094/clear-campus.html`, `paper-archive.html`, and `dark-command.html` in separate controlled browser tabs. This preview server does not replace the application server on port 8000.

- [ ] **Step 4: Verify each desktop page at 1440×900**

For every page, use Browser Agent accessibility state plus a screenshot and perform these exact checks:

1. Click “答案状态”; assert `#view-answer` is visible and `#view-empty` is hidden.
2. Click “空状态”; assert the reverse.
3. Click the “成绩单” sample; assert `#question` contains “开成绩单要带什么” and retains keyboard focus.
4. Submit the demo; assert the answer view appears and `#answer-title` receives focus.
5. Check one material; assert `#material-progress` changes from `0 / 3 已备齐` to `1 / 3 已备齐`.
6. Activate `#quotes-toggle`; assert `aria-expanded="true"` and `#quotes` is visible.
7. Follow both other local design links and use browser Back; assert no 404 and no external navigation.
8. Read browser console logs; assert no JavaScript errors.

- [ ] **Step 5: Verify each narrow page at 400×844**

Set the controlled browser viewport to 400×844, reload each page, and check:

1. No horizontal document overflow: `document.documentElement.scrollWidth <= window.innerWidth`.
2. The answer grid has one column and all material controls remain reachable.
3. Navigation can scroll horizontally without covering the question form.
4. Body text remains readable and keyboard focus remains visible.
5. Repeat material and quotes interactions once per page.

Restore the original browser viewport afterward.

- [ ] **Step 6: Confirm existing application routes remain available**

With the existing application server still running on port 8000, run:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/classic
```

Expected: two lines, each `200`. These are availability checks only; do not replace either page with a visual draft.

- [ ] **Step 7: Deliver the comparison**

Provide direct absolute-path links to all three HTML files. Keep one controlled comparison tab as a browser deliverable and show representative screenshots of all three directions. State exactly which automated and browser checks passed. Do not claim that a direction has been selected or integrated into the production frontend.
