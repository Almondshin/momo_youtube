# ep03 계획: 더 촘촘하고 리듬감 있는 진짜 동요

## 1. ep02가 지루했던 이유 (빌드 타임라인에서 직접 잰 값)
- 2분 48초(167.5초) 동안 컷이 24개뿐이라 평균 7초짜리 컷이었습니다. 10초짜리 컷이 9개입니다.
- 템포는 96 BPM으로 느긋했습니다. 목소리가 나오는 시간은 **61%** 이고, 나머지 39%는 반주만 흐릅니다. 줄 사이에 4초 가까이 비는 곳도 4번 있습니다.
- 가사 33줄이 전부 달라서 반복되는 후렴이 없습니다. 후렴처럼 들리는 줄도 1분 5초에야 처음 나옵니다.
- 한 줄씩 TTS로 읽는 챈트라서 멜로디가 없습니다.

## 2. ep03 목표
| | ep02 | ep03 |
|---|---|---|
| 템포 | 96 BPM | **120 BPM** (1마디가 정확히 2초) |
| 길이 | 2분 48초 | **약 2분 2초** (61마디, 지시서의 2~3분 안) |
| 컷 | 24개, 평균 7초 | **38개, 평균 3.2초** (최소 2초, 노래 중에는 최대 4초) |
| 목소리 비중 | 61% | **약 85~90%** |
| 후렴 | 없음 (후렴 같은 줄 1분 5초) | 4초에 첫 후렴, 이후 후렴 3번 |
| 따라 말하기 대기 | 약 4초 | 1마디 (1.5~2초) |

- 구성: 인트로 → 후렴 앞부분 → 1절·후렴 → 2절·후렴 → 3절(Ducky 등장) → 단어 복습 → 마지막 후렴 → 아웃트로
- 컷은 모두 마디 첫 박에 바뀝니다. 가사 자막은 실제로 부르는 단어에 맞춰 톡톡 튀게 합니다.
- **지시서와 달라지는 점 (승인 필요)**
  - 챈트 대신 진짜 노래로 부릅니다.
  - 컷이 22~28개에서 38개로 늘어납니다.
  - 움직이는 영상 컷(V컷)이 15개를 넘으므로 사유를 기록해야 합니다.

## 3. 진짜 노래를 만드는 방법
- **1순위: ACE-Step 1.5.** 이 맥에서 직접 돌리는 무료 오픈소스 작곡 AI입니다. 가사·템포·조를 넣으면 반주와 노래를 한 번에 만들어 줍니다.
  - **크레딧: 0**
  - **라이선스:** 코드와 모델 모두 MIT라 수익 채널에서 써도 됩니다.
  - **설치:** 약 15~20GB, 30~60분 걸립니다.
  - **생성 속도:** 2분짜리 곡 하나에 1~2분입니다(추정). 여러 개를 뽑아서 가장 좋은 것을 고릅니다.
  - **약점**
    - 진짜 아이 목소리보다는 '밝은 젊은 여성' 목소리가 나올 가능성이 큽니다.
    - 인트로·아웃트로의 모모 목소리(Gracie)와 가수 목소리가 다릅니다.
    - 금속성 잡음이 섞일 수 있습니다.
    - 음악성 점수는 최상위가 아닙니다. 강점은 발음과 템포 조절입니다.
- **대안: 모모 목소리 그대로 부르게 만들기.** 지금 쓰는 Gracie TTS 문장을 음표 길이에 맞게 늘리고 음높이를 바꾸는 도구를 직접 만듭니다.
  - 모모 목소리가 유지됩니다.
  - 크레딧은 거의 0입니다 (한 줄에 0.2).
  - 개발에 1.5~3일 걸리고, 약간 '오토튠' 느낌이 납니다.
- **쓰지 않을 것**
  - YuE2: 실제로 받는 모델 파일이 비상업용 라이선스입니다.
  - SongGeneration: 연구용 라이선스입니다.
  - MiniMax: 이 맥에서 돌아가지 않습니다.
  - ElevenLabs [sings]: 멜로디를 우리가 정할 수 없습니다.
