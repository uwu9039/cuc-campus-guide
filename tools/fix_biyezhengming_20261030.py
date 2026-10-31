import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"
data = json.loads(P.read_text(encoding="utf-8"))
by = {i["id"]: i for i in data["items"]}

it = by["doc-20240412-c6366a218572"]
it["steps"] = [
    {"when": "适用情形",
     "what": "如毕业生毕业证书、学位证书有遗失或者损坏，可以按照表格要求办理毕业证明书、学位证明书"},
    {"when": "提交材料",
     "what": "材料均需线下提交至艺术与传播大楼本科生院301"},
    {"when": "证件照",
     "what": "办理以上证明书，须将个人证件照片以姓名和身份证号命名的方式发到邮箱 xjglk@cuc.edu.cn，"
             "照片大小压缩在 30K 之内，照片要求是蓝底"},
    {"when": "委托办理",
     "what": "如不是本人办理，办理人需出具《委托书》，委托书模板可直接下载"},
    {"when": "损坏换发",
     "what": "证书原件损坏补办证明书的，办理时须交回证书原件"},
    {"when": "表格下载",
     "what": "申请表格请见附件"},
]
it["evidence"] = {
    "steps.0": {"src": "20240412-c6366a218572",
                "quote": "如毕业生毕业证书、学位证书有遗失或者损坏，可以按照表格要求办理毕业证明书、学位证明书。"},
    "steps.1": {"src": "20240412-c6366a218572",
                "quote": "材料均需线下提交至艺术与传播大楼本科生院301。"},
    "steps.2": {"src": "att-7c658c64ba",
                "quote": "3.办理以上证明书，须将个人证件照片以姓名+身份证号命名的方式发到邮箱xjglk@cuc.edu.cn，照片大小压缩在30K之内，照片要求是蓝底。"},
    "steps.3": {"src": "att-7c658c64ba",
                "quote": "4.如不是本人办理，办理人需出具《委托书》，委托书模板可直接下载。"},
    "steps.4": {"src": "att-7c658c64ba",
                "quote": "2.证书原件损坏补办证明书的，办理时须交回证书原件。"},
    "steps.5": {"src": "20240412-c6366a218572", "quote": "申请表格请见附件。"},
    "location": {"src": "20240412-c6366a218572",
                 "quote": "材料均需线下提交至艺术与传播大楼本科生院301。"},
}
it["location"] = "艺术与传播大楼本科生院301"

P.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("steps", len(it["steps"]), "evidence", len(it["evidence"]))
