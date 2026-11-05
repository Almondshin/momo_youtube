# Song keyword captions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the approved ep12 song with one fruit keyword per cut while retaining its full audio and timing.

**Architecture:** Add optional `song.caption_mode` (`lyrics` default, `keywords` opt-in). Timeline planning keeps all audio/timing calculations and song lyric data, then selects keyword-only visual overlays. Reuse the existing keyword renderer.

**Tech Stack:** Python 3.10+, existing Pillow/numpy/ffmpeg pipeline; no production dependencies added.

**Spec:** `momo/episodes/ep12/VISUAL_PLAN.md`, approved by user 2026-11-05.

## Global Constraints

- Work in `momo/`; retain the current production branch and assets.
- No changes to approved library assets, voices, song audio, or lyric alignment.
- No full lyric lines or auxiliary card text in keyword mode; an absent keyword means no caption.
- Default mode preserves existing song behavior; invalid modes are validation errors.
- Run `bash momo/tests/run_all.sh` using `.venv/bin/python`; test runner's own isolated temporary fixture is allowed by its existing safety guard.

## Review Focus

- Existing songs without the field retain karaoke and cards.
- Empty keyword cuts show no text.
- Keyword mode does not expose old `card.text` alongside the keyword.
- English/Korean keyword selection follows the render language.
- Caption selection never changes the audio, cut boundaries, or stored aligned lyrics.

### Task 1: Add and verify caption selection

**Files:** `momo/momolib/episode.py`, `momo/tests/test_song.py`, `momo/docs/MANIFEST.md`.
**Interfaces:** `validate_manifest(cfg, manifest)` validates `song.caption_mode`; `plan_timeline(paths, cfg, manifest, lang, allow_missing)` sets `CutPlan.keyword`, `lyrics`, and `card` without altering audio fields.

- [x] Write `test_track_keyword_captions` using existing track fixtures: literal keyword list ['', 'APPLE', 'BANANA', '']; empty visual lyrics/cards; literal boundaries 0/4.5/6.5/8.5/13; full source lyrics unchanged; Korean keywords selected; default karaoke/card retained.
- [x] Write `test_song_caption_mode_validation`: accept absent/lyrics/keywords; reject unknown/string typo/non-string modes.
- [x] Run these two tests before the change. Expected: keyword test and validation test fail for missing behavior.
- [x] Add the minimal validation/overlay selection and field documentation.
- [x] Run the two tests, then the whole repository test script. Expected: all checks pass.
- [x] Enable keywords in ep12, inspect its real timeline: 90 seconds, no full lyric/card overlays, only APPLE/BANANA or blank; source lyrics unchanged.
- [ ] Commit code/docs/tests, request one independent final code review under executing-plans, and resolve material findings before production render.

## Execution ledger

- Pre-flight: one task; no shared task interfaces. User approved production and keyword-only captions; no additional implementation-method question is needed.
- Ruling: use existing non-main production branch in place; a separate worktree would split ongoing media records. Keep all authored files in momo/.
- Ruling: plan/ledger remain in this file rather than a root .superpowers directory, honoring the user's momo-only requirement.
- Baseline attempt with a fixture inside momo/out was rejected by the fixture safety guard; rerunning the unchanged test script with its default temporary directory. No code failure was involved.

- Baseline default-run result: 18 PASS / 0 FAIL / 0 WARN.
- RED: both new behavior tests failed before implementation (missing keyword output; invalid mode accepted).
- GREEN: both passed after minimal implementation.
- Full verification: `PYTHON=.venv/bin/python bash momo/tests/run_all.sh` → 18 PASS / 0 FAIL / 0 WARN (audio/test-keyword-captions.log).
- ep12 timeline: 90 seconds / 35 cuts; only blank, APPLE, BANANA; 0 full lyric/card/speech overlays; all 42 aligned lyric lines retained.
- Ruling: ran the required full suite directly and retained its evidence rather than re-running it through task-done; developer instructions prohibit repeating passing checks without a new concern.
