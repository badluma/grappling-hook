from .data import data
from .functions import Spinner, walk_files

import libtorrent as lt
import os
import pty
import re
import signal
import time
import subprocess
import ast
import inquirer
from os.path import expanduser, expandvars
from inquirer.themes import term

SAVE_PATH = expanduser(expandvars(data["save_path"]))

# Aniworld gets its own folder so its files are not mixed into the torrent's
DUB_PATH = os.path.join(SAVE_PATH, ".dub")

# "Show S01E001 - [####------]  42.0% | 00:11:39 | 19.9x" and "Show S01E001 - [ 42%] 12.3/45.6 MB"
PROGRESS = re.compile(r"(\S+) - \[.*?([\d.]+)\s*%")

def download_torrent(magnet: str, status: dict | None = None) -> tuple[str, list[str]]:

    status = status if status is not None else {}

    session = lt.session()
    session.listen_on(6881, 6891)

    params = {
        "save_path": SAVE_PATH,
        "storage_mode": lt.storage_mode_t.storage_mode_sparse,
    }

    handle = lt.add_magnet_uri(session, magnet, params)

    try:
        with Spinner("Downloading metadata...") as spinner:
            while not handle.has_metadata():
                spinner.set_message(f"Downloading metadata...{dub_progress(status)}")
                time.sleep(0.1)

        with Spinner("Downloading files...") as spinner:
            while handle.status().state != lt.torrent_status.seeding:
                torrent = handle.status()
                spinner.set_message(f"Downloading files... {term.bright_black}({torrent.progress * 100:.2f}% down, rate: {torrent.download_rate / 1000000:.2f} MB/s, peers: {torrent.num_peers}){term.normal}{dub_progress(status)}")
                time.sleep(0.1)

            # The torrent is done, so only the dub is left to wait for
            while status.get("dub"):
                spinner.set_message(f"Downloading dub... {term.bright_black}({status['dub']}){term.normal}")
                time.sleep(0.1)
    finally:
        stop_dub(status)

    if status.get("failed"):
        print("Dub download failed!")
    print("\r\x1b[2KDownload complete!")

    # The torrent names its own root folder, everything it holds hangs off it
    torrent = handle.torrent_file()
    files = torrent.files()
    return (
        os.path.join(SAVE_PATH, torrent.name()),
        [os.path.join(SAVE_PATH, files.file_path(i)) for i in range(files.num_files())],
    )

def dub_progress(status: dict) -> str:
    return f" {term.bright_black}(dub: {status['dub']}){term.normal}" if status.get("dub") else ""

def download_dub(urls: list[str], status: dict):

    args = [data["aniworld_path"], "--no-menu", "--action", "Download", "--language", data["language"], "--output", DUB_PATH, *urls]

    # Aniworld only prints its progress when stderr is a terminal, so give it one
    master, slave = pty.openpty()
    process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=slave, text=True, start_new_session=True)
    os.close(slave)
    status["process"] = process

    # Read the progress aniworld writes while it downloads
    with os.fdopen(master, errors="replace") as output:
        try:
            for line in output:
                match = PROGRESS.search(line)
                if match:
                    status["dub"] = f"{match[1]} {float(match[2]):.2f}%"
        except OSError:  # The terminal closes once aniworld is gone
            pass

    status["failed"] = process.wait() != 0
    status["files"] = dub_files()
    status["dub"] = None


def dub_files() -> list[str]:
    return walk_files(DUB_PATH)

def stop_dub(status: dict):

    # Aniworld is its own process group, so Ctrl+C does not leave it downloading
    process = status.get("process")
    if process and process.poll() is None:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

def search_aniworld(query: str, category: str):

    aniworld = data["aniworld_path"]

    args = [aniworld, "--raw-search", query]
    if category == "show":
        args.append("--use-sto-search")

    with Spinner("Searching dubs..."):
        raw = run_aniworld(args)

    result = []
    for item in raw:
        result.append(
            (f"{item['title']} {term.bright_black}({item['url']}){term.normal}", item['url'])
        )

    return result

def get_info(url: str):

    with Spinner("Collecting info..."):
        return run_aniworld([data["aniworld_path"], "--raw-info", url])

def run_aniworld(args: list[str]):

    result = subprocess.run(args, capture_output=True, text=True)
    if not result.stdout.strip():
        raise RuntimeError(result.stderr.strip() or "Aniworld returned nothing")

    return ast.literal_eval(result.stdout)

def season_number(season: list) -> int:
    tail = season[0].rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def select_episodes(info: dict, render) -> list[str]:
    content = info["content"]

    # Seasons are lists of their url and their episodes, season 0 is just specials
    seasons = sorted(
        (c for c in content if isinstance(c, list) and season_number(c) > 0),
        key=season_number,
    )

    # Movies have no seasons, so there is only the one url to download
    if not seasons:
        return [content[0]]

    # Choose seasons
    if len(seasons) > 1:
        by_url = {s[0]: s for s in seasons}
        chosen = inquirer.checkbox(
            "Seasons:   ",
            choices=[(f"Season {season_number(s)}", s[0]) for s in seasons],
            default=[seasons[0][0]],
            render=render,
        )
        seasons = [by_url[url] for url in chosen]

    # Choose whether to pick single episodes, otherwise aniworld downloads whole seasons
    if not inquirer.list_input("Episodes:  ", choices=[("All", False), ("Select", True)], render=render):
        return [s[0] for s in seasons]

    # Choose episodes
    episodes = [
        (f"S{season_number(s):02d}E{e['episode_number']:02d} {term.bright_black}({e.get('title_en') or e.get('title_de') or ''}){term.normal}", e["url"])
        for s in seasons
        for e in s[1:]
    ]
    return inquirer.checkbox("Episodes:  ", choices=episodes, render=render)

if __name__ == "__main__":
    assert PROGRESS.search("Show S01E001 - [####------]  42.0% | 00:11:39 | 19.9x").groups() == ("S01E001", "42.0")
    assert PROGRESS.search("Show S01E001 - [ 42%] 12.3/45.6 MB").groups() == ("S01E001", "42")
    assert PROGRESS.search("Downloading files...") is None
    print(search_aniworld("cyberpunk edgerunners", "show"))
