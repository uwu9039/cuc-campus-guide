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
    "quotes", "quotes-toggle", "answer-title", "source-search", "print-checklist",
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
        for function_name in (
            "setView", "fillQuestion", "submitDemo", "toggleMaterial", "toggleQuotes",
            "findOriginal", "printChecklist",
        ):
            self.assertIn(function_name, text)
        self.assertIn("联系方式", text)
        self.assertIn("校园卡及网络报修：65783878", text)
        self.assertRegex(text, r'<div id="quotes"[^>]*tabindex="-1"[^>]*hidden>')
        self.assertRegex(text, r'</div>\s*<section class="auxiliary-entry"')
        self.assertRegex(text, r'<button id="source-search"[^>]*>\s*搜原文\s*</button>')
        self.assertRegex(text, r'<button id="print-checklist"[^>]*>\s*打印清单\s*</button>')
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
