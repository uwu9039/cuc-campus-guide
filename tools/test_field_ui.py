"""钴蓝场前端 /field 的静态契约测试。

覆盖：路由注册与位置、新文件存在且自包含、主题 token 集中、结果分支顺序与
数据契约、第一期用户反馈的落地（经典版入口 / 概览缺失即隐藏 / 可读性 / 返回键 /
页脚署名 / 主标题 / 校徽）、第二期三块（原文检索 / 联系方式 / 地图）与个人数据留禁用、
生产文件除经典版那一条入口外未被改动（显示层改动按逐行白名单放行，见 DISPLAY_DIFF_OK）。
运行： .venv/Scripts/python.exe -m unittest discover -s tools -p "test_field*.py"
"""
import difflib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web-next"
BACKUP = ROOT / "_backups" / "web-next-before-field-2026-11-02"
NEW_FILES = ("field.html", "field.css", "field.js")
EMBLEM = "assets/cuc-emblem.svg"
ALLOWED_ENDPOINTS = {
    "/api/health", "/api/campus", "/api/ask", "/api/deliver", "/api/search", "/api/contacts",
}
PHASE_TWO_LABELS = ("地图", "原文检索", "联系方式", "个人数据")
PHASE_TWO_KINDS = {"地图": "map", "原文检索": "search", "联系方式": "contacts", "个人数据": "personal"}
LOCKED_LABEL = "个人数据"
# 两个官方系统的入口地址以经典版组件里的常量为唯一出处，/field 不许各写一份
PERSONAL_SOURCES = ("CARD_URL", "COURSES_URL")


def read(name):
    return (WEB / name).read_text(encoding="utf-8")


def diff_lines(old_path, new_path):
    """改前/改后之间的 ± 行，排序后比。同一行改两处要算两条，不靠出现顺序。"""
    old = old_path.read_text(encoding="utf-8").splitlines()
    new = new_path.read_text(encoding="utf-8").splitlines()
    return sorted(line for line in difflib.unified_diff(old, new, lineterm="", n=0)
                  if line[:1] in "+-" and not line.startswith(("+++", "---")))


# 显示层白名单（2026-11-03 用户点名的一类改动，逐行核过之后写死在这里）：
#   甲 大字里不出现 .docx/.pdf 这类来源后缀：渲染处套一层 docName(...)，
#     data-ask / data-alt 仍原样发，路由一个字都没动；
#   乙 选项点击带上条目 id：加 pickAttr 与 { pick: … }，治好「点完选项又摊回同一份菜单」。
# 放行的是这几行差异，不是这两个文件：清单里多不出来、也少不了一条，
# 想在白名单外改任何东西，照样红。要新增放行必须本人复看后逐行加进来。
CLASSIC_DISPLAY_DIFF = [
    "+// 条目名里的来源后缀（· 图书馆手册.docx）只给检索用，不进给用户看的话；data-alt 仍原样发。",
    "+const docName = (s) => String(s ?? \"\").replace(/\\.(docx|xlsx|pptx|pdf|doc|xls|ppt|txt|md|wps)\\b/gi, \"\");",
    "-        `<button class=\"opt\" data-alt=\"${esc(b.title)}\">${esc(b.label || b.title)}${b.dept ? `<span class=\"odept\">${esc(b.dept)}</span>` : \"\"}</button>`).join(\"\")}</div></div>`",
    "+        `<button class=\"opt\" data-alt=\"${esc(b.title)}\">${esc(docName(b.label || b.title))}${b.dept ? `<span class=\"odept\">${esc(b.dept)}</span>` : \"\"}</button>`).join(\"\")}</div></div>`",
    "-    `<button class=\"opt\" data-alt=\"${esc(b.title)}\">${esc(b.label || b.title)}${b.dept ? `<span class=\"odept\">${esc(b.dept)}</span>` : \"\"}</button>`).join(\"\");",
    "+    `<button class=\"opt\" data-alt=\"${esc(b.title)}\">${esc(docName(b.label || b.title))}${b.dept ? `<span class=\"odept\">${esc(b.dept)}</span>` : \"\"}</button>`).join(\"\");",
    "-        `<button class=\"opt\" data-alt=\"${esc(b.title)}\">${esc(b.label || b.title)}${b.dept ? `<span class=\"odept\">${esc(b.dept)}</span>` : \"\"}</button>`).join(\"\")}</div></div>`",
    "+        `<button class=\"opt\" data-alt=\"${esc(b.title)}\">${esc(docName(b.label || b.title))}${b.dept ? `<span class=\"odept\">${esc(b.dept)}</span>` : \"\"}</button>`).join(\"\")}</div></div>`",
    "-    <div class=\"ht\"><span>${esc(h.title)}</span><span class=\"hk\">${esc(h.kind)}${h.page ? \" · \" + esc(h.page) : \"\"}</span></div>",
    "+    <div class=\"ht\"><span>${esc(docName(h.title))}</span><span class=\"hk\">${esc(h.kind)}${h.page ? \" · \" + esc(h.page) : \"\"}</span></div>",
    "-  const alts = (r.alternatives || []).map((a) => `<span class=\"chip\" data-alt=\"${esc(a.title)}\">${esc(a.title)}</span>`).join(\"\");",
    "-  const related = (r.related_items || []).map((a) => `<span class=\"chip\" data-alt=\"${esc(a.title)}\">${esc(a.label || a.title)}</span>`).join(\"\");",
    "+  const alts = (r.alternatives || []).map((a) => `<span class=\"chip\" data-alt=\"${esc(a.title)}\">${esc(docName(a.title))}</span>`).join(\"\");",
    "+  const related = (r.related_items || []).map((a) => `<span class=\"chip\" data-alt=\"${esc(a.title)}\">${esc(docName(a.label || a.title))}</span>`).join(\"\");",
    "-    .map((a) => `<span class=\"chip\" data-alt=\"${esc(a.title)}\">${esc(a.title)}</span>`).join(\"\");",
    "+    .map((a) => `<span class=\"chip\" data-alt=\"${esc(a.title)}\">${esc(docName(a.title))}</span>`).join(\"\");",
    "-      <div><div class=\"t\">${esc(item.title)} ${badge}</div>",
    "+      <div><div class=\"t\">${esc(docName(item.title))} ${badge}</div>",
]
APPJS_DISPLAY_DIFF = [
    "+  // 反问菜单的选项带条目 id：点下去按 id 打开那一条，别再拿标题重新路由一遍",
    "+  const pickAttr = (b) => (b && b.id ? ` data-pick=\"${esc(b.id)}\"` : \"\");",
    "+  // 条目名里的「· 图书馆手册.docx」这类来源后缀只给检索用，不进给用户看的话。",
    "+  // 只改显示，data-ask 原样发，免得动到路由。",
    "+  const docName = (s) => String(s == null ? \"\" : s)",
    "+    .replace(/\\.(docx|xlsx|pptx|pdf|doc|xls|ppt|txt|md|wps)\\b/gi, \"\");",
    "+        // 点选项时带上条目 id：只按标题重新问，同一句词会再摊出同一份菜单",
    "+        pick_item: opts.pick || null,",
    "-      `<button class=\"opt\" type=\"button\" data-ask=\"${esc(b.title)}\">${esc(b.label || b.title)}<span class=\"odept\">${esc(b.dept || \"\")}</span></button>`).join(\"\");",
    "+      `<button class=\"opt\" type=\"button\" data-ask=\"${esc(b.title)}\"${pickAttr(b)}>${esc(docName(b.label || b.title))}<span class=\"odept\">${esc(b.dept || \"\")}</span></button>`).join(\"\");",
    "-        <span class=\"cfstamp\">NO.${String(state.exCount).padStart(3, \"0\")} / 条目 ${esc(item.title || \"\")}</span>",
    "+        <span class=\"cfstamp\">NO.${String(state.exCount).padStart(3, \"0\")} / 条目 ${esc(docName(item.title))}</span>",
    "-      `<button class=\"opt\" type=\"button\" data-ask=\"${esc(b.title)}\">${esc(b.label || b.title)}<span class=\"odept\">${esc(b.dept || \"\")}</span></button>`).join(\"\");",
    "+      `<button class=\"opt\" type=\"button\" data-ask=\"${esc(b.title)}\"${pickAttr(b)}>${esc(docName(b.label || b.title))}<span class=\"odept\">${esc(b.dept || \"\")}</span></button>`).join(\"\");",
    "-        <div class=\"ht\">${esc(h.title || \"原文段落\")}</div>",
    "+        <div class=\"ht\">${esc(docName(h.title) || \"原文段落\")}</div>",
    "-      `<button class=\"opt\" type=\"button\" data-ask=\"${esc(a.title)}\">${esc(a.title)}</button>`).join(\"\");",
    "+      `<button class=\"opt\" type=\"button\" data-ask=\"${esc(a.title)}\">${esc(docName(a.title))}</button>`).join(\"\");",
    "-      `<button class=\"opt\" type=\"button\" data-ask=\"${esc(b.title)}\">${esc(b.title)}<span class=\"odept\">${esc(b.dept || \"\")}</span></button>`).join(\"\");",
    "+      `<button class=\"opt\" type=\"button\" data-ask=\"${esc(b.title)}\"${pickAttr(b)}>${esc(docName(b.title))}<span class=\"odept\">${esc(b.dept || \"\")}</span></button>`).join(\"\");",
    "-      `<button class=\"opt\" type=\"button\" data-ask=\"${esc(a.title)}\">${esc(a.label || a.title)}</button>`).join(\"\");",
    "+      `<button class=\"opt\" type=\"button\" data-ask=\"${esc(a.title)}\">${esc(docName(a.label || a.title))}</button>`).join(\"\");",
    "-    el.title.textContent = item.title;",
    "+    el.title.textContent = docName(item.title);",
    "-      `${item.title}（${item.dept || \"\"}）`,",
    "+      `${docName(item.title)}（${item.dept || \"\"}）`,",
    "-    el.printsheet.innerHTML = `<h1>${esc(item.title)}</h1>",
    "+    el.printsheet.innerHTML = `<h1>${esc(docName(item.title))}</h1>",
    "-          <h3>${esc(h.title || \"原文段落\")}</h3>",
    "+          <h3>${esc(docName(h.title) || \"原文段落\")}</h3>",
    "-      if (t.dataset.ask) { e.preventDefault(); el.q.value = t.dataset.ask; ask(t.dataset.ask); return; }",
    "+      if (t.dataset.ask) { e.preventDefault(); el.q.value = t.dataset.ask; ask(t.dataset.ask, { pick: t.dataset.pick }); return; }",
    "-        ask(askBtn.dataset.ask);",
    "+        ask(askBtn.dataset.ask, { pick: askBtn.dataset.pick });",
    "-        copyText(`${item.title}\\n${mats.map((m) => \"□ \" + m).join(\"\\n\")}`, \"材料清单已复制\");",
    "+        copyText(`${docName(item.title)}\\n${mats.map((m) => \"□ \" + m).join(\"\\n\")}`, \"材料清单已复制\");",
]
# 文件名 → 放行的差异行；classic.html 那份还要叠上页脚版本号那一处
DISPLAY_DIFF_OK = {"app.js": APPJS_DISPLAY_DIFF}


