"""最小连通性探针：只调一次 ds_chat，确认 Key 与网络可用。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

t0 = time.time()
out = app.ds_chat([{"role": "user", "content": "只回一个字：好"}], max_tokens=20, json_mode=False)
print("elapsed", round(time.time() - t0, 2), "->", out[:80])
