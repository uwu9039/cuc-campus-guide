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
    # 开场：痛点
    {"id": "a1", "kind": "punch", "text": "办一件事，跑三趟。", "head": "跑三趟", "sub": "问四个人"},
    {"id": "a2", "kind": "shot", "text": "这是中国传媒大学的校园办事向导。", "img": "raw-2.png", "zoom": 1.0,
     "head": "校园办事向导", "line": "问一句，给原文"},
    # 一、成绩单：问 → 答 → 原文
    {"id": "b1", "kind": "shot", "text": "成绩单密封章，几点能办？", "img": "raw-2.png", "zoom": 1.0,
     "head": "成绩单密封章几点能办", "line": "一句人话就够了"},
    {"id": "b2", "kind": "shot", "text": "周二周四，下午两点半到四点半。", "img": "raw-2.png", "zoom": 1.26,
     "head": "周二 · 周四 14:00–16:30", "line": "原句压在下头，可以点开"},
    {"id": "b25", "kind": "shot", "text": "每句结论下面，都压着原话。", "img": "raw-2.png", "zoom": 1.3,
     "head": "引文可核", "line": "点开就是官方原文"},
    # 二、选课：会反问
    {"id": "b3", "kind": "shot", "text": "有的问题，它得先问你一句。", "img": "raw-3.png", "zoom": 1.0,
     "head": "选课截止，看第几周开课", "line": "条件不清，它不硬答"},
    {"id": "b4", "kind": "shot", "text": "第一周，还是之后，时限不一样。", "img": "raw-3.png", "zoom": 1.3,
     "head": "第一周 / 晚于第一周", "line": "两条通道，时限不同"},
    # 三、转专业：各学院门槛不同
    {"id": "c1", "kind": "shot", "text": "转专业，每个学院门槛都不一样。", "img": "raw-zwzy.png", "zoom": 1.0,
     "head": "转专业 · 各学院门槛不同", "line": "问哪个学院，答哪个学院"},
    {"id": "c2", "kind": "shot", "text": "新闻学院三月四号考试。", "img": "raw-zwzy.png", "zoom": 1.3,
     "head": "新闻学院 3 月 4 日", "line": "考试内容、地点都写清楚"},
    {"id": "c3", "kind": "shot", "text": "动画学院要作品集，一月交。", "img": "raw-zwzy.png", "zoom": 1.34,
     "head": "动画学院 · 作品集", "line": "1 月 9 日到 12 日提交"},
    {"id": "c4", "kind": "stat", "text": "六百八十八份官方文件打底。", "num": "688", "label": "份语料",
     "note": "官网 · 制度汇编 · 公众号"},
    # 四、体测
    {"id": "d1", "kind": "shot", "text": "体测免测，当年按五十分计。", "img": "raw-tic.png", "zoom": 1.2,
     "head": "免测当年按 50 分计", "line": "条款写得很细"},
    {"id": "d2", "kind": "shot", "text": "伤病免测，得交材料。", "img": "raw-tic.png", "zoom": 1.28,
     "head": "免测要交材料", "line": "按标准逐项认定"},
    # 五、校园卡
    {"id": "e1", "kind": "shot", "text": "校园卡丢了，机器上补，二十块。", "img": "raw-xyk.png", "zoom": 1.22,
     "head": "补卡 20 元工本费", "line": "艺术与传播大楼 1 层"},
    {"id": "e2", "kind": "shot", "text": "挂失在手机上就能办。", "img": "raw-xyk.png", "zoom": 1.3,
     "head": "手机可挂失", "line": "补卡还是要去窗口"},
    # 六、报修
    {"id": "f1", "kind": "shot", "text": "宿舍报修，打这个号。", "img": "raw-bx.png", "zoom": 1.18,
     "head": "24 小时热线 65783000", "line": "公众号也能报修"},
    {"id": "f2", "kind": "shot", "text": "半夜坏了，也能打。", "img": "raw-bx.png", "zoom": 1.26,
     "head": "24 小时都有人接", "line": "后勤保障处"},
    # 数据
    {"id": "g1", "kind": "stat", "text": "一千五百八十九条事实，条条能查。", "num": "1589", "label": "个事实字段",
     "note": "0 条缺证 · 逐条引文可核"},
    # 收尾态度
    {"id": "h1", "kind": "punch", "text": "答不上来，就说答不上来。", "head": "不会编", "sub": "答不出就直说"},
    # 片尾
    {"id": "z1", "kind": "closing", "text": "校园办事向导，说得清，带得对。",
     "head": "校园办事向导", "sub": "说得清，带得对",
     "line": "357 条事项|1589 条事实|0 条缺证"},
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