def js_region(source, start, end):
    """取 field.js 里某一块代码：从 start 标记到下一个 end 标记之间。"""
    at = source.index(start)
    stop = source.index(end, at + len(start))
    return source[at:stop]


def root_blocks(css):
    """返回 :root 规则块的字符区间，用于检查颜色字面量是否只出现在 token 定义里。"""
    spans = []
    for match in re.finditer(r":root[^{]*\{", css):
        depth = 0
        start = match.end() - 1
        for index in range(start, len(css)):
            if css[index] == "{":
                depth += 1
            elif css[index] == "}":
                depth -= 1
                if depth == 0:
                    spans.append((match.start(), index + 1))
                    break
    return spans


def strip_root_blocks(css):
    outside = css
    for start, end in sorted(root_blocks(css), reverse=True):
        outside = outside[:start] + outside[end:]
    return outside


class RouteTest(unittest.TestCase):
    def routes(self, path):
        sys.path.insert(0, str(ROOT))
        import app as backend

        return [r for r in backend.app.routes if getattr(r, "path", None) == path]

    def test_field_route_is_registered_before_static_mount(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('@app.get("/field")', source, "app.py 没有 /field 路由")
        mount = source.index('app.mount("/", StaticFiles')
        self.assertLess(source.index('@app.get("/field")'), mount, "/field 必须注册在静态挂载之前")
        # / 与 /desk 同样要抢在挂载之前，否则 / 会被静态目录里的 index.html 吃掉
        for deco in ('@app.get("/")', '@app.get("/desk")'):
            self.assertIn(deco, source, f"app.py 没有 {deco} 路由")
            self.assertLess(source.index(deco), mount, f"{deco} 必须注册在静态挂载之前")

    def test_field_route_serves_field_html_without_cache(self):
        routes = self.routes("/field")
        self.assertEqual(len(routes), 1, f"/field 路由应恰好一条，实际 {len(routes)}")
        methods = set(routes[0].methods or set())
        self.assertEqual(methods - {"HEAD"}, {"GET"}, "/field 只应接受 GET")
        response = routes[0].endpoint()
        self.assertEqual(Path(str(response.path)).name, "field.html")
        self.assertTrue(str(response.media_type or "").startswith("text/html"))
        self.assertIn("no-store", str(response.headers.get("cache-control", "")))

    def test_root_redirects_to_field(self):
        # 首次进入要落在向导页：/ 不再发文件，改成 302。用 302 不用 301/308，
        # 免得浏览器把跳转缓存死，之后想改入口改不动。
        routes = self.routes("/")
        self.assertEqual(len(routes), 1, f"/ 路由应恰好一条，实际 {len(routes)}")
        response = routes[0].endpoint(self.request(""))
        self.assertEqual(type(response).__name__, "RedirectResponse", "/ 必须重定向，不能再直接发页面文件")
        self.assertEqual(response.status_code, 302, "/ 应返回 302 而不是永久重定向")
        self.assertEqual(response.headers.get("location"), "/field", "/ 要跳到向导页")

    def test_root_redirect_keeps_query_string(self):
        # README 里的演示链接是 /?q=我要开个证明；跳转丢掉查询串，
        # /field 的 presetQuery 就取不到问题，等于把分享链接废了。
        response = self.routes("/")[0].endpoint(self.request("q=%E6%A0%A1%E5%9C%92%E5%8D%A1"))
        self.assertEqual(response.headers.get("location"), "/field?q=%E6%A0%A1%E5%9C%92%E5%8D%A1",
                          "跳转必须原样带上查询串")

    def request(self, query_string):
        from starlette.requests import Request

        return Request({
            "type": "http", "http_version": "1.1", "method": "GET", "scheme": "http",
            "path": "/", "raw_path": b"/", "query_string": query_string.encode("ascii"),
            "root_path": "", "server": ("testserver", 80), "headers": [],
        })

    def test_desk_serves_two_column_page_without_cache(self):
        # 双栏界面挪到 /desk：文件还是原来那份 index.html，只是换了地址
        routes = self.routes("/desk")
        self.assertEqual(len(routes), 1, f"/desk 路由应恰好一条，实际 {len(routes)}")
        response = routes[0].endpoint()
        self.assertEqual(Path(str(response.path)).name, "index.html")
        self.assertTrue(str(response.media_type or "").startswith("text/html"))
        self.assertIn("no-store", str(response.headers.get("cache-control", "")))


class FileTest(unittest.TestCase):
    def test_new_files_exist(self):
        for name in NEW_FILES + (EMBLEM,):
            self.assertTrue((WEB / name).is_file(), f"缺少 {name}")

    def test_html_links_only_local_css_and_js(self):
        html = read("field.html")
        for asset in ("field.css", "field.js"):
            self.assertIn(asset, html, f"field.html 没有引用 {asset}")
        self.assertNotIn('src="http', html)
        self.assertNotIn('href="http', html)
        self.assertNotIn("@import", read("field.css"))
        # 地图要接真底图，但 Leaflet 仍然只准用仓库里的本地副本，不许换成 CDN
        self.assertIn('href="vendor/leaflet/leaflet.css"', html, "地图样式没引本地 Leaflet")
        self.assertIn('src="vendor/leaflet/leaflet.js"', html, "地图脚本没引本地 Leaflet")

    def test_no_external_storage_or_cdn(self):
        blob = "".join(read(name) for name in NEW_FILES)
        for banned in ("localStorage", "sessionStorage", "googleapis", "cdn.", "unpkg", "jsdelivr"):
            self.assertNotIn(banned, blob, f"页面依赖外部资源或本地存储：{banned}")

    def test_emblem_is_self_contained_vector(self):
        # 校徽从中传官网首页那份纯矢量 logo 裁出来，只留徽章本体；不得再引外部图
        svg = (WEB / EMBLEM).read_text(encoding="utf-8")
        self.assertTrue(svg.lstrip().startswith("<svg"), "校徽文件不是 SVG")
        self.assertIn('viewBox="0 0 68 68"', svg, "校徽要裁成方形徽章")
        for banned in ("xlink:href", "<image", "base64"):
            self.assertNotIn(banned, svg, f"校徽里出现了外部引用或位图：{banned}")
        self.assertGreaterEqual(svg.count("<path"), 40, "校徽要是矢量描边，不是简化的圆牌")
        self.assertIn('fill="#fff"', svg, "校徽按官网原样保留白字，界面把它放在钴蓝圆盘上")
        self.assertNotIn("<style", svg, "校徽内部不带样式，颜色交给界面")
        self.assertLess(len(svg), 200_000, "校徽文件过大")


    def test_only_allowed_endpoints_are_called(self):
        blob = read("field.js") + read("field.html")
        called = set(re.findall(r"/api/[a-zA-Z0-9_/-]+", blob))
        unexpected = called - ALLOWED_ENDPOINTS
        self.assertFalse(unexpected, f"调用了契约外的接口：{sorted(unexpected)}")
        for endpoint in ("api/ask", "api/deliver", "api/health", "api/campus", "api/search", "api/contacts"):
            self.assertIn(endpoint, blob, f"缺少对 /{endpoint} 的调用")

    def test_requests_stay_on_this_origin(self):
        # 面板里的外链只能是用户主动点的 a 标签，不能是页面自己发的请求
        js = read("field.js")
        self.assertNotRegex(js, r"fetch\(\s*[\"'`]https?:", "fetch 只能打同源相对路径")
        for banned in ("XMLHttpRequest", "navigator.sendBeacon", "new Image("):
            self.assertNotIn(banned, js, f"页面不该有额外的请求通道：{banned}")


class ThemeTest(unittest.TestCase):
    def test_tokens_are_defined_in_root(self):
        css = read("field.css")
        blocks = root_blocks(css)
        self.assertTrue(blocks, "field.css 没有 :root token 块")
        root_text = "".join(css[start:end] for start, end in blocks)
        for token in ("--bg", "--ink", "--accent", "--accent-ink", "--muted", "--line", "--radius-panel", "--radius-pill"):
            self.assertIn(f"{token}:", root_text, f":root 里缺少 token {token}")
        self.assertIn("#2b5bff", root_text.lower(), "强调色必须是选定的钴蓝")
        self.assertIn('data-theme="cobalt-field"', read("field.html"), "主题身份要由 html data-theme 表达")

    def test_no_hardcoded_colors_outside_root(self):
        outside = strip_root_blocks(read("field.css"))
        offenders = re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", outside)
        self.assertFalse(offenders, f"结构 CSS 里出现裸色值，换主题会漏改：{sorted(set(offenders))}")

    def test_structural_rules_use_variables(self):
        outside = strip_root_blocks(read("field.css"))
        for token in ("var(--bg)", "var(--ink)", "var(--accent)", "var(--line)"):
            self.assertIn(token, outside, f"结构 CSS 没有消费 {token}")


class ReelTest(unittest.TestCase):
    def test_word_pool_keeps_selection_rules(self):
        source = read("field.js")
        pool = re.search(r"FIELD_WORDS\s*=\s*\[([^\]]*)\]", source, re.S)
        self.assertTrue(pool, "field.js 里没有 FIELD_WORDS 词表")
        words = [item.strip().strip('"\'') for item in pool.group(1).replace("\n", "").split(",") if item.strip()]
        self.assertEqual(words[0], "CUC", "进入页面第一帧必须是 CUC")
        self.assertGreaterEqual(words.count("CUC"), 3, "CUC 出现频率要高于其他词")
        self.assertIn("LOCATION", words)
        self.assertNotIn("20 YUAN", words, "用户明确要求去掉 20 YUAN")
        others = [word for word in words if word != "CUC"]
        self.assertGreaterEqual(len(others), 6, "词表要比选型稿更大、更多样")
        self.assertEqual(len(others), len(set(others)), "除刻意多出的 CUC 外，词条不得重复")

    def test_reel_timing_is_two_and_a_half_seconds_per_row(self):
        source = read("field.js")
        timing = re.search(r"REEL_SECONDS_PER_ROW\s*=\s*([\d.]+)", source)
        self.assertTrue(timing, "field.js 里没有 REEL_SECONDS_PER_ROW")
        self.assertAlmostEqual(float(timing.group(1)), 2.5, places=3)
        self.assertNotIn("25s", source, "时长要由词数 × 节奏推导，不能写死")

    def test_reel_loops_without_blank_frame(self):
        source = read("field.js")
        self.assertRegex(source, r"FIELD_WORDS\[0\]", "轮换需要把首行复制到末尾才能无缝循环")
        mask = re.search(r"\.rotate\s*\{[^}]*\}", read("field.css"))
        self.assertTrue(mask and "overflow: hidden" in mask.group(0),
                        ".rotate 自身必须带遮罩，否则会一次露出两行半字")


class ResultContractTest(unittest.TestCase):
    def test_branch_order_matches_main_frontend(self):
        source = read("field.js")
        patterns = [
            ("plan", r"data\.plan\b"),
            ("miss", r"data\.matched\b"),
            ("clarify", r"data\.disambiguate\b|data\.clarify\b"),
            ("hold", r"data\.hold\b|data\.followups\b"),
            ("answers", r"data\.answers\b"),
        ]
        positions = []
        for label, pattern in patterns:
            match = re.search(pattern, source)
            self.assertTrue(match, f"缺少 {label} 分支")
            positions.append((label, match.start()))
        for index in range(len(positions) - 1):
            before, before_at = positions[index]
            after, after_at = positions[index + 1]
            self.assertLess(before_at, after_at, f"{before} 分支必须排在 {after} 之前")

    def test_unverified_item_shows_disclosure_not_invention(self):
        source = read("field.js")
        branch = re.search(r"if \(!a\.found\) \{\s*value = `([^`]*)`", source)
        self.assertTrue(branch, "answers[].found 为假时必须有独立分支")
        self.assertIn("官方页面没有写这一项", branch.group(1), "该分支只能给披露文案，不能替学校补")
        plain = source[source.index("function plainAnswer"):]
        self.assertIn("官方页面没有写这一项", plain, "复制出去的纯文本也要保留披露")

    def test_quotes_keep_all_six_source_fields(self):
        source = read("field.js")
        quote_render = source[source.index("renderQuotes"):] if "renderQuotes" in source else source
        for field in ("quote", "src", "label", "kind", "date", "url"):
            self.assertRegex(quote_render, rf"\.{field}\b|['\"]{field}['\"]", f"引证渲染缺少字段 {field}")

    def test_error_text_reads_all_three_backend_shapes(self):
        source = read("field.js")
        api_body = re.search(r"async function api\([\s\S]*?\n  \}", source)
        self.assertTrue(api_body, "找不到 api() 封装")
        for field in ("error", "detail", "message"):
            self.assertRegex(api_body.group(0), rf"data\.{field}\b", f"api() 没有读 {field}，后端错误文案会被丢掉")

    def test_deep_link_question_is_supported(self):
        self.assertRegex(read("field.js"), r"URLSearchParams[\s\S]{0,80}get\(\s*[\"']q[\"']\s*\)", "/field?q= 深链要能自动提问")

    def test_plan_card_keeps_answers_and_real_major_names(self):
        # 浏览器对齐发现 /field 的转专业卡只列专业、漏了 answers 各面，且用了不存在的字段名
        body = re.search(r"function planCard\(data\)\s*\{([\s\S]*?)\n  \}", read("field.js"))
        self.assertTrue(body, "找不到 planCard()")
        code = body.group(1)
        self.assertRegex(code, r"data\.answers\b[\s\S]{0,40}partHtml", "计划卡要渲染后端给出的 answers 各面")
        self.assertRegex(code, r"name \|\| ", "专业名要取 majors[].name（后端就是这个字段）")
        self.assertIn("转专业到", code, "专业按钮要能直接追问")
        self.assertRegex(code, r"data\.plan_file\b", "计划卡要给出学院接收计划 PDF 链接")
        self.assertRegex(code, r"data\.plan_no_file\b", "未公开 PDF 时要披露")

    def test_miss_card_keeps_every_backend_clue(self):
        body = re.search(r"function missCard\(data\)\s*\{([\s\S]*?)\n  \}", read("field.js"))
        self.assertTrue(body, "找不到 missCard()")
        code = body.group(1)
        for field in ("original_search", "alternatives", "hints", "contacts", "next_actions", "suggestion", "related_items"):
            self.assertRegex(code, rf"data\.{field}\b", f"未命中卡少了后端给出的 {field}，两版内容就不一致了")

    def test_followup_card_keeps_options_and_slots(self):
        body = re.search(r"function holdCard\(data\)\s*\{([\s\S]*?)\n  \}", read("field.js"))
        self.assertTrue(body, "找不到 holdCard()")
        code = body.group(1)
        self.assertRegex(code, r"data\.followups\b[\s\S]{0,400}f\.question", "先确认卡要显示追问原句")
        self.assertRegex(code, r"data-key=\"\$\{esc\(f\.key\)\}\"[\s\S]{0,80}data-opt", "备选项要带 key/opt，点了才能填槽重问")
        self.assertRegex(code, r"\.filter\(\(a\) => a\.found\)", "只能把查证到的部分作为「先给你能确定的部分」")
        self.assertRegex(read("field.js"), r"state\.slots\[slotBtn\.dataset\.key\] = slotBtn\.dataset\.opt", "点击备选后要写回 slots 再用原话重问")

    def test_enter_submits_without_shift(self):
        source = read("field.js")
        handler = re.search(r"el\.q\.addEventListener\(\"keydown\", \(event\) => \{([\s\S]*?)\}\);", source)
        self.assertTrue(handler, "输入框没有 keydown 处理：回车无法提交")
        body = handler.group(1)
        self.assertRegex(body, r"event\.key !== \"Enter\"", "只处理 Enter")
        self.assertRegex(body, r"event\.shiftKey", "Shift+Enter 要留给换行")
        self.assertRegex(body, r"requestSubmit|dispatchEvent\(new Event\(\"submit\"", "回车要走表单提交那一条路径")
        guard = re.search(r"document\.addEventListener\(\"keydown\", \(event\) => \{([\s\S]*?)\}\);", source)
        self.assertTrue(guard, "全局键盘处理缺失")
        self.assertRegex(guard.group(1), r"event\.target === el\.q\) return", "全局勾选处理要让开输入框")

    def test_grid_tracks_cannot_be_pushed_wide(self):
        # 400px 视口实测溢出 925px：裸 1fr 轨道的最小尺寸是 auto，会被横滚条的 min-content 顶宽
        css = read("field.css")
        for line in re.findall(r"grid-template-columns:[^;]*;", css):
            residue = re.sub(r"minmax\([^)]*\)", "", line)
            self.assertNotIn("1fr", residue, f"{line.strip()} 里有裸 1fr 轨道，会被内容顶宽")
        self.assertRegex(css, r"\.workspace > \* \{[^}]*min-width: 0", "栏内元素要允许收缩，否则窄屏会被顶宽")

    def test_answer_slot_is_taken_before_the_nodes_move(self):
        # 线上实测：先搬节点再找 [data-slot] 会拿到 null，答案永远渲染不出来
        body = re.search(r"function addExchange\(text\)\s*\{([\s\S]*?)\n  \}", read("field.js"))
        self.assertTrue(body, "找不到 addExchange()")
        code = body.group(1)
        self.assertIn("wrap.lastElementChild", code, "要先从包装里取出答案槽")
        self.assertLess(code.index("wrap.lastElementChild"), code.index("while (wrap.firstChild)"),
                        "答案槽必须在搬走子节点之前取")
        self.assertRegex(code, r"return slot;", "渲染要返回那个槽")

    def test_note_only_shows_where_classic_shows_it(self):
        # 浏览器对齐发现：经典版只在答案卡与计划卡渲染 d.note，澄清/先确认/未命中卡都不渲染。
        # /field 多渲染一次就是内容不一致，不是呈现差异。
        source = read("field.js")
        for name in ("clarifyCard", "holdCard", "missCard"):
            body = re.search(rf"function {name}\(data\)\s*\{{([\s\S]*?)\n  \}}", source)
            self.assertTrue(body, f"找不到 {name}()")
            self.assertNotIn("noteBlock(", body.group(1), f"{name}() 不该渲染整体备注，经典版没有这一处")
        for name in ("planCard", "answerCard"):
            body = re.search(rf"function {name}\(data\)\s*\{{([\s\S]*?)\n  \}}", source)
            self.assertTrue(body, f"找不到 {name}()")
            self.assertIn("noteBlock(data)", body.group(1), f"{name}() 要渲染后端给的 d.note")
        copy = re.search(r"function plainAnswer\(\)\s*\{([\s\S]*?)\n  \}", source)
        self.assertTrue(copy, "找不到 plainAnswer()")
        self.assertRegex(copy.group(1), r"d\.note", "复制出去的纯文本要带说明，和经典版复制内容一致")


class FeedbackTest(unittest.TestCase):
    """2026-11-02 的七条用户反馈，逐条钉住。"""

    def test_classic_page_links_to_field(self):
        # 反馈 1：经典版没有任何入口能跳到 /field
        html = (WEB / "index.html").read_text(encoding="utf-8")
        link = re.search(r'<a class="ghostbtn" href="/field"[^>]*>([^<]*)</a>', html)
        self.assertTrue(link, "经典版顶栏没有指向 /field 的入口按钮")
        self.assertIn("新版", link.group(1), "入口文案要说清这是新版")

    def test_overview_hides_rows_the_school_never_stated(self):
        # 反馈 2：概览里「官方页面没有写这一项」刷屏，缺失就整行不显示
        body = re.search(r"function renderOverview\(item\)\s*\{([\s\S]*?)\n  \}", read("field.js"))
        self.assertTrue(body, "找不到 renderOverview()")
        code = body.group(1)
        self.assertRegex(code, r"\.filter\(", "缺失字段要先过滤掉，不留空行")
        self.assertNotIn("none-tag", code, "概览不再给缺失项挂「官方页面没有写这一项」标签")
        self.assertNotIn("官方页面没有写", code, "概览里不出现这条披露文案")
        self.assertNotIn("insempty", code, "六行全空时概览标签已经整块收起，不该再留占位话")
        # 聚合披露仍然保留在后端给出的 note / missing 上，只是不再逐行刷屏
        note = re.search(r"function noteBlock\(data\)\s*\{([\s\S]*?)\n  \}", read("field.js"))
        self.assertTrue(note, "找不到 noteBlock()")
        self.assertIn("官方页面没有写", note.group(1), "整条缺失说明不能一起删掉")
        css = read("field.css")
        self.assertNotIn(".none-tag", css, "标签样式随规则一起清理")

    def test_quotes_are_present_but_secondary(self):
        # 反馈 3：引文要看得见（两版内容必须一致），但视觉权重让给答案正文
        js = read("field.js")
        body = re.search(r"function partHtml\(a\)\s*\{([\s\S]*?)\n  \}", js)
        self.assertTrue(body, "找不到 partHtml()")
        code = body.group(1)
        self.assertIn('class="qsrc"', code, "每条引文包在次级容器里")
        self.assertNotIn("<details", code, "不能用折叠隐藏原文：折叠后浏览器取不到全文，两版内容就不一致了")
        self.assertNotIn("这一项另有", js, "「另有 N 段原文」这类提示噪声要删掉")
        self.assertNotIn("点「核对原文」查看", js, "同上")
        self.assertRegex(js, r"function holdCard[\s\S]{0,900}class=\"why\"", "反问的理由要用轻量的 why 行")
        css = read("field.css")
        answer = re.search(r"\.aval \{[^}]*font-size: ([\d.]+)px", css)
        quote = re.search(r"\.qsrc \.qtxt \{[^}]*font-size: ([\d.]+)px", css)
        self.assertTrue(answer and quote, "答案与引文的字号要有明确层级")
        self.assertGreater(float(answer.group(1)) + 0.01, float(quote.group(1)) * 1.25, "答案正文要明显压过引文")
        self.assertRegex(css, r"\.qsrc \{[^}]*border-left", "引文用一条浅色竖线收边，不靠大字")

    def test_back_key_returns_to_the_initial_hero(self):
        # 反馈 4：要有返回键，回到刚进 /field 的满屏初始态
        html = read("field.html")
        self.assertRegex(html, r'<button class="ghostbtn backbtn" type="button" id="backbtn"', "顶栏要有返回按钮")
        js = read("field.js")
        self.assertRegex(js, r"function resetToHero\(", "返回与「重新问」共用一套复位")
        reset = re.search(r"function resetToHero\(\)\s*\{([\s\S]*?)\n  \}", js)
        self.assertTrue(reset, "找不到 resetToHero()")
        code = reset.group(1)
        for needed in ("state.slots = {}", "state.history = []", 'el.thread.innerHTML = ""', 'setMode("hero")'):
            self.assertIn(needed, code, f"复位漏了 {needed}")
        self.assertRegex(js, r'el\.back\.addEventListener\("click"[\s\S]{0,200}history\.back\(\)', "返回优先走浏览器历史")
        self.assertRegex(js, r'addEventListener\("popstate"[\s\S]{0,160}resetToHero\(\)', "浏览器返回键也要复位")
        self.assertRegex(js, r'mode === "work"[\s\S]{0,120}history\.pushState', "进入工作区时才压一条历史，避免堆栈")
        self.assertRegex(js, r'el\.clear\.addEventListener\("click", \(\) => resetToHero', "「重新问」复用同一个复位")
        css = read("field.css")
        self.assertRegex(css, r'body\[data-mode="hero"\] #backbtn \{ display: none', "满屏态不显示返回键")

    def test_footer_carries_the_team_credit(self):
        # 反馈 5：页脚小字署名
        html = read("field.html")
        footer = re.search(r'<footer class="page-footer">([\s\S]*?)</footer>', html)
        self.assertTrue(footer, "页脚没了")
        self.assertIn("广院通——由记忆队制作", footer.group(1), "署名要按用户给的原句")
        self.assertIn("/api/", footer.group(1), "数据来源说明保留")

    def test_hero_headline_is_the_new_copy_without_the_grey_lede(self):
        # 反馈 6：大字换成「校园事务 / 有求必应」，滚动大字下面的灰字删掉
        html = read("field.html")
        hero = re.search(r'<section class="hero"[\s\S]*?</section>', html)
        self.assertTrue(hero, "找不到 hero 区块")
        block = hero.group(0)
        h1 = re.search(r"<h1>([\s\S]*?)</h1>", block)
        self.assertTrue(h1, "hero 没有主标题")
        self.assertIn("校园事务", h1.group(1))
        self.assertIn("有求必应", h1.group(1))
        self.assertNotIn("把校园办事", html)
        self.assertNotIn("说得清楚", html)
        self.assertNotIn('class="lede"', block, "滚动大字下面的灰字按用户要求删除")
        self.assertNotIn("不会替你猜", html)

    def test_brand_is_guangyuantong_with_the_school_emblem(self):
        # 反馈 8 + 命名裁决：广院通做主名，校园办事向导做副标，CUC 圆牌换成中传校徽
        html = read("field.html")
        brand = re.search(r'<a class="brand" href="/field"[^>]*>([\s\S]*?)</a>\s*<span class="topline"', html)
        self.assertTrue(brand, "找不到品牌块")
        block = brand.group(1)
        self.assertIn("广院通", block, "主名要是广院通")
        self.assertIn("校园办事向导", block, "副标保留校园办事向导")
        self.assertIn(EMBLEM, block, "品牌位用中传校徽")
        self.assertNotRegex(block, r'class="brand-mark"[^>]*>\s*CUC', "不能再拿 CUC 字样当 logo")
        self.assertRegex(html, r"<title>广院通[^<]*</title>", "标签页标题跟主名一致")
        css = read("field.css")
        self.assertRegex(css, r"\.brand-mark \{[^}]*var\(--emblem-bg\)", "校徽底盘要读 token，方便换主题")
        self.assertRegex(css, r"\.brand-sub", "副标要有自己的样式类，不能和主名同字号")

    def test_brand_link_returns_to_the_field_home_page(self):
        # 用户要求：点右上角校标和「广院通」回 /field 首页。裁决走真链接，不做页内复位——
        # 链接不依赖 JS 就成立，重新加载也就把问答痕迹、槽位、深链参数一次清干净。
        html = read("field.html")
        link = re.search(r'<a class="brand" href="([^"]+)" title="([^"]*)">', html)
        self.assertTrue(link, "品牌块得是一个能点的链接")
        self.assertEqual(link.group(1), "/field", "回首页就落在 /field，别带查询串也别退回经典版")
        self.assertIn("广院通", link.group(2), "提示语要说清点这个会发生什么")
        self.assertNotIn('<span class="brand">', html, "旧的不可点品牌块要换掉，不能两处并存")
        # 链接里包住的是同一块校徽 + 主名，不是另起一个入口
        start = html.index('<a class="brand"')
        end = html.index('<span class="topline"')
        self.assertIn(EMBLEM, html[start:end], "校徽要包在链接里，点哪一块都算回首页")
        self.assertIn("广院通", html[start:end])
        css = read("field.css")
        self.assertRegex(css, r"\.brand \{[^}]*text-decoration: none", "品牌链接不许带下划线")

    def test_reel_words_are_untouched_by_the_logo_change(self):
        # 只换 logo，字幕轮换里的 CUC 是用户另行定过的规则
        source = read("field.js")
        self.assertRegex(source, r'FIELD_WORDS\s*=\s*\[\s*"CUC"')


class EntryLinkTest(unittest.TestCase):
    """v0.8：双栏从 / 挪到 /desk 之后，界面里的入口链接要跟到新地址。"""

    def test_field_page_entry_link_points_to_desk(self):
        # 双栏挪到 /desk 之后，这个入口再指 / 就是被 302 弹回 /field，点了等于没点
        html = read("field.html")
        link = re.search(r'<a class="ghostbtn" href="([^"]*)">经典版</a>', html)
        self.assertTrue(link, "/field 顶栏没有「经典版」入口")
        self.assertEqual(link.group(1), "/desk", "入口要指向双栏的新地址 /desk")

    def test_no_page_links_to_the_redirecting_root(self):
        # 除经典版（受发布守卫逐字节锁定）以外，任何界面都不许再直连 /：
        # / 现在只负责把人弹到 /field，指着它等于原地打转
        for name in ("field.html", "index.html"):
            html = read(name)
            self.assertNotIn('href="/"', html, f"{name} 里还有指向 / 的入口")

    def test_source_block_limits_and_guards(self):
        # 需求 2：问题对应的条目带官方网址时，回答里要能直接点开
        js = read("field.js")
        self.assertIn("function sourceBlock(", js, "field.js 里还没有 sourceBlock()")
        self.assertIn("function sourceLinks(", js, "field.js 里还没有 sourceLinks()")
        block = js_region(js, "function sourceLinks(", "function partHtml(")
        self.assertIn(".filter(", block, "要先滤掉没有网址的来源")
        self.assertIn("s.url", block, "过滤条件是来源自带 url")
        self.assertIn("slice(0, 2)", block, "回答卡只给前两条来源，别把卡片变成链接堆")
        self.assertIn('if (!list.length) return "";', block, "一条网址都没有就整块不出现")
        self.assertIn('target="_blank"', block, "外链新窗口打开")
        self.assertIn('rel="noreferrer"', block, "外链不带 referrer")
        self.assertIn("esc(", block, "网址与标题都要转义")
        self.assertIn("官方来源", block, "小标题写明是官方来源")

    def test_answer_card_renders_sources_above_the_footer(self):
        js = read("field.js")
        card = js_region(js, "function answerCard(", "function partHtml(")
        self.assertIn("${sourceBlock(item)}", card, "回答卡要渲染官方来源块")
        self.assertLess(card.index("${sourceBlock(item)}"), card.index('<div class="cardfoot">'),
                         "来源要在按钮行之前，别掉到卡片底下")

    def test_plain_answer_carries_the_source_urls(self):
        # 「复制答案」带走的纯文本也要有网址，否则截图转发时来源就丢了
        js = read("field.js")
        self.assertIn("function sourceLinks(", js, "筛选来源的规则要收在一个函数里，两处共用")
        copy = js_region(js, "function plainAnswer(", "function copyAnswer(")
        self.assertIn("sourceLinks(item)", copy, "复制文本要走同一套来源筛选")
        self.assertIn("官方来源", copy, "复制出去的文本要标明这是官方来源")

    def test_machine_endpoints_are_not_shown_as_sources(self):
        # 语料里有少数来源记的是接口地址（图书馆引擎返回 JSON，人打不开），
        # 这类不能当「官方来源」摆给用户
        js = read("field.js")
        gate = re.search(r"isReadableSource = \(url\)[\s\S]*?\n", js)
        self.assertTrue(gate, "没有 isReadableSource()，接口地址会混进官方来源")
        for pattern in ("engine2", "api-v2", r"\.json"):
            self.assertRegex(gate.group(0), pattern, f"筛选规则漏了 {pattern}")

    def test_source_block_is_styled(self):
        # 只要求「有这条规则」是空转：把规则掏空照样过，所以盯住具体的排版属性
        css = read("field.css")
        srcs = re.search(r"\.srcs \{([^}]*)\}", css)
        link = re.search(r"\.srclink \{([^}]*)\}", css)
        self.assertTrue(srcs, "官方来源块没有排版规则")
        self.assertTrue(link, "来源链接没有排版规则")
        self.assertIn("margin-top", srcs.group(1), "来源块要和上面的正文拉开距离")
        self.assertIn("color: var(", link.group(1), "来源链接用界面色值，不写死颜色")
        self.assertIn("text-decoration: none", link.group(1), "来源链接不带下划线，靠边线区分")

    def test_source_block_behavior(self):
        # 真跑一遍：空来源不渲染、缺 url 的来源跳过、最多两条
        import subprocess
        import tempfile

        js = read("field.js")
        esc = re.search(r"  const esc = \(value\) =>[\s\S]*?;\n", js)
        fn = re.search(r"  const isReadableSource[\s\S]*?function sourceBlock\(item\)[\s\S]*?\n  \}\n", js)
        self.assertTrue(esc and fn, "取不到 esc 或 sourceLinks/sourceBlock，没法跑行为检查")
        script = (
            esc.group(0) + fn.group(0) +
            "const cases=["
            "{},"
            "{source:[]},"
            '{source:[{title:"无网址的"},{title:"甲",url:"https://a.cuc.edu.cn/x"},'
            '{title:"乙",url:"https://b.cuc.edu.cn/y"},{title:"丙",url:"https://c.cuc.edu.cn/z"}]},'
            '{source:[{title:"接口",url:"https://ilib.cuc.edu.cn/engine2/data/api-v2/abc/get-classify?ac=true"},'
            '{title:"真页",url:"https://ilib.cuc.edu.cn/xygd.htm"}]}];'
            "process.stdout.write(JSON.stringify(cases.map(sourceBlock)));"
        )
        handle = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
        handle.write(script)
        handle.close()
        try:
            result = subprocess.run(["node", handle.name], capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, f"node 跑不起来：{result.stderr[:400]}")
            empty, no_url, three, machine = json.loads(result.stdout)
            self.assertEqual(empty, "", "条目没有 source 时不该出现来源块")
            self.assertEqual(no_url, "", "来源全都没有网址时不该出现来源块")
            self.assertIn("https://a.cuc.edu.cn/x", three)
            self.assertIn("https://b.cuc.edu.cn/y", three)
            self.assertNotIn("https://c.cuc.edu.cn/z", three, "只给前两条")
            self.assertNotIn("无网址的", three, "没有网址的来源不该出现在链接里")
            self.assertEqual(three.count("<a "), 2, f"应恰好两条链接：{three}")
            self.assertNotIn("接口", machine, "返回 JSON 的接口地址不该当官方来源")
            self.assertIn("https://ilib.cuc.edu.cn/xygd.htm", machine, "接口被滤掉后真页面要补上来")
        finally:
            Path(handle.name).unlink(missing_ok=True)


class PhaseTwoTest(unittest.TestCase):
    def test_four_entries_all_work(self):
        # 2026-11-02 用户改口：个人数据不再留禁用，但只做「跳官方系统」，页内不读数据
        html = read("field.html")
        acts = re.search(r'<nav class="topacts"[\s\S]*?</nav>', html)
        self.assertTrue(acts, "顶栏功能区没了")
        block = acts.group(0)
        for label in PHASE_TWO_LABELS:
            btn = re.search(rf'<button class="ghostbtn" type="button" id="[a-z]+"[^>]*>{label}', block)
            self.assertTrue(btn, f"{label} 入口没有启用")
            self.assertNotIn("disabled", btn.group(0), f"{label} 不该还是禁用态")
            # 负控抓到：入口光「没禁用」不算能用，得有 data-panel 口令才会真的开面板
            self.assertIn(f'data-panel="{PHASE_TWO_KINDS[label]}"', btn.group(0), f"{label} 入口没接到 {PHASE_TWO_KINDS[label]} 面板")
        self.assertNotIn("未接入", block, f"{LOCKED_LABEL} 已经能用了，别再挂未接入")
        self.assertNotIn("暂未开放", html, "第一期那四个纯占位说明已经过期")
        title = re.search(r'<button class="ghostbtn" type="button" id="databtn"[^>]*title="([^"]+)"', block)
        self.assertTrue(title, f"{LOCKED_LABEL} 入口要说明点开会看到什么")
        self.assertIn("不读取", title.group(1), "入口的提示就要先讲清页内不读数据")

    def test_personal_panel_links_out_and_reads_nothing(self):
        # 面板只给两个官方入口，查数据仍在学校系统里完成：地址必须与经典版组件逐字一致
        source = read("field.js")
        self.assertIn("function personalPanel", source, f"{LOCKED_LABEL} 面板还没实现")
        component = (WEB / "personal-data.js").read_text(encoding="utf-8")
        urls = {}
        for name in PERSONAL_SOURCES:
            hit = re.search(rf'const {name} = "([^"]+)"', component)
            self.assertTrue(hit, f"经典版组件里找不到 {name}，比对失去出处")
            urls[name] = hit.group(1)
        self.assertEqual(urls["CARD_URL"], "https://pcard.cuc.edu.cn/servicehall/ykt/query?code=5")
        self.assertEqual(urls["COURSES_URL"], "https://courses.cuc.edu.cn/user/index")
        # field.js 顶部那两个常量必须和组件逐字一致——注释里写了「有测试比对」，就得真比
        for name in PERSONAL_SOURCES:
            mine = re.search(rf'const {name} = "([^"]+)"', source)
            self.assertTrue(mine, f"field.js 里要有 {name} 常量")
            self.assertEqual(mine.group(1), urls[name], f"{name} 与经典版组件不一致，两版会点进不同系统")
        block = js_region(source, "function personalPanel", "/* ----------")
        for name in PERSONAL_SOURCES:
            self.assertIn("${" + name + "}", block, f"面板链接要引用常量 {name}，不要另抄一遍地址")
        self.assertIn("校园卡", block)
        self.assertIn("畅课", block)
        self.assertEqual(len(re.findall(r'<a class="pdlink"', block)), 2, f"{LOCKED_LABEL} 面板只许有两个链接")
        for attr in ('target="_blank"', 'rel="noreferrer"'):
            self.assertEqual(block.count(attr), 2, f"两个链接都要带 {attr}")
        # 页内不读数据：不许 iframe、不许对这两个域名发请求
        self.assertNotIn("iframe", block, f"{LOCKED_LABEL} 面板不许嵌官方页面")
        self.assertNotRegex(source, r"(fetch|api|XMLHttpRequest)\s*\(\s*[\"'`]https?://(pcard|courses)\.",
                            "向导页不许去请求官方系统，查数据只在官方页面里完成")
        # 说清「这里不读取任何数据、要本人登录」
        for keyword in ("不读取", "本人"):
            self.assertIn(keyword, block, f"面板要写明「{keyword}」")

    def test_wechat_hint_only_shows_inside_wechat(self):
        # 用户口径：微信里打不开时提示「打不开请在浏览器打开」；普通浏览器不必看见这句
        source = read("field.js")
        self.assertIn("function personalPanel", source, "先有面板实现，再谈提示的显示条件")
        block = js_region(source, "function personalPanel", "/* ----------")
        self.assertRegex(source, r"MicroMessenger", "要靠 UA 判断是不是微信内置浏览器")
        self.assertIn("浏览器打开", block)
        at = block.index("MicroMessenger")
        self.assertLess(at, block.index("浏览器打开"), "先判定微信，再输出那句提示——常驻显示等于所有人都看见")
        # 光「判定过」不算只在微信里显示：那句提示必须长在条件分支里
        self.assertRegex(block, r"inWeChat\s*\?\s*`<p class=\"pdwarn\"",
                         "提示要挂在 inWeChat 条件分支上，改成恒真是给所有人看")

    def test_panel_shell_is_a_dialog(self):
        html = read("field.html")
        panel = re.search(r'<section class="panel"[\s\S]*?</section>', html)
        self.assertTrue(panel, "缺少面板容器")
        block = panel.group(0)
        for needed in ('id="panel"', 'role="dialog"', 'aria-modal="true"', 'aria-labelledby="pantitle"', 'id="pantitle"'):
            self.assertIn(needed, block, f"面板缺 {needed}")
        self.assertIn('id="panelbody"', block, "面板要有内容区")
        self.assertRegex(block, r"\shidden[\s>]", "面板默认收起")
        js = read("field.js")
        self.assertRegex(js, r"function openPanel\(", "缺少 openPanel()")
        self.assertRegex(js, r"function closePanel\(", "缺少 closePanel()")
        self.assertRegex(js, r'event\.key === "Escape"[\s\S]{0,160}closePanel', "Esc 能关面板")
        self.assertRegex(js, r'el\.scrim\.addEventListener\("click"', "点遮罩能关面板")
        css = read("field.css")
        self.assertRegex(css, r"\.panel\[hidden\] \{ display: none", "hidden 属性要真的压过定位样式")

    def test_search_panel_uses_the_real_contract(self):
        js = read("field.js")
        body = re.search(r"function searchPanel\(\)\s*\{([\s\S]*?)\n  \}", js)
        self.assertTrue(body, "找不到 searchPanel()")
        code = body.group(1)
        self.assertRegex(code, r'/api/search\?q=" \+ encodeURIComponent', "检索要走 GET /api/search?q=")
        self.assertRegex(code, r"&k=", "要带条数参数 k")
        for field in ("title", "kind", "score", "snippet", "url"):
            self.assertRegex(code, rf"\.{field}\b", f"检索结果少渲染字段 {field}")
        self.assertRegex(code, r"\.total\b", "要报命中条数")
        self.assertRegex(code, r"length < 2", "空/过短问句先拦住，后端也是这么要求")
        self.assertRegex(code, r"只给原文", "要写清楚检索只给原文、不生成答案")

    def test_contact_panel_links_and_categorises(self):
        js = read("field.js")
        body = re.search(r"function contactPanel\(\)\s*\{([\s\S]*?)\n  \}", js)
        self.assertTrue(body, "找不到 contactPanel()")
        code = body.group(1)
        self.assertRegex(code, r"/api/contacts", "联系方式走 GET /api/contacts")
        self.assertRegex(code, r'phone: "tel:', "电话要能一键拨号")
        self.assertRegex(code, r'mailto:', "邮箱要能一键发信")
        for field in ("dept", "purpose", "context", "source_url"):
            self.assertRegex(code, rf"\.{field}\b", f"联系方式少渲染字段 {field}")
        self.assertRegex(code, r"\.purposes\b", "要按用途分类筛选")
        self.assertRegex(code, r"公开", "要说明这是公开联系方式，不是内部号码")

    def test_map_panel_is_a_real_basemap(self):
        # 用户 2026-11-02 定：地图还是接入比较直观。面板下面是真底图，
        # 旧的「不是地图底图」披露必须一起删掉，留着就是假话。
        js = read("field.js")
        self.assertRegex(js, r"function mapPanel\(\)", "找不到 mapPanel()")
        # 地图这一块的字段渲染拆到了 pickCard / poiRows 里（mapPanel 要保持扁平、能被上面的正则整段取出），
        # 所以核对范围是整个位置区段，不只是 mapPanel 函数体。
        code = js_region(js, "/* ---------- 位置：本地 Leaflet", "/* ---------- 场域动效")
        self.assertRegex(code, r"const campus = state\.campus", "地图复用已加载的 /api/campus，不重复请求")
        for field in ("lat", "lng", "name", "place", "kind"):
            self.assertRegex(code, rf"\.{field}\b", f"地图少用字段 {field}")
        self.assertRegex(code, r"amap_marker", "标记要能跳高德")
        self.assertRegex(code, r"coord_confidence\]", "要披露坐标可信度")
        self.assertRegex(code, r"ensureBasemap", "建图要单独成函数：面板重画时不能对同一个容器重复 L.map")
        self.assertRegex(code, r"底图来自高德", "要写明底图是谁的，不能假装是自己或学校的数据")
        self.assertRegex(code, r"官方没有给出这一处的坐标", "没有坐标的地点仍要如实说明，不许拿校园中心糊一个点")
        self.assertNotRegex(code, r"不是地图底图", "这句披露已经过期，现在面板里就是底图")
        self.assertNotRegex(code, r"示意图", "位置面板不再是示意图，措辞要跟着改")

    def test_place_without_official_coords_is_not_fabricated(self):
        # 回答里点到的地点未必在校内清单里，坐标只能从高德深链里解；
        # 解不出来就留空，让界面如实说「官方没有给出坐标」，不能拿校园中心凑一个点。
        js = read("field.js")
        code = js_region(js, "function pickTarget(all)", "function pickCard(")
        self.assertRegex(code, r"markerCoords\(answer\.marker\)", "回答里的地点要靠深链解坐标，不能自己编")
        self.assertNotRegex(code, r"lat:\s*MAP_HOME", "解不出坐标时不许拿校园中心假造一个点")
        self.assertRegex(code, r"spot \? spot\[0\] : null", "解不出坐标要把 lat 留空，交给详情文案如实说明")

    def test_basemap_matches_the_classic_page(self):
        # 两版共用同一份本地 Leaflet 与同一个瓦片地址，否则同一栋楼在两版地图上会落在不同底图上
        classic = read("app.js")
        tile = re.search(r'L\.tileLayer\("([^"]+)"', classic)
        self.assertTrue(tile, "取不到经典版的瓦片地址，没法核对两边是否同一底图")
        js = read("field.js")
        self.assertIn(tile.group(1), js, f"钴蓝场的瓦片和经典版不一致，应为 {tile.group(1)}")
        self.assertRegex(js, r"L\.map\(", "要真的建 Leaflet 地图，不是贴一张静态图")
        self.assertRegex(js, r"L\.circleMarker\(", "地点用 circleMarker 打点：默认图标是位图，钴蓝场不要那种浮层")
        self.assertRegex(js, r"subdomains", "高德瓦片要带子域，不然同一位置会被限流")
        self.assertRegex(js, r"attribution", "底图署名要留给高德，不能抹掉")

    def test_location_answers_bring_up_the_map(self):
        # 用户实测的缺陷：问「图书馆在哪」，答案出来了地图却没拉起。
        # 后端 /api/ask 一直在返回 data.map，经典版靠 if (d.map) showMap(d.map) 开抽屉，
        # /field 之前根本没读这个字段——这是漏接，不是后端没给。
        js = read("field.js")
        body = re.search(r"function afterResult\(response\)\s*\{([\s\S]*?)\n  \}", js)
        self.assertTrue(body, "找不到 afterResult()")
        code = body.group(1)
        self.assertRegex(code, r"if \(response\.map && response\.map\.name\)", "回答里带地点时要接住 data.map")
        self.assertRegex(code, r"""openPanel\(\s*"map"\s*,\s*true\s*\)""", "接住 data.map 就要真的打开地图面板，第二个参数表示不抢焦点")
        self.assertRegex(js, r"state\.mapPlace\s*=", "把这一处地点存进 state，面板才知道标哪个点")
        self.assertRegex(js, r"function openPanel\(kind, keepFocus\)", "自动拉起要能选择不移动焦点")
        self.assertRegex(js, r"if \(!keepFocus\) ", "焦点只在用户主动点入口时才送进面板")
        # 用户自己开着面板问别的事，不该被一句没有地点的回答抢关
        self.assertNotRegex(code, r"closePanel\(", "没有地点的回答不要把用户开着的面板抢关")

    def test_basemap_instance_is_released_when_the_panel_changes(self):
        # Leaflet 的地图实例绑死在容器节点上。面板换类型时 panelbody 会被清空，
        # 不先把实例 remove 掉，再开一次地图就会撞 "Map container is already initialized"。
        js = read("field.js")
        self.assertRegex(js, r"function resetBasemap\(\)", "要有释放地图实例的函数")
        self.assertRegex(js, r"view\.remove\(\)", "释放要真的调用 Leaflet 的 remove")
        shell = re.search(r"function openPanel\(kind, keepFocus\)\s*\{([\s\S]*?)\n  \}", js)
        self.assertTrue(shell, "找不到 openPanel(kind, keepFocus)")
        self.assertRegex(shell.group(1), r"resetBasemap\(\)", "换面板类型时要先释放旧地图")
        closer = re.search(r"function closePanel\(\)\s*\{([\s\S]*?)\n  \}", js)
        self.assertTrue(closer, "找不到 closePanel()")

    def test_panel_body_flag_cannot_swallow_the_in_panel_clicks(self):
        # 浏览器实测抓到的真 bug：滚动锁定把属性写在 body 上且和入口属性同名，
        # 于是 closest("[data-panel]") 在面板内点「地点名」「用途筛选」时先命中 body，
        # 走成重画面板，选点与筛选永远不生效。入口要按标签限定，锁定属性另起名字。
        js = read("field.js")
        self.assertRegex(js, r'closest\("button\[data-panel\], a\[data-panel\]"\)',
                         "面板入口要按标签限定，不能让 body 上的同名属性被当成入口")
        self.assertNotIn('el.body.dataset.panel = kind', js, "滚动锁定不能复用入口那个属性名")
        self.assertRegex(js, r"el\.body\.dataset\.panelOpen = kind", "滚动锁定改用 data-panel-open")
        self.assertRegex(js, r"delete el\.body\.dataset\.panelOpen", "关面板要把锁定属性一起清掉")
        css = read("field.css")
        self.assertRegex(css, r"body\[data-panel-open\] \{ overflow: hidden", "CSS 跟着改名后的属性走")
        self.assertNotIn("body[data-panel] {", css, "旧属性名要一并清掉，留着就是双份锁定")

    def test_panel_does_not_cover_the_top_entries(self):
        # 面板从顶栏下面开始：否则右侧的 地图/原文检索/联系方式 被面板压住，
        # 看着能点其实点不动，换面板只能先关再开。
        # 浏览器实测（2026-11-02）：窄屏答完题后顶栏多出「当前事项」一行，从 159px 长到 190px，
        # 写死的 172px 就把顶栏压住了。顶栏高度是动态的，只能实测后下发给 CSS。
        css = read("field.css")
        js = read("field.js")
        panel = re.search(r"\.panel \{([^}]*)\}", css)
        self.assertTrue(panel, "找不到 .panel 定位规则")
        self.assertRegex(panel.group(1), r"top: var\(--panel-top, var\(--topbar-keep\)\)",
                         "面板上沿读实测高度，JS 没跑起来时用 token 兜底")
        self.assertRegex(css, r"\.scrim \{[^}]*inset: var\(--panel-top, var\(--topbar-keep\)\) 0 0",
                         "遮罩也要让开顶栏，入口点下去是换面板而不是白点一次")
        self.assertRegex(css, r"--topbar-keep:", "兜底高度要写成 token，顶栏改高度时不会漏")
        self.assertRegex(js, r'"--panel-top"', "要把实测出来的顶栏高度下发成 CSS 变量")
        code = js_region(js, "function syncPanelTop()", "function closePanel()")
        self.assertRegex(code, r"getBoundingClientRect\(\)\.bottom", "顶栏高度要实测，不能猜")
        self.assertRegex(js, r"syncPanelTop\(\)", "打开面板时要先按当前顶栏高度对齐")
        self.assertRegex(js, r"ResizeObserver", "顶栏换行是动态的：靠观察尺寸变化，不靠背下来的常量")
        # 写死的窄屏档位已经不管用了，留着只会让人以为它还在生效
        self.assertNotRegex(css, r"--topbar-keep-mobile", "窄屏改用实测高度，写死的档位要一并删掉")

    def test_narrow_full_width_send_does_not_squeeze_the_panel_form(self):
        # 窄屏截图复核抓到：把「问」按钮拉满整行的规则写成了裸 .send，
        # 于是面板里的「定位 / 搜索」也一起满行，输入框被挤到只剩几个字。
        css = read("field.css")
        narrow = css[css.index("@media (max-width: 720px)"):]
        self.assertNotRegex(narrow, r"\n\s*\.send \{[^}]*width: 100%",
                            "满整行只该给提问框的「问」，别连面板表单的按钮一起拉走")
        self.assertRegex(narrow, r"\.boxfoot \.send \{[^}]*width: 100%", "提问框的按钮在窄屏满行，要写清是给 .boxfoot 的")

    def test_panel_opens_do_not_touch_the_answer_flow(self):
        # 面板是附加层，不能把主链路的分支顺序或卡片结构带跑
        js = read("field.js")
        order = [js.index(marker) for marker in ("data.plan", "data.matched", "data.disambiguate", "data.hold", "data.answers")]
        self.assertEqual(order, sorted(order), "结果分支顺序必须仍是计划→未命中→澄清→先确认→答案")
        self.assertLess(js.index("function renderResult"), js.index("function planCard"))
        html = read("field.html")
        self.assertIn('id="thread"', html, "对话线程不能被面板替换")
        self.assertIn('id="composer"', html, "提问框不能被面板替换")


class HospitalPinDataTest(unittest.TestCase):
    """问校医院时，图上的点和跳高德的落点都必须是 20 号楼。

    用户 2026-11-02 实测：校医院在 20 号楼这句是对的，但图上标点的位置是错的。
    根因在数据层——原来的坐标取自 OpenStreetMap 的 amenity=hospital 节点，
    那个点在高德自己的逆地理里落在「中国传媒大学附属中学」一带，离 20 号楼差四百多米。
    这几条钉住更正后的来源，防止重新生成 campus-map.json 时又把 OSM 那个点写回去。
    """

    def test_hospital_pin_uses_the_amap_building_20_point(self):
        cm = json.loads((ROOT / "campus-map.json").read_text(encoding="utf-8"))
        hit = [p for p in cm["pois"] if p.get("name") == "校医院"]
        self.assertEqual(len(hit), 1, "campus-map.json 里校医院应该只有一条")
        entry = hit[0]
        # 高德 POI「中国传媒大学20号楼」B0FFF7RE6W 的 GCJ-02 坐标，与底图同一基准
        self.assertAlmostEqual(entry["lat"], 39.913089, places=6, msg="落点不是高德标注的 20 号楼")
        self.assertAlmostEqual(entry["lng"], 116.558813, places=6, msg="落点不是高德标注的 20 号楼")
        self.assertEqual(entry.get("confidence"), "high")
        self.assertIn("高德地图 POI", entry.get("source", ""), "坐标来源要写高德 POI，不能再用那个偏了四百米的 OSM 节点")
        self.assertIn("B0FFF7RE6W", entry.get("source", ""), "要留下可复核的高德 POI 编号")
        self.assertNotIn("N7321277718", entry.get("source", ""), "被否决的 OSM 点位不能再当成坐标来源")

    def test_hospital_entry_keeps_the_official_address_wording(self):
        cm = json.loads((ROOT / "campus-map.json").read_text(encoding="utf-8"))
        entry = [p for p in cm["pois"] if p.get("name") == "校医院"][0]
        self.assertIn("20 号楼", entry.get("address", "") + entry.get("note", ""),
                      "官方原文说校医院在 20 号楼（原幼儿园），这条要留在数据里")

    def test_map_query_sends_the_amap_link_to_building_20(self):
        # 「在高德里打开」在没有坐标时退回搜索链接，搜索词也得指向 20 号楼，
        # 否则用户点过去看到的是别的楼。
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertRegex(source, r'"校医院":\s*\("20号楼",\s*"校医院（20号楼）"\)',
                         "校医院的高德搜索词要指到 20 号楼")

    def test_build_script_holds_the_same_coordinate(self):
        # campus-map.json 是脚本生成的，只改产物不改生成器，下次重跑就回退
        script = (ROOT / "tools" / "build_campus_map.py").read_text(encoding="utf-8")
        block = script[script.index('id="xiaoyiyuan"'):]
        block = block[:block.index("),\n")]
        self.assertIn("(AMAP, 39.913089, 116.558813)", block, "生成脚本里的校医院坐标要和高德 20 号楼一致")
        self.assertIn("B0FFF7RE6W", block, "生成脚本要留下高德 POI 编号")
        self.assertNotIn("(OSM, 39.914185, 116.548511)", block, "旧的 OSM 点位不能再当坐标来源")


class ProductionUntouchedTest(unittest.TestCase):
    def test_classic_page_only_gained_the_field_entry(self):
        old = (BACKUP / "index.html").read_text(encoding="utf-8")
        new = (WEB / "index.html").read_text(encoding="utf-8")
        diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0))
        added = [line for line in diff if line.startswith("+") and not line.startswith("+++")]
        removed = [line for line in diff if line.startswith("-") and not line.startswith("---")]
        self.assertFalse(removed, f"经典版删了行：{removed}")
        self.assertEqual(len(added), 1, f"经典版只允许新增一行入口，实际新增 {len(added)} 行：{added}")
        self.assertIn('href="/field"', added[0], "经典版那唯一一处改动必须是 /field 入口")

    # 发布要求页脚版本号跟着版本走：备份里是 v0.6，本次发布到 v0.8；
    # 这一行是 classic.html 唯一允许的改动，其余内容仍必须与动手前的备份逐字节一致。
    RELEASE_LINE_DIFF = [
        "-    <span>校园办事向导 v0.6 · 管理类</span>",
        "+    <span>校园办事向导 v0.8.2 · 管理类</span>",
    ]

    def test_classic_page_diff_is_only_the_release_version(self):
        diff = diff_lines(BACKUP / "classic.html", WEB / "classic.html")
        self.assertEqual(diff, sorted(self.RELEASE_LINE_DIFF + CLASSIC_DISPLAY_DIFF),
                         "classic.html 只许改页脚版本号，加上显示层白名单那几行，实际差异：%s" % diff)

    def test_display_whitelist_leaves_the_ask_text_alone(self):
        """白名单只放行显示层：发给路由的原文必须一个字没改，否则就不是「只显示」。"""
        for name, lines in list(DISPLAY_DIFF_OK.items()) + [("classic.html", CLASSIC_DISPLAY_DIFF)]:
            for line in lines:
                if not line.startswith("+"):
                    continue
                if "docName" in line and "const docName" in line:
                    continue
                for attr in ("data-ask=\"${esc(docName", "data-alt=\"${esc(docName",
                             "data-ask=\"${docName", "data-alt=\"${docName"):
                    self.assertNotIn(attr, line, f"{name} 的放行行把发送原文也剥了后缀：{line}")

    def test_other_original_files_are_byte_identical_to_backup(self):
        self.assertTrue(BACKUP.is_dir(), "缺少动手前的整目录备份")
        import filecmp

        changed = []
        missing = []
        for path in sorted(BACKUP.rglob("*")):
            if path.is_dir() or path.name in ("index.html", "classic.html"):
                continue
            target = WEB / path.relative_to(BACKUP)
            if not target.is_file():
                missing.append(str(target.relative_to(ROOT)))
            elif not filecmp.cmp(path, target, shallow=False):
                allowed = DISPLAY_DIFF_OK.get(path.name)
                if allowed is not None and diff_lines(path, target) == sorted(allowed):
                    continue   # 白名单内的显示层改动
                changed.append(str(target.relative_to(ROOT)))
        self.assertFalse(missing, f"原文件被删除：{missing}")
        self.assertFalse(changed, f"原文件被修改：{changed}")

    def test_only_the_expected_files_were_added(self):
        expected = {f"field.{ext}" for ext in ("html", "css", "js")} | {EMBLEM}
        added = {
            str(path.relative_to(WEB)).replace("\\", "/")
            for path in WEB.rglob("*")
            if path.is_file() and not (BACKUP / path.relative_to(WEB)).is_file()
        }
        self.assertEqual(added, expected, "web-next 里出现或缺少了计划外的文件")



