"""CPU 上交叉编码器到底跑不跑得动：量「一次给模型判 32 条全文打分」的墙钟。

这一步是 #55 剩下那半的门槛。判据写在结论里，不在此处下断言：
  - 冷启动（首次调用含权重载入）看一次性代价；
  - 稳态（第二次起）看每问真实增加的时间——创空间是 CPU 容器，
    稳态若超过 2 秒就不该上生产，只留离线实验。

用法：
  ./.venv/Scripts/python.exe tools/measure_reranker.py                 # 默认模型
  ./.venv/Scripts/python.exe tools/measure_reranker.py --model BAAI/bge-reranker-base
  ./.venv/Scripts/python.exe tools/measure_reranker.py --n 14 --chars 512   # 按现行池子大小与摘要长度
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import app  # noqa: E402

QS = ["学校医保", "图书馆周末开吗", "校园卡丢了怎么补办", "游泳馆开放时间"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BAAI/bge-reranker-base")
    ap.add_argument("--n", type=int, default=32, help="一次打分的条目数")
    ap.add_argument("--chars", type=int, default=512, help="每条喂进去的正文字数")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--arch-random", action="store_true",
                    help="不下权重，用同结构随机初始化模型只量 CPU 墙钟（延迟由结构决定，与权重无关）")
    a = ap.parse_args()

    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except Exception as e:  # noqa: BLE001
        print(f"transformers 不可用：{e}\n先装：pip install --index-url https://download.pytorch.org/whl/cpu "
              "--extra-index-url https://pypi.org/simple torch transformers")
        return 2

    print(f"载入 {a.model} …")
    t0 = time.time()
    if a.arch_random:
        # 同结构、随机权重：量的就是 12 层 XLM-R base 在前向上的真实开销
        from transformers import XLMRobertaConfig, XLMRobertaForSequenceClassification
        ref = XLMRobertaConfig.from_pretrained(a.model)
        net = XLMRobertaForSequenceClassification(ref)
        net.eval()
        tok = AutoTokenizer.from_pretrained(a.model)
    else:
        tok = AutoTokenizer.from_pretrained(a.model)
        net = AutoModelForSequenceClassification.from_pretrained(a.model)
        net.eval()
    print(f"载入 {time.time() - t0:.1f}s | 线程 {__import__('torch').get_num_threads()} "
          f"| 参数 {sum(p.numel() for p in net.parameters())/1e6:.0f}M"
          f"{' | 随机权重，只量延迟' if a.arch_random else ''}")

    import torch  # noqa: F401

    ranked = app.rank(QS[0])
    pool = app.rerank_candidates(QS[0], ranked, limit=a.n)
    docs = [app._item_full_text(it, a.chars) for it, _ in pool]
    docs = [d for d in docs if d.strip()]
    print(f"实际条目 {len(docs)} 条 | 平均正文 {sum(len(d) for d in docs) // max(len(docs), 1)} 字")

    for q in QS:
        pool = app.rerank_candidates(q, app.rank(q), limit=a.n)
        docs = [app._item_full_text(it, a.chars) for it, _ in pool if (it.get("title") or "").strip()]
        for r in range(a.rounds):
            t = time.time()
            with torch.no_grad():
                f = tok([q] * len(docs), docs, padding=True, truncation=True,
                        max_length=512, return_tensors="pt")
                s = torch.softmax(net(**f).logits.view(-1), dim=-1)
            dt = time.time() - t
            top = sorted(zip(s.tolist(), [it["id"] for it, _ in pool][:len(docs)]), reverse=True)[:3]
            tag = "冷" if (q == QS[0] and r == 0) else "稳"
            print(f"[{tag}] 「{q}」 第{r + 1}轮 {dt:.2f}s / {len(docs)} 条 "
                  f"| 前三 {[(round(p, 3), i) for p, i in top]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
