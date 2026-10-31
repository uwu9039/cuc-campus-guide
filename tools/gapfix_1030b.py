"""修正 1030 批次里的两处引文断页问题（PDF 页码插在句子中间）。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S_714 = "loc-2026级本科生入学须知-校本部-2cdd30"
Q_WEIXIN = "关注“中国传媒大学信息门户”微信服务号→"
Q_WEIXIN2 = (
    "点击菜单栏“服务入口”→选择“校园卡”选项→完成统一身份认证，"
    "跳转至一卡通页面后系统将自动完成绑定。"
)
Q_YUANSHENG = (
    "4.开通校园卡微信原生码消费权限后，微信付款码可直接支付，"
    "无需预充值并同样享受基础伙食补助。"
)


def main() -> None:
    path = ROOT / "items.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    by = {it["id"]: it for it in data["items"]}

    jiaofei = by["xinsheng-jiaofei"]
    jiaofei["evidence"]["steps.10"] = {
        "sources": [
            {"src": S_714, "quote": Q_WEIXIN},
            {"src": S_714, "quote": Q_WEIXIN2},
        ]
    }

    xiaoyuanka = by["xinsheng-xiaoyuanka"]
    xiaoyuanka["evidence"]["steps.3"] = {
        "sources": [
            {"src": S_714, "quote": Q_YUANSHENG},
            {"src": S_714, "quote": Q_WEIXIN},
            {"src": S_714, "quote": Q_WEIXIN2},
        ]
    }

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("fixed", len(data["items"]))


if __name__ == "__main__":
    main()