class EmptySectionTest(unittest.TestCase):
    """用户反馈：概览 / 材料 / 流程某一节整块没有内容时，连标签一起不显示，不要点进去看一句「没有」。"""

    def test_tab_bar_hides_empty_sections(self):
        code = read("field.js")
        self.assertIn("function visibleTabs", code, "要有一处统一决定哪些标签有内容")
        for content in ("OVERVIEW_KEYS", "MATERIAL_KEYS", "STEPS_KEYS"):
            self.assertIn(content, code, f"缺少 {content}：某一节有没有内容的判据")

    def test_hidden_tab_is_not_left_selected(self):
        code = read("field.js")
        self.assertRegex(code, r"state\.tab\s*=\s*", "标签显隐后要复位当前标签")
        self.assertRegex(code, r"\.hidden\s*=\s*", "标签按钮要真的收起来")

    def test_empty_placeholders_are_gone(self):
        code = read("field.js")
        for line in ("官方页面没有列出材料清单", "官方页面没有写分步流程", "这条事项在官方页面里没有登记地点"):
            self.assertNotIn(line, code, f"这一节空着已经不显示标签了，{line} 的占位话该删")

    def test_quotes_tab_always_stays(self):
        html = read("field.html")
        self.assertRegex(html, r'<button role="tab"[^>]*data-tab="quotes"', "原文标签是核对出处用的，不能跟着收起来")


