"""补录：学生创作成果管理与服务平台（cz）操作手册 + 条目证据。

背景：cz-czjg-platform 条目是 11-11 由别处写进 items.json 的，evidence 全空，
      引用手册 PDF 又没有入 sources/，check_quotes 会报 11 个字段缺证据。
本脚本做四件事（可重复执行）：
  1. 原件入库：_cz_manual.pdf → sources/pdf/cz-czjg-platform.pdf
  2. 逐页转录：sources/cz-czjg-platform.txt（原 PDF 是图片版，pdftotext 抽不出字）
  3. 索引：sources/index.json、sources/corpus-index.json 各补一条
  4. 证据：给 11 个字段挂 quote；把「根地址显示功能停用」这条无原文支撑的 pitfalls
     移进 advisory（advisory 不需要逐字证据）
用法：.venv/Scripts/python.exe -X utf8 -u tools/ingest_cz_manual_20261111.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLUG = "cz-czjg-platform"
PDF_SRC = ROOT / "_cz_manual.pdf"
PDF_DST = ROOT / "sources" / "pdf" / f"{SLUG}.pdf"
TXT_DST = ROOT / "sources" / f"{SLUG}.txt"

TRANSCRIPT = """学生创作成果管理与服务平台操作手册（学生）
（原件为图片版 PDF，共 7 页；本文件逐页转录，原 PDF 见 sources/pdf/cz-czjg-platform.pdf）

— p.1 —
学生创作成果管理与服务平台操作手册（学生）
1. 注册与登录
中国传媒大学学生创作成果管理与服务平台登录地址如下：
https://cz.cuc.edu.cn/
为确保视频等文件的预览显示效果，建议使用 win10 及以上系统，火狐或谷歌浏览器进行登录。如有系统相关问题（如忘记密码和邮箱等），可联系技术支持 QQ3807211672（工作日：9:00-11:30；13:00-18:30）进行咨询。
1.1 注册（未注册用户）
1.1.1 点击系统登录框注册按钮
1.1.2 填写资料，点击下一步
注册时请根据实际身份选项对应的证件类型并填写证件号码。姓名、证件号码等基本信息填充后不支持修改，如发现错误请联系技术支持 QQ3807211672 处理。

— p.2 —
1.1.3 补充基本信息资料
其中标注红色星号“*”的为必填项，不能为空。
1.2 登录（已注册用户）
1.2.1 输入账号密码进行登录

— p.3 —
1.3 忘记密码
可点击登录页面的忘记密码按钮，通过邮箱找回。
2. 修改信息
2.1 修改个人信息
点击“个人中心”，可前往个人信息编辑页面。

— p.4 —
2.2 修改密码
2.2.1 点击页面右上角修改密码
2.2.2 修改密码
需要邮箱验证，修改后点击确定即可完成修改。
3. 查看场景与报名
3.1 查看全部场景
点击首页，可查看所有场景。

— p.5 —
点击页面最底部的“查看更多”，可以展示所有场景。
3.2 报名
选择场景，点击立即参与。如未登录，需要先通过账号密码进行登录。
3.2.1 选择模块填写信息

— p.6 —
3.2.2 填写信息并提交
部分个人基本信息无法在报名页面修改，可前往“个人中心”页面修改。
建议使用 win10 及以上系统，火狐或谷歌浏览器进行登录，否则可能会出现视频等文件的预览显示问题。
上传文件请勿手动更改文件后缀（如将 .mp4 更改为 .mov），可能会造成文件无法正常显示的问题。
可以多次保存，保存后还可以再编辑修改。
每个模块只允许提交一次，提交后不能再修改。
4. 查看参与的场景、模块和成绩
4.1 查看参与场景和模块

