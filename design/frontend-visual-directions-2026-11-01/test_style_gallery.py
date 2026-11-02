from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

import generate_style_gallery as gallery


ROOT = Path(__file__).resolve().parent
EXISTING = ["clear-campus.html", "paper-archive.html", "dark-command.html"]
NEW_THEMES = {f'{theme["slug"]}.html': theme["name"] for theme in gallery.THEMES}
FIELD_THEMES = [theme for theme in gallery.THEMES if theme.get("field")]
FIELD_PAGES = [f'{theme["slug"]}.html' for theme in FIELD_THEMES]
PAGE_NUMBERS = {f'{theme["slug"]}.html': theme["number"] for theme in gallery.THEMES}

# 字幕词表要求（用户 2026-11-02 定）：默认第一帧是 CUC 且整轮多出现，去掉 20 YUAN，补 LOCATION。
REEL_LEAD = "CUC"
REEL_LEAD_MIN = 3
REEL_REQUIRED = ("CUC", "LOCATION")
REEL_BANNED = "20 YUAN"
REEL_SECONDS_PER_ROW = 2.5
REEL_MIN_SECONDS_PER_ROW = 2.2

APPLE_PAGES = [
    "aurora-glass.html",
    "graphite-halo.html",
    "silver-studio.html",
    "deep-blue-focus.html",
    "spectrum-prism.html",
]

# (页内文件名, 说明, 从生成 HTML 中取色的正则, 参照色, 最低对比度)
# 参照色是该主题「最不利」的合成背景：正文渐变色叠上环境染色层与指针光斑后压暗（或提亮）的极端值，
# 由 generate_style_gallery.py 中的实际色值算出。两个色都参与对比度计算，角色无关。
# 正文与小字要求 4.5:1（WCAG AA），≥48px 大标题只要求 3:1。
CONTRAST_AUDIT = {
    "aurora-glass.html": [
        ("辅助文字 --muted", r"--muted: (#[0-9a-fA-F]{6})", "#aac6fe", 4.5),
        ("强调小字 --accent", r"--accent: (#[0-9a-fA-F]{6})", "#aac6fe", 4.5),
        ("返回链接", r"\.back-link \{ border: 0; color: (#[0-9a-fA-F]{6})", "#aac6fe", 4.5),
        ("风格标签", r"\.style-tag \{ background: rgba\(255,255,255,\.42\); color: (#[0-9a-fA-F]{6})", "#aac6fe", 4.5),
        ("卡片小标题", r"\.answer-grid span, \.answer-kicker \{ color: (#[0-9a-fA-F]{6})", "#aac6fe", 4.5),
        ("主按钮文字", r"\.primary-button \{ border: 0; border-radius: 18px; background: (#[0-9a-fA-F]{6})", "#ffffff", 4.5),
        ("大标题中段", r"h1 em \{ background: linear-gradient\(110deg, #[0-9a-fA-F]{6}, (#[0-9a-fA-F]{6}) 48%", "#aac6fe", 3.0),
    ],
    "graphite-halo.html": [
        ("辅助文字 --muted", r"--muted: (#[0-9a-fA-F]{6})", "#2f3750", 4.5),
        ("kicker 与卡片小标题", r"\.kicker, \.answer-kicker, \.answer-grid span \{ color: (#[0-9a-fA-F]{6})", "#2f3750", 4.5),
        ("风格标签", r"\.style-tag \{ background: rgba\(255,255,255,\.035\); color: (#[0-9a-fA-F]{6})", "#2f3750", 4.5),
        ("示例按钮", r"\.sample-row button \{ background: rgba\(255,255,255,\.035\); border-color: rgba\(255,255,255,\.1\); color: (#[0-9a-fA-F]{6})", "#2f3750", 4.5),
        ("返回链接", r"\.back-link \{ border-bottom-color: rgba\(255,255,255,\.25\); color: (#[0-9a-fA-F]{6})", "#2f3750", 4.5),
        ("主按钮文字", r"\.primary-button \{ background: (#[0-9a-fA-F]{6}); color: #11141b", "#11141b", 4.5),
    ],
    "silver-studio.html": [
        ("辅助文字 --muted", r"--muted: (#[0-9a-fA-F]{6})", "#e7eaef", 4.5),
        ("kicker", r"\.kicker \{ color: (#[0-9a-fA-F]{6})", "#e7eaef", 4.5),
        ("风格标签", r"\.style-tag \{ background: rgba\(255,255,255,\.48\); border-color: rgba\(255,255,255,\.85\); color: (#[0-9a-fA-F]{6})", "#e7eaef", 4.5),
        ("卡片小标题", r"\.answer-grid span, \.answer-kicker \{ color: (#[0-9a-fA-F]{6})", "#e7eaef", 4.5),
        ("大标题中段", r"h1 em \{ background: linear-gradient\(100deg, #[0-9a-fA-F]{6} 5%, (#[0-9a-fA-F]{6}) 48%", "#e7eaef", 3.0),
    ],
    "deep-blue-focus.html": [
        ("辅助文字 --muted", r"--muted: (#[0-9a-fA-F]{6})", "#143650", 4.5),
        ("kicker 与卡片小标题", r"\.kicker, \.answer-kicker, \.answer-grid span \{ color: (#[0-9a-fA-F]{6})", "#143650", 4.5),
        ("风格标签", r"\.style-tag \{ background: rgba\(125,211,252,\.05\); color: (#[0-9a-fA-F]{6})", "#143650", 4.5),
        ("示例按钮", r"\.sample-row button \{ background: rgba\(125,211,252,\.04\); color: (#[0-9a-fA-F]{6})", "#143650", 4.5),
        ("返回链接", r"\.back-link \{ color: (#[0-9a-fA-F]{6})", "#143650", 4.5),
        ("主按钮文字", r"\.primary-button \{ background: (#[0-9a-fA-F]{6}); color: #062033", "#062033", 4.5),
    ],
    "spectrum-prism.html": [
        ("辅助文字 --muted", r"--muted: (#[0-9a-fA-F]{6})", "#e2ddf6", 4.5),
        ("强调小字 --accent", r"--accent: (#[0-9a-fA-F]{6})", "#e2ddf6", 4.5),
        ("风格标签", r"\.style-tag \{ background: rgba\(255,255,255,\.4\); color: (#[0-9a-fA-F]{6})", "#e2ddf6", 4.5),
        ("卡片小标题", r"\.answer-grid span, \.answer-kicker \{ color: (#[0-9a-fA-F]{6})", "#e2ddf6", 4.5),
        ("大标题中段", r"h1 em \{ background: linear-gradient\(100deg, #[0-9a-fA-F]{6}, (#[0-9a-fA-F]{6}) 52%", "#e2ddf6", 3.0),
    ],
}


