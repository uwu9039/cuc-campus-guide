"""auto_01 第二遍复核：脚本清理后暴露出的残留问题（社团名重复、段内列表符、标题与正文粘连）。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
LOG = ROOT / "_review_items" / "applied_auto_01b.txt"

# 名称重复：X + X + 谓语
DEDUP = [
    "pt-852e340c6d", "pt-800402f1cd", "pt-80ec8fa0fa", "pt-bc6be9bc2b",
    "pt-cc64b696fd", "pt-b190266e45", "pt-d0b2bee21e", "pt-fadf09ef64",
    "pt-ac6e578736", "pt-f0a6582259", "pt-89ad9b99c1", "pt-bb29f3bfa0",
    "pt-7ac57ec80d", "pt-ab7ad573b5", "pt-e8c1aba0f0", "pt-6a5a63092a",
    "pt-89dfdacb89", "pt-f76075bfcd", "pt-9ccaf3a791", "pt-dfe2eaeb9b",
    "pt-7cc6a0ce3b", "pt-b53cd9d4c9", "pt-e37150ea89", "pt-718af87787",
    "pt-882530223b", "pt-b3cc0c97fb", "pt-5d151023dc", "pt-a9d7b36823",
    "pt-d5cd289e2e",
]

REPAIRS = {
    # 部门/活动介绍：标题与正文粘连
    "pt-5d2407b3db": "综合拓展组是社团部至关重要的组成部分，承担着信息交互与资金支持的关键职责，是社团部稳定运行的重要保障，是社团部内外联络的综合枢纽。",
    "pt-a608b3ae46": "社团部职责：负责学生社团的成立、注册、注销和年审考核相关材料的复审和归档工作，准确掌握学生社团数量、学生社团成员和发展情况。",
    "pt-10bb49a51c": "为深入落实教育部、团中央《高校学生社团建设管理办法》精神，社团部迅速响应，结合本校实际情况，制定并印发了《中国传媒大学学生社团建设管理办法》，对社团类别开展创新整合工作，全面梳理现有社团情况，去除重复、同质化项目，优化精简社团分类及整体架构。",
    "pt-8933ef0701": "打造全新活动空间，助力社团发展。2023年秋，基于丰富学生课余生活、推动社团蓬勃发展的考量，正式启动轮滑广场建设，并于2024年9月正式启用，为社团提供多功能活动空间。",
    "pt-5b29200c1a": "建立全面智能化社团管理线上平台，完成社团活动线上审批系统的开发工作，正式上线《“优秀团学组织”社团评级表》，并完成全流程线上进行的社团年审工作。",
    "pt-c46b1f2a4e": "“百团大战”学生社团招新活动通常于10月举办，是新生进入校园接触到的第一个社团相关的大型活动，参与社团数量众多，每届超70个社团参与，系列推送总浏览量超10万次，极大拓展了校园文化传播版图。",
    "pt-579de5d78c": "社彩秋韵学生社团文化展演晚会是社团部主办的大型晚会，也是秋季新生入学后接触校内社团文化的第一台大型晚会。",
    "pt-8eef477da1": "舞动中传舞蹈类社团文化展演晚会是由社团部主办的大型晚会。",
    "pt-5ac7b4a9c7": "为支持校内社团蓬勃发展，为社团提供活动保障，社团部开展专项基金答辩会，社团在答辩会上介绍下学年预计举办的活动，并说明活动所需要的经费以及经费使用的必要性，社团部部长及组长根据答辩内容对答辩社团进行打分，最终按照分数排序给社团发放不同等级的资金，供社团举办相应活动，平均每年发放超3万元以供社团组织特色活动。",
    # 段内列表符
    "pt-d757485762": "活动需在学期第二周至第十四周提交申请。",
    "pt-a78007d4c9": "教室借用：通过“教室借用申请”服务上传审批单。",
    "pt-7b58774893": "提交购买链接：活动前20天提交商品链接（需支持电子发票和信用卡支付）。",
    "pt-70f65dece5": "总报销金额不得超过社团获批额度。",
    "pt-8b16567697": "业务指导单位的学生社团建设管理职责：加强对学生社团的业务指导，负责学生社团指导教师选聘评价，为社团日常运行与活动开展提供必要保障；组织学生社团学习党和国家的有关方针、政策及学生社团管理的相关规定。",
    "pt-71b167276b": "指导教师的主要职责。指导教师在业务指导单位的领导下对学生社团行使管理指导职责，包括：指导学生社团发展建设，把握社团发展的正确方向；规范学生社团日常管理，每学年指导学生社团制定工作计划，进行工作总结，审核学生社团注册登记材料，加强学生社团日常活动、宣传材料管理审批，指导学生社团规范开展全体成员大会。",
    "pt-f1d5684126": "有规范的名称和相应的组织机构，名称与其业务性质和特征相符，符合法律法规要求，符合校园文化建设的需要，不违背校园文明和社会公共道德；有规范的社团章程。",
    "pt-a5622f1645": "申请成立学生社团，发起人在业务指导单位指导下准备如下材料，经指导老师同意、业务指导单位复核后，向校团委提交：社团成立筹备申请书。",
    "pt-7fecdf4085": "学生社团成立审批程序：校团委对社团申请成立材料进行复核无误后，提交评议委员会核准并做出同意或不同意决定。",
    "pt-c2f1a0d91b": "学生社团负责人须具备以下条件：政治立场鲜明，自觉拥护中国共产党的领导，自觉践行社会主义核心价值观，遵守法律法规和校纪校规。",
    "pt-fd378cb5b6": "须是本科二年级（含）以上学生，上一学年综合测评排名须在本班前50%，成为该学生社团成员半年以上，并经常参加该学生社团活动（新成立的学生社团除外)；思想政治类社团和志愿公益类社团的主要负责人应为中共正式党员；本科生担任学生社团负责人，须事先征得班主任或辅导员同意；研究生担任学生社团负责人，须事先征得导师同意。",
    "pt-b89c4ab56a": "学生社团在日常运行工作中应履行下列职责：建立健全民主决策制度、考核奖惩制度、重大事项报告制度、财务管理制度、接受使用捐赠公示制度等工作制度；安排1名社团成员负责本社团内部财务工作，并接受全体成员和业务指导单位的财务监督。",
    "pt-f7df40d419": "按规定提交注册登记和年审考核材料，有关材料经业务指导单位初审后，送校团委进行复审和归档；社团的登记和备案事项需要变更时，按程序履行相关变更手续。",
    "pt-deead6fb9c": "各项资助经费应严格按照学校财务制度规范管理和使用，任何组织、单位和个人不得侵占、私分或挪用。",
    "pt-e5b15b0830": "每年，中国传媒大学团委会举办各类校级社团文化展演活动，其中“社彩秋韵”、“舞动中传”文化展演晚会既是同学们展示才艺、展现活力的舞台，也是社团间相互交流的平台，展现了我校学生全面发展、多才多艺的精神风貌。",
    "pt-cc43c3fb76": "DE街舞社创立于2003年，以“永舞无止境”为宗旨，通过参与广院之春、风采之星、舞动中传、社彩秋韵等大型文化展演活动，让全校同学感受到街舞的魅力。",
}


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def load_texts() -> dict[str, str]:
    idx = json.loads((ROOT / "sources" / "index.json").read_text(encoding="utf-8"))
    texts = {slug: squash((ROOT / "sources" / f"{slug}.txt").read_text(encoding="utf-8")) for slug in idx}
    for sub in ("wechat", "crawl", "cdp", "pdf", "chsi", "moe", "national", "extra", "huibian", "local", "wendao-extra", "wendao-text", "attachments/text", "ilib-text"):
        for f in (ROOT / "sources" / sub).glob("*.txt"):
            texts[f.stem] = squash(f.read_text(encoding="utf-8"))
    return texts


def retitle(item: dict, new_answer: str) -> None:
    old = item.get("title", "")
    suffix = " · " + old.rsplit(" · ", 1)[1] if " · " in old else ""
    short = new_answer[:40] + ("…" if len(new_answer) > 40 else "")
    item["title"] = short + suffix
    aliases = item.get("aliases") or []
    if aliases:
        aliases[0] = short
        item["aliases"] = aliases


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    texts = load_texts()
    log: list[str] = []
    changed = 0

    for it in data["items"]:
        iid = it["id"]
        old = it.get("answer") or ""
        new = old
        if iid in REPAIRS:
            new = REPAIRS[iid]
        elif iid in DEDUP:
            m = re.match(r"^([^\s，。；：、]{2,14}?)\1", old)
            if m:
                new = m.group(1) + old[m.end():]
        if new == old or not new:
            continue
        it["answer"] = new
        retitle(it, new)
        ev = (it.get("evidence") or {}).get("answer")
        if ev and squash(new) in texts.get(ev.get("src", ""), ""):
            ev["quote"] = new
        changed += 1
        log.append(f"FIX   {iid}\n  OLD {old}\n  NEW {new}")

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"第二遍修改 {changed} 条，剩余 {len(data['items'])} 条")


if __name__ == "__main__":
    main()
