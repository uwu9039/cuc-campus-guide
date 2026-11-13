"""打本地部署（127.0.0.1:8000）：health + 非流式 + 流式各一发。"""
from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8000"
Q = "挂科了还能保研吗？补考通过算吗？"


def post(payload: dict, stream: bool = False):
    req = urllib.request.Request(
        BASE + "/api/ask", data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "text/event-stream" if stream else "application/json"})
    if not stream:
        with urllib.request.urlopen(req, timeout=240) as r:
            return json.loads(r.read())
    events = []
    with urllib.request.urlopen(req, timeout=240) as r:
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if line.startswith("data: "):
                events.append(line[6:])
    return events


def main() -> None:
    with urllib.request.urlopen(BASE + "/api/health", timeout=10) as r:
        h = json.loads(r.read())
    print("health:", h["ok"], "items", h["items"], "key", h["key_configured"])

    d = post({"text": Q, "synth": True})
    mr = d.get("model_route") or {}
    print("非流式:", "gate", mr.get("gate"), "| synth", bool(d.get("synth")),
          "| item", (d.get("item") or {}).get("id"), "| fallback", mr.get("synth_fallback"),
          "| conf", d.get("confidence"), d.get("confidence_note"))
    print("  结论:", ((d.get("synth") or {}).get("conclusion") or "")[:90])

    evs = post({"text": Q, "synth": True}, stream=True)
    print("流式帧数:", len(evs))
    if evs:
        done = json.loads(evs[-1])
        mr = done.get("model_route") or {}
        print("  末帧:", "synth", bool(done.get("synth")), "| item", (done.get("item") or {}).get("id"),
              "| fallback", mr.get("synth_fallback"))
        steps = []
        for e in evs[:-1]:
            try:
                steps.append(json.loads(e).get("label") or json.loads(e).get("id"))
            except Exception:  # noqa: BLE001
                pass
        print("  步骤:", steps[:8])


if __name__ == "__main__":
    main()