def composite(foreground, background, opacity):
    """前景色以 opacity 的不透明度压在后景上的合成结果，用于算环境染色层下的最不利底色。"""
    first = foreground.lstrip("#")
    second = background.lstrip("#")
    channels = []
    for index in (0, 2, 4):
        top = int(first[index:index + 2], 16)
        bottom = int(second[index:index + 2], 16)
        channels.append(round(top * opacity + bottom * (1 - opacity)))
    return "#" + "".join(f"{value:02x}" for value in channels)


AMBIENT_OPACITY = float(re.search(r"\.field \.ambient \{ opacity: ([\d.]+)", gallery.FIELD_BASE_CSS).group(1))


def field_contrast_audit():
    audit = {}
    for theme in FIELD_THEMES:
        tinted_page = composite(theme["accent"], "#ffffff", AMBIENT_OPACITY)
        audit[f'{theme["slug"]}.html'] = [
            ("辅助文字 --muted", r"--muted: (#[0-9a-fA-F]{6})", tinted_page, 4.5),
            ("强调色块上的文字 --accent-ink", r"--accent-ink: (#[0-9a-fA-F]{6})", theme["accent"], 4.5),
            ("巨型字标正文", r"\.field \.rotate span \{[^}]*color: (var\(--ink\)|#[0-9a-fA-F]{6})", "#ffffff", 4.5),
            ("胶囊导航文字", r"\.field \.topbar \{[^}]*color: (#[0-9a-fA-F]{6})", "#111111", 4.5),
        ]
    return audit


CONTRAST_AUDIT.update(field_contrast_audit())


