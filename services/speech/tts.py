"""edge-tts synthesis with word-level timings.

edge-tts emits WordBoundary events during synthesis, which give start time and
duration per token for free. Those timings drive three things at once: caption
highlighting, slide element build-up, and avatar visemes.

Devanagari is the reason `align_to_words()` exists. The service tokenises Hindi
by orthographic cluster, so a single written word can produce several boundary
events. Cue timing must key off real script words, so boundary events are merged
back onto the words of the script by walking both in order.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, asdict
from pathlib import Path

import edge_tts
import yaml

VOICES_PATH = Path(__file__).with_name("voices.yaml")
AUDIO_DIR = Path("storage/audio")

_TICKS_PER_MS = 10_000  # edge-tts reports offsets in 100-nanosecond ticks


@dataclass
class WordTiming:
    word: str
    index: int          # index into script.split()
    start_ms: int
    duration_ms: int

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms

    def to_dict(self) -> dict:
        return asdict(self)


def _voices() -> dict:
    return yaml.safe_load(VOICES_PATH.read_text(encoding="utf-8"))["languages"]


def voice_for(language: str) -> str:
    cfg = _voices()
    entry = cfg.get(language) or cfg["en-IN"]
    return entry["voice"]


def _norm(s: str) -> str:
    """Strip punctuation and marks so a boundary token can match a script word."""
    return re.sub(r"[^\wऀ-ॿ]+", "", s).lower()


def align_to_words(script: str, boundaries: list[dict]) -> list[WordTiming]:
    """Merge raw boundary events onto the whitespace words of `script`.

    Three cases have to survive here:
      - one event per word, the common case;
      - a word split across several events, which Devanagari can do;
      - a script token that is never spoken and so gets no event at all, such as
        the "=" in "V = W/Q". These must still be emitted and must not desync
        every following word.
    """
    words = script.split()
    norm_words = [_norm(w) for w in words]
    out: list[WordTiming] = []

    wi = 0
    acc = ""
    start_ms: int | None = None
    end_ms = 0

    def flush_silent(at_ms: int) -> None:
        """Emit unspoken tokens (punctuation, symbols) at the current position."""
        nonlocal wi
        while wi < len(words) and not norm_words[wi]:
            out.append(WordTiming(words[wi], wi, at_ms, 0))
            wi += 1

    for b in boundaries:
        tok = _norm(b["text"])
        if not tok:
            continue
        b_start = b["offset"] // _TICKS_PER_MS
        b_end = (b["offset"] + b["duration"]) // _TICKS_PER_MS

        flush_silent(b_start)
        if wi >= len(words):
            break

        if start_ms is None:
            start_ms = b_start
        end_ms = b_end
        acc += tok

        while wi < len(words) and norm_words[wi] and acc.startswith(norm_words[wi]):
            out.append(WordTiming(words[wi], wi, start_ms, max(0, end_ms - start_ms)))
            acc = acc[len(norm_words[wi]):]
            wi += 1
            flush_silent(end_ms)
            if acc:
                start_ms = end_ms
        if not acc:
            start_ms = None
        elif len(acc) > 40:
            # Desynced beyond recovery: drop the accumulator rather than let one
            # bad token silently zero every remaining cue.
            acc = ""
            start_ms = None

    flush_silent(end_ms)
    for i in range(len(out), len(words)):
        out.append(WordTiming(words[i], i, end_ms, 0))
    return out


async def _synthesize(text: str, voice: str, out_path: Path) -> list[dict]:
    # edge-tts 7.x defaults to SentenceBoundary. Word boundaries are opt-in, and
    # without this the stream yields one event per sentence and every cue
    # collapses to 0 ms.
    comm = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    boundaries: list[dict] = []
    with out_path.open("wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append({
                    "text": chunk["text"],
                    "offset": chunk["offset"],
                    "duration": chunk["duration"],
                })
    return boundaries


def _run(coro):
    """asyncio.run() refuses to nest, and Playwright's sync API already owns a
    loop. Fall back to a worker thread so speak() is callable from anywhere."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def speak(text: str, language: str = "en-IN", *, cache: bool = True) -> tuple[Path, list[WordTiming]]:
    """Synthesize `text`, returning the mp3 path and per-word timings."""
    voice = voice_for(language)
    key = hashlib.sha256(f"{voice}|{text}".encode("utf-8")).hexdigest()[:16]
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    mp3 = AUDIO_DIR / f"{key}.mp3"
    raw = AUDIO_DIR / f"{key}.boundaries.json"

    if cache and mp3.exists() and raw.exists():
        import json
        boundaries = json.loads(raw.read_text(encoding="utf-8"))
    else:
        boundaries = _run(_synthesize(text, voice, mp3))
        import json
        raw.write_text(json.dumps(boundaries), encoding="utf-8")

    return mp3, align_to_words(text, boundaries)


def audio_duration_ms(path: Path) -> int:
    """Container duration via ffprobe, the ground truth for drift measurement."""
    import subprocess

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return int(float(r.stdout.strip()) * 1000)
