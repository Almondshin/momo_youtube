"""오디오 믹스 (numpy) — build.py / compile.py 공용.

- 모든 입력은 ffmpeg 로 48kHz float32 로 디코드해서 샘플 단위로 배치한다.
- 나레이션: 컷 시작 + nar_offset 부터 speech/[pause] 순서대로. [pause] 는 무음.
- BGM: 전체 길이만큼 루프(짧은 크로스페이드), 기본 bgm_gain_db, speech 구간에서 duck_db 추가 감쇠
  (attack/release 선형 램프, dB 도메인), 시작 페이드인·끝 페이드아웃.
- SFX: 컷 시작 + at 위치에 gain_db 로.
- loudnorm 2-pass (1차 측정 → 2차 linear=true), 결과는 48kHz 로 되돌리고 샘플 수를 정확히 맞춘다.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .common import AUDIO_EXTS, MomoError, Paths, list_files, run


def db_gain(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def decode(path: Path, sr: int, channels: int) -> np.ndarray:
    """아무 오디오(또는 영상의 음성) → float32 (샘플 수, channels)."""
    proc = run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-vn", "-f", "f32le",
                "-acodec", "pcm_f32le", "-ac", str(channels), "-ar", str(sr), "-"])
    data = np.frombuffer(proc.stdout, dtype="<f4")
    return data.reshape(-1, channels).astype(np.float32)


def add_at(buf: np.ndarray, x: np.ndarray, start: int) -> None:
    """buf[start:] += x (범위 밖은 잘라냄)."""
    if start < 0:
        x, start = x[-start:], 0
    end = min(len(buf), start + len(x))
    if end > start:
        buf[start:end] += x[:end - start]


def write_wav(path: Path, data: np.ndarray, sr: int) -> Path:
    """float32 WAV (클리핑 없이 loudnorm 으로 넘기기 위해)."""
    ch = 1 if data.ndim == 1 else data.shape[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", str(ch), "-i", "-",
         "-c:a", "pcm_f32le", str(path)], input_bytes=np.ascontiguousarray(data, dtype="<f4").tobytes())
    return path


# ---------------------------------------------------------------- 나레이션

def build_narration(plans, total: float, cfg: dict) -> tuple[np.ndarray, list[tuple[float, float]]]:
    """(mono 트랙, speech 구간 목록[(시작, 끝) 초]). 없는 음성(애니매틱)은 추정 길이만큼 무음."""
    sr = int(cfg["audio"]["sample_rate"])
    gain = db_gain(float(cfg["audio"]["narration_gain_db"]))
    buf = np.zeros(int(round(total * sr)), dtype=np.float32)
    spans: list[tuple[float, float]] = []
    for p in plans:
        t = p.start + p.nar_offset
        k = 0
        for it in p.items:
            if it.kind == "pause":
                t += it.seconds
                continue
            f, d = p.speech_files[k], p.speech_durs[k]
            k += 1
            if f is not None:
                x = decode(f, sr, 1)[:, 0] * gain
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


def duck_gain(spans: list[tuple[float, float]], n: int, sr: int, cfg: dict) -> np.ndarray:
    """BGM 게인 곡선 (선형 배수, 길이 n). dB 도메인에서 덕킹 램프 + 페이드인/아웃."""
    a = cfg["audio"]
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

    bgm_path = find_bgm(paths, cfg, manifest)
    if bgm_path is None:
        if not allow_missing:
            raise MomoError(f"BGM 없음: assets/bgm/ 에 BGM 을 넣어줘 ({paths.bgm})")
        info["warnings"].append("BGM 없음 → BGM 없이 조립 (--allow-missing)")
    else:
        bgm = loop_to(decode(bgm_path, sr, 2), n, sr)
        mix += bgm * duck_gain(spans, n, sr, cfg)[:, None]
        info["bgm"] = bgm_path.name

    for p in plans:
        for s in p.sfx:
            x = decode(s["file"], sr, 2) * db_gain(s["gain_db"])
            add_at(mix, x, int(round((p.start + s["at"]) * sr)))
            info["sfx"] += 1

    premix = write_wav(out_wav.with_name(out_wav.stem + "_premix.wav"), mix, sr)
    info["loudnorm"] = loudnorm(premix, out_wav, cfg, n)
    return info
