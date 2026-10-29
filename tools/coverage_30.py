"""对照用户列出的 30 个主题，检查 items.json 覆盖情况，输出 sources/topic-coverage.json。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TOPICS = [
    ("生活事务", "宿舍水电费充值", ["hq-goudian", "zyshui-butie", "xyk-chongzhi"], None),
    ("生活事务", "热水 / 洗浴规则", ["sushe-xizao", "zyshui-butie"], None),
    (
        "生活事务",
        "校园卡使用与丢失补办",
        ["xyk-buka", "xyk-guashi", "xyk-yishi", "xyk-yanqi", "xyk-chongzhi", "shitang-wukou"],
        None,
    ),
    ("生活事务", "宿舍电器使用规则", ["sushe-dianqi"], None),
    ("生活事务", "报修流程", ["hq-baoxiu", "it-wangluo", "xinxi-fuwu-daohang"], None),
    (
        "生活事务",
        "快递和外卖存放点",
        ["kuaidi-yizhan"],
        "快递有官方依据；外卖存放点官方文件未收录，只会答“知识库未收录”",
    ),
    ("生活事务", "洗衣晾晒规则", ["xiyi-liangshai"], None),
    ("学习教务", "选课流程", ["jwc-buxuanke", "rule-20201124-c6366a176044", "fuxiu-baoming"], None),
    ("学习教务", "转专业规则", ["zhuanzhuanye"], "另有 20+ 条学院转专业细则条目"),
    ("学习教务", "绩点 / 学分 / 重修", ["xueji-liuji", "xueji-biye", "jwc-zhuanhuan"], None),
    (
        "学习教务",
        "考试与考勤",
        ["jwc-cet", "kaoshi-weiji", "jwc-chengji-fuhe", "jwc-kaoshi"],
        None,
    ),
    (
        "学习教务",
        "免修 / 缓考 / 休学",
        ["jwc-tiyu", "tizhi-miance", "jwc-zixiu", "xueji-huankao", "xueji-xiuxue", "xueji-fuxue", "xueji-baoliu"],
        None,
    ),
    (
        "学习教务",
        "教材 / 实验课 / 机房要求",
        ["jiaocai-fafang", "rule-20240304-c6487a216884", "rule-dfb6c69a", "rule-3f058183", "qa-18fe5c7d-48"],
        "机房使用规则官方文件未单独收录",
    ),
    (
        "校园空间",
        "教学楼 / 教室编号",
        ["campus-jiancheng", "campus-louming", "jiaoshi-jieyong", "baogaoting-yuyue"],
        None,
    ),
    ("校园空间", "图书馆使用", ["lib-jieyue"], None),
    ("校园空间", "校医院就医与医保", ["xyy-jiuzhen", "xyy-gongfei"], None),
    (
        "校园空间",
        "校园网和账号",
        [
            "it-wangluo",
            "it-wangfei",
            "it-mima",
            "it-vpn",
            "it-ganzhi",
            "it-jihuo",
            "it-shensu",
            "it-youxiang",
            "xinxi-fuwu-daohang",
        ],
        None,
    ),
    (
        "校园空间",
        "校内交通",
        ["it-jiaotong", "zxc-chongdian"],
        "校车 / 班车、共享单车官方文件未收录，只会答“知识库未收录”",
    ),
    ("制度手续", "奖助学金", ["jiangxuejin", "zxj-guojia", "xszz-qingong"], None),
    ("制度手续", "助学贷款和缴费", ["dk-zhuxue", "zb-zizhu"], "学费缴纳另有《校园统一支付平台》操作指南条目"),
    (
        "制度手续",
        "党团关系转接",
        ["rule-da6bcf3c", "rule-402ecf2831", "rule-ebd32b2d", "rule-e9b74298dd"],
        None,
    ),
    (
        "制度手续",
        "请假 / 走读 / 换宿",
        ["qa-18fe5c7d-13", "sushe-huansu", "sushe-tuixiu"],
        None,
    ),
    (
        "制度手续",
        "学生证 / 身份证 / 档案材料管理",
        [
            "qa-18fe5c7d-43",
            "doc-20260528-c2753a271114",
            "jwc-zaidu",
            "jwc-chengjidan",
            "chsi-baogao",
            "biye-hukou-dangan",
        ],
        None,
    ),
    # 额外 7 个高频主题
    ("延伸", "军训与新生报到", ["xinsheng-baodao"], None),
    ("延伸", "就业手续", ["jy-shouxu", "chsi-baogao"], None),
    ("延伸", "出国 / 境外交流", ["liuxue-jiaoliu", "waijing-jiaoliu", "jwc-zhuanhuan"], None),
    ("延伸", "体育课与体测", ["jwc-tiyu", "tizhi-miance"], None),
    ("延伸", "宿舍门禁与安全", ["sushe-menjin", "sushe-yaoshi", "sushe-zhengming"], None),
    ("延伸", "食堂与餐饮", ["shitang-wukou"], "仅覆盖误扣款；菜品、营业时间官方文件未收录"),
    ("延伸", "推免 / 保研", ["tuimian-2027"], None),
]


def main() -> None:
    items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]
    ids = {it["id"] for it in items}
    rows = []
    missing = []
    for group, topic, want, note in TOPICS:
        found = [i for i in want if i in ids]
        lost = [i for i in want if i not in ids]
        if lost:
            missing.extend((topic, i) for i in lost)
        rows.append(
            {
                "group": group,
                "topic": topic,
                "items": found,
                "count": len(found),
                "covered": bool(found),
                "note": note,
            }
        )
    out = {"updated": "2026-10-29", "total_topics": len(rows), "topics": rows}
    (ROOT / "sources" / "topic-coverage.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"主题 {len(rows)} 个")
    for r in rows:
        mark = "OK " if r["covered"] else "缺口"
        print(f"  {mark} [{r['group']}] {r['topic']}: {r['count']} 条 — {', '.join(r['items'][:4])}")
        if r["note"]:
            print(f"       注：{r['note']}")
    if missing:
        print("\n以下 id 不存在：")
        for t, i in missing:
            print(" ", t, i)


if __name__ == "__main__":
    main()