- **YouTube:** AI로 만든 음악은 업로드할 때 'AI 사용 = 예'로 표시해야 합니다. 수익화에는 영향이 없습니다. 지금 설정은 false라서 바꿔야 하고, 반주가 AI였던 ep02도 표시하는 것을 권합니다.

## 4. 크레딧 예상 (한도 250)
- 노래는 0입니다.
- 영상 기본안은 161입니다.
  - 재생성 20%를 넣으면 193
  - ep02의 실제 재생성률로 계산하면 204~214
  - 최악의 경우 약 230
- 절약안(마지막 후렴 영상 재사용 등)은 139이고, 재생성 20%를 넣으면 167입니다.
- 참고로 ep02는 한 편 몫만 약 316이었습니다 (1회성 비용 제외).

## 5. 리스크와 먼저 해 볼 작은 테스트
1. **[0 크레딧]** ACE-Step을 설치하고 후렴 40초만 8개 뽑아서 들려드립니다. 목소리·발음·리듬을 승인받습니다.
2. **[0 크레딧]** 승인된 전체 곡으로 이미지 없이 미리보기 영상을 만들어 템포감을 확인합니다.
3. **[12 크레딧]** 후렴 립싱크 클립 2개만 먼저 만들어, 노래의 긴 모음에 입 모양이 맞는지 확인합니다.

**리스크**
- 가수 목소리가 모모 목소리와 다릅니다.
- 후렴이 매번 조금씩 다르게 나와서, 1번째 후렴을 복사해 붙여야 합니다.
- 영어 가사를 틀리게 부를 수 있습니다. 자동으로 검사하고 틀리면 다시 뽑습니다.
- 맥 설치 과정에서 문제가 생길 수 있습니다.

**결정해 주실 것**
1. 주제 (비 오는 날 추천)
2. 새 형식 승인
3. 맥에 약 20GB 설치 승인
4. 밝은 여성 가수 목소리로 갈지, 대안으로 모모 목소리를 유지할지
5. 후렴 영상 일부를 반복해도 괜찮은지

참고: ffmpeg 는 세션 준비 단계(CLAUDE.md 세션 시작 절차)에서 `brew install ffmpeg` 로 설치했다 (/opt/homebrew/bin/ffmpeg).

---

## Appendix: technical plan (English, for the implementer)

### A. Evidence and corrections applied
- **ep02 pacing, verified** from the build timeline copy (`scratchpad/ep02_timeline.json`, built 2026-09-30T05:58Z):
  - 167.5 s and 24 cuts: 14 × 5 s, 9 × 10 s, 1 × 7.5 s.
  - 33 lines; voiced 101.6 s = 60.7%.
  - 4 inter-line gaps ≥ 3 s, the longest 3.98 s.
- **Verifier corrections folded in:**
  - MMS_FA dropped (CC-BY-NC weights).
  - The ACE-Step XL repetition workaround needs DCW off AND `audio_cover_strength=0`. DCW is on by default for turbo, and REST has no per-request DCW switch.
  - Do not set `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`.
  - ACE-Step scores below HeartMuLa on WSB musicality. It is chosen for licence, first-party Mac/MLX support, speed and bpm/key control, not for sound quality.
  - YuE2 is excluded: the HF weight repos still ship plain CC BY-NC.
  - Length must be ≥ 60 bars at 120 BPM (brief: 2–3 min).
  - The call-and-response wait gets its own non-frontal shot (ep02 c19 failure).
  - No library cheer/transition clips in sung bars; no 1-bar Ken Burns stills; no downbeat punch-in (the brief forbids zoom).
  - Raincoat is open-front and non-yellow, so both yellow buttons stay visible.
  - `genrec.clip_seconds` floors, so the planner writes `ceil`.
  - Every V cut must set `clip_model` and `clip_seconds`; otherwise it falls back to kling3_0_turbo 5 s.
  - V > 15 needs `notes.v_over_reason`.
  - `genrec.estimate` skips the `song_slots` music slot (`lang=None`).
