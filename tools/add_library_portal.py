"""把图书馆门户「本馆简介」和 2026-10-27 大屏阅览区公告落盘成源，并补成条目。

来源
  https://ilib.cuc.edu.cn/                               本馆简介（2025年12月版，含空间布局与馆藏统计）
  https://ilib.cuc.edu.cn/v2/sub/0f27ed3da20addfc60dcc035ddc642f4   大屏阅览区正式投入使用

用法：python tools/add_library_portal.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
EXTRA = SRC / "extra"
TZ = timezone(timedelta(hours=8))

ABOUT_URL = "https://ilib.cuc.edu.cn/"
ABOUT_TITLE = "中国传媒大学图书馆·本馆简介（2025年12月版）"
ABOUT_TEXT = """中国传媒大学图书馆·本馆简介
来源：https://ilib.cuc.edu.cn/
页面发布时间：2025-12-24 10:00

中国传媒大学图书馆（大阅城）馆舍于2012年竣工并交付使用，是一座集文献收藏、学术研究、学科服务与文化传播于一体的现代化图书馆。主体建筑由主楼和副楼组成，地上七层，地下两层，总建筑面积达4.3万余平方米。目前，图书馆与传媒博物馆、档案（校史）馆共同入驻于此。其中，一至六层为图书馆主要功能区域，使用面积超过2.6万平方米。在2022年7月完成新一轮升级改造后，图书馆于同年10月28日以全新的面貌全面恢复开放。

图书馆秉承开放、自助的服务理念，全面实行“借、阅、藏、研”一体化的管理模式。空间布局科学合理：地上一层设有中传学者文库、密集音像资料库、教师书吧及借阅咨询区；二层为报刊阅览区与静音阅读区；三至五层为普通图书借阅区，每层中间靠近电梯厅设有视听间，其中五层特别设立外文图书专区与深度自习区；六层除库本阅览区与古籍文库外，另设有深度阅读区以及深度服务于学校交叉学科发展战略的“区域国别学学科馆”；二层至四层东南侧靠窗区域设有各类研讨间。

2024年9月25日，中传学者文库揭牌投入使用。“中传学者文库”是图书馆的特色馆藏空间，系统收藏和展示我校学者的学术著作、手稿及研究成果，集中呈现中传学人的学术传承与创新脉络，成为彰显学校学术底蕴、促进师生学术交流的重要学术高地。

2025年11月5日，区域国别学学科馆揭牌投入使用。区域国别学学科馆作为图书馆学科服务体系的深化与延伸，系统整合了国际政治、国际关系、国际传播、国别媒体研究、跨文化交流等领域的学术资源，旨在构建一个集专题文献保障、学术研究支持、国际学术交流于一体的高水平知识平台。它的设立是图书馆主动对接国家战略、支撑学校“双一流”学科建设的重要举措。

截至2025年11月，图书馆共拥有各类阅览座位4200余个，并配备了20间研讨间、3间视听间、16个静音舱、20个蛋形椅、休闲沙发等多种阅览空间，为师生提供了多元化、智能化的学习与研究环境。馆藏资源方面，截至2025年底，累计拥有纸本图书190多万册（包含8万册外文原版图书及4.3万册古籍），累计订购纸质报刊2000余种，开通中外文数据库40余个，涵盖电子期刊5万余种、电子图书700余万册、中外文学位论文1000余万篇，音像资料3万余件。面向未来，中国传媒大学图书馆将坚定立足“四个中心”——即纸质文献与数据资源汇聚中心、智能泛在共享学习中心、学科建设信息服务中心、传媒与艺术教育资源集散中心的战略定位。以“中传学者文库”、“区域国别学学科馆”等特色空间与深度学科服务为代表，图书馆正朝着资源特色化、服务智能化、技术赋能化、空间人文化的方向稳步迈进，全力建设与“中国特色、世界一流”传媒大学相匹配的、特色鲜明的未来学习与创新融合中心。

中国传媒大学图书馆
2025年12月
"""

NEWS_URL = "https://ilib.cuc.edu.cn/v2/sub/0f27ed3da20addfc60dcc035ddc642f4"
NEWS_TITLE = "教育资源中心（图书馆）大屏阅览区正式投入使用"
NEWS_TEXT = """教育资源中心（图书馆）大屏阅览区正式投入使用
作者：曹兰琴
发布时间：2026-10-27 12:31:36

