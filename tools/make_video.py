"""生成演示视频：真实界面截图 + 中文 TTS 旁白 + ffmpeg 推镜合成。

用法：
    python tools/make_video.py --scenes 2,3 --out dist/demo-sample.mp4   # 只做指定幕
    python tools/make_video.py                                          # 全片

依赖：本机 Edge（截图）、Windows System.Speech（TTS）、imageio-ffmpeg（ffmpeg）
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "dist" / "video"
W, H, FPS = 1920, 1080, 30
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://127.0.0.1:8000"

scenes = [
    {"id": 1, "kind": "card", "title": "校园办事", "sub": "说得清，带得对",
     "narration": "办一件事，你通常要跑三趟、问四个人。第一趟问去哪，第二趟带错材料，第三趟才办成。这个作品想解决的，就是这三趟。", "sec": 9},
    {"id": 2, "kind": "shot", "q": "成绩单密封章几点能办", "head": "只答被问的那一面", "line": "先翻译成「成绩单办理 · 办理时间」，再给答案和原文",
     "narration": "比如这个问题。它不会把整张流程表倒给你，而是先把你的话翻译成一句话：成绩单办理，办理时间。然后只回答这一面。", "sec": 10},
    {"id": 3, "kind": "shot", "q": "选课什么时候截止", "head": "该问的它先问你", "line": "时限取决于这门课第几周开课，所以先追问再回答",
     "narration": "有的问题不能直接答。你问选课什么时候截止，它会先反问：这门课是第几周开始上的。因为非首周开课才有单独的退课通道，时限完全不同。", "sec": 11},
    {"id": 4, "kind": "shot", "q": "2019届毕业生能自助打成绩单吗", "head": "两个官方说法并列", "line": "官网说到二十届以后，校友会说零七到一九届也行，各自标来源",
     "narration": "这里还能看到两个官方说法并列。官网写的是二十届以后，校友会的公众号说零七到一九届也已支持线上办理。两条都标了来源和日期，不替你做取舍。", "sec": 12},
    {"id": 5, "kind": "card", "title": "它不会编", "sub": "答不上来就说答不上来",
     "narration": "更重要的是，它不会编。库里没有的，它直接说没有，并告诉你该去哪个部门问。六百二十七个事实字段，每一条都能点开看官方原文。", "sec": 11},
]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def edge_shot(url: str, out: Path, size: str = f"{W},{H}", budget: int = 9000) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    prof = str(Path(os.environ.get("TEMP", ".")) / f"edge-vid-{abs(hash(url)) % 9999}")
    run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--window-size={size}", "--force-device-scale-factor=1",
         f"--virtual-time-budget={budget}", f"--user-data-dir={prof}",
         f"--screenshot={out}", url], timeout=90)


def card_html(s: dict) -> Path:
    p = WORK / f"card-{s['id']}.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    html,body{{margin:0;height:100%;background:#15130f;color:#f6f2e9;
      font-family:"Microsoft YaHei","PingFang SC",sans-serif}}
    .wrap{{height:100%;display:flex;flex-direction:column;justify-content:center;
      padding:0 150px;position:relative;
      background:radial-gradient(1200px 700px at 22% 30%, #221f19 0%, #15130f 62%)}}
    .k{{font-size:19px;letter-spacing:.34em;color:#9a8f7b;font-weight:700}}
    h1{{font-size:132px;line-height:1.05;margin:30px 0 22px;letter-spacing:-.03em;font-weight:800}}
    .s{{font-size:52px;color:#e0483a;font-weight:700}}
    .rule{{position:absolute;left:150px;bottom:190px;width:120px;height:6px;background:#e0483a}}
    .foot{{position:absolute;left:150px;bottom:120px;font-size:19px;color:#8d8371;letter-spacing:.14em}}
    </style></head><body><div class="wrap">
      <div class="k">CAMPUS CONCIERGE · 2026 智能体节</div>
      <h1>{s['title']}</h1><div class="s">{s['sub']}</div>
      <div class="rule"></div><div class="foot">中国传媒大学 · 校园办事向导</div>
    </div></body></html>""", encoding="utf-8")
    return p


