"""补一条「学生创作成果管理与服务平台」条目。

依据：
- 平台操作手册（学生）2024-04-12，https://cz.cuc.edu.cn/help/20240412.pdf（已下载 _cz_manual.pdf）
- 【融合门户】服务_本科生院_有链接.docx（fileId 25bc194d…）里的服务条目与入口链接
  入口：https://cz.cuc.edu.cn/teacher/choice
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"

ITEMS = [
    {
        "id": "cz-czjg-platform",
        "title": "学生创作成果管理与服务平台（创作成果平台）",
        "aliases": [
            "学生创作成果管理与服务平台", "创作成果平台", "创作成果管理与服务平台",
            "cz平台", "cz.cuc.edu.cn", "作品征集平台", "创作成果提交", "场景报名",
        ],
        "keywords": ["创作成果", "平台", "场景", "报名", "提交", "成绩", "作品", "征集"],
        "dept": "本科生院（技术支持：招生处）",
        "channel": ["线上系统"],
        "audience": ["本科生", "教师"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": [
            {"when": "进入",
             "what": "从融合门户「学生创作成果管理与服务平台」进入，或直接打开入口页；未注册先点登录框的注册按钮，按身份选证件类型、填证件号与基本信息（标红星为必填）",
             "where": "https://cz.cuc.edu.cn/teacher/choice"},
            {"when": "登录",
             "what": "用账号密码登录；忘记密码在登录页点「忘记密码」，通过邮箱找回",
             "where": "https://cz.cuc.edu.cn/teacher/choice"},
            {"when": "报名",
             "what": "首页或页面最底部「查看更多」浏览全部场景，选场景点「立即参与」，选模块填写信息后提交；报名页改不了的个人基本信息去「个人中心」改",
             "where": "平台内 首页 / 我的场景"},
            {"when": "查成绩",
             "what": "在「我的场景」看已参与的场景与模块；成绩公布时间内，在已参与场景页面对应模块查看成绩",
             "where": "平台内 我的场景"},
        ],
        "fee": None,
        "location": "线上（融合门户入口 https://cz.cuc.edu.cn/teacher/choice）",
        "hours": "技术支持（QQ 3807211672）工作日 9:00-11:30、13:00-18:30",
        "duration": None,
        "window": None,
        "pitfalls": [
            "每个模块只允许提交一次，提交后不能再修改；保存可以多次，保存后仍可继续编辑。",
            "上传文件不要手动改后缀（如把 .mp4 改成 .mov），否则可能无法正常显示。",
            "姓名、证件号码等基本信息注册后不支持修改，填错要联系技术支持 QQ 3807211672 处理。",
            "建议 Win10 及以上系统 + 火狐或 Chrome，否则视频等文件可能预览异常。",
            "平台根地址现在显示「功能停用」（招生处作品征集的旧入口），学生走 /teacher/choice 或融合门户入口。",
        ],
        "slots": [],
        "draft": None,
        "kind": "service",
        "source": [
            {"title": "学生创作成果管理与服务平台操作手册（学生）",
             "url": "https://cz.cuc.edu.cn/help/20240412.pdf", "checked": "2026-11-11"},
            {"title": "【融合门户】服务_本科生院_有链接（学生创作成果管理与服务平台条目）",
             "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=25bc194de6b34103840f5d6bb405d8b2",
             "checked": "2026-11-11"},
        ],
        "advisory": [
            "平台内的场景清单、模块要求、成绩只在登录后可见；本条目只覆盖操作手册与入口。",
            "平台相关疑问先看操作手册，再联系技术支持 QQ 3807211672（工作日 9:00-11:30、13:00-18:30）。",
        ],
    },
]


def main() -> None:
    d = json.loads(P.read_text(encoding="utf-8"))
    have = {i["id"] for i in d["items"]}
    add = [i for i in ITEMS if i["id"] not in have]
    if not add:
        print("已存在，跳过")
        return
    bak = P.with_suffix(".json.bak-czplatform")
    if not bak.exists():
        shutil.copy2(P, bak)
        print("备份", bak.name, bak.stat().st_size, "字节")
    d["items"].extend(add)
    d["updated"] = datetime.now().strftime("%Y-%m-%d")
    tmp = P.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(P)
    print("新增", len(add), "条；总条目", len(d["items"]))


if __name__ == "__main__":
    main()