- **ffmpeg** is installed at `/opt/homebrew/bin/ffmpeg` (brew, installed by the main session as part of CLAUDE.md session setup — not by the research agents).
- **YouTube:** `config.youtube.contains_synthetic_media` is `false`. YouTube's help page lists "AI generated music" as needing disclosure. Setting it to true is a config change and needs approval; consider editing ep02 in Studio too.

### B. Install (NOT executed; needs the user's approval, about 15–20 GB total)
```bash
# 1) Song model: ACE-Step 1.5 (requires-python >=3.11,<3.13 → use 3.12)
mkdir -p ~/ml && cd ~/ml
git clone https://github.com/ACE-Step/ACE-Step-1.5.git && cd ACE-Step-1.5
uv python install 3.12
uv sync --python 3.12
export ACESTEP_CHECKPOINTS_DIR=~/ml/ace-step-models        # add to ~/.zshrc
uv run acestep-download                                     # vae + Qwen3-Embedding-0.6B + v15-turbo + lm-1.7B (~10.1 GB)
uv run acestep-download --model acestep-5Hz-lm-0.6B         # ~1.4 GB
chmod +x start_gradio_ui_macos.sh start_api_server_macos.sh
# edit start_gradio_ui_macos.sh: CONFIG_PATH="--config_path acestep-v15-turbo"
#                                LM_MODEL_PATH="--lm_model_path acestep-5Hz-lm-0.6B"
./start_gradio_ui_macos.sh     # sets ACESTEP_LM_BACKEND=mlx, --backend mlx; UI at :7860. Turn Autoscore OFF (#1081 leak).
```
Confirm in the log that the MLX DiT/VAE path is active (MLX had 97 waveform discontinuities vs 3062 on PyTorch-MPS in a community test). Do not set `PYTORCH_MPS_HIGH_WATERMARK_RATIO`.

```bash
# 2) Analysis sidecar (outside the repo; never imported by momo/*.py; results enter manifest as JSON)
uv venv --python 3.12 ~/.venvs/momo-audio
uv pip install --python ~/.venvs/momo-audio/bin/python \
  "mlx==0.32.3" "mlx-audio-io==1.3.20" "demucs-mlx[convert]==1.4.14" "mlx-audio[stt]==0.5.7" \
  "torch==2.11.*" "torchaudio==2.11.*" soundfile "librosa>=1.0,<1.1"
~/.venvs/momo-audio/bin/python -m mlx_audio_io.doctor       # mlx-audio-io is sdist-only (C++/nanobind build); must match mlx 0.32.3
# If the demucs-mlx build fails, use PyTorch Demucs in its own throwaway env:
#   uvx --python 3.12 --from "demucs==4.1.0" demucs --two-stems vocals -n htdemucs_ft -d mps -o sep song.wav
```
A dry `uv pip compile` of this set resolved to 76 packages (mlx 0.32.3, torch/torchaudio 2.11.0, transformers 5.17.0). It has never actually been installed.

### C. Song generation (ACE-Step 1.5)
- **Models:**
  - Start with `acestep-v15-turbo` + `acestep-5Hz-lm-0.6B`, the safe choice for 24 GB.
  - A/B `lm-1.7B` if lyric adherence is weak.
  - XL-turbo only as a later A/B, with `dcw_enabled=False` and `audio_cover_strength=0` through the Python API or Gradio (not REST).
- **Settings:**
  - `bpm=120`, `keyscale="C Major"` (or G/D), `timesignature="4"`, `vocal_language="en"`
  - `inference_steps=8`, `shift=3.0` (turbo; guidance is auto-fixed to 1.0)
  - `thinking=True`, `lm_temperature≈0.7`
  - `batch_size=2` at first, fixed `seeds`, `audio_format="wav"`
  - Full song: `duration≈124`. Bake-off: `duration≈44` (intro + hook + V1 + C1).
- **Caption variants for the bake-off**, each with 4 seeds:
  - (a) `children's nursery rhyme, cheerful and bouncy, bright clear young female vocal, very clear English diction, ukulele strum, glockenspiel, light hand claps, soft kick, simple major-key sing-along melody`
  - (b) = (a) + `children's choir on the chorus`
  - (c) `sweet playful female vocal, preschool TV show song, ukulele, glockenspiel, claps`