def _srgb_channel(value):
    value /= 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _relative_luminance(color):
    digits = color.lstrip("#")
    red, green, blue = (int(digits[index:index + 2], 16) for index in (0, 2, 4))
    return 0.2126 * _srgb_channel(red) + 0.7152 * _srgb_channel(green) + 0.0722 * _srgb_channel(blue)


def contrast_ratio(first, second):
    lighter, darker = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


class GalleryParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.has_main = False
        self.has_viewport = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "main":
            self.has_main = True
        if tag == "meta" and attrs.get("name") == "viewport":
            self.has_viewport = True
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])


class StyleGalleryTests(unittest.TestCase):
    def test_gallery_contains_all_pages(self):
        missing = [name for name in EXISTING + list(NEW_THEMES) if not (ROOT / name).is_file()]
        self.assertEqual([], missing)

    def test_new_pages_are_self_contained_and_responsive(self):
        for filename, theme_name in NEW_THEMES.items():
            with self.subTest(filename=filename):
                path = ROOT / filename
                self.assertTrue(path.is_file(), filename)
                html = path.read_text(encoding="utf-8")
                parser = GalleryParser()
                parser.feed(html)
                self.assertIn("<!DOCTYPE html>", html[:100])
                self.assertIn('lang="zh-CN"', html)
                self.assertTrue(parser.has_main)
                self.assertTrue(parser.has_viewport)
                self.assertIn("<style>", html)
                self.assertIn("@media (max-width: 720px)", html)
                self.assertIn("prefers-reduced-motion", html)
                self.assertIn(theme_name, html)
                self.assertIn("校园卡丢了怎么办", html)
                self.assertIn("校园卡补卡", html)
                self.assertIn("index.html", parser.links)
                self.assertTrue({"question", "question-form", "answer"}.issubset(parser.ids))
                self.assertNotRegex(html, r"<(?:script|img|link|iframe)\b[^>]*(?:src|href)=[\"']https?://")
                self.assertNotIn("fetch(", html)
                self.assertNotIn("localStorage", html)

    def test_apple_pages_load_one_script(self):
        for filename in APPLE_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                self.assertEqual(1, html.count("<script"), f"{filename} attaches duplicate handlers")

    def test_apple_pages_scope_shared_rules_and_consume_motion_variables(self):
        for filename in APPLE_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                slug = filename.removesuffix(".html")
                self.assertIn(f'class="{slug} apple"', html)
                self.assertIn(".apple .demo { grid-template-columns: 1fr; }", html)
                self.assertIn("var(--pointer-x)", html)
                self.assertIn("var(--pointer-y)", html)
                self.assertIn("var(--scroll-shift)", html)

    def test_apple_pages_move_background_layers_with_scroll(self):
        for filename in APPLE_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                rule = r"\.apple \.ambient (i|b|span) \{ translate: 0 calc\(var\(--scroll-shift\) \* (-?[\d.]+)\)"
                layers = dict(re.findall(rule, html))
                self.assertEqual({"i", "b", "span"}, set(layers), f"{filename} 背景层不齐，滚动时无纵深：{layers}")
                speeds = {float(value) for value in layers.values()}
                self.assertEqual(3, len(speeds), f"{filename} 各层速度未分层：{layers}")
                self.assertTrue(
                    any(value < 0 for value in speeds) and any(value > 0 for value in speeds),
                    f"{filename} 背景层没有反向位移，滚动时图形不会重新排布：{layers}",
                )
                self.assertIn("rotate: calc(var(--scroll-progress)", html, f"{filename} 缺少滚动驱动的旋转")
                self.assertIn("scrollHeight", html, f"{filename} 位移仍按固定像素封顶，未按整页进度")

    def assertRule(self, html, pattern, message):
        self.assertTrue(re.search(pattern, html), message)

    def test_field_pages_are_flat_not_glass(self):
        for filename in FIELD_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                slug = filename.removesuffix(".html")
                self.assertIn(f'class="{slug} field"', html, f"{filename} 没有 field 作用域，扁平规则不会生效")
                self.assertNotIn("backdrop-filter", html, f"{filename} 仍在用玻璃拟态，与这套语言相反")
                self.assertNotIn("filter: blur", html, f"{filename} 仍在用模糊，图形边缘不该是雾的")
                self.assertIn("--shadow: none", html, f"{filename} 卡片还带投影")
                self.assertRule(html, r"\.field \.query-panel, \.field \.answer \{[^}]*border: 0", f"{filename} 卡片还带描边")

    def test_field_pages_use_metaball_and_equalizer_background(self):
        for filename in FIELD_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                balls = re.findall(r"\.field \.ambient (i|b|span) \{", html)
                self.assertEqual(3, len(set(balls)), f"{filename} 实心圆层不齐，重叠后不会连成一片")
                self.assertRule(html, r"\.field \.ambient (i|b|span)[^{]*\{[^}]*background: var\(--accent\)", f"{filename} 圆形不是同色实心")
                self.assertRule(html, r"\.field \.ambient \{ opacity: \.\d+", f"{filename} 没有整层透明度，重叠处会露出接缝")
                bars = re.findall(r"--h: \d+%", html)
                self.assertGreaterEqual(len(bars), 10, f"{filename} 均衡器条数不足，只有 {len(bars)} 根")
                self.assertIn("@keyframes field-eq", html, f"{filename} 均衡器没有上下泵动的关键帧")
                self.assertIn('</span></div><div class="fx"', html, f"{filename} 均衡器还挂在环境层里，会被整层透明度压到看不见")
                self.assertRule(html, r"\.fx \{[^}]*position: fixed", f"{filename} 均衡器没有钉在视口底部")
                self.assertRule(html, r"\.fx \{[^}]*opacity: \.[5-9]", f"{filename} 均衡器透明度过低，读不出一条能量带")

    def test_field_pages_use_oversized_bleeding_headline(self):
        for filename in FIELD_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                self.assertRule(html, r"\.field h1 \{[^}]*text-transform: uppercase", f"{filename} 巨型字标没有转大写")
                self.assertRule(html, r"\.field h1 \{[^}]*font-size: clamp\([\d.]+px, [\d.]+vw, (1\d{2}|9\d)px", f"{filename} 主标题没有铺到 90px 以上")
                self.assertRule(html, r"\.field h1 \{[^}]*margin-left: clamp\(-", f"{filename} 标题没有向左出血")
                self.assertIn("field-reel", html, f"{filename} 缺少 CSS 轮换字标")
                self.assertRule(html, r"\.field \.rotate \{[^}]*overflow: hidden", f"{filename} 轮换字标没有遮罩，会同时看到两行")
                self.assertRule(html, r"\.field h1 \{[^}]*line-height: 1\.\d", f"{filename} 行距小于 1，中文标题上下两行会碰在一起")
                self.assertRule(html, r"\.field h1 em \{[^}]*display: inline-block", f"{filename} 高亮还是行内盒，色块会按字体 em 盒盖住上一行")
                self.assertRule(html, r"\.field h1 em \{[^}]*line-height: 1[;\s]", f"{filename} 高亮盒没有自己的行高，色块高度失控")

    def test_field_pages_use_floating_pill_navigation(self):
        for filename in FIELD_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                self.assertRule(html, r"\.field \.topbar \{[^}]*position: fixed", f"{filename} 导航仍是文档流里的通栏")
                self.assertRule(html, r"\.field \.topbar \{[^}]*border-radius: 999px", f"{filename} 导航不是胶囊形")
                self.assertRule(html, r"\.field \.back-link \{[^}]*border: 0", f"{filename} 胶囊里还留着下划线")
                self.assertRule(html, r"\.field \.topbar \{[^}]*top: 22px", f"{filename} 胶囊悬在左下角，会压住示例按钮")
                bands = [int(value) for value in re.findall(r"\.field \.page \{[^}]*padding-top: (\d+)px", html)]
                self.assertTrue(bands and min(bands) >= 80, f"{filename} 顶部让位不足 80 像素，正文会顶进胶囊：{bands}")

    def test_field_pages_move_background_layers_with_scroll(self):
        for filename in FIELD_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                rule = r"\.field (?:\.ambient )?(i|b|\.fx) \{ translate: 0 calc\(var\(--scroll-shift\) \* (-?[\d.]+)\)"
                layers = dict(re.findall(rule, html))
                self.assertEqual({"i", "b", ".fx"}, set(layers), f"{filename} 背景层不齐：{layers}")
                speeds = {float(value) for value in layers.values()}
                self.assertEqual(3, len(speeds), f"{filename} 各层速度未分层：{layers}")
                self.assertTrue(
                    any(value < 0 for value in speeds) and any(value > 0 for value in speeds),
                    f"{filename} 背景层没有反向位移：{layers}",
                )
                self.assertIn("rotate: calc(var(--scroll-progress)", html, f"{filename} 缺少滚动驱动的旋转")
                self.assertIn("scrollHeight", html, f"{filename} 位移仍按固定像素封顶")

    def test_field_pages_load_one_script(self):
        for filename in FIELD_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                self.assertEqual(1, html.count("<script"), f"{filename} 挂了多份脚本")

    def test_field_color_variants_keep_one_effect_and_change_only_accent(self):
        accents = [theme["accent"] for theme in FIELD_THEMES]
        self.assertGreaterEqual(len(accents), 7, f"只做了 {len(accents)} 版配色，不够用户挑")
        self.assertEqual(len(accents), len(set(accents)), f"配色重复：{accents}")
        htmls = {filename: (ROOT / filename).read_text(encoding="utf-8") for filename in FIELD_PAGES}
        reference = htmls[FIELD_PAGES[0]]
        for filename, html in htmls.items():
            with self.subTest(filename=filename):
                for token in ("field-reel", "field-eq", "field-drift-a", ".field .fx", '<div class="fx"'):
                    self.assertIn(token, html, f"{filename} 缺 {token}，这版效果的动效没带过来")
                self.assertEqual(
                    len(re.findall(r"\.field \.ambient (i|b|span) \{", reference)),
                    len(re.findall(r"\.field \.ambient (i|b|span) \{", html)),
                    f"{filename} 背景圆结构和基准版不一致",
                )
                self.assertEqual(
                    len(re.findall(r'--h: \d+%', reference)),
                    len(re.findall(r'--h: \d+%', html)),
                    f"{filename} 均衡器条数和基准版不一致",
                )

    def test_field_accent_block_text_routes_through_one_token(self):
        for filename in FIELD_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                for selector in (r"\.field h1 em", r"\.field \.style-tag", r"\.field \.status", r"\.field \.primary-button"):
                    self.assertRule(
                        html, selector + r" \{[^}]*background: var\(--accent\); color: var\(--accent-ink\)",
                        f"{filename} 的 {selector} 没走 --accent-ink，换深色强调时会写出读不出的组合",
                    )

    def test_field_reel_loops_without_blank_frame(self):
        for filename in FIELD_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                strip = re.search(r'<div class="rotate"[^>]*><div class="rotate-inner">(.*?)</div></div>', html, re.S)
                self.assertTrue(strip, f"{filename} 找不到轮换字标")
                rows = re.findall(r"<span>([^<]+)</span>", strip.group(1))
                self.assertGreaterEqual(len(rows), 5, f"{filename} 字标只有 {rows}，末行无法复制首行无缝循环")
                self.assertEqual(REEL_LEAD, rows[0], f"{filename} 进入页面看到的第一个词不是 {REEL_LEAD}：{rows}")
                self.assertEqual(rows[0], rows[-1], f"{filename} 末行不是首行的复制，循环回到开头会跳字：{rows}")
                content = rows[:-1]
                self.assertGreaterEqual(content.count(REEL_LEAD), REEL_LEAD_MIN,
                                        f"{filename} {REEL_LEAD} 一轮只出现 {content.count(REEL_LEAD)} 次，出现频率没提高：{content}")
                others = [row for row in content if row != REEL_LEAD]
                self.assertEqual(len(others), len(set(others)), f"{filename} 除 {REEL_LEAD} 外的内容行有重复：{content}")
                self.assertGreaterEqual(len(others), 6, f"{filename} 词条只有 {len(others)} 条，滚动库没变大：{content}")
                self.assertNotIn(REEL_BANNED, content, f"{filename} 还留着 {REEL_BANNED}")
                for word in REEL_REQUIRED:
                    self.assertIn(word, content, f"{filename} 词表缺 {word}：{content}")
                keyframes = re.search(r"@keyframes field-reel \{(.*?)\n\}", html, re.S)
                self.assertTrue(keyframes, f"{filename} 找不到 field-reel 关键帧")
                shifts = [float(value) for value in re.findall(r"translateY\(-([\d.]+)%\)", keyframes.group(1))]
                self.assertTrue(shifts, f"{filename} field-reel 没有位移帧")
                expected = (len(rows) - 1) / len(rows) * 100
                self.assertAlmostEqual(expected, max(shifts), places=2,
                                       msg=f"{filename} 最大位移 -{max(shifts)}% 不等于 -{expected}%，末帧会露出空白")

    def test_field_reel_reads_at_two_and_a_half_seconds_per_row(self):
        for filename in FIELD_PAGES:
            with self.subTest(filename=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                strip = re.search(r'<div class="rotate"[^>]*><div class="rotate-inner">(.*?)</div></div>', html, re.S)
                row_count = len(re.findall(r"<span>([^<]+)</span>", strip.group(1))) - 1
                pace = re.search(r"animation: field-reel ([\d.]+)s", html)
                self.assertTrue(pace, f"{filename} 读不到 field-reel 的时长")
                seconds_per_row = float(pace.group(1)) / row_count
                self.assertAlmostEqual(REEL_SECONDS_PER_ROW, seconds_per_row, places=1,
                                       msg=f"{filename} {row_count} 条词跑 {pace.group(1)}s，每条 {seconds_per_row:.2f}s，不是每条 {REEL_SECONDS_PER_ROW}s")
                self.assertGreaterEqual(seconds_per_row, REEL_MIN_SECONDS_PER_ROW,
                                        f"{filename} 每条只停 {seconds_per_row:.2f}s，大字来不及读完")

    def resolve_color(self, html, value):
        match = re.fullmatch(r"var\(--([a-z-]+)\)", value)
        if not match:
            return value
        tokens = dict(re.findall(r"--([a-z-]+): (#[0-9a-fA-F]{6})", html))
        self.assertIn(match.group(1), tokens, f"页面里没有 --{match.group(1)} 的色值，无法核对对比度")
        return tokens[match.group(1)]

    def test_audited_pages_small_text_meets_wcag_aa(self):
        for filename, entries in CONTRAST_AUDIT.items():
            html = (ROOT / filename).read_text(encoding="utf-8")
            for label, pattern, reference, minimum in entries:
                with self.subTest(filename=filename, element=label):
                    matches = re.findall(pattern, html)
                    self.assertTrue(matches, f"{filename}: {label} 规则被改写，需同步对比度断言")
                    color = self.resolve_color(html, matches[-1])
                    reference = self.resolve_color(html, reference)
                    ratio = contrast_ratio(color, reference)
                    self.assertGreaterEqual(
                        round(ratio, 2), minimum,
                        f"{filename}: {label} {color} 对 {reference} 仅 {ratio:.2f}:1，要求 {minimum}:1",
                    )

    def test_index_links_to_all_styles(self):
        path = ROOT / "index.html"
        self.assertTrue(path.is_file())
        html = path.read_text(encoding="utf-8")
        parser = GalleryParser()
        parser.feed(html)
        for filename in EXISTING + list(NEW_THEMES):
            with self.subTest(link=filename):
                self.assertIn(filename, parser.links)
        total = len(EXISTING) + len(NEW_THEMES)
        self.assertEqual(total, len(re.findall(r'class="style-card"', html)))
        self.assertIn(f"{total} 个方向", html)
        self.assertIn(f"{total} / {total}", html)
        self.assertNotIn("26 个方向", html, "目录仍写着 26 个方向")
        for filename in NEW_THEMES:
            with self.subTest(page_link=filename):
                page = (ROOT / filename).read_text(encoding="utf-8")
                self.assertNotIn("二十六种风格目录", page, f"{filename} 返回链接仍写旧数量")
                self.assertIn(f"风格试验 {PAGE_NUMBERS[filename]} / {total}", page, f"{filename} 页脚编号没更新")
        self.assertTrue(parser.has_viewport)


if __name__ == "__main__":
    unittest.main()
