import contextlib
import os
import re
import shutil
import subprocess
import sys
import threading
import time

import inquirer

from thepiratebay_api import TorrentClient
from thepiratebay_api.models import BriefTorrent

LOGO = """    ______
    \\ \\ \\ \\
<‾\\ /_/_/_/
 \\(____|___/)
  \\________/"""

WAVE = "~-_.,.,_-~~-_.,.,_-~~"

# "Show.S01E02.mkv" and the "S01E002" aniworld writes
EPISODE = re.compile(r"[Ss](\d{1,3})[Ee](\d{1,3})")

VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".m4v", ".mov", ".ts", ".webm")

# Colors
GRAY = "\x1b[90m"
RESET = "\x1b[0m"



def boot() -> None:
    width = shutil.get_terminal_size(fallback=(20, 20)).columns
    wave_len = max(width - 4, 0)
    wave = (WAVE * (wave_len // len(WAVE) + 1))[:wave_len]
    print(f"{LOGO}\n  {wave}  \n")


@contextlib.contextmanager
def hidden_cursor():
    print("\x1b[?25l", end="", flush=True)
    try:
        yield
    finally:
        print("\x1b[?25h", end="", flush=True)


@contextlib.contextmanager
def visible_beam_cursor():
    print("\x1b[6 q\x1b[?25h", end="", flush=True)  # steady bar (beam) cursor, shown
    try:
        yield
    finally:
        print("\x1b[?25l\x1b[0 q", end="", flush=True)  # hide, reset shape to default


def episode_code(name: str) -> tuple[int, int] | None:
    match = EPISODE.search(name)
    return (int(match[1]), int(match[2])) if match else None


def is_episode(name: str) -> bool:
    return episode_code(name) is not None


def search_category(client: TorrentClient, query: str, category: int) -> list[BriefTorrent]:
    return client.search(query, category=category).torrents


class Spinner:
    def __init__(self, message: str):
        self._message = message
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        n = len(WAVE)
        self._frames = ["".join(WAVE[(i + j) % n] for j in range(11)) for i in range(n)]

    def _run(self) -> None:
        i = 0
        while not self._stop.is_set():
            print(f"\r{self._frames[i % len(self._frames)]} {self._message}\x1b[K", end="", flush=True)  # clear what a longer message left behind
            i += 1
            time.sleep(0.1)

    def set_message(self, message: str) -> None:
        self._message = message

    def start(self) -> "Spinner":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join()
        print("\r\x1b[2K", end="")  # clear spinner line

    def __enter__(self) -> "Spinner":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()


def walk_files(path: str) -> list[str]:
    return [os.path.join(root, f) for root, _, files in os.walk(path) for f in files]


def video_files(paths: list[str]) -> list[str]:
    return [p for p in paths if p.lower().endswith(VIDEO_EXTENSIONS) and "sample" not in os.path.basename(p).lower()]


def match_episodes(torrents: list[str], dubs: list[str]) -> list[list[str | None]]:
    """Pair every torrent episode with the dub episode sharing its SxxExx code."""

    torrents = video_files(torrents)
    dubs = video_files(dubs)

    # A dub folder holds one episode per code, so the code is enough to look them up
    by_code = {}
    for dub in dubs:
        code = episode_code(os.path.basename(dub))
        if code and code not in by_code:
            by_code[code] = dub

    # Movies have no episode codes, so there is only the one file to pair up
    if len(torrents) == 1 and len(dubs) == 1 and not episode_code(os.path.basename(torrents[0])):
        return [[torrents[0], dubs[0]]]

    matches = []
    for torrent in sorted(torrents):
        code = episode_code(os.path.basename(torrent))
        matches.append([torrent, by_code.get(code)])

    return matches


def print_matches(matches: list[list[str | None]]) -> None:
    print("Matches:")
    for i, (torrent, dub) in enumerate(matches):
        last = i == len(matches) - 1
        print(f"{'└──' if last else '├──'} {os.path.basename(torrent)}")
        name = os.path.basename(dub) if dub else "no dub"
        print(f"{'   ' if last else '│  '} └── {GRAY}{name}{RESET}")
    print()


def pick_matches(matches: list[list[str | None]], dubs: list[str], render) -> list[list[str | None]]:
    """Let the user replace the guessed dub of every episode by hand."""

    choices = [(os.path.basename(d), d) for d in sorted(video_files(dubs))] + [("None", None)]

    picked = []
    for torrent, dub in matches:
        code = episode_code(os.path.basename(torrent))
        label = f"S{code[0]:02d}E{code[1]:02d}:" if code else "Episode:"
        picked.append([torrent, inquirer.list_input(
            label.ljust(11), choices=choices, default=dub, render=render
        )])

    return picked


def duration(path: str) -> float:
    """Container duration in seconds, 0.0 if ffprobe cannot read it."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        stdin=subprocess.DEVNULL, capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:  # unreadable or truncated beyond repair
        return 0.0


def check_dubs(pairs: list[tuple[str, str]]) -> None:
    """Refuse to merge dubs that are shorter than their video, i.e. cut off mid-download."""

    short = []
    with Spinner("Checking dubs...") as spinner:
        for video, dub in pairs:
            spinner.set_message(f"Checking {os.path.basename(dub)}...")
            video_len, dub_len = duration(video), duration(dub)
            # ponytail: 90% of the video length, dubs legitimately differ by intros/outros
            if video_len and dub_len < video_len * 0.9:
                short.append(f"{os.path.basename(dub)} ({dub_len / 60:.1f} of {video_len / 60:.1f} min)")

    if short:
        raise RuntimeError("Incomplete dub, delete it and download it again:\n  " + "\n  ".join(short))


def ffmpeg_error(stderr: str) -> str:
    # ffmpeg ends on "Conversion failed!", the reason sits in the lines above it
    lines = [l for l in stderr.strip().splitlines() if l.strip()]
    return "\n".join(lines[-5:]) if lines else "ffmpeg failed"


def merge_audio(matches: list[list[str | None]], offset: float = 0.0) -> None:
    """Mux the dub audio into the torrent video as the default audio track.

    offset shifts the dub in seconds, positive delays it, negative pulls it forward.
    Dub and torrent are different rips, so their zero points rarely line up exactly.
    """

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is not installed")

    pairs = [(v, d) for v, d in matches if d]
    if not pairs:
        return

    check_dubs(pairs)

    with Spinner("Merging...") as spinner:
        for video, dub in pairs:
            spinner.set_message(f"Merging {os.path.basename(video)}...")

            # Everything has to end up in a matroska container to survive the copy
            base = os.path.splitext(video)[0]
            temp = f"{base}.merging.mkv"

            # mp4 subtitles (mov_text) cannot be copied into matroska, so convert
            # them, and drop them if even that fails (bitmap subs have no text form)
            # ponytail: dub subs (1:s) are untagged, players show them as "Undetermined";
            # tag them if that ever matters, the stream count of 0:s makes indexing fiddly
            keep = ["-map", "0:s?", "-map", "1:s?"]
            for subtitles in (keep, keep + ["-c:s", "srt"], []):
                result = subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", video,
                        # -itsoffset only applies to the input that follows it
                        *(["-itsoffset", str(offset)] if offset else []), "-i", dub,
                        "-map", "0:v", "-map", "1:a", "-map", "0:a?",
                        "-c", "copy", "-metadata:s:a:0", "title=Dub",
                        # the source flags its own audio default, so clear every
                        # flag first, else players keep playing the original
                        "-disposition:a", "0", "-disposition:a:0", "default",
                        *subtitles, temp,
                    ],
                    stdin=subprocess.DEVNULL, capture_output=True, text=True,
                )
                if result.returncode == 0:
                    break
                os.path.exists(temp) and os.remove(temp)
            else:
                raise RuntimeError(ffmpeg_error(result.stderr))

            os.replace(temp, f"{base}.mkv")
            if video != f"{base}.mkv":
                os.remove(video)

    print("\r\x1b[2KMerge complete!")


def quit_now(code: int) -> None:
    # ponytail: os._exit skips interpreter shutdown, so no waiting on daemon
    # threads and no second Ctrl+C interrupting finalization ("Exception
    # ignored in ... WeakSet._remove"). Cleanup runs in the finally blocks.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


if __name__ == "__main__":
    assert episode_code("Show.S01E02.1080p.mkv") == (1, 2)
    assert episode_code("Show S01E002.mp4") == (1, 2)
    assert episode_code("Show.2160p.mkv") is None
    assert is_episode("Show.S01E02.mkv") and not is_episode("Show 2019 1080p")
    assert match_episodes(
        ["/t/Show.S01E02.mkv", "/t/Show.S01E01.mkv", "/t/sample.mkv", "/t/info.nfo"],
        ["/d/Show S01E001.mp4", "/d/Show S01E003.mp4"],
    ) == [["/t/Show.S01E01.mkv", "/d/Show S01E001.mp4"], ["/t/Show.S01E02.mkv", None]]
    assert match_episodes(["/t/Movie.mkv"], ["/d/Movie.mp4"]) == [["/t/Movie.mkv", "/d/Movie.mp4"]]
    assert ffmpeg_error("x\n\nSubtitle codec 94213 (mov_text) is not supported\nConversion failed!\n") == (
        "x\nSubtitle codec 94213 (mov_text) is not supported\nConversion failed!")
    assert ffmpeg_error("   ") == "ffmpeg failed"
    assert duration("/does/not/exist.mkv") == 0.0
    print_matches(match_episodes(["/t/Show.S01E01.mkv", "/t/Show.S01E02.mkv"], ["/d/Show S01E001.mp4"]))