- **Lyrics template.** Topic not yet approved; this is an illustration. Tags follow the docs: UPPERCASE = intensity, (parentheses) = backing vocals.
  ```
  [Intro - ukulele and claps]
  [Chorus - catchy, bouncy]
  Pitter-patter, pitter-patter,
  rain is falling down!
  [Verse 1]
  Blue raincoat, blue raincoat,
  on it goes, on it goes!
  Can you say "raincoat"?
  Raincoat! Hooray!
  [Chorus - catchy, bouncy]
  Pitter-patter, pitter-patter,
  rain is falling down!
  SPLISH! SPLASH! SPLISH! SPLASH!
  Let's play in the rain!
  [Verse 2]  Red rain boots, red rain boots, / stomp, stomp, stomp, stomp! / Can you say "boots"? / Boots! Hooray!
  [Chorus] …
  [Verse 3]  Big umbrella, big umbrella, / Ducky comes too! (Quack, quack!) / Can you say "umbrella"? / Umbrella! Hooray!
  [Bridge - shout along]  Raincoat! Boots! Umbrella! Hooray!
  [Chorus - final, bigger] …
  [Outro - instrumental, final chord]
  ```
  - Lines have 4–8 syllables with matching counts per position. This is shorter than the docs' 6–10 advice; unverified whether short lines get rushed.
  - Keep a sun-shower mood. SCARY_WORDS (storm, dark, night, thunder…) only warns on `image_prompt`, so check lyrics by hand.
- **Python API** (per docs/en/INFERENCE.md; the Mac `device` string is unverified, so copy what `start_api_server_macos.sh` passes):
  ```python
  from acestep.handler import AceStepHandler
  from acestep.llm_inference import LLMHandler
  from acestep.inference import GenerationParams, GenerationConfig, generate_music
  dit = AceStepHandler(); dit.initialize_service(project_root=".", config_path="acestep-v15-turbo", device="mps")
  lm = LLMHandler(); lm.initialize(checkpoint_dir=CKPT, lm_model_path="acestep-5Hz-lm-0.6B", backend="mlx", device="mps")
  p = GenerationParams(caption=CAP, lyrics=LYR, vocal_language="en", bpm=120, keyscale="C Major",
                       timesignature="4", duration=124, inference_steps=8, shift=3.0, lm_temperature=0.7)
  c = GenerationConfig(batch_size=2, use_random_seed=False, seeds=[11, 22], audio_format="wav")
  r = generate_music(dit, lm, p, c, save_dir="~/ml/momo_ep03/takes")
  ```
- **Fixing one line:** `task_type="repaint"`, `src_audio=<take>`, `repainting_start/end` on bar boundaries.
- **Call-and-response wait bar:** the model may sing or fill through it (unverified). The fix is to use the stems sum with the vocal stem muted in that bar, crossfaded into the original mix at the downbeats.
- **Provenance:** record tool, DiT, LM, seed, params and sha1 in `song.track`, with credits 0. Host the mix and the vocal stem on momo-previews, the same raw-URL pattern PRODUCTION (8).6 uses for nar refs, so `fetch_assets.py` can restore them. Unverified that fetch_assets accepts that URL, but it downloads by URL.

### D. Post-processing
1. **Grid:**
   - `ffmpeg -i take.wav -ar 44100 -ac 2 song.wav`
   - Run `momolib.audio.detect_beats(instrumental.wav, bpm_hint=120)` (4/4 only, constant tempo).
   - Drift check in the sidecar: `librosa.beat.beat_track` on the instrumental, fit a linear grid; require median residual < 25 ms and max < 60 ms.
   - Set `song.bpm = analysis.bpm` with no time-stretch. Do not use `song_music()`: it applies atempo and drops audio before downbeat0, cutting pickups.
2. **Chorus lock** (needed to reuse lip-sync takes):
   - Copy the C1 mix onto the C2 bars and its first 4 bars onto the hook.
   - Use 15 ms equal-power crossfades at downbeats; C3 is left as sung.
   - Listen to every seam.
   - Then re-run separation on the locked mix.
