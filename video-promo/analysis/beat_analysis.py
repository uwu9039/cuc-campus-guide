"""BGM 节奏网格分析（video-shotcraft references/music-beat-sync.md 的 numpy 实现）。

本机 Python 3.15 无 librosa/scipy 轮子，故按文档同一套判据自写：
  §1 最小二乘等距网格拟合求真实 BPM 与相位（不信 tempo 标量）
  §2a 三频段瞬态分类 kick 40-160Hz / snare 150-500Hz+1-3kHz / hihat 6-14kHz
  §2b RMS 能量曲线 → 音乐结构表 + 最强 hit 候选拍
  §3 网格验收四指标 match≥98% / mean_abs<10ms / drift<5ms / 首拍有效，0.5x-1x-2x 投票
时刻全程浮点秒，换算成帧不在此脚本发生。

用法：python beat_analysis.py <bgm.mp3> [...]  → analysis/beat_data_<name>.json + grid_candidates_<name>.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 22050
FFMPEG = Path(__file__).resolve().parents[2] / ".venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries" / "ffmpeg-win-x86_64-v7.1.exe"
N_FFT = 1024
HOP = 256   # 86.13 帧/秒：一帧 11.6ms，才够判 ±30ms 的拍位命中
ENV_HZ = SR / HOP


def decode(mp3: Path) -> np.ndarray:
    raw = subprocess.run(
        [str(FFMPEG), "-v", "error", "-i", str(mp3), "-ac", "1", "-ar", str(SR),
         "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    y = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    return y - y.mean()


def stft_mag(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    win = np.hanning(N_FFT + 2)[1:-1]
    n = 1 + (len(y) - N_FFT) // HOP
    frames = np.lib.stride_tricks.as_strided(
        y, shape=(n, N_FFT), strides=(HOP * y.itemsize, y.itemsize))
    spec = np.fft.rfft(frames * win, axis=1)
    mag = np.abs(spec)
    times = (np.arange(n) * HOP + N_FFT / 2) / SR
    return mag, times


def flux(mag: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """指定频段的正差能量流（onset strength），log 压缩抑制宽带噪声。"""
    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    band = mag[:, (freqs >= lo) & (freqs <= hi)]
    lb = np.log1p(band * 1000)
    d = np.diff(lb, axis=0, prepend=lb[:1])
    out = np.clip(d, 0, None).sum(axis=1)
    return out / (np.median(out[out > 0]) + 1e-9)


def peaks(env: np.ndarray, min_gap_s: float = 0.05, thr: float = 1.6) -> np.ndarray:
    gap = max(1, int(round(min_gap_s * ENV_HZ)))
    idx = []
    for i in range(1, len(env) - 1):
        if env[i] < thr:
            continue
        a = max(0, i - gap)
        b = min(len(env), i + gap + 1)
        if env[i] == env[a:b].max():
            idx.append(i)
    out = []
    for i in idx:
        if not out or i - out[-1] >= gap:
            out.append(i)
    return np.array(out, dtype=int)


def grid_fit(onset_times: np.ndarray, T_guess: float, t0_guess: float,
             tol: float = 0.03, iters: int = 4) -> tuple[float, float, np.ndarray, np.ndarray]:
    """把 onset 时刻指派到整数拍，最小二乘拟合 t_i = t0 + i*T，迭代收敛。"""
    T, t0 = T_guess, t0_guess
    used = np.array([], dtype=int)
    for _ in range(iters):
        if len(onset_times) == 0:
            break
        k = np.rint((onset_times - t0) / T).astype(int)
        keep = np.abs(onset_times - (t0 + k * T)) <= tol
        k, tt = k[keep], onset_times[keep]
        if len(k) < 8:
            break
        A = np.vstack([k, np.ones_like(k, dtype=float)]).T
        (T, t0), *_ = np.linalg.lstsq(A, tt, rcond=None)
        used = np.unique(k)
    return T, t0, used, np.array([k, tt]) if len(k) else np.array([[], []])


def score_grid(T: float, t0: float, onset_times: np.ndarray, dur: float) -> dict:
    n = int((dur - t0) // T)
    beats = t0 + np.arange(n) * T
    d = onset_times[None, :] - beats[:, None] if len(onset_times) else np.empty((len(beats), 0))
    nearest = np.abs(d).min(axis=1) if d.size else np.full(len(beats), np.inf)
    hit = nearest <= 0.025
    matched_idx = np.abs(d).argmin(axis=1)[hit] if d.size else np.array([], dtype=int)
    err = nearest[hit]
    # 漂移：命中误差对时间做线性回归的斜率 × 全曲时长
    if hit.sum() > 10:
        A = np.vstack([beats[hit], np.ones(hit.sum())]).T
        (slope, _), *_ = np.linalg.lstsq(A, np.sign(d[hit, matched_idx]) * err, rcond=None)
        drift_ms = abs(slope) * dur * 1000
    else:
        drift_ms = float("inf")
    return {
        "T": round(T, 6), "t0": round(t0, 5), "bpm": round(60.0 / T, 3), "n_beats": n,
        "match": round(float(hit.mean()), 4),
        "mean_abs_ms": round(float(err.mean() * 1000), 2) if err.size else None,
        "max_abs_ms": round(float(err.max() * 1000), 2) if err.size else None,
        "drift_ms_total": round(drift_ms, 2),
        "first_beat_on_attack": bool(len(onset_times) and abs(onset_times[np.abs(onset_times - t0).argmin()] - t0) <= 0.030),
        "pass": bool(hit.mean() >= 0.98 and (err.size and err.mean() * 1000 < 10)
                     and drift_ms < 5 and len(onset_times) and abs(onset_times[np.abs(onset_times - t0).argmin()] - t0) <= 0.030),
    }


def coverage(T: float, t0: float, kick: np.ndarray, times: np.ndarray, dur: float) -> dict:
    """鼓点覆盖率：每个网格拍位置的 kick 能量对同拍反拍位（+T/2）参照的抬升。

    比「25ms 内有没有 onset」更贴合 music-beat-sync §3 的语义——机器鼓点的
    拍位必然有打击能量，反拍位没有；onset 峰太密会让前者判不出来。
    """
    n = int((dur - t0 - 0.05) // T)
    beats = t0 + np.arange(n) * T
    win = int(round(0.045 * ENV_HZ))
    on_vals, on_pos, off_vals, bt_eval = [], [], [], []
    for t in beats:
        c = int(round(t * ENV_HZ))
        a, b = max(0, c - win), min(len(kick), c + win + 1)
        if b - a < 2:
            continue
        bt_eval.append(t)
        seg = kick[a:b]
        j = int(np.argmax(seg))
        on_vals.append(float(seg[j]))
        on_pos.append(times[a + j] - t)
        m = int(round((t + T / 2) * ENV_HZ))
        p, q = max(0, m - win), min(len(kick), m + win + 1)
        off_vals.append(float(kick[p:q].max()) if q - p >= 2 else 0.0)
    on = np.array(on_vals); off = np.array(off_vals); pos = np.array(on_pos)
    bt_arr = np.array(bt_eval)
    ref = np.median(off) + 1e-9
    hit = on > 1.12 * ref
    err = pos[hit]
    signed = np.where(np.abs(err) <= 0.05, err, 0.0)
    if hit.sum() > 10:
        A = np.vstack([bt_arr[hit], np.ones(int(hit.sum()))]).T
        (slope, _), *_ = np.linalg.lstsq(A, signed, rcond=None)
        drift_ms = abs(slope) * dur * 1000
    else:
        drift_ms = float("inf")
    return {
        "T": round(T, 6), "t0": round(t0, 5), "bpm": round(60.0 / T, 3), "n_beats": n,
        "match": round(float(hit.mean()), 4),
        "mean_abs_ms": round(float(np.abs(signed).mean() * 1000), 2) if hit.any() else None,
        "max_abs_ms": round(float(np.abs(signed).max() * 1000), 2) if hit.any() else None,
        "drift_ms_total": round(drift_ms, 2),
        "kick_lift_median": round(float(np.median(on) / ref), 3),
        "first_beat_on_attack": bool(kick[max(0, int(t0 * ENV_HZ) - 2):int(t0 * ENV_HZ) + 4].max() > 1.1 * ref),
        "pass": bool(hit.mean() >= 0.98 and np.abs(signed).mean() * 1000 < 10
                     and drift_ms < 5 and kick[max(0, int(t0 * ENV_HZ) - 2):int(t0 * ENV_HZ) + 4].max() > 1.1 * ref),
    }


def transient_coverage(T: float, t0: float, env: np.ndarray, times: np.ndarray, dur: float) -> dict:
    """§3 的「网格拍命中真实瞬态」判据：拍位 ±40ms 内必须有局部瞬态峰，
    且峰强于该拍前后 ±(T/2) 处的局部基线。打击成分用宽带 flux（含 kick/snare/hat），
    低频贝斯不参与，避免 bass-heavy 编曲把反拍基线抬高造成误判。"""
    n = int((dur - t0 - 0.05) // T)
    beats = t0 + np.arange(n) * T
    w = int(round(0.050 * ENV_HZ))
    base_w = int(round(0.10 * ENV_HZ))
    vals, errs, refs, bt_eval = [], [], [], []
    for t in beats:
        c = int(round(t * ENV_HZ))
        a, b = max(0, c - w), min(len(env), c + w + 1)
        if b - a < 2:
            continue
        bt_eval.append(t)
        j = int(np.argmax(env[a:b]))
        vals.append(float(env[a:b][j]))
        errs.append(times[a + j] - t)
        lo, hi = max(0, c - int(T / 2 * ENV_HZ) - base_w), min(len(env), c + int(T / 2 * ENV_HZ) + base_w)
        side = np.concatenate([env[max(0, c - int(T / 2 * ENV_HZ)) - base_w:max(0, c - int(T / 2 * ENV_HZ)) + base_w],
                               env[hi - 2 * base_w:hi]]) if hi - 2 * base_w > 0 else env[lo:hi]
        refs.append(float(np.median(side)) if side.size else 0.0)
    v = np.array(vals); e = np.array(errs); r = np.array(refs) + 1e-9
    bt_arr = np.array(bt_eval)
    hit = (v > 1.25 * r) & (np.abs(e) <= 0.030)
    signed = e[hit]
    if hit.sum() > 10:
        A = np.vstack([bt_arr[hit], np.ones(int(hit.sum()))]).T
        (slope, _), *_ = np.linalg.lstsq(A, signed, rcond=None)
        drift_ms = abs(slope) * dur * 1000
    else:
        drift_ms = float("inf")
    return {
        "T": round(T, 6), "t0": round(t0, 5), "bpm": round(60.0 / T, 3), "n_beats": n,
        "match": round(float(hit.mean()), 4),
        "mean_abs_ms": round(float(np.abs(signed).mean() * 1000), 2) if hit.any() else None,
        "max_abs_ms": round(float(np.abs(signed).max() * 1000), 2) if hit.any() else None,
        "drift_ms_total": round(drift_ms, 2),
        "lift_median": round(float(np.median(v / r)), 3),
        "first_beat_on_attack": bool(env[max(0, int(t0 * ENV_HZ) - 2):int(t0 * ENV_HZ) + 4].max() > 1.25 * np.median(r)),
        "pass": bool(hit.mean() >= 0.98 and (hit.any() and np.abs(signed).mean() * 1000 < 10)
                     and drift_ms < 5 and env[max(0, int(t0 * ENV_HZ) - 2):int(t0 * ENV_HZ) + 4].max() > 1.25 * np.median(r)),
    }


def fit_to_kick(kick_times: np.ndarray, T_guess: float, t0_guess: float,
                tol: float = 0.05, iters: int = 6) -> tuple[float, float]:
    """把 kick 瞬态指派到整数拍并最小二乘拟合，迭代收敛到 (T, t0)。"""
    T, t0 = T_guess, t0_guess
    for _ in range(iters):
        if len(kick_times) < 8:
            break
        k = np.rint((kick_times - t0) / T).astype(int)
        keep = np.abs(kick_times - (t0 + k * T)) <= tol
        if keep.sum() < 8:
            break
        A = np.vstack([k[keep], np.ones(int(keep.sum()))]).T
        (T, t0), *_ = np.linalg.lstsq(A, kick_times[keep], rcond=None)
    return float(T), float(t0)


def analyze(mp3: Path) -> dict:
    y = decode(mp3)
    dur = len(y) / SR
    mag, times = stft_mag(y)
    env_all = flux(mag, 40, 12000)
    kick = flux(mag, 40, 160)
    body = flux(mag, 150, 500)
    snap = flux(mag, 1000, 3000)
    hat = flux(mag, 6000, 14000)
    perc = flux(mag, 150, 12000)   # 打击成分：排除 sub-bass，避免贝斯抬高反拍基线

    onset_t = times[peaks(env_all)]
    kick_t = times[peaks(kick, min_gap_s=0.10, thr=1.25)]

    # 候选周期：kick 包络自相关的多个峰 + 全频段 AC 最优，各取 0.5x/1x/2x
    ek = kick - kick.mean()
    ac = np.correlate(ek, ek, "full")[len(ek) - 1:]
    ac /= ac[0] + 1e-12
    lag_lo, lag_hi = int(ENV_HZ * 60 / 180), int(ENV_HZ * 60 / 70)
    lags = np.arange(lag_lo, lag_hi)
    ac_l = ac[lags]
    loc = [lags[i] for i in range(1, len(ac_l) - 1)
           if ac_l[i] == ac_l[max(0, i - 6):i + 7].max() and ac_l[i] > 0.12][:6]
    T_seeds = [l / ENV_HZ for l in loc]
    if not T_seeds:
        T_seeds = [lags[np.argmax(ac_l)] / ENV_HZ]
    t0_seed = float(kick_t[0]) if len(kick_t) else (float(onset_t[0]) if len(onset_t) else 0.0)

    cands = []
    seen = set()
    for seed in T_seeds:
        for mult, label in ((0.5, "0.5x"), (1.0, "1x"), (2.0, "2x")):
            T, t0 = fit_to_kick(kick_t, seed * mult, t0_seed)
            if not (0.28 <= T <= 1.0):
                continue
            key = round(T, 3)
            if key in seen:
                continue
            seen.add(key)
            cands.append({"seed_bpm": round(60 / (seed * mult), 2), "which": label,
                          **transient_coverage(T, t0, perc, times, dur)})
    cands.sort(key=lambda c: (c["match"], -(c["mean_abs_ms"] or 999), -c["drift_ms_total"]), reverse=True)
    win = cands[0]

    # 命中表：整数拍位置按频段归类
    beats = win["t0"] + np.arange(win["n_beats"]) * win["T"]
    hits = []
    for i, t in enumerate(beats):
        j = int(round(t * ENV_HZ))
        if j >= len(kick):
            break
        k, b, s, h = kick[j], body[j], snap[j], hat[j]
        kind = "kick" if k >= max(b, s, h) else ("hat" if h >= max(k, b, s) else ("snare" if (b > 1 and s > 1) else "kick"))
        hits.append({"beat": i, "t": round(float(t), 5), "s": round(float(k + b + s + h), 3), "k": kind})
    top = sorted(hits, key=lambda x: -x["s"])[:12]

    # RMS 结构
    frame_rms = np.sqrt((np.lib.stride_tricks.as_strided(
        y, shape=(len(times), N_FFT), strides=(HOP * y.itemsize, y.itemsize)) ** 2).mean(axis=1))
    k_smooth = int(round(ENV_HZ / 4))
    smooth = np.convolve(frame_rms, np.ones(k_smooth) / k_smooth, "same")
    rel = smooth / (smooth.max() + 1e-12)
    full = rel > 0.72
    quiet = rel < 0.35
    sections = {
        "peak_rms_at_beats": [h["beat"] for h in top],
        "strongest_hits": top,
        "full_energy_from_beat": int(np.argmax(full) // (ENV_HZ * win["T"])) if full.any() else None,
        "quiet_frac": round(float(quiet.mean()), 3),
        "quiet_spans_sec": [[round(float(times[min(a, len(times) - 1)]), 2),
                             round(float(times[min(b, len(times) - 1)]), 2)]
                            for a, b in _spans(quiet, min_len=int(ENV_HZ * 0.6))],
    }
    return {
        "file": mp3.name, "duration_sec": round(dur, 3), "sr": SR,
        "grid": win, "candidates": cands,
        "beats_sec": [round(float(b), 5) for b in beats],
        "hits": hits, "sections": sections,
        "onset_count": int(len(onset_t)),
        "method": "numpy STFT spectral flux + least-squares grid fit (librosa/scipy unavailable on py3.15)",
    }


def _spans(mask: np.ndarray, min_len: int):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    if start is not None and len(mask) - start >= min_len:
        out.append((start, len(mask)))
    return out


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    for arg in sys.argv[1:]:
        p = Path(arg)
        r = analyze(p)
        (out_dir / f"beat_data_{p.stem}.json").write_text(
            json.dumps(r, ensure_ascii=False), encoding="utf-8")
        g = r["grid"]
        print(f"{p.name:<22} BPM {g['bpm']:>7.2f}  t0 {g['t0']:.4f}s  T {g['T']:.5f}s  "
              f"match {g['match']*100:5.1f}%  mean {g['mean_abs_ms']}ms  max {g['max_abs_ms']}ms  "
              f"drift {g['drift_ms_total']}ms  beat0 {'OK' if g['first_beat_on_attack'] else 'NO'}  "
              f"{'PASS' if g['pass'] else 'FAIL'}")