def compose_shot(s: dict, shot_png: Path) -> Path:
    """左文右屏：把界面截图放进 1920×1080 的版式里，比裸截图上镜。"""
    out_html = WORK / f"frame-{s['id']}.html"
    img_uri = shot_png.as_posix()
    out_html.write_text(f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    html,body{{margin:0;height:100%;background:#15130f;color:#f6f2e9;
      font-family:"Microsoft YaHei","PingFang SC",sans-serif;overflow:hidden}}
    .grid{{height:100%;display:grid;grid-template-columns:38% 62%;align-items:center;
      background:radial-gradient(1300px 760px at 18% 34%, #221f19 0%, #15130f 64%)}}
    .left{{padding:0 26px 0 120px}}
    .k{{font-size:16px;letter-spacing:.3em;color:#94896f;font-weight:700}}
    h2{{font-size:60px;line-height:1.2;margin:24px 0 20px;font-weight:800;letter-spacing:-.02em}}
    .line{{font-size:26px;line-height:1.65;color:#bdb5a4}}
    .rule{{width:110px;height:6px;background:#e0483a;margin-top:34px}}
    .right{{display:flex;align-items:center;justify-content:flex-start;padding-right:60px}}
    .shot{{width:100%;height:760px;object-fit:cover;object-position:top center;
      border-radius:6px;border:1px solid #3a352c;
      box-shadow:0 40px 90px -30px rgba(0,0,0,.85), 0 0 0 10px rgba(255,255,255,.02)}}
    </style></head><body><div class="grid">
      <div class="left"><div class="k">CAMPUS CONCIERGE</div>
        <h2>{s.get('head','')}</h2><div class="line">{s.get('line','')}</div><div class="rule"></div></div>
      <div class="right"><img class="shot" src="file:///{img_uri}"></div>
    </div></body></html>""", encoding="utf-8")
    frame = WORK / f"scene-{s['id']}.png"
    edge_shot(f"file:///{out_html.as_posix()}", frame, budget=3000)
    return frame


def tts(text: str, out: Path) -> float:
    """用 Windows 中文语音合成，返回音频时长（秒）。"""
    out.parent.mkdir(parents=True, exist_ok=True)
    txt = out.with_suffix(".txt")
    txt.write_text(text, encoding="utf-8")
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.SelectVoice('Microsoft Huihui Desktop'); $s.Rate = 0; "
        f"$s.SetOutputToWaveFile('{out}'); "
        f"$s.Speak([IO.File]::ReadAllText('{txt}', [Text.Encoding]::UTF8)); $s.Dispose()"
    )
    r = run(["powershell", "-NoProfile", "-Command", ps], timeout=120)
    if not out.exists():
        raise SystemExit(f"TTS 失败: {r.stderr[:200]}")
    ff = ffmpeg()
    probe = run([ff, "-i", str(out)], timeout=30)
    for line in (probe.stderr or "").splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, sec = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(sec)
    return 8.0


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def scene_video(idx: int, img: Path, audio: Path | None, dur: float, out: Path) -> None:
    ff = ffmpeg()
    frames = int(dur * FPS)
    vf = (f"scale={W * 2}:{H * 2},"
          f"zoompan=z='min(zoom+0.0005,1.06)':d={frames}"
          f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H},format=yuv420p")
    cmd = [ff, "-y", "-loop", "1", "-t", f"{dur:.2f}", "-i", str(img)]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "20"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "160k", "-shortest"]
    cmd += [str(out)]
    r = run(cmd, timeout=300)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：{r.stderr[-400:]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default="")
    ap.add_argument("--out", default=str(ROOT / "dist" / "demo.mp4"))
    args = ap.parse_args()
    only = {int(x) for x in args.scenes.split(",") if x.strip()} if args.scenes else None
    picked = [s for s in scenes if only is None or s["id"] in only]

    WORK.mkdir(parents=True, exist_ok=True)
    segs: list[Path] = []
    for s in picked:
        print(f"[幕 {s['id']}] 准备素材")
        if s["kind"] == "card":
            html = card_html(s)
            img = WORK / f"scene-{s['id']}.png"
            edge_shot(f"file:///{html.as_posix()}", img, budget=3000)
        else:
            raw = WORK / f"raw-{s['id']}.png"
            edge_shot(f"{BASE}/?q={urllib.parse.quote(s['q'])}", raw, size="1280,1200")
            img = compose_shot(s, raw)
        audio = WORK / f"scene-{s['id']}.wav"
        dur = tts(s["narration"], audio)
        dur = max(dur + 0.8, s["sec"])            # 留一点呼吸
        seg = WORK / f"scene-{s['id']}.mp4"
        print(f"[幕 {s['id']}] 合成 {dur:.1f}s")
        scene_video(s["id"], img, audio, dur, seg)
        segs.append(seg)

    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in segs), encoding="utf-8")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    r = run([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-c", "copy", str(out)], timeout=300)
    if r.returncode != 0:
        raise SystemExit(f"拼接失败：{r.stderr[-400:]}")
    print(f"完成：{out}  {out.stat().st_size/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