3. **Separation:**
   - `~/.venvs/momo-audio/bin/demucs-mlx -n htdemucs_ft -o sep song.wav` produces vocals, drums, bass and other. CLI flags are from the README, unverified locally.
   - Instrumental = drums + bass + other.
4. **Lyric QA:**
   - `python -m mlx_audio.stt.generate --model mlx-community/Qwen3-ASR-1.7B-8bit --audio sep/song/vocals.wav --language English --output-path qa`
   - Diff against the lyrics with difflib; re-roll or repaint any missing or garbled line.
5. **Word timing:** per 2-bar window (±1 beat margin), never the whole song at once, because repetition breaks whole-song alignment.
   - Primary: Qwen3-ForcedAligner-0.6B-8bit (Apache-2.0):
     `python -m mlx_audio.stt.generate --model mlx-community/Qwen3-ForcedAligner-0.6B-8bit --audio win.wav --text "<line>" --language English --output-path align`
   - Cross-check: `torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H` (MIT) + `torchaudio.functional.forced_align` / `merge_tokens`, with audio loaded by soundfile. Flag words where the two disagree by more than 120 ms.
   - For the first song, run the aligners on BOTH the stem and the mix; one sung-lyrics study found separated vocals made alignment worse.
   - Snap word starts to `librosa.onset.onset_detect(vocals, backtrack=True)` within ±60 ms.
   - ACE-Step's LRC output is a third, line-level opinion.
6. **Lip-sync driver refs:** a slice of the vocal stem exactly the cut window (2 or 4 s), gated with `clean_speech` at about −35 to −40 dBFS. `wan2_7 clip_seconds = ceil(window)`.

