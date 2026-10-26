"""加完材料后的标准体检：一条命令跑完四步。

用法：
    python tools/pipeline.py            # 全量体检
    python tools/pipeline.py --fast     # 跳过 LLM 对比（省钱省时）

步骤：
  1. check_quotes.py    每条事实能否在官方原文里找到逐字引文
  2. eval.py            识别 / 拒答 / 聚焦 / 同族对照
  3. audit_routing.py   变体问法压测，输出混淆矩阵
  4. derive_sensitive.py 重新推导敏感词表（写入 sensitive.json）

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