class TransparentTopbarTest(unittest.TestCase):
    """用户反馈：地图 / 原文检索 / 联系方式 / 个人数据 / 返回 / 经典版 这一栏整条透明，只留按钮白底加描边。"""

    def test_topbar_paints_nothing(self):
        css = read("field.css")
        for match in re.finditer(r"\.topbar\s*\{[^}]*\}", css):
            self.assertNotIn("background", match.group(0), f"顶栏要透明：{match.group(0)[:120]}")

    def test_nav_buttons_are_white_with_outline(self):
        css = read("field.css")
        block = re.search(r"\.ghostbtn\s*\{[^}]*\}", css).group(0)
        self.assertIn("background: var(--bg)", block, "按钮底要白色")
        self.assertRegex(block, r"border:\s*1px solid var\(--btn-line\)", "按钮要有描边")
        self.assertIn("--btn-line:", css, "描边色要写成 token，不许在结构 CSS 里写死")

    def test_mobile_no_longer_makes_buttons_transparent(self):
        css = read("field.css")
        self.assertNotRegex(css, r"\.ghostbtn\s*\{[^}]*background:\s*transparent", "窄屏把按钮刷成透明，就和「白底+描边」相反了")


class PresetTest(unittest.TestCase):
    """用户点名把 /field 首页预设换成这 8 条：字面、条数、顺序都按给的原话，不自作主张改写。"""

    WANTED = [
        "48教在哪", "校医院在哪", "校卡怎么补办", "转专业",
        "出国用的成绩单怎么开", "奖学金", "保研", "宿舍购电",
    ]

    def presets(self):
        code = read("field.js")
        block = re.search(r"const PRESETS = \[(.*?)\];", code, re.S).group(1)
        return re.findall(r'"([^"]+)"', block)

    def test_presets_are_exactly_the_eight_the_user_named(self):
        self.assertEqual(self.presets(), self.WANTED, "预设问法要与用户点名的逐字一致、顺序一致")

    def test_every_preset_answers(self):
        import app
        for text in self.WANTED:
            if text == "转专业":
                # 光一个词的问法按设计先给联想菜单，不算答不上
                d = app.answer_question(text, {}, False)
                self.assertTrue(d.get("ambiguous"), "「转专业」这种单词问法要给选项菜单")
                continue
            d = app.answer_question(text, {}, False)
            answers = d.get("answers") or []
            self.assertTrue(d.get("matched") and answers, f"{text} 答不上来，不能当预设")
            self.assertTrue(str(answers[0].get("text") or "").strip(), f"{text} 答案正文是空的")
            # 「非官方补充」是诚实标注，允许；「这一问这次没答到」和已经答上是矛盾的，不许
            self.assertNotIn("没答到", str(d.get("note") or ""), f"{text} 不该带自相矛盾的漏答提示")

    def test_school_card_spoken_shortcut_resolves(self):
        import app
        d = app.answer_question("校卡怎么补办", {}, False)
        self.assertEqual((d.get("item") or {}).get("id"), "xyk-buka",
                         "「校卡」是校园卡的口语说法，要能落到校园卡补卡条目")


