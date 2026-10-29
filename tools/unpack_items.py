"""把发布用的 items.json.gz 还原成 items.json。

仓库里大文件以 gz 发布（明文 31MB，GitHub 大请求体传不上去）；app.py 两种都认，
但部分开发脚本只读明文，跑它们之前执行一次本脚本即可。
用法：python tools/unpack_items.py
"""
from __future__ import annotations

import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    plain = ROOT / "items.json"
    gz = ROOT / "items.json.gz"
    if plain.exists():
        print("items.json 已存在，跳过")
        return
    plain.write_bytes(gzip.decompress(gz.read_bytes()))
    print(f"已还原 items.json（{plain.stat().st_size / 1048576:.1f} MB）")


if __name__ == "__main__":
    main()