（通讯员 曹兰琴）2026年10月27日，教育资源中心（图书馆）在五层阅览区建成大屏阅览区，20台专业大屏幕显示器全部就位，正式投入使用。

当AI浪潮席卷创作领域，当每一帧画面都值得被认真对待，学习创作的“装备”亟待升级。该区域面向视频剪辑、影视创作、代码开发与AI实训等专业场景，为师生提供超宽视野、专业色准的创作工位。面向AI时代的创作需求，这里只等你带着灵感前来体验。

一、超宽视界，一屏尽收

每台显示器均为34英寸21:9超宽带鱼屏，1500R曲面环抱视野，分辨率达WQHD（3440×1440）。剪辑时，左侧轨道、中间素材库、右侧预览可同屏展开，时间线不再局促；编写代码时，更能获得更长的纵向视野。相较传统16:9显示器，超宽屏幕让多任务并行从容不迫。

每台显示器均提供HDMI和USB-C两种接口，支持笔记本电脑一线连接，也支持具备USB-C接口显示输出功能的手机、平板电脑等设备将内容投屏显示，操作更加自由便捷。

二、专业画质，为创作而生

HDR400高动态显示技术让画面明暗层次纤毫毕现，99% sRGB广色域精准还原每一处色彩细节，调色时不必担心“屏上一套、导出另一套”。200Hz高刷新率与1ms GTG快速响应，让预览丝般顺滑；屏幕内置11种情景模式，阅读、观影、护眼一键切换，长时间创作也能保持轻松舒适。

三、为谁而建？为每一个爱创作、爱编程的你

无论你是剪辑作业的影视专业同学、打磨毕业作品的创作达人，还是潜心写代码的技术爱好者，这里都是理想的工位：剪视频时，超宽屏让你与时间线“打交道”更高效；做设计时，广色域助你精修每一个像素；跑AI实训时，大屏多窗口并行让工作流一目了然。

四、阅览位置

大屏阅览区设置在图书馆五层滚梯旁、邻近中央天井的区域。

五、使用规则与预约攻略

1. 请预约使用，座位号为5579~5618，预约方法与其他座位相同。

2. 请使用静音键盘，避免相互影响。

3. 大屏阅览区资源有限，仅供师生视频剪辑、创作、写论文、编程等专业用途，请勿用于玩游戏、看小视频等娱乐用途。

