import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"
data = json.loads(P.read_text(encoding="utf-8"))
by = {i["id"]: i for i in data["items"]}

by["jiaoshi-zige"]["scope_note"] = (
    "认定对象是本校在职在岗教师，在校学生不在本条范围，"
    "学生考教师资格证以国家考试通知为准"
)
by["biye-hukou-dangan"]["scope_note"] = (
    "本条只写毕业生户口与档案的转出，在校期间的学籍档案库里没有收录"
)
by["putonghua-peixun"]["scope_note"] = (
    "本条是培训项目的立项公示，不是普通话水平测试的报名入口，"
    "测试报名以官方测试机构的通知为准"
)
by["jwc-kaoshi"]["scope_note"] = (
    "官方只提供成绩复议申请单的 PDF 下载，页面没有写办理流程、受理窗口和时限"
)
by["jwc-zixiu"]["scope_note"] = (
    "官方页面只有一句适用说明和自修申请操作手册，没有写在线操作步骤"
)
by["qa-shuangxuewei"]["scope_note"] = (
    "公开文件只写了双学士学位的授予条件和它与辅修的关系，"
    "没有全校统一的报名通知，具体项目以学院当年简章为准"
)
by["shiwu-zhaoling"]["scope_note"] = (
    "库里只收录到遗失卡查询与后勤报失招领两个入口，没有全校统一的失物招领平台说明"
)
by["lib-zixishi"]["scope_note"] = (
    "有声和延时自习室的教室号与开放时间按学期调整，"
    "这里写的是 2025—2026 春季学期安排，新学期以教育服务中心通知为准"
)

zx = by["lib-zixishi"]
zx["location"] = "立德楼（1教）与博学楼（48教）的空闲公共教室"
zx["evidence"]["location"] = {
    "src": "bd7b1d20",
    "quote": "普通自习室开放时间周一至周五8:00-22：00：立德楼（1教）全部空闲公共教室，"
             "博学楼（48教）二至八层全部空闲公共教室（207除外）；周末、节假日8:00-22:00："
             "立德楼（1教）二层、三层，博学楼（48教）五层、六层",
}

P.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok", by["jiaoshi-zige"]["scope_note"], "|", by["biye-hukou-dangan"]["scope_note"])