class HideTopbarOnScrollTest(unittest.TestCase):
    """用户要求：往下滑时顶栏收起，往上滑时再拉出来。收起只能用位移，不能用 display:none（会把内容顶跳）。"""

    def test_css_moves_the_bar_up_out_of_view(self):
        css = read("field.css")
        rule = re.search(r"\.topbar\.is-up\s*\{([^}]*)\}", css)
        self.assertIsNotNone(rule, "要有一条 .topbar.is-up 收起规则")
        body = rule.group(1)
        self.assertRegex(body, r"transform:\s*translateY\(-1\d+(\.\d+)?%", "整条往上移出视口")
        self.assertIn("visibility: hidden", body, "移出后要从 Tab 焦点里出去，否则键盘用户会摸到看不见的按钮")
        self.assertNotIn("display: none", body, "顶栏是 sticky，用 display:none 收起会让下面的内容整块跳动")

    def test_bar_slides_instead_of_snapping(self):
        css = read("field.css")
        base = re.search(r"\.topbar\s*\{[^}]*\}", css).group(0)
        self.assertRegex(base, r"transition:[^;]*transform[^;]*var\(--bar-slide\)",
                         "位移时长要读 token，收起和拉出用同一个值")
        up = re.search(r"\.topbar\.is-up\s*\{([^}]*)\}", css).group(1)
        self.assertRegex(up, r"visibility\s+0s\s+var\(--bar-slide\)",
                         "隐藏要延到位移结束再切，延时长必须跟位移时长是同一个 token")

    def test_slide_duration_is_slow_enough(self):
        # 用户要求「稍微慢一点，时长长一些」：0.22s 太急，卡在 0.3s 以上
        css = read("field.css")
        match = re.search(r"--bar-slide:\s*(\.\d+|\d+(?:\.\d+)?)s\s*;", css)
        self.assertIsNotNone(match, "顶栏位移时长要写成 :root 里的 --bar-slide")
        self.assertGreater(float(match.group(1)), 0.3, f"顶栏位移要慢一点，当前 --bar-slide={match.group(1)}s")

    def test_slide_duration_token_lives_in_root(self):
        css = read("field.css")
        root = "".join(css[start:end] for start, end in root_blocks(css))
        self.assertIn("--btn-line:", root, "先确认拿到的是主 :root")
        self.assertIn("--bar-slide:", root, "时长 token 要和其他 token 一起放在 :root")

    def test_js_toggles_the_class_on_scroll_direction(self):
        code = read("field.js")
        self.assertTrue(re.search(r'classList\.toggle\("is-up",\s*[\w.]+\)', code),
                        "收起与否要由滚动方向算出来的布尔值决定，不能裸 toggle")
        handler = re.search(r"function syncBarHide\([^)]*\)\s*\{(.*?)\n  \}", code, re.S)
        self.assertIsNotNone(handler, "滚动逻辑集中在一处 syncBarHide")
        body = handler.group(1)
        self.assertIn("scrollY", body, "按滚动位置判方向")
        self.assertIn("lastY", body, "要记住上一次的位置才能分辨上划还是下滑")
        self.assertIn("delta", body, "要有一个最小位移量，否则手指微抖就会来回开关")

    def test_bar_stays_when_panel_open_or_near_top(self):
        code = read("field.js")
        body = re.search(r"function syncBarHide\([^)]*\)\s*\{(.*?)\n  \}", code, re.S).group(1)
        self.assertIn("el.panel.hidden", body, "面板开着时顶栏不能收，收起会让面板位置一起跳")
        self.assertRegex(body, r"BAR_KEEP|scrollY\s*<\s*\d+", "贴着顶部时不收，否则首屏一抖顶栏就没了")

    def test_scroll_listener_is_passive(self):
        code = read("field.js")
        self.assertTrue(
            re.search(r'window\.addEventListener\("scroll",\s*\(\)\s*=>\s*syncBarHide\(\),\s*\{[^}]*passive:\s*true', code),
            "滚动监听要 passive，不然手机端跟着掉帧")

    def test_panel_top_ignores_the_collapsed_bar(self):
        code = read("field.js")
        body = re.search(r"function syncPanelTop\([^)]*\)\s*\{(.*?)\n  \}", code, re.S).group(1)
        self.assertIn("barBottom", body,
                      "顶栏收起时量到的是位移中的中间值，面板要按上一次没收起时量到的高度定位")

    def test_opening_a_panel_pulls_the_bar_back_out_first(self):
        code = read("field.js")
        body = re.search(r"function openPanel\([^)]*\)\s*\{(.*?)\n  \}", code, re.S).group(1)
        self.assertIn('"is-up"', body, "打开面板前先把顶栏拉出来，否则面板会从顶栏中间开始盖住那一排入口")


if __name__ == "__main__":
    unittest.main(verbosity=2)
