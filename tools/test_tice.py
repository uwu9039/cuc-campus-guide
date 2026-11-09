"""体测评分表 JSON 的数据不变量与文件契约。见 spec §12。"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web-next" / "tice-standard.json"
STD = json.loads(DATA.read_text(encoding="utf-8"))
GROUPS = ("grade12", "grade34")
WANT_LADDER = [100, 95, 90, 85, 80, 78, 76, 74, 72, 70, 68, 66, 64, 62, 60, 50, 40, 30, 20, 10]
WANT_NULLS = {("pullUps", "male", "grade12"): [5, 7, 9, 11, 13],
              ("pullUps", "male", "grade34"): [5, 7, 9, 11, 13]}


def tables(events):
    for ev, d in events.items():
        for g in d["genders"]:
            for grp in GROUPS:
                yield ev, g, grp, d["thresholds"][g][grp]


def check_slot_count(events):
    bad = [(e, g, gr, len(t)) for e, g, gr, t in tables(events) if len(t) != 20]
    assert not bad, f"槽位数不是 20：{bad}"


def check_null_layout(events):
    found, total = {}, 0
    for e, g, gr, t in tables(events):
        ix = [i for i, v in enumerate(t) if v is None]
        total += len(t)
        if ix:
            found[(e, g, gr)] = ix
    assert found == WANT_NULLS, f"null 位置不符：{found}"
    assert total == 480, f"总槽位 {total} != 480"
    nums = sum(1 for _, _, _, t in tables(events) for v in t if v is not None)
    assert nums == 470, f"非空阈值 {nums} != 470"


def _as_number(x):
    if isinstance(x, str) and "'" in x:
        m = re.match(r"(\d+)'(\d+)\"", x)
        return int(m.group(1)) * 60 + int(m.group(2))
    return float(x)


def check_monotonic(events):
    for ev, d in events.items():
        assert d["direction"] in ("higher_is_better", "lower_is_better"), \
            f"{ev} 的 direction 是 {d['direction']!r}，不在契约两值内"
        asc = d["direction"] == "lower_is_better"
        for e, g, gr, t in tables(events):
            if e != ev:
                continue
            v = [_as_number(x) for x in t if x is not None]
            got = sorted(v) if asc else sorted(v, reverse=True)
            assert v == got, f"{ev}/{g}/{gr} 阈值不单调：{v}"


class LadderTest(unittest.TestCase):
    def test_score_ladder_is_the_20_official_steps(self):
        self.assertEqual([x["score"] for x in STD["scoreLadder"]], WANT_LADDER)

    def test_levels_map_to_the_four_bands(self):
        by = {x["score"]: x["level"] for x in STD["scoreLadder"]}
        for s, want in [(100, "优秀"), (95, "优秀"), (90, "优秀"), (85, "良好"), (80, "良好"),
                        (78, "及格"), (60, "及格"), (50, "不及格"), (10, "不及格")]:
            self.assertEqual(by[s], want, f"{s} 分档等级错")

    def test_limits_are_the_official_four(self):
        self.assertEqual(STD["limits"], {"maxStandardScore": 100, "maxSingleBonusScore": 10,
                                        "maxTotalBonusScore": 20, "maxTotalScore": 120})

    def test_weights_sum_to_hundred_per_gender(self):
        w = STD["weights"]
        self.assertEqual(sum(w.values()), 130, "男女并集 9 键：15+15+20+10+10+10+20 两遍")
        male = ["bmi", "vitalCapacity", "sprint50m", "sitAndReach", "standingLongJump",
                "pullUps", "run1000m"]
        female = ["bmi", "vitalCapacity", "sprint50m", "sitAndReach", "standingLongJump",
                  "sitUps", "run800m"]
        self.assertEqual(sum(w[k] for k in male), 100)
        self.assertEqual(sum(w[k] for k in female), 100)
        self.assertEqual(w, {"bmi": 15, "vitalCapacity": 15, "sprint50m": 20,
                             "sitAndReach": 10, "standingLongJump": 10, "pullUps": 10,
                             "sitUps": 10, "run800m": 20, "run1000m": 20})


class ThresholdTest(unittest.TestCase):
    def test_slot_count(self):
        check_slot_count(STD["events"])

    def test_null_layout_and_totals(self):
        check_null_layout(STD["events"])

    def test_monotonic(self):
        check_monotonic(STD["events"])

    def test_gender_specific_events_have_one_gender_only(self):
        self.assertEqual(STD["events"]["pullUps"]["genders"], ["male"])
        self.assertEqual(STD["events"]["run1000m"]["genders"], ["male"])
        self.assertEqual(STD["events"]["sitUps"]["genders"], ["female"])
        self.assertEqual(STD["events"]["run800m"]["genders"], ["female"])

    def test_unit_type_and_grade_map_are_the_contract_keys(self):
        # 这两键是 Task 1 复核补回来的（unitType 曾被 JSON.stringify 静默丢掉、
        # gradeToGroup 曾是 freshman/… 英文键）。下游按它们解单位与年级，必须钉住。
        self.assertEqual({k: v["unitType"] for k, v in STD["events"].items()},
                         {"vitalCapacity": "number", "sprint50m": "number", "sitAndReach": "number",
                          "standingLongJump": "number", "pullUps": "number", "sitUps": "number",
                          "run1000m": "mmss", "run800m": "mmss"})
        self.assertEqual(STD["gradeToGroup"],
                         {"大一": "grade12", "大二": "grade12", "大三": "grade34", "大四": "grade34"})

    def test_semantic_policy_keys_are_pinned(self):
        # 回源轮（2026-11-09）新增的四键是**算分语义**，不是装饰：错了不会报错，只会静默换一套规则。
        # 派生器里已有同样的闸，这里再钉一遍落盘产物——JSON 被手改时派生器的闸不会跑。
        ev = STD["events"]
        self.assertEqual(sorted(k for k, v in ev.items() if v["integerOnly"]),
                         ["pullUps", "run1000m", "run800m", "sitUps"])
        self.assertEqual({k: v["belowMinimumRuleStatus"] for k, v in ev.items()},
                         {k: "zero_score" for k in ev})
        self.assertEqual(sorted(k for k, v in ev.items() if v["allowZero"]),
                         ["pullUps", "sitAndReach", "sitUps", "standingLongJump", "vitalCapacity"])
        self.assertEqual(sorted(k for k, v in ev.items() if v["allowNegative"]), ["sitAndReach"])
        self.assertIs(STD["bmi"]["allowZero"], False)
        self.assertIs(STD["bmi"]["allowNegative"], False)

    def test_bonus_is_only_strength_and_endurance(self):
        self.assertEqual(sorted(k for k, v in STD["events"].items() if v["bonusEligible"]),
                         ["pullUps", "run1000m", "run800m", "sitUps"])

    def test_bonus_tables_descend_ten_to_one(self):
        for k, v in STD["events"].items():
            if v["bonusDeltas"]:
                self.assertEqual([t["bonusScore"] for t in v["bonusDeltas"]], list(range(10, 0, -1)), k)

    def test_strength_and_endurance_delta_ranges(self):
        self.assertEqual([t["delta"] for t in STD["events"]["pullUps"]["bonusDeltas"]],
                         list(range(10, 0, -1)))
        self.assertEqual([t["delta"] for t in STD["events"]["sitUps"]["bonusDeltas"]],
                         [13, 12, 11, 10, 9, 8, 7, 6, 4, 2])
        self.assertEqual([t["reductionSeconds"] for t in STD["events"]["run1000m"]["bonusDeltas"]],
                         [35, 32, 29, 26, 23, 20, 16, 12, 8, 4])
        self.assertEqual([t["reductionSeconds"] for t in STD["events"]["run800m"]["bonusDeltas"]],
                         [50, 45, 40, 35, 30, 25, 20, 15, 10, 5])


class BmiTest(unittest.TestCase):
    def test_four_categories_both_genders(self):
        for g in ("male", "female"):
            self.assertEqual(len(STD["bmi"]["categoriesByGender"][g]), 4, g)

    def test_categories_do_not_leave_gaps_on_scaled_scale(self):
        # 低体重下界与肥胖上界是开区间，落盘为 None；直接 sorted(…, reverse=True) 会
        # TypeError: '<' not supported between NoneType and int，所以按升序 + None 占位排序。
        for g in ("male", "female"):
            segs = sorted([(c["scaledMinInclusive"], c["scaledMaxInclusive"])
                           for c in STD["bmi"]["categoriesByGender"][g]],
                          key=lambda s: float("-inf") if s[0] is None else s[0])
            for lo, hi in zip(segs, segs[1:]):
                self.assertIsNotNone(lo[1], f"{g} 非最高档区间缺上界：{lo} {hi}")
                self.assertEqual(hi[0], lo[1] + 1, f"{g} 相邻 BMI 区间没接上：{lo} {hi}")
            # 三条内缝接上不等于整把刻度被铺满：两端必须是开区间，否则最低端/最高端留了洞
            self.assertIsNone(segs[0][0], f"{g} 低体重下界不是开区间：{segs[0]}")
            self.assertIsNone(segs[-1][1], f"{g} 肥胖上界不是开区间：{segs[-1]}")

    def test_bmi_scores_are_the_official_four(self):
        for g in ("male", "female"):
            self.assertEqual({c["category"]: c["score"] for c in STD["bmi"]["categoriesByGender"][g]},
                             {"normal": 100, "underweight": 80, "overweight": 80, "obese": 60})


class MetaTest(unittest.TestCase):
    def test_provenance_fields_are_present_and_verbatim(self):
        m = STD["meta"]
        for k in ("standardName", "standardDocNo", "schoolPolicyName", "schoolPolicyDocNo",
                  "policyEffectiveScope", "verifiedDate", "sourceSha256"):
            self.assertTrue(m.get(k), f"meta 缺 {k}")
        self.assertEqual(m["standardDocNo"], "教体艺〔2014〕5号")
        self.assertIn("2024级本科生起施行", m["policyEffectiveScope"])

    def test_three_unresolved_rules_are_kept(self):
        self.assertEqual(sorted(STD["unresolvedRules"]),
                         ["bmi_boundary_precision_unresolved",
                          "cuc_2024_policy_multi_year_scope_unresolved",
                          "measurement_precision_rounding_unresolved"])


class FileContractTest(unittest.TestCase):
    def test_css_has_no_raw_colors(self):
        css_path = ROOT / "web-next" / "tice.css"
        if not css_path.exists():
            # 本任务先于页面存在。让整套门保持绿：任何一条红都是真消息，
            # 而不是「反正有一条是预置的红」被顺手放过。Task 8 建出文件后这条自动生效。
            self.skipTest("web-next/tice.css 由 Task 8 创建")
        css = css_path.read_text(encoding="utf-8")
        bad = re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", css)
        self.assertFalse(bad, f"tice.css 出现裸色值：{bad[:5]}")

    def test_no_other_file_embeds_thresholds(self):
        # 不外调 grep：硬门不该依赖 PATH 上有哪个二进制，且 grep 无命中时 rc=1、
        # stdout 为空，原写法会把「没查到」报成「内嵌在 []」这种看不懂的失败信息。
        for probe in ("5040", "4920", "4550", "2300", "3030"):
            hits = [p.name for p in sorted((ROOT / "web-next").rglob("*"))
                    if p.is_file() and probe in p.read_text(encoding="utf-8", errors="ignore")]
            self.assertEqual(hits, ["tice-standard.json"],
                             f"特征值 {probe} 应只出现在 tice-standard.json，实得 {hits}")


class ProbeTest(unittest.TestCase):
    """假阳性检查：三项检查必须真的能红。用被改坏的副本喂同一个函数，不许比文件差异冒充。"""

    def setUp(self):
        self.ev = json.loads(json.dumps(STD["events"]))

    def test_disorder_injection_is_caught(self):
        self.ev["vitalCapacity"]["thresholds"]["male"]["grade12"][3] = 9999
        with self.assertRaises(AssertionError) as ctx:
            check_monotonic(self.ev)
        self.assertIn("vitalCapacity", str(ctx.exception))

    def test_missing_slot_is_caught(self):
        self.ev["sitAndReach"]["thresholds"]["female"]["grade12"].pop()
        with self.assertRaises(AssertionError) as ctx:
            check_slot_count(self.ev)
        self.assertIn("sitAndReach", str(ctx.exception))

    def test_extra_null_in_wrong_place_is_caught(self):
        self.ev["standingLongJump"]["thresholds"]["male"]["grade12"][6] = None
        with self.assertRaises(AssertionError) as ctx:
            check_null_layout(self.ev)
        self.assertIn("standingLongJump", str(ctx.exception))

    def test_untouched_copy_passes_all_three(self):
        check_slot_count(STD["events"])
        check_null_layout(STD["events"])
        check_monotonic(STD["events"])
