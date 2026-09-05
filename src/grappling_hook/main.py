import os
import sys

import inquirer
import threading
from concurrent.futures import ThreadPoolExecutor
from inquirer.themes import term
from thepiratebay_api import TorrentClient

from . import functions, style
from .arguments import parse_args
from .data import data
from .downloader import download_dub, download_torrent, get_info, search_aniworld, select_episodes


MOVIE_QUALITIES = [("2160p+", 211), ("720p-1080p", 207), ("≤480p", 201)]
SHOW_QUALITIES = [("2160p+", 212), ("720p-1080p", 208), ("≤480p", 201)]
QUALITY_NAMES = {"high": 0, "medium": 1, "low": 2}


def run(args) -> None:
    with functions.hidden_cursor():
        _run(args)


def _run(args) -> None:
    render = style.render()

    functions.boot()

    # Merge two folders that are already on disk instead of downloading anything
    if args.merge:
        video_dir, dub_dir = args.merge
        for folder in (video_dir, dub_dir):
            if not os.path.isdir(folder):
                raise RuntimeError(f"Not a folder: {folder}")
        merge(functions.walk_files(video_dir), functions.walk_files(dub_dir), video_dir, render, args.offset)
        return

    # Choose category
    category = args.category or inquirer.list_input(
        "Categories:", choices=["Movie", "Show"], render=render
    ).lower()

    # Choose qualities
    qualities = MOVIE_QUALITIES if category == "movie" else SHOW_QUALITIES
    if args.qualities:
        quality = [qualities[QUALITY_NAMES[q]][1] for q in args.qualities]
    else:
        quality = inquirer.checkbox(
            "Quality:   ", choices=qualities, default=[qualities[1][1]], render=render
        )

    # Search
    if args.query:
        query = args.query
    else:
        with functions.visible_beam_cursor():
            query = inquirer.text("Search:    ", render=render)

    print()

    # Show loading animation
    spinner = functions.Spinner("Searching...").start()
    with TorrentClient() as client, ThreadPoolExecutor() as pool:
        results = pool.map(lambda q: functions.search_category(client, query, q), quality)
        torrents = [t for r in results for t in r]
    spinner.stop()
    torrents = [t for t in torrents if not functions.is_episode(t.title)]

    # Show results
    print(f"Results:    {len(torrents)} torrent{'s' if len(torrents) != 1 else ''}")
    if not torrents:
        return

    # Label torrents with size for inquiry
    results = [
        (f"{t.title} {term.bright_black}({t.size}){term.normal}", i)
        for i, t in enumerate(torrents)
    ]

    # Choose result
    selected = inquirer.list_input("Select:    ", choices=results, render=render)

    # Choose whether to download dub
    if args.language:
        data["language"] = args.language
    is_dub = args.dub if args.dub is not None else inquirer.list_input(
        "Dub:       ", choices=[("Yes", True), ("No", False)], render=render
    )

    status = {}
    if is_dub:

        # Choose dub
        dub_results = search_aniworld(query, category)
        dub_url = inquirer.list_input("Select:    ", choices=dub_results, render=render)

        # Choose what to download of it
        episodes = select_episodes(get_info(dub_url), render)

        # Start the dub download next to the torrent
        if episodes:
            status = {"dub": "preparing..."}
            threading.Thread(target=download_dub, args=(episodes, status), daemon=True).start()

    # Download selected torrent
    root, files = download_torrent(torrents[selected].magnet_link, status)

    # Nothing to merge without a dub
    dubs = status.get("files")
    if dubs:
        merge(files, dubs, root, render, args.offset)


def merge(files: list[str], dubs: list[str], root: str, render, offset: float = 0.0) -> None:

    # Show which dub was matched to which torrent episode
    matches = functions.match_episodes(files, dubs)
    if not matches:
        print("Nothing to merge")
        return
    print()
    functions.print_matches(matches)

    # Let the user fix the matches episode by episode
    if not inquirer.list_input("Correct:   ", choices=[("Yes", True), ("No", False)], render=render):
        matches = functions.pick_matches(matches, dubs, render)
        print()
        functions.print_matches(matches)

    functions.merge_audio(matches, offset)

    # Rename the folder the torrent downloaded into
    if inquirer.list_input("Rename:    ", choices=[("No", False), ("Yes", True)], render=render):
        with functions.visible_beam_cursor():
            name = inquirer.text("Name:      ", default=os.path.basename(root), render=render)
        if name:
            os.rename(root, os.path.join(os.path.dirname(root), name))


def main() -> None:
    args = parse_args()
    try:
        run(args)
    except KeyboardInterrupt: # Quit if interrupted
        functions.quit_now(130)
    except Exception as e: # Quit and show error message
        print(e, file=sys.stderr)
        functions.quit_now(1)
    functions.quit_now(0)


if __name__ == "__main__":
    main()
