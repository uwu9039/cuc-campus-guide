"""加完材料后的标准体检：一条命令跑完。

用法：
    python tools/pipeline.py            # 全量体检
    python tools/pipeline.py --fast     # 跳过 LLM 对比（省钱省时）
    python tools/pipeline.py --vector   # 先重建原文向量库再体检

步骤：
  1. check_quotes.py          每条事实能否在官方原文里找到逐字引文
  2. clean_auto_keywords.py   自动制度卡片不得抢人工条目的关键词
  3. gen_presets.py           重新生成预置问法，跑偏即失败
  4. check_counts.py          items / presets / contacts / 语料口径一致
  5. check_hot.py             重点问法回归（曾经跑偏的那批）
  6. check_transfer.py        16 个学院转专业问法（规则必须全中，向量做对照）
  7. check_major_aliases.py   2026 版专业简称 → 学院 / 计划专业逐条对上
  8. eval.py                  识别 / 拒答 / 聚焦 / 同族对照
  9. audit_routing.py         变体问法压测，输出混淆矩阵
 10. derive_sensitive.py      重新推导敏感词表（写入 sensitive.json）

关键：任何一步失败都以非零退出，不"带着问题上线"。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")


def run(name: str, args: list[str], must_pass: bool = True) -> bool:
    print(f"\n{'='*64}\n▶ {name}\n{'='*64}")
    r = subprocess.run([PY, *args], cwd=str(ROOT), capture_output=True, text=True)
    tail = (r.stdout or "").strip().splitlines()
    print("\n".join(tail[-12:]) if tail else "(无输出)")
    if r.returncode != 0:
        err = (r.stderr or "").strip().splitlines()
        if err:
            print("\n".join(err[-6:]))
        if must_pass:
            print(f"✗ {name} 未通过")
            return False
        print(f"⚠ {name} 有告警（不阻断）")
    return True


def main() -> None:
    fast = "--fast" in sys.argv
    ok = True
    ok &= run("证据校验 check_quotes", ["tools/check_quotes.py"])
    ok &= run("关键词归属 clean_auto_keywords", ["tools/clean_auto_keywords.py", "--check"])
    ok &= run("预置问法 gen_presets", ["tools/gen_presets.py"])
    manifest = ROOT / "sources" / "vector" / "manifest.json"
    if "--vector" in sys.argv or not manifest.exists():
        ok &= run("原文向量库 build_vector", ["tools/build_vector.py"])
    if not (ROOT / "transfer-plans.json").exists():
        ok &= run("学院接收计划 build_transfer_plans", ["tools/build_transfer_plans.py"])
    if not (ROOT / "major-aliases.json").exists():
        ok &= run("专业简称 import_major_aliases", ["tools/import_major_aliases.py"])
    ok &= run("口径核对 check_counts", ["tools/check_counts.py"])
    ok &= run("重点问法 check_hot", ["tools/check_hot.py"])
    ok &= run("学院转专业 check_transfer", ["tools/check_transfer.py"])
    ok &= run("专业简称 check_major_aliases", ["tools/check_major_aliases.py"])
    ok &= run("评测 eval", ["eval.py"])
    ok &= run("路由审计 audit_routing", ["tools/audit_routing.py", "--top", "8"])
    ok &= run("敏感词推导 derive_sensitive", ["tools/derive_sensitive.py"])
    if not fast:
        run("LLM 兜底对比", ["tools/audit_llm.py", "--limit", "6"], must_pass=False)

    print("\n" + "=" * 64)
    print("✓ 全部通过，可以交付" if ok else "✗ 有检查未通过，先修再交付")
    print("=" * 64)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
