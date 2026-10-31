"""auto_03 人工复核：办公地点表编号、共青团大纲标题粘连、学士学位页眉乱码、
青马通知页码、高性能计算手册 OCR、志联总结标题粘连与列表残段、论文规范标题粘连。

判定原则：
- 只删不可独立成句、OCR 错误会误导、或内容已被合并条完整保留的自动碎片
- 能修的优先修：去掉编号/标题/页码，保留原文连续片段
- 列表残段合并回主条后再删碎片，删前逐条核对
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
LOG = ROOT / "_review_items" / "applied_auto_03.txt"

DROPS = {
    "pt-c7ff816874": "无主语残句，指代上文「未来影像中心」",
    "pt-72471c0fae": "「按要求加强冷链食品管控」12字空泛句，无可执行信息",
    "pt-0c067d48f9": "食堂委员会职责尾段，内容并入 pt-1b84555868",
    "pt-d241427e47": "食堂职责（三）（四）（五），内容并入 pt-6b95abe59c",
    "pt-98cd19c382": "食堂职责（六）（七），内容并入 pt-6b95abe59c",
    "pt-c45d0976b1": "表格注释「标注▲」，脱离表格无意义",
    "pt-da66295823": "表格注释「标注※」，脱离表格无意义",
    "pt-7e63a33b24": "公文头（印发通知与收文单位），非事项",
    "pt-58570b52b4": "「以下均需注明推荐排序」无主语残句",
    "pt-1f9ed79f99": "387字公文头，招募条件与流程另有专条",
    "pt-02b5ac44af": "OCR 乱码：dhttps、cuc.eu.cn、下图",
    "pt-0716fa17e9": "OCR 邮箱域名错误：cuc.eu.cn",
    "pt-16713b7e12": "OCR 表头乱码：di、MNAE、MTIE",
    "pt-2ae52745ff": "OCR 目录名错误：rshae",
    "pt-5e7da75743": "OCR 路径乱码：drc/dddrc/drrrc",
    "pt-83778c9ed4": "截断残句，结尾「（！」",
    "pt-92a637324d": "OCR 目录名错误：rshae",
    "pt-9f8c91e3b0": "OCR 命令错误：scancel+jobID",
    "pt-a0c831b5f5": "表头与首行粘连，关键词含义不完整",
    "pt-e0d65c7c25": "OCR 路径与命令乱码",
    "pt-d313f50f94": "残句「项目成员：计算研究任务开展」",
    "pt-1628bb3662": "活动名残句，内容并入 pt-39f9fe6775",
    "pt-33478be718": "活动名残句，内容并入 pt-39f9fe6775",
    "pt-486a6850fe": "活动名残句，内容并入 pt-39f9fe6775",
    "pt-608bc8c045": "分类残句，内容并入 pt-618d77a7a4",
    "pt-82892c9cd4": "分类残句，内容并入 pt-618d77a7a4",
    "pt-0e57a23220": "「形象松暖暖的展示」语序错乱，品牌宣传低价值",
    "pt-d096aa64c8": "「加入…计划」无主语残句",
    "pt-056263dcf1": "「脚注紧跟在该页的下面）。」括号残句",
    "pt-0c9740cf0e": "「主要包括绪论…」无主语残句",
    "pt-0eea6eac52": "教改总结模板问句，非规范条文",
    "pt-19ac2645b2": "教改总结模板问句，非规范条文",
    "pt-16c5725374": "评分档次残句，无主语",
    "pt-2204ad539a": "两个评分档次粘连，句读混乱",
    "pt-2bdf587dc1": "「教师对资料收集的指导。」列表残句",
    "pt-38f4d4820c": "「例如样本、问卷…」无主语残句",
}

PRE = {
    "pt-02fed94bd3": "160、", "pt-03ab29a810": "167、", "pt-186ed80519": "168、",
    "pt-220fcc4f09": "139、", "pt-240506856c": "162、", "pt-342a2a0755": "166、",
    "pt-41a3859209": "161、", "pt-643a20289c": "163、", "pt-e5085d8d59": "164、",
    "pt-eaa48aa173": "165、",
    "pt-2f2175bf72": "三、评价原则", "pt-317132aa16": "四、评价主体",
    "pt-52d64b87a9": "一、基本思路", "pt-57838994ca": "二、评价对象",
    "pt-bd9e4adce7": "新时代共青团激励机制指导大纲（试行）",
    "pt-d0f280fd5a": "一、基本思路", "pt-dd6a19a643": "六、指标体系",
    "pt-fbbbed3d51": "共青团中央办公厅2020年12月31日新时代共青团员先进性评价指导大纲（试行）",
    "pt-04555a51f0": "六、录取公示", "pt-0eeb01dc3c": "三、招生条件",
    "pt-1aacf92212": "四、学习安排及日常管理", "pt-613aba4e54": "七、工作要求",
    "pt-bff41022e7": "五、工作流程", "pt-d93968432c": "一、组织架构",
    "pt-d62bf54f38": "二、招生对象", "pt-766eff849c": "4", "pt-c6c98bcfa5": "5",
    "pt-5c52050cd5": "3.作业终止3-1web页面终止作业", "pt-708e4b2968": "2.项目组命名规范",
    "pt-8101291210": "3.项目成员3-1成员类型", "pt-8fdd4d1107": "2.作业提交2-1web页面提交作业",
    "pt-95e87cbe2d": "3.数据总览", "pt-9a6251f2fd": "1.资源总览",
    "pt-a60f9fe1cc": "6.指定项目申请资源", "pt-a87b05b31f": "5.项目账户充值5-1个人账户转账",
    "pt-c3c0f8130f": "7.删除项目", "pt-ccbd9aa96b": "3.重置密码",
    "pt-0614d7483d": "1.创建项目", "pt-0734c5e200": "2.账户总览",
    "pt-98d80af755": "5-2邮件反馈",
    "pt-1f37909235": "一、部门概述", "pt-601d8697e4": "一、部门概述",
    "pt-69c1fdcded": "一、部门概述", "pt-76bc380e58": "一、部门概述",
    "pt-845333d7fe": "一、部门概述", "pt-ac199c9bfe": "一、国家重大活动服务保障任务",
    "pt-226948c207": "四、宣传与经验分享", "pt-4397e69414": "二、主要活动",
    "pt-944245733d": "四、宣传与经验分享", "pt-bda4d818c9": "四、宣传与经验分享",
    "pt-c0eee6005d": "四、宣传与经验分享", "pt-341b4fce55": "三、贡献度",
    "pt-353b6db8ca": "三、贡献度",
    "pt-228d16442c": "1.积极创新校内志愿活动形式", "pt-22d1b5dc83": "（2）中传志联急救队组建",
    "pt-2b1807d566": "1.“暖暖云课堂”线上支教项目",
    "pt-2d4dccd773": "（3）12.1世界艾滋病日宣传摆台活动",
    "pt-429cc19016": "2.“暖暖向前跑”暑期夏令营", "pt-532e19302f": "3.手语歌公益展演",
    "pt-69a187b279": "4.手语线上线下公益课堂", "pt-6dce0344ac": "1.星星雨日间志愿陪护",
    "pt-76c6c4cf6f": "2.“小陶子”流动图书馆", "pt-87b93ef69f": "2.急救培训活动",
    "pt-8cca3de30b": "4.眼科义诊活动",
    "pt-8f80d61861": "1.防艾系列活动（1）首都高校红丝带防艾校园情景剧拍摄",
    "pt-9133b8f72a": "1.电影博物馆志愿服务", "pt-93d0c508e9": "3.无偿献血活动",
    "pt-a19e5d17d1": "（2）防艾同伴教育", "pt-ad25d5efc5": "3.志联暖暖夏令营暑期支教项目",
    "pt-afebabdbb1": "3.注重笃行实干，投身社会实践",
    "pt-b336770c00": "2.急救系列活动（1）急救培训",
    "pt-b5a5f563d2": "3.养老社区定期陪伴", "pt-c0e1b7d878": "1.中医药文化进校园活动",
    "pt-c70b0ce122": "2.融爱融乐心伙伴计划",
    "pt-d1d3630bf2": "2.春日穿搭指南：“春日焕新计划”",
    "pt-d3ffe83946": "2.国家图书馆线上文献整理项目",
    "pt-0717ef9756": "1.“世界孤独症日”系列主题活动",
    "pt-083afc183e": "（九）正文", "pt-0f1434f8fb": "八、评分要求（一）指导教师评阅",
    "pt-1a7ebdc038": "（三）最终成绩评定",
}

SUF = {"pt-d98093724e": "章学位程第三授予序"}

SUB = {
    "pt-f178869c25": ("需3达到", "需达到"),
    "pt-107453b3c8": ("中期检查中期检查", "中期检查"),
    "pt-6236349c91": ("！！", ""),
    "pt-e0830a5c06": ("其中：", ""),
}

TAIL_SEMI = {
    "pt-099125ae5c", "pt-0c7ffff86c", "pt-2a245e81d2", "pt-41f89bce80", "pt-fb41155064",
}

SPECIAL = {
    "pt-1b84555868": (
        "委员会主要职责如下：（一）制定学校食堂管理制度，统筹组织领导、监督检查食堂管理和服务工作；"
        "（二）建立协同联动、齐抓共管的工作机制，明确学校各职能部门对食堂管理工作的职责分工；"
        "（三）完善考核评价机制，委员会成员单位每年向委员会汇报本年度履职和管理情况，全面提升食堂管理水平；"
        "（四）畅通学校和学生的沟通渠道，深入细致地做好思想教育工作，增进学生对食堂工作的理解，定期开展满意度测评；"
        "（五）研究解决食堂工作中出现的重大问题，提出工作要求。视情况需要向学校党委常委会或校长办公会进行工作汇报；"
        "（六）根据上级主管部门要求，做好有关食堂管理服务的其他工作。"
    ),
    "pt-6b95abe59c": (
        "饮食服务中心的主要职责如下：（一）宣传贯彻国家和北京市有关法律法规以及上级主管部门的各项规章制度，"
        "维护食堂的正常就餐秩序；（二）制定食堂工作计划，组织食堂的生产加工和销售，按时按质按量保证伙食供应，"
        "不断提升饮食服务质量，满足师生员工不同层次的饮食需求；（三）加强食品安全生产，不断规范、完善食品卫生管理工作，"
        "狠抓原材料采购、贮存、加工、销售等各个环节，落实食品安全生产责任制，杜绝各类食品安全事故的发生；"
        "（四）加强从业人员业务技能培训和个人卫生管理，积极推行服务承诺制，不断提高餐饮服务质量和从业人员业务素质；"
        "（五）强化伙食成本核算，合理使用各类资金，不断改善食堂就餐条件，营造良好的就餐环境；"
        "（六）定期与校学生会生活权益部召开生活座谈会，听取学生意见和建议，不断改进管理措施和服务质量；"
        "（七）做好假期食堂管理及服务工作。"
    ),
    "pt-170a63c065": (
        "毕业论文及相关表格顺序：（1）封面；（2）中英文摘要（含关键词）；（3）目录；（4）正文；（5）注释；"
        "（6）参考文献；（7）附录；（8）后记；（9）审题表；（10）指导记录表；（11）指导教师意见；"
        "（12）评阅人意见；（13）成绩表；（14）答辩记录；（15）封底。"
    ),
    "pt-8101291210": "项目组用户分管理员、组长和组员。",
    "pt-7bb0bd7aee": "在“设置账号”中设置绑定个人邮箱即可。",
    "pt-29c33d3973": (
        "荣誉授予和表彰采取自下而上（基层单位、县、市、省、全国，系统团委参照执行）、阶梯晋级的方式开展，"
        "坚持以下原则：（1）参评上一级荣誉，原则上须已获本级或下一级同类荣誉，且获得时间不在同一年度"
        "（如：参评省级优秀共青团员，须已获评市级或县级优秀共青团员。针对评选周期不一致的地区，"
        "支撑荣誉可扩大至相应级别的同类型荣誉）；"
    ),
    "pt-39f9fe6775": (
        "中传志联还开展了多项富有创意的公益活动，包括：“舞动星空”融合舞蹈活动。"
        "“小陶子”流动图书馆绘本共读活动。“暖暖来信·爱有回响”手写信志愿活动。“心语之声”手语公益课等。"
    ),
    "pt-618d77a7a4": (
        "近年来，校团委精心策划并实施了180项志愿服务活动，包括：校外活动：如“京彩文化青春绽放”行动、"
        "国家图书馆、中国电影博物馆、北京城市图书馆、中山公园等场馆服务。社区服务：助老助残、"
        "关爱少年儿童等专项活动。校内活动：义诊急救、献血防艾、艺考迎新、旧衣旧书回收等。"
        "荣誉与认可：被中国电影博物馆授予“优秀协作单位”，收到中华慈善总会感谢信。"
    ),
    "pt-0416d6bfc0": (
        "封面颜色一般为白色，要按照学校统一规定的格式排版，论文题目是文章总体内容的体现，"
        "应简洁明确、有概括性，字数不宜超过20个字，可分为两行。"
    ),
    "pt-cbb16ae9e0": "“故书共读，衣旧焕新”旧衣旧书捐赠活动如期开展。",
    "pt-753b88d60c": "项目管理员可创建项目，可充入项目点数，也可转出项目点数。",
    "pt-be7fd1dbef": (
        "1.实验文件上传\n"
        "1-1 web页面进行数据传输\n"
        "1-1-1 可在资源总览页面下点击“文件夹”图标，上传所需实验文件，选择本地资源和平台上传路径。\n"
        "1-1-2 可在数据总览页面上传所需实验文件。\n"
        "1-2 ssh端口进行数据传输\n"
        "由于Web传输文件功能有限，对于开放了SSH端口的集群或实例，用户可以通过SSH账户使用scp类的工具来传输数据。"
    ),
    "pt-de22c73ab9": (
        "集群的计算节点默认不允许用户直接登录，对需要交互式处理的程序，在登录到集群后，使用salloc命令分配节点，"
        "然后再ssh到分配的节点上进行处理。计算完成后，使用exit命令退出节点，注意需要exit两次，"
        "第一次exit是从计算节点退出到登录节点，第二次exit是释放所申请的资源。"
    ),
}


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def load_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    for sub in ("", "wechat", "crawl", "cdp", "pdf", "chsi", "moe", "national", "extra",
                "huibian", "local", "wendao-extra", "wendao-text", "attachments/text", "ilib-text"):
        base = ROOT / "sources" / sub if sub else ROOT / "sources"
        for f in base.glob("*.txt"):
            texts[f.stem] = squash(f.read_text(encoding="utf-8"))
    return texts


def retitle(item: dict, new_answer: str) -> None:
    old = item.get("title", "")
    suffix = ""
    if " · " in old:
        suffix = " · " + old.rsplit(" · ", 1)[1]
    item["title"] = new_answer[:40] + ("…" if len(new_answer) > 40 else "") + suffix
    aliases = item.get("aliases") or []
    if aliases:
        aliases[0] = new_answer[:40] + ("…" if len(new_answer) > 40 else "")
        item["aliases"] = aliases


def build_changes(items: dict[str, dict]) -> dict[str, str]:
    changes: dict[str, str] = {}
    for pid, prefix in PRE.items():
        old = items[pid]["answer"]
        if not old.startswith(prefix):
            raise SystemExit(f"前缀不匹配 {pid}: {old[:40]}")
        changes[pid] = old[len(prefix):]
    for pid, suffix in SUF.items():
        old = items[pid]["answer"]
        if not old.endswith(suffix):
            raise SystemExit(f"后缀不匹配 {pid}: {old[-30:]}")
        changes[pid] = old[:-len(suffix)]
    for pid, (a, b) in SUB.items():
        old = items[pid]["answer"]
        if a not in old:
            raise SystemExit(f"子串不匹配 {pid}")
        changes[pid] = old.replace(a, b)
    for pid in TAIL_SEMI:
        old = items[pid]["answer"]
        if not old.endswith("；"):
            raise SystemExit(f"结尾不是分号 {pid}: {old[-20:]}")
        changes[pid] = old[:-1] + "。"
    changes.update(SPECIAL)
    overlap = set(DROPS) & set(changes)
    if overlap:
        raise SystemExit(f"同一条既删又改：{overlap}")
    return changes


def main() -> None:
    dry = "--dry-run" in sys.argv
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = {it["id"]: it for it in data["items"]}
    texts = load_texts()

    missing = [pid for pid in list(DROPS) + list(PRE) + list(SUF) + list(SUB) + list(SPECIAL)
               if pid not in items]
    if missing:
        raise SystemExit(f"条目不存在：{missing}")

    changes = build_changes(items)
    log: list[str] = []

    not_in_source = []
    for pid, new in changes.items():
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if squash(new) not in texts.get(src, ""):
            not_in_source.append((pid, src, new[:60]))

    for pid, reason in sorted(DROPS.items()):
        log.append(f"DROP  {pid}  {reason}  |  {items[pid]['answer'][:50]}")
    for pid in sorted(changes):
        log.append(f"FIX   {pid}  {items[pid]['answer'][:50]}  ->  {changes[pid][:70]}")

    print(f"删除 {len(DROPS)} 条，修改 {len(changes)} 条，当前 {len(data['items'])} 条")
    if not_in_source:
        print(f"\n改写后不是原文连续片段 {len(not_in_source)} 条（保留原引文）：")
        for pid, src, head in not_in_source:
            print(f"  {pid} {src} {head}")

    if dry:
        print("\n".join(log[:20]))
        return

    for pid in DROPS:
        data["items"].remove(items[pid])
    for pid, new in changes.items():
        it = items[pid]
        old = it["answer"]
        if new == old or not new:
            raise SystemExit(f"空改写 {pid}")
        it["answer"] = new
        retitle(it, new)
        ev = (it.get("evidence") or {}).get("answer")
        if ev and squash(new) in texts.get(ev.get("src", ""), ""):
            ev["quote"] = new

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"已写回，剩余 {len(data['items'])} 条；日志 {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
