"""오디오 믹스 (numpy) — build.py / compile.py 공용.

- 모든 입력은 ffmpeg 로 48kHz float32 로 디코드해서 샘플 단위로 배치한다.
- 나레이션: 컷 시작 + nar_offset 부터 speech/[pause] 순서대로. [pause] 는 무음.
  Every speech block is gated (silence before the first / after the last sustained voiced frame is zeroed,
  short fades) — TTS files carry isolated clicks in their leading/trailing silence.
- Song episodes (manifest.song): blocks start on their beats (plan.block_starts), trimmed to the voice and
  sped up by plan.block_tempos when they would run past the next line; the AI instrumental is tempo-fitted to
  song.bpm and started on its first downbeat instead of the BGM loop.
- BGM: 전체 길이만큼 루프(짧은 크로스페이드), 기본 bgm_gain_db, speech 구간에서 duck_db 추가 감쇠
  (attack/release 선형 램프, dB 도메인), 시작 페이드인·끝 페이드아웃.
- SFX: 컷 시작 + at 위치에 gain_db 로.
- loudnorm 2-pass (1차 측정 → 2차 linear=true), 결과는 48kHz 로 되돌리고 샘플 수를 정확히 맞춘다.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path

import numpy as np

from .common import AUDIO_EXTS, MomoError, Paths, find_media, list_files, run


def db_gain(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def decode(path: Path, sr: int, channels: int, af: str | None = None) -> np.ndarray:
    """아무 오디오(또는 영상의 음성) → float32 (샘플 수, channels). af: optional ffmpeg audio filter chain."""
    proc = run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-vn", *(["-af", af] if af else []),
                "-f", "f32le", "-acodec", "pcm_f32le", "-ac", str(channels), "-ar", str(sr), "-"])
    data = np.frombuffer(proc.stdout, dtype="<f4")
    return data.reshape(-1, channels).astype(np.float32)


def add_at(buf: np.ndarray, x: np.ndarray, start: int) -> None:
    """buf[start:] += x (범위 밖은 잘라냄)."""
    if start < 0:
        x, start = x[-start:], 0
    end = min(len(buf), start + len(x))
    if end > start:
        buf[start:end] += x[:end - start]


def write_wav(path: Path, data: np.ndarray, sr: int, codec: str = "pcm_f32le") -> Path:
    """float32 WAV (클리핑 없이 loudnorm 으로 넘기기 위해). codec="pcm_s16le" for files other tools import."""
    ch = 1 if data.ndim == 1 else data.shape[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", str(ch), "-i", "-",
         "-c:a", codec, str(path)], input_bytes=np.ascontiguousarray(data, dtype="<f4").tobytes())
    return path


# ---------------------------------------------------------------- 음성 블록 정리 (클릭 제거)

GATE_DB = -35.0          # voiced = 10 ms RMS within this many dB of the block's loudest frame
GATE_SUSTAIN = 3         # frames (30 ms) in a row → real speech, not an isolated click
HEAD_PAD, TAIL_PAD = 0.02, 0.04
FADE_IN, FADE_OUT = 0.008, 0.03


def voiced_bounds(x: np.ndarray, sr: int) -> tuple[int, int] | None:
    """(first, last) sample of sustained speech in a mono block, None for silence."""
    hop = max(1, int(sr * 0.01))
    n = len(x) // hop
    if n == 0:
        return None
    rms = np.sqrt((x[:n * hop].reshape(n, hop).astype(np.float64) ** 2).mean(axis=1))
    peak = float(rms.max())
    if peak < 1e-5:
        return None
    voiced = rms >= peak * 10 ** (GATE_DB / 20)
    run_len = np.convolve(voiced.astype(int), np.ones(GATE_SUSTAIN, dtype=int), "valid")
    starts = np.where(run_len == GATE_SUSTAIN)[0]
    if len(starts) == 0:
        return None
    return int(starts[0] * hop), int(min(len(x), (starts[-1] + GATE_SUSTAIN) * hop))


CLICK_RATIO = 4.0      # a click is this much louder than everything 15–40 ms around it
CLICK_MAX = 0.025      # … and lasts at most this long (s) — words are longer


def declick(x: np.ndarray, sr: int) -> np.ndarray:
    """Mute isolated clicks: a burst ≤ CLICK_MAX long, ≥ CLICK_RATIO × louder than its 15–40 ms surroundings.

    Running speech always has energy around a loud stretch, so only stray TTS clicks (typically right after the
    last word) are hit. The muted stretch gets 2 ms ramps.
    """
    w = max(1, int(sr * 0.005))
    n = len(x) // w
    if n < 20:
        return x
    e = np.sqrt((x[:n * w].reshape(n, w).astype(np.float64) ** 2).mean(axis=1)) + 1e-9
    floor = e.max() * 0.03
    loud = np.zeros(n, dtype=bool)
    for i in range(n):
        if e[i] < floor:
            continue
        ctx = np.concatenate([e[max(0, i - 8):max(0, i - 3)], e[i + 4:i + 9]])
        loud[i] = len(ctx) >= 5 and e[i] > CLICK_RATIO * ctx.max()
    y = x.copy()
    ramp = max(1, int(sr * 0.002))
    i = 0
    while i < n:
        if not loud[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and loud[j + 1]:
            j += 1
        if (j - i + 1) * w <= CLICK_MAX * sr:
            a, b = max(0, i * w - w // 2), min(len(y), (j + 1) * w + w // 2)
            g = np.zeros(b - a, dtype=np.float32)
            r = min(ramp, (b - a) // 2)
            if r:
                g[:r] = np.linspace(1.0, 0.0, r, dtype=np.float32)
                g[-r:] = np.linspace(0.0, 1.0, r, dtype=np.float32)
            y[a:b] *= g
        i = j + 1
    return y


def clean_speech(x: np.ndarray, sr: int, trim: bool = False) -> np.ndarray:
    """Zero the silence around a speech block (and its stray clicks) with short fades.

    trim=False keeps the length (timing unchanged); trim=True cuts to the voice ± pads (song lines start on beats).
    """
    x = declick(x, sr)
    b = voiced_bounds(x, sr)
    if b is None:
        return x[:0].copy() if trim else np.zeros_like(x)
    a = max(0, b[0] - int(HEAD_PAD * sr))
    e = min(len(x), b[1] + int(TAIL_PAD * sr))
    y = x[a:e].astype(np.float32, copy=True)
    fi, fo = min(len(y), int(FADE_IN * sr)), min(len(y), int(FADE_OUT * sr))
    if fi:
        y[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)
    if fo:
        y[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)
    if trim:
        return y
    out = np.zeros_like(x)
    out[a:e] = y
    return out


def speech_length(path: Path, sr: int = 48000) -> float:
    """Seconds of voice in a TTS file after trimming (what a song line occupies before any speed-up)."""
    return len(clean_speech(decode(path, sr, 1)[:, 0], sr, trim=True)) / sr


def cut_vocal(files: list[Path], starts: list[float], tempos: list[float], sr: int) -> np.ndarray:
    """A song cut's lyric lines from its first line on — a lip-sync clip's audio_references (t=0 = first line)."""
    blocks = [song_block(f, sr, k) for f, k in zip(files, tempos)]
    base = starts[0] if starts else 0.0
    n = int(round((max((s - base + len(b) / sr for s, b in zip(starts, blocks)), default=0.0) + 0.05) * sr))
    buf = np.zeros(n, dtype=np.float32)
    for s, b in zip(starts, blocks):
        add_at(buf, b, int(round((s - base) * sr)))
    return buf


def song_block(path: Path, sr: int, tempo: float = 1.0) -> np.ndarray:
    """A song line: trimmed to the voice, sped up by tempo (atempo keeps the pitch)."""
    x = clean_speech(decode(path, sr, 1)[:, 0], sr, trim=True)
    if abs(tempo - 1.0) < 1e-3 or not len(x):
        return x
    fd, name = tempfile.mkstemp(prefix="momo_line_", suffix=".wav")
    os.close(fd)
    tmp = write_wav(Path(name), x, sr)
    try:
        y = decode(tmp, sr, 1, af=f"atempo={tempo:.5f}")[:, 0]
    finally:
        tmp.unlink(missing_ok=True)
    return clean_speech(y, sr, trim=True)


# ---------------------------------------------------------------- 나레이션

def build_narration(plans, total: float, cfg: dict) -> tuple[np.ndarray, list[tuple[float, float]]]:
    """(mono 트랙, speech 구간 목록[(시작, 끝) 초]). 없는 음성(애니매틱)은 추정 길이만큼 무음."""
    sr = int(cfg["audio"]["sample_rate"])
    gain = db_gain(float(cfg["audio"]["narration_gain_db"]))
    buf = np.zeros(int(round(total * sr)), dtype=np.float32)
    spans: list[tuple[float, float]] = []
    for p in plans:
        if p.block_starts:  # song: each line on its beat, trimmed to the voice, maybe sped up
            for f, rel, tempo in zip(p.speech_files, p.block_starts, p.block_tempos):
                if f is None:
                    continue
                t = p.start + rel
                x = song_block(f, sr, tempo) * gain
                add_at(buf, x, int(round(t * sr)))
                spans.append((t, t + len(x) / sr))
            continue
        t = p.start + p.nar_offset
        k = 0
        for it in p.items:
            if it.kind == "pause":
                t += it.seconds
                continue
            f, d = p.speech_files[k], p.speech_durs[k]
            k += 1
            if f is not None:
                x = clean_speech(decode(f, sr, 1)[:, 0], sr) * gain
                add_at(buf, x, int(round(t * sr)))
                spans.append((t, t + len(x) / sr))
            t += d
    return buf, spans


# ---------------------------------------------------------------- BGM

def find_bgm(paths: Paths, cfg: dict, manifest: dict | None) -> Path | None:
    """manifest.bgm → config.audio.bgm_file → assets/bgm 첫 파일."""
    name = (manifest or {}).get("bgm") or cfg["audio"].get("bgm_file")
    if name:
        p = Path(name)
        p = p if p.is_absolute() else paths.bgm / p
        if not p.exists():
            raise MomoError(f"BGM 파일 없음: {p}")
        return p
    files = list_files(paths.bgm, AUDIO_EXTS)
    return files[0] if files else None


def loop_to(x: np.ndarray, n: int, sr: int, xfade: float = 0.05) -> np.ndarray:
    """x 를 n 샘플까지 반복 (이음새는 짧은 선형 크로스페이드)."""
    if len(x) == 0:
        raise MomoError("BGM 이 비어 있음")
    if len(x) >= n:
        return x[:n].copy()
    xf = min(int(sr * xfade), len(x) // 4)
    step = len(x) - xf
    win = np.ones(len(x), dtype=np.float32)
    if xf:
        ramp = np.linspace(0.0, 1.0, xf, endpoint=False, dtype=np.float32)
        win[:xf], win[-xf:] = ramp, ramp[::-1] + (1.0 / xf)
    out = np.zeros((n + len(x), x.shape[1]), dtype=np.float32)
    pos, first = 0, True
    while pos < n:
        w = win.copy()
        if first:
            w[:xf] = 1.0
            first = False
        out[pos:pos + len(x)] += x * w[:, None]
        pos += step
    return out[:n]


def duck_gain(spans: list[tuple[float, float]], n: int, sr: int, cfg: dict,
              base_db: float | None = None, duck_db: float | None = None) -> np.ndarray:
    """BGM 게인 곡선 (선형 배수, 길이 n). dB 도메인에서 덕킹 램프 + 페이드인/아웃."""
    a = dict(cfg["audio"])
    if base_db is not None:
        a["bgm_gain_db"] = base_db
    if duck_db is not None:
        a["duck_db"] = duck_db
    att, rel = max(1e-3, float(a["duck_attack"])), max(1e-3, float(a["duck_release"]))
    total = n / sr
    rate = 1000
    t = np.arange(int(math.ceil(total * rate)) + 1, dtype=np.float64) / rate
    duck = np.zeros_like(t)
    for s, e in spans:
        up = np.clip((t - (s - att)) / att, 0.0, 1.0)
        down = np.clip(((e + rel) - t) / rel, 0.0, 1.0)
        np.maximum(duck, np.minimum(up, down), out=duck)
    g_db = float(a["bgm_gain_db"]) + float(a["duck_db"]) * duck
    g = 10.0 ** (g_db / 20.0)
    fi, fo = float(a["bgm_fade_in"]), float(a["bgm_fade_out"])
    if fi > 0:
        g *= np.clip(t / fi, 0.0, 1.0)
    if fo > 0:
        g *= np.clip((total - t) / fo, 0.0, 1.0)
    return np.interp(np.arange(n) / sr, t, g).astype(np.float32)


# ---------------------------------------------------------------- 노래 반주 (song episodes)

def _onsets(x: np.ndarray, sr: int, hop: int = 256, win: int = 2048):
    """(spectral-flux onset envelope, low-band (<150 Hz) envelope, chroma (n×12), frames per second).

    Frame k is centred at (k·hop + win/2)/sr — callers add ONSET_LAG to frame times.
    """
    n = 1 + (len(x) - win) // hop
    if n < 64:
        raise MomoError("반주가 너무 짧아 박자를 찾을 수 없음")
    window = np.hanning(win).astype(np.float32)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    low_bins = freqs < 150
    tonal = (freqs > 80) & (freqs < 4000)
    pc = np.round(12 * np.log2(freqs[tonal] / 440.0) + 69).astype(int) % 12
    full, low, chroma = np.zeros(n), np.zeros(n), np.zeros((n, 12))
    prev = None
    for s in range(0, n, 2048):  # chunks keep memory small
        idx = np.arange(win)[None, :] + hop * np.arange(s, min(n, s + 2048))[:, None]
        spec = np.abs(np.fft.rfft(x[idx] * window, axis=1))
        for c in range(12):
            chroma[s:s + len(spec), c] = spec[:, tonal][:, pc == c].sum(axis=1)
        mag = np.log1p(100 * spec)
        if prev is not None:
            mag = np.vstack([prev[None, :], mag])
        d = np.maximum(0.0, np.diff(mag, axis=0))
        k = s + (0 if prev is not None else 1)
        full[k:k + len(d)] = d.sum(axis=1)
        low[k:k + len(d)] = d[:, low_bins].sum(axis=1)
        prev = mag[-1]

    def hp(v: np.ndarray) -> np.ndarray:
        return np.maximum(0.0, v - np.convolve(v, np.ones(16) / 16, "same"))
    return hp(full), hp(low), chroma, sr / hop


def _comb(env: np.ndarray, period: float, phase: float, step: float = 1.0) -> float:
    ks = np.arange(0, (len(env) - 1 - phase) / (period * step))
    return float(np.interp(phase + ks * period * step, np.arange(len(env)), env).mean()) if len(ks) else 0.0


def detect_beats(path: Path, bpm_hint: float | None = None) -> dict:
    """Tempo and beat grid of an instrumental: {bpm, beat0, downbeat0, confidence} (seconds from file start).

    Autocorrelation of the spectral-flux onset envelope picks the period (70–160 BPM, prior around bpm_hint),
    a comb over the whole track refines period and phase, the strongest low-band beat of the bar is beat 1.
    """
    sr, win = 22050, 2048
    env, low, chroma, fps = _onsets(decode(path, sr, 1)[:, 0], sr, win=win)
    lag_s = win / 2 / sr
    spec = np.fft.rfft(env - env.mean(), 2 * len(env))
    ac = np.fft.irfft(spec * np.conj(spec))[:len(env)]
    lags = np.arange(1, len(env) // 4)
    bpms = 60 * fps / lags
    prior = np.exp(-0.5 * (np.log2(bpms / (bpm_hint or 110.0)) / 0.6) ** 2)
    score = np.where((bpms >= 70) & (bpms <= 160), ac[lags] * prior, -np.inf)
    lag = float(lags[int(np.argmax(score))])
    best = (-1.0, lag, 0.0)
    for period in np.linspace(lag * 0.985, lag * 1.015, 61):
        for phase in np.arange(0.0, period, 0.25):
            sc = _comb(env, period, phase)
            if sc > best[0]:
                best = (sc, float(period), float(phase))
    sc, period, phase = best
    # beat 1 of the bar: chords change on bar lines (chroma novelty) and the kick is strongest there
    norm = chroma / (np.linalg.norm(chroma, axis=1, keepdims=True) + 1e-9)
    cum = np.vstack([np.zeros((1, 12)), np.cumsum(norm, axis=0)])
    half = max(1, int(round(2 * period)))

    def novelty(t: float) -> float:
        i = int(round(t))
        if i - half < 0 or i + half >= len(norm):
            return 0.0
        a, b = cum[i] - cum[i - half], cum[i + half] - cum[i]
        return 1.0 - float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

    def bar_score(j: int) -> tuple[float, float]:
        ts = np.arange(phase + j * period, len(norm), 4 * period)
        return float(np.mean([novelty(t) for t in ts])) if len(ts) else 0.0, _comb(low, period, phase + j * period, 4.0)
    scores = [bar_score(j) for j in range(4)]
    nov = np.array([s[0] for s in scores])
    kick = np.array([s[1] for s in scores])
    z = (nov - nov.mean()) / (nov.std() + 1e-9) + 0.5 * (kick - kick.mean()) / (kick.std() + 1e-9)
    j = int(np.argmax(z))
    off_beat = _comb(env, period, phase + period / 2)
    return {"bpm": round(60 * fps / period, 4), "beat0": round(phase / fps + lag_s, 4),
            "downbeat0": round((phase + j * period) / fps + lag_s, 4),
            "confidence": round(sc / (off_beat + 1e-9), 3)}


def music_file(paths: Paths, ep: str) -> Path | None:
    return find_media(paths.ep(ep) / "audio", "music", AUDIO_EXTS)


def song_music(path: Path, song: dict, n: int, sr: int) -> tuple[np.ndarray, dict]:
    """The instrumental fitted to song.bpm, starting on its first downbeat at song.music_start (s), n samples."""
    ana = (song.get("music") or {}).get("analysis") or detect_beats(path, float(song["bpm"]))
    ratio = float(song["bpm"]) / float(ana["bpm"])
    x = decode(path, sr, 2, af=f"atempo={ratio:.6f}")
    head = int(round(float(ana["downbeat0"]) / ratio * sr))
    x = x[head:]
    fi = min(len(x), int(0.01 * sr))
    x[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    out = np.zeros((n, 2), dtype=np.float32)
    add_at(out, x, int(round(float(song.get("music_start") or 0.0) * sr)))
    info = {"bpm_detected": ana["bpm"], "tempo_ratio": round(ratio, 5), "downbeat0": ana["downbeat0"],
            "short_by": round(max(0.0, (n - head - len(x)) / sr), 2)}
    return out, info


def track_file(paths: Paths, ep: str) -> Path | None:
    """The finished song of a track episode (song.track) → episodes/<ep>/audio/song.<ext>."""
    return find_media(paths.ep(ep) / "audio", "song", AUDIO_EXTS)


def vocals_file(paths: Paths, ep: str) -> Path | None:
    """Its vocal stem (lip-sync references) → episodes/<ep>/audio/song_vocals.<ext>."""
    return find_media(paths.ep(ep) / "audio", "song_vocals", AUDIO_EXTS)


def song_track_audio(path: Path, song: dict, n: int, sr: int) -> tuple[np.ndarray, dict]:
    """The finished song as the episode bed: song-file time track.start → video 0, n samples, no time-stretch."""
    tr = song.get("track") or {}
    x = decode(path, sr, 2)
    head = int(round(float(tr.get("start") or 0.0) * sr))
    x = x[head:head + n]
    out = np.zeros((n, 2), dtype=np.float32)
    out[:len(x)] = x
    fo = min(len(x), int(0.02 * sr))  # no click if the video ends before the song does
    if len(x) == n and fo:
        out[n - fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)[:, None]
    return out, {"file": path.name, "start": float(tr.get("start") or 0.0),
                 "short_by": round(max(0.0, (n - len(x)) / sr), 2)}


# ---------------------------------------------------------------- loudnorm

def _last_json(stderr: bytes) -> dict:
    text = stderr.decode("utf-8", "replace")
    i, j = text.rfind("{"), text.rfind("}")
    if i < 0 or j < i:
        raise MomoError("loudnorm 측정값을 읽지 못함:\n" + text[-1500:])
    return json.loads(text[i:j + 1])


def loudnorm(src: Path, dst: Path, cfg: dict, n_samples: int | None = None) -> dict:
    """2-pass loudnorm (I/TP 는 config, LRA 11). 1차 측정값으로 2차 linear=true. 결과 48kHz float WAV."""
    a = cfg["audio"]
    sr = int(a["sample_rate"])
    base = f"loudnorm=I={float(a['loudness_lufs'])}:TP={float(a['true_peak'])}:LRA=11"
    m = _last_json(run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(src), "-af",
                        base + ":print_format=json", "-f", "null", "-"]).stderr)
    fit = f",apad=whole_len={n_samples},atrim=end_sample={n_samples}" if n_samples else ""
    try:
        measured_i = float(m["input_i"])
    except (KeyError, ValueError):
        measured_i = -math.inf
    if not measured_i > -70.0:  # 무음 (loudnorm 이 -inf 를 돌려줌) → 그대로 복사
        run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", f"aresample={sr}{fit}",
             "-c:a", "pcm_f32le", str(dst)])
        return {"input_i": None, "output_i": None, "normalization_type": "silent"}
    af = (f"{base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
          f":print_format=json,aresample={sr}{fit}")
    r = _last_json(run(["ffmpeg", "-y", "-hide_banner", "-nostdin", "-i", str(src), "-af", af,
                        "-ar", str(sr), "-c:a", "pcm_f32le", str(dst)]).stderr)
    return {"input_i": float(m["input_i"]), "input_tp": float(m["input_tp"]),
            "output_i": float(r["output_i"]), "output_tp": float(r["output_tp"]),
            "normalization_type": r.get("normalization_type")}


# ---------------------------------------------------------------- 에피소드 믹스

def build_mix(paths: Paths, cfg: dict, manifest: dict, plans, total: float, out_wav: Path,
              allow_missing: bool = False) -> dict:
    """나레이션 + BGM(덕킹) + SFX → loudnorm → out_wav (48k 스테레오, 정확히 total 초)."""
    sr = int(cfg["audio"]["sample_rate"])
    n = int(round(total * sr))
    nar, spans = build_narration(plans, total, cfg)
    mix = np.repeat(nar[:, None], 2, axis=1)
    info: dict = {"speech_blocks": len(spans), "bgm": None, "sfx": 0, "warnings": []}

    song = manifest.get("song") if isinstance(manifest.get("song"), dict) else None
    if song and isinstance(song.get("track"), dict):  # finished song: vocals + music already mixed
        tfile = track_file(paths, manifest["ep"])
        if tfile is None:
            if not allow_missing:
                raise MomoError(f"노래 파일 없음: episodes/{manifest['ep']}/audio/song.* "
                                f"(fetch_assets.py --ep {manifest['ep']})")
            info["warnings"].append("노래 파일 없음 → 인트로·아웃트로 음성만 (--allow-missing)")
        else:
            bed, tinfo = song_track_audio(tfile, song, n, sr)
            mix += bed * duck_gain(spans, n, sr, cfg, float(song.get("track_gain_db", 0.0)),
                                   float(song.get("duck_db", -6.0)))[:, None]
            info["track"] = tinfo
            if tinfo["short_by"] > 0.05:
                info["warnings"].append(f"노래가 영상보다 {tinfo['short_by']}초 짧음 — bars / track.end 확인")
    else:
        _add_bed(paths, cfg, manifest, song, spans, n, sr, mix, info, allow_missing)

    for p in plans:
        for s in p.sfx:
            x = decode(s["file"], sr, 2) * db_gain(s["gain_db"])
            add_at(mix, x, int(round((p.start + s["at"]) * sr)))
            info["sfx"] += 1

    premix = write_wav(out_wav.with_name(out_wav.stem + "_premix.wav"), mix, sr)
    info["loudnorm"] = loudnorm(premix, out_wav, cfg, n)
    return info


def _add_bed(paths: Paths, cfg: dict, manifest: dict, song: dict | None, spans, n: int, sr: int,
             mix: np.ndarray, info: dict, allow_missing: bool) -> None:
    """Chant songs: the AI instrumental (ducked); other episodes: the looped BGM (ducked)."""
    mfile = music_file(paths, manifest["ep"]) if song else None
    if song and mfile is None and not allow_missing:
        raise MomoError(f"노래 반주 파일 없음: episodes/{manifest['ep']}/audio/music.* (fetch_assets.py --ep {manifest['ep']})")
    bgm_path = None if song else find_bgm(paths, cfg, manifest)
    if mfile is not None:
        music, minfo = song_music(mfile, song, n, sr)
        mix += music * duck_gain(spans, n, sr, cfg, float(song.get("music_gain_db", -6.0)),
                                 float(song.get("duck_db", -5.0)))[:, None]
        info["music"] = {"file": mfile.name, **minfo}
        if minfo["short_by"] > 0:
            info["warnings"].append(f"반주가 {minfo['short_by']}초 짧음 — 더 긴 반주를 생성할 것")
    elif song:
        info["warnings"].append("반주 없음 → 음성만 (--allow-missing)")
    elif bgm_path is None:
        if not allow_missing:
            raise MomoError(f"BGM 없음: assets/bgm/ 에 BGM 을 넣어줘 ({paths.bgm})")
        info["warnings"].append("BGM 없음 → BGM 없이 조립 (--allow-missing)")
    else:
        bgm = loop_to(decode(bgm_path, sr, 2), n, sr)
        mix += bgm * duck_gain(spans, n, sr, cfg)[:, None]
        info["bgm"] = bgm_path.name