大屏已亮起，灵感正当时。欢迎师生走进图书馆五层视频创作大屏阅览区，亲手体验专业大屏带来的全新创作感受——你的下一部作品，也许就诞生在这里！
"""


def src_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:10]


def write_source(url: str, title: str, text: str) -> str:
    sid = src_id(url)
    EXTRA.mkdir(parents=True, exist_ok=True)
    (EXTRA / f"{sid}.txt").write_text(text, encoding="utf-8", newline="\n")
    index_path = SRC / "extra-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index[sid] = {
        "url": url,
        "title": title,
        "chars": len(text),
        "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
        "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "kind": "extra",
    }
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return sid


def base_item(item_id: str, title: str, aliases: list[str], keywords: list[str],
              steps: list[dict], evidence: dict, *, source: dict,
              location: str | None = None, pitfalls: list[str] | None = None) -> dict:
    return {
        "id": item_id,
        "title": title,
        "aliases": aliases,
        "keywords": keywords,
        "dept": "图书馆",
        "channel": ["线下"],
        "audience": ["本科生", "研究生", "教职工"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": steps,
        "fee": None,
        "location": location,
        "hours": None,
        "duration": None,
        "window": None,
        "pitfalls": pitfalls or [],
        "contact": None,
        "slots": [],
        "draft": None,
        "answer": None,
        "kind": "service",
        "source": [source],
        "evidence": evidence,
    }


def main() -> None:
    about_id = write_source(ABOUT_URL, ABOUT_TITLE, ABOUT_TEXT)
    news_id = write_source(NEWS_URL, NEWS_TITLE, NEWS_TEXT)

    about_src = {"title": ABOUT_TITLE, "url": ABOUT_URL, "checked": "2026-10-29"}
    news_src = {"title": NEWS_TITLE, "url": NEWS_URL, "checked": "2026-10-29"}

    items_path = ROOT / "items.json"
    data = json.loads(items_path.read_text(encoding="utf-8"))
    items = data["items"]
    by_id = {it["id"]: i for i, it in enumerate(items)}

    new_items = [
        base_item(
            "lib-benguan-buju",
            "图书馆楼层布局（一层到六层）",
            [
                "图书馆楼层布局", "图书馆各层", "图书馆每层有什么", "图书馆布局",
                "图书馆空间布局", "图书馆有哪些空间", "图书馆各层分布", "大阅城楼层分布",
                "图书馆一层有什么", "图书馆二层有什么", "图书馆六层有什么",
                "图书馆研讨间在哪层", "图书馆主楼布局",
            ],
            ["楼层布局", "空间布局"],
            [
                {"when": "馆舍概况", "what": "中国传媒大学图书馆（大阅城）馆舍于2012年竣工并交付使用，主体建筑由主楼和副楼组成，地上七层，地下两层，总建筑面积达4.3万余平方米。", "where": "大阅城"},
                {"when": "使用面积", "what": "其中，一至六层为图书馆主要功能区域，使用面积超过2.6万平方米。在2022年7月完成新一轮升级改造后，图书馆于同年10月28日以全新的面貌全面恢复开放。"},
                {"when": "一层", "what": "地上一层设有中传学者文库、密集音像资料库、教师书吧及借阅咨询区", "where": "一层"},
                {"when": "二层", "what": "二层为报刊阅览区与静音阅读区", "where": "二层"},
                {"when": "三至五层", "what": "三至五层为普通图书借阅区，每层中间靠近电梯厅设有视听间，其中五层特别设立外文图书专区与深度自习区", "where": "三至五层"},
                {"when": "六层", "what": "六层除库本阅览区与古籍文库外，另设有深度阅读区以及深度服务于学校交叉学科发展战略的“区域国别学学科馆”", "where": "六层"},
                {"when": "研讨间", "what": "二层至四层东南侧靠窗区域设有各类研讨间", "where": "二层至四层东南侧"},
                {"when": "中传学者文库", "what": "2024年9月25日，中传学者文库揭牌投入使用。", "where": "一层"},
                {"when": "区域国别学学科馆", "what": "2025年11月5日，区域国别学学科馆揭牌投入使用。", "where": "六层"},
            ],
            {
                "steps.0": {"src": about_id, "quote": "中国传媒大学图书馆（大阅城）馆舍于2012年竣工并交付使用，是一座集文献收藏、学术研究、学科服务与文化传播于一体的现代化图书馆。主体建筑由主楼和副楼组成，地上七层，地下两层，总建筑面积达4.3万余平方米。"},
                "steps.1": {"src": about_id, "quote": "其中，一至六层为图书馆主要功能区域，使用面积超过2.6万平方米。在2022年7月完成新一轮升级改造后，图书馆于同年10月28日以全新的面貌全面恢复开放。"},
                "steps.2": {"src": about_id, "quote": "地上一层设有中传学者文库、密集音像资料库、教师书吧及借阅咨询区"},
                "steps.3": {"src": about_id, "quote": "二层为报刊阅览区与静音阅读区"},
                "steps.4": {"src": about_id, "quote": "三至五层为普通图书借阅区，每层中间靠近电梯厅设有视听间，其中五层特别设立外文图书专区与深度自习区"},
                "steps.5": {"src": about_id, "quote": "六层除库本阅览区与古籍文库外，另设有深度阅读区以及深度服务于学校交叉学科发展战略的“区域国别学学科馆”"},
                "steps.6": {"src": about_id, "quote": "二层至四层东南侧靠窗区域设有各类研讨间"},
                "steps.7": {"src": about_id, "quote": "2024年9月25日，中传学者文库揭牌投入使用。"},
                "steps.8": {"src": about_id, "quote": "2025年11月5日，区域国别学学科馆揭牌投入使用。"},
            },
            source=about_src,
        ),
        base_item(
            "lib-quyuguobie",
            "区域国别学学科馆（六层）",
            [
                "区域国别学学科馆", "区域国别学馆", "国别学学科馆",
                "区域国别学学科馆在哪", "区域国别学学科馆是什么",
                "区域国别学学科馆什么时候开放", "区域国别学学科馆有什么",
            ],
            ["区域国别学", "国别学"],
            [
                {"when": "启用", "what": "2025年11月5日，区域国别学学科馆揭牌投入使用。", "where": "六层"},
                {"when": "资源范围", "what": "区域国别学学科馆作为图书馆学科服务体系的深化与延伸，系统整合了国际政治、国际关系、国际传播、国别媒体研究、跨文化交流等领域的学术资源"},
                {"when": "平台定位", "what": "旨在构建一个集专题文献保障、学术研究支持、国际学术交流于一体的高水平知识平台。"},
                {"when": "设立意义", "what": "它的设立是图书馆主动对接国家战略、支撑学校“双一流”学科建设的重要举措。"},
            ],
            {
                "steps.0": {"src": about_id, "quote": "2025年11月5日，区域国别学学科馆揭牌投入使用。"},
                "steps.1": {"src": about_id, "quote": "区域国别学学科馆作为图书馆学科服务体系的深化与延伸，系统整合了国际政治、国际关系、国际传播、国别媒体研究、跨文化交流等领域的学术资源"},
                "steps.2": {"src": about_id, "quote": "旨在构建一个集专题文献保障、学术研究支持、国际学术交流于一体的高水平知识平台。"},
                "steps.3": {"src": about_id, "quote": "它的设立是图书馆主动对接国家战略、支撑学校“双一流”学科建设的重要举措。"},
                "location": {"src": about_id, "quote": "六层除库本阅览区与古籍文库外，另设有深度阅读区以及深度服务于学校交叉学科发展战略的“区域国别学学科馆”"},
            },
            source=about_src,
            location="六层",
        ),
        base_item(
            "lib-daping-yuelan",
            "大屏阅览区（五层滚梯旁，座位 5579-5618）",
            [
                "大屏阅览区", "视频创作大屏阅览区", "大屏阅览区在哪",
                "大屏阅览区怎么预约", "大屏阅览区座位", "图书馆大屏",
                "图书馆大屏阅览区", "大屏阅览区使用规则",
            ],
            ["大屏阅览区", "大屏"],
            [
                {"when": "位置", "what": "大屏阅览区设置在图书馆五层滚梯旁、邻近中央天井的区域。", "where": "五层滚梯旁"},
                {"when": "建成投用", "what": "2026年10月27日，教育资源中心（图书馆）在五层阅览区建成大屏阅览区，20台专业大屏幕显示器全部就位，正式投入使用。", "where": "五层阅览区"},
                {"when": "设备", "what": "每台显示器均为34英寸21:9超宽带鱼屏，1500R曲面环抱视野，分辨率达WQHD（3440×1440）。"},
                {"when": "预约", "what": "请预约使用，座位号为5579~5618，预约方法与其他座位相同。", "where": "五层"},
                {"when": "静音要求", "what": "请使用静音键盘，避免相互影响。"},
            ],
            {
                "steps.0": {"src": news_id, "quote": "大屏阅览区设置在图书馆五层滚梯旁、邻近中央天井的区域。"},
                "steps.1": {"src": news_id, "quote": "2026年10月27日，教育资源中心（图书馆）在五层阅览区建成大屏阅览区，20台专业大屏幕显示器全部就位，正式投入使用。"},
                "steps.2": {"src": news_id, "quote": "每台显示器均为34英寸21:9超宽带鱼屏，1500R曲面环抱视野，分辨率达WQHD（3440×1440）。"},
                "steps.3": {"src": news_id, "quote": "请预约使用，座位号为5579~5618，预约方法与其他座位相同。"},
                "steps.4": {"src": news_id, "quote": "请使用静音键盘，避免相互影响。"},
                "location": {"src": news_id, "quote": "大屏阅览区设置在图书馆五层滚梯旁、邻近中央天井的区域。"},
                "pitfalls.0": {"src": news_id, "quote": "大屏阅览区资源有限，仅供师生视频剪辑、创作、写论文、编程等专业用途，请勿用于玩游戏、看小视频等娱乐用途。"},
            },
            source=news_src,
            location="五层滚梯旁、邻近中央天井",
            pitfalls=["大屏阅览区资源有限，仅供师生视频剪辑、创作、写论文、编程等专业用途，请勿用于玩游戏、看小视频等娱乐用途。"],
        ),
        base_item(
            "lib-guimo",
            "图书馆规模与馆藏（2025年11月—2025年底）",
            [
                "图书馆有多少座位", "图书馆座位数", "图书馆有多少研讨间",
                "图书馆有几个静音舱", "图书馆馆藏多少", "图书馆有多少书",
                "图书馆规模", "图书馆藏书量", "图书馆有多少数据库", "图书馆有多少视听间",
            ],
            ["馆藏规模", "座位数", "藏书量"],
            [
                {"when": "阅览空间", "what": "截至2025年11月，图书馆共拥有各类阅览座位4200余个，并配备了20间研讨间、3间视听间、16个静音舱、20个蛋形椅、休闲沙发等多种阅览空间"},
                {"when": "纸质馆藏", "what": "截至2025年底，累计拥有纸本图书190多万册（包含8万册外文原版图书及4.3万册古籍），累计订购纸质报刊2000余种"},
                {"when": "数字资源", "what": "开通中外文数据库40余个，涵盖电子期刊5万余种、电子图书700余万册、中外文学位论文1000余万篇，音像资料3万余件。"},
            ],
            {
                "steps.0": {"src": about_id, "quote": "截至2025年11月，图书馆共拥有各类阅览座位4200余个，并配备了20间研讨间、3间视听间、16个静音舱、20个蛋形椅、休闲沙发等多种阅览空间"},
                "steps.1": {"src": about_id, "quote": "截至2025年底，累计拥有纸本图书190多万册（包含8万册外文原版图书及4.3万册古籍），累计订购纸质报刊2000余种"},
                "steps.2": {"src": about_id, "quote": "开通中外文数据库40余个，涵盖电子期刊5万余种、电子图书700余万册、中外文学位论文1000余万篇，音像资料3万余件。"},
            },
            source=about_src,
        ),
    ]

    for item in new_items:
        if item["id"] in by_id:
            items[by_id[item["id"]]] = item
        else:
            items.append(item)
            by_id[item["id"]] = len(items) - 1

    # 特色阅览区总览补上「中传学者文库」「区域国别学学科馆」两处特色空间
    umbrella = next(it for it in items if it["id"] == "lib-tese-yuelan")
    umbrella["title"] = "图书馆特色阅览区与特色空间（位置与规则）"
    for a in ["图书馆特色空间", "特色空间", "图书馆有哪些特色空间", "图书馆特色阅览区有哪些"]:
        if a not in umbrella["aliases"]:
            umbrella["aliases"].append(a)
    extra_steps = [
        {"when": "中传学者文库", "what": "“中传学者文库”是图书馆的特色馆藏空间，系统收藏和展示我校学者的学术著作、手稿及研究成果", "where": "一层"},
        {"when": "区域国别学学科馆", "what": "区域国别学学科馆作为图书馆学科服务体系的深化与延伸，系统整合了国际政治、国际关系、国际传播、国别媒体研究、跨文化交流等领域的学术资源", "where": "六层"},
    ]
    umbrella["steps"] = umbrella["steps"][:9] + extra_steps
    umbrella["evidence"]["steps.9"] = {"src": about_id, "quote": "“中传学者文库”是图书馆的特色馆藏空间，系统收藏和展示我校学者的学术著作、手稿及研究成果"}
    umbrella["evidence"]["steps.10"] = {"src": about_id, "quote": "区域国别学学科馆作为图书馆学科服务体系的深化与延伸，系统整合了国际政治、国际关系、国际传播、国别媒体研究、跨文化交流等领域的学术资源"}
    umbrella.setdefault("source", []).append(about_src)

    backup = ROOT / "items.json.bak-before-libportal"
    if not backup.exists():
        shutil.copy2(items_path, backup)
    items_path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"来源 {about_id} / {news_id} 已写入 sources/extra")
    print(f"新增/更新条目 {len(new_items)} 条，特色总览现有 {len(umbrella['steps'])} 处空间")
    print(f"items.json 现有 {len(items)} 条")


if __name__ == "__main__":
    main()
