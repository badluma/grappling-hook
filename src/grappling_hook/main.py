import sys

import inquirer
from thepiratebay_api import TorrentClient

from . import functions, style
from .arguments import parse_args

MOVIE_QUALITIES = [("2160p+", 211), ("720p-1080p", 207), ("≤480p", 201)]
SHOW_QUALITIES = [("2160p+", 212), ("720p-1080p", 208), ("≤480p", 201)]
QUALITY_NAMES = {"high": 0, "medium": 1, "low": 2}


def run(args) -> None:
    with functions.hidden_cursor():
        _run(args)


def _run(args) -> None:
    render = style.render()

    functions.boot()

    category = args.category or inquirer.list_input(
        "Categories:", choices=["Movie", "Show"], render=render
    ).lower()

    qualities = MOVIE_QUALITIES if category == "movie" else SHOW_QUALITIES
    if args.qualities:
        quality = [qualities[QUALITY_NAMES[q]][1] for q in args.qualities]
    else:
        quality = inquirer.checkbox(
            "Quality:   ", choices=qualities, default=[qualities[1][1]], render=render
        )

    if args.query:
        query = args.query
    else:
        with functions.visible_beam_cursor():
            query = inquirer.text("Search:    ", render=render)

    print()

    spinner = functions.Spinner("Searching...").start()
    with TorrentClient() as client:
        torrents = []
        for q in quality:
            torrents.extend(functions.search_category(client, query, q))
    spinner.stop()

    print(f"Results:    {len(torrents)} torrent{'s' if len(torrents) != 1 else ''}")
    if not torrents:
        return

    def keep(t) -> bool:
        return not functions.is_episode(t.title)

    longest_name_length = max((len(t.title) for t in torrents if keep(t)), default=0)

    results = [
        (f"{t.title:<{longest_name_length}} | {t.size}", i)
        for i, t in enumerate(torrents)
        if keep(t)
    ]

    selected = inquirer.list_input("Select:     ", choices=results, render=render)

    functions.open_that(torrents[selected].magnet_link)
    print("\nOpened magnet link in default app.")

    actions = [("Done", 0), ("Reopen magnet link", 1), ("Show magnet link", 2), ("Cancel", 3)]
    while True:
        action = inquirer.list_input(
            "Select 'Done' when the download finished.", choices=actions, render=render
        )
        if action == 1:
            functions.open_that(torrents[selected].magnet_link)
        elif action == 2:
            print(f"\nMagnet link: {torrents[selected].magnet_link}\n")
        elif action == 3:
            sys.exit(0)
        else:
            break


def main() -> None:
    args = parse_args()
    try:
        run(args)
    except KeyboardInterrupt:
        return
    except Exception as e:  # noqa: BLE001 - mirrors the Rust top-level error print
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