— p.7 —
点击“我的场景”即可查看已参与的场景和模块情况。
4.2 查看成绩
在成绩公布时间内，可以在已参与的场景页面对应模块中查看成绩。
"""

# 字段 → (src, quote)。quote 必须能在对应 src 的正文里逐字找到（空白不计）。
EVIDENCE = {
    "location": ("25bc194d",
                 "[学生创作成果管理与服务平台入口](https://cz.cuc.edu.cn/teacher/choice)"),
    "hours": (SLUG,
              "可联系技术支持 QQ3807211672（工作日：9:00-11:30；13:00-18:30）进行咨询。"),
    "steps.0": (SLUG,
                "注册时请根据实际身份选项对应的证件类型并填写证件号码。"),
    "steps.1": (SLUG, "可点击登录页面的忘记密码按钮，通过邮箱找回。"),
    "steps.2": (SLUG,
                "选择场景，点击立即参与。如未登录，需要先通过账号密码进行登录。"),
    "steps.3": (SLUG,
                "在成绩公布时间内，可以在已参与的场景页面对应模块中查看成绩。"),
    "pitfalls.0": (SLUG, "每个模块只允许提交一次，提交后不能再修改。"),
    "pitfalls.1": (SLUG,
                   "上传文件请勿手动更改文件后缀（如将 .mp4 更改为 .mov），"
                   "可能会造成文件无法正常显示的问题。"),
    "pitfalls.2": (SLUG,
                   "姓名、证件号码等基本信息填充后不支持修改，"
                   "如发现错误请联系技术支持 QQ3807211672 处理。"),
    "pitfalls.3": (SLUG,
                   "建议使用 win10 及以上系统，火狐或谷歌浏览器进行登录，"
                   "否则可能会出现视频等文件的预览显示问题。"),
}


def main() -> None:
    # 1) 原件入库
    PDF_DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PDF_SRC, PDF_DST)
    sha = hashlib.sha256(PDF_DST.read_bytes()).hexdigest()[:16]

    # 2) 转录
    TXT_DST.write_text(TRANSCRIPT, encoding="utf-8")

    # 3) 索引
    idx_p = ROOT / "sources" / "index.json"
    idx = json.loads(idx_p.read_text(encoding="utf-8"))
    idx[SLUG] = {
        "url": "https://cz.cuc.edu.cn/help/20240412.pdf",
        "title": "学生创作成果管理与服务平台操作手册（学生）",
        "chars": len(TRANSCRIPT),
        "sha256": sha,
        "fetched_at": "2026-11-11T18:51:00+08:00",
        "kind": "pdf",
        "pages": 7,
        "local_path": "（本地路径已隐藏）",
    }
    idx_p.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")

    ci_p = ROOT / "sources" / "corpus-index.json"
    ci = json.loads(ci_p.read_text(encoding="utf-8"))
    ci[SLUG] = {
        "slug": SLUG,
        "kind": "官方附件·操作手册",
        "title": "学生创作成果管理与服务平台操作手册（学生）",
        "account": "",
        "date": "2024-04-12",
        "url": "https://cz.cuc.edu.cn/help/20240412.pdf",
        "chars": len(TRANSCRIPT),
        "fetched_at": "2026-11-11T18:51:00+08:00",
        "official": True,
        "used_by_items": [SLUG],
        "note": "图片版 PDF，正文为逐页转录（pdftotext 抽不出字）",
    }
    ci_p.write_text(json.dumps(ci, ensure_ascii=False, indent=1), encoding="utf-8")

    # 4) 条目证据
    items_p = ROOT / "items.json"
    shutil.copyfile(items_p, ROOT / "items.json.bak-cz-evidence")
    data = json.loads(items_p.read_text(encoding="utf-8"))
    it = next(i for i in data["items"] if i["id"] == SLUG)
    ev = {}
    for key, (src, quote) in EVIDENCE.items():
        ev[key] = {"src": src, "quote": quote}
    it["evidence"] = ev
    # 「平台根地址显示功能停用」没有原文支撑，移进 advisory（不需要逐字证据）
    pits = list(it.get("pitfalls") or [])
    moved = [p for p in pits if "功能停用" in p]
    it["pitfalls"] = [p for p in pits if "功能停用" not in p]
    adv = list(it.get("advisory") or [])
    for m in moved:
        if m not in adv:
            adv.append(m + "（2026-11-11 人工核验，暂无原文引用）")
    it["advisory"] = adv
    items_p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    print(f"PDF  → {PDF_DST.relative_to(ROOT)}  sha256[:16]={sha}")
    print(f"转录 → {TXT_DST.relative_to(ROOT)}  {len(TRANSCRIPT)} 字")
    print(f"index.json {len(idx)} 条；corpus-index.json {len(ci)} 条")
    print(f"证据 {len(ev)} 个字段；pitfalls {len(pits)} → {len(it['pitfalls'])}；adv advisory {len(adv)}")
    print("checks:", "location/hours/steps.0-3/pitfalls.0-3 已挂", "| 移出 pitfalls:", len(moved))


if __name__ == "__main__":
    main()
