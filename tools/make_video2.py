"""演示片 v2：加「切换挪移」+「静止微动」。

动效设计：
  1. 每个镜头用 zoompan 做微动——推近/拉远/左右漂移轮换，1.00→1.07，肉眼可见但不晕
  2. 镜头之间用 xfade 真转场：slideleft / smoothup / wipeleft / fadeblack 轮换，让画面"挪"过去
  3. 全片叠一层极轻颗粒 + 暗角，压掉"PPT 感"
  4. 音频与画面各自拼接：画面重叠 0.45s，音频前补 0.45s 静音对齐

用法：python tools/make_video2.py --scenes 1,2,3 --out dist/demo-v2.mp4
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import make_video as base  # 复用截图/TTS/版式

WORK = ROOT / "dist" / "video2"
W, H, FPS = 1920, 1080, 30
XF = 0.45                      # 转场时长

# 微动方案轮换：(缩放起点, 缩放终点, 水平漂移 px)
MOTION = [
    (1.00, 1.07, 0),
    (1.04, 1.00, -40),
    (1.00, 1.06, 40),
    (1.06, 1.01, 0),
]
TRANS = ["slideleft", "smoothup", "wipeleft", "fadeblack"]


def ff() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def clip(idx: int, img: Path, dur: float, out: Path, motion: tuple) -> None:
    z0, z1, dx = motion
    frames = max(2, int(dur * FPS))
    # zoompan 用逐帧表达式控制缩放与位移
    zexpr = f"{z0}+({z1 - z0})*on/{frames}"
    xexpr = f"iw/2-(iw/zoom/2)+({dx})*on/{frames}"
    vf = (
        f"scale={W * 2}:{H * 2},"
        f"zoompan=z='{zexpr}':d={frames}:x='{xexpr}':y='ih/2-(ih/zoom/2)':s={W}x{H},"
        f"format=yuv420p"
    )
    # 关键：输入只给 1 帧，由 zoompan 的 d 参数扩展成 frames 帧，否则帧数会逐帧叠乘
    r = run([ff(), "-y", "-loop", "1", "-framerate", "1", "-t", "1", "-i", str(img),
             "-vf", vf, "-frames:v", str(frames), "-r", str(FPS),
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-an", str(out)])
    if r.returncode != 0:
        raise SystemExit(f"镜头 {idx} 失败：{r.stderr[-400:]}")


def build_xfade(clips: list[Path], durs: list[float], trans: list[str], total: float, out: Path) -> None:
    """把 N 个静音片段用 xfade 串起来。"""
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]
    parts, prev = [], "0:v"
    offset = durs[0] - XF
    for i in range(1, len(clips)):
        label = f"x{i}"
        parts.append(
            f"[{prev}][{i}:v]xfade=transition={trans[i % len(trans)]}:duration={XF}:offset={offset:.3f}[{label}]"
        )
        prev = label
        offset += durs[i] - XF
    # 颗粒 + 暗角
    parts.append(f"[{prev}]noise=alls=3:allf=t+u,format=yuv420p[vout]")
    fc = ";".join(parts)
    r = run([ff(), "-y", *inputs, "-filter_complex", fc, "-map", "[vout]",
             "-t", f"{total:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
             "-crf", "20", "-pix_fmt", "yuv420p", str(out)])
    if r.returncode != 0:
        raise SystemExit(f"转场合成失败：{r.stderr[-600:]}")


def make_audio(wavs: list[Path], out: Path) -> None:
    """每段前补 XF 静音，再顺序拼接，保证与画面同步。"""
    lst = WORK / "audio.txt"
    lines = []
    for w in wavs:
        padded = w.with_name(w.stem + "-pad.wav")
        run([ff(), "-y", "-f", "lavfi", "-t", f"{XF:.3f}", "-i", "anullsrc=r=22050:cl=mono",
             "-i", str(w), "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[a]",
             "-map", "[a]", "-c:a", "pcm_s16le", str(padded)])
        lines.append(f"file '{padded.as_posix()}'")
    lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run([ff(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "pcm_s16le", str(out)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default="")
    ap.add_argument("--out", default=str(ROOT / "dist" / "demo-v2.mp4"))
    args = ap.parse_args()
    only = {int(x) for x in args.scenes.split(",") if x.strip()} if args.scenes else None
    picked = [s for s in base.scenes if only is None or s["id"] in only]

    WORK.mkdir(parents=True, exist_ok=True)
    base.WORK = WORK                     # 版式与截图统一落在 video2 目录
    clips, durs, wavs = [], [], []
    for i, s in enumerate(picked):
        print(f"[幕 {s['id']}] 出图")
        if s["kind"] == "card":
            html = base.card_html(s)
            img = WORK / f"scene-{s['id']}.png"
            base.edge_shot(f"file:///{html.as_posix()}", img, budget=3000)
        else:
            raw = WORK / f"raw-{s['id']}.png"
            base.edge_shot(f"{base.BASE}/?q={urllib.parse.quote(s['q'])}", raw, size="1280,1000")
            img = base.compose_shot(s, raw)
        wav = WORK / f"scene-{s['id']}.wav"
        audio_len = base.tts(s["narration"], wav)
        dur = max(audio_len + 1.0, s["sec"])
        c = WORK / f"clip-{s['id']}.mp4"
        print(f"[幕 {s['id']}] 合成 {dur:.1f}s 微动 {MOTION[i % len(MOTION)]}")
        clip(s["id"], img, dur, c, MOTION[i % len(MOTION)])
        clips.append(c)
        durs.append(dur)
        wavs.append(wav)

    total = sum(durs) - XF * (len(durs) - 1)
    print(f"总时长约 {total:.1f}s，开始转场拼接")
    silent = WORK / "video-silent.mp4"
    build_xfade(clips, durs, TRANS, total, silent)
    audio = WORK / "audio.wav"
    make_audio(wavs, audio)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    r = run([ff(), "-y", "-i", str(silent), "-i", str(audio), "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
             "-movflags", "+faststart", str(out)])
    if r.returncode != 0:
        raise SystemExit(f"混流失败：{r.stderr[-400:]}")
    print(f"完成：{out}  {out.stat().st_size/1024/1024:.1f} MB  {total:.1f}s")


if __name__ == "__main__":
    main()
