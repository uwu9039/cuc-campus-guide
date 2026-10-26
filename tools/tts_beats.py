"""按"节拍"生成旁白：短句 + 快语速，并输出 beats.json 给 Remotion 用。

设计：
  - 每个节拍一句短旁白（8–18 字），语速 Rate=2（比默认快）
  - 生成 wav 后读时长，写进 beats.json，Remotion 按它排时间线
  - 路径一律用 pathlib / 正斜杠，不手写反斜杠

用法：python tools/tts_beats.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "video-remotion" / "public" / "beats"
BEATS_JSON = ROOT / "video-remotion" / "src" / "beats.json"
RATE = 2          # 语速：2 略快，4 很快
VOICE = "Microsoft Huihui Desktop"


def ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def dur_of(wav: Path) -> float:
    r = subprocess.run([ffmpeg(), "-i", str(wav)], capture_output=True, text=True)
    for line in (r.stderr or "").splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 2.5


def speak(text: str, wav: Path) -> float:
    wav.parent.mkdir(parents=True, exist_ok=True)
    txt = wav.with_suffix(".txt")
    txt.write_text(text, encoding="utf-8")
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SelectVoice('{VOICE}'); $s.Rate = {RATE}; "
        f"$s.SetOutputToWaveFile('{wav.as_posix()}'); "
        f"$s.Speak([IO.File]::ReadAllText('{txt.as_posix()}', [Text.Encoding]::UTF8)); $s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=120)
    if not wav.exists():
        raise SystemExit(f"TTS 失败：{text}")
    return dur_of(wav)


# ---- 节拍脚本：说一句、看一屏 ----
BEATS = [
    {"id": "a1", "kind": "punch", "text": "办一件事，跑三趟。", "head": "跑三趟", "sub": "问四个人"},
    {"id": "a2", "kind": "shot", "text": "比如这个。", "img": "raw-2.png", "zoom": 1.0,
     "head": "成绩单密封章几点能办", "line": "一句具体的话"},
    {"id": "a3", "kind": "shot", "text": "它只答被问的那一面。", "img": "raw-2.png", "zoom": 1.22,
     "head": "只答这一面", "line": "先翻译成「成绩单办理 · 办理时间」"},
    {"id": "a4", "kind": "shot", "text": "周二周四，下午两点半到四点半。", "img": "raw-2.png", "zoom": 1.32,
     "head": "周二 · 周四 14:00–16:30", "line": "原句压在下头，可点开"},
    {"id": "a5", "kind": "shot", "text": "有些问题，它得先问你。", "img": "raw-3.png", "zoom": 1.0,
     "head": "该问的它先问你", "line": "选课截止，取决于第几周开课"},
    {"id": "a6", "kind": "shot", "text": "因为时限跟着开课周走。", "img": "raw-3.png", "zoom": 1.3,
     "head": "第一周？还是晚于第一周", "line": "两条通道，时限不同"},
    {"id": "a7", "kind": "stat", "text": "六百二十七个事实，条条能查。", "num": "627", "label": "个事实字段",
     "note": "0 条缺证 · 逐条引文可核"},
    {"id": "a8", "kind": "punch", "text": "答不上来，就说答不上来。", "head": "不会编", "sub": "答不出就直说"},
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    result = []
    for b in BEATS:
        wav = OUT / f"{b['id']}.wav"
        d = speak(b["text"], wav)
        item = {**b, "audio": f"beats/{b['id']}.wav", "dur": round(d + 0.35, 2)}
        result.append(item)
        print(f"  {b['id']}: {d:.2f}s  {b['text']}")
    BEATS_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(b["dur"] for b in result)
    print(f"共 {len(result)} 拍，总时长约 {total:.1f}s（不含转场重叠）")


if __name__ == "__main__":
    main()
