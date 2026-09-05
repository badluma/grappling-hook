import argparse
from . import __version__

def _quality_list(value: str) -> list[str]:
    qualities = value.split(",")
    for q in qualities:
        if q not in ("low", "medium", "high"):
            raise argparse.ArgumentTypeError(f"Invalid quality: {q!r} (choose from low, medium, high)")
    return qualities


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Terminal client for downloading Movies and TV shows from The Pirate Bay.",
        add_help=False,
    )
    parser.add_argument(
        "-h",
        "--help",
        help="Show this message and exit",
        action="help"
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Show the version number and exit",
        action="version",
        version=__version__
    )
    parser.add_argument(
        "-c",
        "--category",
        choices=["movie", "show"],
        help="Category of the media"
    )
    parser.add_argument(
        "-s",
        "--search",
        dest="query",
        help="Search query to look up on The Pirate Bay and Aniworld"
    )
    parser.add_argument(
        "-d",
        "--dub",
        action=argparse.BooleanOptionalAction,
        help="Download a dub alongside the torrent, or skip the question with --no-dub"
    )
    parser.add_argument(
        "-l",
        "--language",
        choices=["German Dub", "English Dub", "German Sub", "English Sub"],
        help="Language of the dub, overrides the config for this run"
    )
    parser.add_argument(
        "-m",
        "--merge",
        nargs=2,
        metavar=("VIDEO", "DUB"),
        help="Merge two folders that are already downloaded instead of downloading, video folder first"
    )
    parser.add_argument(
        "-o",
        "--offset",
        type=float,
        default=0.0,
        help="Shift the dub audio by SECONDS when merging, positive delays it (e.g. -o 1.0)"
    )
    parser.add_argument(
        "-q",
        "--quality",
        dest="qualities",
        type=_quality_list,
        help="Qualities of the media to include (comma-separated: low,medium,high)"
    )
    return parser.parse_args(argv)
