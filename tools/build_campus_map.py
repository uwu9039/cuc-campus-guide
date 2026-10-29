# -*- coding: utf-8 -*-
"""生成 campus-map.json（中国传媒大学校园地图 POI）。

坐标来源与处理：
- amap：高德地图网页版 POI 搜索（www.amap.com/service/poiInfo）取到的 GCJ-02 原始坐标，
  本次拿到 4 个楼宇点位（立德楼 / 博学楼 / 艺术与传播大楼 / 图书馆）。
- osm：OpenStreetMap 原生 WGS84 坐标（经 Photon 反查/检索得到 osm_type/osm_id），
  由本脚本用标准 WGS84→GCJ-02 算法转换，楼体中心而非门点。
- null：公开渠道查不到，不猜坐标，confidence 记 low。

用法：
    python tools/build_campus_map.py            # 写 campus-map.json
    python tools/build_campus_map.py --check    # 只打印统计，不写文件
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "campus-map.json"

# ---------------------------------------------------------------- 坐标转换
A = 6378245.0
EE = 0.00669342162296594323


def _tlat(x: float, y: float) -> float:
    r = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    r += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    r += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return r


def _tlng(x: float, y: float) -> float:
    r = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    r += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    r += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return r


def wgs2gcj(lat: float, lng: float) -> tuple[float, float]:
    dlat = _tlat(lng - 105.0, lat - 35.0)
    dlng = _tlng(lng - 105.0, lat - 35.0)
    rad = lat / 180.0 * math.pi
    magic = 1 - EE * math.sin(rad) ** 2
    sq = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sq) * math.pi)
    dlng = (dlng * 180.0) / (A / sq * math.cos(rad) * math.pi)
    return round(lat + dlat, 6), round(lng + dlng, 6)


def gcj2wgs(lat: float, lng: float) -> tuple[float, float]:
    """GCJ-02 → WGS84，迭代逼近（误差 < 0.5 m）。"""
    wlat, wlng = lat, lng
    for _ in range(8):
        glat, glng = wgs2gcj(wlat, wlng)
        wlat += lat - glat
        wlng += lng - glng
    return round(wlat, 6), round(wlng, 6)


# ---------------------------------------------------------------- 数据
# src: ("amap", lat, lng) 已是 GCJ-02；("osm", lat, lng) 是 WGS84；None 未查到
AMAP = "amap"
OSM = "osm"

POIS: list[dict] = [
    # ---------------- 校门
    dict(
        id="nanmen", name="南门", aliases=["南校门", "学校南门", "中国传媒大学南门"],
        category="gate", src=None, confidence="low",
        address="朝阳区定福庄东街1号（建国路北侧）",
        source="待确认：OSM/高德公开页面均未返回门体点位",
        note="官方原文：主楼位于南门正对着的高楼。据此南门在主楼正南、建国路北侧，但未取到可核实的门点位，故坐标为 null。",
    ),
    dict(
        id="beimen", name="北门", aliases=["北校门", "北门转盘"],
        category="gate", src=(OSM, 39.913849, 116.550045), confidence="medium",
        address="朝阳路南侧，校内北门转盘处",
        source="OpenStreetMap W783282804「北门转盘」",
        url="https://www.openstreetmap.org/way/783282804",
        note="取 OSM「北门转盘」点位；实际门线更靠北（近朝阳路），约偏北 50 m。",
    ),
    dict(
        id="ximen", name="西门", aliases=["西校门", "定福庄东街校门"],
        category="gate", src=None, confidence="low",
        address="定福庄东街一侧",
        source="待确认：OSM 未单独标注西门",
        note="校园西侧沿定福庄东街（3/4/7 号楼一线），但未取到门体点位。",
    ),
    # ---------------- 教学 / 办公
    dict(
        id="lidelou", name="立德楼", aliases=["1教", "一教", "1号楼", "一号教学楼", "立德楼（1号楼）"],
        category="teaching", src=(AMAP, 39.910873, 116.557034), confidence="high",
        address="定福庄东街1号 中国传媒大学（传媒大学地铁站东北口步行约420米）",
        source="高德地图 POI「中国传媒大学立德楼」B0FFKHN1MM",
        url="https://www.amap.com/place/B0FFKHN1MM",
        note="高德点位；OSM 另有「1教」楼体中心（W198238561），与本点相距约 90 m。",
    ),
    dict(
        id="boxuelou", name="博学楼", aliases=["48教", "四十八教", "48号楼", "四十八号楼"],
        category="teaching", src=(AMAP, 39.913440, 116.555315), confidence="high",
        address="定福庄东街1号 中国传媒大学",
        source="高德地图 POI「中国传媒大学博学楼」B0FFHUU1AY",
        url="https://www.amap.com/place/B0FFHUU1AY",
        note="高德点位；OSM 楼体中心 W255744677 在东偏北约 70 m。",
        facilities=[{
            "floor": 1, "toilets": {"female": 3, "male": 1},
            "note": "一层 3 女 1 男", "source": "user",
        }],
    ),
    dict(
        id="yichuan", name="艺术与传播大楼", aliases=["27号楼", "艺传大楼", "艺传", "艺术传播大楼"],
        category="teaching", src=(AMAP, 39.911941, 116.556485), confidence="high",
        address="南操场西侧，艺术展览中心北侧，阳明书院南侧（2024 年新建）",
        source="高德地图 POI「中国传媒大学艺术与传播大楼」B0K0UZXD1C",
        url="https://www.amap.com/place/B0K0UZXD1C",
        note="官方：本科生院 3 层 301、学生工作部 2 层、财务处 4 层、校园建设处 5 层均在楼内。",
        facilities=[
            {"type": "elevator", "note": "有电梯（原文「三楼出电梯左转本科生院」）", "source": "25bc194d"},
            {"type": "service_hall", "floor": 1, "note": "1 层校园生活服务大厅（进门往左）", "source": "1b97d899"},
        ],
    ),
    dict(
        id="tushuguan", name="图书馆", aliases=["大阅城", "49号楼", "中传图书馆", "图书馆大阅城"],
        category="teaching", src=(AMAP, 39.913935, 116.558324), confidence="high",
        address="49 号楼（大阅城），钢琴湖畔；副楼 1 层校史馆、2 层圆形报告厅与 4K 影厅",
        source="高德地图 POI「中国传媒大学图书馆」B000AA0V9S",
        url="https://www.amap.com/place/B000AA0V9S",
        note="高德点位；OSM 大阅城楼体 W523569201 中心在西南约 70 m。东门另有 POI「中国传媒大学图书馆(东门)」B0FFH20K1L。",
        facilities=[
            {"type": "elevator", "note": "各层有电梯；视听间位于三至五层电梯南侧", "source": "图书馆读者手册2024"},
            {"type": "toilet", "note": "每层设卫生间（垃圾桶设于每层卫生间）", "source": "图书馆读者手册2024"},
            {"type": "silent_booth", "note": "静音舱：二至五层东侧", "source": "图书馆读者手册2024"},
            {"type": "seminar_room", "note": "研讨间：二至四层南侧（304-305 为教师专用）", "source": "图书馆读者手册2024"},
        ],
    ),
    dict(
        id="benkeshengyuan", name="本科生院", aliases=["本科生院301", "艺术与传播大楼301", "教务"],
        category="office", src=(AMAP, 39.911941, 116.556485), confidence="medium",
        address="艺术与传播大楼 3 层 301、309-316",
        source="官方位置表 1b97d899；坐标取艺传大楼楼体点位",
        note="楼内房间，坐标沿用艺术与传播大楼。",
    ),
    dict(
        id="kawu", name="校园卡服务中心（卡务中心）", aliases=["卡务中心", "校园卡中心", "学生综合服务大厅", "校园生活服务大厅"],
        category="office", src=(AMAP, 39.911941, 116.556485), confidence="medium",
        address="艺术与传播大楼 1 层（进门往左）",
        source="官方位置表 1b97d899 / 信息化指南 48e1da04",
        note="官方 2024-2025 版位置为艺传大楼 1 层；任务描述中的「44 号楼卡务中心」疑为旧位置，建议现场确认。",
    ),
    dict(
        id="b30", name="30号楼（保卫处综合服务厅）", aliases=["30号楼", "30号教学楼", "保卫处", "保卫部（处）综合办事大厅"],
        category="office", src=(OSM, 39.909603, 116.552465), confidence="medium",
        address="南操场正西侧，艺传大楼正东侧（保卫部（处）在 1 层 101）",
        source="OpenStreetMap W783788116「30号教学楼」",
        url="https://www.openstreetmap.org/way/783788116",
        note="OSM 楼体中心；官方描述方位与之一致，但 OSM 另有「保卫处」楼（东侧），未采用。",
    ),
    dict(
        id="b21", name="21号楼（国际交流中心）", aliases=["21号楼", "国际交流中心", "21号楼C区", "21号楼D区"],
        category="office", src=None, confidence="low",
        address="南操场正东侧（棕色高楼）",
        source="待确认：官方方位明确，OSM 未标注该楼",
        note="官方原文：位于南操场正东边，一栋棕色高楼。OSM 该位置仅标有「东看台」，未取到楼体点位。",
    ),
    dict(
        id="b44", name="44号楼", aliases=["44号楼", "四十四号楼"],
        category="office", src=None, confidence="low",
        address="47 号楼东侧、校内菜鸟驿站（临建1）南侧",
        source="待确认：OSM 该区域仅有「学生办」「广告学院」等要素",
        note="官方位置表只给出相对关系（临建1 在 47 号楼东侧、44 号楼北侧），未取到楼体点位。",
    ),
    dict(
        id="mingdelou", name="明德楼（2号楼）", aliases=["2号楼", "二号楼", "明德楼"],
        category="teaching", src=(OSM, 39.911277, 116.550068), confidence="medium",
        address="校园中西部，中传学术中心在其正后方",
        source="OpenStreetMap W768059205「2号楼」",
        url="https://www.openstreetmap.org/way/768059205",
        note="OSM 楼体中心；楼内有 4K 演播馆（2 层）与多个机关（8-12 层）。",
    ),
    dict(
        id="zhulou", name="主楼", aliases=["学校主楼", "主楼"],
        category="landmark", src=(OSM, 39.909297, 116.550345), confidence="medium",
        address="南门正对，东西两侧为东配楼、西配楼",
        source="OpenStreetMap W772369994「学校主楼」",
        url="https://www.openstreetmap.org/way/772369994",
        note="OSM 楼体中心；招生处 3 层、戏剧影视学院灯光暗房 B1 层。",
    ),
    # ---------------- 医疗
    dict(
        id="xiaoyiyuan", name="校医院", aliases=["学校医院", "20号楼（原幼儿园）", "中传校医院"],
        category="medical", src=(OSM, 39.914185, 116.548511), confidence="high",
        address="校内 20 号楼（原幼儿园），近北苑餐厅与定福庄东街",
        source="OpenStreetMap N7321277718（amenity=hospital）+ W781983689 楼体",
        url="https://www.openstreetmap.org/node/7321277718",
        note="OSM 同时有楼体与 POI 节点，二者相距约 20 m。",
    ),
    # ---------------- 场馆
    dict(
        id="zhongchuanlitang", name="中传礼堂", aliases=["1500报", "1500人报告厅", "1500", "大报告厅", "大礼堂"],
        category="venue", src=(OSM, 39.909183, 116.555041), confidence="high",
        address="国重大楼（22 号楼）1 层",
        source="OpenStreetMap W783787656「1500人报告厅」",
        url="https://www.openstreetmap.org/way/783787656",
        note="与 400 报同处 22 号楼 1 层；OSM 以「1500人报告厅」命名该楼体。",
    ),
    dict(
        id="zhongchuanjiangtang", name="中传讲堂", aliases=["400报", "400人报告厅", "400", "小讲堂"],
        category="venue", src=(OSM, 39.909183, 116.555041), confidence="medium",
        address="国重大楼（22 号楼）1 层",
        source="官方位置表 1b97d899 + 简称表 cd72bce4；坐标取 1500 报同楼点位",
        note="与中传礼堂同楼同层，无独立点位，坐标共用。",
    ),
    dict(
        id="guozhong", name="国重大楼（22号楼）", aliases=["22号楼", "国重大楼", "国重", "国家重点实验室大楼"],
        category="landmark", src=(OSM, 39.909183, 116.555041), confidence="medium",
        address="校园东南部，1 层为中传礼堂（1500 报）与中传讲堂（400 报）",
        source="OpenStreetMap W783787656（OSM 以「1500人报告厅」命名该楼体）",
        url="https://www.openstreetmap.org/way/783787656",
        note="楼内 1-16 层为实验室与研究中心（官方位置表）；电梯需梯控授权。",
        facilities=[
            {"type": "elevator_access", "note": "电梯梯控须在融合门户申请，审批通过次日 11:00 生效", "source": "48e1da04"},
            {"type": "toilet", "note": "场馆配套含卫生间、化妆间、贵宾室", "source": "5ee0f0ae"},
        ],
    ),
    dict(
        id="xueshuzhongxin", name="中传学术中心", aliases=["学术中心"],
        category="venue", src=None, confidence="low",
        address="2 号楼（明德楼）正后方，正门朝西",
        source="待确认：仅有官方方位描述",
        note="OSM 在 2 号楼正后方有「演播厅」楼（W783788781），可能即学术中心或 4K 演播馆，未能确认，坐标留空。",
    ),
    dict(
        id="yuanxing", name="圆形报告厅", aliases=["圆形报告厅", "图书馆圆形报告厅"],
        category="venue", src=(AMAP, 39.913935, 116.558324), confidence="medium",
        address="大阅城（图书馆）副楼 2 层",
        source="图书馆读者手册 00f4cdcc；坐标取图书馆点位",
        note="读者手册：副楼一层校史馆，副楼二层为圆形报告厅和 4K 影厅。",
    ),
    dict(
        id="yanboguan", name="中传演播馆", aliases=["1400平米演播馆", "1400", "4K演播馆", "4K演播室", "4K演播厅"],
        category="venue", src=(OSM, 39.911693, 116.550088), confidence="medium",
        address="2 号楼（明德楼）2 层（官方）；OSM 点位在 2 号楼正后方",
        source="简称表 cd72bce4（中传演播馆=4K演播馆）+ 官方位置表 1b97d899；坐标取 OSM「演播厅」W783788781",
        url="https://www.openstreetmap.org/way/783788781",
        note="面积 1400㎡（公共实践场馆管理办法）。OSM「演播厅」楼紧邻 2 号楼，认定为同一组建筑，仍需现场核对。",
    ),
    dict(
        id="yinyueting", name="中传音乐厅", aliases=["音乐厅"],
        category="venue", src=None, confidence="low",
        address="待确认（209 座）",
        source="待确认：管理办法只给面积/座位，未给楼栋",
        note="《公共实践场馆管理办法》：中传音乐厅 209 座，配套三角钢琴；未查到所在楼栋。",
    ),
    dict(
        id="k4fangying", name="4K放映厅", aliases=["4K影厅", "中传放映厅", "4K放映厅"],
        category="venue", src=(AMAP, 39.913935, 116.558324), confidence="medium",
        address="大阅城（图书馆）副楼 2 层",
        source="图书馆读者手册 00f4cdcc；坐标取图书馆点位",
        note="与圆形报告厅同层；另有 84 座的「中传放映厅」列于公共实践场馆，二者是否同一处待确认。",
    ),
    dict(
        id="yizhan", name="艺术展览中心", aliases=["艺展中心", "展览中心", "原南苑餐厅"],
        category="venue", src=(OSM, 39.909588, 116.552003), confidence="medium",
        address="南操场西侧、艺传大楼南侧（原南苑餐厅）",
        source="OpenStreetMap W783788117「南苑食堂」",
        url="https://www.openstreetmap.org/way/783788117",
        note="官方：艺术展览中心（原南苑餐厅），2 层为离退休工作处、工会；OSM 仍沿用旧名「南苑食堂」。",
    ),
    # ---------------- 体育
    dict(
        id="caochang", name="操场（南操场）", aliases=["南操场", "南操", "田径场", "风雨操场", "中传体育场", "足球场"],
        category="sports", src=(OSM, 39.910347, 116.553053), confidence="high",
        address="校园南部，艺传大楼东侧、21 号楼西侧",
        source="OpenStreetMap W198238559「中传足球场」",
        url="https://www.openstreetmap.org/way/198238559",
        note="取球场多边形中心；看台在东西两侧（W 侧「操场主看台」、E 侧「东看台」）。",
    ),
    dict(
        id="youyongguan", name="游泳馆", aliases=["游泳池", "中传游泳馆", "水立方"],
        category="sports", src=(OSM, 39.912579, 116.554178), confidence="high",
        address="校园中部偏东，手球馆南侧",
        source="OpenStreetMap N5096880463（leisure=sports_centre）",
        url="https://www.openstreetmap.org/node/5096880463",
        note="北侧有地下通道通手球馆（官方）。",
        facilities=[
            {"type": "underground_passage", "note": "北侧地下通道可抵手球馆（51 号楼）", "source": "1b97d899"},
        ],
    ),
    dict(
        id="shouqiuguan", name="手球馆", aliases=["羽毛球馆", "羽毛球场", "新利体育馆", "51号楼"],
        category="sports", src=(OSM, 39.914187, 116.555449), confidence="high",
        address="51 号楼，游泳馆北侧（可走地下通道）",
        source="OpenStreetMap W523569198（leisure=sports_centre）",
        url="https://www.openstreetmap.org/way/523569198",
        note="官方：51 号楼，可通过中传游泳馆北侧地下通道抵达；羽毛球场地在此预约。",
    ),
    dict(
        id="dahuodong", name="大学生活动中心", aliases=["大活", "活动中心", "55号楼", "大学生活动中心体育馆"],
        category="sports", src=(OSM, 39.912911, 116.554587), confidence="medium",
        address="55 号楼，1 层为体育馆（篮球/排球/气排球/乒乓球）",
        source="OpenStreetMap W523220221「学生活动中心」",
        url="https://www.openstreetmap.org/way/523220221",
        note="OSM 另有一处 amenity=community_centre 的「大学生活动中心」节点（东偏南约 180 m），未采用，建议现场核对。",
        facilities=[
            {"type": "gym", "floor": 1, "note": "1 层体育馆，团体/个人预约均可", "source": "4b3b7735"},
        ],
    ),
    # ---------------- 生活
    dict(
        id="baiyangdaji", name="白杨大集", aliases=["白杨市集", "大集", "白杨大集广场"],
        category="life", src=None, confidence="medium",
        address="校内，与轮滑广场同一片绿化改造区域（具体以活动通知为准）",
        source="中国政府采购网成交公告「中国传媒大学白杨大集和轮滑广场绿化改造工程」（2024-05-22）",
        url="https://www.ccgp.gov.cn/cggg/zygg/cjgg/202405/t20240522_22169832.htm",
        note="校方 70 周年校庆通知亦提到白杨大集；公开渠道未查到独立 POI 点位，坐标为 null，未做估算。",
    ),
    dict(
        id="beiyuan", name="北苑餐厅", aliases=["北苑", "北苑食堂", "一食堂"],
        category="life", src=(OSM, 39.913443, 116.548623), confidence="high",
        address="校园西北角，近定福庄东街与校医院",
        source="OpenStreetMap W523254357",
        url="https://www.openstreetmap.org/way/523254357",
        note="OSM 楼体中心。",
    ),
    dict(
        id="yixiangyuan", name="溢香苑餐厅", aliases=["溢香园", "溢香苑", "40号楼餐厅"],
        category="life", src=(OSM, 39.912396, 116.551367), confidence="medium",
        address="40 号楼（官方位置表：溢香园位于 40 号楼）",
        source="OpenStreetMap W523569205「溢香苑餐厅」",
        url="https://www.openstreetmap.org/way/523569205",
        note="OSM 该楼体类型标为 dormitory，与「餐厅」不一致，取点位但降为 medium。",
    ),
    dict(
        id="jibenhuo", name="基本伙食堂", aliases=["基本伙", "学生基本伙", "基本伙窗口"],
        category="life", src=None, confidence="low",
        address="待确认",
        source="待确认：《中国传媒大学食堂管理办法》只区分「基本伙」与合作经营食堂",
        note="校规中「基本伙」是食堂类别而非独立楼栋；北苑餐厅、溢香苑为常见学生食堂，基本伙窗口具体在哪栋未核实。",
    ),
    dict(
        id="kuaidi", name="快递驿站（菜鸟驿站）", aliases=["菜鸟驿站", "快递", "取快递", "快递柜"],
        category="life", src=None, confidence="low",
        address="临建1（47 号楼东侧、44 号楼北侧）",
        source="待确认：官方位置表 1b97d899 只有相对位置",
        note="OSM 的「菜鸟驿站」（定福庄东街西侧）在校外，未采用；快递柜点位未查到。",
    ),
    # ---------------- 宿舍
    dict(
        id="d10", name="10号楼（宿舍）", aliases=["10号楼", "十号楼"],
        category="dorm", src=(OSM, 39.912079, 116.554103), confidence="medium",
        address="校园中部偏东，11 号楼北侧",
        source="OpenStreetMap W523569212「住宅（10号楼）」",
        url="https://www.openstreetmap.org/way/523569212",
        note="OSM 楼体中心。",
    ),
    dict(
        id="d11", name="11号楼（宿舍）", aliases=["11号楼", "十一号楼"],
        category="dorm", src=(OSM, 39.911746, 116.554195), confidence="medium",
        address="校园中部偏东，10 号楼南侧",
        source="OpenStreetMap W198238556「住宅（11号楼）」",
        url="https://www.openstreetmap.org/way/198238556",
        note="OSM 楼体中心。",
    ),
    dict(
        id="d14", name="14号楼（宿舍）", aliases=["14号楼", "十四号楼"],
        category="dorm", src=(OSM, 39.911461, 116.553543), confidence="medium",
        address="校园中部，南操场东北侧",
        source="OpenStreetMap W198239285「14号楼」",
        url="https://www.openstreetmap.org/way/198239285",
        note="OSM 楼体中心。",
    ),
    dict(
        id="d16", name="16号楼（宿舍）", aliases=["16号楼", "十六号楼"],
        category="dorm", src=(OSM, 39.911413, 116.552948), confidence="medium",
        address="校园中部，14 号楼西侧",
        source="OpenStreetMap W198239281「16号楼」",
        url="https://www.openstreetmap.org/way/198239281",
        note="OSM 楼体中心。",
    ),
]

ROUTES = [
    {
        "from": "youyongguan", "to": "shouqiuguan", "type": "underground_passage",
        "note": "手球馆可通过中传游泳馆北侧地下通道抵达", "source": "官方 1b97d899",
    },
    {
        "from": "nanmen", "to": "zhulou", "type": "walk",
        "note": "南门正对主楼，进门即主楼前广场（喷泉广场）", "source": "官方 1b97d899",
    },
]

NOTES = [
    "坐标系：lat/lng 为 GCJ-02（高德/腾讯底图可直接用）；wgs84 为 WGS84（OSM/Leaflet 用）。",
    "wgs84_derived=true 表示由 GCJ-02 用标准算法反算，非原始观测；OSM 来源的 wgs84 是原生坐标，lat/lng 才是换算值。",
    "高德点位与 OSM 楼体中心存在 50–150 m 差异（POI 点 vs 楼体中心），同一点位请优先用 confidence 高者。",
    "南门、西门、21号楼、44号楼、中传学术中心、中传音乐厅、基本伙食堂、快递驿站、白杨大集未能取到可核实坐标，lat/lng 为 null，未做估算。",
    "2026-10-29 采集：高德网页版 poiInfo 接口在连续请求后触发滑块验证，仅完成 4 个楼宇查询；未使用任何 API Key / 付费接口。",
    "建议现场核对：21/44 号楼位置、中传音乐厅所在楼栋、演播馆与学术中心、快递驿站与快递柜。",
]


def build() -> dict:
    pois = []
    lats, lngs = [], []
    for p in POIS:
        src = p.get("src")
        if src:
            kind, la, ln = src
            if kind == AMAP:
                lat, lng = round(la, 6), round(ln, 6)
                wlat, wlng = gcj2wgs(lat, lng)
                derived = True
            else:
                wlat, wlng = round(la, 6), round(ln, 6)
                lat, lng = wgs2gcj(wlat, wlng)
                derived = False
            lats.append(lat)
            lngs.append(lng)
        else:
            lat = lng = wlat = wlng = None
            derived = None

        poi = {
            "id": p["id"],
            "name": p["name"],
            "aliases": p["aliases"],
            "category": p["category"],
            "lat": lat,
            "lng": lng,
            "wgs84": {"lat": wlat, "lng": wlng} if wlat is not None else None,
            "wgs84_derived": derived,
            "address": p["address"],
            "source": p["source"],
            "confidence": p["confidence"],
            "note": p["note"],
        }
        if p.get("url"):
            poi["source_url"] = p["url"]
        if p.get("facilities"):
            poi["facilities"] = p["facilities"]
        pois.append(poi)

    center = {
        "lat": round(sum(lats) / len(lats), 6),
        "lng": round(sum(lngs) / len(lngs), 6),
        "crs": "GCJ-02",
        "note": "取全部有坐标 POI 的算术平均，非校区多边形重心",
    }
    return {
        "updated": "2026-10-29",
        "center": center,
        "amap_key_env": "AMAP_KEY",
        "pois": pois,
        "routes": ROUTES,
        "notes": NOTES,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只打印统计，不写文件")
    args = ap.parse_args()

    data = build()
    pois = data["pois"]
    with_xy = [p for p in pois if p["lat"] is not None]
    by_conf: dict[str, int] = {}
    for p in pois:
        by_conf[p["confidence"]] = by_conf.get(p["confidence"], 0) + 1
    empty = [p["id"] for p in pois if p["lat"] is None]

    print(f"POI 总数 {len(pois)}，有坐标 {len(with_xy)}，缺坐标 {len(empty)}")
    print("confidence:", by_conf)
    print("缺坐标:", ", ".join(empty) or "-")
    print("center:", data["center"])

    if not args.check:
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("written:", OUT)


if __name__ == "__main__":
    main()
