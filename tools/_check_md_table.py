from pathlib import Path

bad = 0
rows = 0
for i, line in enumerate(Path("24-金标准12题题库-20261113.md").read_text(encoding="utf-8").splitlines(), 1):
    s = line.strip()
    if not s.startswith("|") or s.startswith("|---"):
        continue
    rows += 1
    cols = [c for c in s.strip("|").split(" | ")]
    if len(cols) != 6:
        bad += 1
        print("BAD", i, len(cols), s[:70])
print(f"checked {rows} rows, bad={bad}")
