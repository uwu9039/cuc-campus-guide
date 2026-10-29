#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
for i in $(seq 1 20); do
  out=$(.venv/Scripts/python.exe -u tools/upload_sources_raw.py --rate 0.75 --max 40 2>&1 | tail -3)
  echo "[round $i] $out"
  echo "$out" | grep -q "没有新增文件" && break
done
echo "ALL DONE"