### E. Cut sheet: 61 bars @ 120 BPM = 122 s, 38 cuts, mean 3.21 s
| Section | Bars | Cuts (bars) | New generations |
|---|---|---|---|
| Intro | 1–2 | L intro_wave (2), spoken line on beat 2 | 0 |
| Hook | 3–6 | LS-cA↺ (2) · RAIN↺ hflip (2) | 0 |
| V1 / V2 / V3 (Ducky) | 8 each | LS-a (2) · ACT side/wide (2) · LS-call (1) · OBJ+card, the wait bar (1) · LS-ans (2, reuses LS-a's image) | each: 4 img, LS 4+2+4 s, MO 4+4 s |
| C1 | 15–22 | LS-cA (2) · RAIN (2) · HOP (1) · SPLASH (1) · LS-cB (2) | 5 img, LS 8 s, MO 12 s |
| C2 | 31–38 | LS-cA↺ · RAIN↺ · HIT2 (1) · SPLASH↺ second half (1) · LS-cB↺ | 1 img, MO 4 s |
| Bridge (review) | 47–50 | OBJ1↺ · OBJ2↺ · OBJ3↺ (second halves, with cards) · CHEER wide, 1 bar each | 1 img, MO 4 s |
| C3 | 51–58 | LS-cA3 (2, new angle with Ducky) · RAIN↺ · HIT3 (1) · SPLASH↺ · LS-cB3 (2) | 3 img, LS 8 s, MO 4 s |
| Outro | 59–61 | L outro_bye (3; 5 s clip held at 1.2×, within SLOW_MAX 1.25) | 0 |

- **Shot rules:**
  - Cut only on downbeats; minimum 1 bar.
  - While vocals are audible, a shot lasts at most 2 bars (L cuts exempt).
  - At most 4 one-bar shots in a row; only the bridge reaches 4.
  - A frontal or 3/4 Momo at medium shot or closer during vocals must be a lip-sync (LS) cut. Everything else is wide, side, back or an object.
  - Each 4 s seedance clip is used as two different 1-bar moments (split pair).
- **Resulting stats:**
  - LS screen share 48%.
  - Voiced share ≈ 89% (estimate).
  - First hook at 0:04.
  - Every V cut: seedance_2_0_mini 4 s or wan2_7 2/4 s, set explicitly.

### F. Credit arithmetic
- **Unit prices (config.higgsfield.unit_costs):** image 2, wan2_7 1.5/s, seedance_2_0_mini 1.0/s.
- **Base cost:**
  - Images: 22 × 2 = **44**
  - wan2_7: (3 × 10 s + 8 + 8) = 46 s × 1.5 = **69**
  - seedance: (3 × 8 + 12 + 4 + 4 + 4) = 48 s × 1.0 = **48**
  - Audio: 0 (local song; approved library intro/outro audio)
  - **Base = 161**
- **With rerolls:**
  - `estimate_credits.py` default ×1.2 → 193.2.
  - ep02-observed reroll rates (images 41%, LS 36%, MO 0–20%) → 203.9–213.5.
- **Adders:**
  - +9 if wan2_7 bills 2 s as 4 s (a 2 s clip has never been billed).
  - +7.9 if the song must fall back to sonilo. Higgsfield's tool text marks sonilo "game pipeline only / not for standalone audio", so prefer ACE `instrumental=True` or `make_music.py` instead.
  - Worst case ≈ 230.4, under the 250 cap. The base already exceeds config `estimate_later_episode` [120, 160].
- **Variants:**
  - Saver: C3 reuses C1's LS clips (−16) and the LS-call start images become local crops of LS-a's 2k still (−6, output size unverified) → **139** (×1.2 = 166.8).
  - No chorus lock: C2 needs a new LS pair → 177.
- **Before any generation:**
  - `clip_from` reuse must exist in genrec and the estimator. Otherwise the estimator counts every V cut as its own image + clip and likely exits 2.
  - Run free `get_cost` checks for seedance 4 s and wan2_7 2 s. wan2_7 4 s is already known at 6.0 (ep02 c06).

### G. Code and manifest changes (then run `bash momo/tests/run_all.sh`)
- **manifest `song`:**
  - `mode:"track"|"lines"`
  - `track` and `vocals` (GenRec with `local:true`, tool, model, seed, params, sha1)
  - `analysis` (+ `drift_ms`), `bar0`, `sections[]`, `lock[]`
  - `lyrics[{bar, text, call, words:[[w, t0, t1]]}]`
  - `align{method, vocals_sha1, at}`
- **Cut fields:** `clip_from:{cut, in, hflip}`, `card.at_word`, `sfx[].beat`.
- **config:** a `song_rules` block (bpm [116, 124], bars [60, 68], cuts [34, 46], cut_bars_max_sung 2, max_1bar_run 4, sung_share_min 0.8, max_gap_beats 4, lipsync_share [0.4, 0.65]). Config change, so it needs approval.
- **momolib/episode.py:**
  - New `song_mode`, `track_lines`, `lines_in_span`, `take_span`, `pacing_stats`.
  - `plan_timeline` track branch: no TTS lookup except L library audio; per-cut word times; resolve `clip_from` into `CutPlan.src_in` / `sync_src` / `hflip`; resolve `at_word` / `beat`.
  - `validate_manifest`:
    - Track mode requires track, vocals and word times.
    - Error if |bpm − analysis.bpm| > 0.3.
    - Check that the `clip_from` target exists and that the lyric window matches.
    - Exempt `clip_from` cuts from the prompt checks and the V-count check.
    - Apply `song_rules` instead of `plan_rules`.
    - The keyword-repeat check reads `song.lyrics`.
- **momolib/audio.py:**
  - New `song_track()` (bar0 → t = 0, no atempo, 0.5 s tail fade), `track_slice()` (gated LS driver), `lock_sections()` (crossfaded splice).
  - `build_mix` gets a track branch.
  - `build_narration` places only L library lines in track mode.
- **momolib/render.py:**
  - `LyricLine(..., word_times=None)` with `lit_at(t)` and a word bounce (1.0 → 1.12 → 1.0 over about 6 frames).
  - `render_song_overlay` takes word times and card `at_word`, plus a 2% card breathe on downbeats.
  - No punch-in.
  - If S cuts are ever used, scale `kenburns_params` zoom by duration.
- **build.py:**
  - `make_segs`: fix the duplicate `"card"` key (rename the second to `"placeholder_card"`); add src_in, hflip, sync_src and word times to the hash; bump `SEG_VERSION = 3`.
  - `render_seg`: `-ss src_in` (hold frame 0 when negative); apply the lip-sync no-stretch rule when `sync_src`; `hflip` filter.
  - `write_timeline`: add a `pacing` block.
- **momolib/genrec.py:**
  - `cut_slots` returns [] for `clip_from` cuts.
  - `song_slots` adds track and vocals slots.
  - `estimate()` includes the `lang=None` music slot.
  - Local records do not increment `credits.generations`.
- **hf_jobs.py:**
  - `cmd_record --song-track/--song-vocals --local --url`.
  - `clip_links` and `cmd_narref` get a track branch (nar_ref = {media_id, track sha1, span}; today they block on `nar_jobs`).
- **preview_assets.py:** `narration_refs` track branch using `track_slice`.
- **New `momo/song_track.py`** (numpy + ffmpeg only; argparse, `add_root_arg`, `main_wrapper`), subcommands `analyze | lock | words --from-json | refs | check`.
- **validate_manifest.py:** `render_plan` gets a song table.
- **Docs:** MANIFEST §7-C; PRODUCTION (9) with the gates in section H.
- **Tests:** `test_track_timeline`, `test_clip_from_sync`, `test_overlay_word_times`, `test_pacing_stats`, `test_validate_song_rules`, `test_lock_sections`, `test_track_build`.
- **Manifest notes:**
  - `notes.v_over_reason` (36 V cuts).
  - `notes.approvals` for the brief deviations: chant → sung (brief 4단계 "[chant]"), 22–28 → 38 cuts, S 0 and L 2 (both warnings).

### H. Gate order
0. [승인] Topic, new format, local install.
1. Install, then the chorus bake-off (0 credits). [승인] voice, diction, groove.
2. Full-song takes → pick → lock → separate → QA → align. [승인] song audio.
3. Code changes and tests.
4. Manifest and plan.md. [승인] plan; commit and push.
5. Animatic with `build.py --allow-missing` (0 credits). [승인]
6. `estimate_credits.py` must pass (exit 0). Pilot the C1 LS-cA and LS-cB clips (12 credits). [승인]
7. Remaining images → LS clips → B-roll, per the runbook groups. Record every Higgsfield job immediately.
8. Final build; upload with synthetic-media disclosure on.

### I. Fallback B1 (if ACE-Step vocals are rejected): Gracie TTS → singing
- Per line, generate a slightly slow seed_audio line.
- Word timing from the aligner, then a voiced-vowel heuristic.
- WORLD analysis with `pyworld-prebuilt` (MIT; arm64 wheels cp39–cp315, so 3.12 or 3.14 both work).
- Replace F0 with the score's notes plus Saitou-2007 overshoot, preparation and vibrato (ω=0.0345 rad/ms, k=0.0018). Stretch only the vowels onto note onsets. Add a light double and reverb.
- Instrumental from ACE `instrumental=True`, or a score-driven extension of `momo/make_music.py` so the key and chords are known exactly. Melody in major pentatonic.
- About 1.5–3 days of work. Prototype on ep02 lines (`fetch_assets.py --ep ep02`) at 0 credits.
- DiffSinger/OpenUtau is not recommended: every usable vocoder is CC BY-NC-SA, and it is a different voice.

### J. Unverified or estimated
- ACE-Step speed on the M5 Pro (1–2 min per 2-min take is extrapolated from M4 Pro/M1 Max reports).
- Child-like timbre.
- Short-line behaviour and whether the model leaves a rest bar.
- Mac `device` string for the Python API.
- The mlx-audio CLI flags and the demucs-mlx CLI name.
- demucs-mlx build success.
- Aligner accuracy on AI-sung vocals.
- Whether chorus splice seams are audible.
- wan2_7 lip-sync on sustained sung vowels, and 2 s billing.
- Whether momo-previews raw URLs work with fetch_assets.
- The 2k still size for local crops.
- Whether 120 BPM and 3.2 s mean cuts suit ages 2–5; external benchmarks were never measured, and `sample_videos.py` from a home IP could check them.
