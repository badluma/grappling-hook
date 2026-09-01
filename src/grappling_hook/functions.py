"""Helpers: boot banner, episode detection, search, spinner, opening magnets."""

import contextlib
import shutil
import subprocess
import sys
import threading
import time

from thepiratebay_api import TorrentClient
from thepiratebay_api.models import BriefTorrent

LOGO = """    ______
    \\ \\ \\ \\
<‾\\ /_/_/_/
 \\(____|___/)
  \\________/"""

WAVE = "~-_.,.,_-~~-_.,.,_-~~"



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


def is_episode(name: str) -> bool:
    lowered = name.lower()
    for i in range(len(lowered) - 5):
        w = lowered[i : i + 6]
        if w[0] == "s" and w[3] == "e" and w[1].isdigit() and w[2].isdigit() and w[4].isdigit() and w[5].isdigit():
            return True
    return False


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
            print(f"\r{self._frames[i % len(self._frames)]} {self._message}", end="", flush=True)
            i += 1
            time.sleep(0.1)

    def start(self) -> "Spinner":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join()
        print("\r\x1b[2K", end="")  # clear spinner line


def open_that(uri: str) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", uri], check=True)
    elif sys.platform.startswith("win"):
        import os

        os.startfile(uri)  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", uri], check=True)
